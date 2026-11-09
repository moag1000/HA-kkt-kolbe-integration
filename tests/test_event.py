"""Test the KKT Kolbe device event entity."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kkt_kolbe import KKTKolbeRuntimeData
from custom_components.kkt_kolbe.event import EVENT_CONNECTION_LOST
from custom_components.kkt_kolbe.event import EVENT_CONNECTION_MODE_CHANGED
from custom_components.kkt_kolbe.event import EVENT_CONNECTION_RESTORED
from custom_components.kkt_kolbe.event import EVENT_FILTER_CLEANING_DUE
from custom_components.kkt_kolbe.event import EVENT_TIMER_FINISHED
from custom_components.kkt_kolbe.event import EVENT_ZONE_ERROR
from custom_components.kkt_kolbe.event import KKTKolbeDeviceEvent
from custom_components.kkt_kolbe.event import async_setup_entry


def _runtime(device_type: str, data: dict, mode: str | None = None) -> KKTKolbeRuntimeData:
    coordinator = MagicMock(spec=["data", "last_update_success", "async_add_listener", "current_mode"])
    coordinator.data = data
    coordinator.last_update_success = True
    if mode is None:
        del coordinator.current_mode
    else:
        coordinator.current_mode = mode
    return KKTKolbeRuntimeData(
        coordinator=coordinator,
        device=None,
        api_client=None,
        device_info={"category": "hood"},
        product_name=device_type,
        device_type=device_type,
        integration_mode="manual",
    )


def _entity(mock_config_entry, runtime) -> tuple[KKTKolbeDeviceEvent, list]:
    mock_config_entry.runtime_data = runtime
    entity = KKTKolbeDeviceEvent(mock_config_entry)
    fired: list = []
    entity._trigger_event = lambda event_type, attrs=None: fired.append((event_type, attrs))
    entity._observe(fire=False)  # baseline, as in async_added_to_hass
    return entity, fired


@pytest.mark.asyncio
async def test_setup_adds_one_event_entity(hass: HomeAssistant, mock_config_entry) -> None:
    """Every device entry gets exactly one event entity."""
    mock_config_entry.add_to_hass(hass)
    mock_config_entry.runtime_data = _runtime("hermes_style_hood", {})
    added: list = []
    await async_setup_entry(hass, mock_config_entry, added.extend)
    assert len(added) == 1
    entity = added[0]
    assert entity.unique_id == f"{mock_config_entry.entry_id}_event_device"
    assert entity.available is True
    assert EVENT_TIMER_FINISHED in entity.event_types
    assert EVENT_FILTER_CLEANING_DUE in entity.event_types
    assert EVENT_ZONE_ERROR not in entity.event_types
    assert EVENT_CONNECTION_MODE_CHANGED not in entity.event_types


def test_first_update_never_fires(mock_config_entry) -> None:
    """The baseline update records state but fires nothing."""
    entity, fired = _entity(mock_config_entry, _runtime("hermes_style_hood", {"13": 0, "6": True}))
    assert entity._observe(fire=True) is False
    assert fired == []


def test_timer_finished_and_filter_due(mock_config_entry) -> None:
    """Countdown >0 -> 0 and filter reminder off -> on fire events."""
    runtime = _runtime("hermes_style_hood", {"13": 5, "6": False})
    entity, fired = _entity(mock_config_entry, runtime)

    runtime.coordinator.data = {"13": 0, "6": True}
    entity._observe(fire=True)

    assert (EVENT_TIMER_FINISHED, {"data_point": 13}) in fired
    assert (EVENT_FILTER_CLEANING_DUE, {"data_point": 6}) in fired

    # Staying at 0 / on does not fire again
    fired.clear()
    entity._observe(fire=True)
    assert fired == []


def test_connection_lost_and_restored(mock_config_entry) -> None:
    """Coordinator failure and recovery are reported."""
    runtime = _runtime("hermes_style_hood", {"13": 3})
    entity, fired = _entity(mock_config_entry, runtime)

    runtime.coordinator.last_update_success = False
    entity._observe(fire=True)
    runtime.coordinator.last_update_success = True
    entity._observe(fire=True)

    assert [event for event, _ in fired] == [EVENT_CONNECTION_LOST, EVENT_CONNECTION_RESTORED]


def test_connection_mode_changed(mock_config_entry) -> None:
    """Hybrid mode switches are reported with old and new mode."""
    runtime = _runtime("hermes_style_hood", {}, mode="local")
    entity, fired = _entity(mock_config_entry, runtime)
    assert EVENT_CONNECTION_MODE_CHANGED in entity.event_types

    runtime.coordinator.current_mode = "smartlife"
    entity._observe(fire=True)

    assert fired == [(EVENT_CONNECTION_MODE_CHANGED, {"mode": "smartlife", "previous_mode": "local"})]


def test_cooktop_zone_error(mock_config_entry) -> None:
    """A new error bit on the cooktop error bitfield fires zone_error."""
    no_error = base64.b64encode(bytes([0])).decode()
    zone2_error = base64.b64encode(bytes([0b10])).decode()
    runtime = _runtime("ind7705hc_cooktop", {"105": no_error})
    entity, fired = _entity(mock_config_entry, runtime)
    assert EVENT_ZONE_ERROR in entity.event_types

    runtime.coordinator.data = {"105": zone2_error}
    entity._observe(fire=True)

    assert fired == [(EVENT_ZONE_ERROR, {"zone": 2, "data_point": 105})]
