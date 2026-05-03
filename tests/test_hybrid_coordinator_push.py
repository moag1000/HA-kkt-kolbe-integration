"""Tests for the HybridCoordinator MQTT push handler + lifecycle (Task 2)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.core import HomeAssistant


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
