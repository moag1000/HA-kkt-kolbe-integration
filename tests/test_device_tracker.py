"""Test the KKT Kolbe device tracker (stale device cleanup)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kkt_kolbe.const import DOMAIN
from custom_components.kkt_kolbe.device_tracker import (
    StaleDeviceTracker,
    async_start_tracker,
    async_stop_tracker,
    track_device_activity,
    STALE_DEVICE_THRESHOLD,
    CLEANUP_INTERVAL,
)


@pytest.fixture
def mock_device_registry():
    """Create a mock device registry."""
    device = MagicMock()
    device.id = "device_123"
    device.name = "Test Hood"
    device.config_entries = {"entry_123"}
    device.created_at = datetime.now() - timedelta(days=1)

    registry = MagicMock()
    registry.async_entries_for_config_entry = MagicMock(return_value=[device])
    registry.async_remove_device = MagicMock()
    return registry, device


@pytest.fixture
def mock_entity_registry():
    """Create a mock entity registry."""
    entity = MagicMock()
    entity.entity_id = "switch.test_hood_power"
    entity.device_id = "device_123"

    registry = MagicMock()
    registry.async_entries_for_device = MagicMock(return_value=[entity])
    return registry, entity


@pytest.mark.asyncio
async def test_stale_device_tracker_init(hass: HomeAssistant) -> None:
    """Test StaleDeviceTracker initialization."""
    tracker = StaleDeviceTracker(hass)

    assert tracker.hass == hass
    assert tracker._cleanup_task is None
    assert len(tracker._tracked_devices) == 0


@pytest.mark.asyncio
async def test_stale_device_tracker_start(hass: HomeAssistant) -> None:
    """Test starting the tracker."""
    tracker = StaleDeviceTracker(hass)

    await tracker.async_start()

    assert tracker._cleanup_task is not None


@pytest.mark.asyncio
async def test_stale_device_tracker_stop(hass: HomeAssistant) -> None:
    """Test stopping the tracker."""
    tracker = StaleDeviceTracker(hass)

    await tracker.async_start()
    await tracker.async_stop()

    assert tracker._cleanup_task is None


@pytest.mark.asyncio
async def test_track_device_activity(hass: HomeAssistant) -> None:
    """Test tracking device activity."""
    tracker = StaleDeviceTracker(hass)

    tracker.track_device("device_123")

    assert "device_123" in tracker._tracked_devices


@pytest.mark.asyncio
async def test_is_device_stale_available_entity(
    hass: HomeAssistant,
    mock_device_registry,
    mock_entity_registry,
) -> None:
    """Test device is not stale when entity is available."""
    device_reg, device = mock_device_registry
    entity_reg, entity = mock_entity_registry

    # Mock state as available
    state = MagicMock()
    state.state = "on"
    state.last_updated = datetime.now()
    hass.states._states = {entity.entity_id: state}

    tracker = StaleDeviceTracker(hass)

    is_stale = await tracker._is_device_stale(device, entity_reg)

    assert is_stale is False


@pytest.mark.asyncio
async def test_is_device_stale_unavailable_entity(
    hass: HomeAssistant,
    mock_device_registry,
    mock_entity_registry,
) -> None:
    """Test device is stale when entity is unavailable for too long."""
    device_reg, device = mock_device_registry
    entity_reg, entity = mock_entity_registry

    # Mock state as unavailable for longer than threshold
    state = MagicMock()
    state.state = "unavailable"
    state.last_updated = datetime.now() - timedelta(days=35)

    # Setup hass.states mock
    hass.states.get = MagicMock(return_value=state)

    # Setup config entries mock
    entry = MagicMock()
    entry.disabled_by = None
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)
    hass.config_entries.async_entries = MagicMock(return_value=[entry])

    # No coordinator data
    hass.data = {}

    tracker = StaleDeviceTracker(hass)

    is_stale = await tracker._is_device_stale(device, entity_reg)

    # Should be stale (unavailable for 35 days > 30 day threshold)
    assert is_stale is True


@pytest.mark.asyncio
async def test_is_device_stale_no_entities(
    hass: HomeAssistant,
    mock_device_registry,
) -> None:
    """Test device staleness check with no entities."""
    device_reg, device = mock_device_registry

    entity_reg = MagicMock()
    entity_reg.async_entries_for_device = MagicMock(return_value=[])

    # Device is old
    device.created_at = datetime.now() - timedelta(days=35)

    tracker = StaleDeviceTracker(hass)

    is_stale = await tracker._is_device_stale(device, entity_reg)

    # Old device with no entities should be stale
    assert is_stale is True


@pytest.mark.asyncio
async def test_is_device_stale_new_device(
    hass: HomeAssistant,
    mock_device_registry,
) -> None:
    """Test new device without entities is not stale."""
    device_reg, device = mock_device_registry

    entity_reg = MagicMock()
    entity_reg.async_entries_for_device = MagicMock(return_value=[])

    # Device is new
    device.created_at = datetime.now() - timedelta(days=1)

    tracker = StaleDeviceTracker(hass)

    is_stale = await tracker._is_device_stale(device, entity_reg)

    # New device should not be stale yet
    assert is_stale is False


@pytest.mark.asyncio
async def test_global_tracker_functions(hass: HomeAssistant) -> None:
    """Test global tracker start/stop functions."""
    await async_start_tracker(hass)

    # Track a device
    track_device_activity("device_123")

    await async_stop_tracker()


@pytest.mark.asyncio
async def test_cleanup_stale_devices(
    hass: HomeAssistant,
    mock_device_registry,
    mock_entity_registry,
) -> None:
    """Test cleanup of stale devices."""
    device_reg, device = mock_device_registry
    entity_reg, entity = mock_entity_registry

    # Mock unavailable state for long time
    state = MagicMock()
    state.state = "unavailable"
    state.last_updated = datetime.now() - timedelta(days=35)
    hass.states.get = MagicMock(return_value=state)

    # Setup config entries
    entry = MagicMock()
    entry.entry_id = "entry_123"
    entry.disabled_by = None
    hass.config_entries.async_entries = MagicMock(return_value=[entry])
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)
    hass.data = {DOMAIN: {}}

    tracker = StaleDeviceTracker(hass)

    with patch.object(tracker, '_is_device_stale', return_value=True):
        with patch('custom_components.kkt_kolbe.device_tracker.dr') as mock_dr:
            with patch('custom_components.kkt_kolbe.device_tracker.er') as mock_er:
                mock_dr.async_get = MagicMock(return_value=device_reg)
                mock_dr.async_entries_for_config_entry = MagicMock(return_value=[device])
                mock_er.async_get = MagicMock(return_value=entity_reg)

                await tracker._async_cleanup_stale_devices(None)

                # Device should be removed
                device_reg.async_remove_device.assert_called_once_with(device.id)


def test_stale_device_threshold() -> None:
    """Test stale device threshold is 30 days."""
    assert STALE_DEVICE_THRESHOLD == timedelta(days=30)


def test_cleanup_interval() -> None:
    """Test cleanup interval is 24 hours."""
    assert CLEANUP_INTERVAL == timedelta(hours=24)
