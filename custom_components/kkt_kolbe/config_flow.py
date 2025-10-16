"""Config flow for KKT Kolbe Dunstabzugshaube integration."""
import asyncio
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

def get_manual_setup_schema():
    """Get manual setup schema with dynamic device choices."""
    from .device_types import get_known_device_choices

    device_choices = get_known_device_choices()

    return vol.Schema({
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Required(CONF_ACCESS_TOKEN): str,
        vol.Required("device_type", default="unknown"): vol.In(device_choices),
        vol.Optional(CONF_NAME, default="KKT Kolbe Device"): str,
    })

# Legacy schema for compatibility
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Required(CONF_ACCESS_TOKEN): str,
        vol.Optional(CONF_TYPE, default="auto"): vol.In(["auto", "hood", "cooktop"]),
        vol.Optional(CONF_NAME, default="KKT Kolbe Device"): str,
        vol.Optional("product_name", default=""): str,  # Tuya product name for auto-detection
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

            # Run ping in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            ping_result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(ping_cmd, capture_output=True, timeout=5)
            )
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
        # Continue anyway, might still work
        pass

    # Test Tuya device connection
    try:
        _LOGGER.info(f"Testing connection to device: {host} with ID: {device_id[:10]}...")

        device = KKTKolbeTuyaDevice(
            device_id=device_id,
            ip_address=host,
            local_key=local_key,
        )

        # Use same connection method as setup for consistency
        await device.async_connect()

        # Additional validation to ensure device responds correctly
        status = await device.async_get_status()
        if not status or not isinstance(status, dict) or "dps" not in status:
            raise ConnectionTestError("Device connected but did not provide valid status - check device ID and local key")

    except Exception as e:
        error_msg = str(e).lower()

        # Handle specific error types from our tuya_device.py
        if "no compatible version found" in error_msg:
            raise ConnectionTestError("Device not responding to any Tuya protocol version. Please check: 1) Device is powered on and connected, 2) IP address is correct, 3) Local key is valid")
        elif "decrypt" in error_msg or ("key" in error_msg and "invalid" in error_msg):
            raise AuthenticationError("Invalid Local Key - device rejected authentication")
        elif "timeout" in error_msg:
            raise NetworkError(f"Connection timeout - device at {host} not responding")
        elif "connection" in error_msg or "refused" in error_msg:
            raise NetworkError(f"Connection refused by device at {host}")
        elif "device" in error_msg and "not found" in error_msg:
            raise ConnectionTestError("Device ID not found or incorrect")
        else:
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

        await async_start_discovery(self.hass)

        # Wait for discovery to find devices
        import asyncio
        max_wait = 8
        wait_interval = 0.5

        for i in range(int(max_wait / wait_interval)):
            from .discovery import get_discovered_devices
            self._discovered_devices = get_discovered_devices()
            if self._discovered_devices:
                break
            await asyncio.sleep(wait_interval)

        # Filter out already configured devices (LocalTuya approach)
        filtered_devices = {}
        for device_id, device_info in self._discovered_devices.items():
            # Check if device is already configured
            already_configured = False
            for entry in self.hass.config_entries.async_entries("kkt_kolbe"):
                if entry.data.get("device_id") == device_id:
                    already_configured = True
                    _LOGGER.info(f"⏭️ Device {device_id} already configured, filtering out")
                    break

            if not already_configured:
                filtered_devices[device_id] = device_info

        self._discovered_devices = filtered_devices

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

            # Ensure device_id is properly set
            if "device_id" not in self._selected_device or not self._selected_device["device_id"]:
                self._selected_device["device_id"] = device_id

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
                    "product_name": self._selected_device.get("product_name", "unknown"),  # CRITICAL: Add product_name from discovery
                }

                info = await validate_input(self.hass, device_config)
                return self.async_create_entry(title=info["title"], data=device_config)
            except AuthenticationError as e:
                errors["access_token"] = str(e)
            except NetworkError as e:
                errors["base"] = "cannot_connect"
            except ConnectionTestError as e:
                errors["base"] = "cannot_connect"
            except ValueError as e:
                errors["base"] = "invalid_input"
            except Exception as e:
                _LOGGER.exception("Unexpected exception during discovery setup")
                errors["base"] = "unknown"
                errors["general"] = f"Unexpected error: {str(e)}"

        credentials_schema = vol.Schema({
            vol.Required(CONF_ACCESS_TOKEN): str,
            vol.Optional(CONF_NAME, default=self._selected_device.get("product_name", "KKT Kolbe Device")): str,
        })

        # Debug the placeholders
        device_name = self._selected_device.get("product_name", "Unknown")
        device_host = self._selected_device.get("host", "Unknown")
        device_id = self._selected_device.get("device_id", "Unknown")


        return self.async_show_form(
            step_id="credentials",
            data_schema=credentials_schema,
            errors=errors,
            description_placeholders={
                "device_name": device_name,
                "device_host": device_host,
                "device_id": device_id,
            }
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # For manual setup, use user-friendly device selection
                from .device_types import get_product_name_from_device_choice, auto_detect_device_config

                manual_config = user_input.copy()
                device_id = user_input.get(CONF_DEVICE_ID, "")
                selected_device_type = user_input.get("device_type", "unknown")

                # First try auto-detection by device ID
                detected_config = auto_detect_device_config(device_id=device_id)

                if detected_config:
                    # Device ID recognized - use auto-detected configuration
                    manual_config["product_name"] = detected_config["product_name"]
                else:
                    # Use user's device type selection
                    manual_config["product_name"] = get_product_name_from_device_choice(selected_device_type)

                info = await validate_input(self.hass, manual_config)
                return self.async_create_entry(title=info["title"], data=manual_config)
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

        # Use the new user-friendly device selection schema
        data_schema = get_manual_setup_schema()

        # Preserve user input on error (simplified)
        if user_input is not None and errors:
            try:
                # Create schema with user's current values as defaults
                from .device_types import get_known_device_choices
                device_choices = get_known_device_choices()

                data_schema = vol.Schema({
                    vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
                    vol.Required(CONF_DEVICE_ID, default=user_input.get(CONF_DEVICE_ID, "")): str,
                    vol.Required(CONF_ACCESS_TOKEN, default=user_input.get(CONF_ACCESS_TOKEN, "")): str,
                    vol.Required("device_type", default=user_input.get("device_type", "unknown")): vol.In(device_choices),
                    vol.Optional(CONF_NAME, default=user_input.get(CONF_NAME, "KKT Kolbe Device")): str,
                })
            except Exception:
                # Fallback to default schema
                data_schema = get_manual_setup_schema()

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
        # Check for device_id in multiple formats (UDP vs mDNS)
        device_id = (
            discovery_info.get("device_id") or  # UDP discovery format
            discovery_info.get("properties", {}).get("id") or  # mDNS format
            discovery_info.get("properties", {}).get("devid")  # Alternative mDNS format
        )


        # If still no device_id, try global discovery as fallback (for pure mDNS)
        if not device_id:
            from .discovery import _discovery_instance
            if _discovery_instance and _discovery_instance.discovered_devices:
                # Find device by IP in discovered devices
                for discovered_id, device_data in _discovery_instance.discovered_devices.items():
                    if device_data.get("host") == host:
                        device_id = discovered_id
                        break

        if not host:
            return self.async_abort(reason="no_host")

        # Set unique ID to prevent duplicates
        unique_id = device_id or host
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        # Store discovery info for later use (preserve original discovered_via)
        self._discovery_info = {
            "host": host,
            "device_id": device_id,
            "name": name,
            "discovered_via": discovery_info.get("discovered_via", "zeroconf")
        }

        # Check if this might be a KKT device
        if device_id and (device_id.startswith('bf735dfe2ad64fba7c') or device_id.startswith('bf5592b47738c5b46e')):
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

        final_device_id = self._discovery_info.get("device_id") or "Unknown"

        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                "name": self._discovery_info["name"],
                "host": self._discovery_info["host"],
                "device_id": final_device_id
            }
        )

    async def async_step_zeroconf_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle credentials for zeroconf discovered device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Extract product name for dynamic device configuration
                product_name = self._discovery_info.get("name", "Unknown")

                device_config = {
                    CONF_HOST: self._discovery_info["host"],
                    CONF_DEVICE_ID: self._discovery_info.get("device_id", ""),
                    CONF_ACCESS_TOKEN: user_input[CONF_ACCESS_TOKEN],
                    CONF_NAME: user_input.get(CONF_NAME, f"KKT Kolbe ({self._discovery_info['host']})"),
                    CONF_TYPE: "auto",
                    "product_name": product_name,  # Store for dynamic entity creation
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

        # Debug the discovery info for zeroconf and determine device_id
        device_name = self._discovery_info.get("name", "Unknown")
        device_host = self._discovery_info.get("host", "Unknown")
        # Try device_id first, then gwId as fallback (like discovery does)
        device_id = self._discovery_info.get("device_id") or self._discovery_info.get("gwId")

        # If still no device_id, check global discovery instance for this IP
        if not device_id:
            from .discovery import _discovery_instance
            if _discovery_instance and _discovery_instance.discovered_devices:
                # Find device by IP in discovered devices
                for discovered_id, device_data in _discovery_instance.discovered_devices.items():
                    if device_data.get("host") == device_host:
                        device_id = discovered_id
                        break

        if not device_id:
            device_id = "Unknown"

        # Now create schema with correct device_id
        credentials_schema = vol.Schema({
            vol.Required(CONF_ACCESS_TOKEN): str,
            vol.Optional(CONF_NAME, default=f"KKT Kolbe ({device_host})"): str,
            vol.Optional(CONF_DEVICE_ID, default=device_id if device_id != "Unknown" else ""): str,
        })


        return self.async_show_form(
            step_id="zeroconf_credentials",
            data_schema=credentials_schema,
            errors=errors,
            description_placeholders={
                "device_name": device_name,
                "device_host": device_host,
                "device_id": device_id,
            }
        )