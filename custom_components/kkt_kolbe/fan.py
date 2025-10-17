"""Fan platform for KKT Kolbe devices."""
import logging
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .base_entity import KKTBaseEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

# Fan speed mapping for KKT Kolbe HERMES & STYLE
SPEED_LIST = ["off", "low", "middle", "high", "strong"]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe fan entity."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

    # Only add fan entity for HERMES & STYLE (range hood)
    if "HERMES" in product_name and "STYLE" in product_name:
        async_add_entities([KKTKolbeFan(coordinator, entry)])


class KKTKolbeFan(KKTBaseEntity, FanEntity):
    """Representation of a KKT Kolbe fan."""

    def __init__(self, coordinator, entry: ConfigEntry):
        """Initialize the fan."""
        config = {
            "dp": 2,
            "name": "Fan",
        }
        super().__init__(coordinator, entry, config, "fan")

        self._attr_supported_features = FanEntityFeature.SET_SPEED
        self._attr_speed_count = len(SPEED_LIST) - 1  # Exclude 'off'
        self._attr_icon = "mdi:fan"

    @property
    def is_on(self) -> bool | None:
        """Return true if the fan is on."""
        speed_level = self._get_data_point_value()
        return speed_level is not None and speed_level > 0

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        speed_level = self._get_data_point_value()
        if speed_level is None or speed_level == 0:
            return 0

        # Convert Tuya speed (1-4) to percentage
        return ordered_list_item_to_percentage(SPEED_LIST, SPEED_LIST[speed_level])

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self.async_turn_off()
            return

        # Convert percentage to Tuya speed level
        speed_name = percentage_to_ordered_list_item(SPEED_LIST, percentage)
        speed_level = SPEED_LIST.index(speed_name)

        await self._async_set_data_point(2, speed_level)
        self._log_entity_state("Set Speed", f"Speed level: {speed_level} ({speed_name})")

    async def async_turn_on(
        self, percentage: int | None = None, preset_mode: str | None = None, **kwargs
    ) -> None:
        """Turn on the fan."""
        if percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            # Default to "low" speed
            await self._async_set_data_point(2, 1)
            self._log_entity_state("Turn On", "Default speed: low")

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the fan."""
        await self._async_set_data_point(2, 0)
        self._log_entity_state("Turn Off", "Speed level: 0")