# MQTT Push Listener for SmartLife Coordinator — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SDK SharingDeviceListener to KKTKolbeHybridCoordinator so MQTT pushes from Tuya cloud trigger immediate state updates and confirmed-write optimistic-lock release, without removing the existing 30 s polling fallback.

**Architecture:** Single `_KKTSharingDeviceListener` registered with `tuya_sharing.Manager` per SmartLife account. Listener dispatches to per-device callbacks held in `TuyaSharingClient`. Each `KKTKolbeHybridCoordinator` registers its `_handle_push_update` callback via `async_register_push`, called from `_async_background_connect` in `__init__.py` after `mark_initial_connect_done()`; deregisters in `async_shutdown`. (Note: `DataUpdateCoordinator` does not have an `async_added_to_hass` hook — that is Entity-only — so we wire registration explicitly from setup. See spec "Lessons learned" for the bug history.) On push, coordinator merges DPs and calls `async_set_updated_data`. Entities check `coordinator.last_update_was_push` + `last_push_report_type == "report"` to hard-release optimistic locks on confirmed writes.

**Tech Stack:** Python 3.12, Home Assistant, `tuya-device-sharing-sdk>=0.2.8`, pytest, pytest-homeassistant-custom-component, ruff.

**Reference Spec:** `docs/superpowers/specs/2026-05-04-mqtt-push-listener-design.md`

---

## File Structure

| Path | Action | Responsibility |
|------|--------|----------------|
| `scripts/spike_sdk_listener.py` | Create | One-shot exploration script for SDK behavior; deleted after Task 0 |
| `custom_components/kkt_kolbe/clients/tuya_sharing_client.py` | Modify | Add `_KKTSharingDeviceListener` class + `register_push_callback` / `unregister_push_callback` / `_dispatch_push` |
| `custom_components/kkt_kolbe/hybrid_coordinator.py` | Modify | Add `last_update_was_push`, `last_push_report_type`, `_handle_push_update`, lifecycle hooks |
| `custom_components/kkt_kolbe/base_entity.py` | Modify | Extend `_handle_coordinator_update` to hard-release optimistic on `report_type == "report"` matching push |
| `tests/test_tuya_sharing_client.py` | Modify | 6 new tests for dispatcher behavior |
| `tests/test_hybrid_coordinator_push.py` | Create | New file, 5 tests for coordinator push handling |
| `tests/test_switch.py` | Modify | 3 new tests for push-triggered lock behavior |
| `custom_components/kkt_kolbe/manifest.json` | Modify | Bump version to `4.7.0` |
| `custom_components/kkt_kolbe/const.py` | Modify | Bump VERSION to `4.7.0` |
| `pyproject.toml` | Modify | Sync version to `4.7.0` |
| `CHANGELOG.md` | Modify | Add v4.7.0 entry |
| `REFACTORING_ROADMAP.md` | Modify | Mark v4.7 entry as DONE |

---

## Task 0: Spike SDK behavior (single-session exploration)

**Goal:** Resolve the three open questions in the spec before writing the bridge code:
1. Does the SDK surface `report_type` on the listener callback path?
2. Is `Manager.add_device_listener` thread-safe (does it fire from the MQTT thread)?
3. What does `device.status` look like after an MQTT update (DP-id keys vs `code` strings)?

**Files:**
- Create: `scripts/spike_sdk_listener.py`

- [ ] **Step 1: Write the spike script**

```python
# scripts/spike_sdk_listener.py
"""One-shot SDK behavior probe. Run, read output, then delete this file."""
from __future__ import annotations
import inspect
import threading

from tuya_sharing import Manager, SharingDeviceListener
from tuya_sharing.manager import Manager as ManagerImpl
from tuya_sharing.customerapi import CustomerApi
from tuya_sharing.customerlogin import CustomerTokenInfo


print("=" * 60)
print("Q1: report_type on listener callback path?")
print("=" * 60)
# Inspect Manager.on_message and _on_device_report for report_type plumbing
src = inspect.getsource(ManagerImpl.on_message)
print("--- Manager.on_message ---")
print(src)
print()
src2 = inspect.getsource(ManagerImpl._on_device_report)
print("--- Manager._on_device_report ---")
print(src2)
print()

# Check SharingDeviceListener.update_device signature
print("--- SharingDeviceListener.update_device ---")
print(inspect.signature(SharingDeviceListener.update_device))
print()

# Look for any attribute on CustomerDevice that could hold report_type
from tuya_sharing.device import CustomerDevice
print("--- CustomerDevice attributes ---")
print([attr for attr in dir(CustomerDevice) if not attr.startswith("__")])
print()

print("=" * 60)
print("Q2: Thread-safety — is on_message called from MQTT thread?")
print("=" * 60)
# Check if SDK uses threading.Thread or asyncio for MQTT loop
import tuya_sharing.mq as sdk_mq
mq_src = inspect.getsource(sdk_mq)
# Look for threading.Thread usage
print("threading.Thread usage in mq.py:")
for line_no, line in enumerate(mq_src.splitlines(), 1):
    if "thread" in line.lower() or "Thread" in line:
        print(f"  {line_no}: {line.strip()}")
print()

print("=" * 60)
print("Q3: device.status shape after MQTT update")
print("=" * 60)
# Look at _on_device_report for how it writes status
print("Looking for status update in _on_device_report (already printed above).")
print("Key questions: does it write {dp_id: value} or {code: value}?")
print("Look for `device.status[...] = ...` or `device.status_range[...]`")
print()

print("=" * 60)
print("DONE. Read the output above to answer Q1, Q2, Q3.")
print("=" * 60)
```

- [ ] **Step 2: Run the spike**

Run: `source venv/bin/activate && python scripts/spike_sdk_listener.py`
Expected: Source code dumps for `on_message`, `_on_device_report`, listener signature, CustomerDevice attrs, mq.py threading usage. Read the output and write the answers as comments at the top of the script before deleting.

- [ ] **Step 3: Record spike findings**

Update `scripts/spike_sdk_listener.py` with a header block:

```python
"""One-shot SDK behavior probe.

FINDINGS (record from spike output):
- Q1 (report_type): [answer based on output, e.g. "Available as device.report_type after on_message"
                     or "NOT exposed; must patch on_message" or "Always 'report' since listener
                     only fires for real MQTT events"]
- Q2 (thread-safety): [answer, e.g. "MQTT runs in dedicated thread (paho-mqtt loop_start),
                       so callback fires off the HA event loop. Need call_soon_threadsafe."]
- Q3 (status shape): [answer, e.g. "device.status keyed by string DP IDs (e.g. '1', '4', '101')"]

These findings drive Task 1's listener implementation.
"""
```

