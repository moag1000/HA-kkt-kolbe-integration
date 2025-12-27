"""Discovery for KKT Kolbe devices using mDNS and UDP broadcasts."""
from __future__ import annotations

import asyncio
import json
import logging
import socket
import time
from hashlib import md5
from typing import Any, Callable

from zeroconf import ServiceBrowser, ServiceListener, ServiceInfo, Zeroconf
from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf
from Crypto.Cipher import AES

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.network import get_url
from homeassistant.components import zeroconf
from homeassistant.const import CONF_HOST, CONF_DEVICE_ID, CONF_IP_ADDRESS

from .const import DOMAIN, MODELS

_LOGGER = logging.getLogger(__name__)

# Tuya UDP Discovery (based on Local Tuya implementation)
# NOTE: Must use standard ports 6666/6667 - Tuya devices only broadcast on these!
UDP_PORTS = [6666, 6667]
UDP_KEY = md5(b"yGAdlopoPVldABfn").digest()
DISCOVERY_TIMEOUT = 6  # seconds

# Device cache cleanup settings
DEVICE_CACHE_MAX_AGE = 3600  # Remove devices not seen for 1 hour
DEVICE_CACHE_MAX_SIZE = 50  # Maximum number of cached devices

# Tuya devices often advertise these mDNS service types
TUYA_SERVICE_TYPES = [
    "_tuya._tcp.local.",
    "_smartlife._tcp.local.",
    "_iot._tcp.local.",
    "_device._tcp.local.",
    "_http._tcp.local.",          # Many IoT devices
    "_homekit._tcp.local.",       # Some Tuya devices expose HomeKit
    "_miio._tcp.local.",          # Xiaomi protocol (some Tuya clones)
]

# KKT Kolbe specific patterns in device names/info
KKT_PATTERNS = [
    "kkt",
    "kolbe",
    "hermes",
    "style",
    "ind7705hc",
]


