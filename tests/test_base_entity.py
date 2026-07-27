"""Test KKTBaseEntity.available against real coordinator circuit-breaker states.

These tests pin the contract described in base_entity.py's `available`
property (~line 271-323): once the coordinator's circuit breaker trips
(DeviceState.UNREACHABLE), the entity must report unavailable even if it
still holds a cached value -- we don't want to keep showing a frozen
reading once retries have been suspended. Transient states (RECONNECTING /
OFFLINE) reached *after* the initial connect must NOT flip the entity
unavailable as long as a cached value exists (this prevents flapping
during short blips).
"""
from __future__ import annotations

from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_device():
    """Create a mock Tuya device (mirrors tests/test_coordinator.py)."""
    device = MagicMock()
    device.device_id = "test_device_123"
    device.ip_address = "192.168.1.100"
    device.local_key = "1234567890123456"
    device.is_connected = True
    device.async_connect = AsyncMock(return_value=True)
    device.async_disconnect = AsyncMock()
    device.async_get_status = AsyncMock(return_value={"1": True, "4": False})
    device.async_set_dp = AsyncMock()
    return device


def _make_entity(coordinator, entry):
    """Build a bare KKTBaseEntity wrapping the given coordinator."""
    from custom_components.kkt_kolbe.base_entity import KKTBaseEntity

    config = {"dp": 1, "name": "Test Entity"}
    return KKTBaseEntity(coordinator, entry, config, "sensor")


@pytest.mark.asyncio
async def test_available_false_when_circuit_breaker_unreachable(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """UNREACHABLE (circuit breaker tripped) must be unavailable even with cache."""
    from custom_components.kkt_kolbe.coordinator import DeviceState
    from custom_components.kkt_kolbe.coordinator import KKTKolbeUpdateCoordinator
    from custom_components.kkt_kolbe.exceptions import KKTConnectionError

    mock_device.async_get_status.side_effect = KKTConnectionError("Connection failed")
    mock_device.is_connected = False
    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeUpdateCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_device,
    )
    coordinator.mark_initial_connect_done()
    coordinator._max_reconnect_attempts = 3

    # Drive the circuit breaker to trip (same technique as
    # test_coordinator_circuit_breaker in tests/test_coordinator.py).
    for _ in range(5):
        await coordinator._async_update_data()

    assert coordinator._device_state == DeviceState.UNREACHABLE
    assert coordinator.is_device_available is False

    entity = _make_entity(coordinator, mock_config_entry)
    # Simulate a previously cached value -- must NOT mask the outage.
    entity._cached_value = 42

    assert entity.available is False, (
        "Entity must report unavailable once the circuit breaker has tripped "
        "(DeviceState.UNREACHABLE), even with a non-None cached value. "
        "See base_entity.py available property, ~line 291-297."
    )


@pytest.mark.asyncio
async def test_available_true_transient_reconnecting_with_cache(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """A single post-startup failure (state -> RECONNECTING) with cached data stays available."""
    from custom_components.kkt_kolbe.coordinator import DeviceState
    from custom_components.kkt_kolbe.coordinator import KKTKolbeUpdateCoordinator
    from custom_components.kkt_kolbe.exceptions import KKTConnectionError

    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeUpdateCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_device,
    )
    coordinator.mark_initial_connect_done()

    # First: a successful update so the coordinator leaves the initial
    # "first update" leniency window (is_device_available's special-case
    # for _is_first_update no longer applies afterwards).
    await coordinator._async_update_data()
    assert coordinator._device_state == DeviceState.ONLINE
    assert coordinator._is_first_update is False

    entity = _make_entity(coordinator, mock_config_entry)
    entity._cached_value = 99

    # Now a single connection failure -- below the OFFLINE threshold (3),
    # and ONLINE -> RECONNECTING per _async_update_data.
    mock_device.async_get_status.side_effect = KKTConnectionError("blip")
    mock_device.is_connected = False
    await coordinator._async_update_data()

    assert coordinator._device_state == DeviceState.RECONNECTING
    assert coordinator.is_device_available is False, (
        "is_device_available should be False for RECONNECTING once past the "
        "first-update leniency window (this test's own precondition)."
    )

    assert entity.available is True, (
        "Entity should stay available during a transient RECONNECTING blip "
        "as long as a cached value exists, to avoid flapping. "
        "See base_entity.py available property, ~line 299-302."
    )


@pytest.mark.asyncio
async def test_available_true_offline_with_cache(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """Sustained failures reaching OFFLINE (not UNREACHABLE) with cached data stays available."""
    from custom_components.kkt_kolbe.coordinator import DeviceState
    from custom_components.kkt_kolbe.coordinator import KKTKolbeUpdateCoordinator
    from custom_components.kkt_kolbe.exceptions import KKTConnectionError

    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeUpdateCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_device,
    )
    coordinator.mark_initial_connect_done()
    # Keep max reconnect attempts generous so we reach OFFLINE, not UNREACHABLE.
    coordinator._max_reconnect_attempts = 10

    await coordinator._async_update_data()
    assert coordinator._device_state == DeviceState.ONLINE

    entity = _make_entity(coordinator, mock_config_entry)
    entity._cached_value = 7

    mock_device.async_get_status.side_effect = KKTConnectionError("still down")
    mock_device.is_connected = False

    # DEFAULT_CONSECUTIVE_FAILURES_THRESHOLD is 3 -- three failures push
    # ONLINE -> RECONNECTING -> RECONNECTING -> OFFLINE.
    for _ in range(3):
        await coordinator._async_update_data()

    assert coordinator._device_state == DeviceState.OFFLINE
    assert coordinator.is_device_available is False

    assert entity.available is True, (
        "Entity should stay available while OFFLINE (not yet circuit-breaker "
        "UNREACHABLE) as long as a cached value exists. "
        "See base_entity.py available property, ~line 299-302."
    )


@pytest.mark.asyncio
async def test_hybrid_coordinator_device_state_and_availability(
    hass: HomeAssistant,
) -> None:
    """Hybrid coordinator must expose device_state/is_device_available so entities
    can go unavailable on a sustained outage (previously only the local-only
    coordinator had these, so hybrid-mode devices froze on a stale cache).
    """
    from unittest.mock import MagicMock

    from custom_components.kkt_kolbe.coordinator import DeviceState
    from custom_components.kkt_kolbe.hybrid_coordinator import KKTKolbeHybridCoordinator

    coord = KKTKolbeHybridCoordinator(hass, "dev1234567890", local_device=MagicMock())

    # Success -> ONLINE / available
    coord.last_update_success = True
    assert coord.device_state == DeviceState.ONLINE
    assert coord.is_device_available is True

    # Transient failure (budget not yet exhausted) -> RECONNECTING, still available
    coord.last_update_success = False
    coord.local_consecutive_errors = 1
    assert coord.device_state == DeviceState.RECONNECTING
    assert coord.is_device_available is True

    # Local channel exhausted, no api channel -> UNREACHABLE / unavailable
    coord.local_consecutive_errors = coord.max_consecutive_errors
    assert coord.device_state == DeviceState.UNREACHABLE
    assert coord.is_device_available is False
