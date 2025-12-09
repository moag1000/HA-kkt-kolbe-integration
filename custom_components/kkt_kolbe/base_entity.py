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
        if not hasattr(self, '_device_info_cached'):
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

        # Set entity name
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
        """Build standardized device info."""
        # Get device data from hass.data (now available via property access)
        if not self.hass:
            # Fallback for cases where hass is not yet available
            device_data = {}
            product_name = "KKT Kolbe Device"
        else:
            device_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {})
            product_name = device_data.get("product_name", "KKT Kolbe Device")

        # Extract device information
        device_id = self._entry.data.get("device_id", "unknown")
        ip_address = self._entry.data.get("ip_address", "unknown")

        # Determine device type and model info
        if "IND7705HC" in product_name:
            device_type = "Induction Cooktop"
            model = "IND7705HC"
            manufacturer = "KKT Kolbe"
        elif "HERMES" in product_name and "STYLE" in product_name:
            device_type = "Range Hood"
            model = "HERMES & STYLE"
            manufacturer = "KKT Kolbe"
        else:
            device_type = "Kitchen Appliance"
            model = product_name
            manufacturer = "KKT Kolbe"

        return DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=f"KKT Kolbe {device_type}",
            manufacturer=manufacturer,
            model=model,
            sw_version=self._get_software_version(),
            hw_version=self._get_hardware_version(),
            configuration_url=f"http://{ip_address}",
            suggested_area=self._get_suggested_area(),
        )

    def _get_software_version(self) -> str:
        """Get software version from device data."""
        # Try to get from coordinator data or use integration version
        if hasattr(self.coordinator, 'data') and self.coordinator.data:
            # Look for firmware version in device data
            if isinstance(self.coordinator.data, dict):
                fw_version = self.coordinator.data.get("firmware_version")
                if fw_version:
                    return str(fw_version)

        # Fallback to integration version from manifest
        return "Unknown"

    def _get_hardware_version(self) -> str:
        """Get hardware version from device data."""
        # Try to get from coordinator data
        if hasattr(self.coordinator, 'data') and self.coordinator.data:
            if isinstance(self.coordinator.data, dict):
                hw_version = self.coordinator.data.get("hardware_version")
                if hw_version:
                    return str(hw_version)

        # Fallback based on product name
        if self.hass:
            product_name = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {}).get("product_name", "")
        else:
            product_name = ""
        if "IND7705HC" in product_name:
            return "IND7705HC"
        elif "HERMES" in product_name:
            return "HERMES_STYLE"

        return "Unknown"

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
        """Return if entity is available."""
        # Check if coordinator has valid data OR we have cached value
        has_data = self.coordinator.data is not None and len(self.coordinator.data) > 0
        has_cached_value = self._cached_value is not None

        # Entity is available if coordinator is working AND (has current data OR cached value)
        is_available = self.coordinator.last_update_success and (has_data or has_cached_value)

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

        # Try both string and integer keys for compatibility
        value = self.coordinator.data.get(str(data_point))
        if value is None:
            value = self.coordinator.data.get(data_point)

        if value is None:
            # DP not available in current update - use cached value instead of None
            _LOGGER.debug(
                f"Entity {self._attr_unique_id}: DP {data_point} not in current update. "
                f"Available DPs: {list(self.coordinator.data.keys())}. Using cached value: {self._cached_value}"
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

        raw_value = self.coordinator.data.get(dp)
        if raw_value is None:
            raw_value = self.coordinator.data.get(str(dp))

        if raw_value is None:
            # DP not available in current update - use cached value
            _LOGGER.debug(
                f"Entity {self._attr_unique_id}: Zone DP {dp} not in current update. "
                f"Available DPs: {list(self.coordinator.data.keys())}. Using cached value: {self._cached_value}"
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

        raw_value = self.coordinator.data.get(dp)
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