"""KKT Kolbe Tuya Device Handler with enhanced config flow and device selection."""
from __future__ import annotations

import asyncio
import logging
import random
import socket
from collections.abc import Callable
from collections.abc import Coroutine
from typing import Any

import tinytuya
from homeassistant.core import HomeAssistant

from .const import DEFAULT_CONNECTION_TIMEOUT
from .const import TCP_KEEPALIVE_COUNT
from .const import TCP_KEEPALIVE_IDLE
from .const import TCP_KEEPALIVE_INTERVAL
from .exceptions import KKTAuthenticationError
from .exceptions import KKTConnectionError
from .exceptions import KKTDataPointError
from .exceptions import KKTTimeoutError

_LOGGER = logging.getLogger(__name__)

class KKTKolbeTuyaDevice:
    """Handle communication with KKT Kolbe device via Tuya protocol."""

    def __init__(self, device_id: str, ip_address: str, local_key: str, version: str = "auto", hass: HomeAssistant | None = None) -> None:
        """Initialize the Tuya device connection.

        Args:
            device_id: Tuya device ID
            ip_address: IP address of the device
            local_key: Local encryption key
            version: Protocol version ("auto" or specific version like "3.3")
            hass: Home Assistant instance (optional, for executor job scheduling)
        """
        self.device_id = device_id
        self.ip_address = ip_address
        self.local_key = local_key
        self._local_key_bytes: bytes | None = None  # Cached latin1-encoded key
        self.version = version

        # Debug: Log local_key encoding details
        self._debug_local_key_encoding(local_key)
        self._device: Any = None
        self._status: dict[str, Any] = {}
        self._connected = False
        self._hass = hass

        # Connection statistics for diagnostics
        self._connection_stats: dict[str, Any] = {
            "total_connects": 0,
            "total_disconnects": 0,
            "total_reconnects": 0,
            "total_timeouts": 0,
            "total_errors": 0,
            "last_connect_time": None,
            "last_disconnect_time": None,
            "protocol_version_detected": None,
        }
        # Don't connect in __init__ - will be done async

    def _debug_local_key_encoding(self, local_key: str) -> None:
        """Log detailed encoding information for debugging local_key issues."""
        try:
            key_len = len(local_key)

            # Encode with different encodings
            try:
                utf8_bytes = local_key.encode("utf-8")
                utf8_hex = utf8_bytes.hex()
                utf8_len = len(utf8_bytes)
            except Exception as e:
                utf8_hex = f"ERROR: {e}"
                utf8_len = -1

            try:
                latin1_bytes = local_key.encode("latin1")
                latin1_hex = latin1_bytes.hex()
                latin1_len = len(latin1_bytes)
                # Cache for later use
                self._local_key_bytes = latin1_bytes
            except Exception as e:
                latin1_hex = f"ERROR: {e}"
                latin1_len = -1

            # Check for non-ASCII characters
            non_ascii = [c for c in local_key if ord(c) > 127]
            has_non_ascii = len(non_ascii) > 0

            # Check for special characters
            special_chars = [c for c in local_key if not c.isalnum()]

            _LOGGER.info(
                "LOCAL_KEY ENCODING DEBUG for device %s:\n"
                "  String length: %d (expected: 16)\n"
                "  UTF-8 bytes: %d, hex: %s\n"
                "  Latin1 bytes: %d, hex: %s\n"
                "  Has non-ASCII: %s (chars: %s)\n"
                "  Special chars: %s\n"
                "  Char codes: %s\n"
                "  Key (masked): %s...%s",
                self.device_id[:8] if hasattr(self, 'device_id') else "???",
                key_len,
                utf8_len, utf8_hex[:40] + "..." if len(utf8_hex) > 40 else utf8_hex,
                latin1_len, latin1_hex[:40] + "..." if len(latin1_hex) > 40 else latin1_hex,
                has_non_ascii, non_ascii[:5] if has_non_ascii else "none",
                special_chars,
                [ord(c) for c in local_key],
                local_key[:2] if key_len >= 2 else "?",
                local_key[-2:] if key_len >= 2 else "?"
            )

            # Warn if UTF-8 and Latin1 produce different lengths
            if utf8_len != latin1_len:
                _LOGGER.warning(
                    "LOCAL_KEY ENCODING MISMATCH: UTF-8 (%d bytes) != Latin1 (%d bytes). "
                    "This may cause connection failures!",
                    utf8_len, latin1_len
                )

        except Exception as e:
            _LOGGER.error("Error debugging local_key encoding: %s", e)

    def _handle_task_result(self, task: asyncio.Task[Any]) -> None:
        """Handle completed async task results and log errors."""
        try:
            task.result()  # This will raise the exception if the task failed
        except Exception as e:
            _LOGGER.error(f"Async task failed: {e}")

    def _create_safe_task(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        """Create async task with error handling."""
        task = asyncio.create_task(coro)
        task.add_done_callback(self._handle_task_result)
        return task

    async def async_connect(self) -> None:
        """Establish async connection to the device with timeout protection and retry mechanism."""
        from datetime import datetime

        if self._connected:
            return

        max_retries = 2  # Reduced from 3 to speed up failure detection
        base_retry_delay = 3.0  # Base delay for retry


        # Quick pre-check before full protocol detection
        is_reachable = await self.async_quick_check(timeout=2.0)
        if not is_reachable:
            _LOGGER.warning(
                f"Quick check failed for device at {self.ip_address}. "
                f"Device appears to be offline or unreachable."
            )
            self._connection_stats["total_errors"] += 1
            raise KKTConnectionError(
                operation="quick_check",
                device_id=self.device_id[:8],
                reason="Device not reachable on port 6668 - check if device is online"
            )

        for attempt in range(max_retries):
            # Add jitter to retry delay to prevent thundering herd
            retry_delay = base_retry_delay * (0.5 + random.random())

            try:
                _LOGGER.info(
                    f"Attempting connection to device {self.device_id[:8]}... "
                    f"at {self.ip_address} (attempt {attempt + 1}/{max_retries})"
                )

                # Apply timeout protection for connection operations
                # Total timeout is 15s (4 versions × 3s + overhead)
                await asyncio.wait_for(self._perform_connection(), timeout=DEFAULT_CONNECTION_TIMEOUT)

                # Update connection statistics
                self._connection_stats["total_connects"] += 1
                self._connection_stats["last_connect_time"] = datetime.now().isoformat()
                if attempt > 0:
                    self._connection_stats["total_reconnects"] += 1

                # Configure TCP Keep-Alive on successful connection
                if self._device:
                    self._configure_socket_keepalive(self._device)

                _LOGGER.info(f"Successfully connected to device {self.device_id[:8]}... at {self.ip_address}")
                return

            except asyncio.CancelledError:
                # Handle cancellation gracefully
                self._connected = False
                self._device = None
                _LOGGER.warning(f"Connection attempt cancelled for device at {self.ip_address}")
                raise  # Always re-raise CancelledError

            except TimeoutError as timeout_err:
                self._connected = False
                self._device = None
                self._connection_stats["total_timeouts"] += 1
                if attempt == max_retries - 1:
                    _LOGGER.error(
                        f"Connection timeout after {DEFAULT_CONNECTION_TIMEOUT} seconds for device at {self.ip_address}. "
                        f"Device may be offline or network unreachable."
                    )
                    raise KKTTimeoutError(
                        operation="connect",
                        device_id=self.device_id[:8],
                        timeout=DEFAULT_CONNECTION_TIMEOUT
                    ) from timeout_err
                else:
                    _LOGGER.info(f"Timeout, retrying in {retry_delay:.1f}s...")
                    await asyncio.sleep(retry_delay)

            except KKTAuthenticationError as e:
                # Authentication errors should not be retried - re-raise immediately
                self._connected = False
                self._device = None
                _LOGGER.error(f"Authentication failed for device at {self.ip_address}: {e}")
                raise

            except (KKTConnectionError, KKTTimeoutError) as e:
                # Re-raise our custom exceptions immediately without retry
                self._connected = False
                self._device = None
                _LOGGER.error(
                    f"Connection failed for device at {self.ip_address}: {e}\n"
                    f"This error typically indicates:\n"
                    f"  - Device not found on network\n"
                    f"  - Incorrect local key\n"
                    f"  - Incompatible Tuya protocol version\n"
                    f"Skipping retries for this error type."
                )
                raise

            except Exception as e:
                self._connected = False
                self._device = None
                if attempt == max_retries - 1:
                    _LOGGER.error(
                        f"Failed to connect to device at {self.ip_address} after {max_retries} attempts.\n"
                        f"Last error: {e}\n"
                        f"Please verify device is online and configuration is correct."
                    )
                    raise KKTConnectionError(
                        operation="connect",
                        device_id=self.device_id[:8],
                        reason=str(e)
                    ) from e
                else:
                    _LOGGER.info(f"Connection attempt {attempt + 1} failed: {e}, retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)

    async def _run_executor_job(self, func: Callable[..., Any], *args: Any) -> Any:
        """Run a function in executor - use hass if available, otherwise fallback to loop.

        This follows Home Assistant best practices for running blocking I/O.
        """
        if self._hass:
            return await self._hass.async_add_executor_job(func, *args)
        else:
            # Fallback for cases where hass is not available (e.g., tests)
            loop = asyncio.get_running_loop()
            if args:
                return await loop.run_in_executor(None, func, *args)
            else:
                return await loop.run_in_executor(None, func)

    def _get_key_variants(self) -> list[tuple[str, str]]:
        """Generate local_key variants to try for encoding issues.

        Returns a list of (key_variant, description) tuples.
        Some devices have keys that were incorrectly encoded/decoded.
        """
        variants = [(self.local_key, "original")]

        # If key has non-ASCII characters, try re-encoding
        if any(ord(c) > 127 for c in self.local_key):
            try:
                # Try latin1->utf8 re-encoding
                latin1_fixed = self.local_key.encode("latin1").decode("utf-8")
                if latin1_fixed != self.local_key:
                    variants.append((latin1_fixed, "latin1->utf8"))
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass

            try:
                # Try utf8->latin1 re-encoding
                utf8_fixed = self.local_key.encode("utf-8").decode("latin1")
                if utf8_fixed != self.local_key:
                    variants.append((utf8_fixed, "utf8->latin1"))
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass

        return variants

    def _is_error_914(self, status: Any) -> bool:
        """Check if status response is Error 914 (key/version check failed)."""
        if isinstance(status, dict):
            err_code = status.get("Err", status.get("err", ""))
            return str(err_code) == "914"
        return False

    async def _try_connect_with_key(self, local_key: str, version: float) -> tuple[Any, dict | None]:
        """Try to connect with a specific key and version.

        Returns (device, status) tuple. Device is None if connection failed.
        """
        test_device = None
        try:
            test_device = await self._run_executor_job(
                lambda: tinytuya.Device(
                    dev_id=self.device_id,
                    address=self.ip_address,
                    local_key=local_key,
                    version=version
                )
            )

            # Configure device with LocalTuya-style settings
            test_device.set_socketPersistent(True)
            test_device.set_socketNODELAY(True)
            test_device.set_socketTimeout(3)
            test_device.set_socketRetryLimit(1)

            # Get status with timeout
            test_status = await asyncio.wait_for(
                self._run_executor_job(test_device.status),
                timeout=3.0
            )

            return test_device, test_status

        except (TimeoutError, asyncio.TimeoutError):
            if test_device:
                try:
                    test_device.close()
                except Exception:
                    pass
            return None, None

        except Exception as e:
            if test_device:
                try:
                    test_device.close()
                except Exception:
                    pass
            raise

    async def _perform_connection(self) -> None:
        """Perform the actual connection logic."""
        # Get key variants to try (for encoding issues)
        key_variants = self._get_key_variants()
        error_914_count = 0

        # LocalTuya-inspired authentication with enhanced protocol detection
        if self.version == "auto":
            _LOGGER.info(f"Auto-detecting Tuya protocol version for {self.ip_address}")

            # Try each version with each key variant
            for test_version in [3.3, 3.4, 3.1, 3.2]:
                for key_variant, key_desc in key_variants:
                    _LOGGER.debug(
                        f"Testing version {test_version} with {key_desc} key for device {self.device_id[:8]}"
                    )
                    test_device = None

                    try:
                        test_device, test_status = await self._try_connect_with_key(
                            key_variant, float(test_version)
                        )

                        if test_status is None:
                            _LOGGER.debug(f"Version {test_version} ({key_desc}) timeout")
                            continue

                        # Check for Error 914
                        if self._is_error_914(test_status):
                            error_914_count += 1
                            _LOGGER.debug(
                                f"Error 914 with version {test_version} ({key_desc} key) - "
                                f"device key/version check failed"
                            )
                            if test_device:
                                try:
                                    test_device.close()
                                except Exception:
                                    pass
                            continue

                        # Check for valid DPS response
                        if (test_status and isinstance(test_status, dict) and
                            "dps" in test_status and test_status["dps"] and
                            len(test_status["dps"]) > 0):

                            self.version = str(test_version)
                            self._connection_stats["protocol_version_detected"] = str(test_version)

                            # If we used a variant key, update local_key
                            if key_variant != self.local_key:
                                _LOGGER.warning(
                                    f"Connection successful with {key_desc} key variant! "
                                    f"Original key had encoding issues."
                                )
                                self.local_key = key_variant

                            _LOGGER.info(f"Detected Tuya protocol version: {test_version}")
                            self._device = test_device
                            self._connected = True
                            return
                        else:
                            # Invalid response, cleanup and try next
                            if test_device:
                                try:
                                    test_device.close()
                                except Exception:
                                    pass

                    except asyncio.CancelledError:
                        if test_device:
                            try:
                                test_device.close()
                            except Exception:
                                pass
                        _LOGGER.warning(f"Protocol detection cancelled for version {test_version}")
                        raise

                    except Exception as e:
                        if test_device:
                            try:
                                test_device.close()
                            except Exception:
                                pass

                        # Check if this is an authentication error
                        error_msg = str(e).lower()
                        if any(keyword in error_msg for keyword in ["decrypt", "encrypt", "hmac", "key", "auth"]):
                            _LOGGER.error(f"Authentication error detected: {e}")
                            raise KKTAuthenticationError(
                                device_id=self.device_id,
                                message=f"Authentication failed - invalid local key: {e}"
                            ) from e

                        _LOGGER.debug(f"Version {test_version} ({key_desc}) failed: {type(e).__name__}")
                        continue

            # If we reach here, auto-detection failed
            if error_914_count > 0:
                _LOGGER.error(
                    f"Protocol auto-detection failed for device at {self.ip_address}\n"
                    f"Got Error 914 {error_914_count} times - this indicates:\n"
                    f"  - Local key is incorrect or has encoding issues\n"
                    f"  - Device may have been re-paired (key changed)\n"
                    f"  - Try using tinytuya wizard to get fresh key\n"
                    f"Key variants tried: {[desc for _, desc in key_variants]}"
                )
            else:
                _LOGGER.error(
                    f"Protocol auto-detection failed for device at {self.ip_address}\n"
                    f"Tested versions: 3.3, 3.4, 3.1, 3.2\n"
                    f"Common causes:\n"
                    f"  1. Device is offline or unreachable\n"
                    f"  2. Incorrect local key (check Tuya IoT Platform)\n"
                    f"  3. Device uses unsupported protocol version\n"
                    f"  4. Firewall blocking connection on port 6668\n"
                    f"Recommendation: Verify device is online and local key is correct"
                )
            raise KKTConnectionError(
                operation="auto_detect",
                device_id=self.device_id[:8],
                reason=f"Device not responding to any Tuya protocol version (3.1-3.4). "
                       f"Error 914 count: {error_914_count}. Check device connectivity and local key."
            )
        else:
            # Use specified version with key variants for encoding issues
            version_float = float(self.version) if self.version != "auto" else 3.3
            error_914_seen = False

            for key_variant, key_desc in key_variants:
                try:
                    test_device, test_status = await self._try_connect_with_key(
                        key_variant, version_float
                    )

                    if test_status is None:
                        _LOGGER.debug(f"Version {version_float} ({key_desc}) timeout")
                        continue

                    # Check for Error 914
                    if self._is_error_914(test_status):
                        error_914_seen = True
                        _LOGGER.debug(
                            f"Error 914 with version {version_float} ({key_desc} key)"
                        )
                        if test_device:
                            try:
                                test_device.close()
                            except Exception:
                                pass
                        continue

                    # Check for valid DPS response
                    if (test_status and isinstance(test_status, dict) and
                        "dps" in test_status and test_status["dps"]):

                        # If we used a variant key, update local_key
                        if key_variant != self.local_key:
                            _LOGGER.warning(
                                f"Connection successful with {key_desc} key variant! "
                                f"Original key had encoding issues."
                            )
                            self.local_key = key_variant

                        self._device = test_device
                        self._connected = True
                        _LOGGER.info(
                            f"Connected to device at {self.ip_address} using version {self.version}"
                        )
                        return
                    else:
                        # Invalid response
                        if test_device:
                            try:
                                test_device.close()
                            except Exception:
                                pass

                except asyncio.CancelledError:
                    raise

                except Exception as e:
                    # Check if this is an authentication error
                    error_msg = str(e).lower()
                    if any(keyword in error_msg for keyword in ["decrypt", "encrypt", "hmac", "key", "auth"]):
                        _LOGGER.error(f"Authentication error detected: {e}")
                        raise KKTAuthenticationError(
                            device_id=self.device_id,
                            message=f"Authentication failed - invalid local key: {e}"
                        ) from e
                    _LOGGER.debug(f"Version {version_float} ({key_desc}) failed: {e}")
                    continue

            # All key variants failed
            if error_914_seen:
                raise KKTConnectionError(
                    operation="validate_connection",
                    device_id=self.device_id[:8],
                    reason=f"Error 914: Device rejected all key variants for version {version_float}. "
                           f"Key may be incorrect or have unsupported encoding."
                )
            else:
                raise KKTConnectionError(
                    operation="validate_connection",
                    device_id=self.device_id[:8],
                    reason=f"Device did not return valid status for version {version_float}"
                )

    async def async_ensure_connected(self) -> None:
        """Ensure device is connected (async) with proper error handling."""
        if not self._connected:
            try:
                await self.async_connect()
            except (KKTConnectionError, KKTTimeoutError):
                # Re-raise our custom exceptions
                raise
            except Exception as e:
                # Convert any other exceptions to our format
                raise KKTConnectionError(
                    operation="ensure_connected",
                    device_id=self.device_id[:8],
                    reason=str(e)
                ) from e

    @property
    def is_connected(self) -> bool:
        """Return True if device is connected."""
        return self._connected and self._device is not None

    async def async_test_connection(self) -> bool:
        """Test connection to device without throwing exceptions (for config flow)."""
        try:
            await self.async_get_status()
            return True
        except (KKTConnectionError, KKTTimeoutError, KKTDataPointError):
            return False
        except Exception:
            return False

    async def async_disconnect(self) -> None:
        """Disconnect from device and cleanup resources properly."""
        from datetime import datetime

        _LOGGER.debug(f"Disconnecting from device {self.device_id[:8]}...")

        if self._device:
            try:
                # Close the socket connection
                self._device.close()
            except Exception as e:
                _LOGGER.debug(f"Error closing device socket: {e}")
            finally:
                self._device = None

        self._connected = False
        self._connection_stats["total_disconnects"] += 1
        self._connection_stats["last_disconnect_time"] = datetime.now().isoformat()

        _LOGGER.debug(f"Disconnected from device {self.device_id[:8]}")

    async def async_quick_check(self, timeout: float = 2.0) -> bool:
        """Quick pre-check if device is reachable before full protocol detection.

        This performs a simple TCP socket connection to see if the device
        is even reachable, avoiding the longer protocol detection process
        for clearly unreachable devices.
        """
        try:
            # Try to open a socket connection to the Tuya port (6668)
            loop = asyncio.get_running_loop()

            def _check_socket():
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                try:
                    result = sock.connect_ex((self.ip_address, 6668))
                    return result == 0
                except (TimeoutError, OSError):
                    return False
                finally:
                    sock.close()

            is_reachable: bool = await asyncio.wait_for(
                loop.run_in_executor(None, _check_socket),
                timeout=timeout + 0.5
            )

            if not is_reachable:
                _LOGGER.debug(f"Quick check: Device {self.ip_address} not reachable on port 6668")
            return is_reachable

        except TimeoutError:
            _LOGGER.debug(f"Quick check timeout for {self.ip_address}")
            return False
        except Exception as e:
            _LOGGER.debug(f"Quick check error for {self.ip_address}: {e}")
            return False

    @property
    def connection_stats(self) -> dict[str, Any]:
        """Get connection statistics for diagnostics."""
        return {
            **self._connection_stats,
            "is_connected": self._connected,
            "device_id": self.device_id[:8] + "...",
            "ip_address": self.ip_address,
            "protocol_version": self.version,
        }

    def _configure_socket_keepalive(self, device: Any) -> None:
        """Configure TCP Keep-Alive on the device socket."""
        try:
            # Get the underlying socket if available
            if hasattr(device, '_socket') and device._socket:
                sock = device._socket
                # Enable TCP Keep-Alive
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

                # Platform-specific keep-alive settings
                import platform
                if platform.system() == 'Linux':
                    # TCP_KEEPIDLE - time before sending keepalive probes
                    tcp_keepidle = getattr(socket, 'TCP_KEEPIDLE', 4)  # 4 is the value on Linux
                    sock.setsockopt(socket.IPPROTO_TCP, tcp_keepidle, TCP_KEEPALIVE_IDLE)
                    # TCP_KEEPINTVL - interval between probes
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, TCP_KEEPALIVE_INTERVAL)
                    # TCP_KEEPCNT - number of failed probes before declaring dead
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, TCP_KEEPALIVE_COUNT)
                elif platform.system() == 'Darwin':  # macOS
                    # macOS uses TCP_KEEPALIVE for idle time
                    sock.setsockopt(socket.IPPROTO_TCP, 0x10, TCP_KEEPALIVE_IDLE)

                _LOGGER.debug(f"TCP Keep-Alive configured for device {self.device_id[:8]}")
        except Exception as e:
            _LOGGER.debug(f"Could not configure TCP Keep-Alive: {e}")

    @property
    def is_on(self) -> bool:
        """Return True if device is on (DP 1)."""
        return bool(self.get_dp_value(1, False))

    def get_dp_value(self, dp: int, default: Any = None) -> Any:
        """Get data point value from cached status."""
        return self._status.get("dps", {}).get(str(dp), default)

    async def async_get_status(self) -> dict[str, Any]:
        """Get current device status asynchronously with explicit status retrieval logic.

        Important: Tuya devices often send partial updates (delta updates).
        TinyTuya internally merges these into a cached status.
        This method returns the merged/cached data, not just the last partial update.
        """
        await self.async_ensure_connected()

        if not self._device:
            raise KKTConnectionError(
                operation="get_status",
                device_id=self.device_id[:8],
                reason="Device not connected"
            )

        try:
            # Explicit status() call with timeout protection
            # This triggers a status request and tinytuya internally merges
            # the response with any cached data
            status = await asyncio.wait_for(
                self._run_executor_job(self._device.status),
                timeout=10.0
            )

            # Enhanced validation and error handling
            if not status:
                raise KKTDataPointError(
                    operation="get_status",
                    device_id=self.device_id[:8],
                    reason="Device returned empty status"
                )

            if not isinstance(status, dict):
                raise KKTDataPointError(
                    operation="get_status",
                    device_id=self.device_id[:8],
                    reason=f"Invalid status format: {type(status)}"
                )

            if "dps" not in status:
                raise KKTDataPointError(
                    operation="get_status",
                    device_id=self.device_id[:8],
                    reason="Status missing 'dps' field"
                )

            # Try to get the merged/cached DPs from tinytuya
            # TinyTuya maintains a dps_cache that contains all DPs seen so far
            # This is crucial for devices that send partial updates (delta updates)
            dps: dict[str, Any] = status.get("dps", {})
            partial_update_count = len(dps)

            # Debug: Log available cache attributes
            _LOGGER.debug(
                f"Cache check: dps_cache exists={hasattr(self._device, 'dps_cache')}, "
                f"_cache exists={hasattr(self._device, '_cache')}"
            )

            # Check for dps_cache (merged DPs from all updates)
            if hasattr(self._device, 'dps_cache'):
                cached_dps = self._device.dps_cache
                _LOGGER.debug(f"dps_cache content: {list(cached_dps.keys()) if cached_dps else 'empty'}")
                if isinstance(cached_dps, dict) and len(cached_dps) > len(dps):
                    _LOGGER.debug(
                        f"Using merged dps_cache with {len(cached_dps)} data points "
                        f"(partial update had {partial_update_count} DPs)"
                    )
                    dps = cached_dps

            # Alternative: try _cache directly (tinytuya internal)
            if hasattr(self._device, '_cache') and self._device._cache:
                internal_cache = self._device._cache
                if isinstance(internal_cache, dict) and 'dps' in internal_cache:
                    cached_dps = internal_cache.get('dps', {})
                    _LOGGER.debug(f"_cache['dps'] content: {list(cached_dps.keys()) if cached_dps else 'empty'}")
                    if len(cached_dps) > len(dps):
                        _LOGGER.debug(
                            f"Using _cache['dps'] with {len(cached_dps)} data points "
                            f"(current has {len(dps)} DPs)"
                        )
                        dps = cached_dps

            self._status = {"dps": dps}  # Store for get_dp_value()
            _LOGGER.debug(f"Retrieved status with {len(dps)} data points: {list(dps.keys())}")
            return dps

        except asyncio.CancelledError:
            # Handle cancellation - cleanup but re-raise
            self._connected = False
            self._device = None
            _LOGGER.debug(f"get_status cancelled for device at {self.ip_address}")
            raise

        except TimeoutError as timeout_err:
            self._connected = False
            self._device = None
            raise KKTTimeoutError(
                operation="get_status",
                device_id=self.device_id[:8],
                timeout=10.0
            ) from timeout_err
        except (KKTDataPointError, KKTTimeoutError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            _LOGGER.error(f"Failed to get device status: {e}")
            self._connected = False  # Mark as disconnected on error - LocalTuya pattern
            self._device = None  # Clear device reference like LocalTuya
            raise KKTConnectionError(
                operation="get_status",
                device_id=self.device_id[:8],
                reason=str(e)
            ) from e

    async def async_update_status(self) -> None:
        """Update device status asynchronously with timeout protection."""
        await self.async_ensure_connected()

        if not self._device:
            raise KKTConnectionError(
                operation="update_status",
                device_id=self.device_id[:8],
                reason="Device not connected"
            )

        try:
            # Explicit status() call with timeout protection
            status = await asyncio.wait_for(
                self._run_executor_job(self._device.status),
                timeout=10.0
            )

            if status and isinstance(status, dict):
                self._status = status
                _LOGGER.debug(f"Status updated with {len(status.get('dps', {}))} data points")
            else:
                _LOGGER.warning("Received invalid status during update")

        except asyncio.CancelledError:
            # Handle cancellation - cleanup but re-raise
            self._connected = False
            self._device = None
            _LOGGER.debug(f"update_status cancelled for device at {self.ip_address}")
            raise

        except TimeoutError as timeout_err:
            self._connected = False
            self._device = None
            raise KKTTimeoutError(
                operation="update_status",
                device_id=self.device_id[:8],
                timeout=10.0
            ) from timeout_err
        except Exception as e:
            _LOGGER.error(f"Failed to update device status: {e}")
            # Properly close connection on error like LocalTuya
            if self._device:
                try:
                    self._device.close()
                except Exception:
                    pass  # Ignore errors during cleanup
            self._connected = False
            self._device = None
            raise KKTConnectionError(
                operation="update_status",
                device_id=self.device_id[:8],
                reason=str(e)
            ) from e

    async def async_set_dp(self, dp: int, value: Any) -> bool:
        """Set data point value asynchronously with explicit data point writing logic."""
        await self.async_ensure_connected()

        if not self._device:
            raise KKTConnectionError(
                operation="set_dp",
                device_id=self.device_id[:8],
                reason="Device not connected"
            )

        try:
            # Explicit set_value() call with timeout protection
            result = await asyncio.wait_for(
                self._run_executor_job(self._device.set_value, dp, value),
                timeout=8.0
            )

            # Validate the result
            if result is None:
                _LOGGER.warning(f"set_value returned None for DP {dp} = {value}")

            _LOGGER.debug(f"Successfully set DP {dp} to {value}")
            return True

        except asyncio.CancelledError:
            # Handle cancellation - cleanup but re-raise
            self._connected = False
            self._device = None
            _LOGGER.debug(f"set_dp cancelled for DP {dp} on device at {self.ip_address}")
            raise

        except TimeoutError as timeout_err:
            self._connected = False
            self._device = None
            raise KKTTimeoutError(
                operation="set_dp",
                device_id=self.device_id[:8],
                data_point=dp,
                timeout=8.0
            ) from timeout_err
        except Exception as e:
            _LOGGER.error(f"Failed to set DP {dp} to {value}: {e}")
            # Properly close connection on error like LocalTuya
            if self._device:
                try:
                    self._device.close()
                except Exception:
                    pass  # Ignore errors during cleanup
            self._connected = False
            self._device = None
            raise KKTDataPointError(
                operation="set_dp",
                device_id=self.device_id[:8],
                data_point=dp,
                reason=str(e)
            ) from e

    def turn_on(self) -> None:
        """Turn device on (DP 1 = True). DEPRECATED: Use coordinator.async_set_data_point() instead."""
        _LOGGER.warning("turn_on() is deprecated. Use coordinator.async_set_data_point() instead.")
        self._create_safe_task(self.async_set_dp(1, True))

    def turn_off(self) -> None:
        """Turn device off (DP 1 = False). DEPRECATED: Use coordinator.async_set_data_point() instead."""
        _LOGGER.warning("turn_off() is deprecated. Use coordinator.async_set_data_point() instead.")
        self._create_safe_task(self.async_set_dp(1, False))

    def set_fan_speed(self, speed: str) -> None:
        """Set fan speed (DP 10). DEPRECATED: Use coordinator.async_set_data_point() instead."""
        _LOGGER.warning("set_fan_speed() is deprecated. Use coordinator.async_set_data_point() instead.")
        speed_map = {
            "off": "0",
            "low": "1",
            "middle": "2",
            "high": "3",
            "strong": "4"
        }
        if speed in speed_map:
            self._create_safe_task(self.async_set_dp(10, speed_map[speed]))

    @property
    def fan_speed(self) -> str:
        """Get current fan speed."""
        speed_value = self.get_dp_value(10, "0")
        speed_map = {
            "0": "off",
            "1": "low",
            "2": "middle",
            "3": "high",
            "4": "strong"
        }
        return speed_map.get(str(speed_value), "off")

    def set_light(self, state: bool) -> None:
        """Set light state (DP 4)."""
        self._create_safe_task(self.async_set_dp(4, state))

    @property
    def light_on(self) -> bool:
        """Return True if light is on."""
        return bool(self.get_dp_value(4, False))

    def set_rgb_mode(self, mode: int) -> None:
        """Set RGB mode (DP 101)."""
        if 0 <= mode <= 9:
            self._create_safe_task(self.async_set_dp(101, mode))

    @property
    def rgb_mode(self) -> int:
        """Get current RGB mode."""
        return int(self.get_dp_value(101, 0))

    def set_countdown(self, minutes: int) -> None:
        """Set countdown timer (DP 13)."""
        if 0 <= minutes <= 60:
            self._create_safe_task(self.async_set_dp(13, minutes))

    @property
    def countdown_minutes(self) -> int:
        """Get current countdown timer minutes."""
        return int(self.get_dp_value(13, 0))

    @property
    def light_brightness(self) -> int:
        """Get current light brightness (DP 5)."""
        return int(self.get_dp_value(5, 255))

    def set_light_brightness(self, brightness: int) -> None:
        """Set light brightness (DP 5)."""
        self._create_safe_task(self.async_set_dp(5, max(0, min(255, brightness))))

    @property
    def rgb_brightness(self) -> int:
        """Get current RGB brightness (DP 102)."""
        return int(self.get_dp_value(102, 255))

    def set_rgb_brightness(self, brightness: int) -> None:
        """Set RGB brightness (DP 102)."""
        self._create_safe_task(self.async_set_dp(102, max(0, min(255, brightness))))

    @property
    def filter_hours(self) -> int:
        """Get filter usage hours (DP 14)."""
        return int(self.get_dp_value(14, 0))

    def reset_filter(self) -> None:
        """Reset filter (DP 15)."""
        self._create_safe_task(self.async_set_dp(15, True))

    def set_fan_speed_direct(self, speed: str) -> None:
        """Set fan speed directly (DP 11)."""
        speed_map = {
            "off": 0,
            "low": 1,
            "middle": 2,
            "high": 3,
            "strong": 4
        }
        if speed in speed_map:
            self._create_safe_task(self.async_set_dp(11, speed_map[speed]))

    @property
    def fan_speed_setting(self) -> str:
        """Get current fan speed setting (DP 11)."""
        speed_value = self.get_dp_value(11, 0)
        speed_map = {
            0: "off",
            1: "low",
            2: "middle",
            3: "high",
            4: "strong"
        }
        return speed_map.get(speed_value, "off")

    # === COOKTOP METHODS FOR IND7705HC ===

    def get_zone_power_level(self, zone: int) -> int:
        """Get power level for specific zone (1-5) from DP 162 bitfield."""
        if not 1 <= zone <= 5:
            return 0
        raw_value = self.get_dp_value(162, b'\x00' * 5)
        if isinstance(raw_value, (bytes, bytearray)) and len(raw_value) >= zone:
            return raw_value[zone - 1]
        return 0

    def set_zone_power_level(self, zone: int, level: int) -> None:
        """Set power level for specific zone (1-5) in DP 162 bitfield."""
        if not (1 <= zone <= 5 and 0 <= level <= 25):
            return
        raw_value = self.get_dp_value(162, b'\x00' * 5)
        if isinstance(raw_value, (bytes, bytearray)):
            data = bytearray(raw_value)
        else:
            data = bytearray(5)
        if len(data) >= zone:
            data[zone - 1] = level
            self._create_safe_task(self.async_set_dp(162, bytes(data)))

    def get_zone_timer(self, zone: int) -> int:
        """Get timer for specific zone (1-5) from DP 167 bitfield."""
        if not 1 <= zone <= 5:
            return 0
        raw_value = self.get_dp_value(167, b'\x00' * 5)
        if isinstance(raw_value, (bytes, bytearray)) and len(raw_value) >= zone:
            return raw_value[zone - 1]
        return 0

    def set_zone_timer(self, zone: int, minutes: int) -> None:
        """Set timer for specific zone (1-5) in DP 167 bitfield."""
        if not (1 <= zone <= 5 and 0 <= minutes <= 255):
            return
        raw_value = self.get_dp_value(167, b'\x00' * 5)
        if isinstance(raw_value, (bytes, bytearray)):
            data = bytearray(raw_value)
        else:
            data = bytearray(5)
        if len(data) >= zone:
            data[zone - 1] = minutes
            self._create_safe_task(self.async_set_dp(167, bytes(data)))

    def get_zone_core_temp(self, zone: int) -> int:
        """Get core temperature for specific zone (1-5) from DP 168 bitfield."""
        if not 1 <= zone <= 5:
            return 0
        raw_value = self.get_dp_value(168, b'\x00' * 5)
        if isinstance(raw_value, (bytes, bytearray)) and len(raw_value) >= zone:
            return raw_value[zone - 1]
        return 0

    def set_zone_core_temp(self, zone: int, temp: int) -> None:
        """Set core temperature for specific zone (1-5) in DP 168 bitfield."""
        if not (1 <= zone <= 5 and 0 <= temp <= 300):
            return
        raw_value = self.get_dp_value(168, b'\x00' * 5)
        if isinstance(raw_value, (bytes, bytearray)):
            data = bytearray(raw_value)
        else:
            data = bytearray(5)
        if len(data) >= zone:
            data[zone - 1] = temp
            self._create_safe_task(self.async_set_dp(168, bytes(data)))

    def get_zone_core_temp_display(self, zone: int) -> int:
        """Get displayed core temperature for specific zone (1-5) from DP 169 bitfield."""
        if not 1 <= zone <= 5:
            return 0
        raw_value = self.get_dp_value(169, b'\x00' * 5)
        if isinstance(raw_value, (bytes, bytearray)) and len(raw_value) >= zone:
            return raw_value[zone - 1]
        return 0

    def get_zone_error(self, zone: int) -> int:
        """Get error code for specific zone (1-5) from DP 105 bitfield."""
        if not 1 <= zone <= 5:
            return 0
        raw_value = self.get_dp_value(105, b'\x00' * 5)
        if isinstance(raw_value, (bytes, bytearray)) and len(raw_value) >= zone:
            return raw_value[zone - 1]
        return 0

    def is_zone_selected(self, zone: int) -> bool:
        """Check if specific zone (1-5) is selected from DP 161 bitfield."""
        if not 1 <= zone <= 5:
            return False
        raw_value = self.get_dp_value(161, b'\x00')
        if isinstance(raw_value, (bytes, bytearray)) and len(raw_value) > 0:
            return bool(raw_value[0] & (1 << (zone - 1)))
        return False

    def set_zone_selected(self, zone: int, selected: bool) -> None:
        """Set zone selection for specific zone (1-5) in DP 161 bitfield."""
        if not 1 <= zone <= 5:
            return
        raw_value = self.get_dp_value(161, b'\x00')
        if isinstance(raw_value, (bytes, bytearray)) and len(raw_value) > 0:
            data = raw_value[0]
        else:
            data = 0
        if selected:
            data |= (1 << (zone - 1))
        else:
            data &= ~(1 << (zone - 1))
        self._create_safe_task(self.async_set_dp(161, bytes([data])))

    def is_zone_boost(self, zone: int) -> bool:
        """Check if specific zone (1-5) is in boost mode from DP 163 bitfield."""
        if not 1 <= zone <= 5:
            return False
        raw_value = self.get_dp_value(163, b'\x00')
        if isinstance(raw_value, (bytes, bytearray)) and len(raw_value) > 0:
            return bool(raw_value[0] & (1 << (zone - 1)))
        return False

    def set_zone_boost(self, zone: int, boost: bool) -> None:
        """Set boost mode for specific zone (1-5) in DP 163 bitfield."""
        if not 1 <= zone <= 5:
            return
        raw_value = self.get_dp_value(163, b'\x00')
        if isinstance(raw_value, (bytes, bytearray)) and len(raw_value) > 0:
            data = raw_value[0]
        else:
            data = 0
        if boost:
            data |= (1 << (zone - 1))
        else:
            data &= ~(1 << (zone - 1))
        self._create_safe_task(self.async_set_dp(163, bytes([data])))

    def is_zone_keep_warm(self, zone: int) -> bool:
        """Check if specific zone (1-5) is in keep warm mode from DP 164 bitfield."""
        if not 1 <= zone <= 5:
            return False
        raw_value = self.get_dp_value(164, b'\x00')
        if isinstance(raw_value, (bytes, bytearray)) and len(raw_value) > 0:
            return bool(raw_value[0] & (1 << (zone - 1)))
        return False

    def set_zone_keep_warm(self, zone: int, keep_warm: bool) -> None:
        """Set keep warm mode for specific zone (1-5) in DP 164 bitfield."""
        if not 1 <= zone <= 5:
            return
        raw_value = self.get_dp_value(164, b'\x00')
        if isinstance(raw_value, (bytes, bytearray)) and len(raw_value) > 0:
            data = raw_value[0]
        else:
            data = 0
        if keep_warm:
            data |= (1 << (zone - 1))
        else:
            data &= ~(1 << (zone - 1))
        self._create_safe_task(self.async_set_dp(164, bytes([data])))

    def is_flex_zone_active(self, side: str) -> bool:
        """Check if flex zone is active (left/right) from DP 165 bitfield."""
        if side not in ["left", "right"]:
            return False
        raw_value = self.get_dp_value(165, b'\x00')
        if isinstance(raw_value, (bytes, bytearray)) and len(raw_value) > 0:
            bit = 0 if side == "left" else 1
            return bool(raw_value[0] & (1 << bit))
        return False

    def set_flex_zone(self, side: str, active: bool) -> None:
        """Set flex zone active state (left/right) in DP 165 bitfield."""
        if side not in ["left", "right"]:
            return
        raw_value = self.get_dp_value(165, b'\x00')
        if isinstance(raw_value, (bytes, bytearray)) and len(raw_value) > 0:
            data = raw_value[0]
        else:
            data = 0
        bit = 0 if side == "left" else 1
        if active:
            data |= (1 << bit)
        else:
            data &= ~(1 << bit)
        self._create_safe_task(self.async_set_dp(165, bytes([data])))

    def is_bbq_mode_active(self, side: str) -> bool:
        """Check if BBQ mode is active (left/right) from DP 166 bitfield."""
        if side not in ["left", "right"]:
            return False
        raw_value = self.get_dp_value(166, b'\x00')
        if isinstance(raw_value, (bytes, bytearray)) and len(raw_value) > 0:
            bit = 0 if side == "left" else 1
            return bool(raw_value[0] & (1 << bit))
        return False

    def set_bbq_mode(self, side: str, active: bool) -> None:
        """Set BBQ mode active state (left/right) in DP 166 bitfield."""
        if side not in ["left", "right"]:
            return
        raw_value = self.get_dp_value(166, b'\x00')
        if isinstance(raw_value, (bytes, bytearray)) and len(raw_value) > 0:
            data = raw_value[0]
        else:
            data = 0
        bit = 0 if side == "left" else 1
        if active:
            data |= (1 << bit)
        else:
            data &= ~(1 << bit)
        self._create_safe_task(self.async_set_dp(166, bytes([data])))

    # Basic cooktop properties
    @property
    def cooktop_power_on(self) -> bool:
        """Get cooktop main power state (DP 101)."""
        return bool(self.get_dp_value(101, False))

    @property
    def cooktop_paused(self) -> bool:
        """Get cooktop pause state (DP 102)."""
        return bool(self.get_dp_value(102, False))

    @property
    def cooktop_child_lock(self) -> bool:
        """Get cooktop child lock state (DP 103)."""
        return bool(self.get_dp_value(103, False))

    @property
    def cooktop_max_level(self) -> int:
        """Get cooktop max power level (DP 104)."""
        return int(self.get_dp_value(104, 0))

    @property
    def cooktop_timer(self) -> int:
        """Get cooktop general timer (DP 134)."""
        return int(self.get_dp_value(134, 0))

    @property
    def cooktop_senior_mode(self) -> bool:
        """Get cooktop senior mode state (DP 145)."""
        return bool(self.get_dp_value(145, False))

    def set_cooktop_power(self, state: bool) -> None:
        """Set cooktop main power (DP 101)."""
        self._create_safe_task(self.async_set_dp(101, state))

    def set_cooktop_pause(self, state: bool) -> None:
        """Set cooktop pause state (DP 102)."""
        self._create_safe_task(self.async_set_dp(102, state))

    def set_cooktop_child_lock(self, state: bool) -> None:
        """Set cooktop child lock (DP 103)."""
        self._create_safe_task(self.async_set_dp(103, state))

    def set_cooktop_max_level(self, level: int) -> None:
        """Set cooktop max power level (DP 104)."""
        if 0 <= level <= 25:
            self._create_safe_task(self.async_set_dp(104, level))

    def set_cooktop_timer(self, minutes: int) -> None:
        """Set cooktop general timer (DP 134)."""
        if 0 <= minutes <= 99:
            self._create_safe_task(self.async_set_dp(134, minutes))

    def set_cooktop_senior_mode(self, state: bool) -> None:
        """Set cooktop senior mode (DP 145)."""
        self._create_safe_task(self.async_set_dp(145, state))

    def set_cooktop_confirm(self, state: bool) -> None:
        """Set cooktop confirm action (DP 108)."""
        self._create_safe_task(self.async_set_dp(108, state))
