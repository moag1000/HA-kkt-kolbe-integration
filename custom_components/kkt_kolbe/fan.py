"""Fan platform for KKT Kolbe devices."""
import logging
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .base_entity import KKTBaseEntity
from .const import DOMAIN
from .device_types import get_device_entities, get_device_entity_config

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

# Default fan speed mapping for KKT Kolbe hoods
DEFAULT_SPEED_LIST = ["off", "low", "middle", "high", "strong"]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe fan entity."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

    # Get fan configuration from device_types
    fan_config = get_device_entity_config(product_name, "fan")

    # Only add if device has fan configuration
    if fan_config:
        async_add_entities([KKTKolbeFan(coordinator, entry, fan_config)])


class KKTKolbeFan(KKTBaseEntity, FanEntity):
    """Representation of a KKT Kolbe fan."""

    def __init__(self, coordinator, entry: ConfigEntry, fan_config: dict):
        """Initialize the fan."""
        # Get speeds from config or use default
        self._speed_list = fan_config.get("speeds", DEFAULT_SPEED_LIST)
        self._dp_id = fan_config.get("dp", 10)  # Default to DP 10 for fan_speed_enum

        config = {
            "dp": self._dp_id,
            "name": "Fan",
        }
        super().__init__(coordinator, entry, config, "fan")

        self._attr_supported_features = (
            FanEntityFeature.SET_SPEED |
            FanEntityFeature.TURN_ON |
            FanEntityFeature.TURN_OFF
        )
        self._attr_speed_count = len(self._speed_list) - 1  # Exclude 'off'
        self._attr_icon = "mdi:fan"
        self._cached_state = None
        self._cached_percentage = None

        # Initialize state from coordinator data
        self._update_cached_state()

    def _update_cached_state(self) -> None:
        """Update the cached state from coordinator data."""
        speed_value = self._get_data_point_value()

        # Update cached state
        if isinstance(speed_value, str):
            self._cached_state = speed_value != "off"
        elif isinstance(speed_value, (int, float)):
            self._cached_state = speed_value > 0
        else:
            self._cached_state = None

        # Update cached percentage
        if isinstance(speed_value, str):
            if speed_value == "off" or speed_value not in self._speed_list:
                self._cached_percentage = 0
            else:
                self._cached_percentage = ordered_list_item_to_percentage(self._speed_list, speed_value)
        elif isinstance(speed_value, (int, float)):
            if speed_value == 0 or speed_value >= len(self._speed_list):
                self._cached_percentage = 0
            else:
                self._cached_percentage = ordered_list_item_to_percentage(self._speed_list, self._speed_list[int(speed_value)])
        else:
            self._cached_percentage = 0

    @property
    def is_on(self) -> bool | None:
        """Return true if the fan is on."""
        return self._cached_state

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        return self._cached_percentage

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self.async_turn_off()
            return

        # Convert percentage to speed name
        speed_name = percentage_to_ordered_list_item(self._speed_list, percentage)

        # For enum types, send the string value directly
        await self._async_set_data_point(self._dp_id, speed_name)
        self._log_entity_state("Set Speed", f"Speed: {speed_name} ({percentage}%)")

    async def async_turn_on(
        self, percentage: int | None = None, preset_mode: str | None = None, **kwargs
    ) -> None:
        """Turn on the fan."""
        if percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            # Default to "low" speed
            await self._async_set_data_point(self._dp_id, "low")
            self._log_entity_state("Turn On", "Default speed: low")

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the fan."""
        # For enum types, send "off" string
        await self._async_set_data_point(self._dp_id, "off")
        self._log_entity_state("Turn Off", "Speed: off")