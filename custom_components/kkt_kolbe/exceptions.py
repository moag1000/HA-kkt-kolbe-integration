"""Custom exceptions for KKT Kolbe integration."""


class KKTKolbeError(Exception):
    """Base exception for KKT Kolbe integration."""

    def __init__(self, message: str = "Unknown KKT Kolbe error occurred"):
        self.message = message
        super().__init__(self.message)


class KKTConnectionError(KKTKolbeError):
    """Connection to KKT Kolbe device failed."""

    def __init__(self, device_id: str = None, message: str = None):
        self.device_id = device_id
        if message is None:
            if device_id:
                message = f"Failed to connect to KKT Kolbe device {device_id[:8]}..."
            else:
                message = "Failed to connect to KKT Kolbe device"
        super().__init__(message)


class KKTAuthenticationError(KKTKolbeError):
    """Authentication with KKT Kolbe device failed."""

    def __init__(self, device_id: str = None, message: str = None):
        self.device_id = device_id
        if message is None:
            if device_id:
                message = f"Authentication failed for KKT Kolbe device {device_id[:8]}... - check local key"
            else:
                message = "Authentication failed - invalid local key"
        super().__init__(message)


class KKTTimeoutError(KKTKolbeError):
    """KKT Kolbe device operation timed out."""

    def __init__(self, operation: str = None, timeout: float = None, message: str = None):
        self.operation = operation
        self.timeout = timeout
        if message is None:
            if operation and timeout:
                message = f"Operation '{operation}' timed out after {timeout}s"
            elif operation:
                message = f"Operation '{operation}' timed out"
            else:
                message = "Device operation timed out"
        super().__init__(message)


class KKTDeviceError(KKTKolbeError):
    """KKT Kolbe device reported an error."""

    def __init__(self, error_code: int = None, device_message: str = None, message: str = None):
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

    def __init__(self, config_field: str = None, message: str = None):
        self.config_field = config_field
        if message is None:
            if config_field:
                message = f"Configuration error in field '{config_field}'"
            else:
                message = "Integration configuration error"
        super().__init__(message)


class KKTDiscoveryError(KKTKolbeError):
    """KKT Kolbe device discovery failed."""

    def __init__(self, discovery_method: str = None, message: str = None):
        self.discovery_method = discovery_method
        if message is None:
            if discovery_method:
                message = f"Device discovery failed using {discovery_method}"
            else:
                message = "Device discovery failed"
        super().__init__(message)


class KKTServiceError(KKTKolbeError):
    """KKT Kolbe service call failed."""

    def __init__(self, service_name: str = None, reason: str = None, message: str = None):
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

    def __init__(self, dp: int = None, operation: str = None, value=None, message: str = None):
        self.dp = dp
        self.operation = operation
        self.value = value
        if message is None:
            if dp and operation and value is not None:
                message = f"Failed to {operation} data point {dp} with value {value}"
            elif dp and operation:
                message = f"Failed to {operation} data point {dp}"
            elif dp:
                message = f"Data point {dp} operation failed"
            else:
                message = "Data point operation failed"
        super().__init__(message)