"""Server-side scan geolocation helpers.

Used as a fallback when the QR landing page client does not send
city/country/lat/lng in the scan payload.
"""

import asyncio
import hashlib
import ipaddress
import json
import logging

import httpx
import redis.asyncio as aioredis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)

IPINFO_URL = "https://ipinfo.io/{}/json"
_IPINFO_CACHE_TTL_SECONDS = 24 * 60 * 60
_IPINFO_CACHE_PREFIX = "qseal:ipinfo:lookup:"
NOMINATIM_REVERSE_GEOCODING_URL = "https://nominatim.openstreetmap.org/reverse"
_NOMINATIM_CACHE_TTL_SECONDS = 30 * 24 * 60 * 60
_NOMINATIM_CACHE_PREFIX = "qseal:nominatim:reverse:"
_NOMINATIM_RATE_KEY = "qseal:nominatim:request-slot"
_NOMINATIM_LOCK_KEY = "qseal:nominatim:request-lock"
_NOMINATIM_LOCK_TIMEOUT_SECONDS = 20
_geoip_redis: aioredis.Redis | None = None
_geoip_redis_init_lock = asyncio.Lock()


def _is_private_ip(ip: str) -> bool:
    """Skip IPs that cannot be reliably geolocated as public addresses."""
    try:
        return not ipaddress.ip_address(ip).is_global
    except ValueError:
        return True


async def lookup_ip(ip_address: str | None) -> dict | None:
    """Look up geolocation for a public IP address.

    Args:
        ip_address: IPv4 or IPv6 address string.

    Returns:
        dict with ipinfo location details and normalized city/state/country and
        latitude/longitude keys, or None if the IP is not public or lookup fails.
    """
    if not ip_address or _is_private_ip(ip_address):
        return None

    normalized_ip = str(ipaddress.ip_address(ip_address))
    cache_key = (
        _IPINFO_CACHE_PREFIX
        + hashlib.sha256(normalized_ip.encode("ascii")).hexdigest()
    )
    redis_client = None
    try:
        redis_client = await _get_geoip_redis()
        cached = await redis_client.get(cache_key)
        if cached:
            result = json.loads(cached)
            result["ip"] = normalized_ip
            return result
    except Exception:
        # IP enrichment is best effort. Keep it available when Redis is down;
        # a successful lookup will still be returned to the caller.
        logger.debug("geoip: IP lookup cache unavailable", exc_info=True)

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(IPINFO_URL.format(normalized_ip))
            resp.raise_for_status()
            data = resp.json()
        if data.get("bogon"):
            return None

        loc = data.get("loc") or ""
        latitude = longitude = None
        if loc:
            try:
                latitude_text, longitude_text = loc.split(",", 1)
                latitude = float(latitude_text)
                longitude = float(longitude_text)
            except (TypeError, ValueError):
                logger.debug("ipinfo returned an invalid location value")

        region = data.get("region") or ""
        result = {
            "ip": data.get("ip") or normalized_ip,
            "city": data.get("city") or "",
            "region": region,
            "state": region,
            "country": data.get("country") or "",
            "postal": data.get("postal") or "",
            "loc": loc,
            "org": data.get("org") or "",
            "timezone": data.get("timezone") or "",
            "source": "ipinfo.io",
            "latitude": latitude,
            "longitude": longitude,
        }
        # Do not store the visitor's raw IP in Redis. The hashed cache key is
        # enough to reuse the non-identifying location fields for a day.
        if redis_client:
            cache_value = {key: value for key, value in result.items() if key != "ip"}
            try:
                await redis_client.setex(
                    cache_key,
                    _IPINFO_CACHE_TTL_SECONDS,
                    json.dumps(cache_value),
                )
            except RedisError:
                logger.debug("geoip: unable to cache IP location", exc_info=True)
        return result
    except Exception:
        logger.debug("geoip: ipinfo lookup failed", exc_info=True)

    return None


async def reverse_geocode(latitude: float, longitude: float) -> dict | None:
    """Translate browser GPS coordinates into a cached, human-readable place.

    Nominatim's public endpoint is limited to one request per second. A Redis
    lock and expiring request slot enforce that limit across core-service
    processes; the coordinate is rounded for lookup and its cache key is
    hashed so precise GPS values are not stored in Redis keys.
    """
    # City/region/country labels do not need street-level precision. Rounding
    # also increases cache hits without displaying the coordinates to users.
    lookup_latitude = round(latitude, 4)
    lookup_longitude = round(longitude, 4)
    cache_digest = hashlib.sha256(
        f"{lookup_latitude:.4f},{lookup_longitude:.4f}".encode("ascii")
    ).hexdigest()
    cache_key = f"{_NOMINATIM_CACHE_PREFIX}{cache_digest}"
    url = settings.reverse_geocoding_url or NOMINATIM_REVERSE_GEOCODING_URL
    params = {
        "lat": lookup_latitude,
        "lon": lookup_longitude,
        "format": "jsonv2",
        "addressdetails": 1,
        "zoom": 14,
    }

    try:
        redis_client = await _get_geoip_redis()
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        request_lock = redis_client.lock(
            _NOMINATIM_LOCK_KEY,
            timeout=_NOMINATIM_LOCK_TIMEOUT_SECONDS,
            blocking_timeout=_NOMINATIM_LOCK_TIMEOUT_SECONDS,
        )
        if not await request_lock.acquire():
            logger.warning("Nominatim request queue is full; skipping reverse geocode")
            return None
        try:
            # A second caller may have filled the cache while this call waited.
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            # Redis expiry provides a shared one-second interval, independent
            # of worker clock skew.
            while not await redis_client.set(
                _NOMINATIM_RATE_KEY, "1", nx=True, ex=1
            ):
                await asyncio.sleep(0.05)

            async with httpx.AsyncClient(
                timeout=settings.reverse_geocoding_timeout_seconds,
                headers={
                    "User-Agent": f"Brandwise-QSeal/{settings.app_version}",
                    "Accept-Language": "en",
                },
            ) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()

            address = payload.get("address") or {}
            display_name = payload.get("display_name")
            city = next(
                (
                    address.get(field)
                    for field in (
                        "_normalized_city",
                        "city",
                        "town",
                        "township",
                        "village",
                        "municipality",
                        "suburb",
                        "city_district",
                        "county",
                    )
                    if address.get(field)
                ),
                None,
            )
            result = {
                "city": city,
                "state": (
                    address.get("state")
                    or address.get("region")
                    or address.get("province")
                ),
                "country": address.get("country"),
                # Bound provider-controlled text before persisting it.
                "street_address": display_name or None,
            }
            if result["street_address"]:
                result["street_address"] = result["street_address"][:1000]
            if any(result.values()):
                await redis_client.setex(
                    cache_key,
                    _NOMINATIM_CACHE_TTL_SECONDS,
                    json.dumps(result),
                )
                return result
            return None
        finally:
            await request_lock.release()
    except (RedisError, json.JSONDecodeError):
        logger.warning(
            "Nominatim reverse geocoding requires the configured Redis service",
            exc_info=True,
        )
        return None
    except Exception:
        logger.warning(
            "reverse geocoding failed for supplied browser coordinates",
            exc_info=True,
        )
        return None


async def _get_geoip_redis() -> aioredis.Redis:
    """Create the shared async Redis client used for geolocation caches."""
    global _geoip_redis
    if _geoip_redis is None:
        async with _geoip_redis_init_lock:
            if _geoip_redis is None:
                _geoip_redis = aioredis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
    return _geoip_redis
