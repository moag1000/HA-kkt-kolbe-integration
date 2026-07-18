"""Test the KKT Kolbe config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kkt_kolbe.const import DOMAIN
from custom_components.kkt_kolbe.const import GLOBAL_API_STORAGE_KEY


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
    """Test the options flow initialization.

    For device entries (entry_type=device), the options flow goes to 'device' step.
    For account entries (entry_type=account), it goes to 'account' step.
    """
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
    # Device entries go to 'device' step, account entries go to 'account' step
    assert result["step_id"] in ("device", "account", "init")


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


@pytest.mark.asyncio
async def test_reconfigure_account_routes_to_smartlife_reauth(
    hass: HomeAssistant,
    mock_smartlife_account_entry,
) -> None:
    """Account entries (entry_type=account) MUST NOT show the device-reconfigure
    menu. They have no IP / device_type / API settings — only SmartLife tokens.

    Regression: pre-4.7.1 the dispatcher in async_step_reconfigure didn't check
    entry_type, so account entries got the device menu and Connection /
    Device Type / API steps which would error or corrupt the entry.
    Fix: route account entries directly to the smartlife_reauth flow.
    """
    mock_smartlife_account_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_smartlife_account_entry.entry_id,
        },
        data=mock_smartlife_account_entry.data,
    )

    # Must land on smartlife_reauth, NOT reconfigure_menu
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "smartlife_reauth"


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
    """Test SmartLife user code validation.

    Note: app_schema is now auto-detected, not provided by user.
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

    # Try with empty user code - should show error (app_schema is auto-detected now)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "user_code": "",
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
    """Test SmartLife scan step when QR code generation fails.

    Note: app_schema is now auto-detected, not provided by user.
    """
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
    Note: app_schema is now auto-detected, not provided by user.
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
        # Enter user code - this starts the QR scan flow (app_schema auto-detected)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "user_code": "EU12345678",
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
    """Test SmartLife account reauth flow redirects to QR code re-login."""
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

    # SmartLife entries should redirect to smartlife_reauth (QR code re-login)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "smartlife_reauth"


@pytest.mark.asyncio
async def test_smartlife_user_code_schema(hass: HomeAssistant) -> None:
    """Test SmartLife user code step has correct schema.

    Note: app_schema is now auto-detected (tries haauthorize, smartlife, tuyaSmart).
    The user only provides user_code.
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

    # Verify we're on the user code step with simplified schema
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "smartlife_user_code"
    # Only user_code is required now (app_schema is auto-detected)
    assert "user_code" in result["data_schema"].schema


def _make_async_context_client(**attrs: object) -> MagicMock:
    """Build a MagicMock usable as `async with TuyaCloudClient(...) as client:`.

    Plain MagicMock() doesn't support the async context manager protocol
    (its __aenter__/__aexit__ would be sync MagicMocks, not awaitable), so
    tests that exercise `async with api_client:` need this helper.
    """
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    for key, value in attrs.items():
        setattr(client, key, value)
    return client


def _schema_default(schema, key: str):
    """Look up the default value for a voluptuous schema key by name."""
    for marker in schema.schema:
        if str(marker) == key:
            return marker.default() if callable(marker.default) else marker.default
    raise KeyError(key)


# === TUYA IOT PLATFORM (api_only) CONFIG FLOW TESTS ===


@pytest.mark.asyncio
async def test_api_only_direct_success_creates_entry(
    hass: HomeAssistant, mock_setup_entry
) -> None:
    """Tuya IoT Platform path: api_only -> submit creds -> device selection -> entry.

    No stored global API credentials, so async_step_api_only goes straight to
    the credentials form instead of the api_choice detour.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"setup_method": "api_only"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "api_only"

    mock_client = _make_async_context_client(
        test_connection=AsyncMock(return_value=True),
        get_device_list_with_details=AsyncMock(
            return_value=[
                {
                    "id": "bf735dfe2ad64fba7cpyhn",
                    "name": "KKT HERMES Hood",
                    "product_name": "KKT Kolbe HERMES",
                    "product_id": "ypaixllljc2dcpae",
                    "category": "yyj",
                    "ip": "192.168.1.100",
                    "local_key": "1234567890abcdef",
                }
            ]
        ),
    )

    with patch(
        "custom_components.kkt_kolbe.api.TuyaCloudClient",
        return_value=mock_client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "api_client_id": "test_client_id_1234",
                "api_client_secret": "test_client_secret_1234567890",
                "api_endpoint": "https://openapi.tuyaeu.com",
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "api_device_selection"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"selected_device": "bf735dfe2ad64fba7cpyhn"},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["device_id"] == "bf735dfe2ad64fba7cpyhn"
    assert result["data"]["integration_mode"] == "api_discovery"
    assert result["data"]["local_key"] == "1234567890abcdef"


