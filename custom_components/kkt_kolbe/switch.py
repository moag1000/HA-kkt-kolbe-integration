"""Switch platform for KKT Kolbe devices."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .base_entity import KKTBaseEntity
from .const import DOMAIN
from .device_types import get_device_entities

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe switch entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_type = hass.data[DOMAIN][entry.entry_id].get("device_type", "auto")
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

    # Prefer device_type (KNOWN_DEVICES key) over product_name (Tuya product ID)
    lookup_key = device_type if device_type not in ("auto", None, "") else product_name

    entities = []
    switch_configs = get_device_entities(lookup_key, "switch")

    for config in switch_configs:
        entities.append(KKTKolbeSwitch(coordinator, entry, config))

    if entities:
        async_add_entities(entities)


class KKTKolbeSwitch(KKTBaseEntity, SwitchEntity):
    """Representation of a KKT Kolbe switch."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: ConfigEntry,
        config: dict[str, Any],
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, config, "switch")
        self._attr_icon = self._get_icon()
        self._cached_state = None

        # Initialize state from coordinator data
        self._update_cached_state()

    def _get_icon(self) -> str:
        """Get appropriate icon for the switch."""
        name_lower = self._name.lower()

        if "power" in name_lower:
            return "mdi:lightning-bolt"
        elif "child" in name_lower and "lock" in name_lower:
            return "mdi:account-child"
        elif "lock" in name_lower:
            return "mdi:lock"
        elif "filter" in name_lower:
            return "mdi:air-filter"
        elif "light" in name_lower:
            return "mdi:lightbulb"
        elif "pause" in name_lower:
            return "mdi:pause"

        return "mdi:toggle-switch"

    def _update_cached_state(self) -> None:
        """Update the cached state from coordinator data."""
        value = self._get_data_point_value()
        if value is None:
            self._cached_state = None
        elif isinstance(value, bool):
            self._cached_state = value
        elif isinstance(value, int):
            self._cached_state = bool(value)
        elif isinstance(value, str):
            self._cached_state = value.lower() in ("on", "true", "1")
        else:
            self._cached_state = False

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return self._cached_state

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_set_data_point(self._dp, True)
        self._log_entity_state("Turn On", f"DP {self._dp} set to True")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_set_data_point(self._dp, False)
        self._log_entity_state("Turn Off", f"DP {self._dp} set to False")