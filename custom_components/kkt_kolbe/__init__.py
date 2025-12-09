"""KKT Kolbe Dunstabzugshaube Integration for Home Assistant."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    Platform,
    CONF_HOST,
    CONF_IP_ADDRESS,
    CONF_DEVICE_ID,
    CONF_ACCESS_TOKEN,
)
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, CONF_API_ENDPOINT
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

    # Start stale device tracker (Gold Tier requirement)
    from .device_tracker import async_start_tracker
    await async_start_tracker(hass)

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
            hass=hass,  # Pass hass for proper executor job scheduling
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
    from .exceptions import KKTConnectionError, KKTTimeoutError, KKTAuthenticationError

    connection_successful = False
    local_connection_failed = False
    local_error_msg = None

    try:
        if device:
            try:
                await device.async_connect()
                connection_successful = True
                _LOGGER.info("Local device connection successful during setup")
            except KKTAuthenticationError as e:
                # Authentication errors should trigger reauth flow
                _LOGGER.error(
                    f"Authentication failed for device at {ip_address}. "
                    f"Local key may be incorrect or expired."
                )

                # Create repair issue for expired local key
                ir.async_create_issue(
                    hass,
                    DOMAIN,
                    f"local_key_expired_{entry.entry_id}",
                    is_fixable=True,
                    severity=ir.IssueSeverity.ERROR,
                    translation_key="local_key_expired",
                    translation_placeholders={
                        "entry_title": entry.title,
                        "device_id": entry.data.get(CONF_DEVICE_ID, "Unknown"),
                    },
                    data={
                        "entry_id": entry.entry_id,
                        "entry_title": entry.title,
                        "device_id": entry.data.get(CONF_DEVICE_ID, "Unknown"),
                    },
                )

                raise ConfigEntryAuthFailed(
                    f"Authentication failed: {e}. Please check your local key."
                ) from e
            except (KKTConnectionError, KKTTimeoutError) as e:
                local_connection_failed = True
                local_error_msg = str(e)

                # Log at debug level to avoid filling logs (HA Best Practice)
                _LOGGER.debug(
                    f"Device connection failed during setup: {e}. "
                    f"Common causes: offline device, network unreachable, firewall."
                )

                # Only raise if this is manual mode (requires local connection)
                if integration_mode == "manual":
                    # For temporary connection issues, use ConfigEntryNotReady
                    # This tells HA to retry setup automatically
                    _LOGGER.warning(
                        f"Device at {ip_address} is not reachable. "
                        f"Home Assistant will retry setup automatically."
                    )
                    raise ConfigEntryNotReady(
                        f"Device not reachable at {ip_address}: {e}"
                    ) from e
            except Exception as e:
                local_connection_failed = True
                local_error_msg = str(e)
                _LOGGER.debug(f"Unexpected error during local connection: {e}")

                if integration_mode == "manual":
                    _LOGGER.warning("Device connection failed, will retry automatically")
                    raise ConfigEntryNotReady(f"Setup failed: {e}") from e

        if api_client:
            try:
                await api_client.test_connection()
                connection_successful = True
                _LOGGER.info("API connection successful during setup")
            except Exception as e:
                _LOGGER.debug(f"API connection failed during setup: {e}")

                # Only raise if this is API-only mode and local also failed
                if integration_mode == "api_discovery" and local_connection_failed:
                    # Check if it's an auth issue
                    if "auth" in str(e).lower() or "401" in str(e) or "403" in str(e):
                        # Create repair issue for API authentication
                        ir.async_create_issue(
                            hass,
                            DOMAIN,
                            f"tuya_api_auth_failed_{entry.entry_id}",
                            is_fixable=True,
                            severity=ir.IssueSeverity.ERROR,
                            translation_key="tuya_api_auth_failed",
                            translation_placeholders={
                                "entry_title": entry.title,
                            },
                            data={
                                "entry_id": entry.entry_id,
                                "entry_title": entry.title,
                            },
                        )

                        raise ConfigEntryAuthFailed(
                            f"API authentication failed: {e}. Please check credentials."
                        ) from e
                    # Check if it's a wrong region/endpoint issue (error code 1004)
                    elif "1004" in str(e) or "sign" in str(e).lower():
                        # Create repair issue for wrong region
                        ir.async_create_issue(
                            hass,
                            DOMAIN,
                            f"tuya_api_wrong_region_{entry.entry_id}",
                            is_fixable=True,
                            severity=ir.IssueSeverity.WARNING,
                            translation_key="tuya_api_wrong_region",
                            translation_placeholders={
                                "entry_title": entry.title,
                                "current_endpoint": entry.data.get(CONF_API_ENDPOINT, "Unknown"),
                            },
                            data={
                                "entry_id": entry.entry_id,
                                "entry_title": entry.title,
                                "current_endpoint": entry.data.get(CONF_API_ENDPOINT, "Unknown"),
                            },
                        )

                        raise ConfigEntryAuthFailed(
                            f"API signature validation failed: {e}. Wrong region/endpoint?"
                        ) from e
                    else:
                        _LOGGER.warning("API connection failed, will retry automatically")
                        raise ConfigEntryNotReady(f"API not reachable: {e}") from e

        # Perform initial data fetch if at least one connection method works
        if connection_successful or integration_mode in ["hybrid", "api_discovery"]:
            try:
                await coordinator.async_config_entry_first_refresh()
                _LOGGER.info("Initial data fetch successful")
            except Exception as e:
                # Log at debug to avoid excessive logging (HA Best Practice)
                _LOGGER.debug(f"Initial data fetch failed, coordinator will retry: {e}")
                # Don't raise here - let coordinator handle retries
                # This allows the integration to load even if the first fetch fails
        else:
            error_details = []
            if local_connection_failed and local_error_msg:
                error_details.append(f"Local: {local_error_msg}")
            if not api_client and not device:
                error_details.append("No connection methods configured")

            full_error = " | ".join(error_details) if error_details else "No connection methods available"
            _LOGGER.warning(f"Setup incomplete: {full_error}")
            raise ConfigEntryNotReady(f"Setup incomplete: {full_error}")

    except (ConfigEntryAuthFailed, ConfigEntryNotReady):
        # Re-raise these Home Assistant exceptions as-is
        raise
    except (KKTConnectionError, KKTTimeoutError) as e:
        # Convert connection errors to ConfigEntryNotReady for auto-retry
        _LOGGER.debug(f"Connection error during setup: {e}")
        raise ConfigEntryNotReady(f"Device connection failed: {e}") from e
    except Exception as e:
        _LOGGER.error(f"Unexpected error during setup: {e}", exc_info=True)
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