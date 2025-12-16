"""Test KKT Kolbe sensor platform."""
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory


@pytest.mark.asyncio
async def test_sensor_entity_category_constants(hass: HomeAssistant) -> None:
    """Test that entity category constants are accessible."""
    assert EntityCategory.DIAGNOSTIC is not None
    assert EntityCategory.CONFIG is not None


@pytest.mark.asyncio
async def test_sensor_module_import(hass: HomeAssistant) -> None:
    """Test that the sensor module can be imported."""
    from custom_components.kkt_kolbe import sensor
    assert hasattr(sensor, "KKTKolbeSensor")
    assert hasattr(sensor, "async_setup_entry")


@pytest.mark.asyncio
async def test_const_import(hass: HomeAssistant) -> None:
    """Test that const module can be imported."""
    from custom_components.kkt_kolbe.const import DOMAIN
    assert DOMAIN == "kkt_kolbe"
