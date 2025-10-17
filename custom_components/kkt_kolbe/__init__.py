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
from .coordinator import KKTKolbeUpdateCoordinator
from .services import async_setup_services, async_unload_services
# Lazy import discovery to reduce startup time

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.FAN, Platform.LIGHT, Platform.SWITCH, Platform.SELECT, Platform.NUMBER, Platform.BINARY_SENSOR]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the KKT Kolbe component from YAML configuration."""
    # Start automatic discovery when Home Assistant starts
    # This enables discovery even before any devices are configured

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

    # Initialize Tuya device connection (async)
    # Use correct key names from config entry
    ip_address = entry.data.get(CONF_IP_ADDRESS) or entry.data.get("ip_address") or entry.data.get("host")
    device_id = entry.data.get(CONF_DEVICE_ID) or entry.data.get("device_id")
    local_key = entry.data.get(CONF_ACCESS_TOKEN) or entry.data.get("local_key")

    device = KKTKolbeTuyaDevice(
        device_id=device_id,
        ip_address=ip_address,
        local_key=local_key,
    )

    # Initialize coordinator
    coordinator = KKTKolbeUpdateCoordinator(hass, entry, device)

    # Test connection to validate credentials early
    try:
        await device.async_connect()
        # Perform initial data fetch
        await coordinator.async_config_entry_first_refresh()
    except Exception as e:
        _LOGGER.error(f"Failed to connect to device during setup: {e}")
        raise

    # Determine device type and platforms based on product name
    from .device_types import get_device_info_by_product_name, get_device_platforms

    product_name = entry.data.get("product_name", "unknown")

    # For manual setup, try to detect product_name from device if possible
    if product_name == "unknown":
        try:
            # Try to get device info to detect product name
            device_status = await device.async_get_status()
            # Here we could add logic to detect device type from status
            # For now, use fallback detection
        except Exception as e:
            _LOGGER.debug(f"Could not get device status for product detection: {e}")

    device_info = get_device_info_by_product_name(product_name)
    platforms = get_device_platforms(device_info["category"])

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "device": device,
        "config": entry.data,
        "device_info": device_info,
        "product_name": product_name,
    }

    # Register device in device registry
    from homeassistant.helpers import device_registry as dr
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        **coordinator.device_info
    )

    # Load only the platforms needed for this specific device
    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    # Set up services when the first device is added
    if len(hass.data[DOMAIN]) == 1:
        await async_setup_services(hass)
        _LOGGER.info("KKT Kolbe services initialized")

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

        # Unload services when the last device is removed
        if not hass.data[DOMAIN]:
            await async_unload_services(hass)
            _LOGGER.info("KKT Kolbe services unloaded")

            from .discovery import async_stop_discovery
            await async_stop_discovery()

    return unload_ok