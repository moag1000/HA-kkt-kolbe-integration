"""KKT Kolbe Dunstabzugshaube Integration for Home Assistant."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    Platform,
    CONF_HOST,
    CONF_DEVICE_ID,
    CONF_ACCESS_TOKEN,
)

from .const import DOMAIN
from .tuya_device import KKTKolbeTuyaDevice
# Lazy import discovery to reduce startup time

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.FAN, Platform.LIGHT, Platform.SWITCH, Platform.SELECT, Platform.NUMBER]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the KKT Kolbe component from YAML configuration."""
    # Start automatic discovery when Home Assistant starts
    # This enables discovery even before any devices are configured
    _LOGGER.info("Starting KKT Kolbe automatic device discovery...")

    # Lazy import to reduce blocking time
    from .discovery import async_start_discovery
    await async_start_discovery(hass)

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up KKT Kolbe from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Start mDNS discovery if this is the first device
    if not hass.data[DOMAIN]:
        from .discovery import async_start_discovery
        await async_start_discovery(hass)

    # Initialize Tuya device connection
    device = KKTKolbeTuyaDevice(
        device_id=entry.data[CONF_DEVICE_ID],
        ip_address=entry.data[CONF_HOST],
        local_key=entry.data[CONF_ACCESS_TOKEN],
    )

    # Determine device type and platforms based on product name
    from .device_types import get_device_info_by_product_name, get_device_platforms

    product_name = entry.data.get("product_name", "unknown")
    device_info = get_device_info_by_product_name(product_name)
    platforms = get_device_platforms(device_info["category"])

    hass.data[DOMAIN][entry.entry_id] = {
        "device": device,
        "config": entry.data,
        "device_info": device_info,
        "product_name": product_name,
    }

    # Load only the platforms needed for this specific device
    await hass.config_entries.async_forward_entry_setups(entry, platforms)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Get the platforms that were loaded for this specific device
    from .device_types import get_device_info_by_product_name, get_device_platforms

    product_name = entry.data.get("product_name", "unknown")
    device_info = get_device_info_by_product_name(product_name)
    platforms = get_device_platforms(device_info["category"])

    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

        # Stop discovery if no more devices
        if not hass.data[DOMAIN]:
            from .discovery import async_stop_discovery
            await async_stop_discovery()

    return unload_ok