"""Switch platform for KKT Kolbe devices."""
import logging
from datetime import timedelta
from typing import Any
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .device_types import get_device_entities

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KKT Kolbe switch entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]
    product_name = hass.data[DOMAIN][entry.entry_id].get("product_name", "unknown")

    entities = []
    switch_configs = get_device_entities(product_name, "switch")

    for config in switch_configs:
        entities.append(KKTKolbeSwitch(coordinator, entry, config))

    if entities:
        async_add_entities(entities)

class KKTKolbeSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a KKT Kolbe switch."""

    def __init__(self, coordinator, entry: ConfigEntry, config: dict):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._entry = entry
        self._config = config
        self._dp = config["dp"]
        self._name = config["name"]
        self._attr_unique_id = f"{entry.entry_id}_switch_{self._name.lower().replace(' ', '_')}"
        self._attr_has_entity_name = True
        self._attr_name = self._name
        self._attr_icon = self._get_icon()
        self._attr_device_class = config.get("device_class")
        self._attr_entity_category = self._get_entity_category()

    def _get_icon(self) -> str:
        """Get appropriate icon for the switch."""
        name_lower = self._name.lower()
        if "power" in name_lower:
            return "mdi:power"
        elif "pause" in name_lower:
            return "mdi:pause"
        elif "lock" in name_lower:
            return "mdi:lock"
        elif "senior" in name_lower:
            return "mdi:account-supervisor"
        elif "confirm" in name_lower:
            return "mdi:check"
        elif "filter" in name_lower:
            return "mdi:air-filter"
        else:
            return "mdi:toggle-switch"

    def _get_entity_category(self):
        """Get appropriate entity category for the switch."""
        name_lower = self._name.lower()

        # Config switches: child lock, senior mode
        if any(word in name_lower for word in ["lock", "senior", "pause"]):
            return EntityCategory.CONFIG

        # Diagnostic switches: filter reset, filter reminder
        if "filter" in name_lower:
            return EntityCategory.DIAGNOSTIC

        return None

    @property
    def device_info(self):
        """Return device information."""
        return self.coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return if the switch is on."""
        data = self.coordinator.data
        if not data:
            return False
        return data.get(self._dp, False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        await self.coordinator.async_set_data_point(self._dp, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self.coordinator.async_set_data_point(self._dp, False)