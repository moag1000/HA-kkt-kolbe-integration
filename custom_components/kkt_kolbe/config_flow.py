"""Config flow for KKT Kolbe integration."""
from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, CONF_SCAN_INTERVAL, CONF_DEVICE_ID, CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN
from .discovery import async_start_discovery, async_stop_discovery, get_discovered_devices
from .tuya_device import KKTKolbeTuyaDevice
from .api_manager import GlobalAPIManager
from .api.real_device_mappings import RealDeviceMappings
from .device_types import KNOWN_DEVICES, CATEGORY_HOOD, CATEGORY_COOKTOP
from .smart_discovery import SmartDiscovery, SmartDiscoveryResult, async_get_configured_device_ids

_LOGGER = logging.getLogger(__name__)


def _is_private_ip(ip_str: str | None) -> bool:
    """Check if an IP address is a private/local network address.

    Returns True for:
    - 10.0.0.0/8 (Class A private)
    - 172.16.0.0/12 (Class B private)
    - 192.168.0.0/16 (Class C private)
    - 169.254.0.0/16 (Link-local)

    Returns False for public IPs or invalid IPs.
    """
    if not ip_str:
        return False
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_link_local
    except ValueError:
        return False


def _detect_device_type_from_api(device: dict[str, Any]) -> tuple[str, str]:
    """Detect device type from Tuya API response.

    Args:
        device: Device dict from Tuya API

    Returns:
        Tuple of (device_type, internal_product_name)
        - device_type: Internal device key for UI display
        - internal_product_name: Product name for entity lookup in KNOWN_DEVICES
    """
    from .device_types import find_device_by_product_name, find_device_by_device_id, KNOWN_DEVICES

    tuya_category = device.get("category", "").lower()
    api_product_name = device.get("product_name", "Unknown Device")
    product_id = device.get("product_id", "")  # Tuya product ID (e.g., "bgvbvjwomgbisd8x")
    device_id = device.get("id", "")  # Device ID for pattern matching
    device_name = device.get("name", "").lower()

    _LOGGER.debug(f"Device detection: product_id={product_id}, device_id={device_id[:12] if device_id else 'N/A'}, "
                  f"category={tuya_category}, product_name={api_product_name}")

    # Method 1: Try to match by Tuya product_id (most accurate)
    # This uses the KNOWN_DEVICES database to find exact matches
    if product_id:
        device_info = find_device_by_product_name(product_id)
        if device_info:
            # Found exact match - return the device key and product_id
            for device_key, info in KNOWN_DEVICES.items():
                if product_id in info.get("product_names", []):
                    _LOGGER.info(f"Detected device by product_id: {device_key} ({product_id})")
                    return (device_key, product_id)

    # Method 2: Try to match by device_id pattern
    # Many devices have predictable ID prefixes (e.g., "bf34515c4ab6ec7f9a" for SOLO HCM)
    if device_id:
        device_info = find_device_by_device_id(device_id)
        if device_info:
            for device_key, info in KNOWN_DEVICES.items():
                # Check exact match
                if device_id in info.get("device_ids", []):
                    _LOGGER.info(f"Detected device by device_id: {device_key} ({device_id[:12]}...)")
                    return (device_key, info["product_names"][0])
                # Check pattern match
                for pattern in info.get("device_id_patterns", []):
                    if device_id.startswith(pattern):
                        _LOGGER.info(f"Detected device by device_id pattern: {device_key} ({pattern}*)")
                        return (device_key, info["product_names"][0])

    # Method 2: Category-based detection with specific device matching
    search_text = f"{api_product_name} {device_name}".lower()

    if tuya_category == "dcl":  # Cooktop category
        return ("ind7705hc_cooktop", "ind7705hc_cooktop")
    elif tuya_category == "yyj":  # Hood category
        # Try to identify specific hood model from product name
        if "solo" in search_text:
            return ("solo_hcm_hood", "bgvbvjwomgbisd8x")
        elif "ecco" in search_text:
            return ("ecco_hcm_hood", "gwdgkteknzvsattn")
        elif "flat" in search_text:
            return ("flat_hood", "luoxakxm2vm9azwu")
        elif "hermes" in search_text:
            return ("hermes_style_hood", "ypaixllljc2dcpae")
        else:
            # Default to generic hood for unknown yyj devices
            return ("default_hood", "default_hood")

    # Method 3: Fallback keyword detection
    if "ind" in search_text or "cooktop" in search_text or "kochfeld" in search_text:
        return ("ind7705hc_cooktop", "ind7705hc_cooktop")
    elif any(kw in search_text for kw in ["hood", "hermes", "style", "ecco", "solo", "dunst", "abzug"]):
        # Try specific matches first
        if "solo" in search_text:
            return ("solo_hcm_hood", "bgvbvjwomgbisd8x")
        elif "ecco" in search_text:
            return ("ecco_hcm_hood", "gwdgkteknzvsattn")
        return ("default_hood", "default_hood")

    # Default: unknown, use API product name
    return ("auto", api_product_name)


