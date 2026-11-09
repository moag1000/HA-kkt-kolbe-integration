"""Test the KKT Kolbe services."""
from __future__ import annotations

from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kkt_kolbe.const import DOMAIN
from custom_components.kkt_kolbe.services import SERVICE_EMERGENCY_STOP
from custom_components.kkt_kolbe.services import SERVICE_RECONNECT_DEVICE
from custom_components.kkt_kolbe.services import SERVICE_SET_COOKING_TIMER
from custom_components.kkt_kolbe.services import SERVICE_SYNC_ALL_DEVICES
from custom_components.kkt_kolbe.services import async_setup_services
from custom_components.kkt_kolbe.services import async_unload_services


def _add_loaded_entry(hass: HomeAssistant, coordinator, entry_id: str = "entry_1") -> MockConfigEntry:
    """Register a loaded device entry whose runtime_data carries the coordinator."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id=entry_id,
        data={"device_id": "test_device_123"},
        state=ConfigEntryState.LOADED,
    )
    entry.add_to_hass(hass)
    entry.runtime_data = MagicMock(coordinator=coordinator)
    return entry


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
    _add_loaded_entry(hass, mock_coordinator)

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
    _add_loaded_entry(hass, mock_coordinator)

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
    _add_loaded_entry(hass, mock_coordinator)

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

    _add_loaded_entry(hass, mock_coordinator)

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

    _add_loaded_entry(hass, mock_coordinator)

    events = []
    hass.bus.async_listen(f"{DOMAIN}_connection_status", lambda e: events.append(e))

    response = await hass.services.async_call(
        DOMAIN,
        "get_connection_status",
        {},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    # Action response (and the legacy event) carry the status per entry
    assert response == {"statuses": {"entry_1": {"state": "online", "ip_address": "192.168.1.100"}}}
    assert len(events) == 1


@pytest.mark.asyncio
async def test_get_firmware_info_response_without_client(
    hass: HomeAssistant,
    mock_coordinator,
) -> None:
    """get_firmware_info returns the per-device payload as action response."""
    await async_setup_services(hass)

    mock_coordinator.smartlife_client = None
    _add_loaded_entry(hass, mock_coordinator)

    response = await hass.services.async_call(
        DOMAIN,
        "get_firmware_info",
        {},
        blocking=True,
        return_response=True,
    )

    assert response == {
        "devices": [
            {
                "entry_id": "entry_1",
                "device_id": "test_device_123",
                "available": False,
                "reason": "SmartLife client not configured for this entry",
            }
        ]
    }


@pytest.mark.asyncio
async def test_entity_action_validates_range(hass: HomeAssistant) -> None:
    """Entity actions validate their fields before touching any entity."""
    import voluptuous as vol

    from custom_components.kkt_kolbe.services import SERVICE_SET_HOOD_FAN_SPEED

    await async_setup_services(hass)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SET_HOOD_FAN_SPEED,
            {"entity_id": "number.kkt_fan_level", "fan_speed": 9},
            blocking=True,
        )


@pytest.mark.asyncio
async def test_reconnect_by_registry_device_id(hass: HomeAssistant, mock_coordinator) -> None:
    """The device selector passes a registry device id; it must match the entry."""
    from homeassistant.helpers import device_registry as dr

    await async_setup_services(hass)
    mock_coordinator.async_request_reconnect = AsyncMock(return_value=True)
    mock_coordinator.device_state = MagicMock(value="online")
    entry = _add_loaded_entry(hass, mock_coordinator)

    other = MagicMock()
    other.async_request_reconnect = AsyncMock(return_value=True)
    _add_loaded_entry(hass, other, entry_id="entry_2")

    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "test_device_123")}
    )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_RECONNECT_DEVICE,
        {"device_id": device.id},
        blocking=True,
    )

    mock_coordinator.async_request_reconnect.assert_awaited_once()
    other.async_request_reconnect.assert_not_called()
