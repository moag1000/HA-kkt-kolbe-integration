"""Config flow for KKT Kolbe integration."""
from __future__ import annotations

import asyncio
import ipaddress
import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.config_entries import ConfigFlow
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.config_entries import OptionsFlow
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api_manager import GlobalAPIManager
from .const import CONF_SMARTLIFE_APP_SCHEMA
from .const import CONF_SMARTLIFE_TOKEN_INFO
from .const import CONF_SMARTLIFE_USER_CODE
from .const import DOMAIN
from .const import ENTRY_TYPE_ACCOUNT
from .const import ENTRY_TYPE_DEVICE
from .const import QR_LOGIN_TIMEOUT
from .const import SETUP_MODE_SMARTLIFE
from .const import SMARTLIFE_SCHEMA
from .const import TUYA_HA_SCHEMA
from .const import TUYA_SMART_SCHEMA
from .device_types import CATEGORY_COOKTOP
from .device_types import CATEGORY_HOOD
from .device_types import KNOWN_DEVICES
from .discovery import async_start_discovery
from .discovery import get_discovered_devices
from .flows.options import KKTKolbeOptionsFlow  # Import the correct OptionsFlow
from .smart_discovery import SmartDiscovery
from .smart_discovery import SmartDiscoveryResult
from .smart_discovery import async_get_configured_device_ids
from .tuya_device import KKTKolbeTuyaDevice

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
    from .device_types import KNOWN_DEVICES
    from .device_types import find_device_by_device_id
    from .device_types import find_device_by_product_name

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
                device_ids = info.get("device_ids", [])
                if isinstance(device_ids, list) and device_id in device_ids:
                    product_names = info.get("product_names", [])
                    product_name = str(product_names[0]) if isinstance(product_names, list) and product_names else device_key
                    _LOGGER.info(f"Detected device by device_id: {device_key} ({device_id[:12]}...)")
                    return (device_key, product_name)
                # Check pattern match
                patterns = info.get("device_id_patterns", [])
                if isinstance(patterns, list):
                    for pattern in patterns:
                        if isinstance(pattern, str) and device_id.startswith(pattern):
                            product_names = info.get("product_names", [])
                            product_name = str(product_names[0]) if isinstance(product_names, list) and product_names else device_key
                            _LOGGER.info(f"Detected device by device_id pattern: {device_key} ({pattern}*)")
                            return (device_key, product_name)

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


def _detect_device_type_from_device_id(device_id: str) -> tuple[str, str, str]:
    """Detect device type from device_id only (for discovery without API).

    Uses device_id patterns from KNOWN_DEVICES to detect device type.

    Args:
        device_id: The Tuya device ID

    Returns:
        Tuple of (device_type, product_name, friendly_name)
    """
    from .device_types import KNOWN_DEVICES

    if not device_id:
        return ("auto", "auto", "KKT Kolbe Device")

    _LOGGER.debug(f"Detecting device type from device_id: {device_id[:12]}...")

    # Check each known device for device_id matches
    for device_key, info in KNOWN_DEVICES.items():
        # Check exact device_id match
        device_ids = info.get("device_ids", [])
        if isinstance(device_ids, list) and device_id in device_ids:
            friendly_name = str(info.get("name", device_key))
            product_names = info.get("product_names", [])
            product_name = str(product_names[0]) if isinstance(product_names, list) and product_names else device_key
            _LOGGER.info(f"Detected device by exact device_id: {device_key} -> {friendly_name}")
            return (device_key, product_name, friendly_name)

        # Check device_id pattern match
        patterns = info.get("device_id_patterns", [])
        if isinstance(patterns, list):
            for pattern in patterns:
                if isinstance(pattern, str) and device_id.startswith(pattern):
                    friendly_name = str(info.get("name", device_key))
                    product_names = info.get("product_names", [])
                    product_name = str(product_names[0]) if isinstance(product_names, list) and product_names else device_key
                    _LOGGER.info(f"Detected device by device_id pattern {pattern}*: {device_key} -> {friendly_name}")
                    return (device_key, product_name, friendly_name)

    # No match found - return defaults
    _LOGGER.debug(f"No device_id pattern matched for {device_id[:12]}, using defaults")
    return ("auto", "auto", "KKT Kolbe Device")


def _is_kkt_device(device: Any) -> tuple[bool, str | None]:
    """Check if a TuyaSharingDevice is a KKT Kolbe device.

    Uses multiple detection methods in priority order:
    1. Match product_id against KNOWN_DEVICES database
    2. Match device_id pattern against KNOWN_DEVICES
    3. Check if product_name starts with "KKT"
    4. Check if category matches known appliance types (yyj, dcl)

    Args:
        device: TuyaSharingDevice instance from tuya_sharing SDK

    Returns:
        Tuple of (is_kkt, device_type_key or None)
        - (True, "hermes_style_hood") = Known KKT device with matched type
        - (True, None) = KKT device but unknown/new model
        - (False, None) = Not a KKT device
    """
    from .device_types import find_device_by_device_id

    # Method 1: Match by product_id (most accurate - exact match in KNOWN_DEVICES)
    if hasattr(device, 'product_id') and device.product_id:
        for device_key, info in KNOWN_DEVICES.items():
            # product_names in KNOWN_DEVICES contains Tuya product_id values
            if device.product_id in info.get("product_names", []):
                _LOGGER.debug(
                    "KKT device detected by product_id: %s -> %s",
                    device.product_id, device_key
                )
                return (True, device_key)

    # Method 2: Match by device_id pattern
    if hasattr(device, 'device_id') and device.device_id:
        device_info = find_device_by_device_id(device.device_id)
        if device_info:
            for device_key, info in KNOWN_DEVICES.items():
                # Check exact match
                device_ids = info.get("device_ids", [])
                if isinstance(device_ids, list) and device.device_id in device_ids:
                    _LOGGER.debug(
                        "KKT device detected by exact device_id: %s",
                        device_key
                    )
                    return (True, device_key)
                # Check pattern match
                patterns = info.get("device_id_patterns", [])
                if isinstance(patterns, list):
                    for pattern in patterns:
                        if isinstance(pattern, str) and device.device_id.startswith(pattern):
                            _LOGGER.debug(
                                "KKT device detected by device_id pattern %s*: %s",
                                pattern, device_key
                            )
                            return (True, device_key)

    # Method 3: Check product_name prefix - all KKT Kolbe products start with "KKT"
    if hasattr(device, 'product_name') and device.product_name:
        if device.product_name.upper().startswith("KKT"):
            _LOGGER.info(
                "KKT device detected by product_name prefix: %s (product_id=%s not in KNOWN_DEVICES)",
                device.product_name,
                getattr(device, 'product_id', 'N/A')
            )
            return (True, None)  # KKT device, but unknown model

    # Method 4: Category-based detection (less reliable, but catches unlisted devices)
    # yyj = range hood, dcl = cooktop
    if hasattr(device, 'category') and device.category in ("yyj", "dcl"):
        # Only use category match if product_name contains KKT-related keywords
        product_name = getattr(device, 'product_name', '') or ''
        name = getattr(device, 'name', '') or ''
        search_text = f"{product_name} {name}".lower()

        if any(kw in search_text for kw in ["kkt", "kolbe", "hermes", "ecco", "solo", "flat"]):
            _LOGGER.info(
                "KKT device detected by category + keywords: category=%s, name=%s",
                device.category, name or product_name
            )
            return (True, None)

    return (False, None)


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
                    return str(local_ip)

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
    vol.Required("local_key"): selector.selector({"text": {"type": "password"}}),
    vol.Optional("test_connection", default=True): bool,
    vol.Optional("back_to_previous", default=False): bool,
})

