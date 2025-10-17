"""Number platform for KKT Kolbe devices."""
import logging
from datetime import timedelta
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
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
    """Set up KKT Kolbe number entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

    entities = []
    number_configs = get_device_entities(product_name, "number")

    for config in number_configs:
        if "zone" in config:
            # Zone-specific entity
            entities.append(KKTKolbeZoneNumber(coordinator, entry, config))
        else:
            # Regular entity
            entities.append(KKTKolbeNumber(coordinator, entry, config))

    if entities:
        async_add_entities(entities)

class KKTKolbeNumber(CoordinatorEntity, NumberEntity):
    """Generic number entity for KKT Kolbe devices."""

    def __init__(self, coordinator, entry: ConfigEntry, config: dict):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._config = config
        self._dp = config["dp"]
        self._name = config["name"]
        self._attr_unique_id = f"{entry.entry_id}_number_{self._name.lower().replace(' ', '_')}"
        self._attr_has_entity_name = True
        self._attr_name = self._name
        self._attr_native_min_value = config.get("min", 0)
        self._attr_native_max_value = config.get("max", 100)
        self._attr_native_unit_of_measurement = config.get("unit")
        self._attr_icon = self._get_icon()

    def _get_icon(self) -> str:
        """Get appropriate icon for the number."""
        name_lower = self._name.lower()
        if "timer" in name_lower or "countdown" in name_lower:
            return "mdi:timer"
        elif "brightness" in name_lower:
            return "mdi:brightness-6"
        elif "power" in name_lower or "level" in name_lower:
            return "mdi:gauge"
        elif "temp" in name_lower:
            return "mdi:thermometer"
        else:
            return "mdi:numeric"

    @property
    def native_value(self) -> float | None:
        """Return the state of the number."""
        data = self.coordinator.data
        if not data:
            return None
        return data.get(self._dp)

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        await self.coordinator.async_set_data_point(self._dp, int(value))

    @property
    def device_info(self):
        """Return device information."""
        return self.coordinator.device_info


class KKTKolbeZoneNumber(CoordinatorEntity, NumberEntity):
    """Zone-specific number entity for KKT Kolbe devices."""

    def __init__(self, coordinator, entry: ConfigEntry, config: dict):
        """Initialize the zone number entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._config = config
        self._dp = config["dp"]
        self._zone = config["zone"]
        self._name = config["name"]
        self._attr_unique_id = f"{entry.entry_id}_number_zone{self._zone}_{self._name.lower().replace(' ', '_')}"
        self._attr_has_entity_name = True
        self._attr_name = self._name
        self._attr_native_min_value = config.get("min", 0)
        self._attr_native_max_value = config.get("max", 100)
        self._attr_native_unit_of_measurement = config.get("unit")
        self._attr_icon = self._get_icon()

    def _get_icon(self) -> str:
        """Get appropriate icon for the number."""
        name_lower = self._name.lower()
        if "timer" in name_lower:
            return "mdi:timer"
        elif "power" in name_lower:
            return "mdi:gauge"
        elif "temp" in name_lower:
            return "mdi:thermometer"
        else:
            return "mdi:numeric"

    @property
    def native_value(self) -> float | None:
        """Return the state of the number."""
        data = self.coordinator.data
        if not data:
            return None

        # Zone numbers often use bitfield data
        raw_value = data.get(self._dp)
        if raw_value is None:
            return None

        # Extract zone-specific data from bitfield
        if isinstance(raw_value, (bytes, bytearray)):
            if self._zone - 1 < len(raw_value):
                return raw_value[self._zone - 1]

        return raw_value

    async def async_set_native_value(self, value: float) -> None:
        """Set new value for zone."""
        data = self.coordinator.data
        if not data:
            return

        # Get current bitfield
        raw_value = data.get(self._dp, bytes(5))  # Default to 5 zones
        if isinstance(raw_value, (bytes, bytearray)):
            data_array = bytearray(raw_value)
        else:
            data_array = bytearray(5)

        # Update zone-specific value
        if self._zone - 1 < len(data_array):
            data_array[self._zone - 1] = int(value)
            await self.coordinator.async_set_data_point(self._dp, bytes(data_array))

    @property
    def device_info(self):
        """Return device information."""
        return self.coordinator.device_info