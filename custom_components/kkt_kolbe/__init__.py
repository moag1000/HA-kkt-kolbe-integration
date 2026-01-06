"""KKT Kolbe Dunstabzugshaube Integration for Home Assistant."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import ConfigEntryNotReady
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir

from .const import CONF_API_ENDPOINT
from .const import CONF_SMARTLIFE_TOKEN_INFO
from .const import DOMAIN
from .const import ENTRY_TYPE_ACCOUNT
from .const import ENTRY_TYPE_DEVICE

if TYPE_CHECKING:
    from .api import TuyaCloudClient
    from .coordinator import KKTKolbeUpdateCoordinator
    from .hybrid_coordinator import KKTKolbeHybridCoordinator
    from .tuya_device import KKTKolbeTuyaDevice

# This integration is config entry only - no YAML configuration
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
# Heavy imports moved to lazy loading to prevent blocking the event loop

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.FAN, Platform.LIGHT, Platform.SWITCH, Platform.SELECT, Platform.NUMBER, Platform.BINARY_SENSOR]


@dataclass
class KKTKolbeRuntimeData:
    """Runtime data for KKT Kolbe device entries."""

    coordinator: KKTKolbeUpdateCoordinator | KKTKolbeHybridCoordinator
    device: KKTKolbeTuyaDevice | None
    api_client: TuyaCloudClient | None
    device_info: dict[str, Any]
    product_name: str
    device_type: str
    integration_mode: str


@dataclass
class KKTKolbeAccountRuntimeData:
    """Runtime data for SmartLife account entries (Parent Entry).

    Account entries manage token information and don't have devices directly.
    They serve as parent entries for device entries.
    """

    token_info: dict[str, Any]
    user_code: str
    app_schema: str  # "smartlife" or "tuyaSmart"
    child_entry_ids: list[str]  # IDs of device entries linked to this account


# Type alias for config entries with runtime data
type KKTKolbeConfigEntry = ConfigEntry[KKTKolbeRuntimeData]
type KKTKolbeAccountConfigEntry = ConfigEntry[KKTKolbeAccountRuntimeData]


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate config entry to a new version.

    This function is called when Home Assistant detects that a config entry
    was created with an older VERSION than the current config_flow.py VERSION.

    Version History:
    - Version 1: Original config entry format (device entries only)
    - Version 2: Added SmartLife support with entry_type (account/device) and setup_mode
    """
    _LOGGER.info(
        "Migrating KKT Kolbe config entry %s from version %s to version 2",
        config_entry.entry_id,
        config_entry.version,
    )

    if config_entry.version == 1:
        # Migrate from version 1 to version 2
        new_data = dict(config_entry.data)

        # Add entry_type if missing (all v1 entries were device entries)
        if "entry_type" not in new_data:
            new_data["entry_type"] = ENTRY_TYPE_DEVICE

        # Add setup_mode if missing (v1 was manual mode only)
        if "setup_mode" not in new_data:
            # Determine setup_mode based on existing fields
            if new_data.get("api_enabled"):
                new_data["setup_mode"] = "iot_platform"
                new_data["integration_mode"] = "hybrid"
            else:
                new_data["setup_mode"] = "manual"
                new_data["integration_mode"] = "manual"

        # HA 2025+: version cannot be set directly, must use async_update_entry
        # Pass both version and data to async_update_entry
        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            version=2,
        )

        _LOGGER.info(
            "Migration of %s complete: entry_type=%s, setup_mode=%s",
            config_entry.entry_id,
            new_data.get("entry_type"),
            new_data.get("setup_mode"),
        )

    return True


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
    """Set up KKT Kolbe from a config entry.

    Dispatches to appropriate setup function based on entry type:
    - account: SmartLife account entry (Parent) - manages tokens
    - device: Device entry (Child or standalone) - manages device connection
    """
    # Keep hass.data for backward compatibility with services
    hass.data.setdefault(DOMAIN, {})

    # Determine entry type - default to "device" for backward compatibility
    entry_type = entry.data.get("entry_type", ENTRY_TYPE_DEVICE)

    if entry_type == ENTRY_TYPE_ACCOUNT:
        return await _async_setup_account_entry(hass, entry)
    else:
        return await _async_setup_device_entry(hass, entry)


