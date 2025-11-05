"""Test the KKT Kolbe config flow."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_IP_ADDRESS, CONF_DEVICE_ID, CONF_ACCESS_TOKEN
from homeassistant.data_entry_flow import FlowResultType

from custom_components.kkt_kolbe.const import DOMAIN


@pytest.mark.asyncio
async def test_user_form_display(hass):
    """Test that the user form is displayed correctly."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_manual_setup_success(hass, mock_tuya_device):
    """Test successful manual setup."""
    with patch(
        "custom_components.kkt_kolbe.config_flow.KKTKolbeTuyaDevice"
    ) as mock_device_class:
        # Mock device instance
        mock_device = AsyncMock()
        mock_device.async_test_connection.return_value = True
        mock_device_class.return_value = mock_device

        # Start flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Submit manual setup choice
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"setup_method": "manual"},
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "manual"

        # Submit device details
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "device_id": "test_device_12345",
                "ip_address": "192.168.1.100",
                "local_key": "test_local_key",
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "KKT Device test_de"
        assert result["data"]["device_id"] == "test_device_12345"
        assert result["data"]["ip_address"] == "192.168.1.100"
        assert result["data"]["local_key"] == "test_local_key"


@pytest.mark.asyncio
async def test_manual_setup_connection_error(hass, mock_tuya_device):
    """Test manual setup with connection error."""
    with patch(
        "custom_components.kkt_kolbe.config_flow.KKTKolbeTuyaDevice"
    ) as mock_device_class:
        # Mock device that fails connection
        mock_device = AsyncMock()
        mock_device.async_test_connection.return_value = False
        mock_device_class.return_value = mock_device

        # Start flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        # Submit manual setup choice
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"setup_method": "manual"},
        )

        # Submit device details (should fail)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "device_id": "test_device_12345",
                "ip_address": "192.168.1.100",
                "local_key": "wrong_key",
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "manual"
        assert result["errors"]["base"] == "cannot_connect"


@pytest.mark.asyncio
async def test_reauth_flow(hass, mock_config_entry):
    """Test reauthentication flow."""
    # Add the config entry
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.kkt_kolbe.config_flow.KKTKolbeTuyaDevice"
    ) as mock_device_class:
        # Mock device with new credentials
        mock_device = AsyncMock()
        mock_device.async_test_connection.return_value = True
        mock_device_class.return_value = mock_device

        # Start reauth flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": mock_config_entry.entry_id,
            },
            data=mock_config_entry.data,
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        # Submit new local key
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"local_key": "new_local_key"},
        )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"


@pytest.mark.asyncio
async def test_duplicate_entry(hass, mock_config_entry, mock_tuya_device):
    """Test that duplicate entries are rejected."""
    # Add existing entry
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.kkt_kolbe.config_flow.KKTKolbeTuyaDevice"
    ) as mock_device_class:
        mock_device = AsyncMock()
        mock_device.async_test_connection.return_value = True
        mock_device_class.return_value = mock_device

        # Try to add same device again
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"setup_method": "manual"},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "device_id": "test_device_id_12345",  # Same as mock_config_entry
                "ip_address": "192.168.1.100",
                "local_key": "test_local_key",
            },
        )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "already_configured"
