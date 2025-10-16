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

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info["title"], data=user_input)
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )