"""Enhanced config flow with TinyTuya API support for KKT Kolbe integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_DEVICE_ID, CONF_HOST, CONF_LOCAL_KEY
from homeassistant.core import callback
from homeassistant.helpers import selector

from .api import TuyaCloudClient, TuyaAPIError, TuyaAuthenticationError
from .api.dynamic_device_factory import DynamicDeviceFactory
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Configuration keys for API
CONF_API_CLIENT_ID = "api_client_id"
CONF_API_CLIENT_SECRET = "api_client_secret"
CONF_API_ENDPOINT = "api_endpoint"
CONF_API_ENABLED = "api_enabled"
CONF_INTEGRATION_MODE = "integration_mode"

# Default values
DEFAULT_API_ENDPOINT = "https://openapi.tuyaeu.com"

# Integration modes
MODE_MANUAL = "manual"
MODE_API_DISCOVERY = "api_discovery"
MODE_HYBRID = "hybrid"


class KKTKolbeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Enhanced configuration flow with API support."""

    VERSION = 2

    def __init__(self):
        """Initialize the config flow."""
        self.api_client: TuyaCloudClient | None = None
        self.discovered_devices: Dict = {}
        self.selected_device: Dict | None = None
        self.integration_mode: str = MODE_MANUAL

    async def async_step_user(
        self, user_input: dict[str, Any | None] = None
    ) -> dict[str, Any]:
        """Handle the initial step - choose integration mode."""
        if user_input is not None:
            self.integration_mode = user_input[CONF_INTEGRATION_MODE]

            if self.integration_mode == MODE_API_DISCOVERY:
                return await self.async_step_api_config()
            elif self.integration_mode == MODE_HYBRID:
                return await self.async_step_api_config()
            else:
                return await self.async_step_manual_config()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_INTEGRATION_MODE, default=MODE_MANUAL): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"value": MODE_MANUAL, "label": "Manual Configuration (Legacy)"},
                            {"value": MODE_API_DISCOVERY, "label": "API Discovery (Recommended)"},
                            {"value": MODE_HYBRID, "label": "Hybrid Mode (API + Manual)"},
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            description_placeholders={
                "manual_desc": "Traditional manual setup with device ID, IP, and local key",
                "api_desc": "Automatic device discovery using Tuya Cloud API",
                "hybrid_desc": "API discovery with manual override options",
            },
        )

    async def async_step_manual_config(
        self, user_input: dict[str, Any | None] = None
    ) -> dict[str, Any]:
        """Handle manual device configuration (legacy mode)."""
        errors = {}

        if user_input is not None:
            # Validate manual configuration
            device_id = user_input[CONF_DEVICE_ID]
            host = user_input[CONF_HOST]
            local_key = user_input[CONF_LOCAL_KEY]

            # Basic validation
            if not all([device_id, host, local_key]):
                errors["base"] = "missing_required_fields"
            else:
                # Set unique_id to prevent duplicate entries (HA standard)
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()

                # Create entry for manual configuration
                config_data = {
                    CONF_DEVICE_ID: device_id,
                    CONF_HOST: host,
                    CONF_LOCAL_KEY: local_key,
                    CONF_API_ENABLED: False,
                    CONF_INTEGRATION_MODE: MODE_MANUAL,
                }

                return self.async_create_entry(
                    title=f"KKT Kolbe Device {device_id}",
                    data=config_data,
                )

        return self.async_show_form(
            step_id="manual_config",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_ID): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_LOCAL_KEY): str,
            }),
            errors=errors,
            description_placeholders={
                "device_id_desc": "20-character device ID from Tuya/Smart Life app",
                "host_desc": "IP address of the device on your network",
                "local_key_desc": "Local encryption key (16 characters)",
            },
        )

    async def async_step_api_config(
        self, user_input: dict[str, Any | None] = None
    ) -> dict[str, Any]:
        """Handle API credentials configuration."""
        errors = {}

        if user_input is not None:
            client_id = user_input[CONF_API_CLIENT_ID]
            client_secret = user_input[CONF_API_CLIENT_SECRET]
            endpoint = user_input.get(CONF_API_ENDPOINT, DEFAULT_API_ENDPOINT)

            # Test API connection
            try:
                async with TuyaCloudClient(
                    client_id=client_id,
                    client_secret=client_secret,
                    endpoint=endpoint,
                ) as client:
                    if await client.test_connection():
                        self.api_client = client
                        return await self.async_step_api_discovery()
                    else:
                        errors["base"] = "api_connection_failed"

            except TuyaAuthenticationError:
                errors["base"] = "api_auth_failed"
            except TuyaAPIError as err:
                _LOGGER.error(f"API configuration error: {err}")
                errors["base"] = "api_error"
            except Exception as err:
                _LOGGER.error(f"Unexpected API error: {err}")
                errors["base"] = "unknown_api_error"

        return self.async_show_form(
            step_id="api_config",
            data_schema=vol.Schema({
                vol.Required(CONF_API_CLIENT_ID): str,
                vol.Required(CONF_API_CLIENT_SECRET): str,
                vol.Optional(CONF_API_ENDPOINT, default=DEFAULT_API_ENDPOINT): str,
            }),
            errors=errors,
            description_placeholders={
                "client_id_desc": "Access ID from Tuya IoT Platform project",
                "client_secret_desc": "Access Secret from Tuya IoT Platform project",
                "endpoint_desc": "API endpoint (EU: openapi.tuyaeu.com, US: openapi.tuyaus.com)",
            },
        )

    async def async_step_api_discovery(
        self, user_input: dict[str, Any | None] = None
    ) -> dict[str, Any]:
        """Handle device discovery via API."""
        if not self.api_client:
            return await self.async_step_api_config()

        errors = {}

        if user_input is not None:
            selected_device_id = user_input["selected_device"]
            self.selected_device = self.discovered_devices.get(selected_device_id)

            if self.selected_device:
                return await self.async_step_device_analysis()
            else:
                errors["base"] = "device_not_found"

        # Discover devices via API
        try:
            _LOGGER.info("Discovering devices via Tuya Cloud API")
            devices = await self.api_client.get_device_list()

            # Filter for potential KKT Kolbe devices
            kkt_devices = []
            for device in devices:
                # Check for KKT Kolbe indicators
                name = device.get("name", "").lower()
                model = device.get("model", "").lower()

                if any(indicator in name or indicator in model
                       for indicator in ["kkt", "kolbe", "hood", "extractor", "dunst"]):
                    kkt_devices.append(device)
                    self.discovered_devices[device["id"]] = device

            if not kkt_devices:
                return self.async_show_form(
                    step_id="api_discovery",
                    errors={"base": "no_kkt_devices_found"},
                    description_placeholders={
                        "total_devices": str(len(devices)),
                        "suggestion": "Try manual configuration if your device is not detected",
                    },
                )

            # Create device selection options
            device_options = []
            for device in kkt_devices:
                device_options.append({
                    "value": device["id"],
                    "label": f"{device.get('name', 'Unknown')} ({device.get('model', 'Unknown Model')})"
                })

            return self.async_show_form(
                step_id="api_discovery",
                data_schema=vol.Schema({
                    vol.Required("selected_device"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=device_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }),
                description_placeholders={
                    "found_devices": str(len(kkt_devices)),
                    "total_devices": str(len(devices)),
                },
            )

        except TuyaAPIError as err:
            _LOGGER.error(f"Device discovery failed: {err}")
            errors["base"] = "discovery_failed"

        return self.async_show_form(
            step_id="api_discovery",
            errors=errors,
        )

    async def async_step_device_analysis(
        self, user_input: dict[str, Any | None] = None
    ) -> dict[str, Any]:
        """Analyze selected device and create configuration."""
        if not self.selected_device or not self.api_client:
            return await self.async_step_api_discovery()

        device_id = self.selected_device["id"]

        # Set unique_id to prevent duplicate entries (HA standard)
        await self.async_set_unique_id(device_id)
        self._abort_if_unique_id_configured()

        try:
            # Get device properties from API
            _LOGGER.info(f"Analyzing device {device_id}")
            properties = await self.api_client.get_device_properties(device_id)

            # Use dynamic factory to analyze device
            factory = DynamicDeviceFactory()
            device_config = await factory.analyze_device_properties({
                "result": {
                    "device_id": device_id,
                    "model_id": self.selected_device.get("model", "unknown"),
                    "name": self.selected_device.get("name", "KKT Kolbe Device"),
                    "model": properties.get("model", "{}"),
                }
            })

            # For hybrid mode, we still need manual local connection details
            if self.integration_mode == MODE_HYBRID:
                return await self.async_step_hybrid_manual_details(device_config)

            # For pure API mode, create entry
            config_data = {
                CONF_DEVICE_ID: device_id,
                CONF_API_ENABLED: True,
                CONF_API_CLIENT_ID: self.api_client.client_id,
                CONF_API_CLIENT_SECRET: self.api_client.client_secret,
                CONF_API_ENDPOINT: self.api_client.endpoint,
                CONF_INTEGRATION_MODE: self.integration_mode,
                "device_model": device_config.model_id,
                "device_type": device_config.device_type,
                "api_entities": len(device_config.entities),
            }

            return self.async_create_entry(
                title=f"{device_config.name} (API)",
                data=config_data,
            )

        except Exception as err:
            _LOGGER.error(f"Device analysis failed: {err}")
            return self.async_show_form(
                step_id="device_analysis",
                errors={"base": "analysis_failed"},
            )

    async def async_step_hybrid_manual_details(
        self, device_config, user_input: dict[str, Any | None] = None
    ) -> dict[str, Any]:
        """Get manual connection details for hybrid mode."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            local_key = user_input[CONF_LOCAL_KEY]

            if host and local_key:
                # Create hybrid configuration entry
                config_data = {
                    CONF_DEVICE_ID: self.selected_device["id"],
                    CONF_HOST: host,
                    CONF_LOCAL_KEY: local_key,
                    CONF_API_ENABLED: True,
                    CONF_API_CLIENT_ID: self.api_client.client_id,
                    CONF_API_CLIENT_SECRET: self.api_client.client_secret,
                    CONF_API_ENDPOINT: self.api_client.endpoint,
                    CONF_INTEGRATION_MODE: MODE_HYBRID,
                    "device_model": device_config.model_id,
                    "device_type": device_config.device_type,
                    "api_entities": len(device_config.entities),
                }

                return self.async_create_entry(
                    title=f"{device_config.name} (Hybrid)",
                    data=config_data,
                )
            else:
                errors["base"] = "missing_local_details"

        return self.async_show_form(
            step_id="hybrid_manual_details",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_LOCAL_KEY): str,
            }),
            errors=errors,
            description_placeholders={
                "device_name": device_config.name,
                "device_id": self.selected_device["id"][:8],
                "host_desc": "IP address for local communication",
                "local_key_desc": "Local encryption key for direct communication",
            },
        )