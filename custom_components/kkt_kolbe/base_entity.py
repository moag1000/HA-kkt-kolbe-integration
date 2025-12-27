"""Base entity for KKT Kolbe devices."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class KKTBaseEntity(CoordinatorEntity[dict[str, Any]]):
    """Base entity for all KKT Kolbe entities."""

    _attr_has_entity_name = True

    # Exclude non-historical attributes from database recording (HA 2024.6+)
    # This reduces database size by not recording frequently changing diagnostic data
    _unrecorded_attributes = frozenset({
        "raw_dp_data",
        "last_update",
        "data_point",
        "device_id",
        "zone",
        "connection_status",
    })

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: ConfigEntry,
        config: dict[str, Any],
        platform: str,
        zone: int | None = None,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)

        self._entry = entry
        self._config = config
        self._platform = platform
        self._zone = zone

        # Extract common configuration
        self._dp = config["dp"]
        self._name = config["name"]

        # State caching to prevent "unknown" values when DPs are temporarily unavailable
        self._cached_value = None
        self._last_update_time = None

        # Set up entity attributes
        self._setup_entity_attributes()

        # Device info will be built as property when needed (self.hass not available in __init__)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this entity."""
        # Don't cache if hass is not available yet - rebuild once it is
        if not self.hass:
            return self._build_device_info()

        # Cache device info once hass is available
        if not hasattr(self, '_device_info_cached') or self._device_info_cached is None:
            self._device_info_cached = self._build_device_info()
        return self._device_info_cached

    def _setup_entity_attributes(self) -> None:
        """Set up common entity attributes."""
        # Generate unique ID
        if self._zone is not None:
            self._attr_unique_id = (
                f"{self._entry.entry_id}_{self._platform}_zone{self._zone}_"
                f"{self._name.lower().replace(' ', '_')}"
            )
        else:
            self._attr_unique_id = (
                f"{self._entry.entry_id}_{self._platform}_"
                f"{self._name.lower().replace(' ', '_')}"
            )

        # Set translation key if provided (Gold Quality requirement)
        translation_key = self._config.get("translation_key")
        if translation_key:
            self._attr_translation_key = translation_key
            # When using translation_key, don't set name (HA uses translation)
        else:
            # Fallback to direct name if no translation key
            self._attr_name = self._name

        # Set device class if provided
        self._attr_device_class = self._config.get("device_class")

        # Set entity category if provided
        entity_category = self._config.get("entity_category")
        if entity_category:
            from homeassistant.helpers.entity import EntityCategory
            if hasattr(EntityCategory, entity_category.upper()):
                self._attr_entity_category = getattr(EntityCategory, entity_category.upper())

        # Disable advanced/diagnostic entities by default (Gold Tier requirement)
        if self._config.get("advanced", False) or entity_category == "diagnostic":
            self._attr_entity_registry_enabled_default = False

    def _build_device_info(self) -> DeviceInfo:
        """Build standardized device info using KNOWN_DEVICES."""
        from .device_types import KNOWN_DEVICES, CATEGORY_HOOD, CATEGORY_COOKTOP

        # Get device data from hass.data (now available via property access)
        if not self.hass:
            device_data = {}
            device_type_key = "auto"
        else:
            device_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {})
            device_type_key = device_data.get("device_type", "auto")

        # Extract device information
        device_id = self._entry.data.get("device_id", "unknown")
        ip_address = self._entry.data.get("ip_address", "unknown")

        # Get device info from KNOWN_DEVICES (HA 2024.6+ model ID support)
        if device_type_key in KNOWN_DEVICES:
            device_info = KNOWN_DEVICES[device_type_key]
            model_id = device_info.get("model_id", device_type_key)
            device_name = device_info.get("name", "KKT Kolbe Device")
            category = device_info.get("category", CATEGORY_HOOD)

            if category == CATEGORY_COOKTOP:
                device_type = "Induction Cooktop"
            else:
                device_type = "Range Hood"
        else:
            # Fallback for unknown devices
            model_id = "unknown"
            device_name = "KKT Kolbe Device"
            device_type = "Kitchen Appliance"

        return DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer="KKT Kolbe",
            model=model_id,  # Use model_id from KNOWN_DEVICES
            sw_version=self._get_software_version(),
            hw_version=self._get_hardware_version(),
            configuration_url=f"http://{ip_address}",
            suggested_area="Kitchen",
        )

    def _get_software_version(self) -> str:
        """Get software version from device data."""
        # Try to get protocol version from device via coordinator
        if hasattr(self.coordinator, 'device') and self.coordinator.device:
            device = self.coordinator.device
            # Check for detected protocol version
            version = getattr(device, 'version', None)
            if version and version != "auto":
                return f"Tuya Protocol {version}"
            # Check connection stats for detected version
            if hasattr(device, '_connection_stats'):
                detected = device._connection_stats.get("protocol_version_detected")
                if detected:
                    return f"Tuya Protocol {detected}"

        # Try to get from entry data (may be set during discovery)
        version = self._entry.data.get("version")
        if version and version != "auto":
            return f"Tuya Protocol {version}"

        # Use integration version as fallback
        from .const import VERSION
        return f"v{VERSION}"

    def _get_hardware_version(self) -> str:
        """Get hardware version from device data."""
        from .device_types import KNOWN_DEVICES

        # Try to get device_type from runtime_data or entry.data
        device_type = None
        product_name = None

        if self.hass:
            runtime_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {})
            device_type = runtime_data.get("device_type", "")
            product_name = runtime_data.get("product_name", "")

        # Fallback to entry.data
        if not device_type or device_type in ("auto", "unknown", ""):
            device_type = self._entry.data.get("device_type", "")
        if not product_name or product_name in ("auto", "unknown", ""):
            product_name = self._entry.data.get("product_name", "")

        # Use model_id from KNOWN_DEVICES if available
        if device_type and device_type in KNOWN_DEVICES:
            model_id = KNOWN_DEVICES[device_type].get("model_id", "")
            if model_id:
                return model_id.upper()

        # Use device_type as hardware identifier if valid
        if device_type and device_type not in ("auto", "unknown", ""):
            return device_type.replace("_", " ").title()

        # Fallback to product_name pattern matching
        if product_name:
            product_upper = product_name.upper()
            if "IND7705HC" in product_upper:
                return "IND7705HC"
            elif "HERMES" in product_upper:
                return "HERMES"
            elif "ECCO" in product_upper:
                return "ECCO HCM"
            elif "SOLO" in product_upper:
                return "SOLO HCM"

        # Try device_id first 8 chars as hardware identifier
        device_id = self._entry.data.get("device_id", "")
        if device_id:
            return device_id[:8].upper()

        return "KKT Device"

    def _get_suggested_area(self) -> str:
        """Get suggested area for the device."""
        if self.hass:
            product_name = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {}).get("product_name", "")
        else:
            product_name = ""

        if "IND7705HC" in product_name:
            return "Kitchen"
        elif "HERMES" in product_name:
            return "Kitchen"

        return "Kitchen"


    @property
    def available(self) -> bool:
        """Return if entity is available.

        Entities are available if:
        1. We have current data from coordinator, OR
        2. We have a cached value from previous successful update, OR
        3. We're in initial startup phase (coordinator hasn't had consecutive failures)

        Entities only become unavailable after persistent connection issues.
        """
        # Check coordinator device state if available (KKTKolbeUpdateCoordinator)
        if hasattr(self.coordinator, 'is_device_available'):
            # Use coordinator's device state which tracks consecutive failures
            device_available = self.coordinator.is_device_available

            # If device is online, we're always available
            if device_available:
                return True

            # If device is offline but we have cached data, still report as available
            # This prevents flapping during temporary connection issues
            if self._cached_value is not None:
                return True

            # If device is offline and no cached data, check if we ever had data
            if self.coordinator.data is not None and len(self.coordinator.data) > 0:
                return True

        # Fallback for other coordinators: check if we have any data
        has_data = self.coordinator.data is not None and len(self.coordinator.data) > 0
        has_cached_value = self._cached_value is not None

        # More lenient: available if we have data OR cache OR no failures yet
        is_available = has_data or has_cached_value or self.coordinator.last_update_success

        if not is_available:
            _LOGGER.debug(
                f"Entity {self._attr_unique_id} unavailable: "
                f"last_update_success={self.coordinator.last_update_success}, "
                f"has_data={has_data}, has_cached_value={has_cached_value}, "
                f"data_keys={list(self.coordinator.data.keys()) if self.coordinator.data else 'None'}"
            )

        return is_available

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Debug logging for coordinator updates
        if _LOGGER.isEnabledFor(logging.DEBUG):
            data_keys = list(self.coordinator.data.keys()) if self.coordinator.data else []
            _LOGGER.debug(
                f"Coordinator update for {self._attr_unique_id}: "
                f"DP {self._dp}, Zone: {self._zone}, "
                f"Available DPs: {data_keys}"
            )

        # Update cached state from coordinator data
        self._update_cached_state()
        self.async_write_ha_state()

    def _update_cached_state(self) -> None:
        """Update the cached state from coordinator data."""
        # This method should be overridden by specific entity types
        pass

    def _get_data_point_value(self, dp: int | None = None) -> Any:
        """Get value for a specific data point, with zone support and state caching."""
        data_point = dp if dp is not None else self._dp

        # If this entity has a zone, use zone-aware data point extraction
        if self._zone is not None:
            return self._get_zone_data_point_value_cached(data_point, self._zone)

        # Standard data point extraction for non-zone entities with caching
        if not self.coordinator.data:
            _LOGGER.debug(f"Entity {self._attr_unique_id}: No coordinator data available, using cached value")
            return self._cached_value

        # Get the DPS dictionary - coordinator may return data with DPs under 'dps' key
        # or directly at top level depending on the coordinator type
        dps_data = self.coordinator.data.get("dps", self.coordinator.data)

        # Try both string and integer keys for compatibility
        value = dps_data.get(str(data_point))
        if value is None:
            value = dps_data.get(data_point)

        if value is None:
            # DP not available in current update - use cached value instead of None
            _LOGGER.debug(
                f"Entity {self._attr_unique_id}: DP {data_point} not in current update. "
                f"Available DPs: {list(dps_data.keys())}. Using cached value: {self._cached_value}"
            )
            return self._cached_value
        else:
            # DP is available - update cache and return new value
            import datetime
            self._cached_value = value
            self._last_update_time = datetime.datetime.now()
            _LOGGER.debug(f"Entity {self._attr_unique_id}: DP {data_point} = {value} (type: {type(value)}) - cached")

        return value

    def _get_zone_data_point_value_cached(self, dp: int, zone: int | None = None) -> Any:
        """Get value for a zone-specific data point with bitfield extraction and caching."""
        zone_number = zone if zone is not None else self._zone
        if zone_number is None:
            return self._cached_value

        if not self.coordinator.data:
            _LOGGER.debug(f"Entity {self._attr_unique_id}: No coordinator data available, using cached value")
            return self._cached_value

        # Get the DPS dictionary - coordinator may return data with DPs under 'dps' key
        dps_data = self.coordinator.data.get("dps", self.coordinator.data)

        raw_value = dps_data.get(dp)
        if raw_value is None:
            raw_value = dps_data.get(str(dp))

        if raw_value is None:
            # DP not available in current update - use cached value
            _LOGGER.debug(
                f"Entity {self._attr_unique_id}: Zone DP {dp} not in current update. "
                f"Available DPs: {list(dps_data.keys())}. Using cached value: {self._cached_value}"
            )
            return self._cached_value

        # Use bitfield_utils for Base64 RAW data extraction
        if isinstance(raw_value, str):
            # This is likely a Base64-encoded RAW string
            from .bitfield_utils import extract_zone_value_from_bitfield
            try:
                value = extract_zone_value_from_bitfield(raw_value, zone_number)
                _LOGGER.debug(f"Zone {zone_number} DP {dp}: Extracted value {value} from Base64 data - cached")

                # Update cache
                import datetime
                self._cached_value = value
                self._last_update_time = datetime.datetime.now()
                return value
            except Exception as e:
                _LOGGER.error(f"Failed to extract zone {zone_number} from DP {dp}: {e}")
                return self._cached_value

        # Fall back to bit extraction for integer/byte bitfields
        if isinstance(raw_value, int):
            # For integer bitfields, extract zone bit
            zone_bit = 1 << (zone_number - 1)
            value = bool(raw_value & zone_bit)
        elif isinstance(raw_value, (bytes, bytearray)):
            # For byte arrays, check individual bytes/bits
            byte_index = (zone_number - 1) // 8
            bit_index = (zone_number - 1) % 8
            if byte_index < len(raw_value):
                value = bool(raw_value[byte_index] & (1 << bit_index))
            else:
                return self._cached_value
        else:
            return self._cached_value

        # Update cache and return new value
        import datetime
        self._cached_value = value
        self._last_update_time = datetime.datetime.now()
        _LOGGER.debug(f"Zone {zone_number} DP {dp}: Extracted value {value} - cached")
        return value

    def _get_zone_data_point_value(self, dp: int, zone: int | None = None) -> Any:
        """Get value for a zone-specific data point with bitfield extraction."""
        if not self.coordinator.data:
            return None

        # Get the DPS dictionary - coordinator may return data with DPs under 'dps' key
        dps_data = self.coordinator.data.get("dps", self.coordinator.data)

        raw_value = dps_data.get(dp)
        if raw_value is None:
            raw_value = dps_data.get(str(dp))
        if raw_value is None:
            return None

        zone_number = zone if zone is not None else self._zone
        if zone_number is None:
            return raw_value

        # Use bitfield_utils for Base64 RAW data extraction
        if isinstance(raw_value, str):
            # This is likely a Base64-encoded RAW string
            from .bitfield_utils import extract_zone_value_from_bitfield
            try:
                value = extract_zone_value_from_bitfield(raw_value, zone_number)
                _LOGGER.debug(f"Zone {zone_number} DP {dp}: Extracted value {value} from Base64 data")
                return value
            except Exception as e:
                _LOGGER.error(f"Failed to extract zone {zone_number} from DP {dp}: {e}")
                return None

        # Fall back to bit extraction for integer/byte bitfields
        if isinstance(raw_value, int):
            # For integer bitfields, extract zone bit
            zone_bit = 1 << (zone_number - 1)
            return bool(raw_value & zone_bit)
        elif isinstance(raw_value, (bytes, bytearray)):
            # For byte arrays, check individual bytes/bits
            byte_index = (zone_number - 1) // 8
            bit_index = (zone_number - 1) % 8
            if byte_index < len(raw_value):
                return bool(raw_value[byte_index] & (1 << bit_index))

        return None

    async def _async_set_data_point(self, dp: int, value: Any) -> None:
        """Set a data point value through the coordinator."""
        try:
            await self.coordinator.async_set_data_point(dp, value)
            _LOGGER.debug(
                "Set data point %d to %s for %s",
                dp, value, self._attr_unique_id
            )
        except Exception as exc:
            _LOGGER.error(
                "Failed to set data point %d to %s for %s: %s",
                dp, value, self._attr_unique_id, exc
            )
            raise

    def _log_entity_state(self, action: str, additional_info: str = "") -> None:
        """Log entity state changes for debugging."""
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "%s: %s %s (DP: %d, Zone: %s) %s",
                action,
                self._platform,
                self._name,
                self._dp,
                self._zone if self._zone else "N/A",
                additional_info
            )


class KKTZoneBaseEntity(KKTBaseEntity):
    """Base entity for zone-specific KKT Kolbe entities."""

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        config: dict[str, Any],
        platform: str,
    ):
        """Initialize the zone base entity."""
        zone = config.get("zone")
        if zone is None:
            raise ValueError("Zone configuration missing for zone entity")

        super().__init__(coordinator, entry, config, platform, zone)

        # Zone entities are typically diagnostic
        from homeassistant.helpers.entity import EntityCategory
        if not hasattr(self, '_attr_entity_category'):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "zone": self._zone,
            "data_point": self._dp,
            "device_id": self._entry.data.get("device_id", "unknown")[:8],
        }