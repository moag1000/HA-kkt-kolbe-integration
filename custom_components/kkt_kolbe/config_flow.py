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
        # Start discovery first if not already running
        from .discovery import async_start_discovery

        _LOGGER.info("Starting KKT Kolbe device discovery...")
        await async_start_discovery(self.hass)

        # Wait for discovery to find devices (with timeout)
        import asyncio
        max_wait = 5  # Maximum 5 seconds
        wait_interval = 0.5  # Check every 500ms

        _LOGGER.info(f"Waiting up to {max_wait}s for device discovery...")

        for i in range(int(max_wait / wait_interval)):
            self._discovered_devices = get_discovered_devices()
            _LOGGER.debug(f"Discovery check {i+1}: Found {len(self._discovered_devices)} devices")
            if self._discovered_devices:
                break
            await asyncio.sleep(wait_interval)

        _LOGGER.info(f"Discovery finished: Found {len(self._discovered_devices)} KKT Kolbe devices")

        if self._discovered_devices:
            return await self.async_step_discovery()
        else:
            return await self.async_step_choose_setup()

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

    async def async_step_choose_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose setup method when no devices discovered."""
        errors: dict[str, str] = {}

        if user_input is not None:
            choice = user_input.get("setup_choice")
            if choice == "manual":
                return await self.async_step_manual()
            elif choice == "test":
                # Add test device for debugging
                from .discovery import add_test_device
                add_test_device()
                self._discovered_devices = get_discovered_devices()
                return await self.async_step_discovery()
            elif choice == "debug":
                return await self.async_step_debug_info()

        setup_schema = vol.Schema({
            vol.Required("setup_choice"): vol.In({
                "manual": "Manual configuration",
                "test": "Add test device (debugging)",
                "debug": "Show debug information"
            })
        })

        return self.async_show_form(
            step_id="choose_setup",
            data_schema=setup_schema,
            errors=errors,
            description_placeholders={
                "reason": "No KKT Kolbe devices found via automatic discovery"
            }
        )

    async def async_step_debug_info(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show debug information about discovery."""
        from .discovery import debug_scan_network

        if user_input is not None:
            return await self.async_step_choose_setup()

        # Scan network for debug info
        network_services = await debug_scan_network()

        debug_info = "mDNS Discovery Debug Information:\n\n"
        from .discovery import TUYA_SERVICE_TYPES
        debug_info += f"Service types scanned: {len(TUYA_SERVICE_TYPES)}\n"
        debug_info += f"Services found in network: {len(network_services)}\n\n"

        for service_type, devices in network_services.items():
            debug_info += f"{service_type}: {len(devices)} devices\n"

        debug_schema = vol.Schema({
            vol.Optional("back", default=True): bool
        })

        return self.async_show_form(
            step_id="debug_info",
            data_schema=debug_schema,
            errors={},
            description_placeholders={
                "debug_info": debug_info
            }
        )