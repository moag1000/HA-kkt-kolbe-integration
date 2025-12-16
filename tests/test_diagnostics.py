"""Test KKT Kolbe diagnostics."""
import pytest
from unittest.mock import MagicMock
from datetime import datetime

from homeassistant.core import HomeAssistant

from custom_components.kkt_kolbe.const import DOMAIN


@pytest.mark.asyncio
async def test_diagnostics_module_import(hass: HomeAssistant) -> None:
    """Test that diagnostics module can be imported."""
    from custom_components.kkt_kolbe import diagnostics
    assert hasattr(diagnostics, "async_get_config_entry_diagnostics")


@pytest.mark.asyncio
async def test_diagnostics_basic(hass: HomeAssistant, mock_config_entry) -> None:
    """Test basic diagnostics data."""
    from custom_components.kkt_kolbe.diagnostics import async_get_config_entry_diagnostics

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
    assert diagnostics["config"]["integration_mode"] == "manual"
    assert diagnostics["coordinator"]["last_update_success"] is True


@pytest.mark.asyncio
async def test_diagnostics_redacts_sensitive_data(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test that sensitive data is redacted."""
    from custom_components.kkt_kolbe.diagnostics import async_get_config_entry_diagnostics

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
