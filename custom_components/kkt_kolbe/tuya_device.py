"""KKT Kolbe Tuya Device Handler."""
import asyncio
import logging
from typing import Any, Dict

import tinytuya

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
        # Connection will be established async when needed

    async def async_connect(self) -> None:
        """Establish async connection to the device."""
        if self._connected:
            return

        try:
            loop = asyncio.get_event_loop()

            # Auto-detect version if needed
            if self.version == "auto" or self.version is None:
                _LOGGER.info(f"Auto-detecting Tuya protocol version for {self.ip_address}")

                # Try versions in order (3.3 is most common for KKT)
                for test_version in ["3.3", "3.4", "3.1"]:
                    try:
                        # Create device in executor to avoid blocking
                        test_device = await loop.run_in_executor(
                            None,
                            self._create_device,
                            test_version
                        )

                        # Test connection in executor
                        test_status = await loop.run_in_executor(
                            None,
                            test_device.status
                        )

                        # Check for valid response
                        if test_status and isinstance(test_status, dict):
                            if "dps" in test_status or "devId" in test_status:
                                self.version = test_version
                                self._device = test_device
                                self._device.set_socketPersistent(True)
                                self._connected = True
                                _LOGGER.info(f"✅ Detected Tuya protocol version: {test_version}")
                                return
                            elif "Err" in str(test_status):
                                if "907" in str(test_status):  # Auth error
                                    _LOGGER.error(f"❌ Authentication failed - invalid local key")
                                    _LOGGER.error(f"Please verify your local key is correct for device {self.device_id}")
                                    raise Exception("Invalid local key - device rejected authentication")
                    except Exception as e:
                        if "Invalid local key" in str(e) or "authentication" in str(e).lower():
                            raise
                        _LOGGER.debug(f"Version {test_version} failed: {e}")
                        continue

                # If auto-detection failed, try 3.3 as fallback
                if not self._device:
                    _LOGGER.warning(f"Auto-detection failed, using version 3.3 as fallback")
                    self.version = "3.3"
                    self._device = await loop.run_in_executor(
                        None,
                        self._create_device,
                        "3.3"
                    )
                    self._device.set_socketPersistent(True)
                    self._connected = True
            else:
                # Use specified version
                self._device = await loop.run_in_executor(
                    None,
                    self._create_device,
                    self.version
                )
                self._device.set_socketPersistent(True)
                self._connected = True

            _LOGGER.info(f"✅ Connected to KKT Kolbe device at {self.ip_address} (version {self.version})")

        except Exception as e:
            self._connected = False
            _LOGGER.error(f"Failed to connect to device: {e}")
            if "Invalid local key" not in str(e) and "authentication" not in str(e).lower():
                _LOGGER.error(f"Device ID: {self.device_id}, IP: {self.ip_address}")
                _LOGGER.error(f"Please verify: 1) Device is on, 2) IP is correct, 3) Local key is valid")
            self._device = None
            raise

    def _create_device(self, version):
        """Create a device instance with the given version."""
        device = tinytuya.Device(
            dev_id=self.device_id,
            address=self.ip_address,
            local_key=self.local_key,
            version=version
        )
        device.set_socketTimeout(5)
        device.set_socketRetryLimit(3)
        return device

    async def async_ensure_connected(self):
        """Ensure device is connected (async)."""
        if not self._connected:
            await self.async_connect()

    @property
    def is_connected(self) -> bool:
        """Return True if device is connected."""
        return self._connected and self._device is not None

    @property
    def is_on(self) -> bool:
        """Return True if device is on (DP 1)."""
        return self.get_dp_value(1, False)

    def get_dp_value(self, dp: int, default=None):
        """Get data point value from cached status."""
        return self._status.get("dps", {}).get(str(dp), default)

    async def async_get_status(self) -> dict:
        """Get device status asynchronously."""
        await self.async_ensure_connected()

        if not self._device:
            return {}

        try:
            loop = asyncio.get_event_loop()
            status = await loop.run_in_executor(
                None,
                self._device.status
            )
            if status and isinstance(status, dict):
                self._status = status
                return status
        except Exception as e:
            _LOGGER.error(f"Failed to get device status: {e}")
            self._connected = False  # Mark as disconnected on error

        return {}

    async def async_update_status(self) -> None:
        """Update device status asynchronously."""
        await self.async_ensure_connected()

        if not self._device:
            return

        try:
            loop = asyncio.get_event_loop()
            status = await loop.run_in_executor(
                None,
                self._device.status
            )
            if status and isinstance(status, dict):
                self._status = status
        except Exception as e:
            _LOGGER.error(f"Failed to update device status: {e}")
            self._connected = False  # Mark as disconnected on error

    async def async_set_dp(self, dp: int, value: Any) -> bool:
        """Set data point value asynchronously."""
        await self.async_ensure_connected()

        if not self._device:
            return False

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._device.set_value,
                dp,
                value
            )
            _LOGGER.debug(f"Set DP {dp} to {value}: {result}")
            return True
        except Exception as e:
            _LOGGER.error(f"Failed to set DP {dp} to {value}: {e}")
            return False

    def turn_on(self):
        """Turn device on (DP 1 = True)."""
        asyncio.create_task(self.async_set_dp(1, True))

    def turn_off(self):
        """Turn device off (DP 1 = False)."""
        asyncio.create_task(self.async_set_dp(1, False))

    def set_fan_speed(self, speed: str):
        """Set fan speed (DP 10)."""
        speed_map = {
            "off": "0",
            "low": "1",
            "middle": "2",
            "high": "3",
            "strong": "4"
        }
        if speed in speed_map:
            asyncio.create_task(self.async_set_dp(10, speed_map[speed]))

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
        asyncio.create_task(self.async_set_dp(4, state))

    @property
    def light_on(self) -> bool:
        """Return True if light is on."""
        return self.get_dp_value(4, False)

    def set_rgb_mode(self, mode: int):
        """Set RGB mode (DP 101)."""
        if 0 <= mode <= 9:
            asyncio.create_task(self.async_set_dp(101, mode))

    @property
    def rgb_mode(self) -> int:
        """Get current RGB mode."""
        return self.get_dp_value(101, 0)