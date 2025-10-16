"""mDNS discovery for KKT Kolbe devices."""
import asyncio
import logging
from typing import Dict, List, Optional
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
from zeroconf.asyncio import AsyncZeroconf

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.network import get_url
from homeassistant.components import zeroconf

from .const import DOMAIN, MODELS

_LOGGER = logging.getLogger(__name__)

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

class KKTKolbeDiscovery(ServiceListener):
    """Discover KKT Kolbe devices via mDNS."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the discovery service."""
        self.hass = hass
        self.discovered_devices: Dict[str, Dict] = {}
        self._zeroconf: Optional[AsyncZeroconf] = None
        self._browsers: List[ServiceBrowser] = []

    async def async_start(self) -> None:
        """Start mDNS discovery."""
        try:
            self._zeroconf = AsyncZeroconf()

            _LOGGER.info(f"Starting mDNS discovery for {len(TUYA_SERVICE_TYPES)} service types...")
            for service_type in TUYA_SERVICE_TYPES:
                _LOGGER.debug(f"Starting browser for service type: {service_type}")
                browser = ServiceBrowser(
                    self._zeroconf.zeroconf,
                    service_type,
                    self
                )
                self._browsers.append(browser)

            _LOGGER.info(f"Started KKT Kolbe mDNS discovery with {len(self._browsers)} browsers")

        except Exception as e:
            _LOGGER.error(f"Failed to start mDNS discovery: {e}", exc_info=True)

    async def async_stop(self) -> None:
        """Stop mDNS discovery."""
        for browser in self._browsers:
            browser.cancel()
        self._browsers.clear()

        if self._zeroconf:
            await self._zeroconf.async_close()
            self._zeroconf = None

        _LOGGER.info("Stopped KKT Kolbe mDNS discovery")

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is discovered."""
        asyncio.create_task(self._async_add_service(zc, type_, name))

    async def _async_add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Handle discovered service asynchronously."""
        try:
            info = zc.get_service_info(type_, name)
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

        # First check if this looks like a Tuya device ID pattern
        name_lower = info.name.lower()

        # Tuya device IDs often start with bf followed by hex characters
        if name_lower.startswith('bf') and len(name_lower) >= 20:
            _LOGGER.info(f"Found potential Tuya device: {info.name}")
            # For Tuya devices, check TXT records for model info
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
                    key_str = key.decode('utf-8').lower()
                    value_str = value.decode('utf-8').lower()
                    txt_data[key_str] = value_str
                except UnicodeDecodeError:
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
                key_str = key.decode('utf-8').lower()
                value_str = value.decode('utf-8')
                txt_data[key_str] = value_str
            except UnicodeDecodeError:
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

        # For debugging: log all Tuya devices for manual verification
        _LOGGER.info(f"Unidentified Tuya device: {info.name} - Model: {model}, DeviceID: {device_id}")
        return False

    def _extract_device_info(self, info) -> Optional[Dict]:
        """Extract device information from mDNS record."""
        if not info:
            return None

        device_info = {
            "name": info.name,
            "host": str(info.parsed_addresses()[0]) if info.parsed_addresses() else None,
            "port": info.port,
        }

        # Extract TXT record information
        if hasattr(info, 'properties') and info.properties:
            for key, value in info.properties.items():
                try:
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

                except UnicodeDecodeError:
                    continue

        # Determine device type from model
        model = device_info.get("model", "")
        if model in MODELS:
            device_info["device_type"] = MODELS[model]["category"]
            device_info["product_name"] = MODELS[model]["name"]

        return device_info if device_info.get("host") else None

    async def _async_trigger_discovery(self, device_info: Dict) -> None:
        """Trigger Home Assistant discovery flow."""
        try:
            discovery_info = {
                "host": device_info["host"],
                "device_id": device_info.get("device_id"),
                "model": device_info.get("model"),
                "name": device_info.get("product_name", device_info["name"]),
                "discovered_via": "mDNS",
            }

            # Create a unique identifier for this discovery
            unique_id = device_info.get("device_id", device_info["host"])

            # Trigger automatic discovery flow
            from homeassistant.helpers import discovery_flow

            await discovery_flow.async_create_flow(
                self.hass,
                DOMAIN,
                context={"source": "zeroconf"},
                data=discovery_info,
            )

            _LOGGER.info(f"Triggered automatic discovery for KKT device: {device_info['name']}")

        except Exception as e:
            _LOGGER.error(f"Failed to trigger discovery: {e}", exc_info=True)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is removed."""
        # Could implement device removal logic here
        pass

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is updated."""
        # Re-process the service in case of updates
        self.add_service(zc, type_, name)


# Global discovery instance
_discovery_instance: Optional[KKTKolbeDiscovery] = None


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


def get_discovered_devices() -> Dict[str, Dict]:
    """Get currently discovered devices."""
    global _discovery_instance

    if _discovery_instance:
        return _discovery_instance.discovered_devices.copy()
    return {}


def add_test_device() -> None:
    """Add a test device for debugging (development only)."""
    global _discovery_instance

    if _discovery_instance:
        test_device = {
            "device_id": "test_kkt_device_12345",
            "host": "192.168.1.100",
            "name": "Test KKT HERMES & STYLE",
            "model": "e1k6i0zo",
            "device_type": "hood",
            "product_name": "Test HERMES & STYLE",
            "discovered_via": "test_simulation"
        }
        _discovery_instance.discovered_devices["test_device"] = test_device
        _LOGGER.warning("Added test device for debugging purposes!")


async def debug_scan_network() -> Dict[str, List[str]]:
    """Scan network for all mDNS services (debugging only)."""
    try:
        from zeroconf import Zeroconf

        zeroconf = Zeroconf()
        services = {}

        # Scan common service types
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
            service_names = zeroconf.get_service_info(service_type, timeout=1)
            if service_names:
                services[service_type] = [str(service_names)]

        zeroconf.close()
        return services

    except Exception as e:
        _LOGGER.error(f"Network scan failed: {e}")
        return {}