async def _async_setup_account_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up a SmartLife account entry (Parent Entry).

    Account entries:
    - Store token information for SmartLife/Tuya Smart authentication
    - Don't create any devices or platforms directly
    - Serve as parent for device entries that use their tokens
    """
    _LOGGER.info("Setting up SmartLife account entry: %s", entry.title)

    # Get token info from entry data
    token_info = entry.data.get(CONF_SMARTLIFE_TOKEN_INFO, {})
    user_code = entry.data.get("smartlife_user_code", "")
    app_schema = entry.data.get("smartlife_app_schema", "smartlife")

    if not token_info:
        _LOGGER.warning(
            "SmartLife account entry %s has no token info stored", entry.entry_id
        )

    # Find child entries linked to this account
    child_entry_ids: list[str] = []
    for config_entry in hass.config_entries.async_entries(DOMAIN):
        if config_entry.data.get("parent_entry_id") == entry.entry_id:
            child_entry_ids.append(config_entry.entry_id)

    # Store runtime data for account entry
    entry.runtime_data = KKTKolbeAccountRuntimeData(
        token_info=token_info,
        user_code=user_code,
        app_schema=app_schema,
        child_entry_ids=child_entry_ids,
    )

    # Store in hass.data for access by child entries
    hass.data[DOMAIN][entry.entry_id] = {
        "entry_type": ENTRY_TYPE_ACCOUNT,
        "token_info": token_info,
        "user_code": user_code,
        "app_schema": app_schema,
        "child_entry_ids": child_entry_ids,
    }

    _LOGGER.info(
        "SmartLife account entry setup complete: %s (children: %d)",
        entry.title,
        len(child_entry_ids),
    )

    # Account entries don't forward to any platforms
    # They only manage token information
    return True


async def _async_setup_device_entry(hass: HomeAssistant, entry: KKTKolbeConfigEntry) -> bool:
    """Set up a KKT Kolbe device entry.

    This handles both:
    - Standalone device entries (manual setup, IoT Platform)
    - Child device entries (linked to a SmartLife account parent)
    """
    from .const import SETUP_MODE_SMARTLIFE

    # Discovery is already started in async_setup, no need to start again

    # Check integration mode (V2 config flow adds this)
    setup_mode = entry.data.get("setup_mode", "manual")
    api_enabled = entry.data.get("api_enabled", False)

    # Determine integration_mode based on setup_mode if not explicitly set
    # SmartLife entries should NOT default to "manual" mode
    if setup_mode == SETUP_MODE_SMARTLIFE:
        integration_mode = entry.data.get("integration_mode", "smartlife")
    else:
        integration_mode = entry.data.get("integration_mode", "manual")

    # =========================================================================
    # SmartLife Parent-Child: Get tokens from parent entry if applicable
    # =========================================================================
    smartlife_token_info: dict[str, Any] | None = None
    parent_entry: ConfigEntry | None = None
    smartlife_client: Any = None  # TuyaSharingClient for cloud fallback

    if setup_mode == SETUP_MODE_SMARTLIFE:
        parent_entry_id = entry.data.get("parent_entry_id")

        if parent_entry_id:
            # Find the parent account entry
            parent_entry = hass.config_entries.async_get_entry(parent_entry_id)

            if parent_entry is None:
                _LOGGER.error(
                    "SmartLife parent entry %s not found for device %s. "
                    "The account may have been deleted.",
                    parent_entry_id[:8], entry.entry_id[:8]
                )
                # Create repair issue
                ir.async_create_issue(
                    hass,
                    DOMAIN,
                    f"parent_entry_missing_{entry.entry_id}",
                    is_fixable=False,
                    severity=ir.IssueSeverity.ERROR,
                    translation_key="parent_entry_missing",
                    translation_placeholders={
                        "device_name": entry.title,
                        "parent_id": parent_entry_id[:8],
                    },
                )
                raise ConfigEntryNotReady(
                    f"SmartLife parent entry {parent_entry_id[:8]} not found"
                )

            # Get token info from parent
            smartlife_token_info = parent_entry.data.get(CONF_SMARTLIFE_TOKEN_INFO)

            if not smartlife_token_info:
                _LOGGER.warning(
                    "SmartLife parent entry %s has no token info",
                    parent_entry_id[:8]
                )
            else:
                # Create TuyaSharingClient from stored tokens for cloud fallback
                try:
                    from .clients.tuya_sharing_client import TuyaSharingClient
                    smartlife_client = await TuyaSharingClient.async_from_stored_tokens(
                        hass, smartlife_token_info
                    )

                    # Register token persistence callback to update parent entry
                    # when tokens are refreshed by the SDK
                    async def update_parent_tokens(new_token_info: dict) -> None:
                        """Persist refreshed tokens to parent config entry."""
                        if parent_entry:
                            _LOGGER.info(
                                "Persisting refreshed SmartLife tokens to parent entry %s",
                                parent_entry.entry_id[:8]
                            )
                            new_data = dict(parent_entry.data)
                            new_data[CONF_SMARTLIFE_TOKEN_INFO] = new_token_info
                            hass.config_entries.async_update_entry(
                                parent_entry, data=new_data
                            )

                    smartlife_client.set_token_update_callback(update_parent_tokens)

                    _LOGGER.info(
                        "SmartLife client restored from stored tokens for device %s",
                        entry.entry_id[:8]
                    )
                except Exception as err:
                    _LOGGER.warning(
                        "Could not restore SmartLife client from tokens: %s. "
                        "Cloud fallback will not be available.",
                        err
                    )
                    smartlife_client = None

            _LOGGER.debug(
                "SmartLife device %s using tokens from parent %s",
                entry.entry_id[:8], parent_entry_id[:8]
            )
        else:
            _LOGGER.warning(
                "SmartLife device %s has no parent_entry_id - tokens may be outdated",
                entry.entry_id[:8]
            )

    device = None
    api_client = None
    coordinator = None

    # Initialize API client if enabled
    if api_enabled:
        from .api import TuyaCloudClient
        from .api_manager import GlobalAPIManager

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

            # Store credentials globally for reuse with other devices
            # This ensures credentials persist across restarts via config entry AND persistent storage
            api_manager = GlobalAPIManager(hass)
            has_creds = await api_manager.async_has_stored_credentials()
            if not has_creds:
                await api_manager.async_store_api_credentials(client_id, client_secret, endpoint)
                _LOGGER.info("API credentials restored from config entry to global persistent storage")

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
    # SmartLife mode uses HybridCoordinator with smartlife_client for cloud fallback
    if setup_mode == SETUP_MODE_SMARTLIFE and (device or smartlife_client):
        from .hybrid_coordinator import KKTKolbeHybridCoordinator

        coordinator = KKTKolbeHybridCoordinator(
            hass=hass,
            device_id=device_id,
            local_device=device,
            api_client=None,  # Not using IoT Platform API
            smartlife_client=smartlife_client,  # Cloud fallback via SmartLife
            prefer_local=True,  # Always prefer local for SmartLife
            entry=entry,
            device_type=entry.data.get("device_type"),
        )
        _LOGGER.info(
            "Hybrid coordinator initialized for SmartLife mode "
            "(local=%s, cloud_fallback=%s)",
            device is not None,
            smartlife_client is not None,
        )
    elif integration_mode in ["hybrid", "api_discovery"] and (device or api_client):
        from .hybrid_coordinator import KKTKolbeHybridCoordinator

        coordinator = KKTKolbeHybridCoordinator(
            hass=hass,
            device_id=device_id,
            local_device=device,
            api_client=api_client,
            smartlife_client=None,  # Not using SmartLife
            prefer_local=(integration_mode == "hybrid"),
            entry=entry,
            device_type=entry.data.get("device_type"),
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
    from .exceptions import KKTAuthenticationError
    from .exceptions import KKTConnectionError
    from .exceptions import KKTTimeoutError

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
        # Use timeout to prevent indefinite hang during setup
        FIRST_REFRESH_TIMEOUT = 60  # seconds
        # Allow initial refresh for modes with cloud fallback even if local fails
        if connection_successful or integration_mode in ["hybrid", "api_discovery", "smartlife"]:
            try:
                await asyncio.wait_for(
                    coordinator.async_config_entry_first_refresh(),
                    timeout=FIRST_REFRESH_TIMEOUT
                )
                _LOGGER.info("Initial data fetch successful")
            except TimeoutError:
                _LOGGER.warning(
                    f"Initial data fetch timed out after {FIRST_REFRESH_TIMEOUT}s, "
                    "coordinator will retry automatically"
                )
                # Don't raise - let coordinator handle retries
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

    # Determine device type and platforms
    # Priority: device_type (KNOWN_DEVICES key) > product_name (Tuya product ID)
    from .device_types import KNOWN_DEVICES
    from .device_types import get_device_info_by_product_name
    from .device_types import get_device_platforms

    device_type = entry.data.get("device_type", "auto")
    product_name = entry.data.get("product_name", "auto")
    effective_device_type = device_type  # Will be updated if we detect a better match

    # Try to get device_info from device_type first (it's often a KNOWN_DEVICES key)
    if device_type and device_type != "auto" and device_type in KNOWN_DEVICES:
        device_info = {
            "model_id": KNOWN_DEVICES[device_type].get("model_id", device_type),
            "category": KNOWN_DEVICES[device_type].get("category", "unknown"),
            "name": KNOWN_DEVICES[device_type].get("name", "KKT Kolbe Device"),
        }
        effective_device_type = device_type
        _LOGGER.info(f"Using device_type '{device_type}' from config: {device_info['name']}")
    elif product_name and product_name != "auto" and product_name != "unknown":
        # Fallback to product_name lookup
        device_info = get_device_info_by_product_name(product_name)
        # Try to find the KNOWN_DEVICES key for this product_name
        for key, info in KNOWN_DEVICES.items():
            if product_name in info.get("product_names", []):
                effective_device_type = key
                _LOGGER.info(f"Resolved product_name '{product_name}' to device_type '{key}'")
                break
        _LOGGER.info(f"Using product_name '{product_name}' for device lookup: {device_info['name']}")
    else:
        # Last resort - try device_id pattern matching
        from .config_flow import _detect_device_type_from_device_id
        detected_type, detected_product, detected_name = _detect_device_type_from_device_id(device_id)
        if detected_type != "auto":
            device_info = {
                "model_id": detected_type,
                "category": KNOWN_DEVICES.get(detected_type, {}).get("category", "unknown"),
                "name": detected_name,
            }
            effective_device_type = detected_type  # Use the detected type!
            product_name = detected_product  # Also update product_name
            _LOGGER.info(f"Detected device from device_id pattern: {detected_name} (device_type={detected_type})")
        else:
            device_info = get_device_info_by_product_name("default_hood")
            effective_device_type = "default_hood"
            _LOGGER.warning("Could not detect device type, using default_hood")

    platforms = get_device_platforms(device_info["category"])

    # Store runtime data using modern pattern (HA 2024.6+)
    entry.runtime_data = KKTKolbeRuntimeData(
        coordinator=coordinator,
        device=device,
        api_client=api_client,
        device_info=device_info,
        product_name=product_name,
        device_type=effective_device_type,
        integration_mode=integration_mode,
    )

    # Also store in hass.data for backward compatibility with services
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "device": device,
        "api_client": api_client,
        "config": entry.data,
        "device_info": device_info,
        "product_name": product_name,
        "device_type": effective_device_type,
        "integration_mode": integration_mode,
    }

    # Register device in device registry with version info
    from homeassistant.helpers import device_registry as dr

    from .const import VERSION as INTEGRATION_VERSION

    device_registry = dr.async_get(hass)

    # Determine software version - prefer detected protocol version
    sw_version = f"v{INTEGRATION_VERSION}"  # Default fallback
    if device and hasattr(device, 'version') and device.version and device.version != "auto":
        sw_version = f"Tuya Protocol {device.version}"
    elif entry.data.get("version") and entry.data.get("version") != "auto":
        sw_version = f"Tuya Protocol {entry.data.get('version')}"

    # Determine hardware version from device type
    hw_version = None
    if effective_device_type and effective_device_type in KNOWN_DEVICES:
        hw_version = KNOWN_DEVICES[effective_device_type].get("model_id", effective_device_type).upper()
    elif device_id:
        hw_version = device_id[:8].upper()

    device_entry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, device_id)},
        manufacturer="KKT Kolbe",
        name=device_info.get("name", "KKT Kolbe Device"),
        model=device_info.get("model_id", device_info.get("name", "Unknown")),
        sw_version=sw_version,
        hw_version=hw_version,
    )

    # Update existing device entry if sw/hw version was previously Unknown
    if device_entry.sw_version == "Unknown" or device_entry.hw_version == "Unknown":
        device_registry.async_update_device(
            device_entry.id,
            sw_version=sw_version,
            hw_version=hw_version,
        )
        _LOGGER.info(f"Updated device registry: sw_version={sw_version}, hw_version={hw_version}")

    # Load only the platforms needed for this specific device
    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    # Register listener for options updates - triggers reload when options change
    entry.async_on_unload(entry.add_update_listener(async_options_update_listener))

    # Set up services when the first device is added
    if len(hass.data[DOMAIN]) == 1:
        from .services import async_setup_services
        await async_setup_services(hass)
        _LOGGER.info("KKT Kolbe services initialized")

    return True

async def async_options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update - reload the integration when options change."""
    _LOGGER.info(f"Options updated for {entry.title}, reloading integration")
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Handles both account entries and device entries.
    """
    entry_type = entry.data.get("entry_type", ENTRY_TYPE_DEVICE)

    if entry_type == ENTRY_TYPE_ACCOUNT:
        return await _async_unload_account_entry(hass, entry)
    else:
        return await _async_unload_device_entry(hass, entry)


async def _async_unload_account_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a SmartLife account entry (Parent Entry).

    Note: Child device entries should be unloaded separately by Home Assistant
    when the user removes the account. This function only cleans up the account
    entry itself.
    """
    _LOGGER.info("Unloading SmartLife account entry: %s", entry.title)

    # Get child entry IDs before cleanup
    child_entry_ids: list[str] = []
    if hasattr(entry, 'runtime_data') and entry.runtime_data:
        child_entry_ids = entry.runtime_data.child_entry_ids
    else:
        # Fallback: scan for child entries
        for config_entry in hass.config_entries.async_entries(DOMAIN):
            if config_entry.data.get("parent_entry_id") == entry.entry_id:
                child_entry_ids.append(config_entry.entry_id)

    # Log warning if there are still child entries
    if child_entry_ids:
        _LOGGER.warning(
            "Unloading SmartLife account entry %s with %d child devices still linked. "
            "Child devices may need token refresh via a new account entry.",
            entry.entry_id,
            len(child_entry_ids),
        )

    # Remove from hass.data
    hass.data[DOMAIN].pop(entry.entry_id, None)

    # Account entries don't have platforms to unload
    _LOGGER.info("SmartLife account entry unloaded: %s", entry.title)
    return True


