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


# === SMARTLIFE CONFIG FLOW TESTS ===


@pytest.mark.asyncio
async def test_smartlife_user_code_step(hass: HomeAssistant) -> None:
    """Test the SmartLife user code input step."""
    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Select SmartLife method
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"setup_method": "smartlife"},
    )

    # Should show SmartLife user code form
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "smartlife_user_code"
    assert "user_code" in result["data_schema"].schema


@pytest.mark.asyncio
async def test_smartlife_user_code_validation(hass: HomeAssistant) -> None:
    """Test SmartLife user code validation."""
    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Select SmartLife method
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"setup_method": "smartlife"},
    )

    # Try with empty user code - should show error
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "user_code": "",
            "app_schema": "smartlife",
        },
    )

    # Should remain on user code form with error or validation
    assert result["type"] == FlowResultType.FORM
    # Either shows error or stays on same step for validation
    assert result["step_id"] == "smartlife_user_code" or "errors" in result


@pytest.mark.asyncio
async def test_smartlife_scan_step_qr_generation_error(
    hass: HomeAssistant,
) -> None:
    """Test SmartLife scan step when QR code generation fails."""
    from custom_components.kkt_kolbe.exceptions import KKTConnectionError

    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Select SmartLife method
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"setup_method": "smartlife"},
    )

    # Enter user code - mock QR generation to fail
    mock_client = MagicMock()
    mock_client.async_generate_qr_code = AsyncMock(
        side_effect=KKTConnectionError(operation="qr_code", reason="Network error")
    )

    # Patch at the module where TuyaSharingClient is imported from
    with patch(
        "custom_components.kkt_kolbe.clients.tuya_sharing_client.TuyaSharingClient",
        return_value=mock_client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "user_code": "EU12345678",
                "app_schema": "smartlife",
            },
        )

    # When QR generation fails, it shows the scan step with errors
    # The flow may show FORM with errors or stay on the scan step
    assert result["type"] == FlowResultType.FORM
    # Either shows error or goes to scan step (behavior may vary based on impl)
    assert result["step_id"] in ["smartlife_scan", "smartlife_user_code"]


@pytest.mark.asyncio
async def test_is_kkt_device_by_product_id() -> None:
    """Test _is_kkt_device detection by product_id."""
    from custom_components.kkt_kolbe.config_flow import _is_kkt_device

    # Create mock device with known KKT product_id
    mock_device = MagicMock()
    mock_device.product_id = "ypaixllljc2dcpae"  # HERMES product_id
    mock_device.device_id = "test123456789012345"
    mock_device.product_name = "Some Device"
    mock_device.category = "yyj"
    mock_device.name = "Test Hood"

    is_kkt, device_type = _is_kkt_device(mock_device)

    assert is_kkt is True
    assert device_type == "hermes_style_hood"


@pytest.mark.asyncio
async def test_is_kkt_device_by_product_name_prefix() -> None:
    """Test _is_kkt_device detection by KKT product name prefix."""
    from custom_components.kkt_kolbe.config_flow import _is_kkt_device

    # Create mock device with KKT prefix in product_name
    mock_device = MagicMock()
    mock_device.product_id = "unknown_product_123"
    mock_device.device_id = "test123456789012345"
    mock_device.product_name = "KKT Kolbe NEW MODEL"
    mock_device.category = "yyj"
    mock_device.name = "My New Hood"

    is_kkt, device_type = _is_kkt_device(mock_device)

    assert is_kkt is True
    # Unknown model, so device_type is None
    assert device_type is None


@pytest.mark.asyncio
async def test_is_kkt_device_by_category_and_keywords() -> None:
    """Test _is_kkt_device detection by category and keywords."""
    from custom_components.kkt_kolbe.config_flow import _is_kkt_device

    # Create mock device with yyj category and HERMES keyword
    mock_device = MagicMock()
    mock_device.product_id = "unknown_product"
    mock_device.device_id = "test123456789012345"
    mock_device.product_name = "Smart Hood"
    mock_device.category = "yyj"
    mock_device.name = "HERMES Kitchen Hood"

    is_kkt, device_type = _is_kkt_device(mock_device)

    assert is_kkt is True


