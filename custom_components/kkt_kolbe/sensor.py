"""Sensor platform for KKT Kolbe devices."""
import logging
from datetime import timedelta
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
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
    """Set up KKT Kolbe sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

    entities = []
    sensor_configs = get_device_entities(product_name, "sensor")

    for config in sensor_configs:
        if "zone" in config:
            # Zone-specific sensor
            entities.append(KKTKolbeZoneSensor(coordinator, entry, config))
        else:
            # Regular sensor
            entities.append(KKTKolbeSensor(coordinator, entry, config))

    if entities:
        async_add_entities(entities)

class KKTKolbeSensor(CoordinatorEntity, SensorEntity):
    """Representation of a KKT Kolbe sensor."""

    def __init__(self, coordinator, entry: ConfigEntry, config: dict):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._config = config
        self._dp = config["dp"]
        self._name = config["name"]
        self._attr_unique_id = f"{entry.entry_id}_sensor_{self._name.lower().replace(' ', '_')}"
        self._attr_has_entity_name = True
        self._attr_name = self._name
        self._attr_device_class = config.get("device_class")
        self._attr_native_unit_of_measurement = config.get("unit")
        self._attr_state_class = self._get_state_class()
        self._attr_entity_category = self._get_entity_category()
        self._attr_icon = self._get_icon()

        # Set options for enum sensors
        if self._attr_device_class == SensorDeviceClass.ENUM and "options" in config:
            self._attr_options = config["options"]

    def _get_icon(self) -> str:
        """Get appropriate icon for the sensor."""
        name_lower = self._name.lower()
        if "error" in name_lower:
            return "mdi:alert-circle"
        elif "temp" in name_lower:
            return "mdi:thermometer"
        elif "timer" in name_lower:
            return "mdi:timer"
        elif "filter" in name_lower:
            return "mdi:air-filter"
        elif "speed" in name_lower:
            return "mdi:fan"
        elif "brightness" in name_lower:
            return "mdi:brightness-6"
        elif "hours" in name_lower:
            return "mdi:clock-time-eight"
        else:
            return "mdi:information"

    def _get_entity_category(self):
        """Get appropriate entity category for the sensor."""
        name_lower = self._name.lower()

        # Diagnostic sensors: errors, filter hours, etc.
        if any(word in name_lower for word in ["error", "problem", "filter", "hours"]):
            return EntityCategory.DIAGNOSTIC

        return None

    def _get_state_class(self):
        """Get appropriate state class for the sensor."""
        name_lower = self._name.lower()

        # Enum sensors have no state class
        if self._attr_device_class == SensorDeviceClass.ENUM:
            return None

        # Timer/countdown sensors have no state class (not measurements)
        if any(word in name_lower for word in ["timer", "countdown"]):
            return None

        # Filter hours are cumulative - use TOTAL_INCREASING
        if "hours" in name_lower and "filter" in name_lower:
            return SensorStateClass.TOTAL_INCREASING

        # Temperature and brightness are measurements
        if self._attr_device_class == SensorDeviceClass.TEMPERATURE:
            return SensorStateClass.MEASUREMENT

        if "brightness" in name_lower:
            return SensorStateClass.MEASUREMENT

        # Default: no state class for unknown sensor types
        return None

    @property
    def native_value(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if not data:
            return None

        value = data.get(self._dp)

        # Handle special conversions
        if self._dp == 10:  # Fan speed enum
            speed_options = self._config.get("options", ["off", "low", "middle", "high", "strong"])
            if isinstance(value, int) and 0 <= value < len(speed_options):
                return speed_options[value]
            return "off"
        elif self._dp in [5, 102]:  # Brightness values
            if value is not None:
                return int((value / 255) * 100)  # Convert to percentage

        return value

    @property
    def device_info(self):
        """Return device information."""
        return self.coordinator.device_info


class KKTKolbeZoneSensor(CoordinatorEntity, SensorEntity):
    """Representation of a KKT Kolbe zone-specific sensor."""

    def __init__(self, coordinator, entry: ConfigEntry, config: dict):
        """Initialize the zone sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._config = config
        self._dp = config["dp"]
        self._zone = config["zone"]
        self._name = config["name"]
        self._attr_unique_id = f"{entry.entry_id}_sensor_zone{self._zone}_{self._name.lower().replace(' ', '_')}"
        self._attr_has_entity_name = True
        self._attr_name = self._name
        self._attr_device_class = config.get("device_class")
        self._attr_native_unit_of_measurement = config.get("unit")
        self._attr_icon = self._get_icon()

    def _get_icon(self) -> str:
        """Get appropriate icon for the sensor."""
        name_lower = self._name.lower()
        if "error" in name_lower:
            return "mdi:alert-circle"
        elif "temp" in name_lower:
            return "mdi:thermometer"
        else:
            return "mdi:information"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        data = self.coordinator.data
        if not data:
            return None

        # Zone sensors often use bitfield data
        raw_value = data.get(self._dp)
        if raw_value is None:
            return None

        # Extract zone-specific data from bitfield
        if isinstance(raw_value, (bytes, bytearray)):
            if self._zone - 1 < len(raw_value):
                return raw_value[self._zone - 1]

        return raw_value

    @property
    def device_info(self):
        """Return device information."""
        return self.coordinator.device_info