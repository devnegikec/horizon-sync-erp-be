"""Auto-parse User-Agent strings into structured device/browser/OS data.

Requires: pip install user-agents
"""

from user_agents import parse


def parse_user_agent(ua_string: str | None) -> dict | None:
    """Parse a raw User-Agent header into structured metadata.

    Args:
        ua_string: Raw User-Agent header value (e.g. from request.headers).

    Returns:
        dict with browser, os, device_type, is_mobile/is_tablet/is_pc/is_bot
        fields, or None if input is empty/None.
    """
    if not ua_string:
        return None

    ua = parse(ua_string)

    return {
        "browser": ua.browser.family or None,
        "browser_version": ua.browser.version_string or None,
        "os": ua.os.family or None,
        "os_version": ua.os.version_string or None,
        "device_type": _device_type(ua),
        "device_family": ua.device.family or None,
        "device_brand": ua.device.brand or None,
        "device_model": ua.device.model or None,
        "is_mobile": ua.is_mobile,
        "is_tablet": ua.is_tablet,
        "is_pc": ua.is_pc,
        "is_bot": ua.is_bot,
    }


def _device_type(ua) -> str:
    """Map parsed UA to a simple device category string."""
    if ua.is_tablet:
        return "tablet"
    if ua.is_mobile:
        return "mobile"
    if ua.is_pc:
        return "desktop"
    return "unknown"
