"""Binary Sensor platform for KKT Kolbe devices."""
import logging
from datetime import timedelta
from typing import Any
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .device_types import get_device_entities

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe binary sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

    # Get binary sensor configurations for this device
    entity_configs = get_device_entities(product_name, "binary_sensor")

    if entity_configs:
        entities = []
        for config in entity_configs:
            if "zone" in config:
                entities.append(KKTKolbeZoneBinarySensor(coordinator, entry, config))
            else:
                entities.append(KKTKolbeBinarySensor(coordinator, entry, config))

        if entities:
            async_add_entities(entities)

class KKTKolbeBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for KKT Kolbe devices."""

    def __init__(self, coordinator, entry: ConfigEntry, config: dict):
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._config = config
        self._dp = config["dp"]
        self._name = config["name"]
        self._attr_unique_id = f"{entry.entry_id}_binary_sensor_{self._name.lower().replace(' ', '_')}"
        self._attr_has_entity_name = True
        self._attr_name = self._name
        self._attr_device_class = config.get("device_class")
        self._attr_entity_category = self._get_entity_category()
        self._attr_icon = self._get_icon()

    def _get_entity_category(self):
        """Get appropriate entity category for the binary sensor."""
        name_lower = self._name.lower()

        # Diagnostic sensors
        if any(word in name_lower for word in ["selected", "boost", "warm", "flex", "bbq"]):
            return EntityCategory.DIAGNOSTIC

        return None

    def _get_icon(self) -> str:
        """Get appropriate icon for the binary sensor."""
        name_lower = self._name.lower()
        device_class = self._attr_device_class

        if device_class == BinarySensorDeviceClass.RUNNING:
            if "boost" in name_lower:
                return "mdi:rocket-launch"
            elif "warm" in name_lower:
                return "mdi:heat-wave"
            elif "flex" in name_lower:
                return "mdi:resize"
            elif "bbq" in name_lower:
                return "mdi:grill"
            elif "selected" in name_lower:
                return "mdi:circle-slice-8"
            return "mdi:play-circle"

        return "mdi:circle"

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        data = self.coordinator.data
        if not data:
            return None

        value = data.get(self._dp)
        if value is None:
            return None

        # For simple boolean DPs
        if isinstance(value, bool):
            return value

        # For bitfield DPs (like zone selections)
        if isinstance(value, int):
            return bool(value)

        return False

    @property
    def device_info(self):
        """Return device information."""
        return self.coordinator.device_info


class KKTKolbeZoneBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Zone-specific binary sensor for KKT Kolbe devices."""

    def __init__(self, coordinator, entry: ConfigEntry, config: dict):
        """Initialize the zone binary sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._config = config
        self._dp = config["dp"]
        self._zone = config["zone"]
        self._name = config["name"]
        self._attr_unique_id = f"{entry.entry_id}_binary_sensor_zone{self._zone}_{self._name.lower().replace(' ', '_')}"
        self._attr_has_entity_name = True
        self._attr_name = self._name
        self._attr_device_class = config.get("device_class", BinarySensorDeviceClass.RUNNING)
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = self._get_icon()

    def _get_icon(self) -> str:
        """Get appropriate icon for the zone binary sensor."""
        name_lower = self._name.lower()

        if "boost" in name_lower:
            return "mdi:rocket-launch"
        elif "warm" in name_lower:
            return "mdi:heat-wave"
        elif "flex" in name_lower:
            return "mdi:resize"
        elif "bbq" in name_lower:
            return "mdi:grill"
        elif "selected" in name_lower:
            return "mdi:circle-slice-8"

        return "mdi:play-circle"

    @property
    def is_on(self) -> bool | None:
        """Return true if the zone binary sensor is on."""
        data = self.coordinator.data
        if not data:
            return None

        # Zone binary sensors use bitfield data
        raw_value = data.get(self._dp)
        if raw_value is None:
            return None

        # Extract zone-specific bit from bitfield
        if isinstance(raw_value, int):
            # Zone is 1-indexed, but bits are 0-indexed
            zone_bit = 1 << (self._zone - 1)
            return bool(raw_value & zone_bit)
        elif isinstance(raw_value, (bytes, bytearray)):
            # For byte arrays, check individual bytes
            byte_index = (self._zone - 1) // 8
            bit_index = (self._zone - 1) % 8
            if byte_index < len(raw_value):
                return bool(raw_value[byte_index] & (1 << bit_index))

        return False

    @property
    def device_info(self):
        """Return device information."""
        return self.coordinator.device_info