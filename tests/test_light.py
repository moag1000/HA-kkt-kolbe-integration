"""Test the KKT Kolbe light platform."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.components.light import ATTR_BRIGHTNESS, ATTR_EFFECT

from custom_components.kkt_kolbe.const import DOMAIN
from custom_components.kkt_kolbe import KKTKolbeRuntimeData


@pytest.fixture
def mock_runtime_data():
    """Create mock runtime data."""
    coordinator = MagicMock()
    coordinator.data = {
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

    async def mock_add_entities(new_entities):
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
