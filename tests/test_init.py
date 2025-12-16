"""Test the KKT Kolbe integration initialization."""
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState

from custom_components.kkt_kolbe.const import DOMAIN


@pytest.mark.asyncio
async def test_init_module_import(hass: HomeAssistant) -> None:
    """Test that init module can be imported."""
    from custom_components import kkt_kolbe
    assert hasattr(kkt_kolbe, "async_setup")
    assert hasattr(kkt_kolbe, "async_setup_entry")
    assert hasattr(kkt_kolbe, "async_unload_entry")


@pytest.mark.asyncio
async def test_platforms_defined(hass: HomeAssistant) -> None:
    """Test that platforms are defined."""
    from custom_components.kkt_kolbe import PLATFORMS
    assert "sensor" in [str(p) for p in PLATFORMS]
    assert "fan" in [str(p) for p in PLATFORMS]
    assert "switch" in [str(p) for p in PLATFORMS]


@pytest.mark.asyncio
async def test_config_schema_defined(hass: HomeAssistant) -> None:
    """Test that CONFIG_SCHEMA is defined."""
    from custom_components.kkt_kolbe import CONFIG_SCHEMA
    assert CONFIG_SCHEMA is not None
