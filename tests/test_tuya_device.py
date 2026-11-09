"""Test KKTKolbeTuyaDevice protocol detection."""

from __future__ import annotations

import pytest

from custom_components.kkt_kolbe.tuya_device import KKTKolbeTuyaDevice


@pytest.mark.asyncio
async def test_auto_detect_protocol_includes_3_5():
    """Auto-detection must try Tuya protocol 3.5.

    Regression: Issue #8, dernick79 reported Error 914 on all detected
    versions. tinytuya scan of his Ploom hood revealed it speaks 3.5,
    but our auto-detection loop only tested [3.3, 3.4, 3.1, 3.2].
    Devices on 3.5 firmware (newer Tuya devices since ~2024) cannot
    connect locally without 3.5 in the test list.
    """
    import inspect

    source = inspect.getsource(KKTKolbeTuyaDevice._perform_connection)
    # The version test list must include 3.5 alongside the older versions.
    assert "3.5" in source, (
        "Protocol 3.5 missing from auto-detect list — devices on 3.5 firmware "
        "(e.g. Ploom hoods, some 2024+ models) cannot connect"
    )


# --- Local connection keep-alive -------------------------------------------

import asyncio  # noqa: E402
import socket as socket_module  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402

from custom_components.kkt_kolbe import tuya_device as tuya_device_module  # noqa: E402
from custom_components.kkt_kolbe.exceptions import KKTConnectionError  # noqa: E402


def _connected_device() -> tuple[KKTKolbeTuyaDevice, MagicMock]:
    device = KKTKolbeTuyaDevice("bf735dfe2ad64fba7cpyhn", "192.168.1.100", "1234567890abcdef", version="3.3")
    raw = MagicMock()
    raw.socket = None
    raw.status.return_value = {"dps": {"1": True}}
    device._device = raw
    device._connected = True
    return device, raw


@pytest.mark.asyncio
async def test_drop_device_closes_socket() -> None:
    """Dropping a connection must close tinytuya's socket (no half-open leftovers)."""
    device, raw = _connected_device()
    device._drop_device()
    raw.close.assert_called_once()
    assert device.is_connected is False


@pytest.mark.asyncio
async def test_status_failure_closes_socket() -> None:
    """An exception during status closes the socket before reconnecting."""
    device, raw = _connected_device()
    raw.status.side_effect = OSError("reset by peer")
    with pytest.raises(KKTConnectionError):
        await device.async_get_status()
    raw.close.assert_called_once()
    assert device.is_connected is False


@pytest.mark.asyncio
async def test_device_calls_are_serialized() -> None:
    """Status and writes never run on the socket at the same time."""
    device, raw = _connected_device()
    active = 0
    max_active = 0
    lock = threading.Lock()

    def slow(*_args):
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return {"dps": {"1": True}}

    raw.status.side_effect = slow
    raw.set_value.side_effect = slow
    await asyncio.gather(device.async_get_status(), device.async_set_dp(1, True), device.async_get_status())
    assert max_active == 1


@pytest.mark.asyncio
async def test_keepalive_configured_on_tinytuya_socket() -> None:
    """TCP keep-alive is set on ``device.socket`` (tinytuya's attribute), once per socket."""
    device, raw = _connected_device()
    sock = MagicMock()
    raw.socket = sock
    await device.async_get_status()
    await device.async_get_status()
    sock.setsockopt.assert_any_call(socket_module.SOL_SOCKET, socket_module.SO_KEEPALIVE, 1)
    keepalive_calls = [c for c in sock.setsockopt.call_args_list if c.args[1] == socket_module.SO_KEEPALIVE]
    assert len(keepalive_calls) == 1

    raw.socket = MagicMock()  # tinytuya reconnected -> new socket gets configured too
    await device.async_get_status()
    raw.socket.setsockopt.assert_any_call(socket_module.SOL_SOCKET, socket_module.SO_KEEPALIVE, 1)


@pytest.mark.asyncio
async def test_heartbeat_sent_when_idle_and_stopped_on_disconnect(monkeypatch) -> None:
    """An idle connection gets HEART_BEATs; disconnect stops the loop."""
    monkeypatch.setattr(tuya_device_module, "HEARTBEAT_INTERVAL", 0.01)
    device, raw = _connected_device()
    device._last_io = 0.0
    device._start_heartbeat()
    for _ in range(50):
        if raw.heartbeat.called:
            break
        await asyncio.sleep(0.01)
    raw.heartbeat.assert_called_with(True)

    await device.async_disconnect()
    assert device._heartbeat_task is None
    raw.close.assert_called()


@pytest.mark.asyncio
async def test_failed_heartbeat_drops_connection(monkeypatch) -> None:
    """A failing heartbeat marks the device disconnected so the next poll reconnects."""
    monkeypatch.setattr(tuya_device_module, "HEARTBEAT_INTERVAL", 0.01)
    device, raw = _connected_device()
    raw.heartbeat.side_effect = OSError("broken pipe")
    device._last_io = 0.0
    device._start_heartbeat()
    for _ in range(50):
        if not device.is_connected:
            break
        await asyncio.sleep(0.01)
    assert device.is_connected is False
    raw.close.assert_called_once()
    device._stop_heartbeat()