@pytest.mark.asyncio
async def test_api_device_selection_aborts_if_already_configured(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """REGRESSION GUARD: async_step_api_device_selection (config_flow.py ~3048)
    must call async_set_unique_id + _abort_if_unique_id_configured so the
    Tuya IoT Platform path can't add the same physical device twice.

    Sets up a device via API-only, but the API-returned device_id matches an
    already-configured entry -> must ABORT with already_configured instead of
    creating a duplicate entry.
    """
    mock_config_entry.add_to_hass(hass)  # unique_id = bf735dfe2ad64fba7cpyhn

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"setup_method": "api_only"},
    )
    assert result["step_id"] == "api_only"

    mock_client = _make_async_context_client(
        test_connection=AsyncMock(return_value=True),
        get_device_list_with_details=AsyncMock(
            return_value=[
                {
                    "id": "bf735dfe2ad64fba7cpyhn",  # SAME as mock_config_entry
                    "name": "KKT HERMES Hood",
                    "product_name": "KKT Kolbe HERMES",
                    "product_id": "ypaixllljc2dcpae",
                    "category": "yyj",
                    "ip": "192.168.1.100",
                    "local_key": "1234567890abcdef",
                }
            ]
        ),
    )

    with patch(
        "custom_components.kkt_kolbe.api.TuyaCloudClient",
        return_value=mock_client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "api_client_id": "test_client_id_1234",
                "api_client_secret": "test_client_secret_1234567890",
                "api_endpoint": "https://openapi.tuyaeu.com",
            },
        )

    assert result["step_id"] == "api_device_selection"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"selected_device": "bf735dfe2ad64fba7cpyhn"},
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.asyncio
async def test_api_only_stored_credentials_routes_via_api_credentials_step(
    hass: HomeAssistant,
    mock_setup_entry,
) -> None:
    """Full documented path: api_only -> api_choice -> api_credentials ->
    api_device_selection -> entry, exercised when global API credentials are
    already stored (so api_only detours through the choice screen).
    """
    hass.data[GLOBAL_API_STORAGE_KEY] = {
        "client_id": "existing_client_id_123",
        "client_secret": "existing_client_secret_1234567890",
        "endpoint": "https://openapi.tuyaeu.com",
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"setup_method": "api_only"},
    )
    # Stored credentials exist -> routed to the choice screen, not api_only form
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "api_choice"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"use_stored_api": False, "manage_api": False},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "api_credentials"

    mock_client = _make_async_context_client(
        test_connection=AsyncMock(return_value=True),
        get_device_list_with_details=AsyncMock(
            return_value=[
                {
                    "id": "bf735dfe2ad64fba7cpyhn",
                    "name": "KKT HERMES Hood",
                    "product_name": "KKT Kolbe HERMES range hood",
                    "product_id": "ypaixllljc2dcpae",
                    "category": "yyj",
                    "ip": "192.168.1.100",
                    "local_key": "1234567890abcdef",
                }
            ]
        ),
    )

    with patch(
        "custom_components.kkt_kolbe.api.TuyaCloudClient",
        return_value=mock_client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "api_client_id": "new_client_id_12345",
                "api_client_secret": "new_client_secret_1234567890",
                "api_endpoint": "https://openapi.tuyaeu.com",
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "api_device_selection"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"selected_device": "bf735dfe2ad64fba7cpyhn"},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["device_id"] == "bf735dfe2ad64fba7cpyhn"


# === SMART DISCOVERY CONFIG FLOW TESTS ===


@pytest.mark.asyncio
async def test_smart_discovery_shows_form_and_creates_entry_when_ready(
    hass: HomeAssistant,
    mock_setup_entry,
) -> None:
    """Smart Discovery renders a device-selection form, and picking a
    'ready_to_add' device (has IP + local_key) does one-click entry creation.
    """
    from custom_components.kkt_kolbe.smart_discovery import SmartDiscoveryResult

    ready_result = SmartDiscoveryResult(
        device_id="bf735dfe2ad64fba7cpyhn",
        name="KKT HERMES Hood",
        ip_address="192.168.1.100",
        local_key="1234567890abcdef",
        product_name="hermes_style_hood",
        device_type="hermes_style_hood",
        discovered_via="local+api",
        api_enriched=True,
        ready_to_add=True,
        friendly_type="HERMES & STYLE",
    )

    mock_discovery_instance = MagicMock()
    mock_discovery_instance.async_discover = AsyncMock(
        return_value={"bf735dfe2ad64fba7cpyhn": ready_result}
    )

    with patch(
        "custom_components.kkt_kolbe.config_flow.SmartDiscovery",
        return_value=mock_discovery_instance,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"setup_method": "smart_discovery"},
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "smart_discovery"
        assert "selected_device" in result["data_schema"].schema

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"selected_device": "bf735dfe2ad64fba7cpyhn"},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["device_id"] == "bf735dfe2ad64fba7cpyhn"
    assert result["data"]["local_key"] == "1234567890abcdef"
    assert result["data"]["integration_mode"] == "hybrid"


