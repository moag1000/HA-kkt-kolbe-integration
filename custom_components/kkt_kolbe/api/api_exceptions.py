"""API-specific exceptions for KKT Kolbe integration."""
from __future__ import annotations


class TuyaAPIError(Exception):
    """Base exception for Tuya API errors."""

    def __init__(self, message: str = None, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class TuyaAuthenticationError(TuyaAPIError):
    """Exception raised when API authentication fails."""

    def __init__(self, message: str = "Authentication failed", error_code: str = None):
        super().__init__(message, error_code)


class TuyaRateLimitError(TuyaAPIError):
    """Exception raised when API rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


class TuyaDeviceNotFoundError(TuyaAPIError):
    """Exception raised when a device is not found via API."""

    def __init__(self, device_id: str, message: str = None):
        self.device_id = device_id
        if not message:
            message = f"Device {device_id} not found"
        super().__init__(message)