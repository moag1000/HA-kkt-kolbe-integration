"""Switch platform for KKT Kolbe Dunstabzugshaube."""
import logging
from typing import Any
from homeassistant.components.switch import SwitchEntity
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
    """Set up KKT Kolbe switch entities."""
    entities = [
        KKTKolbeSwitch(entry, "power", "Power", "mdi:power"),
        KKTKolbeSwitch(entry, "auto_mode", "Auto Mode", "mdi:fan-auto"),
        KKTKolbeSwitch(entry, "timer", "Timer", "mdi:timer"),
    ]
    async_add_entities(entities)

class KKTKolbeSwitch(SwitchEntity):
    """Representation of a KKT Kolbe switch."""

    def __init__(self, entry: ConfigEntry, key: str, name: str, icon: str):
        """Initialize the switch."""
        self._entry = entry
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_switch_{key}"
        self._attr_name = f"KKT Kolbe {name}"
        self._attr_icon = icon
        self._is_on = False

    @property
    def is_on(self) -> bool:
        """Return if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        self._is_on = True
        # TODO: Implement device communication
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        self._is_on = False
        # TODO: Implement device communication
        self.async_write_ha_state()