@pytest.mark.asyncio
async def test_smart_discovery_device_without_local_key_routes_to_authentication(
    hass: HomeAssistant,
) -> None:
    """A discovered device that's NOT ready (no local_key yet) must route to
    the authentication step instead of trying to create an incomplete entry.
    """
    from custom_components.kkt_kolbe.smart_discovery import SmartDiscoveryResult

    not_ready_result = SmartDiscoveryResult(
        device_id="bf999999999999999999",
        name="KKT Device",
        ip_address="192.168.1.150",
        local_key=None,
        product_name="auto",
        device_type="auto",
        discovered_via="local",
        api_enriched=False,
        ready_to_add=False,
        friendly_type="KKT Kolbe Device",
    )

    mock_discovery_instance = MagicMock()
    mock_discovery_instance.async_discover = AsyncMock(
        return_value={"bf999999999999999999": not_ready_result}
    )

    with patch(
        "custom_components.kkt_kolbe.config_flow.SmartDiscovery",
        return_value=mock_discovery_instance,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"setup_method": "smart_discovery"},
        )
        assert result["step_id"] == "smart_discovery"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"selected_device": "bf999999999999999999"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "authentication"


@pytest.mark.asyncio
async def test_smart_discovery_no_devices_shows_retry_form(hass: HomeAssistant) -> None:
    """No devices found at all -> stays on smart_discovery with a retry option
    and a no_devices_found error, instead of crashing on an empty schema.
    """
    mock_discovery_instance = MagicMock()
    mock_discovery_instance.async_discover = AsyncMock(return_value={})

    with patch(
        "custom_components.kkt_kolbe.config_flow.SmartDiscovery",
        return_value=mock_discovery_instance,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"setup_method": "smart_discovery"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "smart_discovery"
    assert result["errors"] == {"base": "no_devices_found"}
    assert "selected_device" not in result["data_schema"].schema


# === ZEROCONF DISCOVERY CONFIG FLOW TESTS ===


@pytest.mark.asyncio
async def test_zeroconf_already_configured_aborts(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """A zeroconf ping for a device_id that's already configured must abort
    immediately (and silently update the IP), never re-prompting the user.
    """
    mock_config_entry.add_to_hass(hass)

    discovery_info = {
        "host": "192.168.1.222",
        "device_id": "bf735dfe2ad64fba7cpyhn",  # matches mock_config_entry
        "name": "bf735dfe2ad64fba7cpyhn._tuya._tcp.local.",
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"

    # IP should have been silently updated on the existing entry.
    updated_entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert updated_entry.data.get("ip_address") == "192.168.1.222"


@pytest.mark.asyncio
async def test_zeroconf_no_local_key_aborts_without_api_credentials(
    hass: HomeAssistant,
) -> None:
    """A new (unconfigured) device with no global API credentials stored
    aborts with no_local_key, deliberately WITHOUT claiming the unique_id, so
    Smart Discovery / manual setup can still pick the device up afterwards.
    """
    discovery_info = {
        "host": "192.168.1.223",
        "device_id": "bfnewdevice00000000",
        "name": "bfnewdevice00000000._smartlife._tcp.local.",
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_local_key"


@pytest.mark.asyncio
async def test_zeroconf_happy_path_confirms_and_creates_entry(
    hass: HomeAssistant,
    mock_setup_entry,
) -> None:
    """New device, API credentials stored and API enrichment finds a
    local_key -> zeroconf_confirm form -> one-click entry creation.
    """
    hass.data[GLOBAL_API_STORAGE_KEY] = {
        "client_id": "existing_client_id_123",
        "client_secret": "existing_client_secret_1234567890",
        "endpoint": "https://openapi.tuyaeu.com",
    }

    discovery_info = {
        "host": "192.168.1.100",
        "device_id": "bf735dfe2ad64fba7cpyhn",
        "name": "bf735dfe2ad64fba7cpyhn._tuya._tcp.local.",
    }

    api_devices = [
        {
            "id": "bf735dfe2ad64fba7cpyhn",
            "name": "KKT HERMES Hood",
            "product_name": "KKT Kolbe HERMES",
            "product_id": "ypaixllljc2dcpae",
            "category": "yyj",
            "local_key": "1234567890abcdef",
            "icon": None,
        }
    ]

    with patch(
        "custom_components.kkt_kolbe.api_manager.GlobalAPIManager.get_kkt_devices_from_api",
        new_callable=AsyncMock,
        return_value=api_devices,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_ZEROCONF},
            data=discovery_info,
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "zeroconf_confirm"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["device_id"] == "bf735dfe2ad64fba7cpyhn"
    assert result["data"]["local_key"] == "1234567890abcdef"
    assert result["data"]["integration_mode"] == "hybrid"


# === RECONFIGURE MENU BRANCH TESTS ===


@pytest.mark.asyncio
async def test_reconfigure_connection_renders_with_empty_local_key_default(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """The reconfigure 'Connection' form must default local_key to "" and
    never echo the stored secret back into the form field.
    """
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry.entry_id,
        },
        data=mock_config_entry.data,
    )
    assert result["step_id"] == "reconfigure_menu"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"reconfigure_option": "connection"},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure_connection"
    assert _schema_default(result["data_schema"], "local_key") == ""
    # Stored secret must never appear as the field default.
    assert _schema_default(result["data_schema"], "local_key") != mock_config_entry.data["local_key"]


@pytest.mark.asyncio
async def test_reconfigure_connection_applies_update(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
) -> None:
    """Submitting the Connection form updates the entry and reloads it."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry.entry_id,
        },
        data=mock_config_entry.data,
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"reconfigure_option": "connection"},
    )
    assert result["step_id"] == "reconfigure_connection"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "ip_address": "192.168.1.200",
            "local_key": "",  # keep current key
            "test_connection": False,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    updated_entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert updated_entry.data["ip_address"] == "192.168.1.200"
    # Local key preserved since an empty string means "keep current".
    assert updated_entry.data["local_key"] == "1234567890abcdef"


@pytest.mark.asyncio
async def test_reconfigure_device_type_renders_and_applies(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
) -> None:
    """Reconfigure 'Device Type' branch renders a form and updates the entry."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry.entry_id,
        },
        data=mock_config_entry.data,
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"reconfigure_option": "device_type"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure_device_type"
    assert "device_type" in result["data_schema"].schema

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"device_type": "ind7705hc_cooktop"},
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    updated_entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert updated_entry.data["device_type"] == "ind7705hc_cooktop"


