"""Smart Discovery for KKT Kolbe - combines local discovery with API data."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .api_manager import GlobalAPIManager
from .discovery import get_discovered_devices, async_start_discovery

_LOGGER = logging.getLogger(__name__)


class SmartDiscoveryResult:
    """Result of smart discovery combining local and API data."""

    def __init__(
        self,
        device_id: str,
        name: str,
        ip_address: str | None = None,
        local_key: str | None = None,
        product_name: str | None = None,
        device_type: str = "auto",
        tuya_category: str | None = None,
        discovered_via: str = "unknown",
        api_enriched: bool = False,
        ready_to_add: bool = False,
        friendly_type: str | None = None,
    ):
        """Initialize smart discovery result."""
        self.device_id = device_id
        self.name = name
        self.ip_address = ip_address
        self.local_key = local_key
        self.product_name = product_name
        self.device_type = device_type
        self.tuya_category = tuya_category
        self.discovered_via = discovered_via
        self.api_enriched = api_enriched
        self.ready_to_add = ready_to_add
        self.friendly_type = friendly_type

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for config flow."""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "ip_address": self.ip_address,
            "ip": self.ip_address,  # Alias for compatibility
            "local_key": self.local_key,
            "product_name": self.product_name,
            "device_type": self.device_type,
            "tuya_category": self.tuya_category,
            "discovered_via": self.discovered_via,
            "api_enriched": self.api_enriched,
            "ready_to_add": self.ready_to_add,
            "friendly_type": self.friendly_type,
        }

    @property
    def display_label(self) -> str:
        """Get display label for UI."""
        status = "Ready" if self.ready_to_add else "Needs Local Key"
        icon = "✅" if self.ready_to_add else "🔑"
        ip_str = self.ip_address or "Unknown IP"

        # Use friendly_type if available, otherwise fall back to name or device_id
        display_name = self.friendly_type or self.name or f"Device {self.device_id[:8]}"

        return f"{icon} {display_name} ({ip_str}) - {status}"


