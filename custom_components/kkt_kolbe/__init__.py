"""KKT Kolbe Dunstabzugshaube Integration for Home Assistant."""

from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import ConfigEntryNotReady
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import CONF_SMARTLIFE_TOKEN_INFO
from .const import DOMAIN
from .const import ENTRY_TYPE_ACCOUNT
from .const import ENTRY_TYPE_DEVICE
from .const import PLATFORMS  # noqa: F401
from .data import KKTKolbeAccountConfigEntry  # noqa: F401
from .data import KKTKolbeAccountRuntimeData
from .data import KKTKolbeConfigEntry
from .data import KKTKolbeRuntimeData

# This integration is config entry only - no YAML configuration
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
# Heavy imports moved to lazy loading to prevent blocking the event loop

_LOGGER = logging.getLogger(__name__)


# Runtime data types are defined in data.py (imported above)
# Re-exported here for backward compatibility: KKTKolbeConfigEntry, KKTKolbeRuntimeData


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


async def _async_setup_account_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
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
        _LOGGER.warning("SmartLife account entry %s has no token info stored", entry.entry_id)

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
        "_previous_options": dict(entry.options),  # For update listener comparison
    }

    _LOGGER.info(
        "SmartLife account entry setup complete: %s (children: %d)",
        entry.title,
        len(child_entry_ids),
    )

    # Account entries don't forward to any platforms
    # They only manage token information
    return True


