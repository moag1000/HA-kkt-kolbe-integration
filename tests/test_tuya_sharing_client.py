"""Test the TuyaSharingClient for SmartLife/Tuya Smart integration."""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kkt_kolbe.clients.tuya_sharing_client import (
    TuyaSharingAuthResult,
    TuyaSharingClient,
    TuyaSharingDevice,
)
from custom_components.kkt_kolbe.const import (
    QR_CODE_FORMAT,
    SMARTLIFE_CLIENT_ID,
    SMARTLIFE_SCHEMA,
    TUYA_SMART_SCHEMA,
)
from custom_components.kkt_kolbe.exceptions import (
    KKTAuthenticationError,
    KKTConnectionError,
    KKTTimeoutError,
)


# === FIXTURES ===


@pytest.fixture
def mock_login_control():
    """Create a mock LoginControl instance."""
    mock = MagicMock()
    mock.qr_code.return_value = {
        "success": True,
        "result": {"qrcode": "test_qr_token_12345"},
    }
    mock.login_result.return_value = (
        True,
        {
            "token_info": {
                "uid": "user_123456",
                "access_token": "access_token_abc",
                "refresh_token": "refresh_token_xyz",
                "expire_time": 7200,
            },
            "terminal_id": "terminal_001",
            "endpoint": "https://openapi.tuyaeu.com",
            "t": 1700000000,
        },
    )
    return mock


@pytest.fixture
def mock_manager():
    """Create a mock Manager instance."""
    mock = MagicMock()
    mock.device_map = {}
    mock.update_device_cache = MagicMock()
    return mock


@pytest.fixture
def mock_customer_device():
    """Create a mock CustomerDevice from tuya_sharing."""
    device = MagicMock()
    device.id = "bf735dfe2ad64fba7cpyhn"
    device.name = "KKT HERMES Hood"
    device.local_key = "1234567890abcdef"
    device.product_id = "ypaixllljc2dcpae"
    device.product_name = "KKT Kolbe HERMES"
    device.category = "yyj"
    device.ip = "192.168.1.100"
    device.online = True
    device.support_local = True
    return device


@pytest.fixture
def sample_token_info() -> dict[str, Any]:
    """Create sample token info for storage tests."""
    return {
        "terminal_id": "terminal_001",
        "endpoint": "https://openapi.tuyaeu.com",
        "access_token": "access_token_abc",
        "refresh_token": "refresh_token_xyz",
        "expire_time": 7200,
        "uid": "user_123456",
        "user_code": "EU12345678",
        "app_schema": SMARTLIFE_SCHEMA,
        "timestamp": 1700000000,
    }


# === TuyaSharingDevice TESTS ===


class TestTuyaSharingDevice:
    """Tests for TuyaSharingDevice dataclass."""

    def test_from_customer_device(self, mock_customer_device):
        """Test creating TuyaSharingDevice from CustomerDevice."""
        device = TuyaSharingDevice.from_customer_device(mock_customer_device)

        assert device.device_id == "bf735dfe2ad64fba7cpyhn"
        assert device.name == "KKT HERMES Hood"
        assert device.local_key == "1234567890abcdef"
        assert device.product_id == "ypaixllljc2dcpae"
        assert device.product_name == "KKT Kolbe HERMES"
        assert device.category == "yyj"
        assert device.ip == "192.168.1.100"
        assert device.online is True
        assert device.support_local is True

    def test_from_customer_device_missing_optional(self):
        """Test handling of missing optional attributes."""
        device = MagicMock()
        device.id = "test_device"
        device.name = "Test Device"
        device.product_id = "test_product"
        device.category = "yyj"
        # Simulate missing attributes
        del device.local_key
        del device.product_name
        del device.ip
        del device.online
        del device.support_local

        result = TuyaSharingDevice.from_customer_device(device)

        assert result.device_id == "test_device"
        assert result.local_key == ""  # Default when missing
        assert result.product_name == ""
        assert result.ip is None
        assert result.online is False
        assert result.support_local is True


# === TuyaSharingClient INITIALIZATION TESTS ===


