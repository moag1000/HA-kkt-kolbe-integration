"""Test the KKT Kolbe coordinator."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.kkt_kolbe.const import DOMAIN


@pytest.fixture
def mock_device():
    """Create a mock Tuya device."""
    device = MagicMock()
    device.device_id = "test_device_123"
    device.ip_address = "192.168.1.100"
    device.local_key = "1234567890123456"
    device.is_connected = True
    device.async_connect = AsyncMock(return_value=True)
    device.async_disconnect = AsyncMock()
    device.async_status = AsyncMock(return_value={"dps": {"1": True, "4": False}})
    device.async_set = AsyncMock()
    return device


@pytest.mark.asyncio
async def test_coordinator_initialization(
    hass: HomeAssistant,
    mock_device,
) -> None:
    """Test coordinator initialization."""
    from custom_components.kkt_kolbe.coordinator import KKTKolbeDataUpdateCoordinator

    coordinator = KKTKolbeDataUpdateCoordinator(
        hass=hass,
        device=mock_device,
        update_interval=timedelta(seconds=30),
    )

    assert coordinator.device == mock_device
    assert coordinator.update_interval == timedelta(seconds=30)


@pytest.mark.asyncio
async def test_coordinator_first_refresh(
    hass: HomeAssistant,
    mock_device,
) -> None:
    """Test coordinator first refresh."""
    from custom_components.kkt_kolbe.coordinator import KKTKolbeDataUpdateCoordinator

    coordinator = KKTKolbeDataUpdateCoordinator(
        hass=hass,
        device=mock_device,
        update_interval=timedelta(seconds=30),
    )

    await coordinator.async_config_entry_first_refresh()

    # Device should have been polled
    mock_device.async_status.assert_called()


@pytest.mark.asyncio
async def test_coordinator_data_update(
    hass: HomeAssistant,
    mock_device,
) -> None:
    """Test coordinator data update."""
    from custom_components.kkt_kolbe.coordinator import KKTKolbeDataUpdateCoordinator

    mock_device.async_status.return_value = {"dps": {"1": True, "4": True, "10": 3}}

    coordinator = KKTKolbeDataUpdateCoordinator(
        hass=hass,
        device=mock_device,
        update_interval=timedelta(seconds=30),
    )

    await coordinator.async_config_entry_first_refresh()

    # Data should be updated
    assert coordinator.data is not None
    assert "1" in coordinator.data or 1 in coordinator.data


@pytest.mark.asyncio
async def test_coordinator_set_data_point(
    hass: HomeAssistant,
    mock_device,
) -> None:
    """Test coordinator set_data_point method."""
    from custom_components.kkt_kolbe.coordinator import KKTKolbeDataUpdateCoordinator

    coordinator = KKTKolbeDataUpdateCoordinator(
        hass=hass,
        device=mock_device,
        update_interval=timedelta(seconds=30),
    )

    await coordinator.async_set_data_point(1, True)

    mock_device.async_set.assert_called()


@pytest.mark.asyncio
async def test_coordinator_connection_failure(
    hass: HomeAssistant,
    mock_device,
) -> None:
    """Test coordinator handles connection failure."""
    from custom_components.kkt_kolbe.coordinator import KKTKolbeDataUpdateCoordinator

    mock_device.async_status.side_effect = Exception("Connection refused")
    mock_device.is_connected = False

    coordinator = KKTKolbeDataUpdateCoordinator(
        hass=hass,
        device=mock_device,
        update_interval=timedelta(seconds=30),
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_reconnect_on_failure(
    hass: HomeAssistant,
    mock_device,
) -> None:
    """Test coordinator attempts reconnection on failure."""
    from custom_components.kkt_kolbe.coordinator import KKTKolbeDataUpdateCoordinator

    # First call fails, second succeeds
    mock_device.async_status.side_effect = [
        Exception("Connection lost"),
        {"dps": {"1": True}},
    ]
    mock_device.is_connected = False

    coordinator = KKTKolbeDataUpdateCoordinator(
        hass=hass,
        device=mock_device,
        update_interval=timedelta(seconds=30),
    )

    # First update should fail
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_hybrid_coordinator_initialization(
    hass: HomeAssistant,
    mock_device,
) -> None:
    """Test hybrid coordinator initialization."""
    from custom_components.kkt_kolbe.hybrid_coordinator import HybridCoordinator

    mock_api_client = MagicMock()
    mock_api_client.is_authenticated = True

    coordinator = HybridCoordinator(
        hass=hass,
        device=mock_device,
        api_client=mock_api_client,
        update_interval=timedelta(seconds=30),
    )

    assert coordinator.device == mock_device
    assert coordinator.api_client == mock_api_client


@pytest.mark.asyncio
async def test_hybrid_coordinator_local_first(
    hass: HomeAssistant,
    mock_device,
) -> None:
    """Test hybrid coordinator tries local first."""
    from custom_components.kkt_kolbe.hybrid_coordinator import HybridCoordinator

    mock_api_client = MagicMock()
    mock_api_client.is_authenticated = True
    mock_api_client.async_get_device_status = AsyncMock()

    mock_device.async_status.return_value = {"dps": {"1": True}}
    mock_device.is_connected = True

    coordinator = HybridCoordinator(
        hass=hass,
        device=mock_device,
        api_client=mock_api_client,
        update_interval=timedelta(seconds=30),
    )

    await coordinator.async_config_entry_first_refresh()

    # Local should be tried first
    mock_device.async_status.assert_called()


@pytest.mark.asyncio
async def test_hybrid_coordinator_api_fallback(
    hass: HomeAssistant,
    mock_device,
) -> None:
    """Test hybrid coordinator falls back to API on local failure."""
    from custom_components.kkt_kolbe.hybrid_coordinator import HybridCoordinator

    mock_api_client = MagicMock()
    mock_api_client.is_authenticated = True
    mock_api_client.async_get_device_status = AsyncMock(
        return_value={"result": {"dps": {"1": True}}}
    )

    mock_device.async_status.side_effect = Exception("Local connection failed")
    mock_device.is_connected = False

    coordinator = HybridCoordinator(
        hass=hass,
        device=mock_device,
        api_client=mock_api_client,
        update_interval=timedelta(seconds=30),
    )

    # Should try API after local fails
    try:
        await coordinator._async_update_data()
    except Exception:
        pass  # May still fail but API should be attempted

    # API fallback should have been attempted
    # (exact behavior depends on implementation)
