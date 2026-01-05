"""Test the KKT Kolbe exceptions."""
from __future__ import annotations

import pytest

from custom_components.kkt_kolbe.exceptions import (
    KKTKolbeError,
    KKTConnectionError,
    KKTAuthenticationError,
    KKTTimeoutError,
    KKTDeviceError,
    KKTConfigurationError,
    KKTDiscoveryError,
    KKTServiceError,
    KKTDataPointError,
    KKTRateLimitError,
)


class TestKKTKolbeError:
    """Test the base KKTKolbeError exception."""

    def test_default_message(self) -> None:
        """Test default error message."""
        error = KKTKolbeError()
        assert "unknown_error" in str(error)
        assert error.translation_key == "unknown_error"

    def test_custom_translation_key(self) -> None:
        """Test custom translation key."""
        error = KKTKolbeError(translation_key="custom_error")
        assert error.translation_key == "custom_error"

    def test_translation_placeholders(self) -> None:
        """Test translation placeholders."""
        error = KKTKolbeError(
            translation_key="test",
            translation_placeholders={"key": "value"}
        )
        assert error.translation_placeholders == {"key": "value"}


class TestKKTConnectionError:
    """Test the KKTConnectionError exception."""

    def test_with_all_params(self) -> None:
        """Test with all parameters."""
        error = KKTConnectionError(
            operation="connect",
            device_id="bf735dfe2ad64fba7cpyhn",
            reason="Network unreachable"
        )
        assert "connect" in str(error)
        assert "bf735dfe" in str(error)
        assert "Network unreachable" in str(error)
        assert error.translation_key == "connection_failed"

    def test_with_device_id_only(self) -> None:
        """Test with device ID only."""
        error = KKTConnectionError(device_id="bf735dfe2ad64fba7cpyhn")
        assert "bf735dfe2ad64fba7cpyhn" in str(error)

    def test_without_params(self) -> None:
        """Test without parameters."""
        error = KKTConnectionError()
        # Should have some form of connection error message
        assert "connect" in str(error).lower() or "failed" in str(error).lower()


class TestKKTAuthenticationError:
    """Test the KKTAuthenticationError exception."""

    def test_with_device_id(self) -> None:
        """Test with device ID."""
        error = KKTAuthenticationError(device_id="bf735dfe2ad64fba7cpyhn")
        assert "bf735dfe" in str(error)
        # Message should mention key or authentication
        assert "key" in str(error).lower() or "auth" in str(error).lower()
        assert error.translation_key == "authentication_failed"

    def test_without_device_id(self) -> None:
        """Test without device ID."""
        error = KKTAuthenticationError()
        # Should have authentication in the message
        error_str = str(error).lower()
        assert "authentication" in error_str or "auth" in error_str or "key" in error_str


class TestKKTTimeoutError:
    """Test the KKTTimeoutError exception."""

    def test_with_all_params(self) -> None:
        """Test with all parameters."""
        error = KKTTimeoutError(
            operation="status",
            device_id="bf735dfe2ad64fba7cpyhn",
            timeout=5.0
        )
        assert "status" in str(error)
        assert "5" in str(error)
        assert error.translation_key == "timeout"

    def test_with_data_point(self) -> None:
        """Test with data point."""
        error = KKTTimeoutError(operation="set", data_point=10)
        assert error.data_point == 10

    def test_without_params(self) -> None:
        """Test without parameters."""
        error = KKTTimeoutError()
        # Should have timeout in the message
        assert "timeout" in str(error).lower() or "timed out" in str(error).lower()


class TestKKTDeviceError:
    """Test the KKTDeviceError exception."""

    def test_with_error_code_and_message(self) -> None:
        """Test with error code and device message."""
        error = KKTDeviceError(error_code=500, device_message="Internal error")
        assert "500" in str(error)
        assert "Internal error" in str(error)
        assert error.translation_key == "device_error"

    def test_with_error_code_only(self) -> None:
        """Test with error code only."""
        error = KKTDeviceError(error_code=404)
        assert "404" in str(error)

    def test_without_params(self) -> None:
        """Test without parameters."""
        error = KKTDeviceError()
        assert "error" in str(error).lower()


class TestKKTConfigurationError:
    """Test the KKTConfigurationError exception."""

    def test_with_config_field(self) -> None:
        """Test with config field."""
        error = KKTConfigurationError(config_field="local_key")
        assert "local_key" in str(error)
        assert error.translation_key == "configuration_error"

    def test_without_config_field(self) -> None:
        """Test without config field."""
        error = KKTConfigurationError()
        assert "configuration" in str(error).lower() or "config" in str(error).lower()


