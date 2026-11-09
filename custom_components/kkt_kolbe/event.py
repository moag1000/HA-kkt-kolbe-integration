"""Event entities for KKT Kolbe devices.

One ``event`` entity per device turns state *transitions* into first-class
Home Assistant events, so automations can trigger on them with a plain
"entity event" trigger instead of listening to raw ``kkt_kolbe_*`` bus events
or comparing sensor states:

- ``connection_lost`` / ``connection_restored``: coordinator updates start
  failing / succeed again
- ``connection_mode_changed``: hybrid coordinator switched between local,
  IoT-API and SmartLife cloud path
- ``timer_finished``: a hood/cooktop countdown DP went from > 0 to 0
- ``filter_cleaning_due``: the filter cleaning reminder DP turned on
- ``zone_error``: a cooktop zone reported an error bit (IND7705HC DP 105)

The entity is always available (it reports transitions, including the
connection going away), and only fires on changes it actually observed: the
first coordinator update just records the baseline.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .bitfield_utils import extract_zone_bit_from_bitfield
from .const import DOMAIN
from .data import KKTKolbeConfigEntry
from .device_types import KNOWN_DEVICES

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

EVENT_CONNECTION_LOST = "connection_lost"
EVENT_CONNECTION_RESTORED = "connection_restored"
EVENT_CONNECTION_MODE_CHANGED = "connection_mode_changed"
EVENT_TIMER_FINISHED = "timer_finished"
EVENT_FILTER_CLEANING_DUE = "filter_cleaning_due"
EVENT_ZONE_ERROR = "zone_error"

# DP names (from KNOWN_DEVICES[...]["data_points"]) with a known meaning
TIMER_DP_NAMES = frozenset({"countdown", "countdown_1", "oem_device_timer_num"})
FILTER_REMINDER_DP_NAMES = frozenset({"switch_lamp"})
ZONE_ERROR_DP_NAMES = frozenset({"oem_hob_error_num"})
COOKTOP_ZONES = range(1, 6)


def _dps_by_name(device_type: str, names: frozenset[str]) -> list[int]:
    """Return the DP ids of a known device whose DP name is in ``names``."""
    data_points = KNOWN_DEVICES.get(device_type, {}).get("data_points", {}) or {}
    return sorted(int(dp) for dp, name in data_points.items() if name in names)


def _filter_reminder_dps(device_type: str) -> list[int]:
    """DPs that are really a filter cleaning reminder on this device.

    ``switch_lamp`` (DP 6) is reused for other things on some models (e.g. the
    RGB light switch), so only count it when the device exposes it as a
    filter entity.
    """
    candidates = _dps_by_name(device_type, FILTER_REMINDER_DP_NAMES)
    if not candidates:
        return []
    entities = KNOWN_DEVICES.get(device_type, {}).get("entities", {}) or {}
    filter_dps: set[int] = set()
    for configs in entities.values():
        for config in configs if isinstance(configs, list) else [configs]:
            if isinstance(config, dict) and "filter" in str(config.get("name", "")).lower():
                filter_dps.add(int(config.get("dp", -1)))
    return [dp for dp in candidates if dp in filter_dps]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KKTKolbeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the device event entity."""
    async_add_entities([KKTKolbeDeviceEvent(entry)])


def _to_int(value: Any) -> int | None:
    """Convert a DP value to int, or None if it isn't numeric."""
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except TypeError, ValueError:
        return None


