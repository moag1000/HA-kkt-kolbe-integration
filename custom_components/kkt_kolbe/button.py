"""Button entities for KKT Kolbe devices.

A "Reconnect" button per device with a local connection, so a stuck local
session can be reset from the device page (or a dashboard / automation)
without calling the ``kkt_kolbe.reconnect_device`` action by hand.
"""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .data import KKTCoordinator
from .data import KKTKolbeConfigEntry
from .services import async_reconnect_coordinator

_LOGGER = logging.getLogger(__name__)

# Reconnecting twice at the same time makes no sense
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KKTKolbeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the reconnect button for devices with a local connection."""
    runtime_data = entry.runtime_data
    if runtime_data.device is None and not hasattr(runtime_data.coordinator, "async_request_reconnect"):
        # Cloud-only device: there is no local session to reset
        return
    async_add_entities([KKTKolbeReconnectButton(entry)])


class KKTKolbeReconnectButton(CoordinatorEntity[KKTCoordinator], ButtonEntity):
    """Reset the local connection of the device."""

    _attr_has_entity_name = True
    _attr_translation_key = "reconnect"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: KKTKolbeConfigEntry) -> None:
        """Initialize the button."""
        super().__init__(entry.runtime_data.coordinator)
        device_id = entry.data.get("device_id", "unknown")
        self._attr_unique_id = f"{entry.entry_id}_reconnect"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

    @property
    def available(self) -> bool:
        """Always pressable: reconnecting is the fix for an offline device."""
        return True

    async def async_press(self) -> None:
        """Reconnect and report a failure in the UI."""
        try:
            result = await async_reconnect_coordinator(self.coordinator)
        except Exception as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="reconnect_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        if not result.get("success"):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="reconnect_failed",
                translation_placeholders={"error": str(result.get("error") or result.get("state", "unknown"))},
            )
