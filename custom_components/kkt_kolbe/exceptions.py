"""Custom exceptions for KKT Kolbe integration."""
from __future__ import annotations

from typing import Any


class KKTKolbeError(Exception):
    """Base exception for KKT Kolbe integration."""

    def __init__(self, message: str = "Unknown KKT Kolbe error occurred") -> None:
        self.message = message
        super().__init__(self.message)


class KKTConnectionError(KKTKolbeError):
    """Connection to KKT Kolbe device failed."""

    def __init__(
        self,
        operation: str | None = None,
        device_id: str | None = None,
        reason: str | None = None,
        message: str | None = None,
    ) -> None:
        self.operation = operation
        self.device_id = device_id
        self.reason = reason
        if message is None:
            if operation and device_id and reason:
                message = f"Failed to {operation} on device {device_id}: {reason}"
            elif operation and device_id:
                message = f"Failed to {operation} on device {device_id}"
            elif device_id:
                message = f"Failed to connect to KKT Kolbe device {device_id}"
            else:
                message = "Failed to connect to KKT Kolbe device"
        super().__init__(message)


class KKTAuthenticationError(KKTKolbeError):
    """Authentication with KKT Kolbe device failed."""

    def __init__(
        self,
        device_id: str | None = None,
        message: str | None = None,
    ) -> None:
        self.device_id = device_id
        if message is None:
            if device_id:
                message = f"Authentication failed for KKT Kolbe device {device_id[:8]}... - check local key"
            else:
                message = "Authentication failed - invalid local key"
        super().__init__(message)


class KKTTimeoutError(KKTKolbeError):
    """KKT Kolbe device operation timed out."""

    def __init__(
        self,
        operation: str | None = None,
        device_id: str | None = None,
        timeout: float | None = None,
        data_point: int | None = None,
        message: str | None = None,
    ) -> None:
        self.operation = operation
        self.device_id = device_id
        self.timeout = timeout
        self.data_point = data_point
        if message is None:
            if operation and device_id and timeout:
                message = f"Operation '{operation}' timed out after {timeout}s on device {device_id}"
            elif operation and timeout:
                message = f"Operation '{operation}' timed out after {timeout}s"
            elif operation and device_id:
                message = f"Operation '{operation}' timed out on device {device_id}"
            elif operation:
                message = f"Operation '{operation}' timed out"
            else:
                message = "Device operation timed out"
        super().__init__(message)


class KKTDeviceError(KKTKolbeError):
    """KKT Kolbe device reported an error."""

    def __init__(
        self,
        error_code: int | None = None,
        device_message: str | None = None,
        message: str | None = None,
    ) -> None:
        self.error_code = error_code
        self.device_message = device_message
        if message is None:
            if error_code and device_message:
                message = f"Device error {error_code}: {device_message}"
            elif error_code:
                message = f"Device error code: {error_code}"
            elif device_message:
                message = f"Device error: {device_message}"
            else:
                message = "Device reported an error"
        super().__init__(message)


class KKTConfigurationError(KKTKolbeError):
    """KKT Kolbe integration configuration error."""

    def __init__(
        self,
        config_field: str | None = None,
        message: str | None = None,
    ) -> None:
        self.config_field = config_field
        if message is None:
            if config_field:
                message = f"Configuration error in field '{config_field}'"
            else:
                message = "Integration configuration error"
        super().__init__(message)


class KKTDiscoveryError(KKTKolbeError):
    """KKT Kolbe device discovery failed."""

    def __init__(
        self,
        discovery_method: str | None = None,
        message: str | None = None,
    ) -> None:
        self.discovery_method = discovery_method
        if message is None:
            if discovery_method:
                message = f"Device discovery failed using {discovery_method}"
            else:
                message = "Device discovery failed"
        super().__init__(message)


class KKTServiceError(KKTKolbeError):
    """KKT Kolbe service call failed."""

    def __init__(
        self,
        service_name: str | None = None,
        reason: str | None = None,
        message: str | None = None,
    ) -> None:
        self.service_name = service_name
        self.reason = reason
        if message is None:
            if service_name and reason:
                message = f"Service '{service_name}' failed: {reason}"
            elif service_name:
                message = f"Service '{service_name}' failed"
            else:
                message = "Service call failed"
        super().__init__(message)


class KKTDataPointError(KKTKolbeError):
    """KKT Kolbe data point operation failed."""

    def __init__(
        self,
        dp: int | None = None,
        operation: str | None = None,
        value: Any = None,
        device_id: str | None = None,
        reason: str | None = None,
        data_point: int | None = None,
        message: str | None = None,
    ) -> None:
        self.dp = dp or data_point  # Support both parameter names
        self.operation = operation
        self.value = value
        self.device_id = device_id
        self.reason = reason

        if message is None:
            # Build message from available parameters
            parts = []
            if operation:
                parts.append(f"Failed to {operation}")
            if self.dp:
                parts.append(f"data point {self.dp}")
            if value is not None:
                parts.append(f"with value {value}")
            if device_id:
                parts.append(f"on device {device_id}")
            if reason:
                parts.append(f": {reason}")

            if parts:
                message = " ".join(parts)
            else:
                message = "Data point operation failed"

        super().__init__(message)