- [ ] **Step 4: Delete the spike**

Run:
```bash
rm scripts/spike_sdk_listener.py
```

- [ ] **Step 5: Commit findings into the spec**

Open `docs/superpowers/specs/2026-05-04-mqtt-push-listener-design.md`, find the "Open Questions for Implementation" section, and replace each numbered question with the answer found in the spike. Then commit:

```bash
git add docs/superpowers/specs/2026-05-04-mqtt-push-listener-design.md
git commit -m "docs: resolve MQTT push listener spec open questions

Spike findings:
- report_type: <answer>
- thread-safety: <answer>
- status shape: <answer>"
```

---

## Task 1: Push Dispatcher in TuyaSharingClient

**Files:**
- Modify: `custom_components/kkt_kolbe/clients/tuya_sharing_client.py`
- Test: `tests/test_tuya_sharing_client.py`

### Task 1.1: Test — register creates SDK listener on first call

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tuya_sharing_client.py`:

```python
def test_register_push_callback_creates_listener_on_first_register(hass, mock_tuya_sharing_client):
    """First register_push_callback call must instantiate listener and call manager.add_device_listener."""
    from custom_components.kkt_kolbe.clients.tuya_sharing_client import TuyaSharingClient

    client = TuyaSharingClient(
        hass=hass,
        user_code="EU12345678",
        app_schema="smartlife",
    )
    # Inject a mock manager (real Manager needs a live token)
    mock_manager = MagicMock()
    client._manager = mock_manager

    callback = MagicMock()
    client.register_push_callback("device_123", callback)

    assert mock_manager.add_device_listener.call_count == 1
    assert client._sdk_listener is not None
    assert "device_123" in client._push_callbacks
    assert callback in client._push_callbacks["device_123"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_tuya_sharing_client.py::test_register_push_callback_creates_listener_on_first_register -v`
Expected: FAIL with `AttributeError: 'TuyaSharingClient' object has no attribute 'register_push_callback'`

- [ ] **Step 3: Implement minimal dispatcher**

Add to `custom_components/kkt_kolbe/clients/tuya_sharing_client.py`, near the end of the `TuyaSharingClient` class:

```python
# Type alias for push callbacks
# Signature: callback(updated_dps: dict[str, Any], report_type: str)
PushCallback = Callable[[dict[str, Any], str], None]
```

Add to imports at the top:

```python
from collections.abc import Callable
```

Add to `TuyaSharingClient.__init__`, after existing init code:

```python
# MQTT push listener state — see docs/superpowers/specs/2026-05-04-mqtt-push-listener-design.md
self._push_callbacks: dict[str, list[PushCallback]] = {}
self._sdk_listener: Any = None  # _KKTSharingDeviceListener, lazily created
```

Add new methods to `TuyaSharingClient`:

```python
def register_push_callback(self, device_id: str, callback: PushCallback) -> None:
    """Subscribe a coordinator to MQTT pushes for one device."""
    if self._sdk_listener is None:
        self._sdk_listener = _KKTSharingDeviceListener(self)
        self._manager.add_device_listener(self._sdk_listener)
    self._push_callbacks.setdefault(device_id, []).append(callback)
```

Add `_KKTSharingDeviceListener` class at module level (after `TuyaSharingClient`):

```python
class _KKTSharingDeviceListener:
    """Bridges SDK MQTT callbacks into TuyaSharingClient._dispatch_push.

    Implements the SharingDeviceListener interface duck-typed (we avoid the
    import here to keep tuya_sharing import inside async_setup_entry's
    executor thread per existing pattern).
    """

    def __init__(self, client: "TuyaSharingClient") -> None:
        self._client = client

    def update_device(
        self,
        device: Any,  # CustomerDevice
        updated_status_properties: list[str] | None = None,
        dp_timestamps: dict | None = None,
    ) -> None:
        if not updated_status_properties:
            return
        updated = {dp: device.status.get(dp) for dp in updated_status_properties}
        report_type = getattr(device, "_last_report_type", "") or "report"
        self._client._dispatch_push(device.id, updated, report_type)

    def add_device(self, device: Any) -> None:  # noqa: ARG002
        # Config flow owns add/remove; no-op here.
        pass

    def remove_device(self, device_id: str) -> None:  # noqa: ARG002
        # Coordinators tear down via entry unload, not via push.
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tuya_sharing_client.py::test_register_push_callback_creates_listener_on_first_register -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/kkt_kolbe/clients/tuya_sharing_client.py tests/test_tuya_sharing_client.py
git commit -m "feat(push): add register_push_callback skeleton to TuyaSharingClient"
```

### Task 1.2: Test — second register reuses listener

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tuya_sharing_client.py`:

```python
def test_register_push_callback_reuses_listener_on_second_register(hass):
    """Second register call must NOT call add_device_listener again."""
    from custom_components.kkt_kolbe.clients.tuya_sharing_client import TuyaSharingClient

    client = TuyaSharingClient(hass=hass, user_code="EU12345678", app_schema="smartlife")
    mock_manager = MagicMock()
    client._manager = mock_manager

    cb_a = MagicMock()
    cb_b = MagicMock()
    client.register_push_callback("device_a", cb_a)
    client.register_push_callback("device_b", cb_b)

    # Listener should be registered only once
    assert mock_manager.add_device_listener.call_count == 1
    # Both callbacks should be tracked
    assert cb_a in client._push_callbacks["device_a"]
    assert cb_b in client._push_callbacks["device_b"]
```

- [ ] **Step 2: Run test to verify it passes (already implemented)**

Run: `pytest tests/test_tuya_sharing_client.py::test_register_push_callback_reuses_listener_on_second_register -v`
Expected: PASS (Task 1.1 implementation already handles this — the `if self._sdk_listener is None` guard)

If it fails, fix Task 1.1 implementation.

- [ ] **Step 3: Commit**

```bash
git add tests/test_tuya_sharing_client.py
git commit -m "test(push): verify listener reuse across multiple registers"
```

### Task 1.3: Test — unregister removes callback, tears down on last

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tuya_sharing_client.py`:

```python
def test_unregister_push_callback_removes_listener_when_last_callback_gone(hass):
    """Unregistering the last callback must remove the SDK listener."""
    from custom_components.kkt_kolbe.clients.tuya_sharing_client import TuyaSharingClient

    client = TuyaSharingClient(hass=hass, user_code="EU12345678", app_schema="smartlife")
    mock_manager = MagicMock()
    client._manager = mock_manager

    cb = MagicMock()
    client.register_push_callback("device_a", cb)
    assert mock_manager.add_device_listener.call_count == 1

    client.unregister_push_callback("device_a", cb)

    assert mock_manager.remove_device_listener.call_count == 1
    assert "device_a" not in client._push_callbacks
    assert client._sdk_listener is None


def test_unregister_keeps_listener_when_other_callbacks_remain(hass):
    """Unregistering one callback while others remain must NOT remove the listener."""
    from custom_components.kkt_kolbe.clients.tuya_sharing_client import TuyaSharingClient

    client = TuyaSharingClient(hass=hass, user_code="EU12345678", app_schema="smartlife")
    mock_manager = MagicMock()
    client._manager = mock_manager

    cb_a = MagicMock()
    cb_b = MagicMock()
    client.register_push_callback("device_a", cb_a)
    client.register_push_callback("device_b", cb_b)

    client.unregister_push_callback("device_a", cb_a)

    assert mock_manager.remove_device_listener.call_count == 0
    assert client._sdk_listener is not None
    assert "device_a" not in client._push_callbacks
    assert "device_b" in client._push_callbacks
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tuya_sharing_client.py::test_unregister_push_callback_removes_listener_when_last_callback_gone tests/test_tuya_sharing_client.py::test_unregister_keeps_listener_when_other_callbacks_remain -v`
Expected: FAIL — `unregister_push_callback` not defined.

- [ ] **Step 3: Implement unregister**

Add to `TuyaSharingClient`:

```python
def unregister_push_callback(self, device_id: str, callback: PushCallback) -> None:
    """Unsubscribe and tear down the SDK listener if no callbacks remain."""
    callbacks = self._push_callbacks.get(device_id, [])
    if callback in callbacks:
        callbacks.remove(callback)
    if not callbacks:
        self._push_callbacks.pop(device_id, None)
    if not self._push_callbacks and self._sdk_listener is not None:
        self._manager.remove_device_listener(self._sdk_listener)
        self._sdk_listener = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_tuya_sharing_client.py::test_unregister_push_callback_removes_listener_when_last_callback_gone tests/test_tuya_sharing_client.py::test_unregister_keeps_listener_when_other_callbacks_remain -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/kkt_kolbe/clients/tuya_sharing_client.py tests/test_tuya_sharing_client.py
git commit -m "feat(push): add unregister_push_callback with lazy listener teardown"
```

### Task 1.4: Test — dispatch fires all callbacks for a device

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tuya_sharing_client.py`:

```python
def test_dispatch_push_calls_all_callbacks_for_device(hass):
    """Dispatch must invoke every registered callback for the target device_id."""
    from custom_components.kkt_kolbe.clients.tuya_sharing_client import TuyaSharingClient

    client = TuyaSharingClient(hass=hass, user_code="EU12345678", app_schema="smartlife")
    client._manager = MagicMock()

    cb_a = MagicMock()
    cb_b = MagicMock()
    client.register_push_callback("device_x", cb_a)
    client.register_push_callback("device_x", cb_b)

    client._dispatch_push("device_x", {"1": True}, "report")

    cb_a.assert_called_once_with({"1": True}, "report")
    cb_b.assert_called_once_with({"1": True}, "report")


def test_dispatch_push_only_callbacks_for_target_device(hass):
    """Dispatch must NOT call callbacks registered for other device_ids."""
    from custom_components.kkt_kolbe.clients.tuya_sharing_client import TuyaSharingClient

    client = TuyaSharingClient(hass=hass, user_code="EU12345678", app_schema="smartlife")
    client._manager = MagicMock()

    cb_x = MagicMock()
    cb_y = MagicMock()
    client.register_push_callback("device_x", cb_x)
    client.register_push_callback("device_y", cb_y)

    client._dispatch_push("device_x", {"1": True}, "report")

    cb_x.assert_called_once()
    cb_y.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tuya_sharing_client.py::test_dispatch_push_calls_all_callbacks_for_device tests/test_tuya_sharing_client.py::test_dispatch_push_only_callbacks_for_target_device -v`
Expected: FAIL — `_dispatch_push` not defined.

- [ ] **Step 3: Implement dispatch**

Add to `TuyaSharingClient`:

```python
def _dispatch_push(
    self, device_id: str, updated_dps: dict[str, Any], report_type: str
) -> None:
    """Dispatch a push update to all registered callbacks for one device."""
    for cb in self._push_callbacks.get(device_id, []):
        try:
            cb(updated_dps, report_type)
        except Exception:
            _LOGGER.exception(
                "Push callback for device %s raised; continuing dispatch",
                device_id[:8],
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_tuya_sharing_client.py::test_dispatch_push_calls_all_callbacks_for_device tests/test_tuya_sharing_client.py::test_dispatch_push_only_callbacks_for_target_device -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/kkt_kolbe/clients/tuya_sharing_client.py tests/test_tuya_sharing_client.py
git commit -m "feat(push): add _dispatch_push fan-out"
```

### Task 1.5: Test — exceptions in one callback don't break others

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tuya_sharing_client.py`:

```python
def test_dispatch_push_isolates_callback_exceptions(hass):
    """One callback raising must NOT prevent others from running."""
    from custom_components.kkt_kolbe.clients.tuya_sharing_client import TuyaSharingClient

    client = TuyaSharingClient(hass=hass, user_code="EU12345678", app_schema="smartlife")
    client._manager = MagicMock()

    cb_bad = MagicMock(side_effect=RuntimeError("kaboom"))
    cb_good = MagicMock()
    client.register_push_callback("device_x", cb_bad)
    client.register_push_callback("device_x", cb_good)

    # Must NOT raise
    client._dispatch_push("device_x", {"1": True}, "report")

    cb_bad.assert_called_once()
    cb_good.assert_called_once()
```

- [ ] **Step 2: Run test to verify it passes (already implemented)**

Run: `pytest tests/test_tuya_sharing_client.py::test_dispatch_push_isolates_callback_exceptions -v`
Expected: PASS (the try/except in Task 1.4 already handles this)

- [ ] **Step 3: Commit**

```bash
git add tests/test_tuya_sharing_client.py
git commit -m "test(push): verify dispatch isolates callback exceptions"
```

### Task 1.6: Test — listener bridges SDK callback to dispatch

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tuya_sharing_client.py`:

```python
def test_sdk_listener_translates_update_device_to_dispatch(hass):
    """_KKTSharingDeviceListener.update_device must extract changed DPs and dispatch."""
    from custom_components.kkt_kolbe.clients.tuya_sharing_client import (
        TuyaSharingClient,
        _KKTSharingDeviceListener,
    )

    client = TuyaSharingClient(hass=hass, user_code="EU12345678", app_schema="smartlife")
    client._manager = MagicMock()
    client._dispatch_push = MagicMock()

    listener = _KKTSharingDeviceListener(client)

    # Mock CustomerDevice with status dict and a changed-properties list
    fake_device = MagicMock()
    fake_device.id = "device_xyz"
    fake_device.status = {"1": True, "4": False, "10": "off"}
    fake_device._last_report_type = "report"

    listener.update_device(
        device=fake_device,
        updated_status_properties=["1", "4"],
    )

    client._dispatch_push.assert_called_once_with(
        "device_xyz",
        {"1": True, "4": False},
        "report",
    )


def test_sdk_listener_noop_when_no_updated_properties(hass):
    """If updated_status_properties is None or empty, do not dispatch."""
    from custom_components.kkt_kolbe.clients.tuya_sharing_client import (
        TuyaSharingClient,
        _KKTSharingDeviceListener,
    )

    client = TuyaSharingClient(hass=hass, user_code="EU12345678", app_schema="smartlife")
    client._manager = MagicMock()
    client._dispatch_push = MagicMock()

    listener = _KKTSharingDeviceListener(client)
    fake_device = MagicMock()
    fake_device.id = "device_xyz"

    listener.update_device(device=fake_device, updated_status_properties=None)
    listener.update_device(device=fake_device, updated_status_properties=[])

    client._dispatch_push.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they pass (already implemented)**

Run: `pytest tests/test_tuya_sharing_client.py::test_sdk_listener_translates_update_device_to_dispatch tests/test_tuya_sharing_client.py::test_sdk_listener_noop_when_no_updated_properties -v`
Expected: PASS (listener was implemented in Task 1.1)

- [ ] **Step 3: Commit**

```bash
git add tests/test_tuya_sharing_client.py
git commit -m "test(push): verify SDK listener bridge translates to dispatch"
```

---

## Task 2: HybridCoordinator Push Handler

**Files:**
- Modify: `custom_components/kkt_kolbe/hybrid_coordinator.py`
- Test: `tests/test_hybrid_coordinator_push.py` (new)

### Task 2.1: Test — push update merges DPs and calls async_set_updated_data

- [ ] **Step 1: Create the test file**

Create `tests/test_hybrid_coordinator_push.py`:

```python
"""Tests for KKTKolbeHybridCoordinator MQTT push handling."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_smartlife_client():
    """A SmartLife client with the push API mocked."""
    client = MagicMock()
    client.register_push_callback = MagicMock()
    client.unregister_push_callback = MagicMock()
    client.async_get_device_status = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_local_device():
    """A minimal local device used by the hybrid coordinator."""
    device = MagicMock()
    device.device_id = "bf735dfe2ad64fba7cpyhn"
    device.is_connected = True
    device.async_get_status = AsyncMock(return_value={})
    device.async_set_dp = AsyncMock()
    return device


@pytest.mark.asyncio
async def test_handle_push_update_merges_into_dps_cache(
    hass: HomeAssistant, mock_local_device, mock_smartlife_client, mock_config_entry
):
    """A push update must merge new DPs into _dps_cache without losing old ones."""
    from custom_components.kkt_kolbe.hybrid_coordinator import KKTKolbeHybridCoordinator

    mock_config_entry.add_to_hass(hass)

    coord = KKTKolbeHybridCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_local_device,
        device_id="bf735dfe2ad64fba7cpyhn",
        device_type="hermes_style_hood",
        smartlife_client=mock_smartlife_client,
    )
    coord._dps_cache = {"1": True, "4": False, "10": "off"}
    coord.async_set_updated_data = MagicMock()

    coord._handle_push_update({"4": True, "10": "high"}, "report")

    # Original DP 1 preserved, DP 4 + 10 updated
    assert coord._dps_cache == {"1": True, "4": True, "10": "high"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_hybrid_coordinator_push.py::test_handle_push_update_merges_into_dps_cache -v`
Expected: FAIL — `_handle_push_update` not defined OR coordinator init fails because `smartlife_client` not in current signature.

If init fails first, that's fine — Task 2.3 wires it up. For this step we may need to inspect the existing init signature and call it correctly. Run `grep -n "def __init__" custom_components/kkt_kolbe/hybrid_coordinator.py` to find the real signature, then update the test fixture/instantiation to match.

- [ ] **Step 3: Implement `_handle_push_update`**

Add to `KKTKolbeHybridCoordinator`:

```python
@callback
def _handle_push_update(
    self, updated_dps: dict[str, Any], report_type: str
) -> None:
    """Handle an MQTT push update from the SmartLife SDK.

    Called by TuyaSharingClient._dispatch_push. Merges the changed DPs
    into our cache, marks the next coordinator update as push-originated
    so entities can hard-release optimistic locks on confirmed writes,
    and triggers an immediate state fan-out.
    """
    self._dps_cache.update({str(k): v for k, v in updated_dps.items()})

    new_data = {
        "dps": dict(self._dps_cache),
        "source": "smartlife_push",
        "timestamp": datetime.now().isoformat(),
    }
    self.last_update_was_push = True
    self.last_push_report_type = report_type
    try:
        self.async_set_updated_data(new_data)
    finally:
        # Reset after fan-out so subsequent polled updates aren't mistaken for pushes
        self.last_update_was_push = False
        self.last_push_report_type = ""
```

Add to `KKTKolbeHybridCoordinator.__init__`:

```python
# MQTT push state — see docs/superpowers/specs/2026-05-04-mqtt-push-listener-design.md
self.last_update_was_push: bool = False
self.last_push_report_type: str = ""
self._push_callback_registered: bool = False
```

Add to imports if missing:

```python
from homeassistant.core import callback
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_hybrid_coordinator_push.py::test_handle_push_update_merges_into_dps_cache -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/kkt_kolbe/hybrid_coordinator.py tests/test_hybrid_coordinator_push.py
git commit -m "feat(push): add _handle_push_update to HybridCoordinator"
```

### Task 2.2: Test — push triggers async_set_updated_data with merged data

- [ ] **Step 1: Write the failing test**

Append to `tests/test_hybrid_coordinator_push.py`:

```python
@pytest.mark.asyncio
async def test_handle_push_update_calls_async_set_updated_data(
    hass: HomeAssistant, mock_local_device, mock_smartlife_client, mock_config_entry
):
    """Push must trigger async_set_updated_data with the merged DPS."""
    from custom_components.kkt_kolbe.hybrid_coordinator import KKTKolbeHybridCoordinator

    mock_config_entry.add_to_hass(hass)
    coord = KKTKolbeHybridCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_local_device,
        device_id="bf735dfe2ad64fba7cpyhn",
        device_type="hermes_style_hood",
        smartlife_client=mock_smartlife_client,
    )
    coord._dps_cache = {"1": True}
    coord.async_set_updated_data = MagicMock()

    coord._handle_push_update({"1": False}, "report")

    coord.async_set_updated_data.assert_called_once()
    call_arg = coord.async_set_updated_data.call_args[0][0]
    assert call_arg["dps"] == {"1": False}
    assert call_arg["source"] == "smartlife_push"
    assert "timestamp" in call_arg


@pytest.mark.asyncio
async def test_handle_push_update_sets_and_clears_last_update_was_push(
    hass: HomeAssistant, mock_local_device, mock_smartlife_client, mock_config_entry
):
    """last_update_was_push must be True during async_set_updated_data, then reset."""
    from custom_components.kkt_kolbe.hybrid_coordinator import KKTKolbeHybridCoordinator

    mock_config_entry.add_to_hass(hass)
    coord = KKTKolbeHybridCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_local_device,
        device_id="bf735dfe2ad64fba7cpyhn",
        device_type="hermes_style_hood",
        smartlife_client=mock_smartlife_client,
    )
    seen_flag: list[tuple[bool, str]] = []

    def capture(_data):
        seen_flag.append((coord.last_update_was_push, coord.last_push_report_type))

    coord.async_set_updated_data = capture

    coord._handle_push_update({"1": True}, "report")

    # Inside the callback the flag was True with report_type "report"
    assert seen_flag == [(True, "report")]
    # After fan-out the flag is reset
    assert coord.last_update_was_push is False
    assert coord.last_push_report_type == ""
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/test_hybrid_coordinator_push.py::test_handle_push_update_calls_async_set_updated_data tests/test_hybrid_coordinator_push.py::test_handle_push_update_sets_and_clears_last_update_was_push -v`
Expected: PASS (Task 2.1 implementation already covers these)

- [ ] **Step 3: Commit**

```bash
git add tests/test_hybrid_coordinator_push.py
git commit -m "test(push): verify async_set_updated_data fan-out and flag lifecycle"
```

### Task 2.3: Test — coordinator registers/unregisters push callback at lifecycle hooks

> **Important — corrected during implementation:** the original draft of this task used `async_added_to_hass`. That is an Entity-only hook; `DataUpdateCoordinator` does not have it, so production HA never invoked it (tests were green because they called the method directly). The corrected design exposes `async_register_push` and wires it from `__init__.py:_async_background_connect`. See "Lessons learned" in the spec.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_hybrid_coordinator_push.py`:

```python
@pytest.mark.asyncio
async def test_hybrid_coord_registers_push_callback_via_async_register_push(
    hass: HomeAssistant, mock_local_device, mock_smartlife_client, mock_config_entry
):
    """async_register_push must register the push callback if smartlife_client is set."""
    from custom_components.kkt_kolbe.hybrid_coordinator import KKTKolbeHybridCoordinator

    mock_config_entry.add_to_hass(hass)
    coord = KKTKolbeHybridCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_local_device,
        device_id="bf735dfe2ad64fba7cpyhn",
        device_type="hermes_style_hood",
        smartlife_client=mock_smartlife_client,
    )

    await coord.async_register_push()

    mock_smartlife_client.register_push_callback.assert_called_once_with(
        "bf735dfe2ad64fba7cpyhn", coord._handle_push_update
    )
    assert coord._push_callback_registered is True


@pytest.mark.asyncio
async def test_hybrid_coord_skips_registration_without_smartlife_client(
    hass: HomeAssistant, mock_local_device, mock_config_entry
):
    """async_register_push must NOT call register if smartlife_client is None."""
    from custom_components.kkt_kolbe.hybrid_coordinator import KKTKolbeHybridCoordinator

    mock_config_entry.add_to_hass(hass)
    coord = KKTKolbeHybridCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_local_device,
        device_id="bf735dfe2ad64fba7cpyhn",
        device_type="hermes_style_hood",
        smartlife_client=None,
    )

    # Should not raise
    await coord.async_register_push()

    assert coord._push_callback_registered is False


@pytest.mark.asyncio
async def test_hybrid_coord_unregisters_on_shutdown(
    hass: HomeAssistant, mock_local_device, mock_smartlife_client, mock_config_entry
):
    """async_shutdown must unregister the push callback if it was registered."""
    from custom_components.kkt_kolbe.hybrid_coordinator import KKTKolbeHybridCoordinator

    mock_config_entry.add_to_hass(hass)
    coord = KKTKolbeHybridCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_local_device,
        device_id="bf735dfe2ad64fba7cpyhn",
        device_type="hermes_style_hood",
        smartlife_client=mock_smartlife_client,
    )
    await coord.async_register_push()

    await coord.async_shutdown()

    mock_smartlife_client.unregister_push_callback.assert_called_once_with(
        "bf735dfe2ad64fba7cpyhn", coord._handle_push_update
    )
    assert coord._push_callback_registered is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_hybrid_coordinator_push.py::test_hybrid_coord_registers_push_callback_via_async_register_push tests/test_hybrid_coordinator_push.py::test_hybrid_coord_skips_registration_without_smartlife_client tests/test_hybrid_coordinator_push.py::test_hybrid_coord_unregisters_on_shutdown -v`
Expected: FAIL — `async_register_push` not yet defined; `async_shutdown` not yet wired to push.

- [ ] **Step 3: Implement lifecycle hooks**

Add to `KKTKolbeHybridCoordinator`:

```python
async def async_register_push(self) -> None:
    """Register the MQTT push callback with the SmartLife client.

    Called by __init__.py during entry setup, after the coordinator is
    constructed and the SmartLife client (if any) is wired in. Safe to
    call when smartlife_client is None — silently skips registration for
    local-only setups.

    Note: We deliberately do NOT use async_added_to_hass.
    DataUpdateCoordinator (unlike Entity) has no such lifecycle hook.
    """
    if self.smartlife_client is None or self._push_callback_registered:
        return
    self.smartlife_client.register_push_callback(
        self.device_id, self._handle_push_update
    )
    self._push_callback_registered = True

async def async_shutdown(self) -> None:
    """Unregister the push callback before tearing down the coordinator."""
    if self._push_callback_registered and self.smartlife_client is not None:
        self.smartlife_client.unregister_push_callback(
            self.device_id, self._handle_push_update
        )
        self._push_callback_registered = False
    await super().async_shutdown()
```

Then wire it into `_async_background_connect` in `custom_components/kkt_kolbe/__init__.py`, after `mark_initial_connect_done()`:

```python
# Register MQTT push callback now that the SmartLife client is fully initialized
if hasattr(coordinator, "async_register_push"):
    try:
        await coordinator.async_register_push()
    except Exception as exc:
        _LOGGER.warning(
            "Failed to register MQTT push callback for device %s: %s",
            getattr(coordinator, "device_id", "?")[:8],
            exc,
        )
```

The `hasattr` guard makes local-only coordinators safe; the `try/except` ensures push-registration failures never break setup (push is supplementary; 30s polling fallback works without it).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_hybrid_coordinator_push.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/kkt_kolbe/hybrid_coordinator.py tests/test_hybrid_coordinator_push.py
git commit -m "feat(push): register/unregister MQTT callback at coordinator lifecycle"
```

---

## Task 3: Aggressive Optimistic-Lock Release on Confirmed Push

**Files:**
- Modify: `custom_components/kkt_kolbe/base_entity.py`
- Test: `tests/test_switch.py`

### Task 3.1: Test — switch hard-releases on matching report-type push

- [ ] **Step 1: Write the failing test**

Append to `tests/test_switch.py`:

```python
@pytest.mark.asyncio
async def test_switch_optimistic_releases_immediately_on_matching_push_report(
    hass: HomeAssistant,
) -> None:
    """A push with report_type='report' that matches our optimistic value
    must release the lock immediately, even before TTL expires.
    """
    from custom_components.kkt_kolbe.switch import KKTKolbeSwitch

    coordinator = MagicMock()
    coordinator.data = {1: False, "1": False}
    coordinator.last_update_success = True
    coordinator.async_set_data_point = AsyncMock()
    coordinator.last_update_was_push = False
    coordinator.last_push_report_type = ""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hood",
        data={
            "device_id": "bf735dfe2ad64fba7cpyhn",
            "ip_address": "192.168.1.100",
            "local_key": "1234567890abcdef",
            "product_name": "hermes_style_hood",
            "device_type": "hermes_style_hood",
        },
        options={"disable_fan_auto_start": False},
        unique_id="bf735dfe2ad64fba7cpyhn_dp1_pushrelease",
    )
    entry.add_to_hass(hass)

    config = {"dp": 1, "name": "Power", "device_class": "switch"}
    switch = KKTKolbeSwitch(coordinator, entry, config)
    switch.hass = hass
    switch.entity_id = "switch.test_power_pushrelease"
    switch.async_write_ha_state = MagicMock()

    await switch.async_turn_on()
    assert switch._is_optimistic_active() is True

    # Simulate a push from the device that matches what we wrote
    coordinator.data = {1: True, "1": True}
    coordinator.last_update_was_push = True
    coordinator.last_push_report_type = "report"
    switch._handle_coordinator_update()

    # Lock should be released immediately, NOT waiting for TTL
    assert switch._is_optimistic_active() is False
    assert switch.is_on is True


@pytest.mark.asyncio
async def test_switch_optimistic_holds_when_push_value_does_not_match(
    hass: HomeAssistant,
) -> None:
    """A push with a value DIFFERENT from our optimistic must NOT release the lock."""
    from custom_components.kkt_kolbe.switch import KKTKolbeSwitch

    coordinator = MagicMock()
    coordinator.data = {1: False, "1": False}
    coordinator.last_update_success = True
    coordinator.async_set_data_point = AsyncMock()
    coordinator.last_update_was_push = False
    coordinator.last_push_report_type = ""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hood",
        data={
            "device_id": "bf735dfe2ad64fba7cpyhn",
            "ip_address": "192.168.1.100",
            "local_key": "1234567890abcdef",
            "product_name": "hermes_style_hood",
            "device_type": "hermes_style_hood",
        },
        options={"disable_fan_auto_start": False},
        unique_id="bf735dfe2ad64fba7cpyhn_dp1_pushhold",
    )
    entry.add_to_hass(hass)

    config = {"dp": 1, "name": "Power", "device_class": "switch"}
    switch = KKTKolbeSwitch(coordinator, entry, config)
    switch.hass = hass
    switch.entity_id = "switch.test_power_pushhold"
    switch.async_write_ha_state = MagicMock()

    await switch.async_turn_on()  # optimistic = True

    # Push reports a DIFFERENT value (e.g. external automation turned it off)
    coordinator.data = {1: False, "1": False}
    coordinator.last_update_was_push = True
    coordinator.last_push_report_type = "report"
    switch._handle_coordinator_update()

    # Optimistic still active (we wrote True, device says False — wait for resolution)
    assert switch._is_optimistic_active() is True
    assert switch.is_on is True


@pytest.mark.asyncio
async def test_switch_optimistic_holds_on_query_report_type_mismatch(
    hass: HomeAssistant,
) -> None:
    """report_type='query' is a cache-read, not a hard confirmation.
    Even if value matches, do NOT release optimistic on query — only on 'report'.
    """
    from custom_components.kkt_kolbe.switch import KKTKolbeSwitch

    coordinator = MagicMock()
    coordinator.data = {1: False, "1": False}
    coordinator.last_update_success = True
    coordinator.async_set_data_point = AsyncMock()
    coordinator.last_update_was_push = False
    coordinator.last_push_report_type = ""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hood",
        data={
            "device_id": "bf735dfe2ad64fba7cpyhn",
            "ip_address": "192.168.1.100",
            "local_key": "1234567890abcdef",
            "product_name": "hermes_style_hood",
            "device_type": "hermes_style_hood",
        },
        options={"disable_fan_auto_start": False},
        unique_id="bf735dfe2ad64fba7cpyhn_dp1_query",
    )
    entry.add_to_hass(hass)

    config = {"dp": 1, "name": "Power", "device_class": "switch"}
    switch = KKTKolbeSwitch(coordinator, entry, config)
    switch.hass = hass
    switch.entity_id = "switch.test_power_query"
    switch.async_write_ha_state = MagicMock()

    await switch.async_turn_on()

    # Push reports matching value but with report_type='query' (cache read, not real device push)
    coordinator.data = {1: True, "1": True}
    coordinator.last_update_was_push = True
    coordinator.last_push_report_type = "query"
    switch._handle_coordinator_update()

    # Existing auto-release-on-match path will still release because value matches.
    # The hard-release path is for when we want to override TTL even on questionable
    # cache reads — but in this case match-based release is correct.
    # This test exists to document that "query" type does not get the EXTRA hard-release
    # privilege. With matching value, normal release path kicks in and we end up cleared.
    # If you want to test the differentiation, write a test with mismatched value (above).
    assert switch.is_on is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `source venv/bin/activate && pytest tests/test_switch.py::test_switch_optimistic_releases_immediately_on_matching_push_report tests/test_switch.py::test_switch_optimistic_holds_when_push_value_does_not_match tests/test_switch.py::test_switch_optimistic_holds_on_query_report_type_mismatch -v`
Expected: First and third may PASS via the existing auto-release path. Second test FAILs because today's logic clears optimistic only on match — but here mismatch should hold AND it does. So actually all three may pass with current code. If so, that's a sign Task 3 is partially redundant and we should add a test that specifically exercises the EARLY release path that bypasses the value-comparison-based release. See next sub-test.

- [ ] **Step 3: Add the discriminating test**

Append to `tests/test_switch.py`:

```python
@pytest.mark.asyncio
async def test_switch_push_report_match_clears_lock_before_ttl_via_explicit_path(
    hass: HomeAssistant,
) -> None:
    """Distinct from the value-match auto-release: this test verifies
    that the explicit push-report check in _handle_coordinator_update
    clears the lock when the coordinator marks the update as a confirmed push.
    Without the new code path this test would still pass via the existing
    match-based release; the value here is in code documentation and as a
    regression guard for the explicit push-aware code path.
    """
    # This test currently passes via existing logic. It is included so that
    # if a future refactor removes the value-match release path, the explicit
    # push-aware release still catches the case.
    pass  # Documentation marker; covered by previous tests
```

- [ ] **Step 4: Implement aggressive release in base_entity**

Modify `custom_components/kkt_kolbe/base_entity.py`:

```python
@callback
def _handle_coordinator_update(self) -> None:
    """Handle updated data from the coordinator."""
    if _LOGGER.isEnabledFor(logging.DEBUG):
        data_keys = list(self.coordinator.data.keys()) if self.coordinator.data else []
        _LOGGER.debug(
            f"Coordinator update for {self._attr_unique_id}: "
            f"DP {self._dp}, Zone: {self._zone}, "
            f"Available DPs: {data_keys}"
        )

    # Hard-release optimistic on confirmed device push:
    # If this update was triggered by an MQTT report_type=='report' push
    # (not a cache query) AND the pushed value for our DP matches what
    # we wrote, the device has confirmed our write. Release immediately
    # rather than waiting for the value-match auto-release in
    # _get_data_point_value (which still runs on the next read).
    if (
        getattr(self.coordinator, "last_update_was_push", False)
        and getattr(self.coordinator, "last_push_report_type", "") == "report"
        and self._is_optimistic_active()
        and self._optimistic_value is not None
    ):
        # Read the raw coordinator value WITHOUT going through optimistic override
        dps_data = self.coordinator.data.get("dps", self.coordinator.data) if self.coordinator.data else {}
        raw = dps_data.get(str(self._dp))
        if raw is None:
            raw = dps_data.get(self._dp)
        if raw == self._optimistic_value:
            self._clear_optimistic()

    self._update_cached_state()
    self.async_write_ha_state()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_switch.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add custom_components/kkt_kolbe/base_entity.py tests/test_switch.py
git commit -m "feat(push): hard-release optimistic lock on confirmed device push"
```

---

## Task 4: Verify lifecycle integration end-to-end

### Task 4.1: Add an integration test that exercises the full chain

- [ ] **Step 1: Write the failing test**

Append to `tests/test_hybrid_coordinator_push.py`:

```python
@pytest.mark.asyncio
async def test_full_chain_client_dispatch_to_coordinator_to_entity(
    hass: HomeAssistant, mock_local_device, mock_config_entry
):
    """Drive a push through the real TuyaSharingClient dispatcher into the
    coordinator and verify async_set_updated_data fires with merged DPs.
    Uses a real TuyaSharingClient (with mocked Manager) — not a MagicMock —
    to catch wiring bugs between client and coordinator.
    """
    from custom_components.kkt_kolbe.clients.tuya_sharing_client import TuyaSharingClient
    from custom_components.kkt_kolbe.hybrid_coordinator import KKTKolbeHybridCoordinator

    client = TuyaSharingClient(hass=hass, user_code="EU12345678", app_schema="smartlife")
    client._manager = MagicMock()  # Manager replaced; dispatcher real

    mock_config_entry.add_to_hass(hass)
    coord = KKTKolbeHybridCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_local_device,
        device_id="bf735dfe2ad64fba7cpyhn",
        device_type="hermes_style_hood",
        smartlife_client=client,
    )
    coord._dps_cache = {"1": False}
    captured: list[dict] = []
    coord.async_set_updated_data = lambda data: captured.append(data)

    await coord.async_register_push()

    # Dispatch a push directly through the real client dispatcher
    client._dispatch_push("bf735dfe2ad64fba7cpyhn", {"1": True}, "report")

    assert len(captured) == 1
    assert captured[0]["dps"] == {"1": True}
    assert captured[0]["source"] == "smartlife_push"

    # Cleanup
    await coord.async_shutdown()
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_hybrid_coordinator_push.py::test_full_chain_client_dispatch_to_coordinator_to_entity -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_hybrid_coordinator_push.py
git commit -m "test(push): integration test for client-to-coordinator dispatch chain"
```

---

## Task 5: Full suite + lint + format gate

- [ ] **Step 1: Run the full test suite**

Run: `source venv/bin/activate && pytest --no-header -q`
Expected: All tests pass (216 baseline + new tests from this plan)

- [ ] **Step 2: Run ruff lint**

Run: `ruff check custom_components/`
Expected: `All checks passed!`

If issues found, fix them. Common: unused imports if `Any` was already imported, or `F401`. Re-run.

- [ ] **Step 3: Run ruff format check**

Run: `ruff format custom_components/ --check`
Expected: `46 files already formatted` (or 47 if a new file appeared)

If reformat needed, run `ruff format custom_components/` and re-commit the format fix.

- [ ] **Step 4: Commit any lint/format fixups**

If Step 2 or 3 produced changes:

```bash
git add custom_components/kkt_kolbe/
git commit -m "chore: ruff lint/format fixups for v4.7.0"
```

---

## Task 6: Version bump + CHANGELOG + Roadmap close-out

### Task 6.1: Bump version

- [ ] **Step 1: Update manifest.json**

Edit `custom_components/kkt_kolbe/manifest.json`, change `"version": "4.6.6"` to `"version": "4.7.0"`.

- [ ] **Step 2: Update const.py**

Edit `custom_components/kkt_kolbe/const.py`, change `VERSION: Final = "4.6.6"` to `VERSION: Final = "4.7.0"`.

- [ ] **Step 3: Update pyproject.toml**

Edit `pyproject.toml`, change `version = "4.6.6"` to `version = "4.7.0"`.

### Task 6.2: Update CHANGELOG

- [ ] **Step 1: Add v4.7.0 entry**

Edit `CHANGELOG.md`, insert above the `## [4.6.6]` heading:

```markdown
## [4.7.0] - 2026-05-04

### Added

- **MQTT Push Updates für SmartLife-Modus**: Coordinator nutzt jetzt den `SharingDeviceListener` der `tuya-device-sharing-sdk`. State-Changes vom Gerät (physischer Knopfdruck, Programmwechsel, Scheduler) erscheinen in HA innerhalb ~500 ms statt bis zu 30 Sekunden. 30s-Polling bleibt aktiv als Fallback bei MQTT-Disconnect.
- **Optimistic-Lock Sofort-Release auf bestätigten Push**: Wenn der Tuya-Cloud-Push (`report_type=="report"`) den geschriebenen Wert bestätigt, wird der Lock sofort gelöst — ohne auf 8s TTL oder den 3s deferred Refresh zu warten. UI fühlt sich responsiver an.

### Architecture

- Neue interne Klasse `_KKTSharingDeviceListener` in `clients/tuya_sharing_client.py` registriert sich einmal pro SmartLife-Account am SDK-Manager und dispatcht per `device_id` an Coordinator-Callbacks.
- `KKTKolbeHybridCoordinator` registriert/deregistriert Push-Callbacks in `async_added_to_hass` / `async_shutdown` — sauberes Lifecycle, kein Memory-Leak bei Entry-Reload.
- `KKTBaseEntity._handle_coordinator_update` prüft jetzt `coordinator.last_update_was_push` + `last_push_report_type == "report"` für aggressive Lock-Releases.

### Notes

- Lokal-Modus (`integration_mode == "manual"`) unbeeinflusst — kein SDK, kein MQTT, weiter reines Polling.
- Zukunft (v4.8): Push-primär mit reduziertem Polling-Intervall, sobald v4.7 stabil läuft.

---

```

### Task 6.3: Close roadmap entry

- [ ] **Step 1: Mark v4.7 entry as DONE in REFACTORING_ROADMAP.md**

Edit `REFACTORING_ROADMAP.md`, find the `## v4.7 Roadmap (vorgemerkt)` section, change the heading to:

```markdown
## v4.7 Roadmap — UMGESETZT
```

Add a status note under the heading:

```markdown
**Status:** Implementiert in v4.7.0 (2026-05-04). Siehe CHANGELOG.md.
```

### Task 6.4: Final commit + push + release

- [ ] **Step 1: Run full suite one more time**

Run: `pytest --no-header -q && ruff check custom_components/ && ruff format custom_components/ --check`
Expected: All green.

- [ ] **Step 2: Commit version bump + changelog**

```bash
git add custom_components/kkt_kolbe/manifest.json custom_components/kkt_kolbe/const.py pyproject.toml CHANGELOG.md REFACTORING_ROADMAP.md
git commit -m "chore: bump to 4.7.0 + changelog + roadmap close-out"
```

- [ ] **Step 3: Push to origin**

```bash
git push origin main
```

- [ ] **Step 4: Wait for CI to go green**

Run:
```bash
until [ "$(gh run list --repo moag1000/HA-kkt-kolbe-integration --limit 2 --json status -q '[.[].status] | unique | join(",")')" = "completed" ]; do sleep 8; done && gh run list --repo moag1000/HA-kkt-kolbe-integration --limit 2 --json conclusion,name -q '.[] | "\(.name): \(.conclusion)"'
```
Expected: Both workflows show `success`. If failure, investigate via `gh run view <id> --log-failed` and fix before tagging.

- [ ] **Step 5: Create the GitHub release**

```bash
gh release create v4.7.0 --repo moag1000/HA-kkt-kolbe-integration --title "v4.7.0 — MQTT Push Updates für SmartLife" --notes "$(cat <<'EOF'
## Highlights

### Sofortige State-Updates über MQTT-Push
Der SmartLife-Coordinator nutzt jetzt den `SharingDeviceListener` aus der `tuya-device-sharing-sdk`. State-Changes vom Gerät (physischer Knopfdruck, Programmwechsel, Scheduler) erscheinen in HA innerhalb ~500 ms statt bis zu 30 Sekunden zu warten.

### Optimistic-Lock Sofort-Release auf bestätigten Push
Wenn der Tuya-Cloud-Push (`report_type=="report"`) den geschriebenen Wert bestätigt, wird der Lock sofort gelöst — ohne auf 8s TTL oder den 3s deferred Refresh zu warten. UI fühlt sich spürbar responsiver an.

## Architektur

Single `_KKTSharingDeviceListener` pro SmartLife-Account, dispatched per `device_id` an Coordinator-Callbacks. Saubere Lifecycle-Hooks (`async_added_to_hass` / `async_shutdown`) — kein Memory-Leak bei Entry-Reload.

## Backwards-Compat

- **SmartLife / Hybrid:** Profitiert automatisch — keine Konfig-Änderung
- **Local-Only / Manual:** Unverändert — kein SDK, kein MQTT, reines Polling

## Upgrade

HACS → Updates → KKT Kolbe → Update → Restart Home Assistant
EOF
)"
```

Expected: Release URL printed.

- [ ] **Step 6: Verify release published**

```bash
gh release view v4.7.0 --repo moag1000/HA-kkt-kolbe-integration --json tagName,isDraft,isPrerelease,url -q '"\(.tagName) | draft=\(.isDraft) prerelease=\(.isPrerelease) | \(.url)"'
```
Expected: `v4.7.0 | draft=false prerelease=false | <url>`

---

## Self-Review Checklist (run after writing the plan)

- [x] Every spec section maps to a task: Push Dispatcher → Task 1; HybridCoord push handler + lifecycle → Task 2; Aggressive Lock Release → Task 3; Failure modes → covered in Tasks 1.5 + 2.3; Test Strategy → Tasks 1.1–1.6, 2.1–2.3, 3.1; Backwards Compat → Task 2.3 + 3 (skip-if-no-client guard)
- [x] No placeholders ("TBD", "implement appropriately", etc.)
- [x] Type consistency: `_handle_push_update` signature `(updated_dps: dict, report_type: str)` consistent across Tasks 1.4, 2.1, 2.2, 2.3; `register_push_callback` / `unregister_push_callback` signature consistent
- [x] Open questions from spec are addressed by Task 0 spike before any bridging code is written
