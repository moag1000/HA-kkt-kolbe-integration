"""Test KKT Kolbe fan platform."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.components.fan import FanEntityFeature

from custom_components.kkt_kolbe.const import DOMAIN


@pytest.mark.asyncio
async def test_fan_initialization(hass: HomeAssistant) -> None:
    """Test fan initialization."""
    from custom_components.kkt_kolbe.fan import KKTKolbeFan
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    mock_coordinator = MagicMock()
    mock_coordinator.data = {"10": "2"}
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
        "name": "Hood Fan",
        "dp": 10,
        "preset_modes": ["low", "middle", "high", "strong"],
    }

    fan = KKTKolbeFan(mock_coordinator, mock_entry, config)

    assert fan.unique_id is not None
    assert FanEntityFeature.SET_SPEED in fan.supported_features
    assert FanEntityFeature.PRESET_MODE in fan.supported_features


@pytest.mark.asyncio
async def test_fan_is_on_property(hass: HomeAssistant) -> None:
    """Test fan is_on property."""
    from custom_components.kkt_kolbe.fan import KKTKolbeFan
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    mock_coordinator = MagicMock()
    mock_coordinator.data = {"1": True}
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
        "name": "Hood Fan",
        "dp": 1,
    }

    fan = KKTKolbeFan(mock_coordinator, mock_entry, config)

    assert fan.is_on is True


@pytest.mark.asyncio
async def test_fan_turn_on(hass: HomeAssistant) -> None:
    """Test turning fan on."""
    from custom_components.kkt_kolbe.fan import KKTKolbeFan
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    mock_coordinator = MagicMock()
    mock_coordinator.data = {"1": False}
    mock_coordinator.hass = hass
    mock_coordinator.async_set_data_point = AsyncMock()
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
        "name": "Hood Fan",
        "dp": 1,
    }

    fan = KKTKolbeFan(mock_coordinator, mock_entry, config)
    await fan.async_turn_on()

    mock_coordinator.async_set_data_point.assert_called_once_with(1, True)


@pytest.mark.asyncio
async def test_fan_turn_off(hass: HomeAssistant) -> None:
    """Test turning fan off."""
    from custom_components.kkt_kolbe.fan import KKTKolbeFan
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    mock_coordinator = MagicMock()
    mock_coordinator.data = {"1": True}
    mock_coordinator.hass = hass
    mock_coordinator.async_set_data_point = AsyncMock()
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
        "name": "Hood Fan",
        "dp": 1,
    }

    fan = KKTKolbeFan(mock_coordinator, mock_entry, config)
    await fan.async_turn_off()

    mock_coordinator.async_set_data_point.assert_called_once_with(1, False)


@pytest.mark.asyncio
async def test_fan_preset_modes(hass: HomeAssistant) -> None:
    """Test fan preset mode setting."""
    from custom_components.kkt_kolbe.fan import KKTKolbeFan
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    mock_coordinator = MagicMock()
    mock_coordinator.data = {"10": "2"}
    mock_coordinator.hass = hass
    mock_coordinator.async_set_data_point = AsyncMock()
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
        "name": "Hood Fan",
        "dp": 10,
        "preset_modes": ["low", "middle", "high", "strong"],
    }

    fan = KKTKolbeFan(mock_coordinator, mock_entry, config)
    await fan.async_set_preset_mode("high")

    mock_coordinator.async_set_data_point.assert_called_once()
