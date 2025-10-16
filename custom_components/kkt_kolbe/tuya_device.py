"""Tuya device communication for KKT Kolbe integration."""
import asyncio
import logging
import tinytuya
from typing import Any, Dict, Optional

from .const import (
    DP_POWER,
    DP_LIGHT,
    DP_FILTER_ALERT,
    DP_FAN_SPEED,
    DP_COUNTDOWN,
    DP_RGB_LIGHT,
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
        self._connect()

    def _connect(self):
        """Establish connection to the device."""
        try:
            # Auto-detect version if needed
            if self.version == "auto" or self.version is None:
                _LOGGER.info(f"Auto-detecting Tuya protocol version for {self.ip_address}")
                # Try version 3.3 first (most common for KKT), then 3.4, then 3.1
                for test_version in ["3.3", "3.4", "3.1"]:
                    try:
                        test_device = tinytuya.Device(
                            dev_id=self.device_id,
                            address=self.ip_address,
                            local_key=self.local_key,
                            version=test_version
                        )
                        test_device.set_socketTimeout(3)  # Give more time for response
                        test_device.set_socketRetryLimit(2)  # Add retry for stability
                        test_status = test_device.status()

                        # Check for valid status response
                        if test_status and isinstance(test_status, dict):
                            if "dps" in test_status or "devId" in test_status:
                                self.version = test_version
                                _LOGGER.info(f"✅ Detected Tuya protocol version: {test_version}")
                                self._device = test_device
                                break
                    except Exception as e:
                        _LOGGER.debug(f"Version {test_version} failed: {e}")
                        continue

                # If auto-detection failed, try 3.3 as fallback
                if not self._device:
                    _LOGGER.warning(f"Auto-detection failed, using version 3.3 as fallback")
                    self.version = "3.3"
                    self._device = tinytuya.Device(
                        dev_id=self.device_id,
                        address=self.ip_address,
                        local_key=self.local_key,
                        version="3.3"
                    )
            else:
                self._device = tinytuya.Device(
                    dev_id=self.device_id,
                    address=self.ip_address,
                    local_key=self.local_key,
                    version=self.version
                )

            if self._device:
                self._device.set_socketPersistent(True)
                self._device.set_socketRetryLimit(3)  # Add more retries
                self._device.set_socketTimeout(5)  # Longer timeout for stability
                _LOGGER.info(f"✅ Connected to KKT Kolbe device at {self.ip_address} (version {self.version})")
            else:
                _LOGGER.error(f"❌ Failed to connect to device - no compatible version found")
                _LOGGER.error(f"Device ID: {self.device_id}, IP: {self.ip_address}")
                _LOGGER.error(f"Please verify: 1) Device is powered on, 2) IP is correct, 3) Local key is valid")
        except Exception as e:
            _LOGGER.error(f"Failed to connect to device: {e}")
            self._device = None

    async def async_connect(self) -> None:
        """Establish async connection to the device."""
        try:
            # Run the blocking connection in executor
            loop = asyncio.get_event_loop()
            self._device = await loop.run_in_executor(
                None,
                lambda: tinytuya.Device(
                    dev_id=self.device_id,
                    address=self.ip_address,
                    local_key=self.local_key,
                    version=3.4  # Try 3.4 as default for newer devices
                )
            )
            _LOGGER.info(f"Connected to KKT Kolbe device at {self.ip_address}")
        except Exception as e:
            _LOGGER.error(f"Failed to connect to device: {e}")
            self._device = None

    async def async_update_status(self) -> Dict[str, Any]:
        """Get current status from device (async version)."""
        if not self._device:
            await self.async_connect()
            if not self._device:
                _LOGGER.error("Device connection failed")
                return {}

        try:
            # Run the blocking tinytuya call in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            status = await loop.run_in_executor(None, self._device.status)

            if "dps" in status:
                self._status = status["dps"]
                _LOGGER.debug(f"Device status updated: {self._status}")
            return self._status
        except Exception as e:
            _LOGGER.error(f"Failed to get device status: {e}")
            return {}

    def update_status(self) -> Dict[str, Any]:
        """Get current status from device (legacy sync version)."""
        _LOGGER.warning("Using deprecated sync update_status, use async_update_status instead")

        if not self._device:
            self._connect()
            if not self._device:
                _LOGGER.error("Device connection failed")
                return {}

        try:
            status = self._device.status()
            if "dps" in status:
                self._status = status["dps"]
                _LOGGER.debug(f"Device status updated: {self._status}")
            return self._status
        except Exception as e:
            _LOGGER.error(f"Failed to get device status: {e}")
            return {}

    async def async_set_dp(self, dp_code: str, value: Any) -> bool:
        """Set a data point value (async version)."""
        if not self._device:
            await self.async_connect()

        try:
            # Run the blocking tinytuya call in executor
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._device.set_value, dp_code, value)

            _LOGGER.debug(f"Set DP {dp_code} to {value}: {result}")
            return result and result.get("dps") is not None
        except Exception as e:
            _LOGGER.error(f"Failed to set DP {dp_code} to {value}: {e}")
            return False

    def set_dp(self, dp_code: str, value: Any) -> bool:
        """Set a data point value."""
        if not self._device:
            self._connect()

        try:
            # Find DP index from code
            dp_map = {
                DP_POWER: 1,
                DP_LIGHT: 4,
                DP_FILTER_ALERT: 6,
                DP_FAN_SPEED: 10,
                DP_COUNTDOWN: 13,
                DP_RGB_LIGHT: 101,
            }

            if dp_code in dp_map:
                dp_index = dp_map[dp_code]
                self._device.set_value(dp_index, value)
                _LOGGER.debug(f"Set DP {dp_index} ({dp_code}) to {value}")
                return True
            else:
                _LOGGER.error(f"Unknown DP code: {dp_code}")
                return False
        except Exception as e:
            _LOGGER.error(f"Failed to set DP {dp_code}: {e}")
            return False

    def get_dp(self, dp_code: str) -> Optional[Any]:
        """Get a data point value."""
        dp_map = {
            DP_POWER: 1,
            DP_LIGHT: 4,
            DP_FILTER_ALERT: 6,
            DP_FAN_SPEED: 10,
            DP_COUNTDOWN: 13,
            DP_RGB_LIGHT: 101,
        }

        if dp_code in dp_map:
            dp_index = dp_map[dp_code]
            return self._status.get(str(dp_index))
        return None

    @property
    def is_on(self) -> bool:
        """Return if device is powered on."""
        return self.get_dp(DP_POWER) or False

    @property
    def light_on(self) -> bool:
        """Return if light is on."""
        return self.get_dp(DP_LIGHT) or False

    @property
    def fan_speed(self) -> str:
        """Return current fan speed."""
        return self.get_dp(DP_FAN_SPEED) or "off"

    @property
    def countdown_minutes(self) -> int:
        """Return countdown timer in minutes."""
        return self.get_dp(DP_COUNTDOWN) or 0

    @property
    def filter_alert(self) -> bool:
        """Return if filter needs cleaning."""
        return self.get_dp(DP_FILTER_ALERT) or False

    @property
    def rgb_mode(self) -> int:
        """Return current RGB light mode."""
        return self.get_dp(DP_RGB_LIGHT) or 0

    def turn_on(self) -> bool:
        """Turn on the device."""
        return self.set_dp(DP_POWER, True)

    def turn_off(self) -> bool:
        """Turn off the device."""
        return self.set_dp(DP_POWER, False)

    def set_light(self, on: bool) -> bool:
        """Turn light on or off."""
        return self.set_dp(DP_LIGHT, on)

    def set_fan_speed(self, speed: str) -> bool:
        """Set fan speed."""
        if speed in ["off", "low", "middle", "high", "strong"]:
            return self.set_dp(DP_FAN_SPEED, speed)
        return False

    def set_countdown(self, minutes: int) -> bool:
        """Set countdown timer (0-60 minutes)."""
        if 0 <= minutes <= 60:
            return self.set_dp(DP_COUNTDOWN, minutes)
        return False

    def set_rgb_mode(self, mode: int) -> bool:
        """Set RGB light mode (0-9)."""
        if 0 <= mode <= 9:
            return self.set_dp(DP_RGB_LIGHT, mode)
        return False

    def reset_filter_alert(self) -> bool:
        """Reset filter cleaning alert."""
        return self.set_dp(DP_FILTER_ALERT, False)