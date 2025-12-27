"""Base utilities for KKT Kolbe config flows."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant

# Import is_private_ip from helpers to avoid duplication
from ..helpers.validation import is_private_ip

_LOGGER = logging.getLogger(__name__)


async def test_device_connection(
    ip_address: str,
    device_id: str,
    local_key: str,
    timeout: float = 10.0,
) -> bool:
    """Test connection to device using enhanced testing method.

    Args:
        ip_address: Device IP address.
        device_id: Tuya device ID.
        local_key: Tuya local key.
        timeout: Connection timeout in seconds.

    Returns:
        True if connection successful, False otherwise.
    """
    from ..tuya_device import KKTKolbeTuyaDevice

    try:
        device = KKTKolbeTuyaDevice(device_id, ip_address, local_key)

        # Use the async_test_connection method with built-in timeout protection
        return await device.async_test_connection()

    except Exception as exc:
        _LOGGER.debug("Connection test failed: %s", exc)
        return False


async def try_discover_local_ip(
    hass: HomeAssistant,
    device_id: str,
    timeout: float = 6.0,
) -> str | None:
    """Try to discover the local IP address of a device via mDNS/UDP.

    Args:
        hass: Home Assistant instance.
        device_id: The Tuya device ID to find.
        timeout: Discovery timeout in seconds.

    Returns:
        Local IP address if found, None otherwise.
    """
    from ..discovery import async_start_discovery, get_discovered_devices

    _LOGGER.debug(f"Trying to discover local IP for device {device_id[:8]}...")

    try:
        # Start discovery
        await async_start_discovery(hass)

        # Wait for discovery to complete
        await asyncio.sleep(timeout)

        # Get discovered devices
        discovered = get_discovered_devices()

        # Look for matching device by ID
        for disc_id, disc_info in discovered.items():
            if disc_id == device_id:
                ip = disc_info.get("ip") or disc_info.get("host")
                if ip:
                    _LOGGER.info(f"Discovered local IP {ip} for device {device_id[:8]}")
                    return ip

        _LOGGER.debug(f"Device {device_id[:8]} not found in discovery results")
        return None

    except Exception as err:
        _LOGGER.debug(f"Local IP discovery failed: {err}")
        return None


def create_config_entry_data(
    ip_address: str,
    device_id: str,
    local_key: str,
    product_name: str = "auto",
    device_type: str = "auto",
    product_id: str | None = None,
    integration_mode: str = "hybrid",
    api_enabled: bool = False,
    api_client_id: str | None = None,
    api_client_secret: str | None = None,
    api_endpoint: str | None = None,
) -> dict[str, Any]:
    """Create standardized config entry data dictionary.

    Args:
        ip_address: Device IP address.
        device_id: Tuya device ID.
        local_key: Tuya local key.
        product_name: Internal product name for entity lookup.
        device_type: Device type key.
        product_id: Tuya product ID (optional).
        integration_mode: Either 'hybrid' or 'manual'.
        api_enabled: Whether API is enabled.
        api_client_id: Tuya API client ID (if API enabled).
        api_client_secret: Tuya API client secret (if API enabled).
        api_endpoint: Tuya API endpoint (if API enabled).

    Returns:
        Dictionary suitable for config entry data.
    """
    data = {
        CONF_IP_ADDRESS: ip_address,
        "device_id": device_id,
        "local_key": local_key,
        "product_name": product_name,
        "device_type": device_type,
        "integration_mode": integration_mode,
    }

    if product_id:
        data["product_id"] = product_id

    if api_enabled:
        data["api_enabled"] = True
        if api_client_id:
            data["api_client_id"] = api_client_id
        if api_client_secret:
            data["api_client_secret"] = api_client_secret
        if api_endpoint:
            data["api_endpoint"] = api_endpoint

    return data


def get_default_options() -> dict[str, Any]:
    """Get default options for new config entries.

    Returns:
        Dictionary with default option values.
    """
    return {
        "enable_advanced_entities": True,
        "enable_debug_logging": False,
    }


def build_entry_title(
    friendly_type: str | None = None,
    device_name: str | None = None,
    device_id: str | None = None,
) -> str:
    """Build a descriptive title for config entry.

    Args:
        friendly_type: Friendly device type name (e.g., "HERMES Style Hood").
        device_name: Device name from API or user.
        device_id: Device ID for fallback.

    Returns:
        Descriptive title string.
    """
    if friendly_type:
        return friendly_type

    if device_name and device_name != "Unknown":
        return f"KKT Kolbe {device_name}"

    if device_id:
        return f"KKT Kolbe Device {device_id[:8]}"

    return "KKT Kolbe Device"


def get_friendly_device_type(device_type: str) -> str:
    """Get friendly name for a device type key.

    Args:
        device_type: Device type key from KNOWN_DEVICES.

    Returns:
        Friendly display name.
    """
    from ..device_types import KNOWN_DEVICES

    if device_type in KNOWN_DEVICES:
        return KNOWN_DEVICES[device_type].get("name", device_type)

    return device_type.replace("_", " ").title()
