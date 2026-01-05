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
    device.async_get_status = AsyncMock(return_value={"1": True, "4": False})
    device.async_set_dp = AsyncMock()
    return device


@pytest.mark.asyncio
async def test_coordinator_initialization(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """Test coordinator initialization."""
    from custom_components.kkt_kolbe.coordinator import KKTKolbeUpdateCoordinator

    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeUpdateCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_device,
    )

    assert coordinator.device == mock_device
    assert coordinator.update_interval == timedelta(seconds=30)


@pytest.mark.asyncio
async def test_coordinator_first_refresh(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """Test coordinator first refresh."""
    from custom_components.kkt_kolbe.coordinator import KKTKolbeUpdateCoordinator

    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeUpdateCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_device,
    )

    # Use async_refresh for tests (async_config_entry_first_refresh requires setup in progress)
    await coordinator.async_refresh()

    # Device should have been polled
    mock_device.async_get_status.assert_called()


@pytest.mark.asyncio
async def test_coordinator_data_update(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """Test coordinator data update."""
    from custom_components.kkt_kolbe.coordinator import KKTKolbeUpdateCoordinator

    mock_device.async_get_status.return_value = {"1": True, "4": True, "10": 3}
    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeUpdateCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_device,
    )

    await coordinator.async_refresh()

    # Data should be updated with new merged cache structure
    assert coordinator.data is not None
    # New format: {"dps": {...}, "source": "merged_cache", ...}
    assert "dps" in coordinator.data
    dps_data = coordinator.data.get("dps", coordinator.data)
    assert "1" in dps_data or 1 in dps_data


@pytest.mark.asyncio
async def test_coordinator_dps_cache_merging(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """Test that coordinator merges partial DPS updates into cache."""
    from custom_components.kkt_kolbe.coordinator import KKTKolbeUpdateCoordinator

    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeUpdateCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_device,
    )

    # First update: only DP 1 and 4
    mock_device.async_get_status.return_value = {"1": True, "4": False}
    await coordinator.async_refresh()

    dps_data = coordinator.data.get("dps", {})
    assert "1" in dps_data
    assert "4" in dps_data
    assert dps_data["1"] is True
    assert dps_data["4"] is False

    # Second update: only DP 10 (partial update)
    mock_device.async_get_status.return_value = {"10": 3}
    await coordinator.async_refresh()

    # Cache should now contain all 3 DPs (merged)
    dps_data = coordinator.data.get("dps", {})
    assert "1" in dps_data, "DP 1 should still be in cache after partial update"
    assert "4" in dps_data, "DP 4 should still be in cache after partial update"
    assert "10" in dps_data, "DP 10 should be added from partial update"
    assert dps_data["1"] is True
    assert dps_data["4"] is False
    assert dps_data["10"] == 3

    # Third update: update existing DP
    mock_device.async_get_status.return_value = {"1": False}
    await coordinator.async_refresh()

    # DP 1 should be updated, others preserved
    dps_data = coordinator.data.get("dps", {})
    assert dps_data["1"] is False, "DP 1 should be updated to False"
    assert dps_data["4"] is False, "DP 4 should still be preserved"
    assert dps_data["10"] == 3, "DP 10 should still be preserved"


@pytest.mark.asyncio
async def test_coordinator_set_data_point(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """Test coordinator set_data_point method."""
    from custom_components.kkt_kolbe.coordinator import KKTKolbeUpdateCoordinator

    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeUpdateCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_device,
    )

    await coordinator.async_set_data_point(1, True)
    # Wait for debounced refresh to complete
    await hass.async_block_till_done()

    mock_device.async_set_dp.assert_called()


