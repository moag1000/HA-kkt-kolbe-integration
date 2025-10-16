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
        self._zone = sensor_config.get("zone")  # Zone number for cooktop zones

        # Create unique ID based on device and data point
        if self._zone:
            if self._dp in [165, 166]:  # Flex/BBQ have left/right, not zones
                side = "left" if "left" in self._sensor_name.lower() else "right"
                self._attr_unique_id = f"{entry.entry_id}_binary_{self._dp}_{side}"
            else:
                self._attr_unique_id = f"{entry.entry_id}_binary_{self._dp}_zone_{self._zone}"
        else:
            self._attr_unique_id = f"{entry.entry_id}_binary_{self._dp}"

        self._attr_name = f"{device_info.get('name', 'KKT Kolbe')} {self._sensor_name}"
        self._attr_icon = self._get_icon()

        if self._device_class:
            self._attr_device_class = getattr(BinarySensorDeviceClass, self._device_class.upper(), None)

    def _get_icon(self) -> str:
        """Get appropriate icon for the binary sensor."""
        name_lower = self._sensor_name.lower()
        if "selected" in name_lower:
            return "mdi:target"
        elif "boost" in name_lower:
            return "mdi:rocket"
        elif "warm" in name_lower:
            return "mdi:heat-wave"
        elif "flex" in name_lower:
            return "mdi:view-grid-plus"
        elif "bbq" in name_lower:
            return "mdi:grill"
        elif "zone" in name_lower:
            return "mdi:stove"
        else:
            return "mdi:information"

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        try:
            # Zone-specific binary sensors with bitfield logic
            if self._zone:
                if self._dp == 161:  # Zone selection
                    return self._device.is_zone_selected(self._zone)
                elif self._dp == 163:  # Zone boost
                    return self._device.is_zone_boost(self._zone)
                elif self._dp == 164:  # Zone keep warm
                    return self._device.is_zone_keep_warm(self._zone)
                elif self._dp == 165:  # Flex zone
                    side = "left" if self._zone == 1 else "right"
                    return self._device.is_flex_zone_active(side)
                elif self._dp == 166:  # BBQ mode
                    side = "left" if self._zone == 1 else "right"
                    return self._device.is_bbq_mode_active(side)

            # Regular boolean data points
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