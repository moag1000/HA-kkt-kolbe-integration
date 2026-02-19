"""Options flow for KKT Kolbe integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import OptionsFlow
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from ..const import DOMAIN
from ..const import ENTRY_TYPE_ACCOUNT
from ..const import SETUP_MODE_SMARTLIFE
from ..helpers import get_options_schema
from ..helpers import validate_api_credentials

_LOGGER = logging.getLogger(__name__)


class KKTKolbeOptionsFlow(OptionsFlow):
    """Handle KKT Kolbe options flow."""

    def __init__(self):
        """Initialize options flow."""
        # No longer store config_entry manually - use self.config_entry property
        # This property is automatically provided by the OptionsFlow parent class
        pass

    async def async_step_init(
        self, user_input: dict[str, Any | None] | None = None
    ) -> FlowResult:
        """Manage the options - routes to appropriate step based on entry type."""
        # Determine entry type
        entry_type = self.config_entry.data.get("entry_type")
        setup_mode = self.config_entry.data.get("setup_mode")

        # SmartLife Account Entry - minimal options
        if entry_type == ENTRY_TYPE_ACCOUNT:
            return await self.async_step_smartlife_account(user_input)

        # SmartLife Device Entry - device options without IoT Platform API
        if setup_mode == SETUP_MODE_SMARTLIFE:
            return await self.async_step_smartlife_device(user_input)

        # Manual/IoT Platform Device Entry - full options
        return await self.async_step_device(user_input)

    async def async_step_smartlife_account(
        self, user_input: dict[str, Any | None] | None = None
    ) -> FlowResult:
        """Options for SmartLife Account entries - menu based."""
        if user_input is not None:
            # Handle menu selection
            if user_input.get("next_step_id") == "renew_token":
                return await self.async_step_renew_token()
            elif user_input.get("next_step_id") == "account_settings":
                return await self.async_step_account_settings()

        # Show menu with options
        return self.async_show_menu(
            step_id="smartlife_account",
            menu_options=["renew_token", "account_settings"],
            description_placeholders={
                "account_name": self.config_entry.title,
            }
        )

    async def async_step_account_settings(
        self, user_input: dict[str, Any | None] | None = None
    ) -> FlowResult:
        """Settings for SmartLife Account entries."""
        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Optional(
                "enable_debug_logging",
                default=self.config_entry.options.get("enable_debug_logging", False)
            ): bool,
        })

        return self.async_show_form(
            step_id="account_settings",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "account_name": self.config_entry.title,
            }
        )

    async def async_step_renew_token(
        self, user_input: dict[str, Any | None] | None = None
    ) -> FlowResult:
        """Renew SmartLife token via QR code scan."""
        errors: dict[str, str] = {}

        # Initialize QR code generation
        if not hasattr(self, "_qr_code_url") or self._qr_code_url is None:
            try:
                from ..clients.tuya_sharing_client import TuyaSharingClient
                from ..const import SMARTLIFE_SCHEMA

                # Get user_code from config entry
                user_code = self.config_entry.data.get("smartlife_user_code", "")
                if not user_code:
                    errors["base"] = "qr_code_failed"
                    _LOGGER.error("No user_code found in config entry for token renewal")
                else:
                    # Create new client for QR code generation
                    self._smartlife_client = TuyaSharingClient(
                        self.hass, user_code=user_code, app_schema=SMARTLIFE_SCHEMA
                    )
                    # Generate QR code - returns string like "tuyaSmart--qrLogin?token=xxx"
                    from urllib.parse import quote
                    qr_code_string = await self._smartlife_client.async_generate_qr_code()
                    # Convert to QR code image URL using qrserver.com API
                    encoded_qr = quote(qr_code_string, safe="")
                    self._qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={encoded_qr}"
                    _LOGGER.info("QR code generated for token renewal, token length: %d", len(qr_code_string))

            except Exception as err:
                errors["base"] = "qr_code_failed"
                _LOGGER.error("Failed to generate QR code: %s", err)

        if user_input is not None:
            # User clicked "I scanned the QR code"
            try:
                # Poll for authentication result
                auth_result = await self._smartlife_client.async_poll_login_result()

                if auth_result.success:
                    # Get new token info
                    new_token_info = self._smartlife_client.get_token_info_for_storage()

                    # Update config entry with new tokens
                    new_data = dict(self.config_entry.data)
                    new_data["smartlife_token_info"] = new_token_info

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )

                    _LOGGER.info("SmartLife tokens successfully renewed")

                    # Clean up
                    self._qr_code_url = None
                    self._smartlife_client = None

                    # Reload the integration to use new tokens
                    await self.hass.config_entries.async_reload(self.config_entry.entry_id)

                    return self.async_create_entry(title="", data={})
                else:
                    errors["base"] = "auth_failed"
                    _LOGGER.error("Token renewal failed: %s", auth_result.error_message)

            except Exception as err:
                errors["base"] = "auth_failed"
                _LOGGER.error("Token renewal failed: %s", err)

        # Show QR code form or error
        qr_url = getattr(self, "_qr_code_url", None) or ""

        if not qr_url and not errors:
            # QR generation failed but no specific error was set
            errors["base"] = "qr_code_failed"

        return self.async_show_form(
            step_id="renew_token",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={
                "qr_code_url": qr_url if qr_url else "https://via.placeholder.com/200?text=QR+Error",
                "account_name": self.config_entry.title,
            }
        )

    async def async_step_smartlife_device(
        self, user_input: dict[str, Any | None] | None = None
    ) -> FlowResult:
        """Options for SmartLife Device entries (no IoT Platform API options)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            validation_errors = await self._validate_options(user_input)
            if not validation_errors:
                return self.async_create_entry(title="", data=user_input)
            errors.update(validation_errors)

        current_interval = self.config_entry.options.get(CONF_SCAN_INTERVAL, 30)
        current_debug = self.config_entry.options.get("enable_debug_logging", False)
        current_advanced = self.config_entry.options.get("enable_advanced_entities", True)
        current_naming = self.config_entry.options.get("zone_naming_scheme", "zone")
        current_fan_suppress = self.config_entry.options.get("disable_fan_auto_start", False)

        # SmartLife Device schema - NO IoT Platform API fields
        schema = vol.Schema({
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

        return self.async_show_form(
            step_id="smartlife_device",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_name": self.config_entry.title,
                "current_interval": str(current_interval),
            }
        )

    async def async_step_device(
        self, user_input: dict[str, Any | None] | None = None
    ) -> FlowResult:
        """Options for Manual/IoT Platform Device entries (full options)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            validation_errors = await self._validate_options(user_input)
            if not validation_errors:
                return self.async_create_entry(title="", data=user_input)
            errors.update(validation_errors)

        # Get current settings from config_entry
        current_interval = self.config_entry.options.get(CONF_SCAN_INTERVAL, 30)
        current_debug = self.config_entry.options.get("enable_debug_logging", False)
        current_advanced = self.config_entry.options.get("enable_advanced_entities", True)
        current_naming = self.config_entry.options.get("zone_naming_scheme", "zone")
        current_fan_suppress = self.config_entry.options.get("disable_fan_auto_start", False)

        # Get current API settings
        current_api_enabled = self.config_entry.data.get("api_enabled", False)
        current_client_id = self.config_entry.data.get("api_client_id", "")
        current_endpoint = self.config_entry.data.get("api_endpoint", "https://openapi.tuyaeu.com")

        # Build full options schema using helper (includes IoT Platform API)
        options_schema = get_options_schema(
            current_interval=current_interval,
            current_debug=current_debug,
            current_advanced=current_advanced,
            current_naming=current_naming,
            current_api_enabled=current_api_enabled,
            current_client_id=current_client_id,
            current_endpoint=current_endpoint,
            current_fan_suppress=current_fan_suppress,
        )

        return self.async_show_form(
            step_id="device",
            data_schema=options_schema,
            errors=errors,
            description_placeholders={
                "device_name": self.config_entry.title,
                "current_interval": str(current_interval),
            }
        )

    async def _validate_options(self, options: dict[str, Any]) -> dict[str, str]:
        """Validate options.

        Args:
            options: User-provided options.

        Returns:
            Dictionary of field names to error keys.
        """
        errors: dict[str, str] = {}

        # Handle new local key update
        new_local_key = options.get("new_local_key", "").strip()
        if new_local_key:
            key_errors = await self._validate_and_update_local_key(new_local_key)
            errors.update(key_errors)

        # Handle API settings update
        api_enabled = options.get("api_enabled", False)
        if api_enabled:
            api_errors = await self._validate_and_update_api_settings(options)
            errors.update(api_errors)

        # Test connection if requested
        if options.get("test_connection", False) and not errors:
            test_errors = await self._test_connection()
            errors.update(test_errors)

        return errors

    async def _validate_and_update_local_key(self, new_local_key: str) -> dict[str, str]:
        """Validate and update local key.

        Args:
            new_local_key: New local key to validate.

        Returns:
            Dictionary of errors if any.
        """
        errors: dict[str, str] = {}

        # Validate local key format (16 characters)
        if len(new_local_key) != 16:
            errors["new_local_key"] = "invalid_local_key_length"
            return errors

        # Test the new local key
        try:
            device_id = (
                self.config_entry.data.get(CONF_DEVICE_ID) or
                self.config_entry.data.get("device_id")
            )
            ip_address = (
                self.config_entry.data.get(CONF_IP_ADDRESS) or
                self.config_entry.data.get("ip_address") or
                self.config_entry.data.get("host")
            )

            if not device_id or not ip_address:
                errors["new_local_key"] = "missing_device_info"
                return errors

            # Test connection with new key
            from ..tuya_device import KKTKolbeTuyaDevice

            test_device = KKTKolbeTuyaDevice(
                device_id=device_id,
                ip_address=ip_address,
                local_key=new_local_key,
                hass=self.hass,
            )

            if await test_device.async_test_connection():
                # Update the config entry with new local key
                new_data = dict(self.config_entry.data)
                new_data[CONF_ACCESS_TOKEN] = new_local_key
                new_data["local_key"] = new_local_key

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
                        "force_reconnect": True,
                    }
                )

                _LOGGER.info(f"Local key successfully updated for device {device_id}")
            else:
                errors["new_local_key"] = "local_key_test_failed"

        except Exception as exc:
            errors["new_local_key"] = "local_key_test_failed"
            _LOGGER.error(f"Local key test failed: {exc}")

        return errors

    async def _validate_and_update_api_settings(
        self, options: dict[str, Any]
    ) -> dict[str, str]:
        """Validate and update API settings.

        Args:
            options: User-provided options containing API settings.

        Returns:
            Dictionary of errors if any.
        """
        errors: dict[str, str] = {}

        client_id = options.get("api_client_id", "").strip()
        client_secret = options.get("api_client_secret", "").strip()

        # Validate credentials format using helper
        validation_errors = validate_api_credentials({
            "api_client_id": client_id,
            "api_client_secret": client_secret,
        })

        if validation_errors:
            return validation_errors

        # Test API connection
        try:
            from ..api import TuyaCloudClient

            api_client = TuyaCloudClient(
                client_id=client_id,
                client_secret=client_secret,
                endpoint=options.get("api_endpoint", "https://openapi.tuyaeu.com"),
            )

            async with api_client:
                if await api_client.test_connection():
                    # Update config entry with API settings
                    device_id = (
                        self.config_entry.data.get(CONF_DEVICE_ID) or
                        self.config_entry.data.get("device_id")
                    )
                    new_data = dict(self.config_entry.data)
                    new_data["api_enabled"] = True
                    new_data["api_client_id"] = client_id
                    new_data["api_client_secret"] = client_secret
                    new_data["api_endpoint"] = options.get(
                        "api_endpoint", "https://openapi.tuyaeu.com"
                    )

                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=new_data
                    )
                    _LOGGER.info(f"API credentials updated for device {device_id}")
                else:
                    errors["api_client_secret"] = "api_test_failed"

        except Exception as exc:
            errors["api_client_secret"] = "api_test_failed"
            _LOGGER.error(f"API test failed: {exc}")

        return errors

    async def _test_connection(self) -> dict[str, str]:
        """Test current connection to device.

        Returns:
            Dictionary of errors if any.
        """
        errors: dict[str, str] = {}

        try:
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]["coordinator"]
            await coordinator.async_refresh()

            if not coordinator.last_update_success:
                errors["base"] = "connection_test_failed"

        except Exception as exc:
            errors["base"] = "connection_test_failed"
            _LOGGER.debug("Connection test failed: %s", exc)

        return errors
