"""Select platform for KKT Kolbe Dunstabzugshaube."""
import logging
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, RGB_MODES

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe select entity."""
    device = hass.data[DOMAIN][entry.entry_id]["device"]
    async_add_entities([KKTKolbeRGBModeSelect(entry, device)])

class KKTKolbeRGBModeSelect(SelectEntity):
    """RGB mode selector for KKT Kolbe hood."""

    def __init__(self, entry: ConfigEntry, device):
        """Initialize the RGB mode selector."""
        self._entry = entry
        self._device = device
        self._attr_unique_id = f"{entry.entry_id}_rgb_mode"
        self._attr_name = "KKT Kolbe RGB Light Mode"
        self._attr_icon = "mdi:palette"
        self._attr_options = list(RGB_MODES.values())

    @property
    def current_option(self) -> str:
        """Return the current RGB mode."""
        mode_num = self._device.rgb_mode
        return RGB_MODES.get(mode_num, "Off")

    async def async_select_option(self, option: str) -> None:
        """Change the selected RGB mode."""
        # Find the mode number for the selected option
        for mode_num, mode_name in RGB_MODES.items():
            if mode_name == option:
                self._device.set_rgb_mode(mode_num)
                break
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Update the entity."""
        await self._device.async_update_status()