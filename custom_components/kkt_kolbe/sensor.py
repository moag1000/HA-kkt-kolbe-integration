"""Sensor platform for KKT Kolbe Dunstabzugshaube."""
import logging
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfTime,
    PERCENTAGE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = [
    SensorEntityDescription(
        key="filter_hours",
        name="Filter Betriebsstunden",
        icon="mdi:air-filter",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
    ),
    SensorEntityDescription(
        key="filter_saturation",
        name="Filter Sättigung",
        icon="mdi:filter-variant",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    SensorEntityDescription(
        key="air_quality",
        name="Luftqualität",
        icon="mdi:air-purifier",
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="temperature",
        name="Temperatur",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe sensor entities."""
    entities = []

    for description in SENSOR_TYPES:
        entities.append(KKTKolbeSensor(entry, description))

    async_add_entities(entities)

class KKTKolbeSensor(SensorEntity):
    """Representation of a KKT Kolbe sensor."""

    def __init__(self, entry: ConfigEntry, description: SensorEntityDescription):
        """Initialize the sensor."""
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_name = f"KKT Kolbe {description.name}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # TODO: Implement actual device communication
        return None