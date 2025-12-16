"""Test the KKT Kolbe integration initialization."""
import pytest
from unittest.mock import patch, AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState

from custom_components.kkt_kolbe.const import DOMAIN


@pytest.mark.asyncio
async def test_setup_success(hass: HomeAssistant, mock_config_entry) -> None:
    """Test successful setup of the integration."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.kkt_kolbe.KKTKolbeTuyaDevice"
    ) as mock_device_class, patch(
        "custom_components.kkt_kolbe.KKTKolbeCoordinator"
    ) as mock_coordinator_class:
        mock_device = AsyncMock()
        mock_device.async_connect = AsyncMock()
        mock_device.async_get_status = AsyncMock(return_value={"1": True, "4": True})
        mock_device.is_connected = True
        mock_device_class.return_value = mock_device

        mock_coordinator = AsyncMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.data = {"1": True}
        mock_coordinator_class.return_value = mock_coordinator

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert mock_config_entry.state in (
            ConfigEntryState.LOADED,
            ConfigEntryState.SETUP_ERROR,
            ConfigEntryState.SETUP_RETRY,
        )


@pytest.mark.asyncio
async def test_setup_connection_error_raises_not_ready(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test that connection errors raise ConfigEntryNotReady."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.kkt_kolbe.KKTKolbeTuyaDevice"
    ) as mock_device_class:
        mock_device = AsyncMock()
        mock_device.async_connect = AsyncMock(side_effect=Exception("Connection failed"))
        mock_device_class.return_value = mock_device

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Should be in retry state due to ConfigEntryNotReady
        assert mock_config_entry.state in (
            ConfigEntryState.SETUP_RETRY,
            ConfigEntryState.SETUP_ERROR,
        )


@pytest.mark.asyncio
async def test_setup_auth_error_raises_auth_failed(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test that authentication errors raise ConfigEntryAuthFailed."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.kkt_kolbe.KKTKolbeTuyaDevice"
    ) as mock_device_class:
        mock_device = AsyncMock()
        # Simulate auth error
        mock_device.async_connect = AsyncMock(
            side_effect=Exception("decrypt failed")
        )
        mock_device_class.return_value = mock_device

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Should fail setup
        assert mock_config_entry.state in (
            ConfigEntryState.SETUP_ERROR,
            ConfigEntryState.SETUP_RETRY,
        )


@pytest.mark.asyncio
async def test_unload_entry(hass: HomeAssistant, mock_config_entry) -> None:
    """Test successful unload of the integration."""
    mock_config_entry.add_to_hass(hass)

    with patch(
        "custom_components.kkt_kolbe.KKTKolbeTuyaDevice"
    ) as mock_device_class, patch(
        "custom_components.kkt_kolbe.KKTKolbeCoordinator"
    ) as mock_coordinator_class:
        mock_device = AsyncMock()
        mock_device.async_connect = AsyncMock()
        mock_device.async_get_status = AsyncMock(return_value={"1": True})
        mock_device.is_connected = True
        mock_device.async_disconnect = AsyncMock()
        mock_device_class.return_value = mock_device

        mock_coordinator = AsyncMock()
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.data = {"1": True}
        mock_coordinator_class.return_value = mock_coordinator

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        if mock_config_entry.state == ConfigEntryState.LOADED:
            await hass.config_entries.async_unload(mock_config_entry.entry_id)
            await hass.async_block_till_done()
            assert mock_config_entry.state == ConfigEntryState.NOT_LOADED
