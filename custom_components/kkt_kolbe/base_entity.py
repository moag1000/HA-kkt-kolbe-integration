"""Base entity for KKT Kolbe devices."""
import logging
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class KKTBaseEntity(CoordinatorEntity):
    """Base entity for all KKT Kolbe entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        config: Dict[str, Any],
        platform: str,
        zone: Optional[int] = None,
    ):
        """Initialize the base entity."""
        super().__init__(coordinator)

        self._entry = entry
        self._config = config
        self._platform = platform
        self._zone = zone

        # Extract common configuration
        self._dp = config["dp"]
        self._name = config["name"]

        # Set up entity attributes
        self._setup_entity_attributes()

        # Build device info
        self._device_info = self._build_device_info()

    def _setup_entity_attributes(self):
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

    def _build_device_info(self) -> DeviceInfo:
        """Build standardized device info."""
        # Get device data from hass.data
        device_data = self.hass.data[DOMAIN][self._entry.entry_id]
        product_name = device_data.get("product_name", "Unknown")

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

        # Fallback to integration version
        return "1.5.2"

    def _get_hardware_version(self) -> str:
        """Get hardware version from device data."""
        # Try to get from coordinator data
        if hasattr(self.coordinator, 'data') and self.coordinator.data:
            if isinstance(self.coordinator.data, dict):
                hw_version = self.coordinator.data.get("hardware_version")
                if hw_version:
                    return str(hw_version)

        # Fallback based on product name
        product_name = self.hass.data[DOMAIN][self._entry.entry_id].get("product_name", "")
        if "IND7705HC" in product_name:
            return "IND7705HC"
        elif "HERMES" in product_name:
            return "HERMES_STYLE"

        return "Unknown"

    def _get_suggested_area(self) -> str:
        """Get suggested area for the device."""
        product_name = self.hass.data[DOMAIN][self._entry.entry_id].get("product_name", "")

        if "IND7705HC" in product_name:
            return "Kitchen"
        elif "HERMES" in product_name:
            return "Kitchen"

        return "Kitchen"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return self._device_info

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    def _get_data_point_value(self, dp: Optional[int] = None) -> Any:
        """Get value for a specific data point."""
        if not self.coordinator.data:
            return None

        data_point = dp if dp is not None else self._dp
        return self.coordinator.data.get(data_point)

    def _get_zone_data_point_value(self, dp: int, zone: Optional[int] = None) -> Any:
        """Get value for a zone-specific data point with bitfield extraction."""
        if not self.coordinator.data:
            return None

        raw_value = self.coordinator.data.get(dp)
        if raw_value is None:
            return None

        zone_number = zone if zone is not None else self._zone
        if zone_number is None:
            return raw_value

        # Extract zone-specific value from bitfield
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

        return False

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
        config: Dict[str, Any],
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
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        return {
            "zone": self._zone,
            "data_point": self._dp,
            "device_id": self._entry.data.get("device_id", "unknown")[:8],
        }