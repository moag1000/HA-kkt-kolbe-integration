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

from .const import DOMAIN
from .device_types import get_device_entities

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe sensor entities."""
    device = hass.data[DOMAIN][entry.entry_id]["device"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

    entities = []
    sensor_configs = get_device_entities(product_name, "sensor")

    for config in sensor_configs:
        if "zone" in config:
            # Zone-specific sensor
            entities.append(KKTKolbeZoneSensor(entry, device, device_info, config))
        else:
            # Regular sensor
            entities.append(KKTKolbeSensor(entry, device, device_info, config))

    if entities:
        async_add_entities(entities)

class KKTKolbeSensor(SensorEntity):
    """Representation of a KKT Kolbe sensor."""

    def __init__(self, entry: ConfigEntry, device, device_info, config: dict):
        """Initialize the sensor."""
        self._entry = entry
        self._device = device
        self._device_info = device_info
        self._config = config
        self._dp = config["dp"]
        self._name = config["name"]

        # Set up entity attributes
        self._attr_unique_id = f"{entry.entry_id}_{self._name.lower().replace(' ', '_')}"
        self._attr_name = f"KKT Kolbe {self._name}"
        self._attr_icon = self._get_icon()
        self._attr_device_class = self._get_device_class()

        # Only set state class for measurement sensors, not for enum sensors
        if self._attr_device_class != SensorDeviceClass.ENUM:
            self._attr_state_class = SensorStateClass.MEASUREMENT

        self._attr_native_unit_of_measurement = config.get("unit")

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
        else:
            return "mdi:information"

    def _get_device_class(self):
        """Get appropriate device class for the sensor."""
        name_lower = self._name.lower()
        unit = self._config.get("unit", "").lower()

        if "temp" in name_lower or "°c" in unit:
            return SensorDeviceClass.TEMPERATURE
        elif "error" in name_lower or "problem" in self._config.get("device_class", ""):
            return SensorDeviceClass.ENUM
        elif "timer" in name_lower or "min" in unit:
            return SensorDeviceClass.DURATION
        else:
            return None

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # Basic sensor reading from DP
        return self._device.get_dp_value(self._dp, 0)

    @property
    def device_info(self):
        """Return device info for device registry."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._device_info.get("name", "KKT Kolbe Device"),
            "manufacturer": "KKT Kolbe",
            "model": self._device_info.get("model_id", "Unknown"),
        }

    async def async_update(self) -> None:
        """Update the entity."""
        await self._device.async_update_status()


class KKTKolbeZoneSensor(SensorEntity):
    """Zone-specific sensor for cooktop zones."""

    def __init__(self, entry: ConfigEntry, device, device_info, config: dict):
        """Initialize the zone sensor."""
        self._entry = entry
        self._device = device
        self._device_info = device_info
        self._config = config
        self._dp = config["dp"]
        self._zone = config["zone"]
        self._name = config["name"]

        # Set up entity attributes
        self._attr_unique_id = f"{entry.entry_id}_zone_{self._zone}_{self._name.lower().replace(' ', '_')}"
        self._attr_name = f"KKT Kolbe {self._name}"
        self._attr_icon = self._get_icon()
        self._attr_device_class = self._get_device_class()

        # Only set state class for measurement sensors, not for enum sensors
        if self._attr_device_class != SensorDeviceClass.ENUM:
            self._attr_state_class = SensorStateClass.MEASUREMENT

        self._attr_native_unit_of_measurement = config.get("unit")

    def _get_icon(self) -> str:
        """Get appropriate icon for the zone sensor."""
        name_lower = self._name.lower()
        if "error" in name_lower:
            return "mdi:alert-circle"
        elif "temp" in name_lower:
            return "mdi:thermometer"
        elif "core" in name_lower:
            return "mdi:thermometer-probe"
        else:
            return "mdi:information"

    def _get_device_class(self):
        """Get appropriate device class for the zone sensor."""
        name_lower = self._name.lower()
        unit = self._config.get("unit", "").lower()

        if "temp" in name_lower or "°c" in unit:
            return SensorDeviceClass.TEMPERATURE
        elif "error" in name_lower:
            return SensorDeviceClass.ENUM
        else:
            return None

    @property
    def native_value(self):
        """Return the zone sensor value."""
        if self._dp == 105:  # Zone error codes
            return self._device.get_zone_error(self._zone)
        elif self._dp == 169:  # Zone core temperature display
            return self._device.get_zone_core_temp_display(self._zone)
        else:
            return 0

    @property
    def device_info(self):
        """Return device info for device registry."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._device_info.get("name", "KKT Kolbe Device"),
            "manufacturer": "KKT Kolbe",
            "model": self._device_info.get("model_id", "Unknown"),
        }

    async def async_update(self) -> None:
        """Update the entity."""
        await self._device.async_update_status()