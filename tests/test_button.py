"""Test the KKT Kolbe reconnect button."""

from __future__ import annotations

from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.kkt_kolbe import KKTKolbeRuntimeData
from custom_components.kkt_kolbe.button import KKTKolbeReconnectButton
from custom_components.kkt_kolbe.button import async_setup_entry


def _runtime(device: MagicMock | None, coordinator: MagicMock) -> KKTKolbeRuntimeData:
    return KKTKolbeRuntimeData(
        coordinator=coordinator,
        device=device,
        api_client=None,
        device_info={"category": "hood"},
        product_name="hermes_style_hood",
        device_type="hermes_style_hood",
        integration_mode="manual",
    )


def _local_coordinator(connected: bool) -> tuple[MagicMock, MagicMock]:
    device = MagicMock()
    device.async_disconnect = AsyncMock()
    device.async_connect = AsyncMock()
    device.is_connected = connected
    coordinator = MagicMock(spec=["device", "async_request_refresh", "async_add_listener", "last_update_success"])
    coordinator.device = device
    coordinator.async_request_refresh = AsyncMock()
    return device, coordinator


@pytest.mark.asyncio
async def test_no_button_for_cloud_only(hass: HomeAssistant, mock_config_entry) -> None:
    """Cloud-only devices have nothing to reconnect locally."""
    coordinator = MagicMock(spec=["device", "async_add_listener"])
    mock_config_entry.runtime_data = _runtime(None, coordinator)
    added: list = []
    await async_setup_entry(hass, mock_config_entry, added.extend)
    assert added == []


@pytest.mark.asyncio
async def test_press_reconnects(hass: HomeAssistant, mock_config_entry) -> None:
    """Pressing the button disconnects, connects and refreshes."""
    device, coordinator = _local_coordinator(connected=True)
    mock_config_entry.runtime_data = _runtime(device, coordinator)
    added: list = []
    await async_setup_entry(hass, mock_config_entry, added.extend)
    assert len(added) == 1
    button = added[0]
    assert isinstance(button, KKTKolbeReconnectButton)
    assert button.unique_id == f"{mock_config_entry.entry_id}_reconnect"
    assert button.available is True

    await button.async_press()
    device.async_disconnect.assert_awaited_once()
    device.async_connect.assert_awaited_once()
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_press_failure_raises(hass: HomeAssistant, mock_config_entry) -> None:
    """A failed reconnect is reported as a translated error."""
    device, coordinator = _local_coordinator(connected=False)
    mock_config_entry.runtime_data = _runtime(device, coordinator)
    button = KKTKolbeReconnectButton(mock_config_entry)
    with pytest.raises(HomeAssistantError) as err:
        await button.async_press()
    assert err.value.translation_key == "reconnect_failed"

    device.async_connect.side_effect = OSError("boom")
    with pytest.raises(HomeAssistantError):
        await button.async_press()
