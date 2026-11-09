"""Raise a repair issue when a device stays unreachable for a long time.

Short outages (Wi-Fi hiccups, hood unplugged for cleaning) are normal and
already visible through the connection sensor and the ``connection_lost``
event. Only when a device has not answered for ``OFFLINE_ISSUE_AFTER`` does
a repair card explain what to check. The card disappears on its own as soon
as the device answers again.
"""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .data import KKTCoordinator
from .data import KKTKolbeConfigEntry

OFFLINE_ISSUE_AFTER = timedelta(hours=24)
CHECK_INTERVAL = timedelta(hours=1)


def issue_id(entry: KKTKolbeConfigEntry) -> str:
    """Repair issue id for an entry."""
    return f"device_offline_{entry.entry_id}"


class OfflineMonitor:
    """Track how long a coordinator has been failing."""

    def __init__(self, hass: HomeAssistant, entry: KKTKolbeConfigEntry, coordinator: KKTCoordinator) -> None:
        """Initialize the monitor."""
        self._hass = hass
        self._entry = entry
        self._coordinator = coordinator
        self.offline_since: datetime | None = None

    @callback
    def async_start(self) -> None:
        """Start listening; stops automatically when the entry unloads."""
        self._entry.async_on_unload(self._coordinator.async_add_listener(self._async_coordinator_updated))
        self._entry.async_on_unload(async_track_time_interval(self._hass, self._async_check, CHECK_INTERVAL))

    @callback
    def _async_coordinator_updated(self) -> None:
        """Remember when the outage started; clear the issue on recovery."""
        if self._coordinator.last_update_success:
            self.offline_since = None
            # The issue survives restarts, so check the registry, not just
            # our own state
            if ir.async_get(self._hass).async_get_issue(DOMAIN, issue_id(self._entry)):
                ir.async_delete_issue(self._hass, DOMAIN, issue_id(self._entry))
        elif self.offline_since is None:
            self.offline_since = dt_util.utcnow()

    @callback
    def _async_check(self, now: datetime | None = None) -> None:
        """Create the repair issue once the outage is long enough."""
        if self.offline_since is None:
            return
        if dt_util.utcnow() - self.offline_since < OFFLINE_ISSUE_AFTER:
            return
        ir.async_create_issue(
            self._hass,
            DOMAIN,
            issue_id(self._entry),
            is_fixable=False,
            is_persistent=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="device_offline",
            translation_placeholders={
                "device_name": self._entry.title,
                "offline_since": dt_util.as_local(self.offline_since).strftime("%Y-%m-%d %H:%M"),
            },
        )


@callback
def async_remove_issue(hass: HomeAssistant, entry: KKTKolbeConfigEntry) -> None:
    """Drop the issue when the entry is removed."""
    ir.async_delete_issue(hass, DOMAIN, issue_id(entry))
