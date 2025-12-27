"""Test the KKT Kolbe binary sensor platform."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.helpers.entity import EntityCategory

from custom_components.kkt_kolbe.const import DOMAIN
from custom_components.kkt_kolbe import KKTKolbeRuntimeData


@pytest.fixture
def mock_runtime_data():
    """Create mock runtime data."""
    coordinator = MagicMock()
    coordinator.data = {
        "6": True,   # Filter reminder on
    }
    coordinator.last_update_success = True
    coordinator.last_update_success_time = datetime.now()
    coordinator.async_set_data_point = AsyncMock()

    device = MagicMock()
    device.is_connected = True
    device.ip_address = "192.168.1.100"
    device.version = "3.3"

    api_client = MagicMock()
    api_client.is_authenticated = True
    api_client._access_token = "mock_token"

    return KKTKolbeRuntimeData(
        coordinator=coordinator,
        device=device,
        api_client=api_client,
        device_info={"name": "Test Hood", "category": "hood"},
        product_name="hermes_style_hood",
        device_type="hermes_style_hood",
        integration_mode="hybrid",
    )


@pytest.mark.asyncio
async def test_binary_sensor_setup_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test binary sensor platform setup."""
    mock_config_entry.add_to_hass(hass)
    mock_config_entry.runtime_data = mock_runtime_data

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_config_entry.entry_id] = {
        "device_type": "hermes_style_hood",
        "product_name": "hermes_style_hood",
    }

    entities = []

    async def mock_add_entities(new_entities):
        entities.extend(new_entities)

    from custom_components.kkt_kolbe.binary_sensor import async_setup_entry

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Should have at least connection sensor
    assert len(entities) >= 1

    # Check for connection sensor
    connection_sensors = [e for e in entities if "connection" in e.unique_id.lower()]
    assert len(connection_sensors) >= 1


@pytest.mark.asyncio
async def test_connection_sensor_is_on(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test connection sensor is_on property."""
    from custom_components.kkt_kolbe.binary_sensor import KKTKolbeConnectionSensor

    mock_config_entry.add_to_hass(hass)
    mock_config_entry.runtime_data = mock_runtime_data

    sensor = KKTKolbeConnectionSensor(
        mock_runtime_data.coordinator,
        mock_config_entry,
    )

    # Device is connected in mock_runtime_data
    assert sensor.is_on is True


@pytest.mark.asyncio
async def test_connection_sensor_device_class(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test connection sensor device class."""
    from custom_components.kkt_kolbe.binary_sensor import KKTKolbeConnectionSensor

    mock_config_entry.add_to_hass(hass)
    mock_config_entry.runtime_data = mock_runtime_data

    sensor = KKTKolbeConnectionSensor(
        mock_runtime_data.coordinator,
        mock_config_entry,
    )

    assert sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY


@pytest.mark.asyncio
async def test_connection_sensor_entity_category(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test connection sensor entity category."""
    from custom_components.kkt_kolbe.binary_sensor import KKTKolbeConnectionSensor

    mock_config_entry.add_to_hass(hass)
    mock_config_entry.runtime_data = mock_runtime_data

    sensor = KKTKolbeConnectionSensor(
        mock_runtime_data.coordinator,
        mock_config_entry,
    )

    assert sensor.entity_category == EntityCategory.DIAGNOSTIC


@pytest.mark.asyncio
async def test_connection_sensor_extra_attributes(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test connection sensor extra state attributes."""
    from custom_components.kkt_kolbe.binary_sensor import KKTKolbeConnectionSensor

    mock_config_entry.add_to_hass(hass)
    mock_config_entry.runtime_data = mock_runtime_data

    sensor = KKTKolbeConnectionSensor(
        mock_runtime_data.coordinator,
        mock_config_entry,
    )

    attrs = sensor.extra_state_attributes

    assert "integration_mode" in attrs
    assert "device_type" in attrs
    assert attrs["integration_mode"] == "hybrid"


@pytest.mark.asyncio
async def test_api_status_sensor_is_on(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test API status sensor is_on property."""
    from custom_components.kkt_kolbe.binary_sensor import KKTKolbeAPIStatusSensor

    mock_config_entry.add_to_hass(hass)
    mock_config_entry.runtime_data = mock_runtime_data

    sensor = KKTKolbeAPIStatusSensor(
        mock_runtime_data.coordinator,
        mock_config_entry,
    )

    # API client is authenticated in mock_runtime_data
    assert sensor.is_on is True


@pytest.mark.asyncio
async def test_api_status_sensor_device_class(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test API status sensor device class."""
    from custom_components.kkt_kolbe.binary_sensor import KKTKolbeAPIStatusSensor

    mock_config_entry.add_to_hass(hass)
    mock_config_entry.runtime_data = mock_runtime_data

    sensor = KKTKolbeAPIStatusSensor(
        mock_runtime_data.coordinator,
        mock_config_entry,
    )

    assert sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY


@pytest.mark.asyncio
async def test_api_status_sensor_extra_attributes(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test API status sensor extra state attributes."""
    from custom_components.kkt_kolbe.binary_sensor import KKTKolbeAPIStatusSensor

    mock_config_entry.add_to_hass(hass)
    mock_config_entry.runtime_data = mock_runtime_data

    sensor = KKTKolbeAPIStatusSensor(
        mock_runtime_data.coordinator,
        mock_config_entry,
    )

    attrs = sensor.extra_state_attributes

    assert "api_enabled" in attrs
    assert attrs["api_enabled"] is True


@pytest.mark.asyncio
async def test_binary_sensor_unique_id(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test binary sensor unique_id generation."""
    from custom_components.kkt_kolbe.binary_sensor import KKTKolbeConnectionSensor

    mock_config_entry.add_to_hass(hass)
    mock_config_entry.runtime_data = mock_runtime_data

    sensor = KKTKolbeConnectionSensor(
        mock_runtime_data.coordinator,
        mock_config_entry,
    )

    assert sensor.unique_id is not None
    assert "connection" in sensor.unique_id.lower()


@pytest.mark.asyncio
async def test_connection_sensor_icon(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test connection sensor icon based on state."""
    from custom_components.kkt_kolbe.binary_sensor import KKTKolbeConnectionSensor

    mock_config_entry.add_to_hass(hass)
    mock_config_entry.runtime_data = mock_runtime_data

    sensor = KKTKolbeConnectionSensor(
        mock_runtime_data.coordinator,
        mock_config_entry,
    )

    # Connected should show lan-connect icon
    assert "connect" in sensor.icon.lower()
