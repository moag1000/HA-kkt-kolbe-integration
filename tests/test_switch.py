"""Test the KKT Kolbe switch platform."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry

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

    def mock_add_entities(new_entities):
        """Sync mock for AddEntitiesCallback."""
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


# =============== FAN SUPPRESS TESTS ===============


@pytest.mark.asyncio
async def test_power_switch_with_fan_suppress(
    hass: HomeAssistant,
) -> None:
    """Test that DP 1 power switch sends fan-off when option is enabled.

    When disable_fan_auto_start=True and the power switch (DP 1) is turned on,
    a fan-off command should be sent after the power-on.
    """
    from custom_components.kkt_kolbe.switch import KKTKolbeSwitch

    coordinator = MagicMock()
    coordinator.data = {1: False, "1": False}
    coordinator.last_update_success = True
    coordinator.async_set_data_point = AsyncMock()

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hood",
        data={
            "device_id": "bf735dfe2ad64fba7cpyhn",
            "ip_address": "192.168.1.100",
            "local_key": "1234567890abcdef",
            "product_name": "hermes_style_hood",
            "device_type": "hermes_style_hood",
        },
        options={"disable_fan_auto_start": True},
        unique_id="bf735dfe2ad64fba7cpyhn",
    )
    entry.add_to_hass(hass)

    config = {"dp": 1, "name": "Power", "device_class": "switch"}
    switch = KKTKolbeSwitch(coordinator, entry, config)

    await switch.async_turn_on()

    calls = coordinator.async_set_data_point.call_args_list
    # Expected: DP 1 = True (power on), then DP 10 = "off" (fan suppress)
    assert call(1, True) in calls, f"Expected power-on call, got: {calls}"
    assert call(10, "off") in calls, f"Expected fan suppress call DP 10='off', got: {calls}"


@pytest.mark.asyncio
async def test_power_switch_without_fan_suppress(
    hass: HomeAssistant,
) -> None:
    """Test that DP 1 power switch does NOT send fan-off when option is disabled.

    When disable_fan_auto_start=False (default), no fan-off should be sent.
    """
    from custom_components.kkt_kolbe.switch import KKTKolbeSwitch

    coordinator = MagicMock()
    coordinator.data = {1: False, "1": False}
    coordinator.last_update_success = True
    coordinator.async_set_data_point = AsyncMock()

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hood",
        data={
            "device_id": "bf735dfe2ad64fba7cpyhn",
            "ip_address": "192.168.1.100",
            "local_key": "1234567890abcdef",
            "product_name": "hermes_style_hood",
            "device_type": "hermes_style_hood",
        },
        options={"disable_fan_auto_start": False},
        unique_id="bf735dfe2ad64fba7cpyhn_nosuppress",
    )
    entry.add_to_hass(hass)

    config = {"dp": 1, "name": "Power", "device_class": "switch"}
    switch = KKTKolbeSwitch(coordinator, entry, config)

    await switch.async_turn_on()

    calls = coordinator.async_set_data_point.call_args_list
    # Expected: only DP 1 = True (power on), NO fan-off
    assert call(1, True) in calls, f"Expected power-on call, got: {calls}"
    assert call(10, "off") not in calls, f"Should NOT send fan-off, got: {calls}"


@pytest.mark.asyncio
async def test_non_power_switch_ignores_fan_suppress(
    hass: HomeAssistant,
) -> None:
    """Test that non-DP-1 switches do NOT trigger fan suppress.

    Even with disable_fan_auto_start=True, only the power switch (DP 1)
    should trigger fan suppress, not other switches like filter reminder (DP 6).
    """
    from custom_components.kkt_kolbe.switch import KKTKolbeSwitch

    coordinator = MagicMock()
    coordinator.data = {6: False, "6": False}
    coordinator.last_update_success = True
    coordinator.async_set_data_point = AsyncMock()

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hood",
        data={
            "device_id": "bf735dfe2ad64fba7cpyhn",
            "ip_address": "192.168.1.100",
            "local_key": "1234567890abcdef",
            "product_name": "hermes_style_hood",
            "device_type": "hermes_style_hood",
        },
        options={"disable_fan_auto_start": True},
        unique_id="bf735dfe2ad64fba7cpyhn_dp6",
    )
    entry.add_to_hass(hass)

    config = {"dp": 6, "name": "Filter Reminder", "device_class": "switch"}
    switch = KKTKolbeSwitch(coordinator, entry, config)

    await switch.async_turn_on()

    calls = coordinator.async_set_data_point.call_args_list
    # Expected: only DP 6 = True, NO fan-off
    assert len(calls) == 1, f"Expected only 1 call (DP 6=True), got: {calls}"
    assert call(6, True) in calls, f"Expected DP 6 call, got: {calls}"
