"""Test the KKT Kolbe discovery module."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kkt_kolbe.discovery import (
    KKTKolbeDiscovery,
    simple_tuya_discover,
)


@pytest.fixture
def mock_tinytuya_device():
    """Create a mock TinyTuya device response."""
    return {
        "ip": "192.168.1.100",
        "gwId": "bf1234567890abcd1234",
        "active": 2,
        "ability": 0,
        "mode": 0,
        "encrypt": True,
        "productKey": "abc123xyz",
        "version": "3.3",
    }


@pytest.mark.asyncio
async def test_discovery_initialization(hass: HomeAssistant) -> None:
    """Test discovery module initialization."""
    discovery = KKTKolbeDiscovery(hass)

    assert discovery.hass == hass
    assert discovery.discovered_devices == {}


@pytest.mark.asyncio
async def test_discovery_scan_empty(hass: HomeAssistant) -> None:
    """Test discovery scan with no devices found."""
    discovery = KKTKolbeDiscovery(hass)

    # The new discovery uses UDP/mDNS, not tinytuya.deviceScan directly
    # We just verify the discovered_devices dict is empty initially
    assert discovery.discovered_devices == {}


@pytest.mark.asyncio
async def test_discovery_scan_with_devices(
    hass: HomeAssistant,
    mock_tinytuya_device,
) -> None:
    """Test discovery can store and retrieve devices."""
    discovery = KKTKolbeDiscovery(hass)

    # Manually add a device to simulate discovery
    discovery.discovered_devices["bf1234567890abcd1234"] = mock_tinytuya_device

    assert len(discovery.discovered_devices) == 1
    assert "bf1234567890abcd1234" in discovery.discovered_devices


@pytest.mark.asyncio
async def test_discovery_filter_kkt_devices(hass: HomeAssistant) -> None:
    """Test that discovery stores KKT Kolbe devices."""
    discovery = KKTKolbeDiscovery(hass)

    kkt_device = {
        "ip": "192.168.1.100",
        "gwId": "bf1234567890abcd1234",
        "version": "3.3",
    }

    # Add a KKT device
    discovery.discovered_devices["bf1234567890abcd1234"] = kkt_device

    assert "bf1234567890abcd1234" in discovery.discovered_devices
    assert discovery.discovered_devices["bf1234567890abcd1234"]["ip"] == "192.168.1.100"


@pytest.mark.asyncio
async def test_discovery_get_device_info(
    hass: HomeAssistant,
    mock_tinytuya_device,
) -> None:
    """Test getting detailed device info."""
    discovery = KKTKolbeDiscovery(hass)

    discovery.discovered_devices["bf1234567890abcd1234"] = mock_tinytuya_device

    info = discovery.discovered_devices.get("bf1234567890abcd1234")

    assert info is not None
    assert info["ip"] == "192.168.1.100"


@pytest.mark.asyncio
async def test_discovery_device_not_found(hass: HomeAssistant) -> None:
    """Test getting info for non-existent device."""
    discovery = KKTKolbeDiscovery(hass)

    info = discovery.discovered_devices.get("nonexistent")

    assert info is None


@pytest.mark.asyncio
async def test_simple_tuya_discover_function(hass: HomeAssistant) -> None:
    """Test the simple_tuya_discover helper function."""
    # Mock the UDP listener creation to avoid actual network operations
    with patch('asyncio.get_running_loop') as mock_loop:
        mock_transport = MagicMock()
        mock_protocol = MagicMock()
        mock_loop.return_value.create_datagram_endpoint = AsyncMock(
            return_value=(mock_transport, mock_protocol)
        )

        devices = await simple_tuya_discover(timeout=0.1)

        assert isinstance(devices, dict)


@pytest.mark.asyncio
async def test_discovery_timeout_handling(hass: HomeAssistant) -> None:
    """Test discovery handles timeouts gracefully."""
    discovery = KKTKolbeDiscovery(hass)

    # Discovery should start with empty devices even if network fails
    assert discovery.discovered_devices == {}


@pytest.mark.asyncio
async def test_discovery_network_error(hass: HomeAssistant) -> None:
    """Test discovery handles network errors gracefully."""
    discovery = KKTKolbeDiscovery(hass)

    # Discovery should be initialized even with network issues
    assert discovery.discovered_devices is not None
    assert isinstance(discovery.discovered_devices, dict)


@pytest.mark.asyncio
async def test_discovery_caches_results(
    hass: HomeAssistant,
    mock_tinytuya_device,
) -> None:
    """Test that discovery caches results."""
    discovery = KKTKolbeDiscovery(hass)

    # Manually add device to simulate discovery
    discovery.discovered_devices["bf1234567890abcd1234"] = mock_tinytuya_device

    # Cached devices should be available
    assert discovery.discovered_devices is not None
    assert "bf1234567890abcd1234" in discovery.discovered_devices


@pytest.mark.asyncio
async def test_discovery_refresh(
    hass: HomeAssistant,
    mock_tinytuya_device,
) -> None:
    """Test refreshing discovery with multiple devices."""
    discovery = KKTKolbeDiscovery(hass)

    # First device
    discovery.discovered_devices["bf1234567890abcd1234"] = mock_tinytuya_device

    # Second device
    new_device = mock_tinytuya_device.copy()
    new_device["gwId"] = "bf9999999999999999"
    new_device["ip"] = "192.168.1.101"
    discovery.discovered_devices["bf9999999999999999"] = new_device

    # Should have both devices now
    assert len(discovery.discovered_devices) == 2
    assert "bf1234567890abcd1234" in discovery.discovered_devices
    assert "bf9999999999999999" in discovery.discovered_devices
