# MQTT Push Listener for SmartLife Coordinator (v4.7)

**Status:** Design draft, awaiting implementation
**Target version:** 4.7.0
**Related:** Issue #6 snap-back race, REFACTORING_ROADMAP.md v4.7 entry

## Problem

The `KKTKolbeHybridCoordinator` currently polls Tuya every 30 seconds. State changes that originate at the device (physical button on the hood, oven program advancing, scheduler firing) are invisible to Home Assistant until the next poll, producing up to 30 s of UI lag. Writes initiated from HA must wait for a coordinator refresh to confirm — see Issue #6 where the optimistic-lock had to bridge this gap with an 8 s TTL plus a 3 s deferred refresh.

The Tuya `tuya-device-sharing-sdk` already maintains a persistent MQTT subscription that the SmartLife app uses for live device updates. Since version 0.2.8 (HA core's pinned version) the listener API also exposes a `report_type` field that distinguishes a real device-pushed report from a queried cache read. We are not consuming any of this today.

## Goal

Wire the SDK's `SharingDeviceListener` into our coordinator so that:
1. Device-originated state changes appear in HA within ~500 ms instead of 0–30 s.
2. Writes from HA are confirmed by the next push, allowing the optimistic-lock to release immediately on confirmed values instead of waiting for the deferred poll.
3. The change is purely additive — 30 s polling stays in place as a fallback for MQTT outages.

## Non-Goals

- Replace 30 s polling. That stays as a heartbeat for MQTT-down windows. A future v4.8 may move to push-primary with reduced polling cadence; this design does not.
- Add push for non-SmartLife integration modes. The local-only mode (`integration_mode == "manual"`) has no SDK Manager and therefore no MQTT channel. Local-mode coordinators are unaffected by this change.
- Out-of-order push detection using `dp_timestamps`. Last-write-wins is acceptable for v4.7. Revisit if symptoms appear.

## Architecture

```
┌────────────────────────────────────────────────────┐
│ Tuya Cloud MQTT                                    │
└──────────────────┬─────────────────────────────────┘
                   │ on_message
                   ▼
┌────────────────────────────────────────────────────┐
│ tuya_sharing.Manager                               │
│   - shared per SmartLife account                   │
│   - dispatches to all registered listeners         │
└──────────────────┬─────────────────────────────────┘
                   │ update_device(device, props, ts)
                   ▼
┌────────────────────────────────────────────────────┐
│ TuyaSharingClient._KKTSharingDeviceListener        │
│   - single instance registered with Manager        │
│   - dispatches per device_id to coordinator        │
│     callbacks                                      │
└──────────────────┬─────────────────────────────────┘
                   │ callback(updated_dps, report_type)
                   ▼
┌────────────────────────────────────────────────────┐
│ KKTKolbeHybridCoordinator._handle_push_update      │
│   - merges DPs into _dps_cache                     │
│   - sets last_update_was_push = True               │
│   - sets last_push_report_type                     │
│   - calls async_set_updated_data(new_data)         │
└──────────────────┬─────────────────────────────────┘
                   │ HA coordinator update fan-out
                   ▼
┌────────────────────────────────────────────────────┐
│ KKTBaseEntity._handle_coordinator_update           │
│   - existing optimistic auto-release path runs     │
│   - if last_update_was_push and report_type=="report"│
│     and value matches optimistic_value → hard      │
│     release immediately (skip TTL check)           │
└────────────────────────────────────────────────────┘
```

## Components

### 1. `clients/tuya_sharing_client.py` — Push Dispatcher

Add to `TuyaSharingClient`:

```python
# Type alias for push callbacks
PushCallback = Callable[[dict[str, Any], str], None]
# Signature: callback(updated_dps, report_type)
#   updated_dps: {dp_id_str: value, ...} for changed DPs only
#   report_type: "report" (device-pushed) or "query" (cached read) or "" (unknown)

class TuyaSharingClient:
    def __init__(...):
        ...
        self._push_callbacks: dict[str, list[PushCallback]] = {}
        self._sdk_listener: _KKTSharingDeviceListener | None = None

    def register_push_callback(self, device_id: str, callback: PushCallback) -> None:
        """Subscribe a coordinator to MQTT pushes for one device."""
        if not self._sdk_listener:
            self._sdk_listener = _KKTSharingDeviceListener(self)
            self._manager.add_device_listener(self._sdk_listener)
        self._push_callbacks.setdefault(device_id, []).append(callback)

    def unregister_push_callback(self, device_id: str, callback: PushCallback) -> None:
        """Unsubscribe and tear down the SDK listener if no callbacks remain."""
        callbacks = self._push_callbacks.get(device_id, [])
        if callback in callbacks:
            callbacks.remove(callback)
        if not callbacks:
            self._push_callbacks.pop(device_id, None)
        if not self._push_callbacks and self._sdk_listener:
            self._manager.remove_device_listener(self._sdk_listener)
            self._sdk_listener = None

    def _dispatch_push(
        self, device_id: str, updated_dps: dict[str, Any], report_type: str
    ) -> None:
        """Called by _KKTSharingDeviceListener.update_device."""
        for cb in self._push_callbacks.get(device_id, []):
            try:
                cb(updated_dps, report_type)
            except Exception:
                _LOGGER.exception(
                    "Push callback for device %s raised; continuing dispatch",
                    device_id[:8],
                )
```

Internal listener class:

```python
class _KKTSharingDeviceListener(SharingDeviceListener):
    """Bridges SDK callbacks into TuyaSharingClient._dispatch_push."""

    def __init__(self, client: TuyaSharingClient) -> None:
        self._client = client

    def update_device(
        self,
        device: CustomerDevice,
        updated_status_properties: list[str] | None = None,
        dp_timestamps: dict | None = None,
    ) -> None:
        if not updated_status_properties:
            return
        # SDK already wrote new values into device.status — extract changed DPs
        updated = {dp: device.status.get(dp) for dp in updated_status_properties}
        # report_type lives on the SDK device object after the message is parsed
        report_type = getattr(device, "_last_report_type", "") or ""
        self._client._dispatch_push(device.id, updated, report_type)

    def add_device(self, device: CustomerDevice) -> None:
        # We do not auto-add devices on push — config flow owns add/remove.
        pass

    def remove_device(self, device_id: str) -> None:
        # SDK signals device removal — coordinators should still tear down via
        # entry unload, not via push. No-op.
        pass
```

**Note on `report_type` extraction:** The SDK does not surface `report_type` on the listener call signature. We need to verify whether it is stored on the `CustomerDevice` instance or accessible only by patching `Manager.on_message`. Plan implementation will spike this first; if the SDK does not expose it, we fall back to treating every push as type `"report"` (since the listener only fires on real MQTT events, not on cache reads).

### 2. `hybrid_coordinator.py` — Push Handler

```python
class KKTKolbeHybridCoordinator(DataUpdateCoordinator):
    def __init__(...):
        ...
        self.last_update_was_push: bool = False
        self.last_push_report_type: str = ""
        self._push_callback_registered: bool = False

    async def async_register_push(self) -> None:
        # Called from __init__.py during entry setup, after the coordinator
        # is constructed and the SmartLife client is wired in.
        #
        # We deliberately do NOT use async_added_to_hass here:
        # DataUpdateCoordinator (unlike Entity) has no such lifecycle hook,
        # so HA would never invoke it in production. The bug went unnoticed
        # because tests called the method directly. See "Lessons learned"
        # below.
        if self.smartlife_client and not self._push_callback_registered:
            self.smartlife_client.register_push_callback(
                self.device_id, self._handle_push_update
            )
            self._push_callback_registered = True

    async def async_shutdown(self) -> None:
        if self._push_callback_registered and self.smartlife_client:
            self.smartlife_client.unregister_push_callback(
                self.device_id, self._handle_push_update
            )
            self._push_callback_registered = False
        await super().async_shutdown()

    @callback
    def _handle_push_update(
        self, updated_dps: dict[str, Any], report_type: str
    ) -> None:
        """Called by TuyaSharingClient on MQTT push for our device."""
        # Merge into existing DPS cache (push only contains changed DPs)
        self._dps_cache.update({str(k): v for k, v in updated_dps.items()})

        new_data = {
            "dps": dict(self._dps_cache),
            "source": "smartlife_push",
            "timestamp": datetime.now().isoformat(),
        }
        self.last_update_was_push = True
        self.last_push_report_type = report_type
        self.async_set_updated_data(new_data)
        self.last_update_was_push = False  # reset after fan-out
```

### 3. `base_entity.py` — Aggressive Lock Release on Confirmed Push

```python
@callback
def _handle_coordinator_update(self) -> None:
    # Existing path: read coord, update cache, check optimistic
    coord = self.coordinator
    if (
        getattr(coord, "last_update_was_push", False)
        and coord.last_push_report_type == "report"
        and self._is_optimistic_active()
    ):
        # Push from device confirms our write: release lock unconditionally
        # if the pushed value matches what we wrote
        pushed_value = self._read_coord_dp_raw(self._dp)
        if pushed_value == self._optimistic_value:
            self._clear_optimistic()

    self._update_cached_state()
    self.async_write_ha_state()
```

The "value matches" check stays the same as today's auto-release. The difference is we trust a `report_type=="report"` match without further scrutiny — it is a hard confirmation from the device, not a possibly-stale cloud read.

## Failure Modes

| Failure | Behavior | Notes |
|---------|----------|-------|
| Listener callback raises | Caught in `_dispatch_push`, logged, dispatch continues to other callbacks | Coord push handler also `try/except`s internally |
| MQTT disconnect | SDK auto-reconnects (since 0.2.x). 30 s polling continues uninterrupted | No special handling needed |
| Multiple coordinators on same device_id | Should not happen; entry uniqueness enforces single coord per device | List allows graceful degradation if it ever does |
| Out-of-order pushes | Last-write-wins for v4.7. `dp_timestamps` ignored | Future enhancement |
| Push fires before coord registered | Push dropped (no callback registered yet). Next 30 s poll picks it up | Acceptable startup-window race |
| Coord re-created (entry reload) | Old coord's `async_shutdown` deregisters; new coord re-registers via `async_register_push` invoked from `_async_background_connect` | Memory-leak risk if shutdown skipped — assert in tests |

## Test Strategy

New tests in `tests/test_tuya_sharing_client.py`:
- `test_register_push_callback_creates_listener_on_first_register`
- `test_register_push_callback_reuses_listener_on_second_register`
- `test_unregister_push_callback_removes_listener_when_last_callback_gone`
- `test_dispatch_push_calls_all_callbacks_for_device`
- `test_dispatch_push_isolates_callback_exceptions`
- `test_dispatch_push_only_callbacks_for_target_device`

New tests in `tests/test_coordinator.py` (or new `test_hybrid_coordinator_push.py`):
- `test_hybrid_coord_registers_push_callback_via_async_register_push`
- `test_hybrid_coord_unregisters_on_shutdown`
- `test_handle_push_update_merges_into_dps_cache`
- `test_handle_push_update_calls_async_set_updated_data`
- `test_handle_push_update_sets_last_update_was_push`

Extension to `tests/test_switch.py` (and select, number):
- `test_switch_optimistic_releases_immediately_on_matching_push_report`
- `test_switch_optimistic_holds_when_push_value_does_not_match`
- `test_switch_optimistic_holds_on_query_report_type` (only "report" triggers hard release)

## Backwards Compatibility

- **SmartLife / Hybrid mode users:** Notice faster UI updates after HACS upgrade. No config change required. No breaking change.
- **Local-only / manual mode users:** Unaffected. `smartlife_client` is `None`, push registration is skipped.
- **Existing automations / scripts:** Behavior identical from the entity-state perspective. Internal change only.

## Migration

None required. Pure additive change. Roll back by reverting the commit.

## Resolved Open Questions

1. Does `tuya-device-sharing-sdk>=0.2.8` actually expose `report_type` on the `update_device` callback path, or only inside `Manager.on_message` before it dispatches? Spike first.

   **Resolved:** No — the listener signature is `update_device(device, updated_status_properties, dp_timestamps)`; `Manager.on_message` filters by `PROTOCOL_DEVICE_REPORT` internally and never forwards report_type, so Task 1's listener must treat every callback as a device-status report (use the `updated_status_properties` list to scope which DPs changed) and ignore report-type-based branching.

2. Is `Manager.add_device_listener` thread-safe? SDK callbacks may fire from MQTT thread, not HA event loop. We need `hass.loop.call_soon_threadsafe` to bounce into the loop before calling `async_set_updated_data`.

   **Resolved:** Not safe — `SharingMQ` extends `threading.Thread` (`tuya_sharing/mq.py` line 33), so `on_message` and the chained listener callback execute on the MQTT background thread; Task 1's `update_device` implementation must use `hass.loop.call_soon_threadsafe(coordinator.async_set_updated_data, ...)` to hop into the HA event loop before touching coordinator state or entities.

3. What does `device.status` look like after an MQTT update — keyed by string DP IDs as the coordinator expects, or by `code` strings (e.g. `"switch_1"`)? Need to confirm with a small live test or by reading SDK source.

   **Resolved:** Keyed by `code` strings — `Manager._on_device_report` runs `strategy.convert()` against `device.local_strategy[dpId]` to produce `(code, value)` and writes `device.status[code] = value` (raw DP-id integers are never exposed); Task 1's listener must read `device.status` by status_code and the coordinator's update path needs to map those codes back to DP-id keys (via the existing `local_strategy` reverse lookup) before merging into the coordinator's DP-id-keyed snapshot.

These were pinned for the implementation plan to address as the first three steps (probe SDK behavior before writing the bridge code) and were resolved by Task 0's spike.

## Lessons learned during implementation

### Critical bug: `async_added_to_hass` is not a Coordinator hook

The original Task 2 implementation used `async def async_added_to_hass(self)` on
`KKTKolbeHybridCoordinator` (which extends `DataUpdateCoordinator`). That hook
exists on `Entity` and `CoordinatorEntity`, **not** on `DataUpdateCoordinator` —
production HA never invoked it, so `register_push_callback` never fired and the
v4.7 feature was inert end-to-end. Tests passed because they called the method
directly (`await coord.async_added_to_hass()`), masking the issue.

**Fix:** Renamed to `async_register_push` and wired explicitly from
`_async_background_connect` in `__init__.py`, after `mark_initial_connect_done()`
so the SmartLife client is fully online when registration happens. A regression
test now drives `_async_background_connect` end-to-end and asserts
`async_register_push` is invoked.

**Takeaway:** When mixing in lifecycle-style methods on non-Entity HA classes,
verify the parent class actually has the hook before relying on it. Entity-only
hooks include `async_added_to_hass`, `async_will_remove_from_hass`, and
`async_remove`. `DataUpdateCoordinator` exposes only `async_shutdown` and the
`async_setup` / `_async_update_data` callbacks.