def get_settings_schema(device_type: str | None = None) -> vol.Schema:
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


class KKTKolbeConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
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

        # SmartLife/Tuya Sharing attributes
        self._smartlife_client: Any | None = None
        self._smartlife_user_code: str | None = None
        self._smartlife_app_schema: str = SMARTLIFE_SCHEMA
        self._smartlife_qr_code: str | None = None
        self._smartlife_devices: list[Any] = []
        self._smartlife_selected_devices: list[str] = []
        self._smartlife_auth_result: Any | None = None
        self._smartlife_scan_task: asyncio.Task[Any] | None = None

    async def async_step_zeroconf(
        self, discovery_info: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery of KKT Kolbe devices.

        Called automatically by Home Assistant when a matching mDNS service is found.

        IMPORTANT: We only set unique_id AFTER confirming we have local_key,
        to avoid blocking user-initiated Smart Discovery flows.
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

        # Check if device is already configured (without setting unique_id yet)
        configured_ids = await async_get_configured_device_ids(self.hass)
        if device_id in configured_ids:
            _LOGGER.debug(f"Zeroconf: Device {device_id[:8]} already configured, updating IP")
            # Update IP address for existing entry
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.data.get("device_id") == device_id:
                    self.hass.config_entries.async_update_entry(
                        entry, data={**entry.data, CONF_IP_ADDRESS: host}
                    )
                    break
            return self.async_abort(reason="already_configured")

        # Check if we have API credentials to get local_key
        # If not, abort early WITHOUT setting unique_id (so Smart Discovery isn't blocked)
        api_manager = GlobalAPIManager(self.hass)
        if not api_manager.has_stored_credentials():
            _LOGGER.debug(f"Zeroconf: No API credentials, aborting early for {device_id[:8]} "
                         f"(Smart Discovery will handle this device)")
            return self.async_abort(reason="no_local_key")

        # Store discovery info for later steps
        self._device_info = {
            "device_id": device_id,
            "ip": host,
            "name": discovery_info.get("name", f"KKT Device {device_id[:8]}"),
            "discovered_via": "zeroconf",
            "friendly_type": "KKT Kolbe Device",
            "device_type": "auto",
            "product_name": "auto",
        }

        # Try to detect device type from device_id pattern BEFORE API enrichment
        # This ensures we have a baseline detection even if API returns wrong type
        if device_id:
            dev_type, prod_name, friendly = _detect_device_type_from_device_id(device_id)
            if dev_type != "auto":
                self._device_info["device_type"] = dev_type
                self._device_info["product_name"] = prod_name
                self._device_info["friendly_type"] = friendly
                _LOGGER.info(f"Zeroconf: Pre-detected device type from device_id pattern: {dev_type} -> {friendly}")

        # Set initial title placeholder
        self.context["title_placeholders"] = {"name": self._device_info.get("friendly_type", "KKT Kolbe Device")}

        # We have API credentials (checked above), try to get local_key
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
                    self._device_info["icon_url"] = api_device.get("icon")  # Tuya device icon

                    # Use API name (user-configured name) or product_name
                    api_name = api_device.get("name") or api_device.get("product_name")
                    if api_name:
                        self._device_info["name"] = api_name

                    # Detect device type for proper entity setup
                    # BUT only update if not already correctly detected from device_id pattern
                    from .device_types import KNOWN_DEVICES
                    api_device_type, internal_product_name = _detect_device_type_from_api(api_device)
                    current_type = self._device_info.get("device_type", "auto")

                    if api_device_type != "auto" and (current_type == "auto" or current_type not in KNOWN_DEVICES):
                        self._device_info["device_type"] = api_device_type
                        self._device_info["product_name"] = internal_product_name
                        _LOGGER.debug(f"Zeroconf: Updated device_type from API: {api_device_type}")
                    else:
                        _LOGGER.debug(f"Zeroconf: Keeping pre-detected device_type: {current_type} (API suggested: {api_device_type})")

                    # Create friendly display name based on detected type
                    effective_device_type = self._device_info.get("device_type", "auto")
                    if effective_device_type in KNOWN_DEVICES:
                        kkt_device_info = KNOWN_DEVICES[effective_device_type]
                        self._device_info["friendly_type"] = kkt_device_info.get("name", effective_device_type)
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

        # If we have local_key, show confirmation (but DON'T set unique_id yet!)
        # unique_id will be set when actually creating the entry to avoid blocking Smart Discovery
        if self._device_info.get("local_key") and self._device_info.get("ip"):
            # Check if already configured without blocking the flow
            configured_ids = await async_get_configured_device_ids(self.hass)
            if device_id in configured_ids:
                # Update IP and abort
                for entry in self.hass.config_entries.async_entries(DOMAIN):
                    if entry.data.get("device_id") == device_id:
                        self.hass.config_entries.async_update_entry(
                            entry, data={**entry.data, CONF_IP_ADDRESS: host}
                        )
                        break
                return self.async_abort(reason="already_configured")
            return await self.async_step_zeroconf_confirm()

        # No local_key available - abort WITHOUT setting unique_id
        # This allows Smart Discovery to handle this device instead
        _LOGGER.info(f"Zeroconf: Device {device_id[:8]} found but no local_key from API. "
                    f"Use Smart Discovery or manual setup. Aborting zeroconf flow.")
        return self.async_abort(reason="no_local_key")

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
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
                "icon_url": self._device_info.get("icon_url"),  # Tuya device icon
            }

            # Store API credentials if available (for persistence after restart)
            api_manager = GlobalAPIManager(self.hass)
            creds = api_manager.get_stored_api_credentials()
            if creds:
                config_data["api_enabled"] = True
                config_data["api_client_id"] = creds["client_id"]
                config_data["api_client_secret"] = creds["client_secret"]
                config_data["api_endpoint"] = creds["endpoint"]
                _LOGGER.info("Zeroconf: API credentials stored in config entry for persistence")

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
    ) -> ConfigFlowResult:
        """Handle zeroconf discovered device that needs local key or API config."""
        errors: dict[str, str] = {}

        api_manager = GlobalAPIManager(self.hass)
        has_api = api_manager.has_stored_credentials()

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
                        "integration_mode": "hybrid" if has_api else "manual",
                        "icon_url": self._device_info.get("icon_url"),  # Tuya device icon
                    }

                    # Store API credentials if available (for persistence after restart)
                    creds = api_manager.get_stored_api_credentials()
                    if creds:
                        config_data["api_enabled"] = True
                        config_data["api_client_id"] = creds["client_id"]
                        config_data["api_client_secret"] = creds["client_secret"]
                        config_data["api_endpoint"] = creds["endpoint"]
                        _LOGGER.info("Zeroconf authenticate: API credentials stored in config entry")

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
                vol.Required("local_key"): selector.selector({"text": {"type": "password"}}),
            })
            api_hint = "API credentials are configured but local_key was not found for this device."
        else:
            # No API configured - offer both options
            schema = vol.Schema({
                vol.Optional("local_key"): selector.selector({"text": {"type": "password"}}),
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
    ) -> ConfigFlowResult:
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
                            api_manager.store_api_credentials(client_id, client_secret, endpoint)
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
                                    self._device_info["icon_url"] = api_device.get("icon")  # Tuya device icon

                                    api_name = api_device.get("name") or api_device.get("product_name")
                                    if api_name:
                                        self._device_info["name"] = api_name

                                    # Detect device type - but only update if not already correctly detected
                                    api_device_type, internal_product_name = _detect_device_type_from_api(api_device)
                                    current_type = self._device_info.get("device_type", "auto")

                                    from .device_types import KNOWN_DEVICES
                                    if api_device_type != "auto" and (current_type == "auto" or current_type not in KNOWN_DEVICES):
                                        self._device_info["device_type"] = api_device_type
                                        self._device_info["product_name"] = internal_product_name
                                        _LOGGER.debug(f"Zeroconf API: Updated device_type from API: {api_device_type}")
                                    else:
                                        _LOGGER.debug(f"Zeroconf API: Keeping pre-detected device_type: {current_type}")

                                    effective_device_type = self._device_info.get("device_type", "auto")
                                    if effective_device_type in KNOWN_DEVICES:
                                        self._device_info["friendly_type"] = KNOWN_DEVICES[effective_device_type].get("name", effective_device_type)
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
                                device_id_str = str(device_id) if device_id else ""
                                _LOGGER.warning(f"API configured but device {device_id_str[:8]} not found or has no local_key")

                                # Still try to detect device type from device_id if not already detected
                                if not self._device_info.get("device_type") or self._device_info.get("device_type") == "auto":
                                    dev_type, prod_name, friendly = _detect_device_type_from_device_id(device_id_str)
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
    ) -> ConfigFlowResult:
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

                    config_data: dict[str, Any] = {
                        CONF_IP_ADDRESS: result.ip_address,
                        "device_id": result.device_id,
                        "local_key": result.local_key,
                        "product_name": product_name,
                        "device_type": device_type,
                        "integration_mode": "hybrid" if result.api_enriched else "manual",
                        "icon_url": getattr(result, "icon_url", None),  # Tuya device icon
                    }

                    # If API was used for enrichment, store credentials persistently
                    if result.api_enriched:
                        api_manager = GlobalAPIManager(self.hass)
                        creds = api_manager.get_stored_api_credentials()
                        if creds:
                            config_data["api_enabled"] = True
                            config_data["api_client_id"] = creds["client_id"]
                            config_data["api_client_secret"] = creds["client_secret"]
                            config_data["api_endpoint"] = creds["endpoint"]
                            _LOGGER.info("Smart Discovery: API credentials stored in config entry for persistence")

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
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step - setup method selection.

        SmartLife QR-Code is now the DEFAULT and recommended method.
        No developer account required!
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            setup_method = user_input["setup_method"]

            if setup_method == "smartlife":
                # SmartLife QR-Code Setup (NEW - Default)
                # First check if existing account can be reused
                return await self.async_step_smartlife_check_existing()
            elif setup_method == "smart_discovery":
                return await self.async_step_smart_discovery()
            elif setup_method == "discovery":
                return await self.async_step_discovery()
            elif setup_method == "manual":
                return await self.async_step_manual()
            elif setup_method == "api_only":
                return await self.async_step_api_only()

        _LOGGER.debug("Showing user config form with setup methods (SmartLife as default)")

        # Check if API credentials are available for smart discovery hint
        api_manager = GlobalAPIManager(self.hass)
        has_api = api_manager.has_stored_credentials()

        # Build schema with SmartLife as the NEW default (no developer account needed!)
        user_schema = vol.Schema({
            vol.Required("setup_method", default="smartlife"): selector.selector({
                "select": {
                    "options": [
                        {"value": "smartlife", "label": "SmartLife / Tuya Smart App (Recommended - No Developer Account)"},
                        {"value": "smart_discovery", "label": "Smart Discovery (Network Scan + API)"},
                        {"value": "discovery", "label": "Local Discovery (Network Scan Only)"},
                        {"value": "manual", "label": "Manual Setup (IP + Local Key)"},
                        {"value": "api_only", "label": "Tuya IoT Platform (Developer Account)"}
                    ],
                    "mode": "dropdown",
                    "translation_key": "setup_method"
                }
            })
        })

        if has_api:
            api_status = "Tuya IoT Platform credentials configured - Smart Discovery available!"
        else:
            api_status = "Use SmartLife/Tuya Smart App for easy setup without developer account"

        return self.async_show_form(
            step_id="user",
            data_schema=user_schema,
            errors=errors,
            description_placeholders={
                "setup_mode": "Choose how you want to set up your KKT Kolbe device",
                "api_status": api_status,
            }
        )

    # =========================================================================
    # SmartLife / Tuya Smart QR-Code Authentication Flow
    # =========================================================================

    async def async_step_smartlife_check_existing(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Check for existing SmartLife accounts and offer to reuse them.

        This prevents users from having to re-authenticate when adding
        additional devices from the same SmartLife account.
        """
        # Find existing SmartLife Account entries
        existing_accounts: list[ConfigEntry] = []
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.data.get("entry_type") == ENTRY_TYPE_ACCOUNT:
                existing_accounts.append(entry)

        # If no existing accounts, go directly to user code input
        if not existing_accounts:
            return await self.async_step_smartlife_user_code()

        # Handle user selection
        if user_input is not None:
            selected = user_input.get("account_choice")

            if selected == "new_account":
                # User wants to create a new account
                return await self.async_step_smartlife_user_code()
            else:
                # User selected an existing account - find it and use its tokens
                for entry in existing_accounts:
                    if entry.entry_id == selected:
                        self._existing_account_entry = entry
                        return await self.async_step_smartlife_use_existing()

                # Entry not found (shouldn't happen)
                return await self.async_step_smartlife_user_code()

        # Build options list with existing accounts
        options = []
        for entry in existing_accounts:
            # Get account info for display
            token_info = entry.data.get(CONF_SMARTLIFE_TOKEN_INFO, {})
            has_token = bool(token_info.get("access_token"))

            status = "✓ Active" if has_token else "⚠ Re-auth needed"
            label = f"{entry.title} ({status})"

            options.append({
                "value": entry.entry_id,
                "label": label,
            })

        # Add option to create new account
        options.append({
            "value": "new_account",
            "label": "➕ Create new SmartLife account",
        })

        schema = vol.Schema({
            vol.Required("account_choice"): selector.selector({
                "select": {
                    "options": options,
                    "mode": "list",
                }
            }),
        })

        return self.async_show_form(
            step_id="smartlife_check_existing",
            data_schema=schema,
            description_placeholders={
                "account_count": str(len(existing_accounts)),
            },
        )

    async def async_step_smartlife_use_existing(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Use existing SmartLife account to add a new device.

        Loads tokens from existing account entry and proceeds to device selection.
        """
        from .clients.tuya_sharing_client import TuyaSharingClient

        if not hasattr(self, '_existing_account_entry') or not self._existing_account_entry:
            return await self.async_step_smartlife_user_code()

        entry = self._existing_account_entry
        token_info = entry.data.get(CONF_SMARTLIFE_TOKEN_INFO, {})

        # Check if tokens are valid
        if not token_info.get("access_token"):
            # No tokens - need re-auth
            _LOGGER.warning(
                "SmartLife account %s has no valid tokens, requiring re-auth",
                entry.title
            )
            return await self.async_step_smartlife_user_code()

        try:
            # Use the classmethod to properly restore the client with all fields
            self._smartlife_client = await TuyaSharingClient.async_from_stored_tokens(
                hass=self.hass,
                token_info=token_info,
            )

            # Store info for device creation
            self._smartlife_user_code = token_info.get("user_code", "")
            self._smartlife_app_schema = token_info.get("app_schema", TUYA_HA_SCHEMA)

            # Get auth result from the restored client
            self._smartlife_auth_result = self._smartlife_client._auth_result

            _LOGGER.info(
                "Restored SmartLife client from existing account: %s (user_id=%s...)",
                entry.title,
                self._smartlife_auth_result.user_id[:8] if self._smartlife_auth_result.user_id else "unknown"
            )

            # Go directly to device selection
            return await self.async_step_smartlife_select_devices()

        except Exception as exc:
            _LOGGER.error(
                "Failed to restore SmartLife client from account %s: %s",
                entry.title, exc
            )
            # Fall back to new auth
            return await self.async_step_smartlife_user_code()

    async def async_step_smartlife_user_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle SmartLife user code input step.

        User provides their User Code from the SmartLife/Tuya Smart app:
        App -> Me -> Settings -> Account and Security -> User Code

        The integration will automatically try both SmartLife and Tuya Smart
        schemas to find the correct one.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            user_code = user_input.get("user_code", "").strip()

            # Validate user code format - minimum 6 characters
            # User codes can be 6-10+ chars (e.g., "Cx1i1Zh", "EU12345678")
            if not user_code or len(user_code) < 6:
                errors["user_code"] = "invalid_user_code"
            else:
                # Store for later steps - will auto-detect correct schema
                self._smartlife_user_code = user_code
                self._smartlife_app_schema = None  # Will be auto-detected

                # Proceed to QR code scan step
                return await self.async_step_smartlife_scan()

        # Show user code input form (simplified - no schema selection needed)
        schema = vol.Schema({
            vol.Required("user_code"): selector.selector({
                "text": {
                    "type": "text",
                }
            }),
        })

        return self.async_show_form(
            step_id="smartlife_user_code",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "user_code_instructions": (
                    "Find your User Code in the SmartLife or Tuya Smart app:\n"
                    "Me -> Settings -> Account and Security -> User Code"
                ),
            },
        )

    async def async_step_smartlife_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle QR code generation and display step.

        Shows QR code using QrCodeSelector (like Tuya core integration).
        User scans with SmartLife/Tuya Smart app, then we poll for result.
        """
        from .clients.tuya_sharing_client import TuyaSharingClient
        from .exceptions import KKTAuthenticationError
        from .exceptions import KKTConnectionError

        # Initialize client and generate QR code if not already done
        if not self._smartlife_qr_code:
            if not self._smartlife_user_code:
                return await self.async_step_smartlife_user_code()

            # Auto-detect schema by trying haauthorize (official HA), SmartLife and Tuya Smart
            # haauthorize is required for the tuya-device-sharing-sdk Manager API
            schemas_to_try = [TUYA_HA_SCHEMA, SMARTLIFE_SCHEMA, TUYA_SMART_SCHEMA]
            last_error: Exception | None = None
            working_schema: str | None = None

            for schema in schemas_to_try:
                try:
                    _LOGGER.debug("Trying app schema: %s for user code %s...", schema, self._smartlife_user_code[:4])
                    self._smartlife_client = TuyaSharingClient(
                        hass=self.hass,
                        user_code=self._smartlife_user_code,
                        app_schema=schema,
                    )

                    # Generate QR code
                    self._smartlife_qr_code = await self._smartlife_client.async_generate_qr_code()
                    working_schema = schema
                    self._smartlife_app_schema = schema
                    _LOGGER.info(
                        "Generated SmartLife QR code with %s schema for user code %s...",
                        schema, self._smartlife_user_code[:4]
                    )
                    break  # Success - exit loop

                except KKTAuthenticationError as err:
                    _LOGGER.debug("Schema %s failed for user code: %s", schema, err)
                    last_error = err
                    continue
                except KKTConnectionError as err:
                    _LOGGER.debug("Connection failed with schema %s: %s", schema, err)
                    last_error = err
                    continue

            # If no schema worked, return to user code input
            if working_schema is None:
                _LOGGER.error(
                    "Failed to generate QR code with both schemas - invalid user code: %s",
                    last_error
                )
                return self.async_show_form(
                    step_id="smartlife_user_code",
                    data_schema=vol.Schema({
                        vol.Required("user_code", default=self._smartlife_user_code or ""): selector.selector({
                            "text": {"type": "text"}
                        }),
                    }),
                    errors={"user_code": "invalid_user_code"},
                    description_placeholders={
                        "error_details": str(last_error) if last_error else "Unknown error",
                    },
                )

        # User clicked "I've scanned" - check login result
        if user_input is not None:
            return await self.async_step_smartlife_check_login()

        # Build QR code data string (like Tuya: "tuyaSmart--qrLogin?token=XXX")
        # Our QR code URL from tuya-device-sharing-sdk is already the full URL
        qr_data = self._smartlife_qr_code

        # Show form with QR code selector
        return self.async_show_form(
            step_id="smartlife_scan",
            data_schema=vol.Schema({
                vol.Optional("qr_code"): selector.QrCodeSelector(
                    config=selector.QrCodeSelectorConfig(
                        data=qr_data,
                        scale=5,
                        error_correction_level=selector.QrErrorCorrectionLevel.QUARTILE,
                    )
                ),
            }),
            description_placeholders={
                "timeout": str(QR_LOGIN_TIMEOUT),
            },
        )

    async def async_step_smartlife_check_login(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Check if QR code was scanned and login successful."""
        from .exceptions import KKTAuthenticationError
        from .exceptions import KKTConnectionError
        from .exceptions import KKTTimeoutError

        if not self._smartlife_client:
            return await self.async_step_smartlife_user_code()

        try:
            # Poll for login result (with shorter timeout since user claims to have scanned)
            auth_result = await self._smartlife_client.async_poll_login_result(
                timeout=30,  # 30 seconds should be enough after user clicked
            )

            if auth_result and auth_result.success:
                self._smartlife_auth_result = auth_result
                _LOGGER.info("SmartLife QR code scan successful for user %s", auth_result.user_id)
                return await self.async_step_smartlife_select_devices()
            else:
                error_msg = getattr(auth_result, 'error_message', 'Authentication failed')
                _LOGGER.warning("SmartLife authentication failed: %s", error_msg)
                return await self.async_step_smartlife_scan_failed()

        except KKTTimeoutError:
            _LOGGER.warning("SmartLife QR code scan check timed out")
            return await self.async_step_smartlife_scan_timeout()
        except (KKTAuthenticationError, KKTConnectionError) as err:
            _LOGGER.error("SmartLife authentication error: %s", err)
            return await self.async_step_smartlife_scan_failed()
        except Exception as err:
            _LOGGER.exception("Unexpected error during SmartLife login check: %s", err)
            return await self.async_step_smartlife_scan_failed()

    async def async_step_smartlife_scan_timeout(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle QR code scan timeout."""
        if user_input is not None:
            if user_input.get("retry"):
                # Reset and retry
                self._smartlife_scan_task = None
                self._smartlife_qr_code = None
                return await self.async_step_smartlife_scan()
            else:
                # Go back to user code input
                return await self.async_step_smartlife_user_code()

        return self.async_show_form(
            step_id="smartlife_scan_timeout",
            data_schema=vol.Schema({
                vol.Optional("retry", default=True): bool,
            }),
            description_placeholders={
                "timeout_message": (
                    f"QR code scan timed out after {QR_LOGIN_TIMEOUT} seconds. "
                    "Please try again and scan the QR code faster."
                ),
            },
        )

    async def async_step_smartlife_scan_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle QR code scan failure."""
        if user_input is not None:
            if user_input.get("retry"):
                # Reset and retry
                self._smartlife_scan_task = None
                self._smartlife_qr_code = None
                return await self.async_step_smartlife_scan()
            else:
                # Go back to user code input to try different user code
                return await self.async_step_smartlife_user_code()

        return self.async_show_form(
            step_id="smartlife_scan_failed",
            data_schema=vol.Schema({
                vol.Optional("retry", default=True): bool,
            }),
            description_placeholders={
                "failure_message": (
                    "QR code authentication failed. "
                    "Please check your User Code and try again."
                ),
            },
        )

    async def async_step_smartlife_select_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle device selection from SmartLife account.

        Fetches all devices from the account, filters for KKT Kolbe devices,
        and allows user to select which ones to add.
        """
        from .exceptions import KKTConnectionError

        errors: dict[str, str] = {}

        if user_input is not None:
            # Single-select returns a string, convert to list for consistency
            selected_device = user_input.get("selected_devices")
            selected_devices = [selected_device] if selected_device else []

            if not selected_devices:
                errors["base"] = "no_devices_selected"
            else:
                self._smartlife_selected_devices = selected_devices

                # Check if the device needs type selection (unknown model)
                unknown_devices = []
                for device_id in selected_devices:
                    for device in self._smartlife_devices:
                        if device.device_id == device_id:
                            is_kkt, device_type = _is_kkt_device(device)
                            if is_kkt and device_type is None:
                                unknown_devices.append(device)
                            break

                if unknown_devices:
                    # Need to select device type for unknown models
                    self._unknown_devices_queue = unknown_devices
                    return await self.async_step_smartlife_select_device_type()

                # All devices have known types - create entries
                return await self._async_create_smartlife_entries()

        # Fetch devices if not already done
        if not self._smartlife_devices:
            if not self._smartlife_client or not self._smartlife_auth_result:
                _LOGGER.error("SmartLife client not initialized")
                return await self.async_step_smartlife_user_code()

            try:
                all_devices = await self._smartlife_client.async_get_devices()
                _LOGGER.info("Retrieved %d devices from SmartLife account", len(all_devices))

                # Filter for KKT Kolbe devices
                kkt_devices = []
                for device in all_devices:
                    is_kkt, device_type = _is_kkt_device(device)
                    if is_kkt:
                        # Store detected type on device for later use
                        device.kkt_device_type = device_type
                        if device_type and device_type in KNOWN_DEVICES:
                            device.kkt_product_name = KNOWN_DEVICES[device_type].get("name", device_type)
                        else:
                            device.kkt_product_name = device.product_name or "Unknown KKT Device"
                        kkt_devices.append(device)
                        _LOGGER.debug(
                            "Found KKT device: %s (%s) - type: %s",
                            device.name, device.device_id[:8], device_type or "unknown"
                        )

                self._smartlife_devices = kkt_devices

                if not kkt_devices:
                    _LOGGER.warning("No KKT Kolbe devices found in SmartLife account")
                    # Show warning with fallback to manual setup
                    return self.async_show_form(
                        step_id="smartlife_select_devices",
                        data_schema=vol.Schema({
                            vol.Optional("use_manual", default=False): bool,
                        }),
                        errors={"base": "no_kkt_devices_found"},
                        description_placeholders={
                            "kkt_device_count": "0",
                            "account_info": f"Found {len(all_devices)} device(s), but none are KKT Kolbe devices.",
                        },
                    )

            except KKTConnectionError as err:
                _LOGGER.error("Failed to fetch devices: %s", err)
                return self.async_show_form(
                    step_id="smartlife_select_devices",
                    data_schema=vol.Schema({}),  # Empty schema to show error
                    errors={"base": "cannot_connect"},
                    description_placeholders={
                        "kkt_device_count": "0",
                        "account_info": f"Error: {err}",
                    },
                )

        # Check for fallback to manual if no devices found
        if user_input and user_input.get("use_manual"):
            return await self.async_step_manual()

        # Get already configured device IDs
        configured_ids = await async_get_configured_device_ids(self.hass)

        # Build device selection options
        device_options = []
        for device in self._smartlife_devices:
            if device.device_id in configured_ids:
                continue  # Skip already configured devices

            # Build display label
            status = "Online" if device.online else "Offline"
            local_key_status = "Key available" if device.local_key else "No key"
            ip_info = device.ip or "IP unknown"

            label = f"{device.name} ({device.kkt_product_name}) - {ip_info} - {status}, {local_key_status}"
            device_options.append({
                "value": device.device_id,
                "label": label,
            })

        if not device_options:
            # All devices already configured
            return self.async_abort(reason="all_devices_configured")

        # Single-select schema for device selection (one device per setup)
        schema = vol.Schema({
            vol.Required("selected_devices"): selector.selector({
                "select": {
                    "options": device_options,
                    "multiple": False,
                    "mode": "list",
                }
            }),
        })

        return self.async_show_form(
            step_id="smartlife_select_devices",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "kkt_device_count": str(len(device_options)),
                "account_info": f"Connected as user {self._smartlife_auth_result.user_id[:8]}...",
            },
        )

    async def async_step_smartlife_select_device_type(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle device type selection for unknown KKT models.

        Only shown when a device is detected as KKT (by product_name prefix)
        but not found in KNOWN_DEVICES database.
        """
        if not hasattr(self, '_unknown_devices_queue') or not self._unknown_devices_queue:
            return await self._async_create_smartlife_entries()

        current_device = self._unknown_devices_queue[0]
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_type = user_input.get("device_type")

            if selected_type == "not_supported":
                # User says device is not supported - remove from selection
                self._smartlife_selected_devices = [
                    d for d in self._smartlife_selected_devices
                    if d != current_device.device_id
                ]
            else:
                # Store selected type on device
                current_device.kkt_device_type = selected_type
                if selected_type in KNOWN_DEVICES:
                    current_device.kkt_product_name = KNOWN_DEVICES[selected_type].get("name", selected_type)

                # Log for future KNOWN_DEVICES addition
                _LOGGER.info(
                    "User selected device type '%s' for product_id '%s' (product_name: %s). "
                    "Consider adding this to KNOWN_DEVICES.",
                    selected_type,
                    current_device.product_id,
                    current_device.product_name,
                )

            # Move to next unknown device or create entries
            self._unknown_devices_queue.pop(0)
            if self._unknown_devices_queue:
                return await self.async_step_smartlife_select_device_type()
            else:
                return await self._async_create_smartlife_entries()

        # Build device type options from KNOWN_DEVICES
        device_type_options = _get_device_type_options()
        device_type_options.append({
            "value": "not_supported",
            "label": "This device is not supported",
        })

        schema = vol.Schema({
            vol.Required("device_type"): selector.selector({
                "select": {
                    "options": device_type_options,
                    "mode": "dropdown",
                }
            }),
        })

        return self.async_show_form(
            step_id="smartlife_select_device_type",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_name": current_device.name,
                "product_name": current_device.product_name or "Unknown",
                "product_id": current_device.product_id or "Unknown",
                "category": current_device.category or "Unknown",
                "hint": (
                    "This device was detected as a KKT Kolbe product but is not yet "
                    "in our database. Please select the closest matching device type."
                ),
            },
        )

    async def _async_create_smartlife_entries(self) -> ConfigFlowResult:
        """Create config entries for selected SmartLife devices.

        Implements the Parent-Child Entry Pattern:
        1. Creates or reuses Account Entry (parent) for central token storage
        2. Creates Device Entry (child) linked to the account

        The Account Entry is created programmatically first, then the Device Entry
        is returned via async_create_entry().
        """

        from homeassistant.config_entries import SOURCE_USER
        from homeassistant.config_entries import ConfigEntry

        if not self._smartlife_client or not self._smartlife_auth_result:
            _LOGGER.error("SmartLife client not initialized - cannot create entries")
            return self.async_abort(reason="smartlife_not_authenticated")

        # Get token info for storage
        token_info = self._smartlife_client.get_token_info_for_storage()
        user_id = self._smartlife_auth_result.user_id

        # =====================================================================
        # Step 1: Find or create Account Entry (Parent)
        # =====================================================================
        parent_entry_id = None
        account_unique_id = f"smartlife_account_{user_id}"

        # Check if account entry already exists for this user
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.unique_id == account_unique_id:
                # Account already exists - use it as parent
                parent_entry_id = entry.entry_id
                _LOGGER.info(
                    "Using existing SmartLife account entry: %s (%s)",
                    entry.title, parent_entry_id[:8]
                )

                # Update tokens in existing entry
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_SMARTLIFE_TOKEN_INFO: token_info,
                    }
                )
                break

        if parent_entry_id is None:
            # Create new Account Entry programmatically
            account_data = {
                "entry_type": ENTRY_TYPE_ACCOUNT,
                "setup_mode": SETUP_MODE_SMARTLIFE,
                CONF_SMARTLIFE_USER_CODE: self._smartlife_user_code,
                CONF_SMARTLIFE_APP_SCHEMA: self._smartlife_app_schema,
                CONF_SMARTLIFE_TOKEN_INFO: token_info,
            }

            # Create ConfigEntry for account (HA 2025.x compatible)
            # IMPORTANT: version must match VERSION = 2 at class level
            account_entry = ConfigEntry(
                version=2,
                minor_version=1,
                domain=DOMAIN,
                title=f"SmartLife Account ({self._smartlife_user_code[:8]}...)",
                data=account_data,
                source=SOURCE_USER,
                options={},
                unique_id=account_unique_id,
                discovery_keys={},  # Required in HA 2024.12+
                subentries_data={},  # Required in HA 2024.12+
            )

            # Add entry to Home Assistant
            await self.hass.config_entries.async_add(account_entry)
            parent_entry_id = account_entry.entry_id

            _LOGGER.info(
                "Created SmartLife account entry: %s (%s)",
                account_entry.title, parent_entry_id[:8]
            )

        # =====================================================================
        # Step 2: Create Device Entry (Child)
        # =====================================================================

        # Get the selected device (single-select, so only one)
        device_id = self._smartlife_selected_devices[0] if self._smartlife_selected_devices else None

        if not device_id:
            return self.async_abort(reason="no_devices_selected")

        # Find the device in our list
        device = None
        for d in self._smartlife_devices:
            if d.device_id == device_id:
                device = d
                break

        if not device:
            _LOGGER.error("Selected device %s not found in device list", device_id[:8])
            return self.async_abort(reason="device_not_found")

        # Determine device type
        device_type = device.kkt_device_type or "default_hood"
        product_name = device.kkt_product_name or device.product_name or "KKT Device"

        # Get friendly name from KNOWN_DEVICES
        if device_type in KNOWN_DEVICES:
            friendly_type = KNOWN_DEVICES[device_type].get("name", device_type)
        else:
            friendly_type = product_name

        # Set unique ID for this device
        await self.async_set_unique_id(device_id)
        self._abort_if_unique_id_configured()

        # Build device entry data
        device_data: dict[str, Any] = {
            "entry_type": ENTRY_TYPE_DEVICE,
            "setup_mode": SETUP_MODE_SMARTLIFE,
            "parent_entry_id": parent_entry_id,  # Link to Account Entry
            "device_id": device.device_id,
            "device_name": device.name,
            "local_key": device.local_key or "",
            "category": device.category,
            "product_id": device.product_id,
            "product_name": device.kkt_device_type or device.product_id,
            "device_type": device_type,
            "icon_url": getattr(device, "icon", None),  # Tuya device icon URL
        }

        # Try to get LOCAL IP from UDP discovery (SmartLife API returns PUBLIC IP)
        local_ip = None
        discovered_devices = get_discovered_devices()
        if discovered_devices and device.device_id in discovered_devices:
            discovered = discovered_devices[device.device_id]
            local_ip = discovered.get("ip")
            _LOGGER.info(
                "Using discovered local IP %s for device %s (API had %s)",
                local_ip, device.device_id[:8], device.ip
            )

        # Use local IP if found, otherwise fall back to API IP (might be public)
        if local_ip:
            device_data[CONF_IP_ADDRESS] = local_ip
        elif device.ip and _is_private_ip(device.ip):
            # Only use API IP if it's actually a private IP
            device_data[CONF_IP_ADDRESS] = device.ip
        else:
            _LOGGER.warning(
                "No local IP found for device %s - local communication may not work",
                device.device_id[:8]
            )

        # Note: Tokens are stored in Account Entry only (not duplicated in device)
        # Device Entry references parent_entry_id to get tokens when needed

        default_options = {
            "enable_advanced_entities": True,
            "enable_debug_logging": False,
        }

        _LOGGER.info(
            "Creating SmartLife device entry: %s (parent: %s)",
            friendly_type, parent_entry_id[:8]
        )

        return self.async_create_entry(
            title=friendly_type,
            data=device_data,
            options=default_options,
        )

    # =========================================================================
    # End of SmartLife Flow
    # =========================================================================

    async def async_step_reauth(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle reauthentication for API credentials."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        if not self._reauth_entry:
            return self.async_abort(reason="reauth_failed")

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
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
                ip_addr = str(self._reauth_entry.data.get("ip_address", ""))
                dev_id = str(self._reauth_entry.data.get("device_id", ""))
                local_key_val = str(user_input["local_key"]) if user_input.get("local_key") else ""
                if await self._test_device_connection(ip_addr, dev_id, local_key_val):
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
        else:
            # Local key reauth
            reauth_schema = vol.Schema({
                vol.Required("local_key"): selector.selector({"text": {"type": "password"}}),
            })

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
                    if isinstance(product_names, list) and product_names:
                        new_data["product_name"] = str(product_names[0])

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
                                api_manager.store_api_credentials(client_id, client_secret, endpoint)
                            else:
                                errors["base"] = "api_connection_failed"
                    except Exception as err:
                        _LOGGER.error(f"API test failed: {err}")
                        errors["base"] = "api_connection_failed"
            else:
                # Disable API
                new_data["api_enabled"] = False
                new_data["integration_mode"] = "manual"
                # Keep credentials in case user re-enables later

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
                        if isinstance(product_names, list) and product_names:
                            new_data["product_name"] = str(product_names[0])

                # Update API settings
                new_data["api_enabled"] = api_enabled
                if api_enabled:
                    client_id = user_input.get("api_client_id", "").strip()
                    client_secret = user_input.get("api_client_secret", "").strip()
                    endpoint = user_input.get("api_endpoint", "https://openapi.tuyaeu.com")

                    if client_id and client_secret:
                        # Test API
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
                "hint": "Leave password fields empty to keep current values",
            },
        )

    async def async_step_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
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
                    self._device_info["source"] = "discovery"
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
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if user wants to go back to discovery
            if user_input.get("back_to_discovery"):
                return await self.async_step_discovery()

            # Validate input format (without local_key)
            validation_errors = await self._validate_manual_input(user_input)
            if not validation_errors:
                device_type = str(user_input.get("device_type", "auto"))
                device_id_val = str(user_input.get("device_id", ""))

                # Check KNOWN_DEVICES first (from device_types.py)
                if device_type in KNOWN_DEVICES:
                    known_device = KNOWN_DEVICES[device_type]
                    device_name = str(known_device.get("name", device_type))
                    device_category = known_device.get("category", "")
                    is_cooktop = device_category == CATEGORY_COOKTOP
                    category = "Induction Cooktop" if is_cooktop else "Range Hood"
                    # Use first product_name for internal identification
                    pnames = known_device.get("product_names", [])
                    product_name_internal = str(pnames[0]) if isinstance(pnames, list) and pnames else device_type
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
                    "device_id": device_id_val,
                    "name": f"KKT Kolbe {device_name} {device_id_val[:8]}",
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
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
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
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle device selection from API discovery."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input.get("retry_discovery"):
                return await self.async_step_api_only()

            selected_device_id = str(user_input.get("selected_device", ""))
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
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
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
                        if creds:
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
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
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
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle authentication step - local key input and validation."""
        errors: dict[str, str] = {}

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

            local_key = str(user_input.get("local_key", ""))
            test_connection = user_input.get("test_connection", True)

            # Store local key
            self._local_key = local_key

            # Test connection if requested
            if test_connection:
                ip_addr = str(self._device_info.get("ip", ""))
                dev_id = str(self._device_info.get("device_id", ""))
                connection_valid = await self._test_device_connection(
                    ip_addr, dev_id, local_key
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
            vol.Required("local_key", default=default_local_key): selector.selector({
                "text": {"type": "password"}
            }),
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
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
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
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle confirmation and create config entry."""
        if user_input is not None:
            # Check if user wants to go back to settings
            if user_input.get("back_to_settings"):
                return await self.async_step_settings()

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

            # Check if we have API credentials stored
            api_manager = GlobalAPIManager(self.hass)
            has_api = api_manager.has_stored_credentials()

            config_data = {
                CONF_IP_ADDRESS: self._device_info["ip"],
                "device_id": self._device_info["device_id"],
                "local_key": self._local_key,
                "product_name": self._device_info.get("product_name", "auto"),
                "device_type": self._device_info.get("device_type", "auto"),
                "product_id": self._device_info.get("product_id"),
                "integration_mode": "hybrid" if has_api else "manual",
                "icon_url": self._device_info.get("icon_url"),  # Tuya device icon
            }

            # Store API credentials if available (for persistence after restart)
            if has_api:
                creds = api_manager.get_stored_api_credentials()
                if creds:
                    config_data["api_enabled"] = True
                    config_data["api_client_id"] = creds["client_id"]
                    config_data["api_client_secret"] = creds["client_secret"]
                    config_data["api_endpoint"] = creds["endpoint"]
                    _LOGGER.info("Confirmation: API credentials stored in config entry for persistence")

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
            result = await device.async_test_connection()
            return bool(result)

        except Exception as exc:
            _LOGGER.debug("Connection test failed: %s", exc)
            return False

