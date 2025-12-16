"""Test KKT Kolbe sensor platform."""
import pytest
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from custom_components.kkt_kolbe.const import DOMAIN


@pytest.mark.asyncio
async def test_sensor_initialization(hass: HomeAssistant) -> None:
    """Test sensor initialization."""
    from custom_components.kkt_kolbe.sensor import KKTKolbeSensor
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    mock_coordinator = MagicMock()
    mock_coordinator.data = {"14": 100}
    mock_coordinator.hass = hass
    mock_coordinator.device_info = {
        "identifiers": {(DOMAIN, "test_device")},
        "name": "Test Device",
        "manufacturer": "KKT Kolbe",
    }

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Device",
        data={"device_id": "test_device"},
        unique_id="test_device",
    )

    config = {
        "name": "Test Sensor",
        "dp": 14,
        "device_class": "duration",
        "state_class": "total",
        "unit_of_measurement": "h",
    }

    sensor = KKTKolbeSensor(mock_coordinator, mock_entry, config)

    assert sensor.unique_id is not None
    assert sensor.state_class == "total"
    assert sensor.native_unit_of_measurement == "h"


@pytest.mark.asyncio
async def test_sensor_diagnostic_category(hass: HomeAssistant) -> None:
    """Test that diagnostic sensors get correct entity category."""
    from custom_components.kkt_kolbe.sensor import KKTKolbeSensor
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    mock_coordinator = MagicMock()
    mock_coordinator.data = {"14": 100}
    mock_coordinator.hass = hass
    mock_coordinator.device_info = {
        "identifiers": {(DOMAIN, "test_device")},
        "name": "Test Device",
        "manufacturer": "KKT Kolbe",
    }

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Device",
        data={"device_id": "test_device"},
        unique_id="test_device",
    )

    config = {
        "name": "Filter Hours",
        "dp": 14,
    }

    sensor = KKTKolbeSensor(mock_coordinator, mock_entry, config)
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC


@pytest.mark.asyncio
async def test_sensor_non_diagnostic_category(hass: HomeAssistant) -> None:
    """Test that non-diagnostic sensors don't get entity category."""
    from custom_components.kkt_kolbe.sensor import KKTKolbeSensor
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    mock_coordinator = MagicMock()
    mock_coordinator.data = {"5": 128}
    mock_coordinator.hass = hass
    mock_coordinator.device_info = {
        "identifiers": {(DOMAIN, "test_device")},
        "name": "Test Device",
        "manufacturer": "KKT Kolbe",
    }

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Device",
        data={"device_id": "test_device"},
        unique_id="test_device",
    )

    config = {
        "name": "Light Brightness",
        "dp": 5,
    }

    sensor = KKTKolbeSensor(mock_coordinator, mock_entry, config)
    assert (
        not hasattr(sensor, "_attr_entity_category")
        or sensor._attr_entity_category is None
    )


@pytest.mark.asyncio
async def test_sensor_state_from_coordinator(hass: HomeAssistant) -> None:
    """Test sensor reads state from coordinator."""
    from custom_components.kkt_kolbe.sensor import KKTKolbeSensor
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    mock_coordinator = MagicMock()
    mock_coordinator.data = {"14": 100}
    mock_coordinator.hass = hass
    mock_coordinator.device_info = {
        "identifiers": {(DOMAIN, "test_device")},
        "name": "Test Device",
        "manufacturer": "KKT Kolbe",
    }

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Device",
        data={"device_id": "test_device"},
        unique_id="test_device",
    )

    config = {
        "name": "Filter Hours",
        "dp": 14,
    }

    sensor = KKTKolbeSensor(mock_coordinator, mock_entry, config)
    assert sensor.native_value == 100
