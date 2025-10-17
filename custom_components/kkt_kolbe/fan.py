"""Fan platform for KKT Kolbe Dunstabzugshaube."""
import logging
from datetime import timedelta
from typing import Any
from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FAN_SPEEDS, FAN_SPEED_TO_DP

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe fan entity."""
    device_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = device_data["coordinator"]
    device_info = device_data["device_info"]

    # Only create fan entity for hood devices
    if device_info.get("category") == "hood":
        async_add_entities([KKTKolbeFan(coordinator, entry)])

class KKTKolbeFan(CoordinatorEntity, FanEntity):
    """Representation of KKT Kolbe Dunstabzugshaube fan."""

    def __init__(self, coordinator, entry: ConfigEntry):
        """Initialize the fan."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_fan"
        self._attr_has_entity_name = True
        self._attr_name = "Fan"
        self._attr_supported_features = FanEntityFeature.SET_SPEED
        self._attr_speed_count = 5  # off, low, middle, high, strong

    @property
    def device_info(self):
        """Return device information."""
        return self.coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return if the fan is on."""
        data = self.coordinator.data
        if not data:
            return False
        return data.get(1, False) and data.get(10, "off") != "off"

    @property
    def percentage(self) -> int:
        """Return the current speed percentage."""
        data = self.coordinator.data
        if not data:
            return 0
        speed = data.get(10, "off")
        return FAN_SPEEDS.get(speed, 0)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        # Turn on device first
        await self.coordinator.async_set_data_point(1, True)

        if percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            await self.coordinator.async_set_data_point(10, "low")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        await self.coordinator.async_set_data_point(10, "off")

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

        await self.coordinator.async_set_data_point(10, speed_name)