class TestTuyaSharingClientInit:
    """Tests for TuyaSharingClient initialization."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, hass: HomeAssistant):
        """Test basic client initialization."""
        client = TuyaSharingClient(
            hass=hass,
            user_code="EU12345678",
            app_schema=SMARTLIFE_SCHEMA,
        )

        assert client.user_code == "EU12345678"
        assert client.app_schema == SMARTLIFE_SCHEMA
        assert client.is_authenticated is False
        assert client._qr_token is None

    @pytest.mark.asyncio
    async def test_client_with_tuya_smart_schema(self, hass: HomeAssistant):
        """Test client with Tuya Smart app schema."""
        client = TuyaSharingClient(
            hass=hass,
            user_code="CN12345678",
            app_schema=TUYA_SMART_SCHEMA,
        )

        assert client.app_schema == TUYA_SMART_SCHEMA

    @pytest.mark.asyncio
    async def test_client_repr(self, hass: HomeAssistant):
        """Test string representation of client."""
        client = TuyaSharingClient(
            hass=hass,
            user_code="EU12345678",
            app_schema=SMARTLIFE_SCHEMA,
        )

        repr_str = repr(client)
        assert "EU12..." in repr_str
        assert "smartlife" in repr_str
        assert "authenticated=False" in repr_str


# === QR CODE GENERATION TESTS ===


class TestQRCodeGeneration:
    """Tests for QR code generation."""

    @pytest.mark.asyncio
    async def test_generate_qr_code_success(
        self, hass: HomeAssistant, mock_login_control
    ):
        """Test successful QR code generation."""
        client = TuyaSharingClient(hass, "EU12345678")

        with patch(
            "tuya_sharing.LoginControl",
            return_value=mock_login_control,
        ):
            qr_code = await client.async_generate_qr_code()

        assert "tuyaSmart--qrLogin?token=" in qr_code
        assert "test_qr_token_12345" in qr_code
        assert client._qr_token == "test_qr_token_12345"

    @pytest.mark.asyncio
    async def test_generate_qr_code_api_failure(self, hass: HomeAssistant):
        """Test QR code generation when API returns failure."""
        client = TuyaSharingClient(hass, "EU12345678")

        mock_lc = MagicMock()
        mock_lc.qr_code.return_value = {
            "success": False,
            "code": "1001",
            "msg": "Invalid user code",
        }

        with patch(
            "tuya_sharing.LoginControl",
            return_value=mock_lc,
        ):
            with pytest.raises(KKTAuthenticationError) as exc_info:
                await client.async_generate_qr_code()

        assert "Invalid user code" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_qr_code_network_error(self, hass: HomeAssistant):
        """Test QR code generation with network error."""
        client = TuyaSharingClient(hass, "EU12345678")

        mock_lc = MagicMock()
        mock_lc.qr_code.side_effect = Exception("Network timeout")

        with patch(
            "tuya_sharing.LoginControl",
            return_value=mock_lc,
        ):
            with pytest.raises(KKTConnectionError) as exc_info:
                await client.async_generate_qr_code()

        # The reason is stored in the exception's reason attribute
        assert exc_info.value.reason == "Network timeout"

    @pytest.mark.asyncio
    async def test_generate_qr_code_no_token(self, hass: HomeAssistant):
        """Test QR code generation when no token in response."""
        client = TuyaSharingClient(hass, "EU12345678")

        mock_lc = MagicMock()
        mock_lc.qr_code.return_value = {
            "success": True,
            "result": {},  # No qrcode field
        }

        with patch(
            "tuya_sharing.LoginControl",
            return_value=mock_lc,
        ):
            with pytest.raises(KKTAuthenticationError) as exc_info:
                await client.async_generate_qr_code()

        assert "No QR token" in str(exc_info.value)


# === LOGIN POLLING TESTS ===


class TestLoginPolling:
    """Tests for login result polling."""

    @pytest.mark.asyncio
    async def test_poll_login_result_success(
        self, hass: HomeAssistant, mock_login_control
    ):
        """Test successful login polling."""
        client = TuyaSharingClient(hass, "EU12345678")

        with patch(
            "tuya_sharing.LoginControl",
            return_value=mock_login_control,
        ):
            await client.async_generate_qr_code()
            auth_result = await client.async_poll_login_result(timeout=5, poll_interval=0.1)

        assert auth_result.success is True
        assert auth_result.user_id == "user_123456"
        assert auth_result.access_token == "access_token_abc"
        assert auth_result.refresh_token == "refresh_token_xyz"
        assert auth_result.terminal_id == "terminal_001"
        assert auth_result.endpoint == "https://openapi.tuyaeu.com"
        assert client.is_authenticated is True

    @pytest.mark.asyncio
    async def test_poll_login_without_qr_code(self, hass: HomeAssistant):
        """Test polling without generating QR code first."""
        client = TuyaSharingClient(hass, "EU12345678")

        with pytest.raises(KKTAuthenticationError) as exc_info:
            await client.async_poll_login_result()

        assert "async_generate_qr_code" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_poll_login_timeout(self, hass: HomeAssistant, mock_login_control):
        """Test login polling timeout."""
        # Modify mock to never return success
        mock_login_control.login_result.return_value = (
            False,
            {"code": "pending", "msg": "Waiting for scan"},
        )

        client = TuyaSharingClient(hass, "EU12345678")

        with patch(
            "tuya_sharing.LoginControl",
            return_value=mock_login_control,
        ):
            await client.async_generate_qr_code()

            with pytest.raises(KKTTimeoutError) as exc_info:
                await client.async_poll_login_result(timeout=0.3, poll_interval=0.1)

        assert "qr_login" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_poll_login_user_denied(self, hass: HomeAssistant, mock_login_control):
        """Test login polling when user denies authorization."""
        mock_login_control.login_result.return_value = (
            False,
            {"code": "login_failed", "msg": "User denied access"},
        )

        client = TuyaSharingClient(hass, "EU12345678")

        with patch(
            "tuya_sharing.LoginControl",
            return_value=mock_login_control,
        ):
            await client.async_generate_qr_code()

            with pytest.raises(KKTAuthenticationError) as exc_info:
                await client.async_poll_login_result(timeout=5, poll_interval=0.1)

        assert "denied" in str(exc_info.value).lower()


# === DEVICE RETRIEVAL TESTS ===


class TestDeviceRetrieval:
    """Tests for device retrieval."""

    @pytest.mark.asyncio
    async def test_get_devices_success(
        self, hass: HomeAssistant, mock_login_control, mock_manager, mock_customer_device
    ):
        """Test successful device retrieval."""
        mock_manager.device_map = {"device_1": mock_customer_device}

        client = TuyaSharingClient(hass, "EU12345678")

        with patch(
            "tuya_sharing.LoginControl",
            return_value=mock_login_control,
        ):
            await client.async_generate_qr_code()
            await client.async_poll_login_result(timeout=5, poll_interval=0.1)

        with patch(
            "tuya_sharing.Manager",
            return_value=mock_manager,
        ):
            with patch("tuya_sharing.SharingTokenListener"):
                devices = await client.async_get_devices()

        assert len(devices) == 1
        assert devices[0].device_id == "bf735dfe2ad64fba7cpyhn"
        assert devices[0].local_key == "1234567890abcdef"

    @pytest.mark.asyncio
    async def test_get_devices_not_authenticated(self, hass: HomeAssistant):
        """Test device retrieval without authentication."""
        client = TuyaSharingClient(hass, "EU12345678")

        with pytest.raises(KKTAuthenticationError) as exc_info:
            await client.async_get_devices()

        assert "authenticate" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_devices_api_error(
        self, hass: HomeAssistant, mock_login_control
    ):
        """Test device retrieval with API error."""
        client = TuyaSharingClient(hass, "EU12345678")

        with patch(
            "tuya_sharing.LoginControl",
            return_value=mock_login_control,
        ):
            await client.async_generate_qr_code()
            await client.async_poll_login_result(timeout=5, poll_interval=0.1)

        mock_mgr = MagicMock()
        mock_mgr.update_device_cache.side_effect = Exception("API connection failed")

        with patch(
            "tuya_sharing.Manager",
            return_value=mock_mgr,
        ):
            with patch("tuya_sharing.SharingTokenListener"):
                with pytest.raises(KKTConnectionError) as exc_info:
                    await client.async_get_devices()

        # The reason is stored in the exception's reason attribute
        assert exc_info.value.reason == "API connection failed"

    @pytest.mark.asyncio
    async def test_refresh_device(
        self, hass: HomeAssistant, mock_login_control, mock_manager, mock_customer_device
    ):
        """Test refreshing a single device."""
        mock_manager.device_map = {"device_1": mock_customer_device}

        client = TuyaSharingClient(hass, "EU12345678")

        with patch(
            "tuya_sharing.LoginControl",
            return_value=mock_login_control,
        ):
            await client.async_generate_qr_code()
            await client.async_poll_login_result(timeout=5, poll_interval=0.1)

        with patch(
            "tuya_sharing.Manager",
            return_value=mock_manager,
        ):
            with patch("tuya_sharing.SharingTokenListener"):
                device = await client.async_refresh_device("bf735dfe2ad64fba7cpyhn")

        assert device is not None
        assert device.device_id == "bf735dfe2ad64fba7cpyhn"

    @pytest.mark.asyncio
    async def test_refresh_device_not_found(
        self, hass: HomeAssistant, mock_login_control, mock_manager, mock_customer_device
    ):
        """Test refreshing a device that doesn't exist."""
        mock_manager.device_map = {"device_1": mock_customer_device}

        client = TuyaSharingClient(hass, "EU12345678")

        with patch(
            "tuya_sharing.LoginControl",
            return_value=mock_login_control,
        ):
            await client.async_generate_qr_code()
            await client.async_poll_login_result(timeout=5, poll_interval=0.1)

        with patch(
            "tuya_sharing.Manager",
            return_value=mock_manager,
        ):
            with patch("tuya_sharing.SharingTokenListener"):
                device = await client.async_refresh_device("nonexistent_device")

        assert device is None


