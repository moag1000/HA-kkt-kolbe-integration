"""Number platform for KKT Kolbe devices."""
import logging
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import KKTBaseEntity, KKTZoneBaseEntity
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
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

    entities = []
    number_configs = get_device_entities(product_name, "number")

    for config in number_configs:
        if "zone" in config:
            entities.append(KKTKolbeZoneNumber(coordinator, entry, config))
        else:
            entities.append(KKTKolbeNumber(coordinator, entry, config))

    if entities:
        async_add_entities(entities)


class KKTKolbeNumber(KKTBaseEntity, NumberEntity):
    """Representation of a KKT Kolbe number entity."""

    def __init__(self, coordinator, entry: ConfigEntry, config: dict):
        """Initialize the number entity."""
        super().__init__(coordinator, entry, config, "number")

        # Set number-specific attributes
        self._attr_native_min_value = config.get("min_value", 0)
        self._attr_native_max_value = config.get("max_value", 100)
        self._attr_native_step = config.get("step", 1)
        self._attr_native_unit_of_measurement = config.get("unit_of_measurement")
        self._attr_icon = self._get_icon()

    def _get_icon(self) -> str:
        """Get appropriate icon for the number entity."""
        name_lower = self._name.lower()

        if "timer" in name_lower:
            return "mdi:timer-outline"
        elif "temperature" in name_lower:
            return "mdi:thermometer"
        elif "power" in name_lower:
            return "mdi:lightning-bolt"
        elif "level" in name_lower:
            return "mdi:gauge"

        return "mdi:numeric"

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        value = self._get_data_point_value()
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the number value."""
        int_value = int(value)
        await self._async_set_data_point(self._dp, int_value)
        self._log_entity_state("Set Value", f"DP {self._dp} set to {int_value}")


class KKTKolbeZoneNumber(KKTZoneBaseEntity, NumberEntity):
    """Zone-specific number entity for KKT Kolbe devices."""

    def __init__(self, coordinator, entry: ConfigEntry, config: dict):
        """Initialize the zone number entity."""
        super().__init__(coordinator, entry, config, "number")

        # Set number-specific attributes
        self._attr_native_min_value = config.get("min_value", 0)
        self._attr_native_max_value = config.get("max_value", 25)
        self._attr_native_step = config.get("step", 1)
        self._attr_native_unit_of_measurement = config.get("unit_of_measurement")
        self._attr_icon = self._get_icon()

    def _get_icon(self) -> str:
        """Get appropriate icon for the zone number entity."""
        name_lower = self._name.lower()

        if "timer" in name_lower:
            return "mdi:timer"
        elif "power" in name_lower or "level" in name_lower:
            return "mdi:gauge"
        elif "temperature" in name_lower:
            return "mdi:thermometer"

        return "mdi:numeric"

    @property
    def native_value(self) -> float | None:
        """Return the current zone value."""
        raw_value = self._get_data_point_value()
        if raw_value is None:
            return None

        # For zone-specific values, extract from bitfield if needed
        if isinstance(raw_value, int) and raw_value > 255:
            # Extract zone-specific value from bitfield
            zone_offset = (self._zone - 1) * 8
            zone_mask = 0xFF << zone_offset
            zone_value = (raw_value & zone_mask) >> zone_offset
            return float(zone_value)

        return float(raw_value) if raw_value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the zone number value."""
        int_value = int(value)

        # For zone entities, we need to update the bitfield
        current_data = self._get_data_point_value()
        if current_data is not None and isinstance(current_data, int) and current_data > 255:
            # Update the specific zone in the bitfield
            zone_offset = (self._zone - 1) * 8
            zone_mask = 0xFF << zone_offset
            new_value = (current_data & ~zone_mask) | ((int_value & 0xFF) << zone_offset)
            await self._async_set_data_point(self._dp, new_value)
        else:
            # Simple value
            await self._async_set_data_point(self._dp, int_value)

        self._log_entity_state("Set Zone Value", f"Zone {self._zone}, DP {self._dp} set to {int_value}")