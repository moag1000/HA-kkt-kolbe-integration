"""Test KKT Kolbe diagnostics."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime

from homeassistant.core import HomeAssistant

from custom_components.kkt_kolbe.diagnostics import async_get_config_entry_diagnostics
from custom_components.kkt_kolbe.const import DOMAIN


@pytest.mark.asyncio
async def test_diagnostics_basic(hass: HomeAssistant, mock_config_entry) -> None:
    """Test basic diagnostics data."""
    mock_coordinator = MagicMock()
    mock_coordinator.last_update_success = True
    mock_coordinator.last_update_success_time = datetime.now()
    mock_coordinator.update_interval.total_seconds.return_value = 30
    mock_coordinator.data = {"1": True, "4": True, "14": 100}

    mock_device = MagicMock()
    mock_device.is_connected = True
    mock_device.version = "3.3"
    mock_device.device_id = "test_device_12345"
    mock_device.ip_address = "192.168.1.100"

    hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {
            "coordinator": mock_coordinator,
            "device": mock_device,
            "api_client": None,
            "integration_mode": "manual",
            "product_name": "DH9509NP",
            "device_info": {
                "manufacturer": "KKT Kolbe",
                "model": "DH9509NP",
            },
        }
    }

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert diagnostics["entry"]["title"] == "Test KKT Device"
    assert diagnostics["entry"]["unique_id"] == "test_device_id_12345"
    assert diagnostics["config"]["integration_mode"] == "manual"
    assert diagnostics["config"]["product_name"] == "DH9509NP"
    assert diagnostics["coordinator"]["last_update_success"] is True
    assert diagnostics["coordinator"]["data_point_count"] == 3


@pytest.mark.asyncio
async def test_diagnostics_with_api(hass: HomeAssistant, mock_config_entry) -> None:
    """Test diagnostics with API client."""
    mock_config_entry.data = {
        **mock_config_entry.data,
        "api_enabled": True,
        "api_client_id": "test_client_id",
        "api_client_secret": "test_secret",
        "api_endpoint": "https://openapi.tuyaeu.com",
    }

    mock_coordinator = MagicMock()
    mock_coordinator.last_update_success = True
    mock_coordinator.last_update_success_time = datetime.now()
    mock_coordinator.update_interval.total_seconds.return_value = 30
    mock_coordinator.data = {}

    mock_api_client = MagicMock()

    hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {
            "coordinator": mock_coordinator,
            "device": None,
            "api_client": mock_api_client,
            "integration_mode": "api_discovery",
            "product_name": "DH9509NP",
            "device_info": {},
        }
    }

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert diagnostics["api"]["enabled"] is True
    assert diagnostics["api"]["endpoint"] == "https://openapi.tuyaeu.com"
    assert diagnostics["api"]["has_client_id"] is True
    assert diagnostics["api"]["has_client_secret"] is True


@pytest.mark.asyncio
async def test_diagnostics_redacts_sensitive_data(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test that sensitive data is redacted."""
    mock_coordinator = MagicMock()
    mock_coordinator.last_update_success = True
    mock_coordinator.last_update_success_time = datetime.now()
    mock_coordinator.update_interval.total_seconds.return_value = 30
    mock_coordinator.data = {}

    hass.data[DOMAIN] = {
        mock_config_entry.entry_id: {
            "coordinator": mock_coordinator,
            "device": None,
            "api_client": None,
            "integration_mode": "manual",
            "product_name": "unknown",
            "device_info": {},
        }
    }

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert "local_key" not in diagnostics["config"]
    assert "api_client_secret" not in diagnostics["config"]
    assert diagnostics["config"]["device_id"].endswith("...")
    assert diagnostics["config"]["has_local_key"] is True
