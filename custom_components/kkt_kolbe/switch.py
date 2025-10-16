"""Switch platform for KKT Kolbe devices."""
import logging
from typing import Any
from homeassistant.components.switch import SwitchEntity
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
    """Set up KKT Kolbe switch entities."""
    device = hass.data[DOMAIN][entry.entry_id]["device"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

    entities = []
    switch_configs = get_device_entities(product_name, "switch")

    for config in switch_configs:
        entities.append(KKTKolbeSwitch(entry, device, device_info, config))

    if entities:
        async_add_entities(entities)

class KKTKolbeSwitch(SwitchEntity):
    """Representation of a KKT Kolbe switch."""

    def __init__(self, entry: ConfigEntry, device, device_info, config: dict):
        """Initialize the switch."""
        self._entry = entry
        self._device = device
        self._device_info = device_info
        self._config = config
        self._dp = config["dp"]
        self._name = config["name"]

        # Set up entity attributes
        self._attr_unique_id = f"{entry.entry_id}_{self._name.lower().replace(' ', '_')}"
        self._attr_name = f"{self._device_info.get('name', 'KKT Kolbe')} {self._name}"
        self._attr_icon = self._get_icon()
        self._attr_device_class = config.get("device_class")

    def _get_icon(self) -> str:
        """Get appropriate icon for the switch."""
        name_lower = self._name.lower()
        if "power" in name_lower:
            return "mdi:power"
        elif "pause" in name_lower:
            return "mdi:pause"
        elif "lock" in name_lower:
            return "mdi:lock"
        elif "senior" in name_lower:
            return "mdi:account-supervisor"
        elif "confirm" in name_lower:
            return "mdi:check"
        elif "filter" in name_lower:
            return "mdi:air-filter"
        else:
            return "mdi:toggle-switch"

    @property
    def is_on(self) -> bool:
        """Return if the switch is on."""
        if self._dp == 1:  # Hood main power
            return self._device.is_on
        elif self._dp == 6:  # Hood filter reminder
            return self._device.get_dp_value(6, False)
        elif self._dp == 101:  # Cooktop main power
            return self._device.cooktop_power_on
        elif self._dp == 102:  # Cooktop pause
            return self._device.cooktop_paused
        elif self._dp == 103:  # Cooktop child lock
            return self._device.cooktop_child_lock
        elif self._dp == 145:  # Cooktop senior mode
            return self._device.cooktop_senior_mode
        elif self._dp == 108:  # Cooktop confirm action
            return self._device.get_dp_value(108, False)
        elif self._dp == 15:  # Hood filter reset
            return self._device.get_dp_value(15, False)
        else:
            return self._device.get_dp_value(self._dp, False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        if self._dp == 1:  # Hood main power
            self._device.turn_on()
        elif self._dp == 6:  # Hood filter reminder
            await self._device.async_set_dp(6, True)
        elif self._dp == 101:  # Cooktop main power
            self._device.set_cooktop_power(True)
        elif self._dp == 102:  # Cooktop pause
            self._device.set_cooktop_pause(True)
        elif self._dp == 103:  # Cooktop child lock
            self._device.set_cooktop_child_lock(True)
        elif self._dp == 145:  # Cooktop senior mode
            self._device.set_cooktop_senior_mode(True)
        elif self._dp == 108:  # Cooktop confirm action
            self._device.set_cooktop_confirm(True)
        elif self._dp == 15:  # Hood filter reset
            self._device.reset_filter()
        else:
            await self._device.async_set_dp(self._dp, True)

        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        if self._dp == 1:  # Hood main power
            self._device.turn_off()
        elif self._dp == 6:  # Hood filter reminder
            await self._device.async_set_dp(6, False)
        elif self._dp == 101:  # Cooktop main power
            self._device.set_cooktop_power(False)
        elif self._dp == 102:  # Cooktop pause
            self._device.set_cooktop_pause(False)
        elif self._dp == 103:  # Cooktop child lock
            self._device.set_cooktop_child_lock(False)
        elif self._dp == 145:  # Cooktop senior mode
            self._device.set_cooktop_senior_mode(False)
        elif self._dp == 108:  # Cooktop confirm action
            self._device.set_cooktop_confirm(False)
        elif self._dp == 15:  # Hood filter reset
            # Filter reset is a toggle action, do nothing on off
            pass
        else:
            await self._device.async_set_dp(self._dp, False)

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