# === TOKEN STORAGE TESTS ===


class TestTokenStorage:
    """Tests for token storage and restoration."""

    @pytest.mark.asyncio
    async def test_get_token_info_for_storage(
        self, hass: HomeAssistant, mock_login_control
    ):
        """Test getting token info for storage."""
        client = TuyaSharingClient(hass, "EU12345678")

        with patch(
            "tuya_sharing.LoginControl",
            return_value=mock_login_control,
        ):
            await client.async_generate_qr_code()
            await client.async_poll_login_result(timeout=5, poll_interval=0.1)

        token_info = client.get_token_info_for_storage()

        assert token_info["user_code"] == "EU12345678"
        assert token_info["app_schema"] == SMARTLIFE_SCHEMA
        assert token_info["access_token"] == "access_token_abc"
        assert token_info["refresh_token"] == "refresh_token_xyz"
        assert token_info["terminal_id"] == "terminal_001"
        assert token_info["uid"] == "user_123456"

    @pytest.mark.asyncio
    async def test_get_token_info_not_authenticated(self, hass: HomeAssistant):
        """Test getting token info without authentication."""
        client = TuyaSharingClient(hass, "EU12345678")

        token_info = client.get_token_info_for_storage()

        assert token_info == {}

    @pytest.mark.asyncio
    async def test_from_stored_tokens(
        self, hass: HomeAssistant, sample_token_info
    ):
        """Test restoring client from stored tokens."""
        client = await TuyaSharingClient.async_from_stored_tokens(
            hass, sample_token_info
        )

        assert client.user_code == "EU12345678"
        assert client.app_schema == SMARTLIFE_SCHEMA
        assert client.is_authenticated is True
        assert client._auth_result.user_id == "user_123456"
        assert client._auth_result.access_token == "access_token_abc"

    @pytest.mark.asyncio
    async def test_from_stored_tokens_missing_user_code(self, hass: HomeAssistant):
        """Test restoring client with missing user_code."""
        token_info = {
            "access_token": "abc",
            "refresh_token": "xyz",
            # Missing user_code
        }

        with pytest.raises(KKTAuthenticationError) as exc_info:
            await TuyaSharingClient.async_from_stored_tokens(hass, token_info)

        assert "user_code" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_from_stored_tokens_roundtrip(
        self, hass: HomeAssistant, mock_login_control
    ):
        """Test full storage/restore roundtrip."""
        # Create and authenticate client
        client1 = TuyaSharingClient(hass, "EU12345678")

        with patch(
            "tuya_sharing.LoginControl",
            return_value=mock_login_control,
        ):
            await client1.async_generate_qr_code()
            await client1.async_poll_login_result(timeout=5, poll_interval=0.1)

        # Store tokens
        token_info = client1.get_token_info_for_storage()

        # Restore to new client
        client2 = await TuyaSharingClient.async_from_stored_tokens(hass, token_info)

        # Verify restored client
        assert client2.user_code == client1.user_code
        assert client2.is_authenticated is True
        assert client2._auth_result.access_token == client1._auth_result.access_token


