"""Light platform for KKT Kolbe Dunstabzugshaube."""
import logging
from datetime import timedelta
from typing import Any
from homeassistant.components.light import (
    LightEntity,
    ColorMode,
    ATTR_BRIGHTNESS,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe light entity."""
    device_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = device_data["coordinator"]
    device_info = device_data["device_info"]

    # Only create light entity for hood devices
    if device_info.get("category") == "hood":
        async_add_entities([KKTKolbeLight(coordinator, entry)])

class KKTKolbeLight(CoordinatorEntity, LightEntity):
    """Representation of KKT Kolbe Dunstabzugshaube light."""

    def __init__(self, coordinator, entry: ConfigEntry):
        """Initialize the light."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_light"
        self._attr_has_entity_name = True
        self._attr_name = "Light"
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def is_on(self) -> bool:
        """Return if the light is on."""
        data = self.coordinator.data
        if not data:
            return False
        return data.get(4, False)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        data = self.coordinator.data
        if not data:
            return None
        return data.get(5, 255)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            await self.coordinator.async_set_data_point(5, brightness)

        await self.coordinator.async_set_data_point(4, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self.coordinator.async_set_data_point(4, False)

    @property
    def device_info(self):
        """Return device information."""
        return self.coordinator.device_info