async def _try_discover_local_ip(
    hass: HomeAssistant,
    device_id: str,
    timeout: float = 6.0
) -> str | None:
    """Try to discover the local IP address of a device via mDNS/UDP.

    Args:
        hass: Home Assistant instance
        device_id: The Tuya device ID to find
        timeout: Discovery timeout in seconds

    Returns:
        Local IP address if found, None otherwise
    """
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
                local_ip = disc_info.get("ip") or disc_info.get("ip_address")
                if local_ip and _is_private_ip(local_ip):
                    _LOGGER.info(
                        f"Found local IP {local_ip} for device {device_id[:8]} via discovery"
                    )
                    return local_ip

        _LOGGER.debug(f"No local IP found for device {device_id[:8]} via discovery")
        return None

    except Exception as err:
        _LOGGER.debug(f"Local IP discovery failed: {err}")
        return None

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

def _get_device_type_options() -> list[dict[str, str]]:
    """Generate device type options from KNOWN_DEVICES.

    Order: Specific hoods, specific cooktops, then generic/default options last.

    Returns:
        List of dicts with 'value' and 'label' keys for selector options.
    """
    options: list[dict[str, str]] = []
    hoods: list[dict[str, str]] = []
    cooktops: list[dict[str, str]] = []
    default_options: list[dict[str, str]] = []

    # Get devices from KNOWN_DEVICES (device_types.py - the main source)
    for device_key, device_info in KNOWN_DEVICES.items():
        category = device_info.get("category", "")
        name = device_info.get("name", device_key)

        # Separate default/generic devices
        if device_key == "default_hood":
            default_options.append({
                "value": device_key,
                "label": "Default Hood - Generic Range Hood (if model unknown)"
            })
        elif category == CATEGORY_HOOD:
            hoods.append({"value": device_key, "label": f"{name}"})
        elif category == CATEGORY_COOKTOP:
            cooktops.append({"value": device_key, "label": f"{name}"})

    # Sort alphabetically
    hoods.sort(key=lambda x: x["label"])
    cooktops.sort(key=lambda x: x["label"])

    # Build final list: specific hoods, cooktops, then defaults at the end
    options.extend(hoods)
    options.extend(cooktops)
    options.extend(default_options)

    return options


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
        product_name = device.get("product_name", "Unknown Device")
        device_name = device.get("name", device_id)
        # Try both possible IP keys from discovery
        ip_address = device.get("ip") or device.get("host") or "Unknown IP"

        label = f"{product_name} - {device_id} ({ip_address})"
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
    }

    # Only show advanced entities option for induction cooktops
    if device_type in ["ind7705hc", "induction_cooktop"]:
        schema_dict[vol.Optional("enable_advanced_entities", default=False)] = bool
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

        # Check if device is already configured
        await self.async_set_unique_id(device_id)
        self._abort_if_unique_id_configured(updates={CONF_IP_ADDRESS: host} if host else None)

        # Store discovery info for later steps
        self._device_info = {
            "device_id": device_id,
            "ip": host,
            "name": discovery_info.get("name", f"KKT Device {device_id[:8]}"),
            "discovered_via": "zeroconf",
        }

        # Check if we have API credentials to auto-fetch local key
        api_manager = GlobalAPIManager(self.hass)
        if api_manager.has_stored_credentials():
            _LOGGER.info(f"Zeroconf: API credentials available, enriching device {device_id[:8]}")
            try:
                api_devices = await api_manager.get_kkt_devices_from_api()
                for api_device in api_devices:
                    if api_device.get("id") == device_id:
                        # Found matching device in API
                        self._device_info["local_key"] = api_device.get("local_key")
                        self._device_info["product_name"] = api_device.get("product_name")
                        self._device_info["tuya_category"] = api_device.get("category")

                        # Detect device type
                        device_type, product_name = _detect_device_type_from_api(api_device)
                        self._device_info["device_type"] = device_type
                        self._device_info["product_name"] = product_name

                        _LOGGER.info(f"Zeroconf: Enriched device {device_id[:8]} with API data")
                        break
            except Exception as err:
                _LOGGER.warning(f"Zeroconf: Failed to enrich with API data: {err}")

        # If we have all required info (including local_key), show confirmation
        if self._device_info.get("local_key") and self._device_info.get("ip"):
            return await self.async_step_zeroconf_confirm()

        # Otherwise, show discovery notification and ask for local key
        return await self.async_step_zeroconf_authenticate()

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
                "device_type": self._device_info.get("device_type", "auto"),
                "integration_mode": "hybrid",
            }

            title = f"KKT Kolbe {self._device_info.get('name', device_id[:8])}"

            return self.async_create_entry(
                title=title,
                data=config_data,
            )

        # Show confirmation form
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                "device_name": self._device_info.get("name", "Unknown"),
                "device_id": self._device_info.get("device_id", "Unknown")[:8],
                "ip_address": self._device_info.get("ip", "Unknown"),
                "product_name": self._device_info.get("product_name", "Auto-detected"),
            },
        )

    async def async_step_zeroconf_authenticate(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle zeroconf discovered device that needs local key."""
        errors: dict[str, str] = {}

        if user_input is not None:
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
                        "device_type": self._device_info.get("device_type", "auto"),
                    }

                    title = f"KKT Kolbe {self._device_info.get('name', device_id[:8])}"

                    return self.async_create_entry(
                        title=title,
                        data=config_data,
                    )
                else:
                    errors["local_key"] = "invalid_auth"

        # Check if API credentials are available but device wasn't found
        api_manager = GlobalAPIManager(self.hass)
        api_hint = ""
        if not api_manager.has_stored_credentials():
            api_hint = "Tip: Configure API credentials to auto-fetch local keys for future devices."

        return self.async_show_form(
            step_id="zeroconf_authenticate",
            data_schema=vol.Schema({
                vol.Required("local_key"): str,
            }),
            errors=errors,
            description_placeholders={
                "device_name": self._device_info.get("name", "Unknown"),
                "device_id": self._device_info.get("device_id", "Unknown")[:8],
                "ip_address": self._device_info.get("ip", "Unknown"),
                "api_hint": api_hint,
            },
        )

    async def async_step_smart_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle smart discovery - combines local scan with API data."""
        errors: dict[str, str] = {}

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

                if result.ready_to_add:
                    # One-click setup - device has all required info
                    await self.async_set_unique_id(result.device_id)
                    self._abort_if_unique_id_configured()

                    # Detect device type
                    device_type = result.device_type
                    product_name = result.product_name or "auto"

                    config_data = {
                        CONF_IP_ADDRESS: result.ip_address,
                        "device_id": result.device_id,
                        "local_key": result.local_key,
                        "product_name": product_name,
                        "device_type": device_type,
                        "integration_mode": "hybrid" if result.api_enriched else "manual",
                    }

                    return self.async_create_entry(
                        title=f"KKT Kolbe {result.name}",
                        data=config_data,
                    )
                else:
                    # Device needs local key - go to authentication step
                    self._device_info = result.to_dict()
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
        has_api = api_manager.has_stored_credentials()

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
                    "category": category
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
        if api_manager.has_stored_credentials() and user_input is None:
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

                    # Test connection and get device list
                    async with api_client:
                        if await api_client.test_connection():
                            devices = await api_client.get_device_list()

                            # Filter for KKT Kolbe devices
                            kkt_devices = []
                            for device in devices:
                                product_name = device.get("product_name", "").lower()
                                if any(keyword in product_name for keyword in ["kkt", "kolbe", "range", "hood", "induction"]):
                                    kkt_devices.append(device)

                            if kkt_devices:
                                # Store API credentials globally for reuse
                                api_manager.store_api_credentials(client_id, client_secret, endpoint)

                                # Store API info and show device selection
                                self._api_info = {
                                    "client_id": client_id,
                                    "client_secret": client_secret,
                                    "endpoint": endpoint
                                }
                                self._discovered_devices = {}
                                for device in kkt_devices:
                                    device_type, internal_product_name = _detect_device_type_from_api(device)
                                    self._discovered_devices[device["id"]] = {
                                        "device_id": device["id"],
                                        "name": device.get("name", f"KKT Device {device['id']}"),
                                        "product_name": internal_product_name,
                                        "api_product_name": device.get("product_name", "Unknown Device"),
                                        "tuya_category": device.get("category", ""),
                                        "ip": device.get("ip"),
                                        "local_key": device.get("local_key"),
                                        "discovered_via": "API",
                                        "device_type": device_type
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

            return self.async_create_entry(
                title=device_info["name"],
                data=config_data
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
                            self._discovered_devices[device["id"]] = {
                                "device_id": device["id"],
                                "name": device.get("name", f"KKT Device {device['id']}"),
                                "product_name": internal_product_name,
                                "api_product_name": device.get("product_name", "Unknown Device"),
                                "tuya_category": device.get("category", ""),
                                "ip": device.get("ip"),  # Include IP from API
                                "local_key": device.get("local_key"),  # Include local_key from API
                                "discovered_via": "API",
                                "device_type": device_type
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

                    # Test connection and get device list
                    async with api_client:
                        if await api_client.test_connection():
                            devices = await api_client.get_device_list()

                            # Filter for KKT Kolbe devices
                            kkt_devices = []
                            for device in devices:
                                product_name = device.get("product_name", "").lower()
                                if any(keyword in product_name for keyword in ["kkt", "kolbe", "range", "hood", "induction"]):
                                    kkt_devices.append(device)

                            if kkt_devices:
                                # Store API credentials globally for reuse
                                api_manager = GlobalAPIManager(self.hass)
                                api_manager.store_api_credentials(client_id, client_secret, endpoint)

                                # Store API info and show device selection
                                self._api_info = {
                                    "client_id": client_id,
                                    "client_secret": client_secret,
                                    "endpoint": endpoint
                                }
                                self._discovered_devices = {}
                                for device in kkt_devices:
                                    device_type, internal_product_name = _detect_device_type_from_api(device)
                                    self._discovered_devices[device["id"]] = {
                                        "device_id": device["id"],
                                        "name": device.get("name", f"KKT Device {device['id']}"),
                                        "product_name": internal_product_name,
                                        "api_product_name": device.get("product_name", "Unknown Device"),
                                        "tuya_category": device.get("category", ""),
                                        "ip": device.get("ip"),  # Include IP from API
                                        "local_key": device.get("local_key"),  # Include local_key from API
                                        "discovered_via": "API",
                                        "device_type": device_type
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

        if user_input is not None:
            # Check if user wants to go back
            if user_input.get("back_to_previous"):
                # Go back to manual or discovery based on where we came from
                if self._device_info.get("product_name") == "Manual Configuration":
                    return await self.async_step_manual()
                else:
                    return await self.async_step_discovery()

            local_key = user_input["local_key"]
            test_connection = user_input.get("test_connection", True)

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

        # Create schema with pre-filled local key and back option
        auth_schema = vol.Schema({
            vol.Required("local_key", default=default_local_key): str,
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

    async def async_step_settings(
        self, user_input: dict[str, Any | None] = None
    ) -> FlowResult:
        """Handle advanced settings step."""
        if user_input is not None:
            # Check if user wants to go back
            if user_input.get("back_to_authentication"):
                return await self.async_step_authentication()

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
        if user_input is not None:
            # Check if user wants to go back to settings
            if user_input.get("back_to_settings"):
                return await self.async_step_settings()

            # Set unique ID and check for duplicates (Bronze requirement: unique-config-entry)
            device_id = self._device_info["device_id"]
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            # Create the config entry
            title = f"KKT Kolbe {self._device_info.get('name', 'Device')}"

            config_data = {
                CONF_IP_ADDRESS: self._device_info["ip"],
                "device_id": self._device_info["device_id"],
                "local_key": self._local_key,
                "product_name": self._device_info.get("product_name", "Unknown"),
            }

            # Add advanced settings as options
            options_data = {
                CONF_SCAN_INTERVAL: self._advanced_settings.get("update_interval", 30),
                "enable_debug_logging": self._advanced_settings.get("enable_debug_logging", False),
                "enable_advanced_entities": self._advanced_settings.get("enable_advanced_entities", False),
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


class KKTKolbeOptionsFlow(OptionsFlow):
    """Handle KKT Kolbe options flow."""

    def __init__(self):
        """Initialize options flow."""
        # No longer store config_entry manually - use self.config_entry property
        # This property is automatically provided by the OptionsFlow parent class
        pass

    async def async_step_init(
        self, user_input: dict[str, Any | None] = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate options
            validation_errors = await self._validate_options(user_input)
            if not validation_errors:
                return self.async_create_entry(title="", data=user_input)
            else:
                errors.update(validation_errors)

        # Get current settings from config_entry
        current_interval = self.config_entry.options.get(CONF_SCAN_INTERVAL, 30)
        current_debug = self.config_entry.options.get("enable_debug_logging", False)
        current_advanced = self.config_entry.options.get("enable_advanced_entities", False)
        current_naming = self.config_entry.options.get("zone_naming_scheme", "zone")
        current_local_key = self.config_entry.data.get(CONF_ACCESS_TOKEN, self.config_entry.data.get("local_key", ""))

        # Get current API settings
        current_api_enabled = self.config_entry.data.get("api_enabled", False)
        current_client_id = self.config_entry.data.get("api_client_id", "")
        current_client_secret = self.config_entry.data.get("api_client_secret", "")
        current_endpoint = self.config_entry.data.get("api_endpoint", "https://openapi.tuyaeu.com")

        options_schema = vol.Schema({
            vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): selector.selector({
                "number": {
                    "min": 10, "max": 300, "step": 5,
                    "unit_of_measurement": "seconds",
                    "mode": "slider"
                }
            }),
            vol.Optional("new_local_key", default=""): selector.selector({
                "text": {
                    "type": "password"
                }
            }),
            vol.Optional("api_enabled", default=current_api_enabled): bool,
            vol.Optional("api_client_id", default=current_client_id): selector.selector({
                "text": {}
            }),
            vol.Optional("api_client_secret", default=""): selector.selector({
                "text": {
                    "type": "password"
                }
            }),
            vol.Optional("api_endpoint", default=current_endpoint): selector.selector({
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
            vol.Optional("enable_debug_logging", default=current_debug): bool,
            vol.Optional("enable_advanced_entities", default=current_advanced): bool,
            vol.Optional("zone_naming_scheme", default=current_naming): selector.selector({
                "select": {
                    "options": [
                        {"value": "zone", "label": "Zone 1, Zone 2, ..."},
                        {"value": "numeric", "label": "1, 2, 3, ..."},
                        {"value": "custom", "label": "Custom Names"}
                    ],
                    "mode": "dropdown"
                }
            }),
            vol.Optional("test_connection", default=True): bool,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
            description_placeholders={
                "device_name": self.config_entry.title,
                "current_interval": current_interval
            }
        )

    async def _validate_options(self, options: dict[str, Any]) -> dict[str, str]:
        """Validate options."""
        errors = {}

        # Handle new local key update
        new_local_key = options.get("new_local_key", "").strip()
        if new_local_key:
            # Validate local key format (16 characters, alphanumeric + special chars)
            if len(new_local_key) != 16:
                errors["new_local_key"] = "invalid_local_key_length"
            else:
                # Test the new local key
                try:
                    device_id = self.config_entry.data.get(CONF_DEVICE_ID) or self.config_entry.data.get("device_id")
                    ip_address = self.config_entry.data.get(CONF_IP_ADDRESS) or self.config_entry.data.get("ip_address") or self.config_entry.data.get("host")

                    if device_id and ip_address:
                        # Lazy import to avoid blocking
                        from .tuya_device import KKTKolbeTuyaDevice

                        # Test new local key with temporary device instance
                        test_device = KKTKolbeTuyaDevice(
                            device_id=device_id,
                            ip_address=ip_address,
                            local_key=new_local_key,
                            hass=self.hass,  # Pass hass for proper executor job scheduling
                        )

                        if await test_device.async_test_connection():
                            # Update the config entry with new local key
                            new_data = self.config_entry.data.copy()
                            new_data[CONF_ACCESS_TOKEN] = new_local_key
                            new_data["local_key"] = new_local_key

                            # Update config entry directly
                            self.hass.config_entries.async_update_entry(
                                self.config_entry, data=new_data
                            )

                            # Trigger service to update coordinator
                            await self.hass.services.async_call(
                                DOMAIN,
                                "update_local_key",
                                {
                                    "device_id": device_id,
                                    "local_key": new_local_key,
                                    "force_reconnect": True
                                }
                            )

                            _LOGGER.info(f"Local key successfully updated for device {device_id}")
                        else:
                            errors["new_local_key"] = "local_key_test_failed"
                    else:
                        errors["new_local_key"] = "missing_device_info"

                except Exception as exc:
                    errors["new_local_key"] = "local_key_test_failed"
                    _LOGGER.error(f"Local key test failed: {exc}")

        # Handle API settings update
        api_enabled = options.get("api_enabled", False)
        if api_enabled:
            client_id = options.get("api_client_id", "").strip()
            client_secret = options.get("api_client_secret", "").strip()

            if not client_id:
                errors["api_client_id"] = "api_client_id_required"
            elif len(client_id) < 10:
                errors["api_client_id"] = "api_client_id_invalid"

            if not client_secret:
                errors["api_client_secret"] = "api_client_secret_required"
            elif len(client_secret) < 20:
                errors["api_client_secret"] = "api_client_secret_invalid"

            # If API credentials are provided, test them
            if client_id and client_secret and not errors:
                try:
                    from .api import TuyaCloudClient

                    api_client = TuyaCloudClient(
                        client_id=client_id,
                        client_secret=client_secret,
                        endpoint=options.get("api_endpoint", "https://openapi.tuyaeu.com")
                    )

                    # Test API connection
                    if not await api_client.test_connection():
                        errors["api_client_secret"] = "api_test_failed"
                    else:
                        # Update config entry with API settings
                        device_id = self.config_entry.data.get(CONF_DEVICE_ID) or self.config_entry.data.get("device_id")
                        new_data = self.config_entry.data.copy()
                        new_data["api_enabled"] = True
                        new_data["api_client_id"] = client_id
                        new_data["api_client_secret"] = client_secret
                        new_data["api_endpoint"] = options.get("api_endpoint", "https://openapi.tuyaeu.com")

                        self.hass.config_entries.async_update_entry(
                            self.config_entry, data=new_data
                        )
                        _LOGGER.info(f"API credentials updated for device {device_id}")

                except Exception as exc:
                    errors["api_client_secret"] = "api_test_failed"
                    _LOGGER.error(f"API test failed: {exc}")

        # Test connection if requested
        if options.get("test_connection", False):
            try:
                coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]["coordinator"]
                await coordinator.async_refresh()

                if not coordinator.last_update_success:
                    errors["base"] = "connection_test_failed"

            except Exception as exc:
                errors["base"] = "connection_test_failed"
                _LOGGER.debug("Connection test failed: %s", exc)

        return errors