"""KKT Kolbe Dunstabzugshaube Integration for Home Assistant."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    Platform,
    CONF_HOST,
    CONF_IP_ADDRESS,
    CONF_DEVICE_ID,
    CONF_ACCESS_TOKEN,
)

from .const import DOMAIN
# Heavy imports moved to lazy loading to prevent blocking the event loop

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

    # Discovery is already started in async_setup, no need to start again

    # Check integration mode (V2 config flow adds this)
    integration_mode = entry.data.get("integration_mode", "manual")
    api_enabled = entry.data.get("api_enabled", False)

    device = None
    api_client = None
    coordinator = None

    # Initialize API client if enabled
    if api_enabled:
        from .api import TuyaCloudClient

        client_id = entry.data.get("api_client_id")
        client_secret = entry.data.get("api_client_secret")
        endpoint = entry.data.get("api_endpoint", "https://openapi.tuyaeu.com")

        if client_id and client_secret:
            api_client = TuyaCloudClient(
                client_id=client_id,
                client_secret=client_secret,
                endpoint=endpoint,
            )
            _LOGGER.info("API client initialized for TinyTuya Cloud API")

    # Initialize local device if we have local connection details
    ip_address = entry.data.get(CONF_IP_ADDRESS) or entry.data.get("ip_address") or entry.data.get("host")
    device_id = entry.data.get(CONF_DEVICE_ID) or entry.data.get("device_id")
    local_key = entry.data.get(CONF_ACCESS_TOKEN) or entry.data.get("local_key")

    if ip_address and device_id and local_key:
        from .tuya_device import KKTKolbeTuyaDevice

        device = KKTKolbeTuyaDevice(
            device_id=device_id,
            ip_address=ip_address,
            local_key=local_key,
        )
        _LOGGER.info("Local device initialized")
    elif integration_mode == "manual":
        # For manual mode, local connection is required
        if not device_id:
            raise ValueError("Device ID not found in config entry data")
        if not ip_address:
            raise ValueError("IP address not found in config entry data")
        if not local_key:
            raise ValueError("Local key not found in config entry data")

    # Initialize appropriate coordinator based on mode
    if integration_mode in ["hybrid", "api_discovery"] and (device or api_client):
        from .hybrid_coordinator import KKTKolbeHybridCoordinator

        coordinator = KKTKolbeHybridCoordinator(
            hass=hass,
            device_id=device_id,
            local_device=device,
            api_client=api_client,
            prefer_local=(integration_mode == "hybrid"),
        )
        _LOGGER.info(f"Hybrid coordinator initialized in {integration_mode} mode")
    elif device:
        # Legacy mode - local only
        from .coordinator import KKTKolbeUpdateCoordinator

        coordinator = KKTKolbeUpdateCoordinator(hass, entry, device)
        _LOGGER.info("Legacy coordinator initialized for local communication")
    else:
        raise ValueError("No valid communication method configured")

    # Test connection to validate credentials early
    # For hybrid/API mode, allow setup even if local connection fails initially
    connection_successful = False
    local_connection_failed = False

    try:
        if device:
            try:
                await device.async_connect()
                connection_successful = True
                _LOGGER.info("Local device connection successful during setup")
            except Exception as e:
                local_connection_failed = True
                _LOGGER.warning(f"Local device connection failed during setup: {e}")

                # Only raise if this is manual mode (requires local connection)
                if integration_mode == "manual":
                    _LOGGER.error("Manual mode requires working local connection")
                    raise

        if api_client:
            try:
                await api_client.test_connection()
                connection_successful = True
                _LOGGER.info("API connection successful during setup")
            except Exception as e:
                _LOGGER.warning(f"API connection failed during setup: {e}")

                # Only raise if this is API-only mode and local also failed
                if integration_mode == "api_discovery" and local_connection_failed:
                    _LOGGER.error("API mode requires working API connection")
                    raise

        # Perform initial data fetch if at least one connection method works
        if connection_successful or integration_mode in ["hybrid", "api_discovery"]:
            try:
                await coordinator.async_config_entry_first_refresh()
                _LOGGER.info("Initial data fetch successful")
            except Exception as e:
                _LOGGER.warning(f"Initial data fetch failed, coordinator will retry: {e}")
                # Don't raise here - let coordinator handle retries
        else:
            _LOGGER.error("No working connection methods available")
            raise ValueError("No working connection methods configured")

    except Exception as e:
        _LOGGER.error(f"Critical error during setup: {e}")
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
        "api_client": api_client,
        "config": entry.data,
        "device_info": device_info,
        "product_name": product_name,
        "integration_mode": integration_mode,
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
        from .services import async_setup_services
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
            from .services import async_unload_services
            await async_unload_services(hass)
            _LOGGER.info("KKT Kolbe services unloaded")

            from .discovery import async_stop_discovery
            await async_stop_discovery()

    return unload_ok