class SmartDiscovery:
    """Smart discovery combining local UDP/mDNS with Tuya Cloud API."""

    def __init__(self, hass: HomeAssistant):
        """Initialize smart discovery."""
        self.hass = hass
        self._api_manager = GlobalAPIManager(hass)
        self._discovered_devices: dict[str, SmartDiscoveryResult] = {}

    async def async_discover(
        self,
        local_timeout: float = 6.0,
        enrich_with_api: bool = True,
    ) -> dict[str, SmartDiscoveryResult]:
        """Run smart discovery.

        1. Start local UDP/mDNS discovery
        2. If API credentials available, fetch device list from API
        3. Match local devices with API data
        4. Return enriched device list

        Args:
            local_timeout: Timeout for local discovery in seconds
            enrich_with_api: Whether to fetch additional data from API

        Returns:
            Dictionary of device_id -> SmartDiscoveryResult
        """
        self._discovered_devices.clear()

        # Step 1: Run local discovery
        _LOGGER.info("Smart Discovery: Starting local device scan...")
        await async_start_discovery(self.hass)
        await asyncio.sleep(local_timeout)

        local_devices = get_discovered_devices()
        _LOGGER.info(f"Smart Discovery: Found {len(local_devices)} local devices")

        # Convert local devices to SmartDiscoveryResult
        for device_id, device_info in local_devices.items():
            # Try to detect device type from device_id pattern (even without API)
            device_type = device_info.get("device_type", "auto")
            product_name = device_info.get("product_name")
            friendly_type = None

            # Use device_id pattern matching to identify device
            if device_id:
                from .device_types import KNOWN_DEVICES, find_device_by_device_id
                detected_info = find_device_by_device_id(device_id)
                if detected_info:
                    friendly_type = detected_info.get("name")
                    if detected_info.get("product_names"):
                        product_name = detected_info["product_names"][0]
                    # Find the device key
                    for key, info in KNOWN_DEVICES.items():
                        if device_id in info.get("device_ids", []):
                            device_type = key
                            break
                        for pattern in info.get("device_id_patterns", []):
                            if device_id.startswith(pattern):
                                device_type = key
                                break
                    _LOGGER.info(f"Smart Discovery: Detected {friendly_type} from device_id pattern")

            self._discovered_devices[device_id] = SmartDiscoveryResult(
                device_id=device_id,
                name=device_info.get("name", f"KKT Device {device_id[:8]}"),
                ip_address=device_info.get("ip") or device_info.get("ip_address"),
                product_name=product_name,
                device_type=device_type,
                discovered_via=device_info.get("discovered_via", "local"),
                friendly_type=friendly_type,
            )

        # Step 2: Enrich with API data if credentials available
        if enrich_with_api and self._api_manager.has_stored_credentials():
            await self._enrich_with_api_data()

        # Step 3: Check which devices are ready to add
        self._update_ready_status()

        return self._discovered_devices

    async def async_discover_api_only(self) -> dict[str, SmartDiscoveryResult]:
        """Discover devices using only the API (no local scan).

        Useful when:
        - User has API credentials configured
        - Local discovery isn't finding devices
        - Devices are on a different subnet

        Returns:
            Dictionary of device_id -> SmartDiscoveryResult
        """
        self._discovered_devices.clear()

        if not self._api_manager.has_stored_credentials():
            _LOGGER.warning("Smart Discovery: No API credentials available")
            return {}

        _LOGGER.info("Smart Discovery: Fetching devices from API...")
        api_devices = await self._api_manager.get_kkt_devices_from_api()

        for device in api_devices:
            device_id = device.get("id", "")
            if not device_id:
                continue

            # Detect device type from API data
            device_type, internal_product_name, friendly_type = self._detect_device_type(device)

            self._discovered_devices[device_id] = SmartDiscoveryResult(
                device_id=device_id,
                name=device.get("name", f"KKT Device {device_id[:8]}"),
                ip_address=device.get("ip"),
                local_key=device.get("local_key"),
                product_name=internal_product_name,
                device_type=device_type,
                tuya_category=device.get("category"),
                discovered_via="API",
                api_enriched=True,
                ready_to_add=bool(device.get("local_key")),
                friendly_type=friendly_type,
            )

        _LOGGER.info(f"Smart Discovery: Found {len(self._discovered_devices)} devices via API")
        return self._discovered_devices

    async def _enrich_with_api_data(self) -> None:
        """Enrich locally discovered devices with API data."""
        try:
            _LOGGER.info("Smart Discovery: Enriching with API data...")
            api_devices = await self._api_manager.get_kkt_devices_from_api()

            # Create lookup by device_id
            api_lookup = {d.get("id", ""): d for d in api_devices}

            # Also add any API-only devices not found locally
            for api_device in api_devices:
                device_id = api_device.get("id", "")
                if not device_id:
                    continue

                if device_id in self._discovered_devices:
                    # Enrich existing local device with API data
                    result = self._discovered_devices[device_id]
                    result.local_key = api_device.get("local_key")
                    result.tuya_category = api_device.get("category")
                    result.api_enriched = True

                    # Update device type if we can detect it from API
                    # BUT only if not already correctly detected from device_id pattern
                    device_type, product_name, friendly_type = self._detect_device_type(api_device)
                    if device_type != "auto":
                        # Only overwrite if current device_type is "auto" or not in KNOWN_DEVICES
                        from .device_types import KNOWN_DEVICES
                        current_type = result.device_type
                        if current_type == "auto" or current_type not in KNOWN_DEVICES:
                            result.device_type = device_type
                            result.product_name = product_name
                            result.friendly_type = friendly_type
                            _LOGGER.debug(f"Updated device_type from API: {device_type}")
                        else:
                            _LOGGER.debug(f"Keeping existing device_type: {current_type} (API suggested: {device_type})")

                    # Prefer API name if more descriptive
                    api_name = api_device.get("name", "")
                    if api_name and len(api_name) > len(result.name):
                        result.name = api_name

                    has_key = bool(result.local_key)
                    _LOGGER.info(f"Enriched device {device_id[:8]}: {friendly_type}, "
                                f"local_key={'present' if has_key else 'MISSING'}")
                else:
                    # Add API-only device (not found locally)
                    device_type, product_name, friendly_type = self._detect_device_type(api_device)

                    self._discovered_devices[device_id] = SmartDiscoveryResult(
                        device_id=device_id,
                        name=api_device.get("name", f"KKT Device {device_id[:8]}"),
                        ip_address=api_device.get("ip"),
                        local_key=api_device.get("local_key"),
                        product_name=product_name,
                        device_type=device_type,
                        tuya_category=api_device.get("category"),
                        discovered_via="API",
                        api_enriched=True,
                        friendly_type=friendly_type,
                    )
                    _LOGGER.debug(f"Added API-only device {device_id[:8]}: {friendly_type}")

            _LOGGER.info(f"Smart Discovery: Enriched {len(api_devices)} devices with API data")

        except Exception as err:
            _LOGGER.warning(f"Smart Discovery: API enrichment failed: {err}")

    def _detect_device_type(self, api_device: dict[str, Any]) -> tuple[str, str, str]:
        """Detect device type from API response using KNOWN_DEVICES.

        Args:
            api_device: Device dict from Tuya API

        Returns:
            Tuple of (device_type, product_name, friendly_type)
        """
        from .device_types import KNOWN_DEVICES, find_device_by_product_name, find_device_by_device_id

        tuya_category = api_device.get("category", "").lower()
        api_product_name = api_device.get("product_name", "Unknown Device")
        device_name = api_device.get("name", "").lower()
        product_id = api_device.get("product_id", "")
        device_id = api_device.get("id", "")

        _LOGGER.debug(f"Smart Discovery detecting: product_id={product_id}, device_id={device_id[:12] if device_id else 'N/A'}, "
                      f"category={tuya_category}")

        # Method 1: Try to match by Tuya product_id (most accurate)
        if product_id:
            device_info = find_device_by_product_name(product_id)
            if device_info:
                for device_key, info in KNOWN_DEVICES.items():
                    if product_id in info.get("product_names", []):
                        friendly_type = info.get("name", device_key)
                        _LOGGER.info(f"Smart Discovery: Detected {friendly_type} by product_id")
                        return (device_key, product_id, friendly_type)

        # Method 2: Try to match by device_id pattern
        if device_id:
            device_info = find_device_by_device_id(device_id)
            if device_info:
                for device_key, info in KNOWN_DEVICES.items():
                    # Check exact match
                    if device_id in info.get("device_ids", []):
                        friendly_type = info.get("name", device_key)
                        _LOGGER.info(f"Smart Discovery: Detected {friendly_type} by device_id")
                        return (device_key, info["product_names"][0], friendly_type)
                    # Check pattern match
                    for pattern in info.get("device_id_patterns", []):
                        if device_id.startswith(pattern):
                            friendly_type = info.get("name", device_key)
                            _LOGGER.info(f"Smart Discovery: Detected {friendly_type} by device_id pattern")
                            return (device_key, info["product_names"][0], friendly_type)

        # Method 3: Category-based detection with keyword matching
        search_text = f"{api_product_name} {device_name}".lower()

        if tuya_category == "dcl":  # Cooktop category
            friendly_type = KNOWN_DEVICES.get("ind7705hc_cooktop", {}).get("name", "Induction Cooktop")
            return ("ind7705hc_cooktop", "ind7705hc_cooktop", friendly_type)
        elif tuya_category == "yyj":  # Hood category
            # Try to identify specific hood model
            if "solo" in search_text:
                friendly_type = KNOWN_DEVICES.get("solo_hcm_hood", {}).get("name", "SOLO HCM Hood")
                return ("solo_hcm_hood", "bgvbvjwomgbisd8x", friendly_type)
            elif "ecco" in search_text:
                friendly_type = KNOWN_DEVICES.get("ecco_hcm_hood", {}).get("name", "ECCO HCM Hood")
                return ("ecco_hcm_hood", "gwdgkteknzvsattn", friendly_type)
            elif "flat" in search_text:
                friendly_type = KNOWN_DEVICES.get("flat_hood", {}).get("name", "FLAT Hood")
                return ("flat_hood", "luoxakxm2vm9azwu", friendly_type)
            elif "hermes" in search_text:
                friendly_type = KNOWN_DEVICES.get("hermes_style_hood", {}).get("name", "HERMES & STYLE Hood")
                return ("hermes_style_hood", "ypaixllljc2dcpae", friendly_type)
            else:
                # Default hood
                friendly_type = KNOWN_DEVICES.get("default_hood", {}).get("name", "Range Hood")
                return ("default_hood", "default_hood", friendly_type)

        # Method 4: Fallback keyword detection
        if "ind" in search_text or "cooktop" in search_text or "kochfeld" in search_text:
            friendly_type = KNOWN_DEVICES.get("ind7705hc_cooktop", {}).get("name", "Induction Cooktop")
            return ("ind7705hc_cooktop", "ind7705hc_cooktop", friendly_type)
        elif any(kw in search_text for kw in ["hood", "hermes", "style", "ecco", "solo", "dunst", "abzug"]):
            if "solo" in search_text:
                friendly_type = KNOWN_DEVICES.get("solo_hcm_hood", {}).get("name", "SOLO HCM Hood")
                return ("solo_hcm_hood", "bgvbvjwomgbisd8x", friendly_type)
            elif "ecco" in search_text:
                friendly_type = KNOWN_DEVICES.get("ecco_hcm_hood", {}).get("name", "ECCO HCM Hood")
                return ("ecco_hcm_hood", "gwdgkteknzvsattn", friendly_type)
            friendly_type = KNOWN_DEVICES.get("default_hood", {}).get("name", "Range Hood")
            return ("default_hood", "default_hood", friendly_type)

        # Default: unknown device
        return ("auto", api_product_name, "KKT Kolbe Device")

    def _update_ready_status(self) -> None:
        """Update ready_to_add status for all devices."""
        for device_id, result in self._discovered_devices.items():
            # A device is ready to add if we have:
            # 1. Device ID (always have this)
            # 2. IP address (from local discovery or API)
            # 3. Local key (from API)
            result.ready_to_add = bool(
                result.device_id and
                result.ip_address and
                result.local_key
            )

    def get_ready_devices(self) -> dict[str, SmartDiscoveryResult]:
        """Get only devices that are ready to add (have all required info)."""
        return {
            device_id: result
            for device_id, result in self._discovered_devices.items()
            if result.ready_to_add
        }

    def get_pending_devices(self) -> dict[str, SmartDiscoveryResult]:
        """Get devices that need manual local key entry."""
        return {
            device_id: result
            for device_id, result in self._discovered_devices.items()
            if not result.ready_to_add
        }


async def async_smart_discover(
    hass: HomeAssistant,
    timeout: float = 6.0,
) -> dict[str, SmartDiscoveryResult]:
    """Convenience function for smart discovery.

    Args:
        hass: Home Assistant instance
        timeout: Local discovery timeout

    Returns:
        Dictionary of device_id -> SmartDiscoveryResult
    """
    smart_discovery = SmartDiscovery(hass)
    return await smart_discovery.async_discover(local_timeout=timeout)


async def async_get_configured_device_ids(hass: HomeAssistant) -> set[str]:
    """Get device IDs that are already configured.

    Args:
        hass: Home Assistant instance

    Returns:
        Set of configured device IDs
    """
    from .const import DOMAIN

    configured_ids = set()
    for entry in hass.config_entries.async_entries(DOMAIN):
        device_id = entry.data.get("device_id")
        if device_id:
            configured_ids.add(device_id)

    return configured_ids
