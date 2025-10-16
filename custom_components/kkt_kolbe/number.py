"""Number platform for KKT Kolbe Dunstabzugshaube."""
import logging
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe number entity."""
    device = hass.data[DOMAIN][entry.entry_id]["device"]
    async_add_entities([KKTKolbeCountdownTimer(entry, device)])

class KKTKolbeCountdownTimer(NumberEntity):
    """Countdown timer for KKT Kolbe hood."""

    def __init__(self, entry: ConfigEntry, device):
        """Initialize the countdown timer."""
        self._entry = entry
        self._device = device
        self._attr_unique_id = f"{entry.entry_id}_countdown"
        self._attr_name = "KKT Kolbe Timer"
        self._attr_icon = "mdi:timer"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 60
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "min"

    @property
    def native_value(self) -> float:
        """Return the current countdown value."""
        return float(self._device.countdown_minutes)

    async def async_set_native_value(self, value: float) -> None:
        """Set the countdown timer."""
        self._device.set_countdown(int(value))
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the entity."""
        await self._device.async_update_status()