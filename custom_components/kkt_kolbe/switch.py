"""Switch platform for KKT Kolbe devices."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .base_entity import KKTBaseEntity
from .device_types import get_device_entities

if TYPE_CHECKING:
    from . import KKTKolbeConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KKTKolbeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe switch entities."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_type = runtime_data.device_type
    product_name = runtime_data.product_name

    # Check if advanced entities are enabled (default: True)
    enable_advanced = entry.options.get("enable_advanced_entities", True)

    # Prefer device_type (KNOWN_DEVICES key) over product_name (Tuya product ID)
    lookup_key = device_type if device_type not in ("auto", None, "") else product_name

    entities = []
    switch_configs = get_device_entities(lookup_key, "switch")

    for config in switch_configs:
        # Skip advanced entities if not enabled
        if config.get("advanced", False) and not enable_advanced:
            continue
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