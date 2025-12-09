"""Light platform for KKT Kolbe devices."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .base_entity import KKTBaseEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe light entity."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

    # Only add light entity for HERMES & STYLE (range hood)
    if "HERMES" in product_name and "STYLE" in product_name:
        async_add_entities([KKTKolbeLight(coordinator, entry)])


class KKTKolbeLight(KKTBaseEntity, LightEntity):
    """Representation of a KKT Kolbe light."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[dict[str, Any]],
        entry: ConfigEntry,
    ) -> None:
        """Initialize the light."""
        config: dict[str, Any] = {
            "dp": 3,
            "name": "Light",
        }
        super().__init__(coordinator, entry, config, "light")
        self._attr_icon = "mdi:lightbulb"

    @property
    def is_on(self) -> bool | None:
        """Return true if the light is on."""
        value = self._get_data_point_value()
        return value is not None and bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        await self._async_set_data_point(self._dp, True)
        self._log_entity_state("Turn On", f"DP {self._dp} set to True")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self._async_set_data_point(self._dp, False)
        self._log_entity_state("Turn Off", f"DP {self._dp} set to False")