"""Regression tests for reauth, reconfigure and options flow fixes."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import selector
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kkt_kolbe.const import DOMAIN

DEVICE_ID = "bf735dfe2ad64fba7cpyhn"
OLD_KEY = "0000000000000000"
NEW_KEY = "1234567890abcdef"
NEW_TOKENS = {"access_token": "fresh", "refresh_token": "fresh_r", "user_code": "EU12345678"}


@pytest.fixture
def no_setup() -> Generator[None]:
    """Keep reloads from running the real setup and unload."""
    with (
        patch("custom_components.kkt_kolbe.async_setup_entry", return_value=True),
        patch("custom_components.kkt_kolbe.async_unload_entry", return_value=True),
    ):
        yield


@pytest.fixture
def sharing_client() -> Generator[MagicMock]:
    """Patch TuyaSharingClient where the flows import it from."""
    client = MagicMock()
    client.async_generate_qr_code = AsyncMock(return_value="tuyaSmart--qrLogin?token=secret")
    client.async_poll_login_result = AsyncMock(return_value=MagicMock(success=True, user_id="user_123456"))
    cloud_device = MagicMock(device_id=DEVICE_ID, local_key=NEW_KEY, ip="84.1.2.3", product_id="ypaixllljc2dcpae")
    client.async_get_devices = AsyncMock(return_value=[cloud_device])
    client.get_token_info_for_storage = MagicMock(return_value=NEW_TOKENS)
    with patch(
        "custom_components.kkt_kolbe.clients.tuya_sharing_client.TuyaSharingClient", return_value=client
    ) as client_class:
        client.client_class = client_class
        yield client


async def test_local_key_reauth_writes_access_token(hass: HomeAssistant, no_setup: None) -> None:
    """Setup reads access_token first, so reauth must replace it too."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DEVICE_ID,
        version=2,
        data={"device_id": DEVICE_ID, "ip_address": "192.168.1.100", "local_key": OLD_KEY, CONF_ACCESS_TOKEN: OLD_KEY},
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "custom_components.kkt_kolbe.config_flow.KKTKolbeConfigFlow._test_device_connection",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"local_key": NEW_KEY})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["local_key"] == NEW_KEY
    assert entry.data[CONF_ACCESS_TOKEN] == NEW_KEY


async def test_smartlife_child_reauth_stores_tokens_on_account(
    hass: HomeAssistant, no_setup: None, sharing_client: MagicMock
) -> None:
    """A device entry reads its tokens from the account entry, so they go there."""
    account = MockConfigEntry(
        domain=DOMAIN,
        unique_id="smartlife_account_user_123456",
        version=2,
        data={
            "entry_type": "account",
            "smartlife_user_code": "EU12345678",
            "smartlife_app_schema": "haauthorize",
            "smartlife_token_info": {"access_token": "expired", "user_code": "EU12345678"},
        },
    )
    account.add_to_hass(hass)
    child = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DEVICE_ID,
        version=2,
        data={
            "entry_type": "device",
            "setup_mode": "smartlife",
            "parent_entry_id": account.entry_id,
            "device_id": DEVICE_ID,
            "ip_address": "192.168.1.100",
            "local_key": OLD_KEY,
            CONF_ACCESS_TOKEN: OLD_KEY,
        },
    )
    child.add_to_hass(hass)

    result = await child.start_reauth_flow(hass)
    assert result["step_id"] == "smartlife_reauth"
    # The user code lives on the account entry and is pre-filled from there
    schema_keys = {str(key): key for key in result["data_schema"].schema}
    assert schema_keys["user_code"].default() == "EU12345678"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"user_code": "EU12345678"})
    assert result["step_id"] == "smartlife_scan"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert account.data["smartlife_token_info"] == NEW_TOKENS
    assert "smartlife_token_info" not in child.data
    assert child.data["local_key"] == NEW_KEY
    assert child.data[CONF_ACCESS_TOKEN] == NEW_KEY
    # The cloud reports the WAN address; the LAN address must stay
    assert child.data["ip_address"] == "192.168.1.100"


async def test_reconfigure_api_empty_secret_keeps_stored(hass: HomeAssistant, no_setup: None) -> None:
    """The form says an empty secret keeps the stored one."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DEVICE_ID,
        version=2,
        data={
            "device_id": DEVICE_ID,
            "ip_address": "192.168.1.100",
            "local_key": OLD_KEY,
            "api_enabled": True,
            "api_client_id": "client_id_123",
            "api_client_secret": "secret_secret_secret_1",
            "api_endpoint": "https://openapi.tuyaeu.com",
            "integration_mode": "hybrid",
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"reconfigure_option": "api"})
    assert result["step_id"] == "reconfigure_api"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "api_enabled": True,
            "api_client_id": "client_id_123",
            "api_client_secret": "",
            "api_endpoint": "https://openapi.tuyaeu.com",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["api_client_secret"] == "secret_secret_secret_1"


async def test_renew_token_renders_qr_code_locally(
    hass: HomeAssistant, no_setup: None, sharing_client: MagicMock
) -> None:
    """The QR login token must not be sent to an external image service."""
    account = MockConfigEntry(
        domain=DOMAIN,
        unique_id="smartlife_account_user_123456",
        version=2,
        data={
            "entry_type": "account",
            "smartlife_user_code": "EU12345678",
            "smartlife_app_schema": "haauthorize",
            "smartlife_token_info": {"access_token": "expired"},
        },
    )
    account.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(account.entry_id)
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": "renew_token"})

    assert result["step_id"] == "renew_token"
    assert not result["errors"]
    assert "qr_code_url" not in (result["description_placeholders"] or {})
    qr_selector = next(iter(result["data_schema"].schema.values()))
    assert isinstance(qr_selector, selector.QrCodeSelector)
    assert qr_selector.config["data"] == "tuyaSmart--qrLogin?token=secret"
    # The stored app schema is reused
    assert sharing_client.client_class.call_args.kwargs["app_schema"] == "haauthorize"

    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert account.data["smartlife_token_info"] == NEW_TOKENS