# === TOKEN VALIDATION TESTS ===


class TestTokenValidation:
    """Tests for token validation."""

    @pytest.mark.asyncio
    async def test_validate_tokens_success(
        self, hass: HomeAssistant, mock_login_control, mock_manager, mock_customer_device
    ):
        """Test successful token validation."""
        mock_manager.device_map = {"device_1": mock_customer_device}

        client = TuyaSharingClient(hass, "EU12345678")

        with patch(
            "tuya_sharing.LoginControl",
            return_value=mock_login_control,
        ):
            await client.async_generate_qr_code()
            await client.async_poll_login_result(timeout=5, poll_interval=0.1)

        with patch(
            "tuya_sharing.Manager",
            return_value=mock_manager,
        ):
            with patch("tuya_sharing.SharingTokenListener"):
                is_valid = await client.async_validate_tokens()

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validate_tokens_not_authenticated(self, hass: HomeAssistant):
        """Test token validation without authentication."""
        client = TuyaSharingClient(hass, "EU12345678")

        is_valid = await client.async_validate_tokens()

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validate_tokens_expired(
        self, hass: HomeAssistant, sample_token_info
    ):
        """Test token validation with expired tokens."""
        client = await TuyaSharingClient.async_from_stored_tokens(
            hass, sample_token_info
        )

        mock_mgr = MagicMock()
        mock_mgr.update_device_cache.side_effect = Exception("Token expired")

        with patch(
            "tuya_sharing.Manager",
            return_value=mock_mgr,
        ):
            with patch("tuya_sharing.SharingTokenListener"):
                is_valid = await client.async_validate_tokens()

        assert is_valid is False


