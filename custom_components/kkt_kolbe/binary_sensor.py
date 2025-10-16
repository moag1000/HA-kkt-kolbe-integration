"""Binary Sensor platform for KKT Kolbe devices."""
import logging
from typing import Any
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
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
    """Set up KKT Kolbe binary sensor entities."""
    device_data = hass.data[DOMAIN][entry.entry_id]
    device = device_data["device"]
    device_info = device_data["device_info"]
    product_name = device_data.get("product_name", "unknown")

    # Get binary sensor configurations for this device
    entity_configs = get_device_entities(product_name, "binary_sensor")

    if entity_configs:
        entities = []
        for config in entity_configs:
            entities.append(
                KKTKolbeBinarySensor(
                    entry=entry,
                    device=device,
                    device_info=device_info,
                    sensor_config=config
                )
            )

        if entities:
            async_add_entities(entities)
            _LOGGER.debug(f"Created {len(entities)} binary sensor entities for {product_name}")

class KKTKolbeBinarySensor(BinarySensorEntity):
    """Representation of a KKT Kolbe binary sensor."""

    def __init__(self, entry: ConfigEntry, device, device_info: dict, sensor_config: dict):
        """Initialize the binary sensor."""
        self._entry = entry
        self._device = device
        self._device_info = device_info
        self._dp = sensor_config["dp"]
        self._sensor_name = sensor_config.get("name", f"Binary Sensor {self._dp}")
        self._device_class = sensor_config.get("device_class")

        # Create unique ID based on device and data point
        self._attr_unique_id = f"{entry.entry_id}_binary_{self._dp}"
        self._attr_name = f"{device_info.get('name', 'KKT Kolbe')} {self._sensor_name}"

        if self._device_class:
            self._attr_device_class = getattr(BinarySensorDeviceClass, self._device_class.upper(), None)

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        try:
            value = self._device.get_dp_value(self._dp)
            # Handle different value types
            if isinstance(value, bool):
                return value
            elif isinstance(value, (int, float)):
                return bool(value)
            elif isinstance(value, str):
                return value.lower() in ['true', 'on', '1']
            else:
                return False
        except Exception as e:
            _LOGGER.error(f"Error getting binary sensor state for DP {self._dp}: {e}")
            return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._device.is_connected

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._device_info.get("name", "KKT Kolbe Device"),
            "manufacturer": "KKT Kolbe",
            "model": self._device_info.get("model_id", "Unknown"),
        }

    async def async_update(self) -> None:
        """Update the entity."""
        await self._device.async_update_status()