"""Test the KKT Kolbe light platform."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_EFFECT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kkt_kolbe.const import DOMAIN
from custom_components.kkt_kolbe import KKTKolbeRuntimeData


@pytest.fixture
def mock_runtime_data():
    """Create mock runtime data."""
    coordinator = MagicMock()
    coordinator.data = {
        1: True,     # Hood power on (required for Auto-Power-On feature)
        "1": True,   # Also string key
        4: True,     # Light on
        "4": True,   # Also string key
        5: 128,      # Brightness at 50%
        "5": 128,    # Also string key
        101: 2,      # Effect mode
        "101": 2,    # Also string key
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
async def test_light_setup_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test light platform setup."""
    mock_config_entry.add_to_hass(hass)
    mock_config_entry.runtime_data = mock_runtime_data

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_config_entry.entry_id] = {
        "device_type": "hermes_style_hood",
        "product_name": "hermes_style_hood",
    }

    entities = []

    def mock_add_entities(new_entities):
        entities.extend(new_entities)

    from custom_components.kkt_kolbe.light import async_setup_entry

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Should have light entities if device has light configuration
    # (depends on device_types configuration)


@pytest.mark.asyncio
async def test_light_is_on(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test light is_on property."""
    from custom_components.kkt_kolbe.light import KKTKolbeLight

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 4,
        "name": "Light",
    }

    light = KKTKolbeLight(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # DP 4 is True in mock_runtime_data
    assert light.is_on is True


@pytest.mark.asyncio
async def test_light_turn_on(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test turning on a light."""
    from custom_components.kkt_kolbe.light import KKTKolbeLight

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 4,
        "name": "Light",
    }

    light = KKTKolbeLight(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    await light.async_turn_on()

    mock_runtime_data.coordinator.async_set_data_point.assert_called_with(4, True)


@pytest.mark.asyncio
async def test_light_turn_off(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test turning off a light."""
    from custom_components.kkt_kolbe.light import KKTKolbeLight

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 4,
        "name": "Light",
    }

    light = KKTKolbeLight(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    await light.async_turn_off()

    mock_runtime_data.coordinator.async_set_data_point.assert_called_with(4, False)


@pytest.mark.asyncio
async def test_light_with_brightness(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test light with brightness support."""
    from custom_components.kkt_kolbe.light import KKTKolbeLight

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 4,
        "name": "Light",
        "brightness_dp": 5,
        "max_brightness": 255,
    }

    light = KKTKolbeLight(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    # DP 5 is 128 in mock_runtime_data (50%)
    brightness = light.brightness
    assert brightness is not None
    assert brightness == 128  # 50% of 255


@pytest.mark.asyncio
async def test_light_with_effects(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test light with effect support."""
    from custom_components.kkt_kolbe.light import KKTKolbeLight

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 4,
        "name": "Light",
        "effect_dp": 101,
        "effects": ["Off", "Rainbow", "Pulse", "Static"],
        "effect_numeric": True,
    }

    light = KKTKolbeLight(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    assert light.effect_list is not None
    assert len(light.effect_list) == 4

    # DP 101 is 2 in mock_runtime_data -> "Pulse" (index 2)
    assert light.effect == "Pulse"


@pytest.mark.asyncio
async def test_light_unique_id(
    hass: HomeAssistant,
    mock_config_entry,
    mock_runtime_data,
) -> None:
    """Test light unique_id generation."""
    from custom_components.kkt_kolbe.light import KKTKolbeLight

    mock_config_entry.add_to_hass(hass)

    config = {
        "dp": 4,
        "name": "Light",
    }

    light = KKTKolbeLight(
        mock_runtime_data.coordinator,
        mock_config_entry,
        config,
    )

    assert light.unique_id is not None
    assert mock_config_entry.entry_id in light.unique_id
    assert "light" in light.unique_id


# =============== FAN SUPPRESS TESTS ===============


@pytest.mark.asyncio
async def test_light_turn_on_with_fan_suppress_enum(
    hass: HomeAssistant,
) -> None:
    """Test fan suppress on light turn-on for enum mode hood (HERMES).

    When disable_fan_auto_start=True and the hood was OFF,
    turning on the light should send fan DP 10 = "off".
    """
    from custom_components.kkt_kolbe.light import KKTKolbeLight

    coordinator = MagicMock()
    # Hood is OFF (DP 1 = False) → will trigger Auto-Power-On
    coordinator.data = {
        1: False, "1": False,
        4: False, "4": False,
    }
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

    config = {"dp": 4, "name": "Light"}
    light = KKTKolbeLight(coordinator, entry, config)

    await light.async_turn_on()

    calls = coordinator.async_set_data_point.call_args_list
    # Expected: DP 1 = True (power on), DP 10 = "off" (fan suppress), DP 4 = True (light on)
    assert call(1, True) in calls, f"Expected power-on call, got: {calls}"
    assert call(10, "off") in calls, f"Expected fan suppress call DP 10='off', got: {calls}"
    assert call(4, True) in calls, f"Expected light-on call, got: {calls}"


@pytest.mark.asyncio
async def test_light_turn_on_with_fan_suppress_numeric(
    hass: HomeAssistant,
) -> None:
    """Test fan suppress on light turn-on for numeric mode hood (SOLO HCM).

    When disable_fan_auto_start=True and the hood was OFF,
    turning on the light should send fan DP 102 = 0 (numeric mode).
    """
    from custom_components.kkt_kolbe.light import KKTKolbeLight

    coordinator = MagicMock()
    # Hood is OFF
    coordinator.data = {
        1: False, "1": False,
        4: False, "4": False,
    }
    coordinator.last_update_success = True
    coordinator.async_set_data_point = AsyncMock()

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test SOLO Hood",
        data={
            "device_id": "bf34515c4ab6ec7f9axqy8",
            "ip_address": "192.168.1.101",
            "local_key": "abcdef1234567890",
            "product_name": "solo_hcm_hood",
            "device_type": "solo_hcm_hood",
        },
        options={"disable_fan_auto_start": True},
        unique_id="bf34515c4ab6ec7f9axqy8",
    )
    entry.add_to_hass(hass)

    config = {"dp": 4, "name": "Light"}
    light = KKTKolbeLight(coordinator, entry, config)

    await light.async_turn_on()

    calls = coordinator.async_set_data_point.call_args_list
    # Expected: DP 1 = True (power on), DP 102 = 0 (fan suppress numeric), DP 4 = True (light on)
    assert call(1, True) in calls, f"Expected power-on call, got: {calls}"
    assert call(102, 0) in calls, f"Expected fan suppress call DP 102=0, got: {calls}"
    assert call(4, True) in calls, f"Expected light-on call, got: {calls}"


@pytest.mark.asyncio
async def test_light_turn_on_fan_suppress_not_when_hood_already_on(
    hass: HomeAssistant,
) -> None:
    """Test that fan suppress is NOT sent when hood is already on.

    When disable_fan_auto_start=True but the hood is ALREADY ON,
    no fan-off command should be sent (to avoid stopping a running fan).
    """
    from custom_components.kkt_kolbe.light import KKTKolbeLight

    coordinator = MagicMock()
    # Hood is already ON (DP 1 = True)
    coordinator.data = {
        1: True, "1": True,
        4: False, "4": False,
        10: "high", "10": "high",  # Fan is running
    }
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
        unique_id="bf735dfe2ad64fba7cpyhn_2",
    )
    entry.add_to_hass(hass)

    config = {"dp": 4, "name": "Light"}
    light = KKTKolbeLight(coordinator, entry, config)

    await light.async_turn_on()

    calls = coordinator.async_set_data_point.call_args_list
    # Should only have the light-on call, NO power-on, NO fan-off
    assert call(4, True) in calls, f"Expected light-on call, got: {calls}"
    assert call(1, True) not in calls, f"Should NOT power-on (already on), got: {calls}"
    assert call(10, "off") not in calls, f"Should NOT send fan-off (hood was already on), got: {calls}"
