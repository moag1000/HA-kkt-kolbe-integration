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
    device_data = hass.data[DOMAIN][entry.entry_id]
    device = device_data["device"]
    device_info = device_data["device_info"]

    # Only create light entity for hood devices
    if device_info.get("category") == "hood":
        async_add_entities([KKTKolbeLight(entry, device, device_info)])

class KKTKolbeLight(LightEntity):
    """Representation of KKT Kolbe Dunstabzugshaube light."""

    def __init__(self, entry: ConfigEntry, device, device_info: dict):
        """Initialize the light."""
        self._entry = entry
        self._device = device
        self._device_info = device_info
        self._attr_unique_id = f"{entry.entry_id}_light"
        self._attr_name = f"{device_info.get('name', 'KKT Kolbe')} Light"
        self._attr_color_mode = ColorMode.BRIGHTNESS
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def is_on(self) -> bool:
        """Return if the light is on."""
        return self._device.light_on

    @property
    def brightness(self) -> int:
        """Return the brightness of the light (RGB mode as brightness)."""
        # Use RGB mode as brightness level (0-9 mapped to 0-255)
        rgb_mode = self._device.rgb_mode
        return int((rgb_mode / 9) * 255) if rgb_mode > 0 else 255

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        if ATTR_BRIGHTNESS in kwargs:
            # Map brightness (0-255) to RGB mode (0-9)
            brightness = kwargs[ATTR_BRIGHTNESS]
            rgb_mode = max(1, int((brightness / 255) * 9))
            self._device.set_rgb_mode(rgb_mode)

        self._device.set_light(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        self._device.set_light(False)
        self.async_write_ha_state()

    @property
    def device_info(self):
        """Return device info for device registry."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._device_info.get("name", "KKT Kolbe Device"),
            "manufacturer": "KKT Kolbe",
            "model": self._device_info.get("model_id", "Unknown"),
            "sw_version": "1.3.0",
        }

    async def async_update(self) -> None:
        """Update the entity."""
        await self._device.async_update_status()