class KKTKolbeDeviceEvent(CoordinatorEntity, EventEntity):
    """Fires device-level events derived from coordinator updates."""

    _attr_has_entity_name = True
    _attr_translation_key = "device_event"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: KKTKolbeConfigEntry) -> None:
        """Initialize the event entity."""
        runtime_data = entry.runtime_data
        super().__init__(runtime_data.coordinator)
        self._entry = entry

        device_type = runtime_data.device_type or ""
        self._timer_dps = _dps_by_name(device_type, TIMER_DP_NAMES)
        self._filter_dps = _filter_reminder_dps(device_type)
        self._zone_error_dps = _dps_by_name(device_type, ZONE_ERROR_DP_NAMES)

        event_types = [EVENT_CONNECTION_LOST, EVENT_CONNECTION_RESTORED]
        if hasattr(self.coordinator, "current_mode"):
            event_types.append(EVENT_CONNECTION_MODE_CHANGED)
        if self._timer_dps:
            event_types.append(EVENT_TIMER_FINISHED)
        if self._filter_dps:
            event_types.append(EVENT_FILTER_CLEANING_DUE)
        if self._zone_error_dps:
            event_types.append(EVENT_ZONE_ERROR)
        self._attr_event_types = event_types

        device_id = entry.data.get("device_id", "unknown")
        self._attr_unique_id = f"{entry.entry_id}_event_device"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)})

        # Baselines; None means "not observed yet" -> never fire on first sight
        self._last_success: bool | None = None
        self._last_mode: str | None = None
        self._last_values: dict[int, Any] = {}

    @property
    def available(self) -> bool:
        """Stay available so connection loss itself can be reported."""
        return True

    async def async_added_to_hass(self) -> None:
        """Record the current state as baseline."""
        await super().async_added_to_hass()
        self._observe(fire=False)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Compare against the previous update and fire on transitions."""
        if self._observe(fire=True):
            self.async_write_ha_state()

    def _dps(self) -> dict[Any, Any]:
        data = self.coordinator.data or {}
        dps = data.get("dps", data) if isinstance(data, dict) else {}
        return dps if isinstance(dps, dict) else {}

    def _dp_value(self, dps: dict[Any, Any], dp: int) -> Any:
        value = dps.get(str(dp))
        return dps.get(dp) if value is None else value

    def _observe(self, *, fire: bool) -> bool:
        """Update baselines; trigger events for observed transitions."""
        fired = False

        def trigger(event_type: str, attributes: dict[str, Any] | None = None) -> None:
            nonlocal fired
            if fire:
                self._trigger_event(event_type, attributes)
                fired = True

        # Connection state
        success = bool(self.coordinator.last_update_success)
        if self._last_success is not None and success != self._last_success:
            trigger(EVENT_CONNECTION_RESTORED if success else EVENT_CONNECTION_LOST)
        self._last_success = success

        # Hybrid coordinator path (local / api / smartlife)
        mode = getattr(self.coordinator, "current_mode", None)
        if isinstance(mode, str):
            if self._last_mode is not None and mode != self._last_mode:
                trigger(EVENT_CONNECTION_MODE_CHANGED, {"mode": mode, "previous_mode": self._last_mode})
            self._last_mode = mode

        # DP transitions only make sense with fresh data
        if not success:
            return fired
        dps = self._dps()

        for dp in self._timer_dps:
            value = _to_int(self._dp_value(dps, dp))
            if value is None:
                continue
            previous = self._last_values.get(dp)
            if previous is not None and previous > 0 and value == 0:
                trigger(EVENT_TIMER_FINISHED, {"data_point": dp})
            self._last_values[dp] = value

        for dp in self._filter_dps:
            raw = self._dp_value(dps, dp)
            if raw is None:
                continue
            value = bool(raw)
            previous = self._last_values.get(dp)
            if previous is False and value:
                trigger(EVENT_FILTER_CLEANING_DUE, {"data_point": dp})
            self._last_values[dp] = value

        for dp in self._zone_error_dps:
            raw = self._dp_value(dps, dp)
            if raw is None:
                continue
            for zone in COOKTOP_ZONES:
                key = dp * 100 + zone
                try:
                    has_error = bool(extract_zone_bit_from_bitfield(raw, zone))
                except Exception:
                    continue
                previous = self._last_values.get(key)
                if previous is False and has_error:
                    trigger(EVENT_ZONE_ERROR, {"zone": zone, "data_point": dp})
                self._last_values[key] = has_error

        return fired
