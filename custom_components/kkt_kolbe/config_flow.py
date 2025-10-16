"""Config flow for KKT Kolbe Dunstabzugshaube integration."""
import logging
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_DEVICE_ID,
    CONF_ACCESS_TOKEN,
    CONF_TYPE,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from . import DOMAIN
from .discovery import get_discovered_devices

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Required(CONF_ACCESS_TOKEN): str,
        vol.Optional(CONF_TYPE, default="auto"): vol.In(["auto", "hood", "cooktop"]),
        vol.Optional(CONF_NAME, default="KKT Kolbe Device"): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    # Test connection with Tuya device
    from .tuya_device import KKTKolbeTuyaDevice

    try:
        device = KKTKolbeTuyaDevice(
            device_id=data[CONF_DEVICE_ID],
            ip_address=data[CONF_HOST],
            local_key=data[CONF_ACCESS_TOKEN],
        )
        status = device.update_status()
        if not status:
            raise Exception("Could not connect to device")
    except Exception as e:
        _LOGGER.error(f"Connection test failed: {e}")
        raise

    # Auto-detect device type if set to auto
    if data.get(CONF_TYPE) == "auto":
        # Try to determine from device response
        # This would need actual device query
        pass

    return {"title": data[CONF_NAME]}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KKT Kolbe."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._discovered_devices = {}
        self._selected_device = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        # Check for discovered devices first
        self._discovered_devices = get_discovered_devices()

        if self._discovered_devices:
            return await self.async_step_discovery()
        else:
            return await self.async_step_manual()

    async def async_step_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle discovered devices."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input.get("device") == "manual":
                return await self.async_step_manual()

            # User selected a discovered device
            device_id = user_input["device"]
            device_info = self._discovered_devices[device_id]

            # Still need local key from user
            self._selected_device = device_info
            return await self.async_step_credentials()

        # Create device selection schema
        device_options = {}
        for device_id, device_info in self._discovered_devices.items():
            name = device_info.get("product_name", device_info.get("name", device_id))
            host = device_info.get("host", "unknown")
            device_options[device_id] = f"{name} ({host})"

        device_options["manual"] = "Manual configuration"

        discovery_schema = vol.Schema({
            vol.Required("device"): vol.In(device_options)
        })

        return self.async_show_form(
            step_id="discovery",
            data_schema=discovery_schema,
            errors=errors,
            description_placeholders={
                "devices_found": str(len(self._discovered_devices))
            }
        )

    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle credentials for discovered device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Combine discovered info with user credentials
                device_config = {
                    CONF_HOST: self._selected_device["host"],
                    CONF_DEVICE_ID: self._selected_device["device_id"],
                    CONF_ACCESS_TOKEN: user_input[CONF_ACCESS_TOKEN],
                    CONF_NAME: user_input.get(CONF_NAME, self._selected_device.get("product_name", "KKT Kolbe Device")),
                    CONF_TYPE: self._selected_device.get("device_type", "auto"),
                }

                info = await validate_input(self.hass, device_config)
                return self.async_create_entry(title=info["title"], data=device_config)
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        credentials_schema = vol.Schema({
            vol.Required(CONF_ACCESS_TOKEN): str,
            vol.Optional(CONF_NAME, default=self._selected_device.get("product_name", "KKT Kolbe Device")): str,
        })

        return self.async_show_form(
            step_id="credentials",
            data_schema=credentials_schema,
            errors=errors,
            description_placeholders={
                "device_name": self._selected_device.get("product_name", "Unknown"),
                "device_host": self._selected_device.get("host", "Unknown"),
                "device_id": self._selected_device.get("device_id", "Unknown")[:10] + "...",
            }
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="manual", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )