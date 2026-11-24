"""Device writes that the device has not confirmed yet, shared per device.

Tuya devices (and above all the Tuya cloud) report a written value back with
a delay of one to three seconds. Until then a poll still returns the old
value. To keep the UI from snapping back (Issue #6) every write is recorded
here, per data point, and overlaid on the reported data until the device
reports the written value or the window expires.

The overlay lives on the coordinator, not on a single entity, because one
data point feeds several entities: the hood power DP 1 drives the power
switch, the fan and the light, and the cooktop zone bitfields (DP 162 ...)
hold the values of all five zones. Every entity of the device therefore sees
the same picture, and a write for zone 2 builds on a pending write for
zone 1 instead of resetting it.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

# Tuya cloud propagation typically takes 1-3s after a write before reads
# return the new value. Within this window the written value wins.
OPTIMISTIC_TTL_SECONDS = 8.0


@dataclass(slots=True, frozen=True)
class PendingWrite:
    """One unconfirmed write."""

    value: Any
    expires: float

    @property
    def active(self) -> bool:
        """Return True while the write is still waiting for confirmation."""
        return self.expires > time.monotonic()


class PendingWrites:
    """Unconfirmed writes of one device, keyed by data point."""

    def __init__(self) -> None:
        """Initialize an empty overlay."""
        self._writes: dict[str, PendingWrite] = {}

    def set(self, dp: int | str, value: Any, ttl: float = OPTIMISTIC_TTL_SECONDS) -> PendingWrite | None:
        """Record a write and return the write it replaces (for ``restore``)."""
        key = str(dp)
        previous = self._writes.get(key)
        self._writes[key] = PendingWrite(value, time.monotonic() + ttl)
        return previous

    def restore(self, dp: int | str, previous: PendingWrite | None) -> None:
        """Undo a failed write: bring back the write it replaced, if any."""
        key = str(dp)
        if previous is not None and previous.active:
            self._writes[key] = previous
        else:
            self._writes.pop(key, None)

    def clear(self, dp: int | str) -> None:
        """Drop the pending write of a data point."""
        self._writes.pop(str(dp), None)

    def get(self, dp: int | str) -> PendingWrite | None:
        """Return the active pending write of a data point, if any."""
        write = self._writes.get(str(dp))
        if write is not None and not write.active:
            del self._writes[str(dp)]
            return None
        return write

    def apply(self, dps: Mapping[Any, Any]) -> dict[Any, Any]:
        """Return ``dps`` with the pending writes overlaid.

        A write is released as soon as the device reports the written value
        (or when it expires), so later changes from the device, the physical
        buttons or another app show up again.
        """
        result = dict(dps)
        for key in list(self._writes):
            write = self.get(key)
            if write is None:
                continue
            reported = dps.get(key)
            if reported is None and key.isdigit():
                reported = dps.get(int(key))
            if reported == write.value:
                del self._writes[key]
                continue
            result[key] = write.value
            if key.isdigit():
                result.pop(int(key), None)
        return result


def pending_writes_for(coordinator: Any) -> PendingWrites:
    """Return the pending-write overlay of a coordinator.

    Both coordinators create one in ``__init__``; coordinators that do not
    (test doubles) get one attached on first use.
    """
    pending = getattr(coordinator, "pending_writes", None)
    if not isinstance(pending, PendingWrites):
        pending = PendingWrites()
        coordinator.pending_writes = pending
    return pending


def effective_dps(coordinator: Any) -> dict[Any, Any]:
    """Return the coordinator's DPs with the unconfirmed writes overlaid.

    This is the single view entities derive their state from. Code that must
    only react to what the device really reported (the event entity) reads
    ``coordinator.data`` instead.
    """
    data = coordinator.data
    if not isinstance(data, Mapping):
        return {}
    dps = data.get("dps", data)
    if not isinstance(dps, Mapping):
        return {}
    return pending_writes_for(coordinator).apply(dps)
