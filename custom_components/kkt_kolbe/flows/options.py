"""Options flow for KKT Kolbe integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import OptionsFlow
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResult

from ..const import DOMAIN
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
        current_advanced = self.config_entry.options.get("enable_advanced_entities", True)
        current_naming = self.config_entry.options.get("zone_naming_scheme", "zone")

        # Get current API settings
        current_api_enabled = self.config_entry.data.get("api_enabled", False)
        current_client_id = self.config_entry.data.get("api_client_id", "")
        current_endpoint = self.config_entry.data.get("api_endpoint", "https://openapi.tuyaeu.com")

        # Build options schema using helper
        options_schema = get_options_schema(
            current_interval=current_interval,
            current_debug=current_debug,
            current_advanced=current_advanced,
            current_naming=current_naming,
            current_api_enabled=current_api_enabled,
            current_client_id=current_client_id,
            current_endpoint=current_endpoint,
        )

        return self.async_show_form(
            step_id="init",
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
