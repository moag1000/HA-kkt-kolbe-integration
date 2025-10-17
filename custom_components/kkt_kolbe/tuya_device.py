"""KKT Kolbe Tuya Device Handler - v1.5.6 with enhanced error handling and timeout protection."""
import asyncio
import logging
from typing import Any, Dict

import tinytuya

from .exceptions import (
    KKTConnectionError,
    KKTTimeoutError,
    KKTDataPointError
)

_LOGGER = logging.getLogger(__name__)

class KKTKolbeTuyaDevice:
    """Handle communication with KKT Kolbe device via Tuya protocol."""

    def __init__(self, device_id: str, ip_address: str, local_key: str, version: str = "auto"):
        """Initialize the Tuya device connection."""
        self.device_id = device_id
        self.ip_address = ip_address
        self.local_key = local_key
        self.version = version
        self._device = None
        self._status = {}
        self._connected = False
        # Don't connect in __init__ - will be done async

    def _handle_task_result(self, task):
        """Handle completed async task results and log errors."""
        try:
            task.result()  # This will raise the exception if the task failed
        except Exception as e:
            _LOGGER.error(f"Async task failed: {e}")

    def _create_safe_task(self, coro):
        """Create async task with error handling."""
        task = asyncio.create_task(coro)
        task.add_done_callback(self._handle_task_result)
        return task

    async def async_connect(self) -> None:
        """Establish async connection to the device with timeout protection."""
        if self._connected:
            return

        try:
            # Apply timeout protection for connection operations
            await asyncio.wait_for(self._perform_connection(), timeout=15.0)

        except asyncio.TimeoutError:
            self._connected = False
            _LOGGER.error(f"Connection timeout after 15 seconds for device {self.ip_address}")
            self._device = None
            raise KKTTimeoutError(
                operation="connect",
                device_id=self.device_id[:8],
                timeout=15.0
            )
        except Exception as e:
            self._connected = False
            _LOGGER.error(f"Failed to connect to device: {e}")
            self._device = None
            raise KKTConnectionError(
                operation="connect",
                device_id=self.device_id[:8],
                reason=str(e)
            )

    async def _perform_connection(self) -> None:
        """Perform the actual connection logic."""
        loop = asyncio.get_event_loop()

        # LocalTuya-inspired authentication with enhanced protocol detection
        if self.version == "auto":
            _LOGGER.info(f"Auto-detecting Tuya protocol version for {self.ip_address}")
            # LocalTuya order: 3.3 default first, then 3.4, 3.1, 3.2 (proven compatibility)
            for test_version in [3.3, 3.4, 3.1, 3.2]:
                try:
                    test_device = await loop.run_in_executor(
                        None,
                        lambda v=test_version: tinytuya.Device(
                            dev_id=self.device_id,
                            address=self.ip_address,
                            local_key=self.local_key,
                            version=float(v)  # Use float like LocalTuya
                        )
                    )

                    # Configure device with LocalTuya-style settings
                    test_device.set_socketPersistent(True)
                    test_device.set_socketNODELAY(True)
                    test_device.set_socketTimeout(5)
                    test_device.set_socketRetryLimit(3)

                    # Enhanced validation with explicit status() call and DPS detection
                    test_status = await asyncio.wait_for(
                        loop.run_in_executor(None, test_device.status),
                        timeout=5.0
                    )

                    # Try to detect available DPS for enhanced validation
                    try:
                        available_dps = await asyncio.wait_for(
                            loop.run_in_executor(None, test_device.detect_available_dps),
                            timeout=3.0
                        )
                        _LOGGER.debug(f"Detected DPS for version {test_version}: {available_dps}")
                    except Exception:
                        # DPS detection is optional - continue if it fails
                        pass

                    # LocalTuya-style validation: Check for datapoints like LocalTuya does
                    if (test_status and isinstance(test_status, dict) and
                        "dps" in test_status and test_status["dps"] and
                        len(test_status["dps"]) > 0):
                        self.version = str(test_version)
                        _LOGGER.info(f"Detected Tuya protocol version: {test_version}")
                        self._device = test_device
                        self._connected = True
                        return

                except asyncio.TimeoutError:
                    _LOGGER.debug(f"Version {test_version} timeout - trying next version")
                    continue
                except Exception as e:
                    _LOGGER.debug(f"Version {test_version} failed: {e} - trying next version")
                    continue

            # If we reach here, auto-detection failed
            _LOGGER.error(f"Auto-detection failed for all versions (3.3, 3.4, 3.1, 3.2)")
            raise KKTConnectionError(
                operation="auto_detect",
                device_id=self.device_id[:8],
                reason="No compatible version found - device not responding to any Tuya protocol"
            )
        else:
            # Use specified version with LocalTuya-style configuration
            version_float = float(self.version) if self.version != "auto" else 3.3
            self._device = await loop.run_in_executor(
                None,
                lambda: tinytuya.Device(
                    dev_id=self.device_id,
                    address=self.ip_address,
                    local_key=self.local_key,
                    version=version_float
                )
            )
            # Apply LocalTuya-style socket configuration
            self._device.set_socketPersistent(True)
            self._device.set_socketNODELAY(True)
            self._device.set_socketTimeout(5)
            self._device.set_socketRetryLimit(3)
            self._connected = True
            _LOGGER.info(f"Connected to KKT Kolbe device at {self.ip_address} (version {self.version})")

    async def async_ensure_connected(self):
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
                )

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

    @property
    def is_on(self) -> bool:
        """Return True if device is on (DP 1)."""
        return self.get_dp_value(1, False)

    def get_dp_value(self, dp: int, default=None):
        """Get data point value from cached status."""
        return self._status.get("dps", {}).get(str(dp), default)

    async def async_get_status(self) -> Dict:
        """Get current device status asynchronously with explicit status retrieval logic."""
        await self.async_ensure_connected()

        if not self._device:
            raise KKTConnectionError(
                operation="get_status",
                device_id=self.device_id[:8],
                reason="Device not connected"
            )

        try:
            loop = asyncio.get_event_loop()

            # Explicit status() call with timeout protection
            status = await asyncio.wait_for(
                loop.run_in_executor(None, self._device.status),
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

            self._status = status
            _LOGGER.debug(f"Retrieved status with {len(status.get('dps', {}))} data points")
            return self._status.get("dps", {})

        except asyncio.TimeoutError:
            self._connected = False
            self._device = None
            raise KKTTimeoutError(
                operation="get_status",
                device_id=self.device_id[:8],
                timeout=10.0
            )
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
            )

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
            loop = asyncio.get_event_loop()

            # Explicit status() call with timeout protection
            status = await asyncio.wait_for(
                loop.run_in_executor(None, self._device.status),
                timeout=10.0
            )

            if status and isinstance(status, dict):
                self._status = status
                _LOGGER.debug(f"Status updated with {len(status.get('dps', {}))} data points")
            else:
                _LOGGER.warning("Received invalid status during update")

        except asyncio.TimeoutError:
            self._connected = False
            self._device = None
            raise KKTTimeoutError(
                operation="update_status",
                device_id=self.device_id[:8],
                timeout=10.0
            )
        except Exception as e:
            _LOGGER.error(f"Failed to update device status: {e}")
            # Properly close connection on error like LocalTuya
            if self._device:
                try:
                    self._device.close()
                except:
                    pass  # Ignore errors during cleanup
            self._connected = False
            self._device = None
            raise KKTConnectionError(
                operation="update_status",
                device_id=self.device_id[:8],
                reason=str(e)
            )

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
            loop = asyncio.get_event_loop()

            # Explicit set_value() call with timeout protection
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._device.set_value,
                    dp,
                    value
                ),
                timeout=8.0
            )

            # Validate the result
            if result is None:
                _LOGGER.warning(f"set_value returned None for DP {dp} = {value}")

            _LOGGER.debug(f"Successfully set DP {dp} to {value}")
            return True

        except asyncio.TimeoutError:
            self._connected = False
            self._device = None
            raise KKTTimeoutError(
                operation="set_dp",
                device_id=self.device_id[:8],
                data_point=dp,
                timeout=8.0
            )
        except Exception as e:
            _LOGGER.error(f"Failed to set DP {dp} to {value}: {e}")
            # Properly close connection on error like LocalTuya
            if self._device:
                try:
                    self._device.close()
                except:
                    pass  # Ignore errors during cleanup
            self._connected = False
            self._device = None
            raise KKTDataPointError(
                operation="set_dp",
                device_id=self.device_id[:8],
                data_point=dp,
                reason=str(e)
            )

    def turn_on(self):
        """Turn device on (DP 1 = True). DEPRECATED: Use coordinator.async_set_data_point() instead."""
        _LOGGER.warning("turn_on() is deprecated. Use coordinator.async_set_data_point() instead.")
        self._create_safe_task(self.async_set_dp(1, True))

    def turn_off(self):
        """Turn device off (DP 1 = False). DEPRECATED: Use coordinator.async_set_data_point() instead."""
        _LOGGER.warning("turn_off() is deprecated. Use coordinator.async_set_data_point() instead.")
        self._create_safe_task(self.async_set_dp(1, False))

    def set_fan_speed(self, speed: str):
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

    def set_light(self, state: bool):
        """Set light state (DP 4)."""
        self._create_safe_task(self.async_set_dp(4, state))

    @property
    def light_on(self) -> bool:
        """Return True if light is on."""
        return self.get_dp_value(4, False)

    def set_rgb_mode(self, mode: int):
        """Set RGB mode (DP 101)."""
        if 0 <= mode <= 9:
            self._create_safe_task(self.async_set_dp(101, mode))

    @property
    def rgb_mode(self) -> int:
        """Get current RGB mode."""
        return self.get_dp_value(101, 0)

    def set_countdown(self, minutes: int):
        """Set countdown timer (DP 13)."""
        if 0 <= minutes <= 60:
            self._create_safe_task(self.async_set_dp(13, minutes))

    @property
    def countdown_minutes(self) -> int:
        """Get current countdown timer minutes."""
        return self.get_dp_value(13, 0)

    @property
    def light_brightness(self) -> int:
        """Get current light brightness (DP 5)."""
        return self.get_dp_value(5, 255)

    def set_light_brightness(self, brightness: int):
        """Set light brightness (DP 5)."""
        self._create_safe_task(self.async_set_dp(5, max(0, min(255, brightness))))

    @property
    def rgb_brightness(self) -> int:
        """Get current RGB brightness (DP 102)."""
        return self.get_dp_value(102, 255)

    def set_rgb_brightness(self, brightness: int):
        """Set RGB brightness (DP 102)."""
        self._create_safe_task(self.async_set_dp(102, max(0, min(255, brightness))))

    @property
    def filter_hours(self) -> int:
        """Get filter usage hours (DP 14)."""
        return self.get_dp_value(14, 0)

    def reset_filter(self):
        """Reset filter (DP 15)."""
        self._create_safe_task(self.async_set_dp(15, True))

    def set_fan_speed_direct(self, speed: str):
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

    def set_zone_power_level(self, zone: int, level: int):
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

    def set_zone_timer(self, zone: int, minutes: int):
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

    def set_zone_core_temp(self, zone: int, temp: int):
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

    def set_zone_selected(self, zone: int, selected: bool):
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

    def set_zone_boost(self, zone: int, boost: bool):
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

    def set_zone_keep_warm(self, zone: int, keep_warm: bool):
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

    def set_flex_zone(self, side: str, active: bool):
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

    def set_bbq_mode(self, side: str, active: bool):
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
        return self.get_dp_value(101, False)

    @property
    def cooktop_paused(self) -> bool:
        """Get cooktop pause state (DP 102)."""
        return self.get_dp_value(102, False)

    @property
    def cooktop_child_lock(self) -> bool:
        """Get cooktop child lock state (DP 103)."""
        return self.get_dp_value(103, False)

    @property
    def cooktop_max_level(self) -> int:
        """Get cooktop max power level (DP 104)."""
        return self.get_dp_value(104, 0)

    @property
    def cooktop_timer(self) -> int:
        """Get cooktop general timer (DP 134)."""
        return self.get_dp_value(134, 0)

    @property
    def cooktop_senior_mode(self) -> bool:
        """Get cooktop senior mode state (DP 145)."""
        return self.get_dp_value(145, False)

    def set_cooktop_power(self, state: bool):
        """Set cooktop main power (DP 101)."""
        self._create_safe_task(self.async_set_dp(101, state))

    def set_cooktop_pause(self, state: bool):
        """Set cooktop pause state (DP 102)."""
        self._create_safe_task(self.async_set_dp(102, state))

    def set_cooktop_child_lock(self, state: bool):
        """Set cooktop child lock (DP 103)."""
        self._create_safe_task(self.async_set_dp(103, state))

    def set_cooktop_max_level(self, level: int):
        """Set cooktop max power level (DP 104)."""
        if 0 <= level <= 25:
            self._create_safe_task(self.async_set_dp(104, level))

    def set_cooktop_timer(self, minutes: int):
        """Set cooktop general timer (DP 134)."""
        if 0 <= minutes <= 99:
            self._create_safe_task(self.async_set_dp(134, minutes))

    def set_cooktop_senior_mode(self, state: bool):
        """Set cooktop senior mode (DP 145)."""
        self._create_safe_task(self.async_set_dp(145, state))

    def set_cooktop_confirm(self, state: bool):
        """Set cooktop confirm action (DP 108)."""
        self._create_safe_task(self.async_set_dp(108, state))