async def _async_unload_device_entry(hass: HomeAssistant, entry: KKTKolbeConfigEntry) -> bool:
    """Unload a KKT Kolbe device entry."""
    # Get the platforms that were loaded for this specific device
    from .device_types import get_device_platforms

    # Use runtime_data if available, fallback to entry.data
    if hasattr(entry, 'runtime_data') and entry.runtime_data:
        device_info = entry.runtime_data.device_info
    else:
        from .device_types import get_device_info_by_product_name
        product_name = entry.data.get("product_name", "unknown")
        device_info = get_device_info_by_product_name(product_name)

    platforms = get_device_platforms(device_info.get("category", "unknown"))

    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        # Remove from hass.data (backward compatibility)
        hass.data[DOMAIN].pop(entry.entry_id, None)

        # Count remaining device entries (exclude account entries)
        device_entries = [
            e for e in hass.data[DOMAIN].values()
            if isinstance(e, dict) and e.get("entry_type") != ENTRY_TYPE_ACCOUNT
        ]

        # Unload services when the last device is removed
        if not device_entries:
            from .services import async_unload_services
            await async_unload_services(hass)
            _LOGGER.info("KKT Kolbe services unloaded")

            from .discovery import async_stop_discovery
            await async_stop_discovery()

    return unload_ok
