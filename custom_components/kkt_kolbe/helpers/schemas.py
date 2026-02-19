"""Schema definitions for KKT Kolbe config flows."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers import selector

# Import get_device_type_options from device_detection to avoid duplication
from .device_detection import get_device_type_options

# API Endpoint options - reusable across all flows
API_ENDPOINTS = {
    "https://openapi.tuyaeu.com": "Europe (EU)",
    "https://openapi.tuyaus.com": "United States (US)",
    "https://openapi.tuyacn.com": "China (CN)",
    "https://openapi.tuyain.com": "India (IN)",
}

API_ENDPOINT_OPTIONS = [
    {"value": endpoint, "label": label}
    for endpoint, label in API_ENDPOINTS.items()
]

DEFAULT_API_ENDPOINT = "https://openapi.tuyaeu.com"


# =============== MANUAL SETUP SCHEMA ===============

def get_manual_schema() -> vol.Schema:
    """Get schema for manual device configuration.

    Returns:
        Schema with IP address, device ID, and device type selector.
    """
    return vol.Schema({
        vol.Required(CONF_IP_ADDRESS): str,
        vol.Required("device_id"): str,
        vol.Required("device_type"): selector.selector({
            "select": {
                "options": get_device_type_options(),
                "mode": "dropdown",
                "translation_key": "device_type"
            }
        })
    })


# =============== AUTHENTICATION SCHEMA ===============

def get_authentication_schema(
    include_back_option: bool = True,
    include_test_option: bool = True,
) -> vol.Schema:
    """Get schema for local key authentication.

    Args:
        include_back_option: Whether to include back navigation option.
        include_test_option: Whether to include connection test option.

    Returns:
        Schema for local key entry.
    """
    schema_dict: dict[Any, Any] = {
        vol.Required("local_key"): str,
    }

    if include_test_option:
        schema_dict[vol.Optional("test_connection", default=True)] = bool

    if include_back_option:
        schema_dict[vol.Optional("back_to_previous", default=False)] = bool

    return vol.Schema(schema_dict)


# =============== API CREDENTIALS SCHEMA ===============

def get_api_credentials_schema(
    default_endpoint: str = DEFAULT_API_ENDPOINT,
    include_enable_toggle: bool = False,
    current_client_id: str = "",
    show_secret_hint: bool = False,
) -> vol.Schema:
    """Get schema for API credentials configuration.

    Args:
        default_endpoint: Default API endpoint to select.
        include_enable_toggle: Whether to include api_enabled toggle.
        current_client_id: Pre-fill client ID if available.
        show_secret_hint: If True, use Optional for secret (keep current).

    Returns:
        Schema for API credentials.
    """
    schema_dict: dict[Any, Any] = {}

    if include_enable_toggle:
        schema_dict[vol.Required("api_enabled", default=False)] = bool

    # Client ID
    if current_client_id:
        schema_dict[vol.Required("api_client_id", default=current_client_id)] = str
    else:
        schema_dict[vol.Required("api_client_id")] = selector.selector({
            "text": {}
        })

    # Client Secret
    if show_secret_hint:
        schema_dict[vol.Optional("api_client_secret", default="")] = selector.selector({
            "text": {"type": "password"}
        })
    else:
        schema_dict[vol.Required("api_client_secret")] = selector.selector({
            "text": {"type": "password"}
        })

    # Endpoint
    schema_dict[vol.Required("api_endpoint", default=default_endpoint)] = selector.selector({
        "select": {
            "options": API_ENDPOINT_OPTIONS,
            "mode": "dropdown"
        }
    })

    return vol.Schema(schema_dict)


# =============== SETTINGS SCHEMA ===============

def get_settings_schema(
    device_type: str | None = None,
    include_back_option: bool = True,
) -> vol.Schema:
    """Get settings schema based on device type.

    Args:
        device_type: Device type key for conditional options.
        include_back_option: Whether to include back navigation.

    Returns:
        Schema for device settings.
    """
    schema_dict: dict[Any, Any] = {
        vol.Optional("update_interval", default=30): selector.selector({
            "number": {
                "min": 10,
                "max": 300,
                "step": 5,
                "unit_of_measurement": "seconds",
                "mode": "slider"
            }
        }),
        vol.Optional("enable_debug_logging", default=False): bool,
        vol.Optional("enable_advanced_entities", default=True): bool,
    }

    # Additional options for induction cooktops
    if device_type in ["ind7705hc", "ind7705hc_cooktop", "induction_cooktop"]:
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

    if include_back_option:
        schema_dict[vol.Optional("back_to_authentication", default=False)] = bool

    return vol.Schema(schema_dict)


# =============== DEVICE SELECTION SCHEMA ===============

def get_device_selection_schema(
    discovered_devices: dict[str, dict[str, Any]],
    include_retry: bool = True,
    include_manual_fallback: bool = True,
) -> vol.Schema:
    """Generate device selection schema based on discovered devices.

    Args:
        discovered_devices: Dict of device_id -> device_info from discovery.
        include_retry: Whether to include retry discovery option.
        include_manual_fallback: Whether to include manual config option.

    Returns:
        Schema for device selection.
    """
    if not discovered_devices:
        schema_dict: dict[Any, Any] = {}
        if include_retry:
            schema_dict[vol.Optional("retry_discovery", default=False)] = bool
        if include_manual_fallback:
            schema_dict[vol.Optional("use_manual_config", default=False)] = bool
        return vol.Schema(schema_dict)

    device_options = []
    for device_id, device in discovered_devices.items():
        # Use friendly_type if available, then device name, then fallback
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

    schema_dict = {
        vol.Required("selected_device"): selector.selector({
            "select": {
                "options": device_options,
                "mode": "dropdown"
            }
        }),
    }

    if include_retry:
        schema_dict[vol.Optional("retry_discovery", default=False)] = bool
    if include_manual_fallback:
        schema_dict[vol.Optional("use_manual_config", default=False)] = bool

    return vol.Schema(schema_dict)


# =============== SMART DISCOVERY SCHEMA ===============

def get_smart_discovery_schema(
    device_options: list[dict[str, str]],
    show_empty_state: bool = False,
) -> vol.Schema:
    """Get schema for smart discovery device selection.

    Args:
        device_options: List of device options with 'value' and 'label' keys.
        show_empty_state: Whether to show empty state (no devices found).

    Returns:
        Schema for smart discovery selection.
    """
    schema_dict: dict[Any, Any] = {}

    if not show_empty_state and device_options:
        schema_dict[vol.Required("selected_device")] = selector.selector({
            "select": {
                "options": device_options,
                "mode": "dropdown",
            }
        })

    schema_dict[vol.Optional("retry_discovery", default=False)] = bool
    schema_dict[vol.Optional("back_to_user", default=False)] = bool

    return vol.Schema(schema_dict)


# =============== CONFIRMATION SCHEMA ===============

def get_confirmation_schema() -> vol.Schema:
    """Get schema for final confirmation step.

    Returns:
        Schema with confirm and back options.
    """
    return vol.Schema({
        vol.Optional("confirm", default=False): bool,
        vol.Optional("back_to_settings", default=False): bool,
    })


# =============== RECONFIGURE SCHEMAS ===============

def get_reconfigure_menu_schema() -> vol.Schema:
    """Get schema for reconfigure menu options.

    Returns:
        Schema with reconfigure option selector.
    """
    return vol.Schema({
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


def get_reconfigure_connection_schema(
    current_ip: str = "",
) -> vol.Schema:
    """Get schema for reconfiguring connection settings.

    Args:
        current_ip: Current IP address to pre-fill.

    Returns:
        Schema for connection reconfiguration.
    """
    return vol.Schema({
        vol.Optional("ip_address", default=current_ip): str,
        vol.Optional("local_key", default=""): selector.selector({
            "text": {"type": "password"}
        }),
        vol.Optional("test_connection", default=True): bool,
    })


def get_reconfigure_device_type_schema(
    current_device_type: str = "auto",
) -> vol.Schema:
    """Get schema for reconfiguring device type.

    Args:
        current_device_type: Current device type to pre-select.

    Returns:
        Schema for device type reconfiguration.
    """
    return vol.Schema({
        vol.Required("device_type", default=current_device_type): selector.selector({
            "select": {
                "options": get_device_type_options(),
                "mode": "dropdown",
            }
        }),
    })


def get_reconfigure_api_schema(
    current_api_enabled: bool = False,
    current_client_id: str = "",
    current_endpoint: str = DEFAULT_API_ENDPOINT,
) -> vol.Schema:
    """Get schema for reconfiguring API settings.

    Args:
        current_api_enabled: Whether API is currently enabled.
        current_client_id: Current API client ID.
        current_endpoint: Current API endpoint.

    Returns:
        Schema for API reconfiguration.
    """
    return vol.Schema({
        vol.Required("api_enabled", default=current_api_enabled): bool,
        vol.Optional("api_client_id", default=current_client_id): str,
        vol.Optional("api_client_secret", default=""): selector.selector({
            "text": {"type": "password"}
        }),
        vol.Optional("api_endpoint", default=current_endpoint): selector.selector({
            "select": {
                "options": API_ENDPOINT_OPTIONS,
                "mode": "dropdown",
            }
        }),
    })


def get_reconfigure_all_schema(
    current_ip: str = "",
    current_device_type: str = "auto",
    current_api_enabled: bool = False,
    current_client_id: str = "",
    current_endpoint: str = DEFAULT_API_ENDPOINT,
) -> vol.Schema:
    """Get schema for reconfiguring all settings.

    Args:
        current_ip: Current IP address.
        current_device_type: Current device type.
        current_api_enabled: Whether API is enabled.
        current_client_id: Current API client ID.
        current_endpoint: Current API endpoint.

    Returns:
        Schema for full reconfiguration.
    """
    return vol.Schema({
        vol.Optional("ip_address", default=current_ip): str,
        vol.Optional("local_key", default=""): selector.selector({
            "text": {"type": "password"}
        }),
        vol.Required("device_type", default=current_device_type): selector.selector({
            "select": {
                "options": get_device_type_options(),
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
                "options": API_ENDPOINT_OPTIONS,
                "mode": "dropdown",
            }
        }),
        vol.Optional("test_connection", default=True): bool,
    })


def get_reconfigure_schemas(
    current_ip: str = "",
    current_device_type: str = "auto",
    current_api_enabled: bool = False,
    current_client_id: str = "",
    current_endpoint: str = DEFAULT_API_ENDPOINT,
) -> dict[str, vol.Schema]:
    """Get all reconfigure schemas as a dictionary.

    Convenience function to get all reconfigure schemas at once.

    Args:
        All current values for pre-filling schemas.

    Returns:
        Dict mapping schema names to Schema objects.
    """
    return {
        "menu": get_reconfigure_menu_schema(),
        "connection": get_reconfigure_connection_schema(current_ip),
        "device_type": get_reconfigure_device_type_schema(current_device_type),
        "api": get_reconfigure_api_schema(
            current_api_enabled, current_client_id, current_endpoint
        ),
        "all": get_reconfigure_all_schema(
            current_ip, current_device_type, current_api_enabled,
            current_client_id, current_endpoint
        ),
    }


# =============== OPTIONS FLOW SCHEMA ===============

def get_options_schema(
    current_interval: int = 30,
    current_debug: bool = False,
    current_advanced: bool = True,
    current_naming: str = "zone",
    current_api_enabled: bool = False,
    current_client_id: str = "",
    current_endpoint: str = DEFAULT_API_ENDPOINT,
    current_fan_suppress: bool = False,
) -> vol.Schema:
    """Get schema for options flow.

    Args:
        All current values for pre-filling the options form.

    Returns:
        Schema for options configuration.
    """
    return vol.Schema({
        vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): selector.selector({
            "number": {
                "min": 10,
                "max": 300,
                "step": 5,
                "unit_of_measurement": "seconds",
                "mode": "slider"
            }
        }),
        vol.Optional("new_local_key", default=""): selector.selector({
            "text": {"type": "password"}
        }),
        vol.Optional("api_enabled", default=current_api_enabled): bool,
        vol.Optional("api_client_id", default=current_client_id): selector.selector({
            "text": {}
        }),
        vol.Optional("api_client_secret", default=""): selector.selector({
            "text": {"type": "password"}
        }),
        vol.Optional("api_endpoint", default=current_endpoint): selector.selector({
            "select": {
                "options": API_ENDPOINT_OPTIONS,
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
        vol.Optional("disable_fan_auto_start", default=current_fan_suppress): bool,
        vol.Optional("test_connection", default=True): bool,
    })


# =============== ZEROCONF SCHEMAS ===============

def get_zeroconf_authenticate_schema(
    has_api: bool = False,
) -> vol.Schema:
    """Get schema for zeroconf authentication step.

    Args:
        has_api: Whether API credentials are already configured.

    Returns:
        Schema for zeroconf local key entry.
    """
    if has_api:
        # API is already configured, just show local key field
        return vol.Schema({
            vol.Required("local_key"): str,
        })
    else:
        # No API configured - offer both options
        return vol.Schema({
            vol.Optional("local_key"): str,
            vol.Optional("configure_api", default=False): bool,
        })