class TuyaUDPDiscovery(asyncio.DatagramProtocol):
    """UDP Discovery Protocol for Tuya devices (based on Local Tuya)."""

    def __init__(
        self,
        devices_found_callback: Callable[[dict[str, Any]], None],
        hass: HomeAssistant | None = None,
    ) -> None:
        """Initialize UDP discovery protocol."""
        self.devices_found_callback = devices_found_callback
        self.transport: asyncio.DatagramTransport | None = None
        self.hass = hass

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        """Called when UDP connection is established."""
        self.transport = transport
        _LOGGER.debug(f"UDP Discovery listening on {transport.get_extra_info('sockname')}")

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Process received UDP datagram from Tuya device."""
        try:
            _LOGGER.debug(f"RAW UDP received from {addr[0]}: length={len(data)}, data={data.hex()[:100]}...")

            # Try to decrypt the message using LocalTuya approach
            decrypted = self._decrypt_udp_message(data)
            if decrypted:
                try:
                    device_info = json.loads(decrypted.decode())
                    _LOGGER.debug(f"TUYA DEVICE FOUND via UDP from {addr[0]}: {device_info}")

                    # Add IP address from UDP source
                    device_info["ip"] = addr[0]

                    # Check if this could be a KKT device
                    if self._is_potential_kkt_device(device_info):
                        _LOGGER.info(f"KKT Device discovered: {device_info.get('gwId', 'unknown')} at {device_info['ip']}")

                        # DIRECT FIX: Add device to global discovery instance
                        global _discovery_instance
                        if _discovery_instance:
                            device_id = device_info.get("gwId", "")

                            # Extract product name from UDP data if available
                            product_key = (
                                device_info.get("productKey") or
                                device_info.get("productName") or
                                device_info.get("product_name") or
                                ""
                            )

                            # Detect device type from product key
                            from .helpers.device_detection import detect_device_type_from_product_key
                            device_type, friendly_name = detect_device_type_from_product_key(product_key, device_id)

                            # LocalTuya approach: Just collect all devices, let config flow filter duplicates
                            formatted_device = {
                                "device_id": device_id,
                                "ip": device_info.get("ip"),  # Use consistent "ip" key
                                "name": friendly_name or f"KKT Device {device_id[:8]}",
                                "discovered_via": "UDP",
                                "product_name": product_key or "auto",
                                "device_type": device_type,
                                "friendly_type": friendly_name,
                            }
                            _discovery_instance.discovered_devices[device_id] = formatted_device
                            _discovery_instance._update_device_last_seen(device_id)
                            _LOGGER.debug(f"Added device {device_id} to discovered_devices")

                        # Also call callback
                        self.devices_found_callback(device_info)
                    else:
                        _LOGGER.debug(f"Non-KKT Tuya device: {device_info.get('gwId', 'unknown')}")

                except json.JSONDecodeError as e:
                    _LOGGER.warning(f"Decrypted data is not valid JSON: {e}")
                    _LOGGER.warning(f"Raw decrypted data: {decrypted.hex() if isinstance(decrypted, bytes) else decrypted}")
            else:
                _LOGGER.debug(f"Could not decrypt UDP data from {addr[0]} (length={len(data)})")
                _LOGGER.debug(f"Full hex dump: {data.hex()}")

        except Exception as e:
            _LOGGER.error(f"Failed to process UDP message from {addr}: {e}", exc_info=True)

    def _decrypt_udp_message(self, data: bytes) -> bytes | None:
        """Decrypt Tuya UDP broadcast message like LocalTuya."""
        try:
            # LocalTuya approach: Strip first 20 and last 8 bytes, then decrypt
            if len(data) < 28:  # Must be at least 20+8 bytes
                _LOGGER.debug(f"UDP message too short: {len(data)} bytes")
                return None

            # Strip first 20 and last 8 bytes (LocalTuya protocol)
            encrypted_payload = data[20:-8]

            if len(encrypted_payload) % 16 != 0:
                _LOGGER.debug(f"Invalid encrypted payload length: {len(encrypted_payload)}")
                return None

            # Decrypt using Tuya UDP key
            cipher = AES.new(UDP_KEY, AES.MODE_ECB)
            decrypted = cipher.decrypt(encrypted_payload)

            # Remove PKCS7 padding
            padding_length = decrypted[-1]
            if 1 <= padding_length <= 16:
                decrypted = decrypted[:-padding_length]
                return decrypted
            else:
                _LOGGER.debug(f"Invalid padding length: {padding_length}")
                return None

        except Exception as e:
            _LOGGER.debug(f"Failed to decrypt UDP message: {e}")

        return None

    def _is_potential_kkt_device(self, device_info: dict[str, Any]) -> bool:
        """Check if UDP discovered device could be KKT Kolbe."""
        gw_id = device_info.get("gwId", "")

        # Check against known KKT device ID patterns
        known_device_ids = [
            'bf735dfe2ad64fba7cpyhn',  # HERMES & STYLE (user's exact device ID)
            'bf5592b47738c5b46e',      # IND7705HC
        ]

        # Exact match first
        if gw_id in known_device_ids:
            _LOGGER.info(f"Found known KKT device via UDP: {gw_id}")
            return True

        # Check patterns (first 18 chars) for flexibility
        known_patterns = [
            'bf735dfe2ad64fba7c',  # HERMES & STYLE pattern
            'bf5592b47738c5b46e',  # IND7705HC pattern
        ]

        for pattern in known_patterns:
            if gw_id.startswith(pattern):
                _LOGGER.info(f"Found KKT device via UDP pattern match: {gw_id}")
                return True

        # TEMPORARY: Accept any Tuya device starting with 'bf' for debugging
        # This helps identify actual device IDs in your network
        if gw_id and len(gw_id) >= 20 and gw_id.startswith('bf'):
            _LOGGER.warning(f"Unknown Tuya device found (could be KKT): {gw_id} - please check if this is your KKT device!")
            return True  # Temporarily accept for identification

        # Log all Tuya devices for debugging
        _LOGGER.debug(f"Non-KKT Tuya device found via UDP: {gw_id}")
        return False

class KKTKolbeDiscovery(ServiceListener):
    """Discover KKT Kolbe devices via mDNS and UDP broadcasts."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the discovery service."""
        self.hass = hass
        self.discovered_devices: dict[str, dict[str, Any]] = {}
        self._device_last_seen: dict[str, float] = {}  # Track when each device was last seen
        self._zeroconf: AsyncZeroconf | None = None
        self._browsers: list[ServiceBrowser] = []
        self._udp_listeners: list[tuple[asyncio.DatagramTransport, TuyaUDPDiscovery]] = []
        self._discovery_callback = self._schedule_discovery_trigger
        self._cleanup_task: asyncio.Task | None = None

    async def async_discover_devices(self, timeout: int = 6) -> dict[str, dict[str, Any]]:
        """Discover devices and return discovered devices dict."""
        # Start discovery if not already running
        if not self._browsers and not self._udp_listeners:
            await self.async_start()

        # Wait for discovery to find devices
        await asyncio.sleep(timeout)

        # Clean up stale devices before returning
        self._cleanup_stale_devices()

        # Return discovered devices
        return self.discovered_devices.copy()

    def _cleanup_stale_devices(self) -> None:
        """Remove devices not seen recently to prevent memory leaks."""
        current_time = time.time()
        stale_devices = []

        for device_id, last_seen in self._device_last_seen.items():
            if current_time - last_seen > DEVICE_CACHE_MAX_AGE:
                stale_devices.append(device_id)

        for device_id in stale_devices:
            if device_id in self.discovered_devices:
                _LOGGER.debug(f"Removing stale device from cache: {device_id[:8]}...")
                del self.discovered_devices[device_id]
            if device_id in self._device_last_seen:
                del self._device_last_seen[device_id]

        # Also enforce max cache size (remove oldest if over limit)
        if len(self.discovered_devices) > DEVICE_CACHE_MAX_SIZE:
            # Sort by last seen and remove oldest
            sorted_devices = sorted(
                self._device_last_seen.items(),
                key=lambda x: x[1]
            )
            devices_to_remove = len(self.discovered_devices) - DEVICE_CACHE_MAX_SIZE
            for device_id, _ in sorted_devices[:devices_to_remove]:
                if device_id in self.discovered_devices:
                    _LOGGER.debug(f"Removing oldest device from cache (size limit): {device_id[:8]}...")
                    del self.discovered_devices[device_id]
                if device_id in self._device_last_seen:
                    del self._device_last_seen[device_id]

        if stale_devices:
            _LOGGER.info(f"Cleaned up {len(stale_devices)} stale devices from discovery cache")

    def _update_device_last_seen(self, device_id: str) -> None:
        """Update the last seen timestamp for a device."""
        self._device_last_seen[device_id] = time.time()

    async def _periodic_cleanup(self) -> None:
        """Periodically clean up stale devices."""
        while True:
            try:
                await asyncio.sleep(DEVICE_CACHE_MAX_AGE / 2)  # Run cleanup every 30 minutes
                self._cleanup_stale_devices()
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.error(f"Error in periodic device cleanup: {e}")

    async def async_start(self) -> None:
        """Start mDNS and UDP discovery."""
        try:
            # Skip if already started
            if self._browsers or self._udp_listeners:
                _LOGGER.debug("Discovery already started, skipping")
                return

            # Clean up any stale devices from previous runs
            self._cleanup_stale_devices()

            # Start mDNS discovery using Home Assistant's shared instance
            from homeassistant.components import zeroconf as ha_zeroconf
            self._zeroconf = await ha_zeroconf.async_get_async_instance(self.hass)

            for service_type in TUYA_SERVICE_TYPES:
                _LOGGER.debug(f"Starting browser for service type: {service_type}")
                browser = ServiceBrowser(
                    self._zeroconf.zeroconf,
                    service_type,
                    self
                )
                self._browsers.append(browser)

            # Start UDP discovery (like Local Tuya)
            # NOTE: If Local Tuya is running, UDP discovery will be disabled
            await self._start_udp_discovery()

            # Start periodic cleanup task
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

        except Exception as e:
            _LOGGER.error(f"Failed to start discovery: {e}", exc_info=True)

    async def _send_udp_broadcast(self) -> None:
        """LocalTuya approach: Don't send broadcasts, just listen."""
        # LocalTuya does NOT send UDP broadcasts - devices broadcast automatically
        # We only listen for incoming device broadcasts
        _LOGGER.debug("UDP discovery: Passive listening mode (LocalTuya approach) - no broadcasts sent")

    async def _start_udp_discovery(self) -> None:
        """Start UDP discovery on Tuya broadcast ports."""
        try:

            for port in UDP_PORTS:
                try:
                    loop = asyncio.get_running_loop()
                    transport, protocol = await loop.create_datagram_endpoint(
                        lambda: TuyaUDPDiscovery(self._on_udp_device_found),
                        local_addr=('0.0.0.0', port),
                        allow_broadcast=True
                    )
                    self._udp_listeners.append((transport, protocol))
                    _LOGGER.debug(f"UDP listener started on port {port}")

                except Exception as e:
                    _LOGGER.warning(f"Failed to start UDP listener on port {port}: {e}")

            if self._udp_listeners:
                # LocalTuya approach: Don't send broadcasts, just listen
                # Devices automatically broadcast their presence
                _LOGGER.debug("UDP discovery started - listening for automatic device broadcasts")
            else:
                _LOGGER.warning(
                    "UDP discovery disabled: Ports 6666/6667 in use. "
                    "This is normal if Local Tuya integration is running. "
                    "mDNS discovery will continue working."
                )

        except Exception as e:
            _LOGGER.error(f"Failed to start UDP discovery: {e}", exc_info=True)

    def _on_udp_device_found(self, device_info: dict[str, Any]) -> None:
        """Handle device found via UDP broadcast."""
        try:
            # Convert UDP device info to our format
            device_id = device_info.get("gwId", "")
            if device_id:
                # Extract product name from UDP data if available
                product_name = (
                    device_info.get("productName") or
                    device_info.get("productKey") or
                    device_info.get("product_name") or
                    "KKT Kolbe Device"
                )

                formatted_device = {
                    "device_id": device_id,
                    "gwId": device_id,  # Keep gwId for zeroconf discovery
                    "ip": device_info.get("ip"),  # Use consistent "ip" key
                    "name": f"KKT Device {device_id}",
                    "discovered_via": "UDP",
                    "product_name": product_name,
                    "device_type": "auto"
                }

                self.discovered_devices[device_id] = formatted_device
                self._update_device_last_seen(device_id)

                # Trigger Home Assistant discovery flow
                # Use callback to schedule in the main event loop
                if hasattr(self, '_discovery_callback'):
                    self._discovery_callback(formatted_device)
                else:
                    _LOGGER.warning("No discovery callback available for UDP device")

                _LOGGER.info(f"Added UDP discovered KKT device: {device_id}")

        except Exception as e:
            _LOGGER.error(f"Failed to process UDP device: {e}")

    def _schedule_discovery_trigger(self, device_info: dict[str, Any]) -> None:
        """Schedule discovery trigger in the main event loop."""
        try:
            # Use call_soon_threadsafe since UDP callbacks run in different thread
            loop = self.hass.loop
            loop.call_soon_threadsafe(
                lambda: self.hass.async_create_task(self._async_trigger_discovery(device_info))
            )
        except Exception as e:
            _LOGGER.error(f"Failed to schedule discovery trigger: {e}")

    async def async_stop(self) -> None:
        """Stop mDNS and UDP discovery."""
        # Cancel periodic cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        # Stop mDNS browsers
        for browser in self._browsers:
            browser.cancel()
        self._browsers.clear()

        # Don't close the shared zeroconf instance, just clear our reference
        if self._zeroconf:
            self._zeroconf = None

        # Stop UDP listeners
        for transport, protocol in self._udp_listeners:
            transport.close()
        self._udp_listeners.clear()

        # Clear device cache on stop
        self.discovered_devices.clear()
        self._device_last_seen.clear()

        _LOGGER.info("Stopped KKT Kolbe discovery (mDNS and UDP)")

    def add_service(self, zc, type_: str, name: str) -> None:
        """Called when a service is discovered."""
        try:
            # Use call_soon_threadsafe since this is called from zeroconf thread
            loop = self.hass.loop
            loop.call_soon_threadsafe(
                lambda: self.hass.async_create_task(self._async_add_service(zc, type_, name))
            )
        except Exception as e:
            _LOGGER.error(f"Failed to schedule async service addition: {e}")

    async def _async_add_service(self, zc, type_: str, name: str) -> None:
        """Handle discovered service asynchronously."""
        try:
            # Use AsyncServiceInfo for proper async context
            async_service_info = AsyncServiceInfo(type_, name)
            await async_service_info.async_request(zc, timeout=3000)
            info = async_service_info

            if not info:
                return

            # Check if this looks like a KKT Kolbe device
            if not self._is_kkt_device(info):
                return

            device_info = self._extract_device_info(info)
            if device_info:
                device_id = device_info.get("device_id")
                if device_id:
                    self.discovered_devices[device_id] = device_info
                    self._update_device_last_seen(device_id)

                    # Trigger Home Assistant discovery flow
                    await self._async_trigger_discovery(device_info)

                    _LOGGER.info(f"Discovered KKT Kolbe device: {device_info}")

        except Exception as e:
            _LOGGER.error(f"Error processing discovered service {name}: {e}")

    def _is_kkt_device(self, info) -> bool:
        """Check if the discovered device is a KKT Kolbe device."""
        if not info:
            return False

        _LOGGER.debug(f"Checking device: {info.name} at {info.parsed_addresses()}")

        # Extract device ID from TXT records first
        device_id = None
        if hasattr(info, 'properties') and info.properties:
            for key, value in info.properties.items():
                try:
                    if key is None or value is None:
                        continue
                    key_str = key.decode('utf-8').lower()
                    value_str = value.decode('utf-8')
                    if key_str in ['id', 'devid', 'device_id']:
                        device_id = value_str
                        break
                except (UnicodeDecodeError, AttributeError):
                    continue

        # Check if device ID matches Tuya pattern
        if device_id and device_id.startswith('bf') and len(device_id) >= 20:
            _LOGGER.info(f"Found potential Tuya device with ID: {device_id}")
            return self._check_tuya_device_info(info)

        # Fallback: Check service name for Tuya pattern (less reliable)
        name_lower = info.name.lower()
        if name_lower.startswith('bf') and len(name_lower) >= 20:
            _LOGGER.info(f"Found potential Tuya device by name: {info.name}")
            return self._check_tuya_device_info(info)

        # Check device name for KKT patterns (fallback)
        for pattern in KKT_PATTERNS:
            if pattern in name_lower:
                _LOGGER.info(f"Found KKT device by name pattern '{pattern}': {info.name}")
                return True

        # Check TXT records for device information
        if hasattr(info, 'properties') and info.properties:
            txt_data = {}
            for key, value in info.properties.items():
                try:
                    if key is None or value is None:
                        continue
                    key_str = key.decode('utf-8').lower()
                    value_str = value.decode('utf-8').lower()
                    txt_data[key_str] = value_str
                except (UnicodeDecodeError, AttributeError):
                    continue

            # Look for KKT/Kolbe in TXT records
            for key, value in txt_data.items():
                if any(pattern in value for pattern in KKT_PATTERNS):
                    return True
                if any(pattern in key for pattern in KKT_PATTERNS):
                    return True

            # Check for known model IDs
            model = txt_data.get('model', '') or txt_data.get('md', '')
            if model in MODELS:
                _LOGGER.info(f"Found KKT device by model ID '{model}': {info.name}")
                return True

            # Also check device ID patterns if available
            device_id = txt_data.get('id', '') or txt_data.get('devid', '') or txt_data.get('device_id', '')
            if device_id:
                _LOGGER.debug(f"Found device with ID: {device_id}")

            # Log all TXT data for debugging
            _LOGGER.debug(f"Device TXT data: {txt_data}")

        return False

    def _check_tuya_device_info(self, info) -> bool:
        """Check if a Tuya device is a KKT Kolbe device by TXT records."""
        if not hasattr(info, 'properties') or not info.properties:
            # If no TXT records, we can't identify it as KKT
            # But log it for manual verification
            _LOGGER.info(f"Tuya device without TXT records: {info.name} - manual check required")
            return False

        txt_data = {}
        for key, value in info.properties.items():
            try:
                if key is None or value is None:
                    continue
                key_str = key.decode('utf-8').lower()
                value_str = value.decode('utf-8')
                txt_data[key_str] = value_str
            except (UnicodeDecodeError, AttributeError):
                continue

        _LOGGER.debug(f"Tuya device TXT data: {txt_data}")

        # Check for known model IDs in TXT records
        model = txt_data.get('model', '') or txt_data.get('md', '') or txt_data.get('productid', '')
        device_id = txt_data.get('id', '') or txt_data.get('devid', '') or txt_data.get('device_id', '')

        # Check if this matches known KKT models
        if model in MODELS:
            _LOGGER.info(f"Found KKT device by model ID '{model}': {info.name}")
            return True

        # Check if device ID matches known KKT device IDs (from your test)
        known_kkt_device_patterns = [
            'bf735dfe2ad64fba7c',  # HERMES & STYLE pattern from your test
            'bf5592b47738c5b46e',  # IND7705HC pattern
        ]

        for pattern in known_kkt_device_patterns:
            if device_id.startswith(pattern):
                _LOGGER.info(f"Found KKT device by device ID pattern '{pattern}': {info.name}")
                return True

        # TEMPORARY: Accept any Tuya device for debugging
        # This helps identify actual device IDs in your network
        if device_id and len(device_id) >= 20 and device_id.startswith('bf'):
            _LOGGER.warning(f"Unknown Tuya device found via mDNS (could be KKT): {info.name} - DeviceID: {device_id} - please check if this is your KKT device!")
            return True  # Temporarily accept for identification

        # For debugging: log all Tuya devices for manual verification
        _LOGGER.info(f"Unidentified Tuya device: {info.name} - Model: {model}, DeviceID: {device_id}")
        return False

    def _extract_device_info(self, info: AsyncServiceInfo) -> dict[str, Any] | None:
        """Extract device information from mDNS record."""
        if not info:
            return None

        device_info = {
            "name": info.name,
            "ip": str(info.parsed_addresses()[0]) if info.parsed_addresses() else None,  # Use consistent "ip" key
            "port": info.port,
        }

        # Extract TXT record information
        if hasattr(info, 'properties') and info.properties:
            for key, value in info.properties.items():
                try:
                    # Handle None values gracefully
                    if key is None or value is None:
                        continue

                    key_str = key.decode('utf-8')
                    value_str = value.decode('utf-8')

                    # Common Tuya device properties
                    if key_str.lower() in ['id', 'devid', 'device_id']:
                        device_info["device_id"] = value_str
                    elif key_str.lower() in ['model', 'md']:
                        device_info["model"] = value_str
                    elif key_str.lower() in ['version', 'ver']:
                        device_info["version"] = value_str
                    elif key_str.lower() in ['manufacturer', 'mfg']:
                        device_info["manufacturer"] = value_str

                except (UnicodeDecodeError, AttributeError):
                    continue

        # Determine device type from model
        model = device_info.get("model", "")
        if model in MODELS:
            device_info["device_type"] = MODELS[model]["category"]
            device_info["product_name"] = MODELS[model]["name"]

        return device_info if device_info.get("ip") else None

    async def _async_trigger_discovery(self, device_info: dict[str, Any]) -> None:
        """Trigger Home Assistant discovery flow."""
        try:
            # Extract device_id from UDP discovery data (gwId) or use existing device_id
            device_id = device_info.get("device_id") or device_info.get("gwId")

            discovery_info = {
                "host": device_info["ip"],  # Use ip but keep "host" key for compatibility
                "device_id": device_id,
                "model": device_info.get("model"),
                "name": device_info.get("product_name", device_info["name"]),
                "discovered_via": device_info.get("discovered_via", "mDNS"),
            }


            # Create a unique identifier for this discovery
            unique_id = device_info.get("device_id", device_info["ip"])

            # Trigger automatic discovery flow
            try:
                from homeassistant.helpers import discovery_flow

                flow_result = discovery_flow.async_create_flow(
                    self.hass,
                    DOMAIN,
                    context={"source": "zeroconf"},
                    data=discovery_info,
                )

                # Only await if it's actually awaitable
                if flow_result is not None:
                    await flow_result

            except Exception as flow_error:
                _LOGGER.debug(f"Discovery flow creation failed: {flow_error}")
                # This is not critical, discovery still works manually

            _LOGGER.info(f"Triggered automatic discovery for KKT device: {device_info['name']}")

        except Exception as e:
            _LOGGER.error(f"Failed to trigger discovery: {e}", exc_info=True)

    def remove_service(self, zc, type_: str, name: str) -> None:
        """Called when a service is removed."""
        # Could implement device removal logic here
        pass

    def update_service(self, zc, type_: str, name: str) -> None:
        """Called when a service is updated - Gold Tier: Update IP address if changed."""
        try:
            # Use call_soon_threadsafe since this is called from zeroconf thread
            loop = self.hass.loop
            loop.call_soon_threadsafe(
                lambda: self.hass.async_create_task(self._async_update_service(zc, type_, name))
            )
        except Exception as e:
            _LOGGER.error(f"Failed to schedule async service update: {e}")

    async def _async_update_service(self, zc, type_: str, name: str) -> None:
        """Handle service update - Update IP address in config entry if changed."""
        try:
            # Get updated service info
            async_service_info = AsyncServiceInfo(type_, name)
            await async_service_info.async_request(zc, timeout=3000)
            info = async_service_info

            if not info or not info.parsed_addresses():
                return

            # Extract device info
            device_id = None
            if hasattr(info, 'properties') and info.properties:
                for key, value in info.properties.items():
                    try:
                        if key is None or value is None:
                            continue
                        key_str = key.decode('utf-8').lower()
                        value_str = value.decode('utf-8')
                        if key_str in ['id', 'devid', 'device_id']:
                            device_id = value_str
                            break
                    except (UnicodeDecodeError, AttributeError):
                        continue

            if not device_id:
                return

            # Get new IP address
            new_ip = str(info.parsed_addresses()[0])

            # Find config entry for this device
            config_entries = self.hass.config_entries.async_entries(DOMAIN)
            for entry in config_entries:
                entry_device_id = entry.data.get("device_id") or entry.data.get(CONF_DEVICE_ID)
                if entry_device_id == device_id:
                    old_ip = entry.data.get("ip_address") or entry.data.get(CONF_IP_ADDRESS) or entry.data.get("host")

                    if old_ip and old_ip != new_ip:
                        _LOGGER.info(f"Device {device_id} IP changed: {old_ip} → {new_ip}")

                        # Update config entry data
                        new_data = dict(entry.data)
                        new_data["ip_address"] = new_ip
                        if "host" in new_data:
                            new_data["host"] = new_ip
                        if CONF_IP_ADDRESS in new_data:
                            new_data[CONF_IP_ADDRESS] = new_ip
                        if CONF_HOST in new_data:
                            new_data[CONF_HOST] = new_ip

                        self.hass.config_entries.async_update_entry(entry, data=new_data)

                        # Reload the integration to use new IP
                        await self.hass.config_entries.async_reload(entry.entry_id)

                        _LOGGER.info(f"Updated and reloaded config entry for device {device_id}")
                    elif not old_ip:
                        _LOGGER.debug(f"Device {device_id} discovered with IP {new_ip}, but no existing IP to compare")
                    break

            # Also update discovered devices cache
            if device_id in self.discovered_devices:
                self.discovered_devices[device_id]["ip"] = new_ip

        except Exception as e:
            _LOGGER.error(f"Error updating service {name}: {e}", exc_info=True)


