"""Test the KKT Kolbe fan platform."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.components.fan import FanEntityFeature

from custom_components.kkt_kolbe.const import DOMAIN
from custom_components.kkt_kolbe import KKTKolbeRuntimeData


@pytest.fixture
def mock_runtime_data():
    """Create mock runtime data."""
    coordinator = MagicMock()
    coordinator.data = {
        1: True,     # Power on
        "1": True,   # Also string key
        10: "3",     # Fan speed at level 3
        "10": "3",   # Also string key
        12: 3,       # Numeric fan speed
        "12": 3,     # Also string key
    }
    coordinator.last_update_success = True
    coordinator.async_set_data_point = AsyncMock()

    return KKTKolbeRuntimeData(
        coordinator=coordinator,
        device=MagicMock(),
        api_client=None,
        device_info={"name": "Test Hood", "category": "hood"},
        product_name="hermes_style_hood",
        device_type="hermes_style_hood",
        integration_mode="manual",
    )


@pytest.mark.asyncio
async def test_domain_constant(hass: HomeAssistant) -> None:
    """Test the domain constant is correct."""
    assert DOMAIN == "kkt_kolbe"


@pytest.mark.asyncio
async def test_fan_setup_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test fan platform setup."""
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

    from custom_components.kkt_kolbe.fan import async_setup_entry

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Should have at least one fan entity
    assert len(entities) >= 1


@pytest.mark.asyncio
async def test_fan_is_on(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test fan is_on property."""
    from custom_components.kkt_kolbe.fan import KKTKolbeFan

    mock_config_entry.add_to_hass(hass)

    config = {
        "name": "Range Hood Fan",
        "power_dp": 1,
        "speed_dp": 10,
        "speed_list": ["off", "1", "2", "3", "4"],
    }

    fan = KKTKolbeFan(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # Power DP 1 is True in mock_runtime_data
    assert fan.is_on is True


@pytest.mark.asyncio
async def test_fan_turn_on(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test turning on the fan."""
    from custom_components.kkt_kolbe.fan import KKTKolbeFan

    mock_config_entry.add_to_hass(hass)

    config = {
        "name": "Range Hood Fan",
        "power_dp": 1,
        "speed_dp": 10,
        "speed_list": ["off", "1", "2", "3", "4"],
    }

    fan = KKTKolbeFan(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    await fan.async_turn_on()

    mock_runtime_data.coordinator.async_set_data_point.assert_called()


@pytest.mark.asyncio
async def test_fan_turn_off(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test turning off the fan."""
    from custom_components.kkt_kolbe.fan import KKTKolbeFan

    mock_config_entry.add_to_hass(hass)

    config = {
        "name": "Range Hood Fan",
        "power_dp": 1,
        "speed_dp": 10,
        "speed_list": ["off", "1", "2", "3", "4"],
    }

    fan = KKTKolbeFan(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    await fan.async_turn_off()

    mock_runtime_data.coordinator.async_set_data_point.assert_called()


@pytest.mark.asyncio
async def test_fan_set_percentage(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test setting fan percentage."""
    from custom_components.kkt_kolbe.fan import KKTKolbeFan

    mock_config_entry.add_to_hass(hass)

    config = {
        "name": "Range Hood Fan",
        "power_dp": 1,
        "speed_dp": 10,
        "speed_list": ["off", "1", "2", "3", "4"],
    }

    fan = KKTKolbeFan(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # Set to 75%
    await fan.async_set_percentage(75)

    mock_runtime_data.coordinator.async_set_data_point.assert_called()


@pytest.mark.asyncio
async def test_fan_percentage(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test fan percentage property."""
    from custom_components.kkt_kolbe.fan import KKTKolbeFan

    mock_config_entry.add_to_hass(hass)

    config = {
        "name": "Range Hood Fan",
        "power_dp": 1,
        "speed_dp": 10,
        "speed_list": ["off", "1", "2", "3", "4"],
    }

    fan = KKTKolbeFan(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # DP 10 is "3" in mock_runtime_data (speed level 3 out of 4)
    percentage = fan.percentage
    assert percentage is not None
    assert percentage > 0


@pytest.mark.asyncio
async def test_fan_speed_count(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test fan speed count property."""
    from custom_components.kkt_kolbe.fan import KKTKolbeFan

    mock_config_entry.add_to_hass(hass)

    config = {
        "name": "Range Hood Fan",
        "power_dp": 1,
        "speed_dp": 10,
        "speed_list": ["off", "1", "2", "3", "4"],
    }

    fan = KKTKolbeFan(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # 4 non-off speeds
    assert fan.speed_count == 4


@pytest.mark.asyncio
async def test_fan_supported_features(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test fan supported features."""
    from custom_components.kkt_kolbe.fan import KKTKolbeFan

    mock_config_entry.add_to_hass(hass)

    config = {
        "name": "Range Hood Fan",
        "power_dp": 1,
        "speed_dp": 10,
        "speed_list": ["off", "1", "2", "3", "4"],
    }

    fan = KKTKolbeFan(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # Should support SET_SPEED
    assert fan.supported_features & FanEntityFeature.SET_SPEED


@pytest.mark.asyncio
async def test_fan_unique_id(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test fan unique_id generation."""
    from custom_components.kkt_kolbe.fan import KKTKolbeFan

    mock_config_entry.add_to_hass(hass)

    config = {
        "name": "Range Hood Fan",
        "power_dp": 1,
        "speed_dp": 10,
        "speed_list": ["off", "1", "2", "3", "4"],
    }

    fan = KKTKolbeFan(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    assert fan.unique_id is not None
    assert mock_config_entry.entry_id in fan.unique_id
    assert "fan" in fan.unique_id
