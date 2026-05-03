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
async def test_hybrid_coord_registers_push_callback_when_smartlife_client_present(
    hass: HomeAssistant,
    mock_config_entry,
    mock_smartlife_client: MagicMock,
) -> None:
    """async_added_to_hass registers our handler on the smartlife client."""
    coord = _make_coord(hass, mock_config_entry, smartlife_client=mock_smartlife_client)

    await coord.async_added_to_hass()

    mock_smartlife_client.register_push_callback.assert_called_once_with(coord.device_id, coord._handle_push_update)
    assert coord._push_callback_registered is True


@pytest.mark.asyncio
async def test_hybrid_coord_skips_registration_without_smartlife_client(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """async_added_to_hass is a no-op when smartlife_client is None."""
    coord = _make_coord(hass, mock_config_entry, smartlife_client=None)

    # Must not raise
    await coord.async_added_to_hass()

    assert coord._push_callback_registered is False


@pytest.mark.asyncio
async def test_hybrid_coord_unregisters_on_shutdown(
    hass: HomeAssistant,
    mock_config_entry,
    mock_smartlife_client: MagicMock,
) -> None:
    """async_shutdown unregisters the push callback and clears the flag."""
    coord = _make_coord(hass, mock_config_entry, smartlife_client=mock_smartlife_client)

    await coord.async_added_to_hass()
    assert coord._push_callback_registered is True

    await coord.async_shutdown()

    mock_smartlife_client.unregister_push_callback.assert_called_once_with(coord.device_id, coord._handle_push_update)
    assert coord._push_callback_registered is False
