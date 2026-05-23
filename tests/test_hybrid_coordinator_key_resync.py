"""Tests for self-healing local_key resync on Error 914 (auth failures).

When the local device raises KKTAuthenticationError — typically because the
SmartLife app re-paired the device and the cloud rotated the local_key — the
coordinator should pull the fresh key from the SmartLife client, update the
config entry, re-key the local device, and retry the local update once.
"""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kkt_kolbe.exceptions import KKTAuthenticationError


def _make_local_device(local_key: str = "stale_key_0000001") -> MagicMock:
    device = MagicMock()
    device.local_key = local_key
    device.ip_address = "192.168.1.100"
    device.async_disconnect = AsyncMock()
    return device


def _make_smartlife_device(local_key: str, ip: str = "192.168.1.100") -> MagicMock:
    sl = MagicMock()
    sl.device_id = "bf735dfe2ad64fba7cpyhn"
    sl.local_key = local_key
    sl.ip = ip
    return sl


def _make_coord(hass, mock_config_entry, *, local_device, smartlife_client):
    from custom_components.kkt_kolbe.hybrid_coordinator import KKTKolbeHybridCoordinator

    mock_config_entry.add_to_hass(hass)
    return KKTKolbeHybridCoordinator(
        hass=hass,
        device_id="bf735dfe2ad64fba7cpyhn",
        local_device=local_device,
        smartlife_client=smartlife_client,
        update_interval=timedelta(seconds=30),
        entry=mock_config_entry,
    )


@pytest.mark.asyncio
async def test_auth_error_triggers_key_resync_and_retry(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Auth error → SmartLife refresh → new key applied → local retry succeeds."""
    local_device = _make_local_device(local_key="stale_key_0000001")
    smartlife_client = MagicMock()
    smartlife_client.async_refresh_device = AsyncMock(
        return_value=_make_smartlife_device(local_key="fresh_key_0000002"),
    )

    coord = _make_coord(
        hass,
        mock_config_entry,
        local_device=local_device,
        smartlife_client=smartlife_client,
    )
    coord._initial_connect_done = True

    success_payload = {"source": "local", "dps": {"1": True}, "available": True}

    call_log: list[str] = []

    async def update_local_side_effect():
        call_log.append("call")
        if len(call_log) == 1:
            raise KKTAuthenticationError(device_id="bf735dfe", message="Error 914")
        return success_payload

    coord.async_update_local = AsyncMock(side_effect=update_local_side_effect)

    data = await coord._async_update_data()

    assert data is success_payload
    smartlife_client.async_refresh_device.assert_awaited_once_with("bf735dfe2ad64fba7cpyhn")
    local_device.async_disconnect.assert_awaited_once()
    assert local_device.local_key == "fresh_key_0000002"
    assert local_device._local_key_bytes is None
    assert coord.config_entry.data["local_key"] == "fresh_key_0000002"
    assert coord.local_consecutive_errors == 0


@pytest.mark.asyncio
async def test_auth_error_with_matching_cloud_key_does_not_apply(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """If SmartLife returns the same key we already have, do not mutate state."""
    local_device = _make_local_device(local_key="same_key_00000001")
    smartlife_client = MagicMock()
    smartlife_client.async_refresh_device = AsyncMock(
        return_value=_make_smartlife_device(local_key="same_key_00000001"),
    )

    coord = _make_coord(
        hass,
        mock_config_entry,
        local_device=local_device,
        smartlife_client=smartlife_client,
    )
    coord._initial_connect_done = True
    coord.async_update_local = AsyncMock(
        side_effect=KKTAuthenticationError(device_id="bf735dfe", message="Error 914"),
    )

    from homeassistant.helpers.update_coordinator import UpdateFailed

    with pytest.raises(UpdateFailed):
        await coord._async_update_data()

    smartlife_client.async_refresh_device.assert_awaited_once()
    local_device.async_disconnect.assert_not_awaited()
    assert local_device.local_key == "same_key_00000001"
    assert coord.local_consecutive_errors == 1


@pytest.mark.asyncio
async def test_auth_error_throttles_repeated_resync_attempts(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """A second auth error within the throttle window must not hit SmartLife again."""
    local_device = _make_local_device(local_key="stale_key_0000001")
    smartlife_client = MagicMock()
    smartlife_client.async_refresh_device = AsyncMock(
        return_value=_make_smartlife_device(local_key="same_key_00000001"),
    )

    coord = _make_coord(
        hass,
        mock_config_entry,
        local_device=local_device,
        smartlife_client=smartlife_client,
    )
    coord._initial_connect_done = True
    coord.async_update_local = AsyncMock(
        side_effect=KKTAuthenticationError(device_id="bf735dfe", message="Error 914"),
    )

    from homeassistant.helpers.update_coordinator import UpdateFailed

    with pytest.raises(UpdateFailed):
        await coord._async_update_data()
    # Reset coordinator into "local" mode and clear local error counter so the
    # second update again starts in the local branch.
    coord.current_mode = "local"
    coord.local_consecutive_errors = 0
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()

    # Refresh called only once because throttle is in effect.
    assert smartlife_client.async_refresh_device.await_count == 1


@pytest.mark.asyncio
async def test_auth_error_without_smartlife_client_falls_through(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Without a SmartLife client, auth errors cannot self-heal — counter advances."""
    local_device = _make_local_device(local_key="stale_key_0000001")

    coord = _make_coord(
        hass,
        mock_config_entry,
        local_device=local_device,
        smartlife_client=None,
    )
    coord._initial_connect_done = True
    coord.async_update_local = AsyncMock(
        side_effect=KKTAuthenticationError(device_id="bf735dfe", message="Error 914"),
    )

    await coord._async_update_data()

    local_device.async_disconnect.assert_not_awaited()
    assert local_device.local_key == "stale_key_0000001"
    assert coord.local_consecutive_errors == 1


@pytest.mark.asyncio
async def test_auth_error_throttle_window_uses_configured_interval(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Aging the throttle past its window allows another resync attempt."""
    local_device = _make_local_device(local_key="stale_key_0000001")
    smartlife_client = MagicMock()
    smartlife_client.async_refresh_device = AsyncMock(
        return_value=_make_smartlife_device(local_key="same_key_00000001"),
    )

    coord = _make_coord(
        hass,
        mock_config_entry,
        local_device=local_device,
        smartlife_client=smartlife_client,
    )
    coord._initial_connect_done = True
    coord.async_update_local = AsyncMock(
        side_effect=KKTAuthenticationError(device_id="bf735dfe", message="Error 914"),
    )

    from homeassistant.helpers.update_coordinator import UpdateFailed

    with pytest.raises(UpdateFailed):
        await coord._async_update_data()
    # Pretend the throttle window has fully elapsed.
    coord._last_key_resync_attempt = datetime.now() - (coord._key_resync_min_interval + timedelta(seconds=1))
    coord.current_mode = "local"
    coord.local_consecutive_errors = 0
    with pytest.raises(UpdateFailed):
        await coord._async_update_data()

    assert smartlife_client.async_refresh_device.await_count == 2
