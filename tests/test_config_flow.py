"""Test the KKT Kolbe config flow."""
import pytest

from homeassistant.core import HomeAssistant

from custom_components.kkt_kolbe.const import DOMAIN


@pytest.mark.asyncio
async def test_domain_constant(hass: HomeAssistant) -> None:
    """Test the domain constant is correct."""
    assert DOMAIN == "kkt_kolbe"
