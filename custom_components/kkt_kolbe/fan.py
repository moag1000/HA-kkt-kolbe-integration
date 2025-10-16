"""Fan platform for KKT Kolbe Dunstabzugshaube."""
import logging
from typing import Any
from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, FAN_SPEEDS, FAN_SPEED_TO_DP

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe fan entity."""
    device = hass.data[DOMAIN][entry.entry_id]["device"]
    async_add_entities([KKTKolbeFan(entry, device)])

class KKTKolbeFan(FanEntity):
    """Representation of KKT Kolbe Dunstabzugshaube fan."""

    def __init__(self, entry: ConfigEntry, device):
        """Initialize the fan."""
        self._entry = entry
        self._device = device
        self._attr_unique_id = f"{entry.entry_id}_fan"
        self._attr_name = "KKT Kolbe Dunstabzugshaube"
        self._attr_supported_features = FanEntityFeature.SET_SPEED
        self._attr_speed_count = 4

    @property
    def is_on(self) -> bool:
        """Return if the fan is on."""
        return self._device.is_on and self._device.fan_speed != "off"

    @property
    def percentage(self) -> int:
        """Return the current speed percentage."""
        speed = self._device.fan_speed
        return FAN_SPEEDS.get(speed, 0)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if not self._device.is_on:
            self._device.turn_on()

        if percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            self._device.set_fan_speed("low")

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        self._device.set_fan_speed("off")
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        # Find closest speed setting
        if percentage == 0:
            speed_name = "off"
        elif percentage <= 25:
            speed_name = "low"
        elif percentage <= 50:
            speed_name = "middle"
        elif percentage <= 75:
            speed_name = "high"
        else:
            speed_name = "strong"

        self._device.set_fan_speed(speed_name)
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the entity."""
        await self._device.async_update_status()