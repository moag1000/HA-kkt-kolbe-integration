"""Test the KKT Kolbe config flow."""
import pytest

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.core import HomeAssistant

from custom_components.kkt_kolbe.const import DOMAIN


@pytest.mark.asyncio
async def test_user_form_display(hass: HomeAssistant) -> None:
    """Test that the user form is displayed correctly."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_config_flow_module_import(hass: HomeAssistant) -> None:
    """Test that config_flow module can be imported."""
    from custom_components.kkt_kolbe import config_flow
    assert hasattr(config_flow, "KKTKolbeConfigFlow")


@pytest.mark.asyncio
async def test_domain_constant(hass: HomeAssistant) -> None:
    """Test the domain constant is correct."""
    assert DOMAIN == "kkt_kolbe"
