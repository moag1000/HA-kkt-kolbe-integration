"""Light platform for KKT Kolbe Dunstabzugshaube."""
import logging
from typing import Any
from homeassistant.components.light import (
    LightEntity,
    ColorMode,
    ATTR_BRIGHTNESS,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe light entity."""
    async_add_entities([KKTKolbeLight(entry)])

class KKTKolbeLight(LightEntity):
    """Representation of KKT Kolbe Dunstabzugshaube light."""

    def __init__(self, entry: ConfigEntry):
        """Initialize the light."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_light"
        self._attr_name = "KKT Kolbe Beleuchtung"
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._is_on = False
        self._brightness = 255

    @property
    def is_on(self) -> bool:
        """Return if the light is on."""
        return self._is_on

    @property
    def brightness(self) -> int:
        """Return the brightness of the light."""
        return self._brightness

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        self._is_on = True
        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
        # TODO: Implement device communication
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        self._is_on = False
        # TODO: Implement device communication
        self.async_write_ha_state()