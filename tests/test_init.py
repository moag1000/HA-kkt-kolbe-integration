"""Test the KKT Kolbe integration initialization."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ConfigEntryNotReady, ConfigEntryAuthFailed

from custom_components.kkt_kolbe.const import DOMAIN


@pytest.mark.asyncio
async def test_setup_success(hass, mock_config_entry, mock_tuya_device):
    """Test successful setup of the integration."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.kkt_kolbe.tuya_device.KKTKolbeTuyaDevice"
    ) as mock_device_class:
        mock_device = AsyncMock()
        mock_device.async_connect = AsyncMock()
        mock_device.async_get_status = AsyncMock(return_value={"1": True, "4": True})
        mock_device.is_connected = True
        mock_device_class.return_value = mock_device

        with patch(
            "custom_components.kkt_kolbe.async_setup_entry", return_value=True
        ):
            assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
            await hass.async_block_till_done()

            assert mock_config_entry.state == ConfigEntryState.LOADED
            assert DOMAIN in hass.data


@pytest.mark.asyncio
async def test_setup_connection_error_raises_not_ready(hass, mock_config_entry):
    """Test that connection errors raise ConfigEntryNotReady."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.kkt_kolbe.tuya_device.KKTKolbeTuyaDevice"
    ) as mock_device_class:
        mock_device = AsyncMock()
        # Simulate connection failure
        mock_device.async_connect.side_effect = Exception("Connection failed")
        mock_device_class.return_value = mock_device

        with pytest.raises(ConfigEntryNotReady):
            await hass.config_entries.async_setup(mock_config_entry.entry_id)


@pytest.mark.asyncio
async def test_setup_auth_error_raises_auth_failed(hass, mock_config_entry):
    """Test that authentication errors raise ConfigEntryAuthFailed."""
    mock_config_entry.add_to_hass(hass)

    from custom_components.kkt_kolbe.exceptions import KKTAuthenticationError

    with patch(
        "custom_components.kkt_kolbe.tuya_device.KKTKolbeTuyaDevice"
    ) as mock_device_class:
        mock_device = AsyncMock()
        # Simulate authentication failure
        mock_device.async_connect.side_effect = KKTAuthenticationError(
            device_id="test_device",
            message="Invalid local key"
        )
        mock_device_class.return_value = mock_device

        with pytest.raises(ConfigEntryAuthFailed):
            await hass.config_entries.async_setup(mock_config_entry.entry_id)


@pytest.mark.asyncio
async def test_unload_entry(hass, mock_config_entry, mock_tuya_device):
    """Test successful unload of the integration."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.kkt_kolbe.tuya_device.KKTKolbeTuyaDevice"
    ) as mock_device_class:
        mock_device = AsyncMock()
        mock_device.async_connect = AsyncMock()
        mock_device.async_get_status = AsyncMock(return_value={"1": True})
        mock_device.is_connected = True
        mock_device_class.return_value = mock_device

        # Setup
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Unload
        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert mock_config_entry.state == ConfigEntryState.NOT_LOADED
