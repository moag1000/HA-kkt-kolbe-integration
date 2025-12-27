"""Config flow for KKT Kolbe integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigEntry, ConfigFlowResult
from homeassistant.const import CONF_IP_ADDRESS, CONF_SCAN_INTERVAL, CONF_DEVICE_ID, CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .discovery import async_start_discovery, async_stop_discovery, get_discovered_devices
from .tuya_device import KKTKolbeTuyaDevice
from .api_manager import GlobalAPIManager
from .device_types import KNOWN_DEVICES, CATEGORY_HOOD, CATEGORY_COOKTOP
from .smart_discovery import SmartDiscovery, SmartDiscoveryResult, async_get_configured_device_ids

# Import helpers for validation and device detection
from .helpers import (
    is_valid_ip,
    is_valid_device_id,
    is_valid_local_key,
    validate_manual_input,
    validate_api_credentials,
    detect_device_type_from_api,
    detect_device_type_from_device_id,
    get_device_type_options,
    API_ENDPOINT_OPTIONS,
    DEFAULT_API_ENDPOINT,
)

# Import flow utilities and options flow
from .flows import (
    is_private_ip,
    test_device_connection,
    try_discover_local_ip,
    get_default_options,
    build_entry_title,
    get_friendly_device_type,
    KKTKolbeOptionsFlow,
)

_LOGGER = logging.getLogger(__name__)


# Legacy aliases for backwards compatibility with existing code
_is_private_ip = is_private_ip
_detect_device_type_from_api = detect_device_type_from_api
_detect_device_type_from_device_id = detect_device_type_from_device_id
_try_discover_local_ip = try_discover_local_ip
_get_device_type_options = get_device_type_options


# Configuration step schemas
STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required("setup_method", default="smart_discovery"): selector.selector({
        "select": {
            "options": [
                {"value": "smart_discovery", "label": "✨ Smart Discovery (Recommended - Auto + API)"},
                {"value": "discovery", "label": "🔍 Local Discovery (Network Scan Only)"},
                {"value": "manual", "label": "🔧 Manual Setup (IP + Local Key)"},
                {"value": "api_only", "label": "☁️ API-Only Setup (TinyTuya Cloud)"}
            ],
            "mode": "dropdown",
            "translation_key": "setup_method"
        }
    })
})


STEP_MANUAL_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_IP_ADDRESS): str,
    vol.Required("device_id"): str,
    vol.Required("device_type"): selector.selector({
        "select": {
            "options": _get_device_type_options(),
            "mode": "dropdown",
            "translation_key": "device_type"
        }
    })
})

STEP_API_ONLY_DATA_SCHEMA = vol.Schema({
    vol.Required("api_client_id"): selector.selector({
        "text": {}
    }),
    vol.Required("api_client_secret"): selector.selector({
        "text": {"type": "password"}
    }),
    vol.Required("api_endpoint", default="https://openapi.tuyaeu.com"): selector.selector({
        "select": {
            "options": [
                {"value": "https://openapi.tuyaeu.com", "label": "Europe (EU)"},
                {"value": "https://openapi.tuyaus.com", "label": "United States (US)"},
                {"value": "https://openapi.tuyacn.com", "label": "China (CN)"},
                {"value": "https://openapi.tuyain.com", "label": "India (IN)"}
            ],
            "mode": "dropdown"
        }
    })
})

def _get_device_selection_schema(discovered_devices: dict[str, dict[str, Any]]) -> vol.Schema:
    """Generate device selection schema based on discovered devices."""
    if not discovered_devices:
        return vol.Schema({
            vol.Optional("retry_discovery", default=False): bool,
            vol.Optional("use_manual_config", default=False): bool
        })

    device_options = []
    for device_id, device in discovered_devices.items():
        # Use friendly_type if available (from device detection), then device name, then fallback
        friendly_type = device.get("friendly_type")
        device_name = device.get("name", "")
        product_name = device.get("product_name", "Unknown Device")

        # Build display name: prefer friendly_type > device_name > product_name
        if friendly_type:
            display_name = friendly_type
        elif device_name and device_name != device_id and not device_name.startswith("KKT Device"):
            display_name = device_name
        else:
            # Last resort: use product_name, but truncate if it looks like a Tuya ID
            if len(product_name) > 12 and product_name.isalnum():
                display_name = f"KKT Device ({device_id[:8]})"
            else:
                display_name = product_name

        # Try both possible IP keys from discovery
        ip_address = device.get("ip") or device.get("host") or "Unknown IP"

        label = f"{display_name} ({ip_address})"
        device_options.append({"value": device_id, "label": label})

    return vol.Schema({
        vol.Required("selected_device"): selector.selector({
            "select": {
                "options": device_options,
                "mode": "dropdown"
            }
        }),
        vol.Optional("retry_discovery", default=False): bool,
        vol.Optional("use_manual_config", default=False): bool
    })

STEP_AUTHENTICATION_DATA_SCHEMA = vol.Schema({
    vol.Required("local_key"): str,
    vol.Optional("test_connection", default=True): bool,
    vol.Optional("back_to_previous", default=False): bool,
})

def get_settings_schema(device_type: str = None) -> vol.Schema:
    """Get settings schema based on device type."""
    schema_dict = {
        vol.Optional("update_interval", default=30): selector.selector({
            "number": {
                "min": 10, "max": 300, "step": 5,
                "unit_of_measurement": "seconds",
                "mode": "slider"
            }
        }),
        vol.Optional("enable_debug_logging", default=False): bool,
        vol.Optional("enable_advanced_entities", default=True): bool,  # Show all entities by default
    }

    # Additional options for induction cooktops
    if device_type in ["ind7705hc", "induction_cooktop"]:
        schema_dict[vol.Optional("zone_naming_scheme", default="zone")] = selector.selector({
            "select": {
                "options": [
                    {"value": "zone", "label": "Zone 1, Zone 2, ..."},
                    {"value": "numeric", "label": "1, 2, 3, ..."},
                    {"value": "custom", "label": "Custom Names"}
                ],
                "mode": "dropdown",
                "translation_key": "zone_naming"
            }
        })

    schema_dict[vol.Optional("back_to_authentication", default=False)] = bool

    return vol.Schema(schema_dict)

# Keep backwards compatibility
STEP_SETTINGS_DATA_SCHEMA = get_settings_schema()


class KKTKolbeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KKT Kolbe."""

    VERSION = 2
    CONNECTION_CLASS = "local_push"

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return KKTKolbeOptionsFlow()

    def __init__(self):
        """Initialize the config flow."""
        self._discovery_data: dict[str, dict[str, Any]] = {}
        self._device_info: dict[str, Any] = {}
        self._connection_method: str | None = None
        self._local_key: str | None = None
        self._advanced_settings: dict[str, Any] = {}
        self._smart_discovery_results: dict[str, SmartDiscoveryResult] = {}
        self._zeroconf_pending: bool = False

    async def async_step_zeroconf(
        self, discovery_info: dict[str, Any]
    ) -> FlowResult:
        """Handle zeroconf discovery of KKT Kolbe devices.

        Called automatically by Home Assistant when a matching mDNS service is found.
        """
        _LOGGER.info(f"Zeroconf discovery triggered: {discovery_info}")

        # Extract device information from zeroconf data
        host = discovery_info.get("host") or discovery_info.get("ip")
        device_id = discovery_info.get("device_id") or discovery_info.get("properties", {}).get("id")

        if not device_id:
            # Try to extract from name (Tuya devices often use device_id as service name)
            name = discovery_info.get("name", "")
            if name.startswith("bf") and len(name) >= 20:
                device_id = name.split(".")[0] if "." in name else name

        if not device_id:
            _LOGGER.debug("Zeroconf discovery: No device ID found, ignoring")
            return self.async_abort(reason="no_device_id")

        # Check if another flow is already in progress for this device
        # Zeroconf always yields to other flows to avoid blocking user-initiated setup
        for flow in self._async_in_progress():
            flow_context = flow.get("context", {})
            flow_unique_id = flow_context.get("unique_id")

            # If there's any flow for the same device, zeroconf should yield
            if flow_unique_id == device_id:
                _LOGGER.debug(
                    "Zeroconf: Another flow in progress for %s (source: %s), yielding",
                    device_id[:8], flow_context.get("source", "unknown")
                )
                return self.async_abort(reason="already_in_progress")

            # Also yield if there's a user-initiated flow doing discovery
            # (it might be scanning for the same device)
            if flow_context.get("source") == "user":
                _LOGGER.debug(
                    "Zeroconf: User flow in progress, yielding to avoid conflicts"
                )
                return self.async_abort(reason="already_in_progress")

        # Check if device is already configured
        await self.async_set_unique_id(device_id)
        # Don't raise error if unique_id already exists - just update IP and abort quietly
        self._abort_if_unique_id_configured(updates={CONF_IP_ADDRESS: host} if host else None)

        # Store discovery info for later steps
        self._device_info = {
            "device_id": device_id,
            "ip": host,
            "name": discovery_info.get("name", f"KKT Device {device_id[:8]}"),
            "discovered_via": "zeroconf",
            "friendly_type": "KKT Kolbe Device",  # Default, will be updated if API available
        }

        # Set initial title placeholder (will be updated after API enrichment)
        self.context["title_placeholders"] = {"name": "KKT Kolbe Device"}

        # Check if we have API credentials to auto-fetch local key and device details
        api_manager = GlobalAPIManager(self.hass)
        if await api_manager.async_has_stored_credentials():
            _LOGGER.info(f"Zeroconf: API credentials available, enriching device {device_id[:8]}")
            try:
                api_devices = await api_manager.get_kkt_devices_from_api()
                _LOGGER.info(f"Zeroconf: API returned {len(api_devices)} KKT devices")

                device_found = False
                for api_device in api_devices:
                    if api_device.get("id") == device_id:
                        device_found = True
                        # Found matching device in API - store ALL useful info
                        self._device_info["local_key"] = api_device.get("local_key")
                        self._device_info["product_id"] = api_device.get("product_id")
                        self._device_info["tuya_category"] = api_device.get("category")

                        # Use API name (user-configured name) or product_name
                        api_name = api_device.get("name") or api_device.get("product_name")
                        if api_name:
                            self._device_info["name"] = api_name

                        # Detect device type for proper entity setup
                        device_type, internal_product_name = _detect_device_type_from_api(api_device)
                        self._device_info["device_type"] = device_type
                        self._device_info["product_name"] = internal_product_name

                        # Create friendly display name based on detected type
                        from .device_types import KNOWN_DEVICES
                        if device_type in KNOWN_DEVICES:
                            device_info = KNOWN_DEVICES[device_type]
                            self._device_info["friendly_type"] = device_info.get("name", device_type)
                        else:
                            self._device_info["friendly_type"] = api_device.get("product_name", "KKT Device")

                        # Update title placeholder for discovery notification
                        self.context["title_placeholders"] = {"name": self._device_info["friendly_type"]}

                        has_local_key = bool(self._device_info.get("local_key"))
                        _LOGGER.info(f"Zeroconf: Enriched device {device_id[:8]}: "
                                    f"friendly_type={self._device_info['friendly_type']}, "
                                    f"local_key={'PRESENT' if has_local_key else 'MISSING'}, "
                                    f"product_id={api_device.get('product_id', 'N/A')}")
                        break

                if not device_found:
                    _LOGGER.warning(f"Zeroconf: Device {device_id[:8]} NOT FOUND in API response! "
                                   f"API returned IDs: {[d.get('id', '')[:8] for d in api_devices]}")

            except Exception as err:
                _LOGGER.warning(f"Zeroconf: Failed to enrich with API data: {err}")
        else:
            _LOGGER.warning(f"Zeroconf: NO API credentials stored! Device {device_id[:8]} cannot get local_key automatically. "
                           f"Trying device_id pattern matching for device type detection...")

            # Try to detect device type from device_id patterns (works without API)
            device_type, product_name, friendly_type = _detect_device_type_from_device_id(device_id)
            if device_type != "auto":
                self._device_info["device_type"] = device_type
                self._device_info["product_name"] = product_name
                self._device_info["friendly_type"] = friendly_type
                self.context["title_placeholders"] = {"name": friendly_type}
                _LOGGER.info(f"Zeroconf: Detected device type from device_id: {friendly_type}")

        # If we have all required info (including local_key), show confirmation
        if self._device_info.get("local_key") and self._device_info.get("ip"):
            return await self.async_step_zeroconf_confirm()

        # No local_key available - abort silently to avoid blocking Smart Discovery
        # The user can use Smart Discovery or manual setup instead
        _LOGGER.info(f"Zeroconf: Device {device_id[:8]} found but no local_key available. "
                    f"Use Smart Discovery or manual setup. Aborting zeroconf flow.")
        return self.async_abort(reason="no_local_key")

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm zeroconf discovered device with all data available (one-click setup)."""
        if user_input is not None:
            # User confirmed, create entry
            device_id = self._device_info["device_id"]
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            config_data = {
                CONF_IP_ADDRESS: self._device_info["ip"],
                "device_id": device_id,
                "local_key": self._device_info["local_key"],
                "product_name": self._device_info.get("product_name", "auto"),
                "product_id": self._device_info.get("product_id"),
                "device_type": self._device_info.get("device_type", "auto"),
                "integration_mode": "hybrid",
            }

            # Use friendly_type for better display name
            friendly_type = self._device_info.get("friendly_type", "")
            device_name = self._device_info.get("name", device_id[:8])

            # Create descriptive title: "HERMES Hood" or "IND7705HC Cooktop"
            if friendly_type:
                title = friendly_type
            else:
                title = f"KKT Kolbe {device_name}"

            # Default options with advanced entities enabled
            default_options = {
                "enable_advanced_entities": True,
                "enable_debug_logging": False,
            }

            return self.async_create_entry(
                title=title,
                data=config_data,
                options=default_options,
            )

        # Get friendly display info
        friendly_type = self._device_info.get("friendly_type", "Auto-detected")
        device_name = self._device_info.get("name", "Unknown")

        # Show confirmation form
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                "device_name": device_name,
                "device_id": self._device_info.get("device_id", "Unknown")[:8],
                "ip_address": self._device_info.get("ip", "Unknown"),
                "product_name": friendly_type,
            },
        )

    async def async_step_zeroconf_authenticate(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle zeroconf discovered device that needs local key or API config."""
        errors: dict[str, str] = {}

        api_manager = GlobalAPIManager(self.hass)
        has_api = await api_manager.async_has_stored_credentials()

        if user_input is not None:
            # Check if user wants to configure API instead
            if user_input.get("configure_api"):
                # Store that we came from zeroconf, so we return here after API config
                self._zeroconf_pending = True
                return await self.async_step_zeroconf_api_credentials()

            local_key = user_input.get("local_key", "").strip()

            if not local_key or len(local_key) < 16:
                errors["local_key"] = "invalid_local_key"
            else:
                # Test connection
                connection_valid = await self._test_device_connection(
                    self._device_info["ip"],
                    self._device_info["device_id"],
                    local_key
                )

                if connection_valid:
                    # Create entry
                    device_id = self._device_info["device_id"]
                    await self.async_set_unique_id(device_id)
                    self._abort_if_unique_id_configured()

                    config_data = {
                        CONF_IP_ADDRESS: self._device_info["ip"],
                        "device_id": device_id,
                        "local_key": local_key,
                        "product_name": self._device_info.get("product_name", "auto"),
                        "product_id": self._device_info.get("product_id"),
                        "device_type": self._device_info.get("device_type", "auto"),
                    }

                    # Use friendly_type for better display name
                    friendly_type = self._device_info.get("friendly_type", "")
                    device_name = self._device_info.get("name", device_id[:8])

                    if friendly_type:
                        title = friendly_type
                    else:
                        title = f"KKT Kolbe {device_name}"

                    # Default options with advanced entities enabled
                    default_options = {
                        "enable_advanced_entities": True,
                        "enable_debug_logging": False,
                    }

                    return self.async_create_entry(
                        title=title,
                        data=config_data,
                        options=default_options,
                    )
                else:
                    errors["local_key"] = "invalid_auth"

        # Get friendly display info
        friendly_type = self._device_info.get("friendly_type", "")
        device_name = self._device_info.get("name", "Unknown")
        display_name = device_name if device_name != "Unknown" else f"Device {self._device_info.get('device_id', '')[:8]}"
        if friendly_type:
            display_name = f"{display_name} ({friendly_type})"

        # Build schema - add API option if no credentials stored
        if has_api:
            # API is already configured, just show local key field
            schema = vol.Schema({
                vol.Required("local_key"): str,
            })
            api_hint = "API credentials are configured but local_key was not found for this device."
        else:
            # No API configured - offer both options
            schema = vol.Schema({
                vol.Optional("local_key"): str,
                vol.Optional("configure_api", default=False): bool,
            })
            api_hint = "You can enter the local key manually, or configure API credentials to fetch it automatically."

        return self.async_show_form(
            step_id="zeroconf_authenticate",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_name": display_name,
                "device_id": self._device_info.get("device_id", "Unknown")[:8],
                "ip_address": self._device_info.get("ip", "Unknown"),
                "api_hint": api_hint,
            },
        )

    async def async_step_zeroconf_api_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure API credentials from zeroconf discovery flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client_id = user_input.get("api_client_id", "").strip()
            client_secret = user_input.get("api_client_secret", "").strip()
            endpoint = user_input.get("api_endpoint", "https://openapi.tuyaeu.com")

            if not client_id or len(client_id) < 10:
                errors["api_client_id"] = "api_client_id_invalid"
            elif not client_secret or len(client_secret) < 20:
                errors["api_client_secret"] = "api_client_secret_invalid"
            else:
                # Test API connection
                from .api import TuyaCloudClient

                try:
                    api_client = TuyaCloudClient(
                        client_id=client_id,
                        client_secret=client_secret,
                        endpoint=endpoint,
                    )
                    async with api_client:
                        if await api_client.test_connection():
                            # Store credentials globally
                            api_manager = GlobalAPIManager(self.hass)
                            await api_manager.async_store_api_credentials(client_id, client_secret, endpoint)
                            _LOGGER.info("API credentials stored from zeroconf flow")

                            # Now try to fetch device info with the new API credentials
                            device_id = self._device_info.get("device_id")
                            api_devices = await api_manager.get_kkt_devices_from_api()

                            for api_device in api_devices:
                                if api_device.get("id") == device_id:
                                    # Found the device! Update info
                                    self._device_info["local_key"] = api_device.get("local_key")
                                    self._device_info["product_id"] = api_device.get("product_id")
                                    self._device_info["tuya_category"] = api_device.get("category")

                                    api_name = api_device.get("name") or api_device.get("product_name")
                                    if api_name:
                                        self._device_info["name"] = api_name

                                    # Detect device type
                                    device_type, internal_product_name = _detect_device_type_from_api(api_device)
                                    self._device_info["device_type"] = device_type
                                    self._device_info["product_name"] = internal_product_name

                                    from .device_types import KNOWN_DEVICES
                                    if device_type in KNOWN_DEVICES:
                                        self._device_info["friendly_type"] = KNOWN_DEVICES[device_type].get("name", device_type)
                                    else:
                                        self._device_info["friendly_type"] = api_device.get("product_name", "KKT Device")

                                    _LOGGER.info(f"Zeroconf API: Found device {device_id[:8]}, "
                                                f"local_key={'PRESENT' if self._device_info.get('local_key') else 'MISSING'}")
                                    break

                            # If we now have local_key, go to confirm step
                            if self._device_info.get("local_key"):
                                return await self.async_step_zeroconf_confirm()
                            else:
                                # API works but device not found or no local_key
                                _LOGGER.warning(f"API configured but device {device_id[:8]} not found or has no local_key")

                                # Still try to detect device type from device_id if not already detected
                                if not self._device_info.get("device_type") or self._device_info.get("device_type") == "auto":
                                    dev_type, prod_name, friendly = _detect_device_type_from_device_id(device_id)
                                    if dev_type != "auto":
                                        self._device_info["device_type"] = dev_type
                                        self._device_info["product_name"] = prod_name
                                        self._device_info["friendly_type"] = friendly
                                        _LOGGER.info(f"Detected device type from device_id: {friendly}")

                                return await self.async_step_zeroconf_authenticate()
                        else:
                            errors["base"] = "api_connection_failed"
                except Exception as err:
                    _LOGGER.error(f"API test failed: {err}")
                    errors["base"] = "api_connection_failed"

        # Show API configuration form
        return self.async_show_form(
            step_id="zeroconf_api_credentials",
            data_schema=vol.Schema({
                vol.Required("api_client_id"): str,
                vol.Required("api_client_secret"): str,
                vol.Required("api_endpoint", default="https://openapi.tuyaeu.com"): vol.In({
                    "https://openapi.tuyaeu.com": "Europe (EU)",
                    "https://openapi.tuyaus.com": "Americas (US)",
                    "https://openapi.tuyacn.com": "China (CN)",
                    "https://openapi.tuyain.com": "India (IN)",
                }),
            }),
            errors=errors,
            description_placeholders={
                "device_name": self._device_info.get("name", "Unknown"),
                "device_id": self._device_info.get("device_id", "Unknown")[:8],
            },
        )

    async def async_step_smart_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle smart discovery - combines local scan with API data."""
        errors: dict[str, str] = {}

        # Abort any conflicting zeroconf flows when user explicitly starts smart discovery
        # This prevents "flow already in progress" errors
        for flow in self._async_in_progress():
            flow_context = flow.get("context", {})
            # Only abort zeroconf-initiated flows, not user-initiated ones
            if flow_context.get("source") == "zeroconf" and flow["flow_id"] != self.flow_id:
                _LOGGER.debug(
                    "SmartDiscovery: Aborting conflicting zeroconf flow %s",
                    flow["flow_id"]
                )
                self.hass.config_entries.flow.async_abort(flow["flow_id"])

        # Get already configured device IDs
        configured_ids = await async_get_configured_device_ids(self.hass)

        if user_input is not None:
            if user_input.get("back_to_user"):
                return await self.async_step_user()

            if user_input.get("retry_discovery"):
                # Clear cached results and retry
                self._smart_discovery_results.clear()
                return await self.async_step_smart_discovery()

            selected_device_id = user_input.get("selected_device")
            if selected_device_id and selected_device_id in self._smart_discovery_results:
                result = self._smart_discovery_results[selected_device_id]

                # Abort any other flows for the same device before proceeding
                for flow in self._async_in_progress():
                    if (flow.get("context", {}).get("unique_id") == selected_device_id
                        and flow["flow_id"] != self.flow_id):
                        _LOGGER.debug(
                            "SmartDiscovery: Aborting conflicting flow %s for device %s",
                            flow["flow_id"], selected_device_id[:8]
                        )
                        self.hass.config_entries.flow.async_abort(flow["flow_id"])

                if result.ready_to_add and result.local_key:
                    # One-click setup - device has all required info including local_key
                    await self.async_set_unique_id(result.device_id)
                    self._abort_if_unique_id_configured()

                    # Detect device type - validate it's not "auto"
                    device_type = result.device_type
                    product_name = result.product_name or "auto"

                    # If device_type is still "auto", try to detect from device_id
                    if device_type in ("auto", None, ""):
                        detected_type, detected_product, detected_friendly = _detect_device_type_from_device_id(result.device_id)
                        device_type = detected_type
                        product_name = detected_product
                        _LOGGER.info(f"SmartDiscovery: Detected device_type '{device_type}' from device_id pattern")

                    config_data = {
                        CONF_IP_ADDRESS: result.ip_address,
                        "device_id": result.device_id,
                        "local_key": result.local_key,
                        "product_name": product_name,
                        "device_type": device_type,
                        "integration_mode": "hybrid" if result.api_enriched else "manual",
                    }

                    # Use friendly_type for better display name
                    title = result.friendly_type or f"KKT Kolbe {result.name}"

                    # Default options with advanced entities enabled
                    default_options = {
                        "enable_advanced_entities": True,
                        "enable_debug_logging": False,
                    }

                    return self.async_create_entry(
                        title=title,
                        data=config_data,
                        options=default_options,
                    )
                else:
                    # Device needs local key - go to authentication step
                    self._device_info = result.to_dict()
                    self._device_info["source"] = "smart_discovery"
                    return await self.async_step_authentication()

        # Run smart discovery if not already done
        if not self._smart_discovery_results:
            smart_discovery = SmartDiscovery(self.hass)
            self._smart_discovery_results = await smart_discovery.async_discover(
                local_timeout=8.0,
                enrich_with_api=True,
            )

        # Filter out already configured devices
        available_devices = {
            device_id: result
            for device_id, result in self._smart_discovery_results.items()
            if device_id not in configured_ids
        }

        if not available_devices:
            # No devices found or all already configured
            return self.async_show_form(
                step_id="smart_discovery",
                data_schema=vol.Schema({
                    vol.Optional("retry_discovery", default=False): bool,
                    vol.Optional("back_to_user", default=False): bool,
                }),
                errors={"base": "no_devices_found"} if not self._smart_discovery_results else {},
                description_placeholders={
                    "found_count": "0",
                    "ready_count": "0",
                    "discovery_status": "No new devices found" if self._smart_discovery_results else "No devices found",
                },
            )

        # Build device selection options
        device_options = []
        ready_count = 0
        for device_id, result in available_devices.items():
            if result.ready_to_add:
                ready_count += 1
            device_options.append({
                "value": device_id,
                "label": result.display_label,
            })

        # Sort: ready devices first
        device_options.sort(key=lambda x: (0 if "✅" in x["label"] else 1, x["label"]))

        schema = vol.Schema({
            vol.Required("selected_device"): selector.selector({
                "select": {
                    "options": device_options,
                    "mode": "dropdown",
                }
            }),
            vol.Optional("retry_discovery", default=False): bool,
            vol.Optional("back_to_user", default=False): bool,
        })

        return self.async_show_form(
            step_id="smart_discovery",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "found_count": str(len(available_devices)),
                "ready_count": str(ready_count),
                "discovery_status": f"Found {len(available_devices)} device(s), {ready_count} ready for one-click setup",
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any | None] = None
    ) -> FlowResult:
        """Handle the initial step - setup method selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            setup_method = user_input["setup_method"]

            if setup_method == "smart_discovery":
                return await self.async_step_smart_discovery()
            elif setup_method == "discovery":
                return await self.async_step_discovery()
            elif setup_method == "manual":
                return await self.async_step_manual()
            elif setup_method == "api_only":
                return await self.async_step_api_only()

        _LOGGER.debug("Showing user config form with setup methods")

        # Check if API credentials are available for smart discovery hint
        api_manager = GlobalAPIManager(self.hass)
        has_api = await api_manager.async_has_stored_credentials()

        # Build schema with smart discovery as recommended default
        user_schema = vol.Schema({
            vol.Required("setup_method", default="smart_discovery"): selector.selector({
                "select": {
                    "options": [
                        {"value": "smart_discovery", "label": "✨ Smart Discovery (Recommended - Auto + API)"},
                        {"value": "discovery", "label": "🔍 Local Discovery (Network Scan Only)"},
                        {"value": "manual", "label": "🔧 Manual Setup (IP + Local Key)"},
                        {"value": "api_only", "label": "☁️ API-Only Setup (TinyTuya Cloud)"}
                    ],
                    "mode": "dropdown",
                    "translation_key": "setup_method"
                }
            })
        })

        api_status = "API credentials configured - one-click setup available!" if has_api else "Configure API credentials for automatic local key retrieval"

        return self.async_show_form(
            step_id="user",
            data_schema=user_schema,
            errors=errors,
            description_placeholders={
                "setup_mode": "Choose how you want to set up your KKT Kolbe device",
                "api_status": api_status,
            }
        )

    async def async_step_reauth(self, user_input: dict[str, Any | None] = None) -> FlowResult:
        """Handle reauthentication for API credentials."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        if not self._reauth_entry:
            return self.async_abort(reason="reauth_failed")

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any | None] = None
    ) -> FlowResult:
        """Handle reauthentication confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if we're updating API credentials
            if "api_client_id" in user_input and "api_client_secret" in user_input:
                # Test API connection
                from .api import TuyaCloudClient
                from .api.api_exceptions import TuyaAuthenticationError

                try:
                    session = async_get_clientsession(self.hass)
                    client = TuyaCloudClient(
                        client_id=user_input["api_client_id"],
                        client_secret=user_input["api_client_secret"],
                        endpoint=user_input.get("api_endpoint", "https://openapi.tuyaeu.com"),
                        session=session
                    )

                    async with client:
                        if await client.test_connection():
                            # Update config entry with new API credentials
                            self.hass.config_entries.async_update_entry(
                                self._reauth_entry,
                                data={
                                    **self._reauth_entry.data,
                                    "api_client_id": user_input["api_client_id"],
                                    "api_client_secret": user_input["api_client_secret"],
                                    "api_endpoint": user_input.get("api_endpoint", "https://openapi.tuyaeu.com"),
                                    "api_enabled": True,
                                }
                            )
                            await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                            return self.async_abort(reason="reauth_successful")
                        else:
                            errors["base"] = "invalid_auth"

                except TuyaAuthenticationError:
                    errors["base"] = "invalid_auth"
                except Exception as exc:
                    _LOGGER.error("Unexpected error during reauthentication: %s", exc)
                    errors["base"] = "unknown"

            # Check if we're updating local key
            elif "local_key" in user_input:
                # Test local connection
                if await self._test_device_connection(
                    self._reauth_entry.data.get("ip_address"),
                    self._reauth_entry.data.get("device_id"),
                    user_input["local_key"]
                ):
                    # Update config entry with new local key
                    self.hass.config_entries.async_update_entry(
                        self._reauth_entry,
                        data={
                            **self._reauth_entry.data,
                            "local_key": user_input["local_key"],
                        }
                    )
                    await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")
                else:
                    errors["base"] = "cannot_connect"

        # Determine what needs reauthentication
        is_api_mode = self._reauth_entry.data.get("api_enabled", False)

        if is_api_mode:
            # API credentials reauth
            reauth_schema = vol.Schema({
                vol.Required("api_client_id", default=self._reauth_entry.data.get("api_client_id", "")): str,
                vol.Required("api_client_secret"): str,
                vol.Optional("api_endpoint", default=self._reauth_entry.data.get("api_endpoint", "https://openapi.tuyaeu.com")): str,
            })
            description_key = "reauth_api"
        else:
            # Local key reauth
            reauth_schema = vol.Schema({
                vol.Required("local_key"): str,
            })
            description_key = "reauth_local"

        placeholders = {
            "device_name": self._reauth_entry.title,
            "device_id": self._reauth_entry.data.get("device_id", "Unknown"),
        }

        # Add setup guide link for API reauth
        if is_api_mode:
            placeholders["setup_info"] = "📚 Setup Guide: https://github.com/moag1000/HA-kkt-kolbe-integration#-tuya-api-setup---vollstaendige-anleitung\n🔗 Tuya IoT Platform: https://iot.tuya.com"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=reauth_schema,
            errors=errors,
            description_placeholders=placeholders
        )

    async def async_step_discovery(
        self, user_input: dict[str, Any | None] = None
    ) -> FlowResult:
        """Handle device discovery step."""
        errors: dict[str, str] = {}

        # Abort any conflicting zeroconf flows when user explicitly starts discovery
        # This prevents "flow already in progress" errors
        for flow in self._async_in_progress():
            flow_context = flow.get("context", {})
            if flow_context.get("source") == "zeroconf" and flow["flow_id"] != self.flow_id:
                _LOGGER.debug(
                    "Discovery: Aborting conflicting zeroconf flow %s",
                    flow["flow_id"]
                )
                self.hass.config_entries.flow.async_abort(flow["flow_id"])

        # Initialize discovery if not done yet or retry requested
        # Only run discovery on first visit or explicit retry request
        should_run_discovery = (
            not self._discovery_data or
            (user_input and user_input.get("retry_discovery"))
        )

        if should_run_discovery:
            try:
                # Show progress to user
                self.hass.bus.async_fire("kkt_kolbe_discovery_started", {
                    "integration": DOMAIN,
                    "status": "scanning"
                })

                # Use global discovery instance (prevents UDP port conflicts)
                await async_start_discovery(self.hass)
                await asyncio.sleep(15)  # Discovery timeout
                discovered = get_discovered_devices()
                self._discovery_data = discovered

                self.hass.bus.async_fire("kkt_kolbe_discovery_completed", {
                    "integration": DOMAIN,
                    "found": len(discovered)
                })

            except Exception as exc:
                _LOGGER.error("Discovery failed: %s", exc)
                errors["base"] = "discovery_failed"

        if user_input is not None and not user_input.get("retry_discovery"):
            # Check if user wants to switch to manual configuration
            if user_input.get("use_manual_config"):
                return await self.async_step_manual()

            # Handle device selection
            if "selected_device" in user_input:
                device_id = user_input["selected_device"]
                if device_id in self._discovery_data:
                    self._device_info = self._discovery_data[device_id]
                    self._device_info["source"] = "discovery"

                    # Ensure device_type is detected from device_id patterns
                    if "device_type" not in self._device_info or self._device_info.get("device_type") in ("auto", None, ""):
                        detected_type, detected_product, detected_friendly = _detect_device_type_from_device_id(device_id)
                        self._device_info["device_type"] = detected_type
                        self._device_info["product_name"] = detected_product
                        self._device_info["friendly_type"] = detected_friendly
                        _LOGGER.info(f"Discovery: Detected device_type '{detected_type}' from device_id pattern")

                    return await self.async_step_authentication()
                else:
                    errors["base"] = "device_not_found"

        # Generate dynamic schema based on discovered devices
        data_schema = _get_device_selection_schema(self._discovery_data)

        description_placeholders = {
            "found_devices": len(self._discovery_data),
            "discovery_status": "completed" if self._discovery_data else "no_devices",
            "fallback_info": ""  # Always provide fallback_info, even if empty
        }

        if not self._discovery_data:
            description_placeholders["fallback_info"] = (
                "No KKT Kolbe devices found automatically. "
                "You can retry discovery or use manual configuration."
            )

        return self.async_show_form(
            step_id="discovery",
            data_schema=data_schema,
            errors=errors,
            description_placeholders=description_placeholders
        )

    async def async_step_manual(
        self, user_input: dict[str, Any | None] = None
    ) -> FlowResult:
        """Handle manual configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if user wants to go back to discovery
            if user_input.get("back_to_discovery"):
                return await self.async_step_discovery()

            # Validate input format (without local_key)
            validation_errors = await self._validate_manual_input(user_input)
            if not validation_errors:
                device_type = user_input["device_type"]

                # Check KNOWN_DEVICES first (from device_types.py)
                if device_type in KNOWN_DEVICES:
                    known_device = KNOWN_DEVICES[device_type]
                    device_name = known_device["name"]
                    device_category = known_device["category"]
                    is_cooktop = device_category == CATEGORY_COOKTOP
                    category = "Induction Cooktop" if is_cooktop else "Range Hood"
                    # Use first product_name for internal identification
                    product_name_internal = known_device["product_names"][0] if known_device.get("product_names") else device_type
                elif device_type == "default_hood":
                    # Default Hood from RealDeviceMappings
                    device_name = "Default Hood"
                    category = "Range Hood"
                    product_name_internal = "default_hood"
                else:
                    # Fallback for unknown device types
                    device_name = device_type.replace("_", " ").title()
                    category = "Unknown Device"
                    product_name_internal = device_type

                self._device_info = {
                    "ip": user_input[CONF_IP_ADDRESS],
                    "device_id": user_input["device_id"],
                    "name": f"KKT Kolbe {device_name} {user_input['device_id'][:8]}",
                    "product_name": product_name_internal,
                    "device_type": device_type,
                    "category": category,
                    "friendly_type": device_name,  # Use device name from KNOWN_DEVICES
                    "source": "manual",  # Track where we came from for back navigation
                }
                # Don't set local_key here - it will be asked in authentication step
                return await self.async_step_authentication()
            else:
                errors.update(validation_errors)

        return self.async_show_form(
            step_id="manual",
            data_schema=STEP_MANUAL_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "device_id_example": "bf735dfe2ad64fba7c1234",
                "ip_example": "192.168.1.100",
                "local_key_info": "Extract Local Key from Smart Life app using tuya-cli or tinytuya"
            }
        )

    async def async_step_api_only(
        self, user_input: dict[str, Any | None] = None
    ) -> FlowResult:
        """Handle API-only setup step."""
        errors: dict[str, str] = {}

        # Check if we have stored global API credentials
        api_manager = GlobalAPIManager(self.hass)

        # If we have stored credentials and user didn't specify to use different ones
        if await api_manager.async_has_stored_credentials() and user_input is None:
            return await self.async_step_api_choice()

        if user_input is not None:
            # Validate API credentials
            validation_errors = await self._validate_api_credentials(user_input)
            if not validation_errors:
                # Test API connection and discover devices
                client_id = user_input["api_client_id"]
                client_secret = user_input["api_client_secret"]
                endpoint = user_input["api_endpoint"]

                try:
                    from .api import TuyaCloudClient

                    api_client = TuyaCloudClient(
                        client_id=client_id,
                        client_secret=client_secret,
                        endpoint=endpoint
                    )

                    # Test connection and get device list with full details (local_key, product_id)
                    async with api_client:
                        if await api_client.test_connection():
                            devices = await api_client.get_device_list_with_details()

                            # Filter for KKT Kolbe devices
                            kkt_devices = []
                            for device in devices:
                                product_name = device.get("product_name", "").lower()
                                device_name = device.get("name", "").lower()
                                category = device.get("category", "").lower()

                                # Match by keywords or Tuya category
                                is_kkt = any(keyword in f"{product_name} {device_name}"
                                            for keyword in ["kkt", "kolbe", "range", "hood", "induction"])
                                is_hood_category = category in ["yyj", "dcl"]

                                if is_kkt or is_hood_category:
                                    kkt_devices.append(device)

                            if kkt_devices:
                                # Store API credentials globally for reuse
                                await api_manager.async_store_api_credentials(client_id, client_secret, endpoint)

                                # Store API info and show device selection
                                self._api_info = {
                                    "client_id": client_id,
                                    "client_secret": client_secret,
                                    "endpoint": endpoint
                                }
                                self._discovered_devices = {}
                                for device in kkt_devices:
                                    device_type, internal_product_name = _detect_device_type_from_api(device)

                                    # Get friendly_type from KNOWN_DEVICES
                                    from .device_types import KNOWN_DEVICES
                                    if device_type in KNOWN_DEVICES:
                                        friendly_type = KNOWN_DEVICES[device_type].get("name", device_type)
                                    else:
                                        friendly_type = device.get("product_name", "KKT Device")

                                    self._discovered_devices[device["id"]] = {
                                        "device_id": device["id"],
                                        "name": device.get("name", f"KKT Device {device['id']}"),
                                        "product_name": internal_product_name,
                                        "product_id": device.get("product_id"),
                                        "api_product_name": device.get("product_name", "Unknown Device"),
                                        "tuya_category": device.get("category", ""),
                                        "ip": device.get("ip"),
                                        "local_key": device.get("local_key"),
                                        "discovered_via": "API",
                                        "device_type": device_type,
                                        "friendly_type": friendly_type,
                                    }
                                return await self.async_step_api_device_selection()
                            else:
                                errors["base"] = "no_kkt_devices_found"
                        else:
                            errors["api_client_secret"] = "api_test_failed"
                except Exception as exc:
                    _LOGGER.error(f"API connection failed: {exc}")
                    errors["api_client_secret"] = "api_connection_failed"
            else:
                errors.update(validation_errors)

        return self.async_show_form(
            step_id="api_only",
            data_schema=STEP_API_ONLY_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "setup_info": "Configure TinyTuya Cloud API for device discovery\n\n📚 Setup Guide: https://github.com/moag1000/HA-kkt-kolbe-integration#-tuya-api-setup---vollstaendige-anleitung\n🔗 Tuya IoT Platform: https://iot.tuya.com"
            }
        )

    async def async_step_api_device_selection(
        self, user_input: dict[str, Any | None] = None
    ) -> FlowResult:
        """Handle device selection from API discovery."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input.get("retry_discovery"):
                return await self.async_step_api_only()

            selected_device_id = user_input["selected_device"]
            device_info = self._discovered_devices[selected_device_id]

            # Create config entry with API-only mode
            # Include IP and local_key if available from API for hybrid/local fallback
            config_data = {
                "integration_mode": "api_discovery",
                "api_enabled": True,
                "api_client_id": self._api_info["client_id"],
                "api_client_secret": self._api_info["client_secret"],
                "api_endpoint": self._api_info["endpoint"],
                CONF_DEVICE_ID: device_info["device_id"],
                "product_name": device_info["product_name"],
                "product_id": device_info.get("product_id"),
                "device_type": device_info["device_type"],
            }

            # Get IP address - prefer local IP over API's WAN IP
            api_ip = device_info.get("ip")
            final_ip = api_ip

            # Check if API returned a public IP (WAN) instead of local IP
            if api_ip and not _is_private_ip(api_ip):
                _LOGGER.warning(
                    f"API returned public IP {api_ip} for device {selected_device_id[:8]}. "
                    f"Trying to discover local IP via mDNS..."
                )
                # Try to find local IP via discovery
                local_ip = await _try_discover_local_ip(
                    self.hass,
                    selected_device_id,
                    timeout=6.0
                )
                if local_ip:
                    _LOGGER.info(
                        f"Using discovered local IP {local_ip} instead of API IP {api_ip}"
                    )
                    final_ip = local_ip
                else:
                    _LOGGER.warning(
                        f"Could not discover local IP for device {selected_device_id[:8]}. "
                        f"Local communication may not work. "
                        f"Consider using Manual Setup with the device's local IP."
                    )
                    # Still use the API IP as fallback (cloud communication might work)

            if final_ip:
                config_data[CONF_IP_ADDRESS] = final_ip

            # Add local_key if available from API (enables local communication)
            if device_info.get("local_key"):
                config_data["local_key"] = device_info["local_key"]

            # Use friendly_type as title, fallback to device name
            title = device_info.get("friendly_type") or device_info["name"]

            # Default options with advanced entities enabled
            default_options = {
                "enable_advanced_entities": True,
                "enable_debug_logging": False,
            }

            return self.async_create_entry(
                title=title,
                data=config_data,
                options=default_options,
            )

        # Show device selection form
        schema = _get_device_selection_schema(self._discovered_devices)
        return self.async_show_form(
            step_id="api_device_selection",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_count": len(self._discovered_devices)
            }
        )

    async def async_step_api_choice(
        self, user_input: dict[str, Any | None] = None
    ) -> FlowResult:
        """Handle choice between using stored API credentials or entering new ones."""
        api_manager = GlobalAPIManager(self.hass)

        if user_input is not None:
            if user_input.get("use_stored_api"):
                # Use stored credentials for device discovery
                try:
                    kkt_devices = await api_manager.get_kkt_devices_from_api()

                    if kkt_devices:
                        # Get stored credentials for later use
                        creds = api_manager.get_stored_api_credentials()
                        self._api_info = creds

                        self._discovered_devices = {}
                        for device in kkt_devices:
                            device_type, internal_product_name = _detect_device_type_from_api(device)

                            # Get friendly_type from KNOWN_DEVICES
                            from .device_types import KNOWN_DEVICES
                            friendly_type = KNOWN_DEVICES.get(device_type, {}).get("name")

                            self._discovered_devices[device["id"]] = {
                                "device_id": device["id"],
                                "name": device.get("name", f"KKT Device {device['id']}"),
                                "product_name": internal_product_name,
                                "api_product_name": device.get("product_name", "Unknown Device"),
                                "tuya_category": device.get("category", ""),
                                "ip": device.get("ip"),  # Include IP from API
                                "local_key": device.get("local_key"),  # Include local_key from API
                                "discovered_via": "API",
                                "device_type": device_type,
                                "friendly_type": friendly_type,
                            }
                        return await self.async_step_api_device_selection()
                    else:
                        return self.async_show_form(
                            step_id="api_choice",
                            data_schema=self._get_api_choice_schema(),
                            errors={"base": "no_kkt_devices_found"},
                            description_placeholders={
                                "stored_api_info": api_manager.get_api_info_summary()
                            }
                        )

                except Exception as exc:
                    _LOGGER.error(f"Failed to use stored API credentials: {exc}")
                    return self.async_show_form(
                        step_id="api_choice",
                        data_schema=self._get_api_choice_schema(),
                        errors={"base": "api_test_failed"},
                        description_placeholders={
                            "stored_api_info": api_manager.get_api_info_summary()
                        }
                    )
            else:
                # User wants to enter new credentials
                return await self.async_step_api_credentials()

        # Show choice form
        return self.async_show_form(
            step_id="api_choice",
            data_schema=self._get_api_choice_schema(),
            description_placeholders={
                "stored_api_info": api_manager.get_api_info_summary()
            }
        )

    def _get_api_choice_schema(self) -> vol.Schema:
        """Get schema for API choice step."""
        return vol.Schema({
            vol.Required("use_stored_api", default=True): bool,
            vol.Optional("manage_api", default=False): bool,
        })

    async def async_step_api_credentials(
        self, user_input: dict[str, Any | None] = None
    ) -> FlowResult:
        """Handle entering new API credentials."""
        # This is essentially the same as the original api_only step
        # but without the stored credentials check
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate API credentials
            validation_errors = await self._validate_api_credentials(user_input)
            if not validation_errors:
                # Test API connection and discover devices
                client_id = user_input["api_client_id"]
                client_secret = user_input["api_client_secret"]
                endpoint = user_input["api_endpoint"]

                try:
                    from .api import TuyaCloudClient

                    api_client = TuyaCloudClient(
                        client_id=client_id,
                        client_secret=client_secret,
                        endpoint=endpoint
                    )

                    # Test connection and get device list with full details (including local_key)
                    async with api_client:
                        if await api_client.test_connection():
                            devices = await api_client.get_device_list_with_details()

                            # Filter for KKT Kolbe devices
                            kkt_devices = []
                            for device in devices:
                                product_name = device.get("product_name", "").lower()
                                if any(keyword in product_name for keyword in ["kkt", "kolbe", "range", "hood", "induction"]):
                                    kkt_devices.append(device)

                            if kkt_devices:
                                # Store API credentials globally for reuse
                                api_manager = GlobalAPIManager(self.hass)
                                await api_manager.async_store_api_credentials(client_id, client_secret, endpoint)

                                # Store API info and show device selection
                                self._api_info = {
                                    "client_id": client_id,
                                    "client_secret": client_secret,
                                    "endpoint": endpoint
                                }
                                self._discovered_devices = {}
                                for device in kkt_devices:
                                    device_type, internal_product_name = _detect_device_type_from_api(device)

                                    # Get friendly_type from KNOWN_DEVICES
                                    from .device_types import KNOWN_DEVICES
                                    friendly_type = KNOWN_DEVICES.get(device_type, {}).get("name")

                                    self._discovered_devices[device["id"]] = {
                                        "device_id": device["id"],
                                        "name": device.get("name", f"KKT Device {device['id']}"),
                                        "product_name": internal_product_name,
                                        "api_product_name": device.get("product_name", "Unknown Device"),
                                        "tuya_category": device.get("category", ""),
                                        "ip": device.get("ip"),  # Include IP from API
                                        "local_key": device.get("local_key"),  # Include local_key from API
                                        "discovered_via": "API",
                                        "device_type": device_type,
                                        "friendly_type": friendly_type,
                                    }
                                return await self.async_step_api_device_selection()
                            else:
                                errors["base"] = "no_kkt_devices_found"
                        else:
                            errors["api_client_secret"] = "api_test_failed"
                except Exception as exc:
                    _LOGGER.error(f"API connection failed: {exc}")
                    errors["api_client_secret"] = "api_connection_failed"
            else:
                errors.update(validation_errors)

        return self.async_show_form(
            step_id="api_credentials",
            data_schema=STEP_API_ONLY_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "setup_info": "Enter new TinyTuya Cloud API credentials\n\n📚 Setup Guide: https://github.com/moag1000/HA-kkt-kolbe-integration#-tuya-api-setup---vollstaendige-anleitung\n🔗 Tuya IoT Platform: https://iot.tuya.com"
            }
        )

    async def async_step_authentication(
        self, user_input: dict[str, Any | None] = None
    ) -> FlowResult:
        """Handle authentication step - local key input and validation."""
        errors: dict[str, str] = {}

        # Check if API credentials are already stored
        api_manager = GlobalAPIManager(self.hass)
        has_api = await api_manager.async_has_stored_credentials()

        if user_input is not None:
            # Check if user wants to go back
            if user_input.get("back_to_previous"):
                # Go back to the previous step based on where we came from
                source = self._device_info.get("source", "discovery")
                if source == "manual":
                    return await self.async_step_manual()
                elif source == "smart_discovery":
                    return await self.async_step_smart_discovery()
                else:
                    return await self.async_step_discovery()

            # Check if user wants to configure API instead
            if user_input.get("configure_api"):
                # Store that we came from authentication, so we return here after API config
                self._auth_pending = True
                return await self.async_step_auth_api_credentials()

            local_key = user_input.get("local_key", "").strip()
            test_connection = user_input.get("test_connection", True)

            if not local_key:
                errors["local_key"] = "invalid_local_key"
            else:
                # Store local key
                self._local_key = local_key

                # Test connection if requested
                if test_connection:
                    connection_valid = await self._test_device_connection(
                        self._device_info["ip"],
                        self._device_info["device_id"],
                        local_key
                    )

                    if not connection_valid:
                        errors["base"] = "invalid_auth"
                    else:
                        # Connection successful, proceed to settings
                        return await self.async_step_settings()
                else:
                    # Skip connection test, proceed to settings
                    return await self.async_step_settings()

        # Pre-fill local key if we have it
        default_local_key = self._local_key or ""

        # Build schema - add API option if no credentials stored
        if has_api:
            # API is already configured, just show local key field
            auth_schema = vol.Schema({
                vol.Required("local_key", default=default_local_key): selector.selector({"text": {"type": "password"}}),
                vol.Optional("test_connection", default=True): bool,
                vol.Optional("back_to_previous", default=False): bool,
            })
        else:
            # No API configured - offer both options
            auth_schema = vol.Schema({
                vol.Optional("local_key", default=default_local_key): selector.selector({"text": {"type": "password"}}),
                vol.Optional("configure_api", default=False): bool,
                vol.Optional("test_connection", default=True): bool,
                vol.Optional("back_to_previous", default=False): bool,
            })

        return self.async_show_form(
            step_id="authentication",
            data_schema=auth_schema,
            errors=errors,
            description_placeholders={
                "device_name": self._device_info.get("name", "Unknown"),
                "device_id": self._device_info.get("device_id", "Unknown")[:8],
                "ip_address": self._device_info.get("ip", "Unknown")
            }
        )

    async def async_step_auth_api_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure API credentials from authentication flow."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client_id = user_input.get("api_client_id", "").strip()
            client_secret = user_input.get("api_client_secret", "").strip()
            endpoint = user_input.get("api_endpoint", "https://openapi.tuyaeu.com")

            if not client_id or len(client_id) < 10:
                errors["api_client_id"] = "api_client_id_invalid"
            elif not client_secret or len(client_secret) < 20:
                errors["api_client_secret"] = "api_client_secret_invalid"
            else:
                # Test API connection
                from .api import TuyaCloudClient

                api_client = TuyaCloudClient(
                    client_id=client_id,
                    client_secret=client_secret,
                    endpoint=endpoint,
                )

                try:
                    await api_client.test_connection()

                    # Store credentials globally
                    api_manager = GlobalAPIManager(self.hass)
                    await api_manager.async_store_api_credentials(client_id, client_secret, endpoint)

                    # Try to fetch local key for the discovered device
                    device_id = self._device_info.get("device_id")
                    if device_id:
                        try:
                            local_key = await api_client.get_local_key(device_id)
                            if local_key:
                                self._local_key = local_key
                                _LOGGER.info(f"Successfully fetched local_key via API for device {device_id[:8]}...")

                                # Also enrich device_type from API if currently "auto" or missing
                                current_device_type = self._device_info.get("device_type", "auto")
                                if current_device_type in ("auto", None, ""):
                                    try:
                                        api_devices = await api_client.get_device_list_with_details()
                                        for api_device in api_devices:
                                            if api_device.get("id") == device_id:
                                                detected_type, detected_product = _detect_device_type_from_api(api_device)
                                                if detected_type != "auto":
                                                    self._device_info["device_type"] = detected_type
                                                    self._device_info["product_name"] = detected_product
                                                    _LOGGER.info(f"Auth API: Enriched device_type to '{detected_type}' from API")
                                                break
                                    except Exception as enrich_err:
                                        _LOGGER.debug(f"Could not enrich device_type from API: {enrich_err}")

                                # Connection test with fetched key
                                connection_valid = await self._test_device_connection(
                                    self._device_info["ip"],
                                    device_id,
                                    local_key
                                )

                                if connection_valid:
                                    # Success! Proceed directly to settings
                                    return await self.async_step_settings()
                                else:
                                    # Key fetched but connection failed - go back to auth
                                    errors["base"] = "api_key_connection_failed"
                            else:
                                _LOGGER.warning(f"API returned no local_key for device {device_id[:8]}")
                                errors["base"] = "api_no_local_key"
                        except Exception as e:
                            _LOGGER.warning(f"Failed to fetch local_key: {e}")
                            errors["base"] = "api_fetch_key_failed"
                    else:
                        errors["base"] = "no_device_id"

                except Exception as e:
                    _LOGGER.error(f"API connection test failed: {e}")
                    if "1004" in str(e) or "sign" in str(e).lower():
                        errors["api_endpoint"] = "api_wrong_region"
                    elif "auth" in str(e).lower() or "401" in str(e) or "403" in str(e):
                        errors["api_client_secret"] = "api_auth_failed"
                    else:
                        errors["base"] = "api_connection_failed"

        # Show API credentials form
        return self.async_show_form(
            step_id="auth_api_credentials",
            data_schema=vol.Schema({
                vol.Required("api_client_id"): selector.selector({"text": {}}),
                vol.Required("api_client_secret"): selector.selector({"text": {"type": "password"}}),
                vol.Optional("api_endpoint", default="https://openapi.tuyaeu.com"): selector.selector({
                    "select": {
                        "options": [
                            {"value": "https://openapi.tuyaeu.com", "label": "Europe (EU)"},
                            {"value": "https://openapi.tuyaus.com", "label": "United States (US)"},
                            {"value": "https://openapi.tuyacn.com", "label": "China (CN)"},
                            {"value": "https://openapi.tuyain.com", "label": "India (IN)"}
                        ],
                        "mode": "dropdown"
                    }
                }),
            }),
            errors=errors,
            description_placeholders={
                "device_name": self._device_info.get("name", "Unknown"),
                "device_id": self._device_info.get("device_id", "Unknown")[:8],
                "setup_info": "Geben Sie Ihre TinyTuya Cloud API Zugangsdaten ein\n\n📚 Einrichtungsanleitung: https://github.com/moag1000/HA-kkt-kolbe-integration#-tuya-api-setup---vollstaendige-anleitung\n🔗 Tuya IoT Platform: https://iot.tuya.com"
            }
        )

    async def async_step_settings(
        self, user_input: dict[str, Any | None] = None
    ) -> FlowResult:
        """Handle advanced settings step."""
        if user_input is not None:
            # Check if user wants to go back
            if user_input.get("back_to_authentication"):
                return await self.async_step_authentication()

            # Ensure enable_advanced_entities defaults to True if not in input
            # (HA UI sometimes doesn't send unchecked bool fields)
            if "enable_advanced_entities" not in user_input:
                user_input["enable_advanced_entities"] = True

            self._advanced_settings = user_input
            return await self.async_step_confirmation()

        # Get device type for dynamic schema
        device_type = self._device_info.get("device_type", "")

        return self.async_show_form(
            step_id="settings",
            data_schema=get_settings_schema(device_type),
            description_placeholders={
                "device_name": self._device_info.get("name", "Unknown"),
                "recommended_interval": "30 seconds for real-time control"
            }
        )

    async def async_step_confirmation(
        self, user_input: dict[str, Any | None] = None
    ) -> FlowResult:
        """Handle confirmation and create config entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if user wants to go back to settings
            if user_input.get("back_to_settings"):
                return await self.async_step_settings()

            # Validate required fields before creating entry
            if not self._local_key:
                _LOGGER.error("Cannot create config entry: local_key is missing")
                errors["base"] = "missing_local_key"
                # Fall back to authentication to get local_key
                return await self.async_step_authentication()

            device_type = self._device_info.get("device_type", "auto")
            if device_type in ("auto", None, ""):
                # Try one last time to detect device_type from device_id
                device_id = self._device_info.get("device_id", "")
                detected_type, detected_product, detected_friendly = _detect_device_type_from_device_id(device_id)
                if detected_type != "auto":
                    self._device_info["device_type"] = detected_type
                    self._device_info["product_name"] = detected_product
                    self._device_info["friendly_type"] = detected_friendly
                    _LOGGER.info(f"Confirmation: Late detection of device_type '{detected_type}' from device_id")
                else:
                    _LOGGER.warning(f"Device type could not be detected, using 'auto' - some entities may not load correctly")

            # Set unique ID and check for duplicates (Bronze requirement: unique-config-entry)
            device_id = self._device_info["device_id"]
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            # Create the config entry with friendly type as title
            friendly_type = self._device_info.get("friendly_type")
            if friendly_type:
                title = friendly_type
            else:
                title = f"KKT Kolbe {self._device_info.get('name', 'Device')}"

            config_data = {
                CONF_IP_ADDRESS: self._device_info["ip"],
                "device_id": self._device_info["device_id"],
                "local_key": self._local_key,
                "product_name": self._device_info.get("product_name", "auto"),
                "device_type": self._device_info.get("device_type", "auto"),
                "product_id": self._device_info.get("product_id"),
            }

            # Add advanced settings as options
            options_data = {
                CONF_SCAN_INTERVAL: self._advanced_settings.get("update_interval", 30),
                "enable_debug_logging": self._advanced_settings.get("enable_debug_logging", False),
                "enable_advanced_entities": self._advanced_settings.get("enable_advanced_entities", True),
                "zone_naming_scheme": self._advanced_settings.get("zone_naming_scheme", "zone"),
            }

            return self.async_create_entry(
                title=title,
                data=config_data,
                options=options_data
            )

        # Show confirmation summary
        summary_info = {
            "device_name": self._device_info.get("name", "Unknown"),
            "device_id": self._device_info.get("device_id", "Unknown")[:8],
            "ip_address": self._device_info.get("ip", "Unknown"),
            "product_name": self._device_info.get("product_name", "Unknown"),
            "update_interval": self._advanced_settings.get("update_interval", 30),
            "debug_logging": "Enabled" if self._advanced_settings.get("enable_debug_logging") else "Disabled",
            "advanced_entities": "Enabled" if self._advanced_settings.get("enable_advanced_entities") else "Disabled",
        }

        return self.async_show_form(
            step_id="confirmation",
            data_schema=vol.Schema({
                vol.Optional("confirm", default=False): bool,
                vol.Optional("back_to_settings", default=False): bool
            }),
            description_placeholders=summary_info
        )

    async def _validate_manual_input(self, user_input: dict[str, Any]) -> dict[str, str]:
        """Validate manual input data (IP and device ID only)."""
        errors = {}

        # Validate IP address
        ip_address = user_input.get(CONF_IP_ADDRESS, "")
        if not self._is_valid_ip(ip_address):
            errors[CONF_IP_ADDRESS] = "invalid_ip"

        # Validate device ID
        device_id = user_input.get("device_id", "")
        if not self._is_valid_device_id(device_id):
            errors["device_id"] = "invalid_device_id"

        # Note: local_key validation is now done in authentication step

        return errors

    async def _validate_api_credentials(self, user_input: dict[str, Any]) -> dict[str, str]:
        """Validate API credentials format."""
        errors = {}

        client_id = user_input.get("api_client_id", "").strip()
        client_secret = user_input.get("api_client_secret", "").strip()

        if not client_id:
            errors["api_client_id"] = "api_client_id_required"
        elif len(client_id) < 10:
            errors["api_client_id"] = "api_client_id_invalid"

        if not client_secret:
            errors["api_client_secret"] = "api_client_secret_required"
        elif len(client_secret) < 20:
            errors["api_client_secret"] = "api_client_secret_invalid"

        return errors

    def _is_valid_ip(self, ip_address: str) -> bool:
        """Validate IP address format."""
        try:
            parts = ip_address.split(".")
            if len(parts) != 4:
                return False
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False
            return True
        except (ValueError, AttributeError):
            return False

    def _is_valid_device_id(self, device_id: str) -> bool:
        """Validate device ID format."""
        return len(device_id) >= 20 and device_id.isalnum()

    def _is_valid_local_key(self, local_key: str) -> bool:
        """Validate local key format."""
        return len(local_key) >= 16

    async def _test_device_connection(
        self, ip_address: str, device_id: str, local_key: str
    ) -> bool:
        """Test connection to device using enhanced testing method."""
        try:
            device = KKTKolbeTuyaDevice(device_id, ip_address, local_key)

            # Use the new async_test_connection method with built-in timeout protection
            return await device.async_test_connection()

        except Exception as exc:
            _LOGGER.debug("Connection test failed: %s", exc)
            return False

    # ================== RECONFIGURE FLOWS ==================

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        reconfigure_entry = self._get_reconfigure_entry()

        if not reconfigure_entry:
            return self.async_abort(reason="reconfigure_failed")

        # Store entry for use in subsequent steps
        self._reconfigure_entry = reconfigure_entry

        return await self.async_step_reconfigure_menu()

    async def async_step_reconfigure_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show reconfiguration menu with options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_option = user_input.get("reconfigure_option")

            if selected_option == "connection":
                return await self.async_step_reconfigure_connection()
            elif selected_option == "device_type":
                return await self.async_step_reconfigure_device_type()
            elif selected_option == "api":
                return await self.async_step_reconfigure_api()
            elif selected_option == "all":
                return await self.async_step_reconfigure_all()

        # Get current configuration summary
        entry = self._reconfigure_entry
        current_ip = entry.data.get(CONF_IP_ADDRESS, "Not configured")
        current_device_type = entry.data.get("device_type", "auto")
        api_enabled = entry.data.get("api_enabled", False)
        integration_mode = entry.data.get("integration_mode", "manual")

        # Get friendly device type name
        if current_device_type in KNOWN_DEVICES:
            device_type_display = KNOWN_DEVICES[current_device_type].get("name", current_device_type)
        else:
            device_type_display = current_device_type

        schema = vol.Schema({
            vol.Required("reconfigure_option"): selector.selector({
                "select": {
                    "options": [
                        {"value": "connection", "label": "🔌 Connection (IP & Local Key)"},
                        {"value": "device_type", "label": "📱 Device Type"},
                        {"value": "api", "label": "☁️ API Settings"},
                        {"value": "all", "label": "🔧 All Settings"},
                    ],
                    "mode": "list",
                }
            }),
        })

        return self.async_show_form(
            step_id="reconfigure_menu",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_name": entry.title,
                "current_ip": current_ip,
                "current_device_type": device_type_display,
                "api_status": "Enabled" if api_enabled else "Disabled",
                "integration_mode": integration_mode,
            },
        )

    async def async_step_reconfigure_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reconfigure connection settings (IP and Local Key)."""
        errors: dict[str, str] = {}
        entry = self._reconfigure_entry

        if user_input is not None:
            new_ip = user_input.get("ip_address", "").strip()
            new_local_key = user_input.get("local_key", "").strip()
            test_connection = user_input.get("test_connection", True)

            # Validate IP if provided
            if new_ip and not self._is_valid_ip(new_ip):
                errors["ip_address"] = "invalid_ip"

            # Validate local key if provided
            if new_local_key and not self._is_valid_local_key(new_local_key):
                errors["local_key"] = "invalid_local_key"

            if not errors:
                # Build updated data
                new_data = dict(entry.data)

                if new_ip:
                    new_data[CONF_IP_ADDRESS] = new_ip
                if new_local_key:
                    new_data["local_key"] = new_local_key
                    new_data[CONF_ACCESS_TOKEN] = new_local_key

                # Test connection if requested and we have all required info
                if test_connection and new_data.get(CONF_IP_ADDRESS) and new_data.get("local_key"):
                    connection_valid = await self._test_device_connection(
                        new_data[CONF_IP_ADDRESS],
                        new_data.get("device_id", entry.data.get("device_id")),
                        new_data["local_key"]
                    )
                    if not connection_valid:
                        errors["base"] = "cannot_connect"

                if not errors:
                    # Update the config entry
                    return self.async_update_reload_and_abort(
                        entry,
                        data=new_data,
                        reason="reconfigure_successful",
                    )

        # Current values
        current_ip = entry.data.get(CONF_IP_ADDRESS, "")

        schema = vol.Schema({
            vol.Optional("ip_address", default=current_ip): str,
            vol.Optional("local_key", default=""): selector.selector({
                "text": {"type": "password"}
            }),
            vol.Optional("test_connection", default=True): bool,
        })

        return self.async_show_form(
            step_id="reconfigure_connection",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_name": entry.title,
                "current_ip": current_ip,
                "local_key_hint": "Leave empty to keep current key",
            },
        )

    async def async_step_reconfigure_device_type(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reconfigure device type."""
        errors: dict[str, str] = {}
        entry = self._reconfigure_entry

        if user_input is not None:
            new_device_type = user_input.get("device_type")

            if new_device_type:
                new_data = dict(entry.data)
                new_data["device_type"] = new_device_type

                # Update product_name based on device type
                if new_device_type in KNOWN_DEVICES:
                    product_names = KNOWN_DEVICES[new_device_type].get("product_names", [])
                    if product_names:
                        new_data["product_name"] = product_names[0]

                # Update the config entry and reload
                return self.async_update_reload_and_abort(
                    entry,
                    data=new_data,
                    reason="reconfigure_successful",
                )

        current_device_type = entry.data.get("device_type", "auto")

        schema = vol.Schema({
            vol.Required("device_type", default=current_device_type): selector.selector({
                "select": {
                    "options": _get_device_type_options(),
                    "mode": "dropdown",
                }
            }),
        })

        return self.async_show_form(
            step_id="reconfigure_device_type",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_name": entry.title,
                "current_device_type": current_device_type,
            },
        )

    async def async_step_reconfigure_api(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reconfigure API settings."""
        errors: dict[str, str] = {}
        entry = self._reconfigure_entry

        if user_input is not None:
            api_enabled = user_input.get("api_enabled", False)

            new_data = dict(entry.data)
            new_data["api_enabled"] = api_enabled

            if api_enabled:
                client_id = user_input.get("api_client_id", "").strip()
                client_secret = user_input.get("api_client_secret", "").strip()
                endpoint = user_input.get("api_endpoint", "https://openapi.tuyaeu.com")

                # Validate credentials if enabling API
                if not client_id or len(client_id) < 10:
                    errors["api_client_id"] = "api_client_id_invalid"
                elif not client_secret or len(client_secret) < 20:
                    errors["api_client_secret"] = "api_client_secret_invalid"
                else:
                    # Test API connection
                    from .api import TuyaCloudClient

                    try:
                        api_client = TuyaCloudClient(
                            client_id=client_id,
                            client_secret=client_secret,
                            endpoint=endpoint,
                        )
                        async with api_client:
                            if await api_client.test_connection():
                                new_data["api_client_id"] = client_id
                                new_data["api_client_secret"] = client_secret
                                new_data["api_endpoint"] = endpoint
                                new_data["integration_mode"] = "hybrid"

                                # Store credentials globally
                                api_manager = GlobalAPIManager(self.hass)
                                await api_manager.async_store_api_credentials(client_id, client_secret, endpoint)
                            else:
                                errors["base"] = "api_connection_failed"
                    except Exception as err:
                        _LOGGER.error(f"API test failed: {err}")
                        errors["base"] = "api_connection_failed"
            else:
                # Disable API
                new_data["api_enabled"] = False
                new_data["integration_mode"] = "manual"

            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data=new_data,
                    reason="reconfigure_successful",
                )

        # Current values
        current_api_enabled = entry.data.get("api_enabled", False)
        current_client_id = entry.data.get("api_client_id", "")
        current_endpoint = entry.data.get("api_endpoint", "https://openapi.tuyaeu.com")

        schema = vol.Schema({
            vol.Required("api_enabled", default=current_api_enabled): bool,
            vol.Optional("api_client_id", default=current_client_id): str,
            vol.Optional("api_client_secret", default=""): selector.selector({
                "text": {"type": "password"}
            }),
            vol.Optional("api_endpoint", default=current_endpoint): selector.selector({
                "select": {
                    "options": [
                        {"value": "https://openapi.tuyaeu.com", "label": "Europe (EU)"},
                        {"value": "https://openapi.tuyaus.com", "label": "United States (US)"},
                        {"value": "https://openapi.tuyacn.com", "label": "China (CN)"},
                        {"value": "https://openapi.tuyain.com", "label": "India (IN)"},
                    ],
                    "mode": "dropdown",
                }
            }),
        })

        return self.async_show_form(
            step_id="reconfigure_api",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_name": entry.title,
                "api_status": "Enabled" if current_api_enabled else "Disabled",
                "secret_hint": "Leave empty to keep current secret",
            },
        )

    async def async_step_reconfigure_all(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reconfigure all settings at once."""
        errors: dict[str, str] = {}
        entry = self._reconfigure_entry

        if user_input is not None:
            new_ip = user_input.get("ip_address", "").strip()
            new_local_key = user_input.get("local_key", "").strip()
            new_device_type = user_input.get("device_type")
            api_enabled = user_input.get("api_enabled", False)
            test_connection = user_input.get("test_connection", True)

            # Validate IP if provided
            if new_ip and not self._is_valid_ip(new_ip):
                errors["ip_address"] = "invalid_ip"

            # Validate local key if provided
            if new_local_key and not self._is_valid_local_key(new_local_key):
                errors["local_key"] = "invalid_local_key"

            if not errors:
                new_data = dict(entry.data)

                # Update connection settings
                if new_ip:
                    new_data[CONF_IP_ADDRESS] = new_ip
                if new_local_key:
                    new_data["local_key"] = new_local_key
                    new_data[CONF_ACCESS_TOKEN] = new_local_key

                # Update device type
                if new_device_type:
                    new_data["device_type"] = new_device_type
                    if new_device_type in KNOWN_DEVICES:
                        product_names = KNOWN_DEVICES[new_device_type].get("product_names", [])
                        if product_names:
                            new_data["product_name"] = product_names[0]

                # Update API settings
                new_data["api_enabled"] = api_enabled
                if api_enabled:
                    client_id = user_input.get("api_client_id", "").strip()
                    client_secret = user_input.get("api_client_secret", "").strip()
                    endpoint = user_input.get("api_endpoint", "https://openapi.tuyaeu.com")

                    if client_id and client_secret:
                        from .api import TuyaCloudClient

                        try:
                            api_client = TuyaCloudClient(
                                client_id=client_id,
                                client_secret=client_secret,
                                endpoint=endpoint,
                            )
                            async with api_client:
                                if await api_client.test_connection():
                                    new_data["api_client_id"] = client_id
                                    new_data["api_client_secret"] = client_secret
                                    new_data["api_endpoint"] = endpoint
                                    new_data["integration_mode"] = "hybrid"
                                else:
                                    errors["base"] = "api_connection_failed"
                        except Exception:
                            errors["base"] = "api_connection_failed"
                else:
                    new_data["integration_mode"] = "manual"

                # Test local connection if requested
                if test_connection and not errors:
                    final_ip = new_data.get(CONF_IP_ADDRESS, entry.data.get(CONF_IP_ADDRESS))
                    final_key = new_data.get("local_key", entry.data.get("local_key"))
                    device_id = new_data.get("device_id", entry.data.get("device_id"))

                    if final_ip and final_key and device_id:
                        connection_valid = await self._test_device_connection(
                            final_ip, device_id, final_key
                        )
                        if not connection_valid:
                            errors["base"] = "cannot_connect"

                if not errors:
                    return self.async_update_reload_and_abort(
                        entry,
                        data=new_data,
                        reason="reconfigure_successful",
                    )

        # Current values
        current_ip = entry.data.get(CONF_IP_ADDRESS, "")
        current_device_type = entry.data.get("device_type", "auto")
        current_api_enabled = entry.data.get("api_enabled", False)
        current_client_id = entry.data.get("api_client_id", "")
        current_endpoint = entry.data.get("api_endpoint", "https://openapi.tuyaeu.com")

        schema = vol.Schema({
            vol.Optional("ip_address", default=current_ip): str,
            vol.Optional("local_key", default=""): selector.selector({
                "text": {"type": "password"}
            }),
            vol.Required("device_type", default=current_device_type): selector.selector({
                "select": {
                    "options": _get_device_type_options(),
                    "mode": "dropdown",
                }
            }),
            vol.Required("api_enabled", default=current_api_enabled): bool,
            vol.Optional("api_client_id", default=current_client_id): str,
            vol.Optional("api_client_secret", default=""): selector.selector({
                "text": {"type": "password"}
            }),
            vol.Optional("api_endpoint", default=current_endpoint): selector.selector({
                "select": {
                    "options": [
                        {"value": "https://openapi.tuyaeu.com", "label": "Europe (EU)"},
                        {"value": "https://openapi.tuyaus.com", "label": "United States (US)"},
                        {"value": "https://openapi.tuyacn.com", "label": "China (CN)"},
                        {"value": "https://openapi.tuyain.com", "label": "India (IN)"},
                    ],
                    "mode": "dropdown",
                }
            }),
            vol.Optional("test_connection", default=True): bool,
        })

        return self.async_show_form(
            step_id="reconfigure_all",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_name": entry.title,
                "local_key_hint": "Leave empty to keep current key",
                "secret_hint": "Leave empty to keep current secret",
            },
        )


# KKTKolbeOptionsFlow is imported from .flows module at the top of this file
# See: custom_components/kkt_kolbe/flows/options.py