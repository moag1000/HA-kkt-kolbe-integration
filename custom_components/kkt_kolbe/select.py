"""Select platform for KKT Kolbe devices."""
import logging
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .device_types import get_device_entities

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe select entities."""
    device = hass.data[DOMAIN][entry.entry_id]["device"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

    entities = []
    select_configs = get_device_entities(product_name, "select")

    for config in select_configs:
        entities.append(KKTKolbeSelect(entry, device, device_info, config))

    if entities:
        async_add_entities(entities)

class KKTKolbeSelect(SelectEntity):
    """Generic select entity for KKT Kolbe devices."""

    def __init__(self, entry: ConfigEntry, device, device_info, config: dict):
        """Initialize the select entity."""
        self._entry = entry
        self._device = device
        self._device_info = device_info
        self._config = config
        self._dp = config["dp"]
        self._name = config["name"]
        self._options = config["options"]

        # Set up entity attributes
        self._attr_unique_id = f"{entry.entry_id}_{self._name.lower().replace(' ', '_')}"
        self._attr_name = f"KKT Kolbe {self._name}"
        self._attr_icon = self._get_icon()

        # Convert options to strings for Home Assistant
        if isinstance(self._options[0], int):
            # RGB mode numbers (0-9) -> convert to string
            self._attr_options = [f"Mode {i}" for i in self._options]
        else:
            # Already strings (quick levels, etc.)
            self._attr_options = list(self._options)

    def _get_icon(self) -> str:
        """Get appropriate icon for the select entity."""
        name_lower = self._name.lower()
        if "rgb" in name_lower or "mode" in name_lower:
            return "mdi:palette"
        elif "quick" in name_lower or "level" in name_lower:
            return "mdi:speedometer"
        elif "power" in name_lower:
            return "mdi:flash"
        elif "zone" in name_lower:
            return "mdi:stove"
        else:
            return "mdi:format-list-bulleted"

    @property
    def current_option(self) -> str:
        """Return the current option."""
        if self._dp == 101:  # Hood RGB mode
            mode_num = self._device.rgb_mode
            if isinstance(self._options[0], int):
                return f"Mode {mode_num}" if mode_num < len(self._attr_options) else "Mode 0"
            else:
                return self._options[mode_num] if mode_num < len(self._options) else self._options[0]

        elif self._dp in [148, 149, 150, 151, 152]:  # Cooktop quick levels
            current_value = self._device.get_dp_value(self._dp, self._options[0])
            return current_value if current_value in self._options else self._options[0]

        elif self._dp in [153, 154, 155]:  # Cooktop save/set/power limit
            current_value = self._device.get_dp_value(self._dp, self._options[0])
            return current_value if current_value in self._options else self._options[0]

        elif self._dp == 11:  # Hood fan speed setting
            return self._device.fan_speed_setting

        else:
            current_value = self._device.get_dp_value(self._dp, self._options[0])
            return str(current_value) if current_value in self._options else str(self._options[0])

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if self._dp == 101:  # Hood RGB mode
            if isinstance(self._options[0], int):
                # Extract mode number from "Mode X" format
                try:
                    mode_num = int(option.split()[-1])
                    self._device.set_rgb_mode(mode_num)
                except (ValueError, IndexError):
                    self._device.set_rgb_mode(0)
            else:
                # Direct mapping
                if option in self._options:
                    mode_num = self._options.index(option)
                    self._device.set_rgb_mode(mode_num)

        elif self._dp in [148, 149, 150, 151, 152]:  # Cooktop quick levels
            if option in self._options:
                await self._device.async_set_dp(self._dp, option)

        elif self._dp in [153, 154, 155]:  # Cooktop save/set/power limit
            if option in self._options:
                await self._device.async_set_dp(self._dp, option)

        elif self._dp == 11:  # Hood fan speed setting
            if option in self._options:
                self._device.set_fan_speed_direct(option)

        else:
            # Generic handling
            if option in [str(opt) for opt in self._options]:
                # Try to convert back to original type
                if isinstance(self._options[0], int):
                    await self._device.async_set_dp(self._dp, int(option))
                else:
                    await self._device.async_set_dp(self._dp, option)

        self.async_write_ha_state()

    @property
    def device_info(self):
        """Return device info for device registry."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._device_info.get("name", "KKT Kolbe Device"),
            "manufacturer": "KKT Kolbe",
            "model": self._device_info.get("model_id", "Unknown"),
        }

    async def async_update(self) -> None:
        """Update the entity."""
        await self._device.async_update_status()