"""Select platform for KKT Kolbe devices."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .base_entity import KKTBaseEntity
from .device_types import get_device_entities

if TYPE_CHECKING:
    from . import KKTKolbeConfigEntry

# Limit parallel updates - 0 means unlimited (coordinator-based entities)
PARALLEL_UPDATES = 0

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KKTKolbeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe select entities."""
    runtime_data = entry.runtime_data
    coordinator = runtime_data.coordinator
    device_type = runtime_data.device_type
    product_name = runtime_data.product_name

    # Check if advanced entities are enabled (default: True)
    enable_advanced = entry.options.get("enable_advanced_entities", True)

    # Prefer device_type (KNOWN_DEVICES key) over product_name (Tuya product ID)
    lookup_key = device_type if device_type not in ("auto", None, "") else product_name

    entities = []
    select_configs = get_device_entities(lookup_key, "select")

    for config in select_configs:
        # Skip advanced entities if not enabled
        if config.get("advanced", False) and not enable_advanced:
            continue
        entities.append(KKTKolbeSelect(coordinator, entry, config))

    if entities:
        async_add_entities(entities)


class KKTKolbeSelect(KKTBaseEntity, SelectEntity):
    """Representation of a KKT Kolbe select entity."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: ConfigEntry,
        config: dict[str, Any],
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, entry, config, "select")

        # Set select-specific attributes
        self._attr_options = config.get("options", [])
        self._options_map = config.get("options_map", {})
        self._attr_icon = self._get_icon()
        self._cached_option: str | None = None

        # Initialize state from coordinator data
        self._update_cached_state()

    def _get_icon(self) -> str:
        """Get appropriate icon for the select entity."""
        name_lower = self._name.lower()

        if "rgb" in name_lower or "light" in name_lower:
            return "mdi:palette"
        elif "mode" in name_lower:
            return "mdi:format-list-bulleted"

        return "mdi:form-select"

    def _update_cached_state(self) -> None:
        """Update the cached state from coordinator data."""
        value = self._get_data_point_value()
        if value is None:
            self._cached_option = None
            return

        # Map device value to option string
        for option, device_value in self._options_map.items():
            if device_value == value:
                self._cached_option = option
                return

        # If no mapping found, try to use value directly if it's in options
        if isinstance(value, str) and value in self._attr_options:
            self._cached_option = value
        else:
            self._cached_option = None

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        return self._cached_option

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        if option not in self._attr_options:
            _LOGGER.error("Invalid option %s for %s", option, self._name)
            return

        # Map option to device value
        device_value = self._options_map.get(option, option)

        await self._async_set_data_point(self._dp, device_value)
        self._log_entity_state("Select Option", f"Option: {option}, Value: {device_value}")