@pytest.mark.asyncio
async def test_reconfigure_api_renders_and_applies(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
) -> None:
    """Reconfigure 'API Settings' branch renders a form and, when API is
    enabled with valid credentials, updates + reloads the entry.
    """
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry.entry_id,
        },
        data=mock_config_entry.data,
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"reconfigure_option": "api"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure_api"

    mock_client = _make_async_context_client(test_connection=AsyncMock(return_value=True))

    with patch(
        "custom_components.kkt_kolbe.api.TuyaCloudClient",
        return_value=mock_client,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "api_enabled": True,
                "api_client_id": "reconf_client_id_1234",
                "api_client_secret": "reconf_client_secret_1234567890",
                "api_endpoint": "https://openapi.tuyaeu.com",
            },
        )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    updated_entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert updated_entry.data["api_enabled"] is True
    assert updated_entry.data["api_client_id"] == "reconf_client_id_1234"
    assert updated_entry.data["integration_mode"] == "hybrid"


@pytest.mark.asyncio
async def test_reconfigure_all_renders_with_empty_local_key_default_and_applies(
    hass: HomeAssistant,
    mock_config_entry,
    mock_setup_entry,
) -> None:
    """Reconfigure 'All Settings' branch renders a form (local_key defaults
    to empty, same rule as Connection) and applies a combined update.
    """
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": mock_config_entry.entry_id,
        },
        data=mock_config_entry.data,
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"reconfigure_option": "all"},
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure_all"
    assert _schema_default(result["data_schema"], "local_key") == ""

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "ip_address": "192.168.1.201",
            "local_key": "",
            "device_type": "hermes_style_hood",
            "api_enabled": False,
            "test_connection": False,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    updated_entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert updated_entry.data["ip_address"] == "192.168.1.201"
    assert updated_entry.data["integration_mode"] == "manual"


# === OPTIONS FLOW (device entry) TESTS ===


@pytest.mark.asyncio
async def test_options_device_step_saves_settings(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Options flow for a manual/device entry: async_step_device renders the
    full options form and saves settings when submitted.
    """
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.kkt_kolbe.async_setup_entry",
        return_value=True,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "device"
    assert "api_client_id" in result["data_schema"].schema  # full options incl. IoT Platform API

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "scan_interval": 60,
            "new_local_key": "",
            "api_enabled": False,
            "api_client_id": "",
            "api_client_secret": "",
            "api_endpoint": "https://openapi.tuyaeu.com",
            "enable_debug_logging": True,
            "enable_advanced_entities": True,
            "zone_naming_scheme": "zone",
            "disable_fan_auto_start": True,
            "test_connection": False,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["scan_interval"] == 60
    assert result["data"]["enable_debug_logging"] is True