class TestKKTDiscoveryError:
    """Test the KKTDiscoveryError exception."""

    def test_with_discovery_method(self) -> None:
        """Test with discovery method."""
        error = KKTDiscoveryError(discovery_method="mDNS")
        assert "mDNS" in str(error)
        assert error.translation_key == "discovery_failed"

    def test_without_discovery_method(self) -> None:
        """Test without discovery method."""
        error = KKTDiscoveryError()
        assert "discovery" in str(error).lower()


class TestKKTServiceError:
    """Test the KKTServiceError exception."""

    def test_with_service_and_reason(self) -> None:
        """Test with service name and reason."""
        error = KKTServiceError(
            service_name="set_fan_speed",
            reason="Device offline"
        )
        assert "set_fan_speed" in str(error)
        assert "Device offline" in str(error)
        assert error.translation_key == "service_failed"

    def test_with_service_only(self) -> None:
        """Test with service name only."""
        error = KKTServiceError(service_name="reset_filter")
        assert "reset_filter" in str(error)

    def test_without_params(self) -> None:
        """Test without parameters."""
        error = KKTServiceError()
        assert "failed" in str(error).lower() or "service" in str(error).lower()


class TestKKTDataPointError:
    """Test the KKTDataPointError exception."""

    def test_with_all_params(self) -> None:
        """Test with all parameters."""
        error = KKTDataPointError(
            dp=10,
            operation="set",
            value="high",
            device_id="bf735dfe2ad64fba7cpyhn",
            reason="Invalid value"
        )
        assert "10" in str(error)
        assert "set" in str(error)
        assert "high" in str(error)
        assert error.translation_key == "data_point_error"

    def test_with_data_point_alias(self) -> None:
        """Test with data_point parameter alias."""
        error = KKTDataPointError(data_point=15)
        assert error.dp == 15

    def test_dp_takes_precedence(self) -> None:
        """Test that dp takes precedence over data_point."""
        error = KKTDataPointError(dp=10, data_point=20)
        assert error.dp == 10

    def test_without_params(self) -> None:
        """Test without parameters."""
        error = KKTDataPointError()
        # Should mention data point or operation failed
        error_str = str(error).lower()
        assert "data" in error_str or "point" in error_str or "failed" in error_str


class TestKKTRateLimitError:
    """Test the KKTRateLimitError exception (HA 2025.12+ feature)."""

    def test_with_retry_after(self) -> None:
        """Test with retry_after parameter."""
        error = KKTRateLimitError(retry_after=60)
        assert error.retry_after == 60
        assert "60" in str(error)
        assert error.translation_key == "rate_limit_exceeded"

    def test_with_device_id(self) -> None:
        """Test with device ID."""
        error = KKTRateLimitError(
            retry_after=30,
            device_id="bf735dfe2ad64fba7cpyhn"
        )
        assert error.retry_after == 30
        assert error.device_id == "bf735dfe2ad64fba7cpyhn"

    def test_without_retry_after(self) -> None:
        """Test without retry_after parameter."""
        error = KKTRateLimitError()
        assert error.retry_after is None
        assert "rate limit" in str(error).lower()

    def test_retry_after_in_placeholders(self) -> None:
        """Test that retry_after is in translation placeholders."""
        error = KKTRateLimitError(retry_after=120)
        assert "retry_after" in error.translation_placeholders
        assert error.translation_placeholders["retry_after"] == "120"

    def test_custom_message(self) -> None:
        """Test with custom message."""
        error = KKTRateLimitError(
            retry_after=45,
            message="API quota exceeded"
        )
        assert error.retry_after == 45
        assert "API quota exceeded" in str(error)


class TestExceptionInheritance:
    """Test exception inheritance."""

    def test_all_exceptions_inherit_from_base(self) -> None:
        """Test that all exceptions inherit from KKTKolbeError."""
        exceptions = [
            KKTConnectionError(),
            KKTAuthenticationError(),
            KKTTimeoutError(),
            KKTDeviceError(),
            KKTConfigurationError(),
            KKTDiscoveryError(),
            KKTServiceError(),
            KKTDataPointError(),
            KKTRateLimitError(),
        ]
        for exc in exceptions:
            assert isinstance(exc, KKTKolbeError)

    def test_exceptions_have_translation_key(self) -> None:
        """Test that all exceptions have translation keys."""
        exceptions = [
            KKTConnectionError(),
            KKTAuthenticationError(),
            KKTTimeoutError(),
            KKTDeviceError(),
            KKTConfigurationError(),
            KKTDiscoveryError(),
            KKTServiceError(),
            KKTDataPointError(),
            KKTRateLimitError(),
        ]
        for exc in exceptions:
            assert hasattr(exc, "translation_key")
            assert exc.translation_key is not None
