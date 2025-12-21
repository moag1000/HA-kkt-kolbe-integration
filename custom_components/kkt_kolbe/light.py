"""Light platform for KKT Kolbe devices.

This module provides proper LightEntity implementations for HomeKit/Siri.
Using light entities instead of switches allows Siri to understand
"Turn on the light" commands naturally.

Supports:
- Simple on/off lights
- Lights with brightness control
- Lights with effect modes (RGB presets)
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    LightEntity,
    LightEntityFeature,
    ColorMode,
    ATTR_BRIGHTNESS,
    ATTR_EFFECT,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .base_entity import KKTBaseEntity
from .const import DOMAIN
from .device_types import get_device_entities, KNOWN_DEVICES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe light entities from device_types configuration."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_type = hass.data[DOMAIN][entry.entry_id].get("device_type", "auto")
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

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
        self._effect_list = light_config.get("effects", [])
        self._effect_numeric = light_config.get("effect_numeric", False)

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
            "KKTKolbeLight [%s] initialized - dp: %d, brightness_dp: %s, effect_dp: %s, effects: %s",
            self._name, self._dp_id, self._brightness_dp, self._effect_dp, self._effect_list
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the light is on."""
        value = self._get_data_point_value()
        if value is None:
            return None
        return bool(value)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light (0-255)."""
        if not self._brightness_dp:
            return None

        # Get brightness from coordinator data
        if self.coordinator.data:
            brightness_value = self.coordinator.data.get(str(self._brightness_dp))
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
            effect_value = self.coordinator.data.get(str(self._effect_dp))
            if effect_value is not None:
                if self._effect_numeric:
                    # Numeric mode: value is index
                    try:
                        idx = int(effect_value)
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
        """Turn on the light."""
        # Handle effect if provided
        if ATTR_EFFECT in kwargs and self._effect_dp:
            effect = kwargs[ATTR_EFFECT]
            await self._set_effect(effect)

        # Handle brightness if provided and supported
        if ATTR_BRIGHTNESS in kwargs and self._brightness_dp:
            brightness = kwargs[ATTR_BRIGHTNESS]
            # Scale from 0-255 to device range
            device_brightness = int((brightness / 255) * self._max_brightness)
            await self._async_set_data_point(self._brightness_dp, device_brightness)
            self._log_entity_state("Set Brightness", f"Brightness: {device_brightness}")

        # Turn on the light
        await self._async_set_data_point(self._dp_id, True)
        self._log_entity_state("Turn On", f"DP {self._dp_id} set to True")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self._async_set_data_point(self._dp_id, False)
        self._log_entity_state("Turn Off", f"DP {self._dp_id} set to False")

    async def _set_effect(self, effect: str) -> None:
        """Set the light effect."""
        if not self._effect_dp or effect not in self._effect_list:
            return

        if self._effect_numeric:
            # Numeric mode: send index
            idx = self._effect_list.index(effect)
            await self._async_set_data_point(self._effect_dp, idx)
            self._log_entity_state("Set Effect", f"Effect: {effect} (index {idx})")
        else:
            # String mode: send effect name
            await self._async_set_data_point(self._effect_dp, effect)
            self._log_entity_state("Set Effect", f"Effect: {effect}")
