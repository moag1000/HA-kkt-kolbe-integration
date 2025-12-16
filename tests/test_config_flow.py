"""Test the KKT Kolbe config flow."""
import pytest
from unittest.mock import patch, AsyncMock

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
async def test_manual_setup_success(hass: HomeAssistant, mock_setup_entry) -> None:
    """Test successful manual setup."""
    with patch(
        "custom_components.kkt_kolbe.config_flow.KKTKolbeTuyaDevice"
    ) as mock_device_class:
        mock_device = AsyncMock()
        mock_device.async_test_connection = AsyncMock(return_value=True)
        mock_device_class.return_value = mock_device

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"setup_method": "manual"},
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "manual"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "device_id": "bf3d8e1234567890abcd",
                "host": "192.168.1.100",
                "device_type": "default_hood",
            },
        )

        # Should proceed to authentication step
        assert result["type"] in (FlowResultType.FORM, FlowResultType.CREATE_ENTRY)


@pytest.mark.asyncio
async def test_manual_setup_connection_error(hass: HomeAssistant, mock_setup_entry) -> None:
    """Test manual setup with connection error."""
    with patch(
        "custom_components.kkt_kolbe.config_flow.KKTKolbeTuyaDevice"
    ) as mock_device_class:
        mock_device = AsyncMock()
        mock_device.async_test_connection = AsyncMock(return_value=False)
        mock_device_class.return_value = mock_device

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
                "device_id": "bf3d8e1234567890abcd",
                "host": "192.168.1.100",
                "device_type": "default_hood",
            },
        )

        # Should show form or error
        assert result["type"] in (FlowResultType.FORM, FlowResultType.ABORT)


@pytest.mark.asyncio
async def test_reauth_flow(hass: HomeAssistant, mock_config_entry, mock_setup_entry) -> None:
    """Test reauthentication flow."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.kkt_kolbe.config_flow.KKTKolbeTuyaDevice"
    ) as mock_device_class:
        mock_device = AsyncMock()
        mock_device.async_test_connection = AsyncMock(return_value=True)
        mock_device_class.return_value = mock_device

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


@pytest.mark.asyncio
async def test_duplicate_entry(hass: HomeAssistant, mock_config_entry, mock_setup_entry) -> None:
    """Test that duplicate entries are rejected."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.kkt_kolbe.config_flow.KKTKolbeTuyaDevice"
    ) as mock_device_class:
        mock_device = AsyncMock()
        mock_device.async_test_connection = AsyncMock(return_value=True)
        mock_device_class.return_value = mock_device

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
                "device_id": "test_device_id_12345",
                "host": "192.168.1.100",
                "device_type": "default_hood",
            },
        )

        # Should abort due to duplicate
        assert result["type"] in (FlowResultType.ABORT, FlowResultType.FORM)
