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
# Lazy import discovery to reduce blocking time

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

class ConnectionTestError(Exception):
    """Custom exception for connection test failures."""
    pass


class AuthenticationError(Exception):
    """Custom exception for authentication failures."""
    pass


class NetworkError(Exception):
    """Custom exception for network-related failures."""
    pass


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    from .tuya_device import KKTKolbeTuyaDevice
    import socket
    import asyncio

    device_id = data[CONF_DEVICE_ID]
    host = data[CONF_HOST]
    local_key = data[CONF_ACCESS_TOKEN]

    # First validate inputs
    # Tuya device IDs are typically 20-22 characters (e.g., bf735dfe2ad64fba7cpyhn)
    if not device_id or len(device_id) < 20 or len(device_id) > 22:
        raise ValueError("Device ID must be 20-22 characters (found in your Tuya app)")

    if not local_key or len(local_key) < 10:
        raise AuthenticationError("Local Key seems too short or invalid")

    # First validate if it's a valid IP address format
    import ipaddress
    try:
        ipaddress.ip_address(host)
        is_ip = True
    except ValueError:
        is_ip = False

    # Test basic network connectivity
    try:
        # Quick socket test to see if host is reachable
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, 6667))  # Standard Tuya device port
        sock.close()

        if result != 0:
            # Try ping-like test
            import subprocess
            ping_cmd = ['ping', '-c', '1', '-W', '3000']
            if is_ip:
                ping_cmd.append('-n')  # Don't resolve IP addresses
            ping_cmd.append(host)

            ping_result = subprocess.run(ping_cmd, capture_output=True, timeout=5)
            if ping_result.returncode != 0:
                raise NetworkError(f"Host {host} is not reachable")

    except socket.timeout:
        raise NetworkError(f"Connection to {host} timed out")
    except socket.gaierror as e:
        if is_ip:
            raise NetworkError(f"Invalid IP address format: {host}")
        else:
            raise NetworkError(f"Cannot resolve hostname {host}")
    except subprocess.TimeoutExpired:
        raise NetworkError(f"Network timeout when trying to reach {host}")
    except Exception as e:
        _LOGGER.debug(f"Network pre-check failed: {e}")
        # Continue anyway, might still work

    # Test Tuya device connection
    try:
        _LOGGER.info(f"Testing connection to device: {host} with ID: {device_id[:10]}...")

        device = KKTKolbeTuyaDevice(
            device_id=device_id,
            ip_address=host,
            local_key=local_key,
        )

        status = await device.async_update_status()
        _LOGGER.debug(f"Device status response: {status}")

        if not status:
            raise ConnectionTestError("Device did not respond to status request - check device ID and local key")

    except Exception as e:
        error_msg = str(e).lower()

        if "decrypt" in error_msg or "key" in error_msg:
            raise AuthenticationError("Invalid Local Key - device rejected authentication")
        elif "timeout" in error_msg:
            raise NetworkError(f"Connection timeout - device at {host} not responding")
        elif "connection" in error_msg or "refused" in error_msg:
            raise NetworkError(f"Connection refused by device at {host}")
        elif "device" in error_msg and "not found" in error_msg:
            raise ConnectionTestError("Device ID not found or incorrect")
        else:
            # Log the actual error for debugging
            _LOGGER.error(f"Tuya connection test failed: {e}")
            raise ConnectionTestError(f"Could not connect to device: {str(e)}")

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
        self._discovery_info = None

    def _create_schema_with_defaults(self, user_input: dict[str, Any]) -> vol.Schema:
        """Create schema with preserved user input as defaults."""
        return vol.Schema(
            {
                vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
                vol.Required(CONF_DEVICE_ID, default=user_input.get(CONF_DEVICE_ID, "")): str,
                vol.Required(CONF_ACCESS_TOKEN, default=user_input.get(CONF_ACCESS_TOKEN, "")): str,
                vol.Optional(CONF_TYPE, default=user_input.get(CONF_TYPE, "auto")): vol.In(["auto", "hood", "cooktop"]),
                vol.Optional(CONF_NAME, default=user_input.get(CONF_NAME, "KKT Kolbe Device")): str,
            }
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        # Start discovery using the working system that finds your devices
        from .discovery import async_start_discovery

        _LOGGER.warning("🔍 Starting working KKT Kolbe device discovery...")
        await async_start_discovery(self.hass)

        # Wait for discovery to find devices (since we know it works!)
        import asyncio
        max_wait = 8  # Wait a bit longer since discovery is working
        wait_interval = 0.5

        _LOGGER.warning(f"Waiting up to {max_wait}s for device discovery...")

        for i in range(int(max_wait / wait_interval)):
            from .discovery import get_discovered_devices
            self._discovered_devices = get_discovered_devices()
            _LOGGER.warning(f"Discovery check {i+1}: Found {len(self._discovered_devices)} devices")
            if self._discovered_devices:
                break
            await asyncio.sleep(wait_interval)

        _LOGGER.warning(f"🎯 Discovery finished: Found {len(self._discovered_devices)} KKT Kolbe devices")

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
            except AuthenticationError as e:
                _LOGGER.warning(f"Authentication failed: {e}")
                # Focus on the specific field with auth issues
                errors["access_token"] = str(e)
            except NetworkError as e:
                _LOGGER.warning(f"Network error: {e}")
                errors["base"] = "cannot_connect"
            except ConnectionTestError as e:
                _LOGGER.warning(f"Connection test failed: {e}")
                errors["base"] = "cannot_connect"
            except ValueError as e:
                _LOGGER.warning(f"Invalid input: {e}")
                errors["base"] = "invalid_input"
            except Exception as e:
                _LOGGER.exception("Unexpected exception during discovery setup")
                errors["base"] = "unknown"
                errors["general"] = f"Unexpected error: {str(e)}"

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
            except AuthenticationError as e:
                _LOGGER.warning(f"Authentication failed: {e}")
                # Focus on the specific field with auth issues
                errors["access_token"] = str(e)
            except NetworkError as e:
                _LOGGER.warning(f"Network error: {e}")
                errors["base"] = "cannot_connect"
                errors["host"] = str(e)
            except ConnectionTestError as e:
                _LOGGER.warning(f"Connection test failed: {e}")
                errors["base"] = "cannot_connect"
            except ValueError as e:
                _LOGGER.warning(f"Invalid input: {e}")
                # Don't set base error if we can be specific about the field
                if "device id" in str(e).lower():
                    errors["device_id"] = str(e)
                elif "local key" in str(e).lower():
                    errors["access_token"] = str(e)
                else:
                    errors["base"] = "invalid_input"
            except Exception as e:
                _LOGGER.exception("Unexpected exception during validation")
                errors["base"] = "unknown"
                errors["general"] = f"Unexpected error: {str(e)}"

        # Preserve user input on error
        if user_input is not None:
            data_schema = self._create_schema_with_defaults(user_input)
        else:
            data_schema = STEP_USER_DATA_SCHEMA

        return self.async_show_form(
            step_id="manual", data_schema=data_schema, errors=errors
        )

    async def async_step_choose_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose setup method when no devices discovered."""
        errors: dict[str, str] = {}

        if user_input is not None:
            choice = user_input.get("setup_choice")
            if choice == "retry":
                # Retry automatic discovery
                return await self.async_step_user()
            elif choice == "manual":
                return await self.async_step_manual()
            elif choice == "test":
                # Add test device for debugging
                from .discovery import add_test_device
                add_test_device()
                from .discovery import get_discovered_devices
                self._discovered_devices = get_discovered_devices()
                return await self.async_step_discovery()
            elif choice == "debug":
                return await self.async_step_debug_info()

        setup_schema = vol.Schema({
            vol.Required("setup_choice"): vol.In({
                "retry": "Retry automatic discovery",
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

        debug_info = "KKT Kolbe Discovery Debug Information:\n\n"

        # mDNS Discovery
        mdns_services = network_services.get("mDNS_services", {})
        debug_info += f"mDNS Services Found: {len(mdns_services)}\n"
        for service_type, devices in mdns_services.items():
            debug_info += f"  {service_type}: {len(devices) if isinstance(devices, list) else 'error'}\n"

        # UDP Discovery
        udp_discovery = network_services.get("UDP_discovery", {})
        debug_info += f"\nUDP Discovery (Tuya Broadcasts):\n"
        if "error" in udp_discovery:
            debug_info += f"  Error: {udp_discovery['error']}\n"
        else:
            debug_info += f"  Devices found: {udp_discovery.get('devices_found', 0)}\n"
            for device in udp_discovery.get('devices', []):
                debug_info += f"    - {device.get('gwId', 'unknown')} at {device.get('ip', 'unknown')}\n"

        # Discovery Status
        status = network_services.get("discovery_status", {})
        debug_info += f"\nDiscovery Service Status:\n"
        debug_info += f"  Active: {status.get('active', False)}\n"
        debug_info += f"  mDNS Browsers: {status.get('mDNS_browsers', 0)}\n"
        debug_info += f"  UDP Listeners: {status.get('UDP_listeners', 0)}\n"
        debug_info += f"  Discovered Devices: {status.get('discovered_devices', 0)}\n"

        from .discovery import TUYA_SERVICE_TYPES, UDP_PORTS
        debug_info += f"\nConfiguration:\n"
        debug_info += f"  mDNS Service Types: {len(TUYA_SERVICE_TYPES)}\n"
        debug_info += f"  UDP Ports: {UDP_PORTS}\n"

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

    async def async_step_zeroconf(
        self, discovery_info: dict[str, Any]
    ) -> FlowResult:
        """Handle zeroconf discovery."""
        _LOGGER.info(f"Zeroconf discovery triggered with: {discovery_info}")

        # Extract discovery information
        host = discovery_info.get("host")
        name = discovery_info.get("name", discovery_info.get("hostname", "Unknown"))
        device_id = discovery_info.get("properties", {}).get("id") or discovery_info.get("properties", {}).get("devid")

        if not host:
            return self.async_abort(reason="no_host")

        # Set unique ID to prevent duplicates
        unique_id = device_id or host
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        # Store discovery info for later use
        self._discovery_info = {
            "host": host,
            "device_id": device_id,
            "name": name,
            "discovered_via": "zeroconf"
        }

        # Check if this might be a KKT device
        if device_id and (device_id.startswith('bf735dfe2ad64fba7c') or device_id.startswith('bf5592b47738c5b46e')):
            _LOGGER.info(f"Discovered known KKT device pattern: {device_id}")
            self.context["title_placeholders"] = {"name": f"KKT Kolbe Device ({host})"}
            return await self.async_step_zeroconf_confirm()

        # For unknown devices, let user confirm
        self.context["title_placeholders"] = {"name": f"Potential KKT Device ({host})"}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm the zeroconf discovery."""
        if user_input is not None:
            # User confirmed, proceed with setup
            return await self.async_step_zeroconf_credentials()

        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                "name": self._discovery_info["name"],
                "host": self._discovery_info["host"],
                "device_id": self._discovery_info.get("device_id", "Unknown")
            }
        )

    async def async_step_zeroconf_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle credentials for zeroconf discovered device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                device_config = {
                    CONF_HOST: self._discovery_info["host"],
                    CONF_DEVICE_ID: self._discovery_info.get("device_id", ""),
                    CONF_ACCESS_TOKEN: user_input[CONF_ACCESS_TOKEN],
                    CONF_NAME: user_input.get(CONF_NAME, f"KKT Kolbe ({self._discovery_info['host']})"),
                    CONF_TYPE: "auto",
                }

                # Validate if device_id is missing
                if not device_config[CONF_DEVICE_ID]:
                    errors["base"] = "missing_device_id"
                else:
                    info = await validate_input(self.hass, device_config)
                    return self.async_create_entry(title=info["title"], data=device_config)

            except AuthenticationError as e:
                _LOGGER.warning(f"Authentication failed: {e}")
                # Focus on the specific field with auth issues
                errors["access_token"] = str(e)
            except NetworkError as e:
                _LOGGER.warning(f"Network error: {e}")
                errors["base"] = "cannot_connect"
            except ConnectionTestError as e:
                _LOGGER.warning(f"Connection test failed: {e}")
                errors["base"] = "cannot_connect"
            except ValueError as e:
                _LOGGER.warning(f"Invalid input: {e}")
                # Don't set base error if we can be specific about the field
                if "device id" in str(e).lower():
                    errors["device_id"] = str(e)
                elif "local key" in str(e).lower():
                    errors["access_token"] = str(e)
                else:
                    errors["base"] = "invalid_input"
            except Exception as e:
                _LOGGER.exception("Unexpected exception during zeroconf setup")
                errors["base"] = "unknown"
                errors["general"] = f"Unexpected error: {str(e)}"

        credentials_schema = vol.Schema({
            vol.Required(CONF_ACCESS_TOKEN): str,
            vol.Optional(CONF_NAME, default=f"KKT Kolbe ({self._discovery_info['host']})"): str,
            vol.Optional(CONF_DEVICE_ID, default=self._discovery_info.get("device_id", "")): str,
        })

        return self.async_show_form(
            step_id="zeroconf_credentials",
            data_schema=credentials_schema,
            errors=errors,
            description_placeholders={
                "device_name": self._discovery_info["name"],
                "device_host": self._discovery_info["host"],
                "device_id": self._discovery_info.get("device_id", "Unknown")
            }
        )