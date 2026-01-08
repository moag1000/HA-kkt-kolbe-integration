"""Tuya Sharing SDK client for SmartLife/Tuya Smart app integration.

This client wraps the tuya-device-sharing-sdk library to provide QR-code based
authentication without requiring a Tuya IoT Developer account.

Authentication Flow:
1. User provides their User Code from SmartLife/Tuya Smart app
2. Client generates a QR code token via Tuya Cloud
3. User scans QR code with their app and authorizes
4. Client polls for authorization result
5. On success, client can fetch all devices including local_key

Reference implementations:
- tuya-local (make-all): https://github.com/make-all/tuya-local
- HA Core Tuya: https://github.com/home-assistant/core/tree/dev/homeassistant/components/tuya
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

from ..const import QR_CODE_FORMAT
from ..const import QR_LOGIN_POLL_INTERVAL
from ..const import QR_LOGIN_TIMEOUT
from ..const import SMARTLIFE_CLIENT_ID
from ..const import SMARTLIFE_SCHEMA
from ..exceptions import KKTAuthenticationError
from ..exceptions import KKTConnectionError
from ..exceptions import KKTTimeoutError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@dataclass
class TuyaSharingDevice:
    """Representation of a device from Tuya Sharing API.

    This dataclass holds all relevant device information retrieved
    from the SmartLife/Tuya Smart cloud, including the crucial local_key
    needed for local device control.

    Attributes:
        device_id: Unique Tuya device identifier (20-22 characters)
        name: User-assigned device name from the app
        local_key: Encryption key for local LAN communication
        product_id: Tuya product identifier
        product_name: Product name (e.g., "KKT Kolbe HERMES")
        category: Device category (yyj=hood, dcl=cooktop)
        ip: Local IP address if available
        online: Whether device is currently online
        support_local: Whether device supports local control
        kkt_device_type: Detected KKT device type key (set during filtering)
        kkt_product_name: Matched product name (set during filtering)
    """

    device_id: str
    name: str
    local_key: str
    product_id: str
    product_name: str
    category: str
    ip: str | None = None
    online: bool = False
    support_local: bool = True
    # Fields set during KKT device detection
    kkt_device_type: str | None = None
    kkt_product_name: str | None = None

    @classmethod
    def from_customer_device(cls, device: Any) -> TuyaSharingDevice:
        """Create TuyaSharingDevice from tuya_sharing.CustomerDevice.

        Args:
            device: CustomerDevice instance from tuya_sharing library

        Returns:
            New TuyaSharingDevice with data extracted from CustomerDevice
        """
        return cls(
            device_id=device.id,
            name=device.name,
            local_key=getattr(device, "local_key", "") or "",
            product_id=device.product_id,
            product_name=getattr(device, "product_name", "") or "",
            category=device.category,
            ip=getattr(device, "ip", None),
            online=getattr(device, "online", False),
            support_local=getattr(device, "support_local", True),
        )


@dataclass
class TuyaSharingAuthResult:
    """Result of QR code authentication.

    Contains all tokens and identifiers needed to maintain
    an authenticated session with the Tuya cloud.

    Attributes:
        success: Whether authentication was successful
        user_id: Tuya user ID (uid)
        terminal_id: Unique terminal identifier for this session
        endpoint: API endpoint URL (region-specific)
        access_token: OAuth access token
        refresh_token: Token for refreshing access_token
        expire_time: Unix timestamp when access_token expires
        timestamp: Server timestamp from authentication response
        error_message: Error description if authentication failed
    """

    success: bool
    user_id: str | None = None
    terminal_id: str | None = None
    endpoint: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    expire_time: int = 0
    timestamp: int = 0
    error_message: str | None = None


class TuyaSharingClient:
    """Client for interacting with Tuya Sharing API.

    This client provides QR-code based authentication flow that works
    with consumer SmartLife/Tuya Smart apps without requiring a
    Tuya IoT Developer account.

    The authentication flow:
    1. Initialize client with user_code from app
    2. Call async_generate_qr_code() to get QR code string
    3. Display QR code for user to scan with app
    4. Call async_poll_login_result() to wait for authorization
    5. Call async_get_devices() to retrieve device list with local_key

    For subsequent sessions, use async_from_stored_tokens() to restore
    authentication from stored token_info.

    Example:
        ```python
        # Initial setup
        client = TuyaSharingClient(hass, "EU12345678", "smartlife")
        qr_code = await client.async_generate_qr_code()
        # Display qr_code to user...
        auth_result = await client.async_poll_login_result()
        devices = await client.async_get_devices()
        token_info = client.get_token_info_for_storage()

        # Later restoration
        client = await TuyaSharingClient.async_from_stored_tokens(
            hass, token_info
        )
        devices = await client.async_get_devices()
        ```
    """

    def __init__(
        self,
        hass: HomeAssistant,
        user_code: str,
        app_schema: str = SMARTLIFE_SCHEMA,
    ) -> None:
        """Initialize the client.

        Args:
            hass: Home Assistant instance for async executor
            user_code: User code from SmartLife/Tuya Smart app
                       (found in: Me -> Settings -> Account and Security -> User Code)
            app_schema: App identifier - "smartlife" or "tuyaSmart"
        """
        self.hass = hass
        self._user_code = user_code
        self._app_schema = app_schema
        self._login_control: Any | None = None
        self._manager: Any | None = None
        self._qr_token: str | None = None
        self._token_info: dict[str, Any] = {}
        self._auth_result: TuyaSharingAuthResult | None = None
        self._token_update_callback: Any | None = None  # Callback for token persistence

    def set_token_update_callback(
        self, callback: Any  # Callable[[dict[str, Any]], Awaitable[None]]
    ) -> None:
        """Set callback for when tokens are refreshed.

        The callback will be called with the new token_info dict whenever
        the SDK refreshes tokens. Use this to persist tokens to config entry.

        Args:
            callback: Async function that takes token_info dict
        """
        self._token_update_callback = callback
        _LOGGER.debug("Token update callback registered")

    @property
    def user_code(self) -> str:
        """Get the user code."""
        return self._user_code

    @property
    def app_schema(self) -> str:
        """Get the app schema (smartlife or tuyaSmart)."""
        return self._app_schema

    @property
    def is_authenticated(self) -> bool:
        """Check if client has valid authentication."""
        return self._auth_result is not None and self._auth_result.success

    async def async_generate_qr_code(self) -> str:
        """Generate QR code token for app scanning.

        This initiates the authentication flow by requesting a QR code
        token from the Tuya cloud. The returned string should be encoded
        as a QR code and displayed to the user for scanning.

        Returns:
            QR code URL string in format "tuyaSmart--qrLogin?token=xxx"

        Raises:
            KKTConnectionError: If unable to connect to Tuya cloud
            KKTAuthenticationError: If user_code is invalid or rejected
        """
        from tuya_sharing import LoginControl

        def _generate() -> dict[str, Any]:
            self._login_control = LoginControl()
            return self._login_control.qr_code(
                SMARTLIFE_CLIENT_ID,
                self._app_schema,
                self._user_code,
            )

        try:
            response = await self.hass.async_add_executor_job(_generate)
        except Exception as err:
            _LOGGER.error("Failed to generate QR code: %s", err)
            raise KKTConnectionError(
                operation="qr_code_generation",
                reason=str(err),
            ) from err

        if not response.get("success"):
            error_code = response.get("code", "unknown")
            error_msg = response.get("msg", "Unknown error")
            _LOGGER.error(
                "QR code generation failed: %s (code: %s)", error_msg, error_code
            )
            raise KKTAuthenticationError(
                message=f"QR code generation failed: {error_msg} (code: {error_code})",
            )

        self._qr_token = response.get("result", {}).get("qrcode")
        if not self._qr_token:
            raise KKTAuthenticationError(
                message="No QR token received in response",
            )

        qr_code_string = QR_CODE_FORMAT.format(token=self._qr_token)
        _LOGGER.debug("Generated QR code token (length: %d)", len(self._qr_token))
        return qr_code_string

    async def async_poll_login_result(
        self,
        timeout: float = QR_LOGIN_TIMEOUT,
        poll_interval: float = QR_LOGIN_POLL_INTERVAL,
    ) -> TuyaSharingAuthResult:
        """Poll for login result after QR code scan.

        This method polls the Tuya cloud for the authentication result
        after the user scans the QR code and authorizes in the app.

        Args:
            timeout: Maximum time to wait for authorization (seconds)
            poll_interval: Time between poll requests (seconds)

        Returns:
            Authentication result with tokens and session info

        Raises:
            KKTAuthenticationError: If not ready to poll or auth denied
            KKTTimeoutError: If user doesn't complete within timeout
        """
        if not self._qr_token or not self._login_control:
            raise KKTAuthenticationError(
                message="Must call async_generate_qr_code() first",
            )

        def _poll() -> tuple[bool, dict[str, Any]]:
            return self._login_control.login_result(
                self._qr_token,
                SMARTLIFE_CLIENT_ID,
                self._user_code,
            )

        start_time = asyncio.get_event_loop().time()
        poll_count = 0

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                _LOGGER.warning(
                    "QR code login timed out after %.1fs (%d polls)",
                    elapsed,
                    poll_count,
                )
                raise KKTTimeoutError(
                    operation="qr_login",
                    timeout=timeout,
                )

            try:
                poll_count += 1
                success, result = await self.hass.async_add_executor_job(_poll)
            except Exception as err:
                _LOGGER.debug("Poll attempt %d failed (retrying): %s", poll_count, err)
                await asyncio.sleep(poll_interval)
                continue

            if success:
                # Authentication successful
                # Note: API returns tokens at top level, not in nested token_info
                token_info = result.get("token_info") or {}
                _LOGGER.debug("QR login result keys: %s", list(result.keys()))

                # Get values from top level first, fall back to token_info
                user_id = result.get("uid") or token_info.get("uid")
                access_token = result.get("access_token") or token_info.get("access_token")
                refresh_token = result.get("refresh_token") or token_info.get("refresh_token")
                raw_expire_time = result.get("expire_time") or token_info.get("expire_time", 0)

                # Convert relative expire_time to absolute Unix timestamp if needed
                # Tuya API returns expire_time as seconds until expiry (e.g., 7200 for 2 hours)
                # We need to store as absolute timestamp for proper comparison later
                import time
                if raw_expire_time < 1000000000:  # Less than year 2001 = probably relative
                    expire_time = int(time.time()) + raw_expire_time
                    _LOGGER.debug(
                        "Converted relative expire_time %d to absolute timestamp %d",
                        raw_expire_time, expire_time
                    )
                else:
                    expire_time = raw_expire_time

                if not user_id:
                    _LOGGER.warning("No user_id found in auth result, using terminal_id as fallback")
                    user_id = result.get("terminal_id", "unknown")

                self._auth_result = TuyaSharingAuthResult(
                    success=True,
                    user_id=user_id,
                    terminal_id=result.get("terminal_id"),
                    endpoint=result.get("endpoint"),
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expire_time=expire_time,
                    timestamp=result.get("t", 0),
                )

                # Store for later use
                self._token_info = {
                    "terminal_id": self._auth_result.terminal_id,
                    "endpoint": self._auth_result.endpoint,
                    "access_token": self._auth_result.access_token,
                    "refresh_token": self._auth_result.refresh_token,
                    "expire_time": self._auth_result.expire_time,
                    "uid": self._auth_result.user_id,
                    "t": self._auth_result.timestamp,
                }

                _LOGGER.info(
                    "QR code login successful after %.1fs (%d polls)",
                    elapsed,
                    poll_count,
                )
                return self._auth_result

            # Check for specific error codes indicating failure
            error_code = result.get("code")
            error_msg = result.get("msg", "")

            if error_code == "login_failed" or "denied" in error_msg.lower():
                _LOGGER.error("User denied authorization: %s", error_msg)
                self._auth_result = TuyaSharingAuthResult(
                    success=False,
                    error_message="User denied authorization",
                )
                raise KKTAuthenticationError(
                    message="User denied authorization in app",
                )

            # Not yet authorized, continue polling
            _LOGGER.debug(
                "Poll %d: awaiting authorization (%.1fs elapsed)",
                poll_count,
                elapsed,
            )
            await asyncio.sleep(poll_interval)

    async def async_get_devices(self) -> list[TuyaSharingDevice]:
        """Get all devices from the account.

        Retrieves all devices associated with the authenticated
        SmartLife/Tuya Smart account, including the local_key needed
        for local LAN communication.

        Returns:
            List of devices with local_key populated

        Raises:
            KKTAuthenticationError: If client is not authenticated
            KKTConnectionError: If unable to fetch devices from cloud
        """
        if not self._auth_result or not self._auth_result.success:
            raise KKTAuthenticationError(
                message="Must authenticate first via QR code",
            )

        from tuya_sharing import Manager
        from tuya_sharing import SharingTokenListener

        # Token update listener to keep tokens fresh
        class TokenListener(SharingTokenListener):
            """Listener for token updates from the SDK."""

            def __init__(self, client: TuyaSharingClient) -> None:
                self._client = client

            def update_token(self, token_info: dict[str, Any]) -> None:
                """Handle token refresh events."""
                _LOGGER.info("Token refreshed by SDK - persisting new tokens")

                # Convert relative expire_time to absolute timestamp if needed
                import time
                raw_expire_time = token_info.get("expire_time", 0)
                if raw_expire_time < 1000000000:  # Less than year 2001 = probably relative
                    absolute_expire_time = int(time.time()) + raw_expire_time
                    token_info = dict(token_info)  # Copy to avoid modifying original
                    token_info["expire_time"] = absolute_expire_time
                    _LOGGER.debug(
                        "Converted relative expire_time %d to absolute timestamp %d",
                        raw_expire_time, absolute_expire_time
                    )

                self._client._token_info.update(token_info)
                if self._client._auth_result:
                    self._client._auth_result.access_token = token_info.get(
                        "access_token"
                    )
                    self._client._auth_result.refresh_token = token_info.get(
                        "refresh_token"
                    )
                    self._client._auth_result.expire_time = token_info.get(
                        "expire_time", 0
                    )

                # Call the persistence callback if registered
                if self._client._token_update_callback:
                    # Get full token info for storage
                    full_token_info = self._client.get_token_info_for_storage()
                    try:
                        # Schedule the async callback
                        asyncio.run_coroutine_threadsafe(
                            self._client._token_update_callback(full_token_info),
                            self._client.hass.loop,
                        )
                        _LOGGER.debug("Token persistence callback scheduled")
                    except Exception as err:
                        _LOGGER.warning("Failed to schedule token persistence: %s", err)

        def _init_manager() -> Any:
            """Initialize the SDK Manager in executor thread."""
            token_info = {
                "access_token": self._auth_result.access_token,
                "refresh_token": self._auth_result.refresh_token,
                "expire_time": self._auth_result.expire_time,
                "uid": self._auth_result.user_id,
            }
            return Manager(
                SMARTLIFE_CLIENT_ID,
                self._user_code,
                self._auth_result.terminal_id,
                self._auth_result.endpoint,
                token_info,
                TokenListener(self),
            )

        def _fetch_devices() -> list[Any]:
            """Fetch devices from cloud in executor thread."""
            self._manager.update_device_cache()
            return list(self._manager.device_map.values())

        try:
            if not self._manager:
                self._manager = await self.hass.async_add_executor_job(_init_manager)
            raw_devices = await self.hass.async_add_executor_job(_fetch_devices)
        except Exception as err:
            _LOGGER.error("Failed to fetch devices: %s", err)
            raise KKTConnectionError(
                operation="fetch_devices",
                reason=str(err),
            ) from err

        devices: list[TuyaSharingDevice] = []
        for raw_device in raw_devices:
            device = TuyaSharingDevice.from_customer_device(raw_device)
            devices.append(device)

            # Log device info for debugging
            if device.local_key:
                _LOGGER.debug(
                    "Device '%s' (%s...): local_key available, category=%s, online=%s",
                    device.name,
                    device.device_id[:8],
                    device.category,
                    device.online,
                )
            else:
                _LOGGER.warning(
                    "Device '%s' (%s...): local_key NOT available - "
                    "may be a hub device or restricted",
                    device.name,
                    device.device_id[:8],
                )

        _LOGGER.info("Retrieved %d devices from SmartLife account", len(devices))
        return devices

    async def async_refresh_device(self, device_id: str) -> TuyaSharingDevice | None:
        """Refresh a single device's data from cloud.

        Useful for updating local_key if it has been rotated.

        Args:
            device_id: The device ID to refresh

        Returns:
            Updated TuyaSharingDevice or None if not found
        """
        devices = await self.async_get_devices()
        for device in devices:
            if device.device_id == device_id:
                return device
        return None

    def get_token_info_for_storage(self) -> dict[str, Any]:
        """Get token info for storing in config entry.

        Returns a dictionary containing all authentication information
        needed to restore the client session later without requiring
        a new QR code scan.

        Returns:
            Dictionary suitable for storing in ConfigEntry.data
        """
        if not self._auth_result or not self._auth_result.success:
            return {}

        return {
            "terminal_id": self._auth_result.terminal_id,
            "endpoint": self._auth_result.endpoint,
            "access_token": self._auth_result.access_token,
            "refresh_token": self._auth_result.refresh_token,
            "expire_time": self._auth_result.expire_time,
            "uid": self._auth_result.user_id,
            "user_code": self._user_code,
            "app_schema": self._app_schema,
            "timestamp": self._auth_result.timestamp,
        }

    @classmethod
    async def async_from_stored_tokens(
        cls,
        hass: HomeAssistant,
        token_info: dict[str, Any],
    ) -> TuyaSharingClient:
        """Create client from stored tokens.

        Use this to restore a client session from previously stored
        token information, avoiding the need for a new QR code scan.

        Args:
            hass: Home Assistant instance
            token_info: Previously stored token info from get_token_info_for_storage()

        Returns:
            Initialized TuyaSharingClient ready to fetch devices

        Raises:
            KKTAuthenticationError: If token_info is missing required fields
        """
        user_code = token_info.get("user_code")
        if not user_code:
            raise KKTAuthenticationError(
                message="Missing user_code in stored token info",
            )

        app_schema = token_info.get("app_schema", SMARTLIFE_SCHEMA)
        client = cls(hass=hass, user_code=user_code, app_schema=app_schema)

        # Restore authentication result
        client._auth_result = TuyaSharingAuthResult(
            success=True,
            user_id=token_info.get("uid"),
            terminal_id=token_info.get("terminal_id"),
            endpoint=token_info.get("endpoint"),
            access_token=token_info.get("access_token"),
            refresh_token=token_info.get("refresh_token"),
            expire_time=token_info.get("expire_time", 0),
            timestamp=token_info.get("timestamp", 0),
        )

        # Store token info
        client._token_info = dict(token_info)

        _LOGGER.debug(
            "Restored TuyaSharingClient from stored tokens (user_code=%s...)",
            user_code[:4] if len(user_code) > 4 else user_code,
        )

        return client

    async def async_restore_tokens(self, token_info: dict[str, Any]) -> None:
        """Restore authentication from stored token info.

        This is an instance method version of async_from_stored_tokens,
        useful when you already have a client instance and want to restore
        its authentication state from stored tokens.

        Args:
            token_info: Previously stored token info from get_token_info_for_storage()

        Raises:
            KKTAuthenticationError: If token_info is missing required fields
        """
        access_token = token_info.get("access_token")
        if not access_token:
            raise KKTAuthenticationError(
                message="Missing access_token in stored token info",
            )

        # Restore authentication result
        self._auth_result = TuyaSharingAuthResult(
            success=True,
            user_id=token_info.get("uid"),
            terminal_id=token_info.get("terminal_id"),
            endpoint=token_info.get("endpoint"),
            access_token=access_token,
            refresh_token=token_info.get("refresh_token"),
            expire_time=token_info.get("expire_time", 0),
            timestamp=token_info.get("timestamp", 0),
        )

        # Store token info
        self._token_info = dict(token_info)

        # Update user_code and app_schema if available in token_info
        if token_info.get("user_code"):
            self._user_code = token_info["user_code"]
        if token_info.get("app_schema"):
            self._app_schema = token_info["app_schema"]

        _LOGGER.debug(
            "Restored authentication from stored tokens (user_id=%s...)",
            self._auth_result.user_id[:8] if self._auth_result.user_id else "unknown",
        )

    async def async_validate_tokens(self) -> bool:
        """Validate that stored tokens are still valid.

        Attempts to fetch devices to verify token validity.

        Returns:
            True if tokens are valid, False otherwise
        """
        if not self._auth_result or not self._auth_result.success:
            return False

        try:
            await self.async_get_devices()
            return True
        except (KKTAuthenticationError, KKTConnectionError) as err:
            _LOGGER.warning("Token validation failed: %s", err)
            return False

    async def async_get_device_status(self, device_id: str) -> list[dict[str, Any]]:
        """Get current status of a device.

        This method provides cloud-fallback functionality for the HybridCoordinator.
        Uses the SDK Manager to fetch device status from Tuya cloud.

        Args:
            device_id: The device ID to get status for

        Returns:
            List of status items with 'code' and 'value' keys

        Raises:
            KKTAuthenticationError: If not authenticated
            KKTConnectionError: If unable to fetch status
        """
        if not self._auth_result or not self._auth_result.success:
            raise KKTAuthenticationError(
                message="Must authenticate first via QR code",
            )

        # Ensure manager is initialized
        if not self._manager:
            await self.async_get_devices()  # This initializes the manager

        def _get_status() -> list[dict[str, Any]]:
            """Get device status in executor thread."""
            # Update device cache to get fresh data
            self._manager.update_device_cache()

            # Find the device in device_map
            device = self._manager.device_map.get(device_id)
            if not device:
                _LOGGER.warning("Device %s not found in manager cache", device_id[:8])
                return []

            # Extract status from device
            status_list: list[dict[str, Any]] = []
            if hasattr(device, "status") and device.status:
                for code, value in device.status.items():
                    status_list.append({"code": code, "value": value})

            return status_list

        try:
            status = await self.hass.async_add_executor_job(_get_status)
            _LOGGER.debug(
                "Retrieved %d status items for device %s via SmartLife",
                len(status), device_id[:8]
            )
            return status
        except Exception as err:
            _LOGGER.error("Failed to get device status: %s", err)
            raise KKTConnectionError(
                operation="get_device_status",
                reason=str(err),
            ) from err

    async def async_send_commands(
        self, device_id: str, commands: list[dict[str, Any]]
    ) -> bool:
        """Send commands to a device via SmartLife cloud.

        This method provides cloud-fallback functionality for the HybridCoordinator.

        Args:
            device_id: The device ID to send commands to
            commands: List of commands, each with 'code' and 'value' keys
                     Example: [{"code": "switch", "value": True}]

        Returns:
            True if command was sent successfully, False otherwise

        Raises:
            KKTAuthenticationError: If not authenticated
        """
        if not self._auth_result or not self._auth_result.success:
            raise KKTAuthenticationError(
                message="Must authenticate first via QR code",
            )

        # Ensure manager is initialized
        if not self._manager:
            await self.async_get_devices()  # This initializes the manager

        def _send_commands() -> bool:
            """Send commands in executor thread."""
            device = self._manager.device_map.get(device_id)
            if not device:
                _LOGGER.warning("Device %s not found in manager cache", device_id[:8])
                return False

            # The tuya_sharing library's device might have a send_commands method
            if hasattr(device, "send_commands"):
                try:
                    device.send_commands(commands)
                    return True
                except Exception as err:
                    _LOGGER.warning("send_commands failed: %s", err)

            # Alternative: Use manager's device control method if available
            if hasattr(self._manager, "send_commands"):
                try:
                    self._manager.send_commands(device_id, commands)
                    return True
                except Exception as err:
                    _LOGGER.warning("manager.send_commands failed: %s", err)

            _LOGGER.warning(
                "No command sending method available for device %s",
                device_id[:8]
            )
            return False

        try:
            success = await self.hass.async_add_executor_job(_send_commands)
            if success:
                _LOGGER.info(
                    "Commands sent successfully to device %s via SmartLife",
                    device_id[:8]
                )
            return success
        except Exception as err:
            _LOGGER.error("Failed to send commands: %s", err)
            return False

    async def async_send_dp_commands(
        self, device_id: str, dps: dict[str, Any]
    ) -> bool:
        """Send DP (Data Point) commands to a device via SmartLife cloud.

        Args:
            device_id: The device ID to send commands to
            dps: Dictionary of DP ID to value, e.g., {"1": True, "2": 50}

        Returns:
            True if command was sent successfully, False otherwise
        """
        # Convert DPs to commands format
        # Note: This requires mapping DP IDs to property codes
        # For now, try sending as-is and let the API figure it out
        commands = [{"code": str(dp_id), "value": value} for dp_id, value in dps.items()]
        return await self.async_send_commands(device_id, commands)

    async def async_test_connection(self) -> bool:
        """Test connection and validate tokens.

        Attempts to fetch devices to verify the connection is working.

        Returns:
            True if connection is valid, False otherwise
        """
        return await self.async_validate_tokens()

    async def async_close(self) -> None:
        """Close the client and cleanup resources.

        Should be called when the client is no longer needed to
        properly cleanup the SDK Manager.
        """
        if self._manager:
            try:
                # Manager might have an unload method
                if hasattr(self._manager, "unload"):
                    await self.hass.async_add_executor_job(self._manager.unload)
            except Exception as err:
                _LOGGER.debug("Error during manager cleanup: %s", err)
            finally:
                self._manager = None

        self._login_control = None
        _LOGGER.debug("TuyaSharingClient closed")

    def __repr__(self) -> str:
        """Return string representation."""
        user_code_masked = (
            f"{self._user_code[:4]}..." if len(self._user_code) > 4 else self._user_code
        )
        return (
            f"TuyaSharingClient(user_code={user_code_masked}, "
            f"app_schema={self._app_schema}, "
            f"authenticated={self.is_authenticated})"
        )
