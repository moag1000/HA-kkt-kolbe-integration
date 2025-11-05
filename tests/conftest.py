"""Fixtures for KKT Kolbe integration tests."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.kkt_kolbe.const import DOMAIN


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
def mock_config_entry():
    """Mock ConfigEntry for testing."""
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.data_entry_flow import FlowResultType

    # Create a real ConfigEntry mock that can be added to hass
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test KKT Device",
        data={
            "device_id": "test_device_id_12345",
            "ip_address": "192.168.1.100",
            "local_key": "test_local_key_12345",
            "integration_mode": "manual",
            "product_name": "KKT DH9509NP",
        },
        options={},
        source="user",
        unique_id="test_device_id_12345",
    )

    return entry


@pytest.fixture
async def hass():
    """Create a Home Assistant instance for testing."""
    from homeassistant.core import HomeAssistant
    from homeassistant.config_entries import ConfigEntries
    from homeassistant.helpers import entity_registry as er, device_registry as dr

    hass = HomeAssistant("/test/config")
    hass.config_entries = ConfigEntries(hass, {})

    # Setup required components
    await async_setup_component(hass, "homeassistant", {})

    # Initialize registries
    er.async_get(hass)
    dr.async_get(hass)

    yield hass

    await hass.async_stop()


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
