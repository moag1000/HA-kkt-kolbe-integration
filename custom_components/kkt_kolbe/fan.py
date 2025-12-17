"""Fan platform for KKT Kolbe devices.

This module provides a proper FanEntity implementation that works well with
HomeKit/Siri integration. The fan is exposed as a percentage-based speed
control rather than multiple switches.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .base_entity import KKTBaseEntity
from .const import DOMAIN
from .device_types import get_device_entities, get_device_entity_config

_LOGGER = logging.getLogger(__name__)


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
        _LOGGER.info(f"Setting up fan entity for {product_name} with config: {fan_config}")
        async_add_entities([KKTKolbeFan(coordinator, entry, fan_config)])
    else:
        _LOGGER.debug(f"No fan configuration found for {product_name}")


class KKTKolbeFan(KKTBaseEntity, FanEntity):
    """Representation of a KKT Kolbe fan.

    This fan entity is designed to work well with HomeKit/Siri:
    - Exposes speed as a percentage (0-100%)
    - Maps to preset speeds: off, low, middle, high, strong
    - Supports turn_on, turn_off, and set_percentage
    """

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: ConfigEntry,
        fan_config: dict[str, Any],
    ) -> None:
        """Initialize the fan."""
        # Get speeds from config or use default
        self._speed_list = fan_config.get("speeds", DEFAULT_SPEED_LIST)
        self._dp_id = fan_config.get("dp", 10)  # Default to DP 10 for fan_speed_enum
        self._last_non_off_speed = "low"  # Remember last speed for turn_on

        config: dict[str, Any] = {
            "dp": self._dp_id,
            "name": "Fan",
        }
        super().__init__(coordinator, entry, config, "fan")

        # Supported features for HomeKit compatibility
        self._attr_supported_features = (
            FanEntityFeature.SET_SPEED |
            FanEntityFeature.TURN_ON |
            FanEntityFeature.TURN_OFF
        )

        # Speed count excludes 'off' - HomeKit uses this for slider steps
        self._attr_speed_count = len(self._speed_list) - 1
        self._attr_icon = "mdi:fan"

        # Initialize cached state
        self._cached_state: bool | None = None
        self._cached_percentage: int = 0

        _LOGGER.info(
            "KKTKolbeFan [%s] initialized - speeds: %s, dp: %d",
            self._name, self._speed_list, self._dp_id
        )

        # Initialize state from coordinator data
        self._update_cached_state()

    def _update_cached_state(self) -> None:
        """Update the cached state from coordinator data."""
        speed_value = self._get_data_point_value()

        if speed_value is None:
            self._cached_state = None
            self._cached_percentage = 0
            return

        # Handle string speed values (enum)
        if isinstance(speed_value, str):
            is_on = speed_value != "off"
            self._cached_state = is_on

            if speed_value == "off" or speed_value not in self._speed_list:
                self._cached_percentage = 0
            else:
                self._cached_percentage = ordered_list_item_to_percentage(
                    self._speed_list, speed_value
                )
                # Remember this speed for turn_on
                self._last_non_off_speed = speed_value

        # Handle numeric speed values (index)
        elif isinstance(speed_value, (int, float)):
            idx = int(speed_value)
            is_on = idx > 0
            self._cached_state = is_on

            if idx == 0 or idx >= len(self._speed_list):
                self._cached_percentage = 0
            else:
                speed_name = self._speed_list[idx]
                self._cached_percentage = ordered_list_item_to_percentage(
                    self._speed_list, speed_name
                )
                self._last_non_off_speed = speed_name
        else:
            self._cached_state = None
            self._cached_percentage = 0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_cached_state()
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool | None:
        """Return true if the fan is on."""
        return self._cached_state

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage (0-100)."""
        return self._cached_percentage

    @property
    def preset_modes(self) -> list[str] | None:
        """Return the list of available preset modes.

        Note: We don't expose preset_modes to keep HomeKit simple.
        HomeKit works better with just percentage-based control.
        """
        return None

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan.

        If percentage is provided, set that speed.
        Otherwise, restore the last non-off speed (default: low).
        """
        if percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            # Restore last speed or use "low" as default
            await self._async_set_data_point(self._dp_id, self._last_non_off_speed)
            self._log_entity_state("Turn On", f"Speed: {self._last_non_off_speed}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        await self._async_set_data_point(self._dp_id, "off")
        self._log_entity_state("Turn Off", "Speed: off")

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan.

        Args:
            percentage: Speed as percentage (0-100)
                - 0% = off
                - 1-25% = low
                - 26-50% = middle
                - 51-75% = high
                - 76-100% = strong
        """
        if percentage == 0:
            await self.async_turn_off()
            return

        # Convert percentage to speed name
        speed_name = percentage_to_ordered_list_item(self._speed_list, percentage)

        # Send the speed value to the device
        await self._async_set_data_point(self._dp_id, speed_name)

        # Remember this speed for turn_on
        self._last_non_off_speed = speed_name

        self._log_entity_state("Set Speed", f"Speed: {speed_name} ({percentage}%)")
