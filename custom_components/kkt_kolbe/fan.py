"""Fan platform for KKT Kolbe devices.

This module provides a proper FanEntity implementation that works well with
HomeKit/Siri integration. The fan is exposed as a percentage-based speed
control rather than multiple switches.

Supports two modes:
1. Enum mode: Speed values like "off", "low", "middle", "high", "strong"
2. Numeric mode: Speed values 0-9 (for SOLO HCM, ECCO HCM hoods)

Auto-Power-On Feature:
For range hoods (Dunstabzugshauben), the main power (DP 1) must be on
before fan speed can be set. This module automatically turns on the hood
if it's off when setting fan speed.
"""
from __future__ import annotations

import asyncio
import logging
import math
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.components.fan import FanEntity
from homeassistant.components.fan import FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.percentage import ordered_list_item_to_percentage
from homeassistant.util.percentage import percentage_to_ordered_list_item

from .base_entity import KKTBaseEntity
from .device_types import get_device_entity_config

if TYPE_CHECKING:
    from . import KKTKolbeConfigEntry

# Limit parallel updates - 0 means unlimited (coordinator-based entities)
PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)


# Default fan speed mapping for KKT Kolbe hoods
DEFAULT_SPEED_LIST = ["off", "low", "middle", "high", "strong"]

# Auto-Power-On configuration for range hoods
HOOD_POWER_DP = 1  # DP 1 is the main power switch for all hoods
POWER_ON_DELAY = 0.5  # Delay in seconds after turning on before setting fan speed


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KKTKolbeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe fan entity."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_type = runtime_data.device_type
    product_name = runtime_data.product_name

    # Prefer device_type (KNOWN_DEVICES key) over product_name (Tuya product ID)
    lookup_key = device_type if device_type not in ("auto", None, "") else product_name

    # Get fan configuration from device_types
    fan_config = get_device_entity_config(lookup_key, "fan")

    # Only add if device has fan configuration
    if fan_config:
        _LOGGER.info(f"Setting up fan entity for {lookup_key} (device_type={device_type}, product={product_name}) with config: {fan_config}")
        async_add_entities([KKTKolbeFan(coordinator, entry, fan_config)])
    else:
        _LOGGER.debug(f"No fan configuration found for {lookup_key}")


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
        self._last_non_off_speed: int | str
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

    def _is_hood_powered_on(self) -> bool:
        """Check if the hood main power (DP 1) is on.

        For range hoods, DP 1 controls the main power switch.
        Fan speed and light can only be controlled when the hood is powered on.

        Returns:
            True if the hood is powered on, False otherwise.
        """
        power_value = self._get_data_point_value(HOOD_POWER_DP)
        # Handle None or non-boolean values
        if power_value is None:
            return False
        return bool(power_value)

    async def _async_ensure_hood_power_on(self) -> None:
        """Ensure hood is powered on before setting fan speed.

        For range hoods, the main power (DP 1) must be on before
        fan speed can be controlled. This method automatically
        turns on the hood if it's off and waits for it to be ready.
        """
        if not self._is_hood_powered_on():
            _LOGGER.info(
                "KKTKolbeFan [%s]: Hood is off, turning on before setting fan speed",
                self._name
            )
            await self._async_set_data_point(HOOD_POWER_DP, True)
            # Wait for the hood to power on before setting fan speed
            await asyncio.sleep(POWER_ON_DELAY)

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
        """Return true if the fan is on.

        Note: If the hood main power (DP 1) is off, the fan is always off
        regardless of the fan speed DP value.
        """
        # If hood is powered off, fan is definitely off
        if not self._is_hood_powered_on():
            return False
        return self._cached_state

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage (0-100).

        Note: If the hood main power (DP 1) is off, percentage is always 0.
        """
        # If hood is powered off, percentage is 0
        if not self._is_hood_powered_on():
            return 0
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

        Auto-Power-On: For range hoods, automatically turns on the hood
        (DP 1) if it's off before setting fan speed.
        """
        # Ensure hood is powered on first (Auto-Power-On feature)
        await self._async_ensure_hood_power_on()

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

        Auto-Power-On: For range hoods, automatically turns on the hood
        (DP 1) if it's off before setting fan speed (non-zero percentage only).
        """
        if percentage == 0:
            await self.async_turn_off()
            return

        # Ensure hood is powered on first (Auto-Power-On feature)
        await self._async_ensure_hood_power_on()

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
