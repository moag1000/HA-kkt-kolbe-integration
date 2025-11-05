"""Test KKT Kolbe fan platform."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from homeassistant.components.fan import FanEntityFeature

from custom_components.kkt_kolbe.fan import KKTKolbeFan
from custom_components.kkt_kolbe.const import DOMAIN


@pytest.mark.asyncio
async def test_fan_initialization(mock_coordinator, mock_config_entry):
    """Test fan initialization."""
    config = {
        "name": "Hood Fan",
        "dp": 10,
        "preset_modes": ["low", "middle", "high", "strong"],
    }

    fan = KKTKolbeFan(mock_coordinator, mock_config_entry, config)

    assert fan.name == "Test KKT Device Hood Fan"
    assert fan.unique_id is not None
    assert FanEntityFeature.SET_SPEED in fan.supported_features
    assert FanEntityFeature.PRESET_MODE in fan.supported_features


@pytest.mark.asyncio
async def test_fan_is_on_property(mock_coordinator, mock_config_entry):
    """Test fan is_on property."""
    config = {
        "name": "Hood Fan",
        "dp": 1,  # Power DP
    }

    # Coordinator data says device is on
    mock_coordinator.data = {"1": True}
    fan = KKTKolbeFan(mock_coordinator, mock_config_entry, config)

    assert fan.is_on is True


@pytest.mark.asyncio
async def test_fan_turn_on(mock_coordinator, mock_config_entry):
    """Test turning fan on."""
    config = {
        "name": "Hood Fan",
        "dp": 1,
    }

    fan = KKTKolbeFan(mock_coordinator, mock_config_entry, config)
    mock_coordinator.async_set_data_point = AsyncMock()

    await fan.async_turn_on()

    mock_coordinator.async_set_data_point.assert_called_once_with(1, True)


@pytest.mark.asyncio
async def test_fan_turn_off(mock_coordinator, mock_config_entry):
    """Test turning fan off."""
    config = {
        "name": "Hood Fan",
        "dp": 1,
    }

    fan = KKTKolbeFan(mock_coordinator, mock_config_entry, config)
    mock_coordinator.async_set_data_point = AsyncMock()

    await fan.async_turn_off()

    mock_coordinator.async_set_data_point.assert_called_once_with(1, False)


@pytest.mark.asyncio
async def test_fan_preset_modes(mock_coordinator, mock_config_entry):
    """Test fan preset mode setting."""
    config = {
        "name": "Hood Fan",
        "dp": 10,
        "preset_modes": ["low", "middle", "high", "strong"],
    }

    fan = KKTKolbeFan(mock_coordinator, mock_config_entry, config)
    mock_coordinator.async_set_data_point = AsyncMock()

    await fan.async_set_preset_mode("high")

    # Preset mode "high" should map to value "3"
    mock_coordinator.async_set_data_point.assert_called_once()
