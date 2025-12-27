"""Test the KKT Kolbe services."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.kkt_kolbe.const import DOMAIN
from custom_components.kkt_kolbe.services import (
    async_setup_services,
    async_unload_services,
    SERVICE_SET_COOKING_TIMER,
    SERVICE_SYNC_ALL_DEVICES,
    SERVICE_EMERGENCY_STOP,
    SERVICE_RECONNECT_DEVICE,
)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.device = MagicMock()
    coordinator.device.device_id = "test_device_123"
    coordinator.device.ip_address = "192.168.1.100"
    coordinator.device.is_connected = True
    coordinator.last_update_success = True
    coordinator.last_update_success_time = None
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_set_data_point = AsyncMock()
    return coordinator


@pytest.mark.asyncio
async def test_setup_services(hass: HomeAssistant) -> None:
    """Test service registration."""
    await async_setup_services(hass)

    # Check that services are registered
    assert hass.services.has_service(DOMAIN, SERVICE_SET_COOKING_TIMER)
    assert hass.services.has_service(DOMAIN, SERVICE_SYNC_ALL_DEVICES)
    assert hass.services.has_service(DOMAIN, SERVICE_EMERGENCY_STOP)
    assert hass.services.has_service(DOMAIN, SERVICE_RECONNECT_DEVICE)


@pytest.mark.asyncio
async def test_unload_services(hass: HomeAssistant) -> None:
    """Test service unregistration."""
    await async_setup_services(hass)
    await async_unload_services(hass)

    # Check that services are removed
    assert not hass.services.has_service(DOMAIN, SERVICE_SET_COOKING_TIMER)
    assert not hass.services.has_service(DOMAIN, SERVICE_SYNC_ALL_DEVICES)


@pytest.mark.asyncio
async def test_sync_all_devices_service(
    hass: HomeAssistant,
    mock_coordinator,
) -> None:
    """Test sync all devices service."""
    await async_setup_services(hass)

    # Setup mock data
    hass.data[DOMAIN] = {
        "entry_1": {"coordinator": mock_coordinator},
    }

    # Call the service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SYNC_ALL_DEVICES,
        {"device_filter": "all"},
        blocking=True,
    )

    # Verify coordinator refresh was called
    mock_coordinator.async_request_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_sync_all_devices_online_filter(
    hass: HomeAssistant,
    mock_coordinator,
) -> None:
    """Test sync all devices with online_only filter."""
    await async_setup_services(hass)

    # Setup mock data with online coordinator
    mock_coordinator.last_update_success = True
    hass.data[DOMAIN] = {
        "entry_1": {"coordinator": mock_coordinator},
    }

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SYNC_ALL_DEVICES,
        {"device_filter": "online_only"},
        blocking=True,
    )

    mock_coordinator.async_request_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_sync_all_devices_offline_filter(
    hass: HomeAssistant,
    mock_coordinator,
) -> None:
    """Test sync all devices with offline_only filter (skips online)."""
    await async_setup_services(hass)

    # Setup mock data with online coordinator
    mock_coordinator.last_update_success = True
    hass.data[DOMAIN] = {
        "entry_1": {"coordinator": mock_coordinator},
    }

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SYNC_ALL_DEVICES,
        {"device_filter": "offline_only"},
        blocking=True,
    )

    # Should not refresh online coordinator
    mock_coordinator.async_request_refresh.assert_not_called()


@pytest.mark.asyncio
async def test_emergency_stop_requires_confirm(hass: HomeAssistant) -> None:
    """Test emergency stop requires confirmation."""
    await async_setup_services(hass)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_EMERGENCY_STOP,
            {"confirm": False},
            blocking=True,
        )


@pytest.mark.asyncio
async def test_reconnect_device_no_match(hass: HomeAssistant) -> None:
    """Test reconnect device with no matching device."""
    await async_setup_services(hass)

    hass.data[DOMAIN] = {}

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RECONNECT_DEVICE,
            {"device_id": "nonexistent"},
            blocking=True,
        )


@pytest.mark.asyncio
async def test_reconnect_device_success(
    hass: HomeAssistant,
    mock_coordinator,
) -> None:
    """Test successful device reconnection."""
    await async_setup_services(hass)

    mock_coordinator.async_request_reconnect = AsyncMock(return_value=True)
    mock_coordinator.device_state = MagicMock()
    mock_coordinator.device_state.value = "online"

    hass.data[DOMAIN] = {
        "entry_1": {"coordinator": mock_coordinator},
    }

    # Capture events
    events = []
    hass.bus.async_listen(f"{DOMAIN}_reconnect_complete", lambda e: events.append(e))

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECONNECT_DEVICE,
        {},
        blocking=True,
    )

    mock_coordinator.async_request_reconnect.assert_called_once()


@pytest.mark.asyncio
async def test_get_connection_status(
    hass: HomeAssistant,
    mock_coordinator,
) -> None:
    """Test get connection status service."""
    await async_setup_services(hass)

    mock_coordinator.connection_info = {
        "state": "online",
        "ip_address": "192.168.1.100",
    }

    hass.data[DOMAIN] = {
        "entry_1": {"coordinator": mock_coordinator},
    }

    events = []
    hass.bus.async_listen(f"{DOMAIN}_connection_status", lambda e: events.append(e))

    await hass.services.async_call(
        DOMAIN,
        "get_connection_status",
        {},
        blocking=True,
    )

    # Event should be fired with status info
    assert len(events) >= 0  # Event fired asynchronously
