"""Tests for the HybridCoordinator MQTT push handler + lifecycle (Task 2)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_smartlife_client() -> MagicMock:
    """Build a mock TuyaSharingClient with push (un)register methods."""
    client = MagicMock()
    client.register_push_callback = MagicMock()
    client.unregister_push_callback = MagicMock()
    client.async_get_device_status = AsyncMock(return_value=[])
    client.async_send_commands = AsyncMock(return_value=True)
    client.async_send_dp_commands = AsyncMock(return_value=True)
    return client


def _make_coord(
    hass: HomeAssistant,
    mock_config_entry,
    smartlife_client=None,
):
    """Construct a HybridCoordinator with optional smartlife client."""
    from custom_components.kkt_kolbe.hybrid_coordinator import KKTKolbeHybridCoordinator

    mock_config_entry.add_to_hass(hass)
    return KKTKolbeHybridCoordinator(
        hass=hass,
        device_id="bf735dfe2ad64fba7cpyhn",
        smartlife_client=smartlife_client,
        update_interval=timedelta(seconds=30),
        entry=mock_config_entry,
    )


@pytest.mark.asyncio
async def test_handle_push_update_merges_into_dps_cache(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Push update merges incoming DPs into the existing _dps_cache."""
    coord = _make_coord(hass, mock_config_entry)
    coord._dps_cache = {"1": True, "4": False, "10": "off"}

    coord._handle_push_update({"4": True, "10": "high"}, "report")

    assert coord._dps_cache == {"1": True, "4": True, "10": "high"}


