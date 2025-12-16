"""Test KKT Kolbe fan platform."""
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.components.fan import FanEntityFeature


@pytest.mark.asyncio
async def test_fan_entity_feature_constants(hass: HomeAssistant) -> None:
    """Test that fan entity features are accessible."""
    assert FanEntityFeature.SET_SPEED is not None
    assert FanEntityFeature.PRESET_MODE is not None


@pytest.mark.asyncio
async def test_fan_module_import(hass: HomeAssistant) -> None:
    """Test that the fan module can be imported."""
    from custom_components.kkt_kolbe import fan
    assert hasattr(fan, "KKTKolbeFan")
    assert hasattr(fan, "async_setup_entry")


@pytest.mark.asyncio
async def test_fan_speed_list_constant(hass: HomeAssistant) -> None:
    """Test the default speed list constant."""
    from custom_components.kkt_kolbe.fan import DEFAULT_SPEED_LIST
    assert "off" in DEFAULT_SPEED_LIST
    assert len(DEFAULT_SPEED_LIST) >= 4
