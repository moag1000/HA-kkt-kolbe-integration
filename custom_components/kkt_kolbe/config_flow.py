"""Config flow for KKT Kolbe integration."""
import asyncio
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow, ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN
from .discovery import async_start_discovery, async_stop_discovery, get_discovered_devices
from .tuya_device import KKTKolbeTuyaDevice

_LOGGER = logging.getLogger(__name__)

# Configuration step schemas
STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required("connection_method", default="discovery"): selector.selector({
        "select": {
            "options": [
                {"value": "discovery", "label": "Automatic Discovery"},
                {"value": "manual", "label": "Manual Configuration"}
            ],
            "mode": "dropdown",
            "translation_key": "connection_method"
        }
    })
})

STEP_MANUAL_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_IP_ADDRESS): str,
    vol.Required("device_id"): str,
    vol.Required("device_type"): selector.selector({
        "select": {
            "options": [
                {"value": "hermes_style", "label": "KKT Kolbe HERMES & STYLE (Range Hood)"},
                {"value": "hermes", "label": "KKT Kolbe HERMES (Range Hood)"},
                {"value": "ecco_hcm", "label": "KKT Kolbe ECCO HCM (Range Hood)"},
                {"value": "ind7705hc", "label": "KKT IND7705HC (Induction Cooktop)"}
            ],
            "mode": "dropdown",
            "translation_key": "device_type"
        }
    })
})

def _get_device_selection_schema(discovered_devices: Dict[str, Dict[str, Any]]):
    """Generate device selection schema based on discovered devices."""
    if not discovered_devices:
        return vol.Schema({
            vol.Optional("retry_discovery", default=False): bool,
            vol.Optional("use_manual_config", default=False): bool
        })

    device_options = []
    for device_id, device in discovered_devices.items():
        product_name = device.get("product_name", "Unknown Device")
        device_name = device.get("name", device_id[:8])
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

    def __init__(self):
        """Initialize the config flow."""
        self._discovery_data: Dict[str, Dict[str, Any]] = {}
        self._device_info: Dict[str, Any] = {}
        self._connection_method: Optional[str] = None
        self._local_key: Optional[str] = None
        self._advanced_settings: Dict[str, Any] = {}

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step - connection method selection."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self._connection_method = user_input["connection_method"]

            if self._connection_method == "discovery":
                return await self.async_step_discovery()
            else:
                return await self.async_step_manual()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "setup_mode": "Choose how you want to set up your KKT Kolbe device"
            }
        )

    async def async_step_reauth(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle reauthentication for API credentials."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        if not self._reauth_entry:
            return self.async_abort(reason="reauth_failed")

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle reauthentication confirmation."""
        errors: Dict[str, str] = {}

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

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=reauth_schema,
            errors=errors,
            description_placeholders={
                "device_name": self._reauth_entry.title,
                "device_id": self._reauth_entry.data.get("device_id", "Unknown"),
            }
        )

    async def async_step_discovery(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle device discovery step."""
        errors: Dict[str, str] = {}

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
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle manual configuration step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Check if user wants to go back to discovery
            if user_input.get("back_to_discovery"):
                return await self.async_step_discovery()

            # Validate input format (without local_key)
            validation_errors = await self._validate_manual_input(user_input)
            if not validation_errors:
                device_type = user_input["device_type"]

                # Map device types to proper names
                device_type_mapping = {
                    "hermes_style": "HERMES & STYLE",
                    "hermes": "HERMES",
                    "ecco_hcm": "ECCO HCM",
                    "ind7705hc": "IND7705HC"
                }

                device_name = device_type_mapping.get(device_type, device_type.upper())
                is_cooktop = device_type == "ind7705hc"
                category = "Induction Cooktop" if is_cooktop else "Range Hood"

                self._device_info = {
                    "ip": user_input[CONF_IP_ADDRESS],
                    "device_id": user_input["device_id"],
                    "name": f"KKT Kolbe {device_name} {user_input['device_id']}",
                    "product_name": f"KKT Kolbe {device_name} ({category})",
                    "device_type": device_type
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

    async def async_step_authentication(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle authentication step - local key input and validation."""
        errors: Dict[str, str] = {}

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
        self, user_input: Optional[Dict[str, Any]] = None
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
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle confirmation and create config entry."""
        if user_input is not None:
            # Check if user wants to go back to settings
            if user_input.get("back_to_settings"):
                return await self.async_step_settings()

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

    async def _validate_manual_input(self, user_input: Dict[str, Any]) -> Dict[str, str]:
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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "KKTKolbeOptionsFlow":
        """Get the options flow for this handler."""
        return KKTKolbeOptionsFlow(config_entry)


class KKTKolbeOptionsFlow(OptionsFlow):
    """Handle KKT Kolbe options flow."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize options flow."""
        # Don't store config_entry as instance variable (deprecated)
        # Access it through self.config_entry property instead
        self._entry_id = config_entry.entry_id
        self._entry_data = config_entry.data
        self._entry_options = config_entry.options
        self._entry_title = config_entry.title

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            # Validate options
            validation_errors = await self._validate_options(user_input)
            if not validation_errors:
                return self.async_create_entry(title="", data=user_input)
            else:
                errors.update(validation_errors)

        # Get current settings from stored options
        current_interval = self._entry_options.get(CONF_SCAN_INTERVAL, 30)
        current_debug = self._entry_options.get("enable_debug_logging", False)
        current_advanced = self._entry_options.get("enable_advanced_entities", False)
        current_naming = self._entry_options.get("zone_naming_scheme", "zone")

        options_schema = vol.Schema({
            vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): selector.selector({
                "number": {
                    "min": 10, "max": 300, "step": 5,
                    "unit_of_measurement": "seconds",
                    "mode": "slider"
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
                "device_name": self._entry_title,
                "current_interval": current_interval
            }
        )

    async def _validate_options(self, options: Dict[str, Any]) -> Dict[str, str]:
        """Validate options."""
        errors = {}

        # Test connection if requested
        if options.get("test_connection", False):
            try:
                coordinator = self.hass.data[DOMAIN][self._entry_id]["coordinator"]
                await coordinator.async_refresh()

                if not coordinator.last_update_success:
                    errors["base"] = "connection_test_failed"

            except Exception as exc:
                errors["base"] = "connection_test_failed"
                _LOGGER.debug("Connection test failed: %s", exc)

        return errors