# Global discovery instance
_discovery_instance: KKTKolbeDiscovery | None = None


async def async_start_discovery(hass: HomeAssistant) -> None:
    """Start the mDNS discovery service."""
    global _discovery_instance

    if _discovery_instance is None:
        _discovery_instance = KKTKolbeDiscovery(hass)
        await _discovery_instance.async_start()


async def async_stop_discovery() -> None:
    """Stop the mDNS discovery service."""
    global _discovery_instance

    if _discovery_instance:
        await _discovery_instance.async_stop()
        _discovery_instance = None


def get_discovered_devices() -> dict[str, dict[str, Any]]:
    """Get currently discovered devices."""
    global _discovery_instance

    if _discovery_instance:
        return _discovery_instance.discovered_devices.copy()
    return {}


async def simple_tuya_discover(timeout: int = 6) -> dict[str, dict[str, Any]]:
    """Simple Tuya device discovery like LocalTuya."""
    discovered = {}

    def device_found(device_info: dict[str, Any]) -> None:
        device_id = device_info.get("gwId", "")
        if device_id:
            discovered[device_id] = device_info

    # Create UDP listeners
    loop = asyncio.get_running_loop()
    listeners = []

    try:
        for port in [6666, 6667]:
            try:
                transport, protocol = await loop.create_datagram_endpoint(
                    lambda: TuyaUDPDiscovery(device_found),
                    local_addr=('0.0.0.0', port)
                )
                listeners.append((transport, protocol))
                pass  # UDP listener started successfully
            except Exception as e:
                _LOGGER.warning(f"Failed to start UDP listener on port {port}: {e}")

        if listeners:
            await asyncio.sleep(timeout)

        # Close listeners
        for transport, protocol in listeners:
            transport.close()

        return discovered

    except Exception as e:
        _LOGGER.error(f"Discovery failed: {e}")
        return {}


