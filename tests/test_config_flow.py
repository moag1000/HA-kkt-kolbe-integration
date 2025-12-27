"""Test the KKT Kolbe config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.kkt_kolbe.const import DOMAIN


@pytest.mark.asyncio
async def test_domain_constant() -> None:
    """Test the domain constant is correct."""
    assert DOMAIN == "kkt_kolbe"


@pytest.mark.asyncio
async def test_config_flow_user_init(hass: HomeAssistant) -> None:
    """Test the initial step of the config flow shows method selection."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert "setup_method" in result["data_schema"].schema


@pytest.mark.asyncio
async def test_config_flow_manual_step(hass: HomeAssistant) -> None:
    """Test the manual configuration step."""
    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Select manual method
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"setup_method": "manual"},
    )

    # Should show manual configuration form
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "manual"


@pytest.mark.asyncio
async def test_config_flow_discovery_step(hass: HomeAssistant) -> None:
    """Test the discovery step."""
    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Mock discovery to return no devices
    with patch(
        "custom_components.kkt_kolbe.config_flow.async_start_discovery",
        new_callable=AsyncMock,
    ):
        with patch(
            "custom_components.kkt_kolbe.config_flow.get_discovered_devices",
            return_value={},
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={"setup_method": "discovery"},
            )

    # Should show discovery form (even with no devices - user can retry or go manual)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "discovery"


@pytest.mark.asyncio
async def test_config_flow_abort_already_configured(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test that flow aborts if device is already configured."""
    # Add the existing entry
    mock_config_entry.add_to_hass(hass)

    # Start a new flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Select manual method
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"setup_method": "manual"},
    )

    # Fill manual form with same device ID
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "ip_address": "192.168.1.100",
            "device_id": "bf735dfe2ad64fba7cpyhn",  # Same as mock_config_entry
            "device_type": "hermes_style_hood",
        },
    )

    # After manual step, we go to authentication step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "authentication"

    # Provide the local key
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "local_key": "1234567890abcdef",
            "test_connection": False,  # Skip connection test
        },
    )

    # After authentication, we go to settings step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "settings"

    # Fill settings form
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "update_interval": 30,
            "enable_debug_logging": False,
            "enable_advanced_entities": True,
        },
    )

    # After settings, we go to confirmation step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "confirmation"

    # Confirm - this is where the abort should happen
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"confirm": True},
    )

    # Now we should get abort as already configured
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_config_flow_invalid_ip(hass: HomeAssistant) -> None:
    """Test that invalid IP address shows error."""
    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Select manual method
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"setup_method": "manual"},
    )

    # Try invalid IP
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "ip_address": "not-an-ip-address",
            "device_id": "bf735dfe2ad64fba7cpyhn",
            "device_type": "hermes_style_hood",
        },
    )

    # Should show error
    assert result["type"] == FlowResultType.FORM
    assert "invalid_ip" in result.get("errors", {}).values() or result["step_id"] == "manual"


@pytest.mark.asyncio
async def test_config_flow_invalid_device_id(hass: HomeAssistant) -> None:
    """Test that invalid device ID shows error."""
    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Select manual method
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"setup_method": "manual"},
    )

    # Try short device ID
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "ip_address": "192.168.1.100",
            "device_id": "short",  # Too short
            "device_type": "hermes_style_hood",
        },
    )

    # Should show error
    assert result["type"] == FlowResultType.FORM
    assert "invalid_device_id" in result.get("errors", {}).values() or result["step_id"] == "manual"


@pytest.mark.asyncio
async def test_options_flow_init(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test the options flow initialization."""
    # Add the entry
    mock_config_entry.add_to_hass(hass)

    # Mock the integration setup
    with patch(
        "custom_components.kkt_kolbe.async_setup_entry",
        return_value=True,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Start options flow
    result = await hass.config_entries.options.async_init(
        mock_config_entry.entry_id,
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_reauth_flow(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test the reauthentication flow."""
    # Add the entry
    mock_config_entry.add_to_hass(hass)

    # Start reauth flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": mock_config_entry.entry_id,
        },
        data=mock_config_entry.data,
    )

    # Should show reauth form
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"


@pytest.mark.asyncio
async def test_reconfigure_flow(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test the reconfigure flow."""
    # Add the entry
    mock_config_entry.add_to_hass(hass)

    # Start reconfigure flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry.entry_id,
        },
        data=mock_config_entry.data,
    )

    # Should show reconfigure menu
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure_menu"
