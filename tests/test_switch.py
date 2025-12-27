"""Test the KKT Kolbe switch platform."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

from custom_components.kkt_kolbe.const import DOMAIN
from custom_components.kkt_kolbe import KKTKolbeRuntimeData


@pytest.fixture
def mock_runtime_data():
    """Create mock runtime data."""
    coordinator = MagicMock()
    coordinator.data = {
        1: True,     # Power on
        "1": True,   # Also string key
        6: False,    # Filter reminder off
        "6": False,  # Also string key
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
async def test_switch_setup_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test switch platform setup."""
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

    from custom_components.kkt_kolbe.switch import async_setup_entry

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Should have at least one switch entity (Power)
    assert len(entities) > 0


@pytest.mark.asyncio
async def test_switch_turn_on(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test turning on a switch."""
    from custom_components.kkt_kolbe.switch import KKTKolbeSwitch

    config = {
        "dp": 1,
        "name": "Power",
        "device_class": "switch",
    }

    switch = KKTKolbeSwitch(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    await switch.async_turn_on()

    mock_runtime_data.coordinator.async_set_data_point.assert_called_once_with(1, True)


@pytest.mark.asyncio
async def test_switch_turn_off(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test turning off a switch."""
    from custom_components.kkt_kolbe.switch import KKTKolbeSwitch

    config = {
        "dp": 1,
        "name": "Power",
        "device_class": "switch",
    }

    switch = KKTKolbeSwitch(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    await switch.async_turn_off()

    mock_runtime_data.coordinator.async_set_data_point.assert_called_once_with(1, False)


@pytest.mark.asyncio
async def test_switch_is_on(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test switch is_on property."""
    from custom_components.kkt_kolbe.switch import KKTKolbeSwitch

    config = {
        "dp": 1,
        "name": "Power",
    }

    switch = KKTKolbeSwitch(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # DP 1 is True in mock_runtime_data
    assert switch.is_on is True


@pytest.mark.asyncio
async def test_switch_is_off(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test switch is_on property when off."""
    from custom_components.kkt_kolbe.switch import KKTKolbeSwitch

    config = {
        "dp": 6,
        "name": "Filter Reminder",
    }

    switch = KKTKolbeSwitch(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # DP 6 is False in mock_runtime_data
    assert switch.is_on is False


@pytest.mark.asyncio
async def test_switch_unique_id(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test switch unique_id generation."""
    from custom_components.kkt_kolbe.switch import KKTKolbeSwitch

    config = {
        "dp": 1,
        "name": "Power",
    }

    switch = KKTKolbeSwitch(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    assert switch.unique_id is not None
    assert mock_config_entry.entry_id in switch.unique_id
    assert "switch" in switch.unique_id