def add_test_device(host: str | None = None, device_id: str | None = None) -> None:
    """Add a test device for debugging (development only).

    Args:
        host: IP address of the test device (default: 192.168.2.43)
        device_id: Device ID to use (default: bf735dfe2ad64fba7cpyhn)
    """
    global _discovery_instance

    if _discovery_instance:
        # Use provided values or real defaults based on user's actual device
        test_device = {
            "device_id": device_id or "bf735dfe2ad64fba7cpyhn",  # User's actual device ID
            "ip": host or "192.168.2.43",  # User's actual IP - use consistent "ip" key
            "name": "Test KKT HERMES & STYLE",
            "model": "e1k6i0zo",
            "device_type": "hood",
            "product_name": "Test HERMES & STYLE",
            "discovered_via": "test_simulation"
        }
        _discovery_instance.discovered_devices["test_device"] = test_device
        _LOGGER.warning(f"Added test device for debugging: {test_device['ip']} / {test_device['device_id'][:10]}...")


async def debug_scan_network() -> dict[str, Any]:
    """Scan network for mDNS services and test UDP discovery (debugging only)."""
    global _discovery_instance

    try:
        results = {
            "mDNS_services": {},
            "UDP_discovery": {},
            "discovery_status": {}
        }

        # mDNS Scan
        try:
            # Use the existing discovery instance's zeroconf if available
            if _discovery_instance and _discovery_instance._zeroconf:
                zeroconf = _discovery_instance._zeroconf.zeroconf

                common_services = [
                    "_http._tcp.local.",
                    "_https._tcp.local.",
                    "_device._tcp.local.",
                    "_tuya._tcp.local.",
                    "_smartlife._tcp.local.",
                    "_iot._tcp.local.",
                    "_homekit._tcp.local.",
                    "_miio._tcp.local.",
                ]

                for service_type in common_services:
                    try:
                        async_service_info = AsyncServiceInfo(service_type, service_type)
                        await async_service_info.async_request(zeroconf, timeout=2000)
                        service_info = async_service_info

                        if service_info:
                            results["mDNS_services"][service_type] = [str(service_info)]
                    except Exception as e:
                        _LOGGER.debug(f"Failed to get service info for {service_type}: {e}")
            else:
                results["mDNS_services"]["error"] = ["Discovery service not active"]
        except Exception as e:
            results["mDNS_services"]["error"] = [f"mDNS scan failed: {e}"]

        # UDP Discovery Test
        try:
            udp_devices = []

            # Quick UDP discovery test
            loop = asyncio.get_running_loop()

            async def test_udp_listener() -> list[dict[str, Any]]:
                discovered: list[dict[str, Any]] = []

                def device_callback(device_info: dict[str, Any]) -> None:
                    discovered.append(device_info)

                listeners = []
                for port in UDP_PORTS:
                    try:
                        transport, protocol = await loop.create_datagram_endpoint(
                            lambda: TuyaUDPDiscovery(device_callback),
                            local_addr=('0.0.0.0', port),
                            allow_broadcast=True
                        )
                        listeners.append((transport, protocol))
                    except Exception as e:
                        _LOGGER.debug(f"Failed to bind UDP port {port}: {e}")

                # Wait 3 seconds for broadcasts
                await asyncio.sleep(3)

                # Close listeners
                for transport, protocol in listeners:
                    transport.close()

                return discovered

            udp_devices = await test_udp_listener()
            results["UDP_discovery"]["devices_found"] = len(udp_devices)
            results["UDP_discovery"]["devices"] = udp_devices

        except Exception as e:
            results["UDP_discovery"]["error"] = f"UDP test failed: {e}"

        # Discovery status
        if _discovery_instance:
            results["discovery_status"]["active"] = True
            results["discovery_status"]["mDNS_browsers"] = len(_discovery_instance._browsers)
            results["discovery_status"]["UDP_listeners"] = len(_discovery_instance._udp_listeners)
            results["discovery_status"]["discovered_devices"] = len(_discovery_instance.discovered_devices)
        else:
            results["discovery_status"]["active"] = False

        return results

    except Exception as e:
        _LOGGER.error(f"Network scan failed: {e}")
        return {"error": f"Debug scan failed: {e}"}