# === CLIENT CLEANUP TESTS ===


class TestClientCleanup:
    """Tests for client cleanup."""

    @pytest.mark.asyncio
    async def test_async_close(self, hass: HomeAssistant, mock_login_control, mock_manager):
        """Test client cleanup."""
        client = TuyaSharingClient(hass, "EU12345678")

        with patch(
            "tuya_sharing.LoginControl",
            return_value=mock_login_control,
        ):
            await client.async_generate_qr_code()
            await client.async_poll_login_result(timeout=5, poll_interval=0.1)

        # Manually set manager
        client._manager = mock_manager

        await client.async_close()

        assert client._manager is None
        assert client._login_control is None

    @pytest.mark.asyncio
    async def test_async_close_with_unload(
        self, hass: HomeAssistant, mock_login_control
    ):
        """Test client cleanup calls manager.unload if available."""
        client = TuyaSharingClient(hass, "EU12345678")

        with patch(
            "tuya_sharing.LoginControl",
            return_value=mock_login_control,
        ):
            await client.async_generate_qr_code()
            await client.async_poll_login_result(timeout=5, poll_interval=0.1)

        mock_mgr = MagicMock()
        mock_mgr.unload = MagicMock()
        client._manager = mock_mgr

        await client.async_close()

        mock_mgr.unload.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_close_no_manager(self, hass: HomeAssistant):
        """Test client cleanup without manager."""
        client = TuyaSharingClient(hass, "EU12345678")

        # Should not raise
        await client.async_close()

        assert client._manager is None


# === AUTH RESULT TESTS ===


class TestTuyaSharingAuthResult:
    """Tests for TuyaSharingAuthResult dataclass."""

    def test_auth_result_success(self):
        """Test successful auth result."""
        result = TuyaSharingAuthResult(
            success=True,
            user_id="user_123",
            terminal_id="terminal_001",
            endpoint="https://api.example.com",
            access_token="token_abc",
            refresh_token="refresh_xyz",
            expire_time=7200,
            timestamp=1700000000,
        )

        assert result.success is True
        assert result.user_id == "user_123"
        assert result.error_message is None

    def test_auth_result_failure(self):
        """Test failed auth result."""
        result = TuyaSharingAuthResult(
            success=False,
            error_message="Authentication denied",
        )

        assert result.success is False
        assert result.error_message == "Authentication denied"
        assert result.access_token is None
