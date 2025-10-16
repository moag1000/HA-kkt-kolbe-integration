"""Number platform for KKT Kolbe devices."""
import logging
from homeassistant.components.number import NumberEntity
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
    """Set up KKT Kolbe number entities."""
    device = hass.data[DOMAIN][entry.entry_id]["device"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

    entities = []
    number_configs = get_device_entities(product_name, "number")

    for config in number_configs:
        if "zone" in config:
            # Zone-specific entity
            entities.append(KKTKolbeZoneNumber(entry, device, device_info, config))
        else:
            # Regular entity
            entities.append(KKTKolbeNumber(entry, device, device_info, config))

    if entities:
        async_add_entities(entities)

class KKTKolbeNumber(NumberEntity):
    """Generic number entity for KKT Kolbe devices."""

    def __init__(self, entry: ConfigEntry, device, device_info, config: dict):
        """Initialize the number entity."""
        self._entry = entry
        self._device = device
        self._device_info = device_info
        self._config = config
        self._dp = config["dp"]
        self._name = config["name"]

        # Set up entity attributes
        self._attr_unique_id = f"{entry.entry_id}_{self._name.lower().replace(' ', '_')}"
        self._attr_name = f"KKT Kolbe {self._name}"
        self._attr_icon = "mdi:timer" if "timer" in self._name.lower() else "mdi:gauge"
        self._attr_native_min_value = config.get("min", 0)
        self._attr_native_max_value = config.get("max", 100)
        self._attr_native_step = config.get("step", 1)
        self._attr_native_unit_of_measurement = config.get("unit")

    @property
    def native_value(self) -> float:
        """Return the current value."""
        if self._dp == 13:  # Hood countdown timer
            return float(self._device.countdown_minutes)
        elif self._dp == 104:  # Cooktop max level
            return float(self._device.cooktop_max_level)
        elif self._dp == 134:  # Cooktop general timer
            return float(self._device.cooktop_timer)
        else:
            return float(self._device.get_dp_value(self._dp, 0))

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        int_value = int(value)

        if self._dp == 13:  # Hood countdown timer
            self._device.set_countdown(int_value)
        elif self._dp == 104:  # Cooktop max level
            self._device.set_cooktop_max_level(int_value)
        elif self._dp == 134:  # Cooktop general timer
            self._device.set_cooktop_timer(int_value)
        else:
            await self._device.async_set_dp(self._dp, int_value)

        self.async_write_ha_state()

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


class KKTKolbeZoneNumber(NumberEntity):
    """Zone-specific number entity for cooktop zones."""

    def __init__(self, entry: ConfigEntry, device, device_info, config: dict):
        """Initialize the zone number entity."""
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
        self._attr_native_min_value = config.get("min", 0)
        self._attr_native_max_value = config.get("max", 100)
        self._attr_native_step = config.get("step", 1)
        self._attr_native_unit_of_measurement = config.get("unit")

    def _get_icon(self) -> str:
        """Get appropriate icon for the entity."""
        if "power" in self._name.lower():
            return "mdi:fire"
        elif "timer" in self._name.lower():
            return "mdi:timer"
        elif "temp" in self._name.lower():
            return "mdi:thermometer"
        else:
            return "mdi:gauge"

    @property
    def native_value(self) -> float:
        """Return the current zone value."""
        if self._dp == 162:  # Zone power levels
            return float(self._device.get_zone_power_level(self._zone))
        elif self._dp == 167:  # Zone timers
            return float(self._device.get_zone_timer(self._zone))
        elif self._dp == 168:  # Zone core temperatures
            return float(self._device.get_zone_core_temp(self._zone))
        else:
            return 0.0

    async def async_set_native_value(self, value: float) -> None:
        """Set the zone value."""
        int_value = int(value)

        if self._dp == 162:  # Zone power levels
            self._device.set_zone_power_level(self._zone, int_value)
        elif self._dp == 167:  # Zone timers
            self._device.set_zone_timer(self._zone, int_value)
        elif self._dp == 168:  # Zone core temperatures
            self._device.set_zone_core_temp(self._zone, int_value)

        self.async_write_ha_state()

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