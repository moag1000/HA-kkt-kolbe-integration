"""Fixtures for KKT Kolbe integration tests."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from custom_components.kkt_kolbe.const import DOMAIN

# Use the hass fixture from pytest-homeassistant-custom-component
# Do NOT override it with a custom fixture


@pytest.fixture
def mock_tuya_device():
    """Mock TinyTuya device for testing."""
    with patch("custom_components.kkt_kolbe.tuya_device.tinytuya.Device") as mock:
        device = MagicMock()
        # Simulate successful connection and status
        device.status.return_value = {
            "dps": {
                "1": True,   # Power
                "4": True,   # Light
                "5": 128,    # Light brightness
                "10": "2",   # Fan speed
                "11": 2,     # Fan speed setting
                "13": 0,     # Countdown
                "14": 100,   # Filter hours
            }
        }
        device.set_value.return_value = None
        device.close.return_value = None
        mock.return_value = device
        yield mock


@pytest.fixture
def mock_config_entry(hass):
    """Mock ConfigEntry for testing."""
    from homeassistant.config_entries import ConfigEntry

    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test KKT Device",
        data={
            "device_id": "test_device_id_12345",
            "ip_address": "192.168.1.100",
            "local_key": "test_local_key_1",
            "integration_mode": "manual",
            "product_name": "KKT DH9509NP",
        },
        options={},
        source="user",
        unique_id="test_device_id_12345",
    )

    return entry


@pytest.fixture
def mock_coordinator():
    """Mock coordinator for testing."""
    coordinator = MagicMock()
    coordinator.data = {
        "1": True,
        "4": True,
        "5": 128,
        "10": "2",
        "11": 2,
        "13": 0,
        "14": 100,
    }
    coordinator.last_update_success = True
    coordinator.async_refresh = AsyncMock()
    coordinator.device_info = {
        "identifiers": {(DOMAIN, "test_device_id_12345")},
        "name": "Test KKT Device",
        "manufacturer": "KKT Kolbe",
        "model": "DH9509NP",
    }

    return coordinator
