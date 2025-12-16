"""Test KKT Kolbe sensor platform."""
import pytest
from unittest.mock import MagicMock
from homeassistant.helpers.entity import EntityCategory

from custom_components.kkt_kolbe.sensor import KKTKolbeSensor


@pytest.mark.asyncio
async def test_sensor_initialization(mock_coordinator, mock_config_entry):
    """Test sensor initialization."""
    config = {
        "name": "Test Sensor",
        "dp": 14,
        "device_class": "duration",
        "state_class": "total",
        "unit_of_measurement": "h",
    }

    sensor = KKTKolbeSensor(mock_coordinator, mock_config_entry, config)

    assert sensor.name == "Test KKT Device Test Sensor"
    assert sensor.unique_id is not None
    assert sensor.state_class == "total"
    assert sensor.native_unit_of_measurement == "h"


@pytest.mark.asyncio
async def test_sensor_diagnostic_category(mock_coordinator, mock_config_entry):
    """Test that diagnostic sensors get correct entity category."""
    # Filter hours sensor (DP 14) should be diagnostic
    config = {
        "name": "Filter Hours",
        "dp": 14,
    }

    sensor = KKTKolbeSensor(mock_coordinator, mock_config_entry, config)
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC


@pytest.mark.asyncio
async def test_sensor_non_diagnostic_category(mock_coordinator, mock_config_entry):
    """Test that non-diagnostic sensors don't get entity category."""
    # Regular sensor (DP 5) should not be diagnostic
    config = {
        "name": "Light Brightness",
        "dp": 5,
    }

    sensor = KKTKolbeSensor(mock_coordinator, mock_config_entry, config)
    assert not hasattr(sensor, "_attr_entity_category") or sensor._attr_entity_category is None


@pytest.mark.asyncio
async def test_sensor_state_from_coordinator(mock_coordinator, mock_config_entry):
    """Test sensor reads state from coordinator."""
    config = {
        "name": "Filter Hours",
        "dp": 14,
    }

    sensor = KKTKolbeSensor(mock_coordinator, mock_config_entry, config)
    assert sensor.native_value == 100  # From mock_coordinator fixture