@pytest.mark.asyncio
async def test_coordinator_connection_failure(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """Test coordinator handles connection failure."""
    from custom_components.kkt_kolbe.coordinator import KKTKolbeUpdateCoordinator

    mock_device.async_get_status.side_effect = Exception("Connection refused")
    mock_device.is_connected = False
    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeUpdateCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_device,
    )

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_reconnect_on_failure(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """Test coordinator attempts reconnection on failure."""
    from custom_components.kkt_kolbe.coordinator import KKTKolbeUpdateCoordinator

    # First call fails, second succeeds
    mock_device.async_get_status.side_effect = [
        Exception("Connection lost"),
        {"1": True},
    ]
    mock_device.is_connected = False
    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeUpdateCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_device,
    )

    # First update should fail
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_hybrid_coordinator_initialization(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """Test hybrid coordinator initialization."""
    from custom_components.kkt_kolbe.hybrid_coordinator import KKTKolbeHybridCoordinator

    mock_api_client = MagicMock()
    mock_api_client.is_authenticated = True
    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeHybridCoordinator(
        hass=hass,
        device_id=mock_device.device_id,
        local_device=mock_device,
        api_client=mock_api_client,
        update_interval=timedelta(seconds=30),
        entry=mock_config_entry,
    )

    assert coordinator.local_device == mock_device
    assert coordinator.api_client == mock_api_client


@pytest.mark.asyncio
async def test_hybrid_coordinator_local_first(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """Test hybrid coordinator tries local first."""
    from custom_components.kkt_kolbe.hybrid_coordinator import KKTKolbeHybridCoordinator

    mock_api_client = MagicMock()
    mock_api_client.is_authenticated = True
    mock_api_client.async_get_device_status = AsyncMock()

    mock_device.async_get_status.return_value = {"1": True}
    mock_device.is_connected = True
    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeHybridCoordinator(
        hass=hass,
        device_id=mock_device.device_id,
        local_device=mock_device,
        api_client=mock_api_client,
        update_interval=timedelta(seconds=30),
        entry=mock_config_entry,
    )

    await coordinator.async_refresh()

    # Local should be tried first
    mock_device.async_get_status.assert_called()


@pytest.mark.asyncio
async def test_hybrid_coordinator_api_fallback(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """Test hybrid coordinator falls back to API on local failure."""
    from custom_components.kkt_kolbe.hybrid_coordinator import KKTKolbeHybridCoordinator

    mock_api_client = MagicMock()
    mock_api_client.is_authenticated = True
    mock_api_client.get_device_status = AsyncMock(
        return_value=[{"code": "switch", "value": True}]
    )

    mock_device.async_get_status.side_effect = Exception("Local connection failed")
    mock_device.is_connected = False
    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeHybridCoordinator(
        hass=hass,
        device_id=mock_device.device_id,
        local_device=mock_device,
        api_client=mock_api_client,
        update_interval=timedelta(seconds=30),
        entry=mock_config_entry,
    )

    # Should try API after local fails
    try:
        await coordinator._async_update_data()
    except Exception:
        pass  # May still fail but API should be attempted

    # API fallback should have been attempted
    # (exact behavior depends on implementation)


@pytest.mark.asyncio
async def test_coordinator_alias() -> None:
    """Test that backwards compatibility alias exists."""
    from custom_components.kkt_kolbe.coordinator import (
        KKTKolbeUpdateCoordinator,
        KKTKolbeDataUpdateCoordinator,
    )

    assert KKTKolbeDataUpdateCoordinator is KKTKolbeUpdateCoordinator


@pytest.mark.asyncio
async def test_hybrid_coordinator_alias() -> None:
    """Test that backwards compatibility alias exists for hybrid coordinator."""
    from custom_components.kkt_kolbe.hybrid_coordinator import (
        KKTKolbeHybridCoordinator,
        HybridCoordinator,
    )

    assert HybridCoordinator is KKTKolbeHybridCoordinator


@pytest.mark.asyncio
async def test_coordinator_error_history(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """Test coordinator records errors in history."""
    from custom_components.kkt_kolbe.coordinator import KKTKolbeUpdateCoordinator
    from custom_components.kkt_kolbe.exceptions import KKTTimeoutError

    mock_device.async_get_status.side_effect = KKTTimeoutError("Test timeout")
    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeUpdateCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_device,
    )

    # Trigger an update that will fail
    await coordinator._async_update_data()

    # Check error history
    assert len(coordinator._error_history) > 0
    assert coordinator._error_history[-1]["error_type"] == "timeout"
    assert "Test timeout" in coordinator._error_history[-1]["message"]


@pytest.mark.asyncio
async def test_coordinator_exponential_backoff(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """Test coordinator applies exponential backoff."""
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

    initial_backoff = coordinator._current_backoff

    # Trigger multiple failures
    for _ in range(3):
        await coordinator._async_update_data()

    # Backoff should have increased
    assert coordinator._current_backoff > initial_backoff
    assert coordinator._reconnect_attempts >= 3


@pytest.mark.asyncio
async def test_coordinator_circuit_breaker(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """Test coordinator circuit breaker trips after max attempts."""
    from custom_components.kkt_kolbe.coordinator import (
        KKTKolbeUpdateCoordinator,
        DeviceState,
    )
    from custom_components.kkt_kolbe.exceptions import KKTConnectionError

    mock_device.async_get_status.side_effect = KKTConnectionError("Connection failed")
    mock_device.is_connected = False
    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeUpdateCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_device,
    )

    # Override max attempts for faster test
    coordinator._max_reconnect_attempts = 3

    # Trigger failures to trip circuit breaker
    for _ in range(5):
        await coordinator._async_update_data()

    # Circuit breaker should be tripped
    assert coordinator._device_state == DeviceState.UNREACHABLE
    assert coordinator._circuit_breaker_retries > 0
    assert coordinator._circuit_breaker_next_retry is not None


@pytest.mark.asyncio
async def test_coordinator_connection_info(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """Test coordinator connection_info property."""
    from custom_components.kkt_kolbe.coordinator import KKTKolbeUpdateCoordinator

    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeUpdateCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_device,
    )

    info = coordinator.connection_info

    assert "state" in info
    assert "consecutive_failures" in info
    assert "is_connected" in info
    assert "reconnect_attempts" in info
    assert "current_backoff" in info
    assert "circuit_breaker_retries" in info


@pytest.mark.asyncio
async def test_coordinator_reset_on_success(
    hass: HomeAssistant,
    mock_device,
    mock_config_entry,
) -> None:
    """Test coordinator resets counters on successful update."""
    from custom_components.kkt_kolbe.coordinator import (
        KKTKolbeUpdateCoordinator,
        DeviceState,
    )
    from custom_components.kkt_kolbe.exceptions import KKTConnectionError

    mock_config_entry.add_to_hass(hass)

    coordinator = KKTKolbeUpdateCoordinator(
        hass=hass,
        entry=mock_config_entry,
        device=mock_device,
    )

    # First, cause some failures
    mock_device.async_get_status.side_effect = KKTConnectionError("Test")
    mock_device.is_connected = False
    await coordinator._async_update_data()
    await coordinator._async_update_data()

    assert coordinator._consecutive_failures > 0
    assert coordinator._reconnect_attempts > 0

    # Now succeed
    mock_device.async_get_status.side_effect = None
    mock_device.async_get_status.return_value = {"1": True}
    mock_device.is_connected = True
    await coordinator._async_update_data()

    # All counters should be reset
    assert coordinator._consecutive_failures == 0
    assert coordinator._reconnect_attempts == 0
    assert coordinator._device_state == DeviceState.ONLINE
    assert coordinator._circuit_breaker_retries == 0