async def _async_background_connect(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: Any,
    device: Any | None,
    api_client: Any | None,
) -> None:
    """Background task: connect device and perform first data refresh.

    Runs after async_setup_entry returns, so HA startup is not blocked.
    Handles auth errors via reauth flow and repair issues.
    """
    from .exceptions import KKTAuthenticationError
    from .exceptions import KKTConnectionError
    from .exceptions import KKTTimeoutError

    # Step 1: Try connecting local device
    if device:
        try:
            await device.async_connect()
            _LOGGER.info("Background connect succeeded for %s", entry.title)
        except KKTAuthenticationError as e:
            _LOGGER.error(
                "Authentication failed for %s: %s. Local key may be incorrect or expired.",
                entry.title,
                e,
            )
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
            entry.async_start_reauth(hass)
            # Still mark connect done so coordinator can try cloud fallback
        except (KKTConnectionError, KKTTimeoutError) as e:
            _LOGGER.debug(
                "Background connect failed for %s: %s (coordinator will retry)",
                entry.title,
                e,
            )
        except Exception as e:
            _LOGGER.warning("Unexpected error during background connect for %s: %s", entry.title, e)

    # Step 2: Test API connection
    if api_client:
        try:
            await api_client.test_connection()
            _LOGGER.info("API connection verified for %s", entry.title)
        except Exception as e:
            _LOGGER.debug("API connection test failed for %s: %s", entry.title, e)

    # Step 3: Mark initial connect done (coordinator can now do normal updates)
    if hasattr(coordinator, "mark_initial_connect_done"):
        coordinator.mark_initial_connect_done()

    # Step 4: Trigger first data refresh
    await coordinator.async_refresh()


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
    smartlife_extended_info: dict[str, Any] = {}  # Extended device info from SmartLife

    if setup_mode == SETUP_MODE_SMARTLIFE:
        parent_entry_id = entry.data.get("parent_entry_id")

        if parent_entry_id:
            # Find the parent account entry
            parent_entry = hass.config_entries.async_get_entry(parent_entry_id)

            if parent_entry is None:
                _LOGGER.error(
                    "SmartLife parent entry %s not found for device %s. The account may have been deleted.",
                    parent_entry_id[:8],
                    entry.entry_id[:8],
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
                raise ConfigEntryNotReady(f"SmartLife parent entry {parent_entry_id[:8]} not found")

            # Get token info from parent
            smartlife_token_info = parent_entry.data.get(CONF_SMARTLIFE_TOKEN_INFO)

            if not smartlife_token_info:
                _LOGGER.warning("SmartLife parent entry %s has no token info", parent_entry_id[:8])
            else:
                # Create TuyaSharingClient from stored tokens for cloud fallback
                try:
                    from .clients.tuya_sharing_client import TuyaSharingClient

                    smartlife_client = await TuyaSharingClient.async_from_stored_tokens(hass, smartlife_token_info)

                    # Register token persistence callback to update parent entry
                    # when tokens are refreshed by the SDK
                    async def update_parent_tokens(new_token_info: dict) -> None:
                        """Persist refreshed tokens to parent config entry."""
                        if parent_entry:
                            _LOGGER.info(
                                "Persisting refreshed SmartLife tokens to parent entry %s", parent_entry.entry_id[:8]
                            )
                            new_data = dict(parent_entry.data)
                            new_data[CONF_SMARTLIFE_TOKEN_INFO] = new_token_info
                            hass.config_entries.async_update_entry(parent_entry, data=new_data)

                    smartlife_client.set_token_update_callback(update_parent_tokens)

                    _LOGGER.info("SmartLife client restored from stored tokens for device %s", entry.entry_id[:8])
                except Exception as err:
                    _LOGGER.warning(
                        "Could not restore SmartLife client from tokens: %s. Cloud fallback will not be available.", err
                    )
                    smartlife_client = None

            _LOGGER.debug("SmartLife device %s using tokens from parent %s", entry.entry_id[:8], parent_entry_id[:8])
        else:
            _LOGGER.warning("SmartLife device %s has no parent_entry_id - tokens may be outdated", entry.entry_id[:8])

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

    # For SmartLife mode: Sync local_key from SmartLife API (may have been rotated)
    # Note: We already fetched devices during smartlife_client setup, so use cached data
    if setup_mode == SETUP_MODE_SMARTLIFE and smartlife_client and device_id:
        try:
            # Get fresh device data including current local_key from SmartLife
            # The client should already have device cache from previous calls
            _LOGGER.debug("Syncing local_key from SmartLife for device %s", device_id[:8])
            smartlife_devices = await smartlife_client.async_get_devices()
            _LOGGER.debug("Got %d devices from SmartLife", len(smartlife_devices))

            for sl_device in smartlife_devices:
                if sl_device.device_id == device_id:
                    fresh_local_key = sl_device.local_key
                    fresh_ip = sl_device.ip
                    _LOGGER.debug(
                        "Found device %s in SmartLife: local_key=%s, ip=%s",
                        device_id[:8],
                        "PRESENT" if fresh_local_key else "MISSING",
                        fresh_ip,
                    )

                    # Check if local_key has changed
                    if fresh_local_key and fresh_local_key != local_key:
                        _LOGGER.warning(
                            "SmartLife local_key differs from stored key for device %s. "
                            "Updating config entry with fresh key (stored length: %d, fresh length: %d)",
                            device_id[:8],
                            len(local_key) if local_key else 0,
                            len(fresh_local_key),
                        )
                        local_key = fresh_local_key

                        # Update config entry with fresh local_key
                        new_data = dict(entry.data)
                        new_data["local_key"] = fresh_local_key
                        new_data[CONF_ACCESS_TOKEN] = fresh_local_key
                        hass.config_entries.async_update_entry(entry, data=new_data)
                    elif fresh_local_key:
                        # Log masked key comparison for debugging
                        stored_masked = (
                            f"{local_key[:3]}...{local_key[-3:]}" if local_key and len(local_key) >= 6 else "???"
                        )
                        fresh_masked = (
                            f"{fresh_local_key[:3]}...{fresh_local_key[-3:]}" if len(fresh_local_key) >= 6 else "???"
                        )
                        _LOGGER.debug(
                            "SmartLife local_key matches stored key for device %s (length: %d, stored: %s, fresh: %s)",
                            device_id[:8],
                            len(fresh_local_key),
                            stored_masked,
                            fresh_masked,
                        )

                    # Also update IP if changed - but ONLY if it's a private/local IP!
                    # SmartLife often returns the public/external IP which won't work for LAN
                    if fresh_ip and fresh_ip != ip_address:
                        # Check if fresh_ip is a private IP (safe for local communication)
                        import ipaddress

                        try:
                            ip_obj = ipaddress.ip_address(fresh_ip)
                            if ip_obj.is_private:
                                _LOGGER.info(
                                    "SmartLife local IP for device %s: %s -> %s", device_id[:8], ip_address, fresh_ip
                                )
                                ip_address = fresh_ip
                                new_data = dict(entry.data)
                                new_data[CONF_IP_ADDRESS] = fresh_ip
                                new_data["ip_address"] = fresh_ip
                                hass.config_entries.async_update_entry(entry, data=new_data)
                            else:
                                _LOGGER.debug(
                                    "SmartLife returned public IP %s for device %s - ignoring "
                                    "(using stored local IP %s instead)",
                                    fresh_ip,
                                    device_id[:8],
                                    ip_address,
                                )
                        except ValueError:
                            _LOGGER.debug("Invalid IP from SmartLife: %s", fresh_ip)

                    # Store extended device info in local variable for later use
                    smartlife_extended_info = {
                        "uuid": sl_device.uuid,
                        "create_time": sl_device.create_time,
                        "active_time": sl_device.active_time,
                        "update_time": sl_device.update_time,
                        "time_zone": sl_device.time_zone,
                        "icon": sl_device.icon,
                    }
                    _LOGGER.debug(
                        "Retrieved extended SmartLife info for %s: uuid=%s, icon=%s",
                        device_id[:8],
                        sl_device.uuid,
                        sl_device.icon,
                    )

                    break
            else:
                _LOGGER.warning("Device %s not found in SmartLife device list. Using stored key.", device_id[:8])
        except Exception as err:
            _LOGGER.warning(
                "Could not sync local_key from SmartLife for device %s: %s (%s). Using stored key.",
                device_id[:8] if device_id else "unknown",
                type(err).__name__,
                err,
            )

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
            "Hybrid coordinator initialized for SmartLife mode (local=%s, cloud_fallback=%s)",
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

    # Schedule background connection (non-blocking HA startup)
    # Connection + first data refresh happens in a background task so that
    # HA startup is not delayed by unreachable devices.
    entry.async_create_background_task(
        hass,
        _async_background_connect(hass, entry, coordinator, device, api_client),
        name=f"kkt_kolbe_{entry.entry_id}_connect",
    )

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
        "smartlife_extended_info": smartlife_extended_info,
        "_previous_options": dict(entry.options),  # For update listener comparison
    }

    # Register device in device registry with version info
    from homeassistant.helpers import device_registry as dr

    from .const import VERSION as INTEGRATION_VERSION

    device_registry = dr.async_get(hass)

    # Use extended SmartLife info from earlier retrieval
    extended_info = smartlife_extended_info

    # Determine software version from Tuya protocol or integration version
    sw_version = f"v{INTEGRATION_VERSION}"  # Default fallback
    if device and hasattr(device, "version") and device.version and device.version != "auto":
        sw_version = f"Tuya Protocol {device.version}"
    elif entry.data.get("version") and entry.data.get("version") != "auto":
        sw_version = f"Tuya Protocol {entry.data.get('version')}"

    # Determine hardware version from device type
    hw_version = None
    if effective_device_type and effective_device_type in KNOWN_DEVICES:
        hw_version = KNOWN_DEVICES[effective_device_type].get("model_id", effective_device_type).upper()
    elif device_id:
        hw_version = device_id[:8].upper()

    # Get serial number from SmartLife UUID if available
    serial_number = extended_info.get("uuid")

    # Build configuration URL
    config_url = None
    if ip_address:
        config_url = f"http://{ip_address}"

    device_entry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, device_id)},
        manufacturer="KKT Kolbe",
        name=device_info.get("name", "KKT Kolbe Device"),
        model=device_info.get("model_id", device_info.get("name", "Unknown")),
        sw_version=sw_version,
        hw_version=hw_version,
        serial_number=serial_number,
        configuration_url=config_url,
    )

    # Update existing device entry with extended info
    update_kwargs = {}
    if device_entry.sw_version == "Unknown" or device_entry.sw_version != sw_version:
        update_kwargs["sw_version"] = sw_version
    if device_entry.hw_version == "Unknown" or device_entry.hw_version != hw_version:
        update_kwargs["hw_version"] = hw_version
    if serial_number and device_entry.serial_number != serial_number:
        update_kwargs["serial_number"] = serial_number
    if config_url and device_entry.configuration_url != config_url:
        update_kwargs["configuration_url"] = config_url

    if update_kwargs:
        device_registry.async_update_device(device_entry.id, **update_kwargs)
        _LOGGER.info("Updated device registry for %s: %s", device_id[:8], update_kwargs)

    # Download device icon from SmartLife or stored URL
    icon_url = extended_info.get("icon") or entry.data.get("icon_url")
    if icon_url:
        from .helpers.icon_downloader import download_icon

        try:
            local_icon_path = await download_icon(hass, device_id, icon_url)
            if local_icon_path:
                _LOGGER.info("Device icon downloaded for %s: %s", device_id[:8], local_icon_path)
        except Exception as err:
            _LOGGER.warning("Failed to download device icon: %s", err)

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
    """Handle options update - reload the integration when options change.

    Note: This listener is called for ANY config entry update (data or options).
    We only want to reload when OPTIONS change, not when data changes (like IP updates).
    """
    # Get the stored previous options to compare
    domain_data = hass.data.get(DOMAIN, {})
    entry_data = domain_data.get(entry.entry_id, {})
    previous_options = entry_data.get("_previous_options")
    current_options = dict(entry.options)

    # Store current options for next comparison
    if entry.entry_id in domain_data and isinstance(domain_data[entry.entry_id], dict):
        domain_data[entry.entry_id]["_previous_options"] = current_options

    # Only reload if options actually changed
    if previous_options is not None and previous_options != current_options:
        _LOGGER.info(f"Options updated for {entry.title}, reloading integration")
        await hass.config_entries.async_reload(entry.entry_id)
    elif previous_options is None:
        # First call after setup - just store options, don't reload
        _LOGGER.debug(f"Options listener initialized for {entry.title}")
    else:
        # Data changed but options are the same - no reload needed
        _LOGGER.debug(f"Config entry data updated for {entry.title} (no reload needed)")


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
    if hasattr(entry, "runtime_data") and entry.runtime_data:
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
    import asyncio

    from .device_types import get_device_platforms

    # Use runtime_data if available, fallback to entry.data
    if hasattr(entry, "runtime_data") and entry.runtime_data:
        device_info = entry.runtime_data.device_info
    else:
        from .device_types import get_device_info_by_product_name

        product_name = entry.data.get("product_name", "unknown")
        device_info = get_device_info_by_product_name(product_name)

    platforms = get_device_platforms(device_info.get("category", "unknown"))

    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        # Shutdown coordinator with timeout to prevent hanging during HA shutdown
        _SHUTDOWN_TIMEOUT = 30
        if hasattr(entry, "runtime_data") and entry.runtime_data:
            try:
                async with asyncio.timeout(_SHUTDOWN_TIMEOUT):
                    await entry.runtime_data.coordinator.async_shutdown()
            except TimeoutError:
                _LOGGER.warning(
                    "Coordinator shutdown timed out after %ds for %s",
                    _SHUTDOWN_TIMEOUT,
                    entry.title,
                )

        # Remove from hass.data (backward compatibility)
        hass.data[DOMAIN].pop(entry.entry_id, None)

        # Count remaining device entries (exclude account entries)
        device_entries = [
            e for e in hass.data[DOMAIN].values() if isinstance(e, dict) and e.get("entry_type") != ENTRY_TYPE_ACCOUNT
        ]

        # Unload services when the last device is removed
        if not device_entries:
            from .services import async_unload_services

            await async_unload_services(hass)
            _LOGGER.info("KKT Kolbe services unloaded")

            from .discovery import async_stop_discovery

            await async_stop_discovery()

    return unload_ok