@pytest.mark.asyncio
async def test_handle_push_update_calls_async_set_updated_data(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Push update fans out via async_set_updated_data with proper payload."""
    coord = _make_coord(hass, mock_config_entry)
    coord._dps_cache = {"1": True}

    captured: dict = {}

    def fake_set_updated_data(data):
        captured.update(data)

    coord.async_set_updated_data = fake_set_updated_data  # type: ignore[assignment]

    coord._handle_push_update({"4": True}, "report")

    assert "dps" in captured
    assert captured["source"] == "smartlife_push"
    assert "timestamp" in captured
    assert captured["dps"] == {"1": True, "4": True}


@pytest.mark.asyncio
async def test_handle_push_update_sets_and_clears_last_update_was_push(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """last_update_was_push is True during fan-out, False after."""
    coord = _make_coord(hass, mock_config_entry)
    coord._dps_cache = {"1": True}

    flag_during: dict = {}

    def fake_set_updated_data(_data):
        # Capture flag value seen INSIDE the fan-out invocation
        flag_during["flag"] = coord.last_update_was_push
        flag_during["report_type"] = coord.last_push_report_type

    coord.async_set_updated_data = fake_set_updated_data  # type: ignore[assignment]

    coord._handle_push_update({"4": True}, "report")

    # Flag was True during fan-out
    assert flag_during["flag"] is True
    assert flag_during["report_type"] == "report"
    # Flag is cleared after
    assert coord.last_update_was_push is False
    assert coord.last_push_report_type == ""


@pytest.mark.asyncio
async def test_hybrid_coord_registers_push_callback_via_async_register_push(
    hass: HomeAssistant,
    mock_config_entry,
    mock_smartlife_client: MagicMock,
) -> None:
    """async_register_push registers our handler on the smartlife client."""
    coord = _make_coord(hass, mock_config_entry, smartlife_client=mock_smartlife_client)

    await coord.async_register_push()

    mock_smartlife_client.register_push_callback.assert_called_once_with(coord.device_id, coord._handle_push_update)
    assert coord._push_callback_registered is True


@pytest.mark.asyncio
async def test_hybrid_coord_skips_registration_without_smartlife_client(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """async_register_push is a no-op when smartlife_client is None."""
    coord = _make_coord(hass, mock_config_entry, smartlife_client=None)

    # Must not raise
    await coord.async_register_push()

    assert coord._push_callback_registered is False


@pytest.mark.asyncio
async def test_hybrid_coord_unregisters_on_shutdown(
    hass: HomeAssistant,
    mock_config_entry,
    mock_smartlife_client: MagicMock,
) -> None:
    """async_shutdown unregisters the push callback and clears the flag."""
    coord = _make_coord(hass, mock_config_entry, smartlife_client=mock_smartlife_client)

    await coord.async_register_push()
    assert coord._push_callback_registered is True

    await coord.async_shutdown()

    mock_smartlife_client.unregister_push_callback.assert_called_once_with(coord.device_id, coord._handle_push_update)
    assert coord._push_callback_registered is False


@pytest.mark.asyncio
async def test_setup_invokes_async_register_push(
    hass: HomeAssistant,
    mock_config_entry,
    mock_smartlife_client: MagicMock,
) -> None:
    """Production wiring test: _async_background_connect must call async_register_push.

    This is the regression test for the v4.7 critical bug where the original
    Task 2 used async_added_to_hass — a hook DataUpdateCoordinator does not
    have, so the registration never fired in production despite tests passing.

    Drives the actual production code path (_async_background_connect) with
    a coordinator instance and verifies async_register_push is invoked.
    """
    from unittest.mock import patch

    from custom_components.kkt_kolbe import _async_background_connect

    coord = _make_coord(hass, mock_config_entry, smartlife_client=mock_smartlife_client)

    with patch.object(
        coord,
        "async_register_push",
        new=AsyncMock(wraps=coord.async_register_push),
    ) as mock_register:
        await _async_background_connect(
            hass=hass,
            entry=mock_config_entry,
            coordinator=coord,
            device=None,
            api_client=None,
        )

        mock_register.assert_awaited_once()
    # And it actually fired through to the smartlife client
    mock_smartlife_client.register_push_callback.assert_called_once_with(coord.device_id, coord._handle_push_update)


@pytest.mark.asyncio
async def test_full_chain_client_dispatch_to_coordinator(
    hass: HomeAssistant,
    mock_tuya_device: MagicMock,
    mock_config_entry,
) -> None:
    """End-to-end: real TuyaSharingClient.dispatch -> real coordinator handler.

    Drive a push through the real dispatcher (with mocked Manager) into a
    real coordinator and verify async_set_updated_data fires with merged
    DPs. Catches wiring bugs that purely-mocked unit tests cannot.
    """
    from custom_components.kkt_kolbe.clients.tuya_sharing_client import TuyaSharingClient
    from custom_components.kkt_kolbe.hybrid_coordinator import KKTKolbeHybridCoordinator

    # Real client with mocked Manager (Manager needs a live token to instantiate)
    client = TuyaSharingClient(hass=hass, user_code="EU12345678", app_schema="smartlife")
    client._manager = MagicMock()

    mock_config_entry.add_to_hass(hass)

    # Real coordinator wired to the real client
    coord = KKTKolbeHybridCoordinator(
        hass=hass,
        entry=mock_config_entry,
        local_device=mock_tuya_device,
        device_id="bf735dfe2ad64fba7cpyhn",
        device_type="hermes_style_hood",
        smartlife_client=client,
    )
    coord._dps_cache = {"1": False, "10": "off"}
    captured: list[dict] = []
    coord.async_set_updated_data = lambda data: captured.append(data)

    # Register through the real lifecycle (renamed from async_added_to_hass per Task 2 fix)
    await coord.async_register_push()

    # Verify the client now has the coord's callback registered
    assert "bf735dfe2ad64fba7cpyhn" in client._push_callbacks
    assert coord._handle_push_update in client._push_callbacks["bf735dfe2ad64fba7cpyhn"]

    # Fire a push via the REAL dispatcher (skips the SDK-listener thread bounce
    # since we're already on the event loop and the listener bridge is tested
    # in test_tuya_sharing_client.py)
    client._dispatch_push("bf735dfe2ad64fba7cpyhn", {"1": True}, "report")

    # Verify the coordinator handler ran and merged correctly
    assert len(captured) == 1
    assert captured[0]["dps"] == {"1": True, "10": "off"}  # merged: existing 10 preserved
    assert captured[0]["source"] == "smartlife_push"
    assert "timestamp" in captured[0]

    # Cleanup: shutdown should unregister
    await coord.async_shutdown()
    assert "bf735dfe2ad64fba7cpyhn" not in client._push_callbacks
