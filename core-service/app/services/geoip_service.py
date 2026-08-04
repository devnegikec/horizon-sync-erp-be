"""Server-side IP geolocation via ip-api.com (free tier, no API key).

Used as a fallback when the QR landing page client does not send
city/country/lat/lng in the scan payload.
"""

import logging

import httpx

logger = logging.getLogger(__name__)

# ip-api.com free tier: 45 requests/minute, no API key required.
# Returns: status, country, regionName, city, lat, lon
IP_API_URL = "http://ip-api.com/json/{}?fields=status,country,regionName,city,lat,lon"

# Private/local IPs we skip (ip-api would return garbage for these).
_PRIVATE_PREFIXES = (
    "127.",
    "10.",
    "192.168.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "0.",
    "169.254.",
)


def _is_private_ip(ip: str) -> bool:
    """Check if an IP is private/local — skip lookup."""
    return ip in ("127.0.0.1", "::1", "localhost") or ip.startswith(_PRIVATE_PREFIXES)


async def lookup_ip(ip_address: str | None) -> dict | None:
    """Look up geolocation for a public IP address.

    Args:
        ip_address: IPv4 or IPv6 address string.

    Returns:
        dict with country, state, city, latitude, longitude keys,
        or None if the IP is private or lookup fails.
    """
    if not ip_address or _is_private_ip(ip_address):
        return None

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(IP_API_URL.format(ip_address))
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "success":
                return {
                    "country": data.get("country"),
                    "state": data.get("regionName"),
                    "city": data.get("city"),
                    "latitude": data.get("lat"),
                    "longitude": data.get("lon"),
                }
            else:
                logger.debug(
                    "geoip: ip-api returned status=%s for %s",
                    data.get("status"),
                    ip_address,
                )
    except Exception:
        logger.debug("geoip: lookup failed for %s", ip_address, exc_info=True)

    return None
