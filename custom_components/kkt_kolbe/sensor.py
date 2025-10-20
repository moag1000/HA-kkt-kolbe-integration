"""Sensor platform for KKT Kolbe devices."""
import logging
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import KKTBaseEntity, KKTZoneBaseEntity
from .const import DOMAIN
from .device_types import get_device_entities
from .bitfield_utils import get_zone_value_from_coordinator, BITFIELD_CONFIG

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
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

class KKTKolbeSensor(KKTBaseEntity, SensorEntity):
    """Representation of a KKT Kolbe sensor."""

    def __init__(self, coordinator, entry: ConfigEntry, config: dict):
        """Initialize the sensor."""
        super().__init__(coordinator, entry, config, "sensor")
        self._cached_value = None

        # Initialize state from coordinator data
        self._update_cached_state()

        # Set sensor-specific attributes
        self._attr_state_class = config.get("state_class")
        self._attr_native_unit_of_measurement = config.get("unit_of_measurement")
        self._attr_icon = self._get_icon()

    def _get_icon(self) -> str:
        """Get appropriate icon for the sensor."""
        name_lower = self._name.lower()
        device_class = self._attr_device_class

        if device_class == SensorDeviceClass.TEMPERATURE:
            return "mdi:thermometer"
        elif "timer" in name_lower:
            return "mdi:timer-outline"
        elif "filter" in name_lower:
            return "mdi:air-filter"
        elif "status" in name_lower:
            return "mdi:information-outline"
        elif "error" in name_lower:
            return "mdi:alert-circle-outline"

        return "mdi:gauge"

    def _update_cached_state(self) -> None:
        """Update the cached state from coordinator data."""
        value = self._get_data_point_value()
        if value is None:
            self._cached_value = None
            return

        # Convert temperature values if needed
        if self._attr_device_class == SensorDeviceClass.TEMPERATURE:
            if isinstance(value, (int, float)):
                # Assuming device reports in Celsius
                self._cached_value = value
            else:
                self._cached_value = None
        else:
            self._cached_value = value

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._cached_value


class KKTKolbeZoneSensor(KKTZoneBaseEntity, SensorEntity):
    """Zone-specific sensor for KKT Kolbe devices."""

    def __init__(self, coordinator, entry: ConfigEntry, config: dict):
        """Initialize the zone sensor."""
        super().__init__(coordinator, entry, config, "sensor")

        # Set sensor-specific attributes
        self._attr_state_class = config.get("state_class")
        self._attr_native_unit_of_measurement = config.get("unit_of_measurement")
        self._attr_icon = self._get_icon()
        self._cached_value = None

        # Initialize state from coordinator data
        self._update_cached_state()

    def _get_icon(self) -> str:
        """Get appropriate icon for the zone sensor."""
        name_lower = self._name.lower()

        if "temperature" in name_lower:
            return "mdi:thermometer"
        elif "timer" in name_lower:
            return "mdi:timer"
        elif "power" in name_lower:
            return "mdi:lightning-bolt"
        elif "level" in name_lower:
            return "mdi:gauge"

        return "mdi:circle-slice-8"

    def _update_cached_state(self) -> None:
        """Update the cached state from coordinator data."""
        # Check if this DP uses bitfield encoding
        if self._dp in BITFIELD_CONFIG and BITFIELD_CONFIG[self._dp]["type"] == "value":
            # Use bitfield utilities for Base64-encoded RAW data
            value = get_zone_value_from_coordinator(self.coordinator, self._dp, self._zone)
            self._cached_value = value
            return

        # Fallback to legacy integer bitfield handling
        raw_value = self._get_data_point_value()
        if raw_value is None:
            self._cached_value = None
            return

        # For zone-specific values, extract from bitfield if needed
        if isinstance(raw_value, int) and raw_value > 255:
            # Likely a bitfield, extract zone-specific value
            # This depends on the specific data point structure
            zone_offset = (self._zone - 1) * 8  # Assuming 8 bits per zone
            zone_mask = 0xFF << zone_offset
            zone_value = (raw_value & zone_mask) >> zone_offset
            self._cached_value = zone_value
        else:
            self._cached_value = raw_value

    @property
    def native_value(self):
        """Return the state of the zone sensor."""
        return self._cached_value