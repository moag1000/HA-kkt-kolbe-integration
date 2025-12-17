"""Fan platform for KKT Kolbe devices.

This module provides a proper FanEntity implementation that works well with
HomeKit/Siri integration. The fan is exposed as a percentage-based speed
control rather than multiple switches.

Supports two modes:
1. Enum mode: Speed values like "off", "low", "middle", "high", "strong"
2. Numeric mode: Speed values 0-9 (for SOLO HCM, ECCO HCM hoods)
"""
from __future__ import annotations

import logging
import math
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
    - Maps to preset speeds (enum or numeric)
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

        # Check if this is numeric mode (0-9) or enum mode (off, low, etc.)
        self._numeric_mode = fan_config.get("numeric", False)
        self._min_speed = fan_config.get("min", 0)
        self._max_speed = fan_config.get("max", len(self._speed_list) - 1)

        # For numeric mode, the "off" speed is 0
        # For enum mode, remember last non-off speed
        if self._numeric_mode:
            self._last_non_off_speed = 3  # Default to level 3 for numeric
        else:
            self._last_non_off_speed = "low"  # Default to "low" for enum

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

        # Speed count for HomeKit slider
        if self._numeric_mode:
            self._attr_speed_count = self._max_speed  # 9 steps for 0-9
        else:
            self._attr_speed_count = len(self._speed_list) - 1  # Exclude 'off'

        self._attr_icon = "mdi:fan"

        # Initialize cached state
        self._cached_state: bool | None = None
        self._cached_percentage: int = 0

        mode_str = "numeric (0-9)" if self._numeric_mode else "enum"
        _LOGGER.info(
            "KKTKolbeFan [%s] initialized - mode: %s, speeds: %s, dp: %d",
            self._name, mode_str, self._speed_list, self._dp_id
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

        if self._numeric_mode:
            # Numeric mode: 0-9
            try:
                speed_int = int(speed_value)
                self._cached_state = speed_int > 0
                # Convert 0-9 to 0-100%
                if speed_int == 0:
                    self._cached_percentage = 0
                else:
                    # Map 1-9 to roughly 11-100%
                    self._cached_percentage = int((speed_int / self._max_speed) * 100)
                    self._last_non_off_speed = speed_int
            except (ValueError, TypeError):
                self._cached_state = None
                self._cached_percentage = 0
        else:
            # Enum mode: off, low, middle, high, strong
            if isinstance(speed_value, str):
                is_on = speed_value != "off"
                self._cached_state = is_on

                if speed_value == "off" or speed_value not in self._speed_list:
                    self._cached_percentage = 0
                else:
                    self._cached_percentage = ordered_list_item_to_percentage(
                        self._speed_list, speed_value
                    )
                    self._last_non_off_speed = speed_value
            elif isinstance(speed_value, (int, float)):
                # Some devices return index instead of string
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
        Otherwise, restore the last non-off speed.
        """
        if percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            # Restore last speed
            await self._async_set_data_point(self._dp_id, self._last_non_off_speed)
            self._log_entity_state("Turn On", f"Speed: {self._last_non_off_speed}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        if self._numeric_mode:
            await self._async_set_data_point(self._dp_id, 0)
        else:
            await self._async_set_data_point(self._dp_id, "off")
        self._log_entity_state("Turn Off", "Speed: off/0")

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan.

        Args:
            percentage: Speed as percentage (0-100)

        For enum mode (5 speeds):
            - 0% = off
            - 1-25% = low
            - 26-50% = middle
            - 51-75% = high
            - 76-100% = strong

        For numeric mode (0-9):
            - 0% = 0
            - 11% = 1
            - 22% = 2
            - ...
            - 100% = 9
        """
        if percentage == 0:
            await self.async_turn_off()
            return

        if self._numeric_mode:
            # Convert percentage to 1-9
            # 1-11% → 1, 12-22% → 2, ..., 90-100% → 9
            speed_int = max(1, min(self._max_speed, math.ceil(percentage / 100 * self._max_speed)))
            await self._async_set_data_point(self._dp_id, speed_int)
            self._last_non_off_speed = speed_int
            self._log_entity_state("Set Speed", f"Speed: {speed_int} ({percentage}%)")
        else:
            # Convert percentage to speed name
            speed_name = percentage_to_ordered_list_item(self._speed_list, percentage)
            await self._async_set_data_point(self._dp_id, speed_name)
            self._last_non_off_speed = speed_name
            self._log_entity_state("Set Speed", f"Speed: {speed_name} ({percentage}%)")
