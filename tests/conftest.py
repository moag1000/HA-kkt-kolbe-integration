"""Fixtures for KKT Kolbe integration tests."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kkt_kolbe.const import DOMAIN


@pytest.fixture
def mock_tuya_device():
    """Mock TinyTuya device for testing."""
    with patch("tinytuya.Device") as mock:
        device = MagicMock()
        device.status.return_value = {
            "dps": {
                "1": True,
                "4": True,
                "5": 128,
                "10": "2",
                "11": 2,
                "13": 0,
                "14": 100,
            }
        }
        device.set_value.return_value = None
        device.close.return_value = None
        mock.return_value = device
        yield mock


@pytest.fixture
def mock_config_entry():
    """Mock ConfigEntry for testing."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test KKT Device",
        data={
            "device_id": "test_device_id_12345",
            "ip_address": "192.168.1.100",
            "local_key": "test_local_key_1",
            "integration_mode": "manual",
            "product_name": "KKT DH9509NP",
        },
        unique_id="test_device_id_12345",
    )


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


@pytest.fixture
def mock_setup_entry():
    """Mock async_setup_entry."""
    with patch(
        "custom_components.kkt_kolbe.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup
