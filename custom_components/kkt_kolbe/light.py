"""Light platform for KKT Kolbe devices.

This module provides proper LightEntity implementations for HomeKit/Siri.
Using light entities instead of switches allows Siri to understand
"Turn on the light" commands naturally.

Supports:
- Simple on/off lights
- Lights with brightness control
- Lights with effect modes (RGB presets)

Auto-Power-On Feature:
For range hoods (Dunstabzugshauben), the main power (DP 1) must be on
before the light can be controlled. This module automatically turns on
the hood if it's off when turning on the light.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS
from homeassistant.components.light import ATTR_EFFECT
from homeassistant.components.light import ColorMode
from homeassistant.components.light import LightEntity
from homeassistant.components.light import LightEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .base_entity import KKTBaseEntity
from .device_types import get_device_entities

if TYPE_CHECKING:
    from . import KKTKolbeConfigEntry

# Limit parallel updates - 0 means unlimited (coordinator-based entities)
PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)

# Auto-Power-On configuration for range hoods
HOOD_POWER_DP = 1  # DP 1 is the main power switch for all hoods
POWER_ON_DELAY = 0.5  # Delay in seconds after turning on before setting light
WORK_MODE_DELAY = 0.3  # Delay in seconds after setting work_mode before setting light


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KKTKolbeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe light entities from device_types configuration."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_type = runtime_data.device_type
    product_name = runtime_data.product_name

    # Prefer device_type (KNOWN_DEVICES key) over product_name (Tuya product ID)
    lookup_key = device_type if device_type not in ("auto", None, "") else product_name

    # Get light configuration from device_types
    light_configs = get_device_entities(lookup_key, "light")

    entities = []

    if light_configs:
        for light_config in light_configs:
            # Handle both dict format (single light) and list format
            if isinstance(light_config, dict):
                entities.append(KKTKolbeLight(coordinator, entry, light_config))

    if entities:
        _LOGGER.info(f"Setting up {len(entities)} light entities for {lookup_key} (device_type={device_type}, product={product_name})")
        async_add_entities(entities)
    else:
        _LOGGER.debug(f"No light configuration found for {lookup_key}")


class KKTKolbeLight(KKTBaseEntity, LightEntity):
    """Representation of a KKT Kolbe light.

    This light entity is designed to work well with HomeKit/Siri:
    - Siri understands "Turn on the light"
    - Supports brightness if configured
    - Supports effect modes (RGB presets)
    """

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: ConfigEntry,
        light_config: dict[str, Any],
    ) -> None:
        """Initialize the light."""
        self._dp_id = light_config.get("dp", 4)
        self._brightness_dp = light_config.get("brightness_dp")
        self._max_brightness = light_config.get("max_brightness", 255)

        # Effect/RGB mode configuration
        self._effect_dp = light_config.get("effect_dp")
        self._effect_list: list[str] = light_config.get("effects", [])
        self._effect_numeric = light_config.get("effect_numeric", False)
        # Offset for numeric effects (e.g., 1 if device uses 0=off, 1=first effect)
        self._effect_offset = light_config.get("effect_offset", 0)

        # Auto-Work-Mode configuration (for devices that need work_mode set before light works)
        self._work_mode_dp = light_config.get("work_mode_dp")
        self._work_mode_default = light_config.get("work_mode_default", "white")

        # Determine color modes
        if self._brightness_dp:
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF

        # Determine supported features
        features = LightEntityFeature(0)
        if self._effect_list:
            features |= LightEntityFeature.EFFECT
        self._attr_supported_features = features

        config: dict[str, Any] = {
            "dp": self._dp_id,
            "name": light_config.get("name", "Light"),
            "icon": light_config.get("icon", "mdi:lightbulb"),
        }
        super().__init__(coordinator, entry, config, "light")

        self._attr_icon = light_config.get("icon", "mdi:lightbulb")

        _LOGGER.info(
            "KKTKolbeLight [%s] initialized - dp: %d, brightness_dp: %s, effect_dp: %s, effects: %s, work_mode_dp: %s",
            self._name, self._dp_id, self._brightness_dp, self._effect_dp, self._effect_list, self._work_mode_dp
        )

    def _is_hood_powered_on(self) -> bool:
        """Check if the hood main power (DP 1) is on.

        For range hoods, DP 1 controls the main power switch.
        Light can only be controlled when the hood is powered on.

        Returns:
            True if the hood is powered on, False otherwise.
        """
        power_value = self._get_data_point_value(HOOD_POWER_DP)
        # Handle None or non-boolean values
        if power_value is None:
            return False
        return bool(power_value)

    async def _async_ensure_hood_power_on(self) -> None:
        """Ensure hood is powered on before controlling light.

        For range hoods, the main power (DP 1) must be on before
        the light can be controlled. This method automatically
        turns on the hood if it's off and waits for it to be ready.
        """
        if not self._is_hood_powered_on():
            _LOGGER.info(
                "KKTKolbeLight [%s]: Hood is off, turning on before setting light",
                self._name
            )
            await self._async_set_data_point(HOOD_POWER_DP, True)
            # Wait for the hood to power on before setting light
            await asyncio.sleep(POWER_ON_DELAY)

    async def _async_ensure_work_mode(self) -> None:
        """Ensure work_mode is set to default before turning on light.

        For devices like SOLO HCM, the work_mode (e.g., DP 108) must be set
        to a valid mode (e.g., "white") before the light will respond.
        Without this, the light may just blink on the device but not turn on.

        Auto-Work-Mode Feature: Automatically sets work_mode to default
        (typically "white") when turning on the light.
        """
        if not self._work_mode_dp:
            return

        # Check current work_mode
        current_mode = None
        if self.coordinator.data:
            dps_data = self.coordinator.data.get("dps", self.coordinator.data)
            current_mode = dps_data.get(str(self._work_mode_dp))

        # Only set if not already set to a valid mode
        if current_mode is None or current_mode == "":
            _LOGGER.info(
                "KKTKolbeLight [%s]: Setting work_mode (DP %d) to '%s' before turning on light",
                self._name, self._work_mode_dp, self._work_mode_default
            )
            await self._async_set_data_point(self._work_mode_dp, self._work_mode_default)
            # Wait for work_mode to be applied before setting light
            await asyncio.sleep(WORK_MODE_DELAY)

    @property
    def is_on(self) -> bool | None:
        """Return true if the light is on.

        Note: If the hood main power (DP 1) is off, the light is always off
        regardless of the light DP value.
        """
        # If hood is powered off, light is definitely off
        if not self._is_hood_powered_on():
            return False
        value = self._get_data_point_value()
        if value is None:
            return None
        return bool(value)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light (0-255).

        Note: If the hood main power (DP 1) is off, brightness is None.
        """
        if not self._brightness_dp:
            return None

        # If hood is powered off, no brightness
        if not self._is_hood_powered_on():
            return None

        # Get brightness from coordinator data
        if self.coordinator.data:
            dps_data = self.coordinator.data.get("dps", self.coordinator.data)
            brightness_value = dps_data.get(str(self._brightness_dp))
            if brightness_value is not None:
                # Scale from device range to 0-255
                return int((brightness_value / self._max_brightness) * 255)
        return None

    @property
    def effect_list(self) -> list[str] | None:
        """Return the list of supported effects."""
        if not self._effect_list:
            return None
        return self._effect_list

    @property
    def effect(self) -> str | None:
        """Return the current effect."""
        if not self._effect_dp or not self._effect_list:
            return None

        if self.coordinator.data:
            dps_data = self.coordinator.data.get("dps", self.coordinator.data)
            effect_value = dps_data.get(str(self._effect_dp))
            if effect_value is not None:
                if self._effect_numeric:
                    # Numeric mode: value is index (with offset)
                    try:
                        idx = int(effect_value) - self._effect_offset
                        if 0 <= idx < len(self._effect_list):
                            return self._effect_list[idx]
                    except (ValueError, TypeError):
                        pass
                else:
                    # String mode: value is effect name
                    if str(effect_value) in self._effect_list:
                        return str(effect_value)
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light.

        Auto-Power-On: For range hoods, automatically turns on the hood
        (DP 1) if it's off before controlling the light.

        Auto-Work-Mode: For devices like SOLO HCM, automatically sets
        work_mode to default (e.g., "white") before turning on the light.

        Note: Light must be turned ON first before setting effect/brightness,
        as most devices require the light to be on before accepting mode changes.
        """
        # Ensure hood is powered on first (Auto-Power-On feature)
        await self._async_ensure_hood_power_on()

        # Ensure work_mode is set (Auto-Work-Mode feature for SOLO HCM etc.)
        await self._async_ensure_work_mode()

        # Turn on the light FIRST (required before setting effect/brightness)
        await self._async_set_data_point(self._dp_id, True)
        self._log_entity_state("Turn On", f"DP {self._dp_id} set to True")

        # Handle effect AFTER light is on
        if ATTR_EFFECT in kwargs and self._effect_dp:
            effect = kwargs[ATTR_EFFECT]
            await self._set_effect(effect)

        # Handle brightness AFTER light is on
        if ATTR_BRIGHTNESS in kwargs and self._brightness_dp:
            brightness = kwargs[ATTR_BRIGHTNESS]
            # Scale from 0-255 to device range
            device_brightness = int((brightness / 255) * self._max_brightness)
            await self._async_set_data_point(self._brightness_dp, device_brightness)
            self._log_entity_state("Set Brightness", f"Brightness: {device_brightness}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self._async_set_data_point(self._dp_id, False)
        self._log_entity_state("Turn Off", f"DP {self._dp_id} set to False")

    async def _set_effect(self, effect: str) -> None:
        """Set the light effect."""
        if not self._effect_dp or effect not in self._effect_list:
            return

        if self._effect_numeric:
            # Numeric mode: send index with offset
            idx = self._effect_list.index(effect) + self._effect_offset
            await self._async_set_data_point(self._effect_dp, idx)
            self._log_entity_state("Set Effect", f"Effect: {effect} (value {idx})")
        else:
            # String mode: send effect name
            await self._async_set_data_point(self._effect_dp, effect)
            self._log_entity_state("Set Effect", f"Effect: {effect}")