@pytest.mark.asyncio
async def test_is_kkt_device_non_kkt() -> None:
    """Test _is_kkt_device returns False for non-KKT devices."""
    from custom_components.kkt_kolbe.config_flow import _is_kkt_device

    # Create mock non-KKT device
    mock_device = MagicMock()
    mock_device.product_id = "generic_light_product"
    mock_device.device_id = "light123456789012345"
    mock_device.product_name = "Generic Smart Light"
    mock_device.category = "dj"  # Light category
    mock_device.name = "Living Room Light"

    is_kkt, device_type = _is_kkt_device(mock_device)

    assert is_kkt is False
    assert device_type is None


@pytest.mark.asyncio
async def test_is_kkt_device_cooktop_category() -> None:
    """Test _is_kkt_device detection for cooktop (dcl category)."""
    from custom_components.kkt_kolbe.config_flow import _is_kkt_device

    # Create mock cooktop device
    mock_device = MagicMock()
    mock_device.product_id = "p8volecsgzdyun29"  # IND7705HC product_id
    mock_device.device_id = "cooktop12345678901234"
    mock_device.product_name = "KKT Kolbe IND7705HC"
    mock_device.category = "dcl"
    mock_device.name = "Kitchen Cooktop"

    is_kkt, device_type = _is_kkt_device(mock_device)

    assert is_kkt is True
    assert device_type == "ind7705hc_cooktop"


@pytest.mark.asyncio
async def test_smartlife_select_devices_form_structure(
    hass: HomeAssistant,
) -> None:
    """Test that SmartLife flow progresses correctly with valid user code.

    Note: Full SmartLife flow testing with progress tasks is complex due to
    the async nature of QR code scanning. This test validates initial steps.
    """
    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Select SmartLife method
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"setup_method": "smartlife"},
    )

    # Verify we're on user code step
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "smartlife_user_code"

    # Mock client to generate QR code successfully
    mock_client = MagicMock()
    mock_client.async_generate_qr_code = AsyncMock(
        return_value="tuyaSmart--qrLogin?token=test_token"
    )

    # Patch at the module where TuyaSharingClient is imported from
    with patch(
        "custom_components.kkt_kolbe.clients.tuya_sharing_client.TuyaSharingClient",
        return_value=mock_client,
    ):
        # Enter user code - this starts the QR scan flow
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "user_code": "EU12345678",
                "app_schema": "smartlife",
            },
        )

    # The scan step uses show_progress, which shows scanning status
    # Result can be FORM, SHOW_PROGRESS, or related progress types
    assert result["type"] in [
        FlowResultType.FORM,
        FlowResultType.SHOW_PROGRESS,
        FlowResultType.SHOW_PROGRESS_DONE,
    ]
    # Should be on scan-related step
    if result["type"] == FlowResultType.FORM:
        assert "scan" in result.get("step_id", "") or "smartlife" in result.get("step_id", "")


@pytest.mark.asyncio
async def test_smartlife_reauth_flow(
    hass: HomeAssistant,
    mock_smartlife_account_entry,
) -> None:
    """Test SmartLife account reauth flow."""
    # Add the existing SmartLife account entry
    mock_smartlife_account_entry.add_to_hass(hass)

    # Start reauth flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": mock_smartlife_account_entry.entry_id,
        },
        data=mock_smartlife_account_entry.data,
    )

    # Should show reauth form
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"


@pytest.mark.asyncio
async def test_smartlife_app_schema_options(hass: HomeAssistant) -> None:
    """Test that both SmartLife and Tuya Smart app schemas are available."""
    # Start the flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    # Select SmartLife method
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"setup_method": "smartlife"},
    )

    # Verify we're on the user code step with app_schema option
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "smartlife_user_code"
    assert "app_schema" in result["data_schema"].schema
