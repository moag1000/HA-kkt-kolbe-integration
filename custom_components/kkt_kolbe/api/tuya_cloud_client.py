"""TinyTuya Cloud API Client for KKT Kolbe integration."""
import asyncio
import hashlib
import hmac
import json
import time
from typing import Dict, List, Optional
import logging

import aiohttp

from .api_exceptions import (
    TuyaAPIError,
    TuyaAuthenticationError,
    TuyaRateLimitError,
    TuyaDeviceNotFoundError,
)

_LOGGER = logging.getLogger(__name__)


class TuyaCloudClient:
    """TinyTuya Cloud API Client für Geräteabfragen."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        endpoint: str = "https://openapi.tuyaeu.com",
        session: Optional[aiohttp.ClientSession] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.endpoint = endpoint.rstrip("/")
        self.session = session
        self._own_session = session is None
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None

    async def __aenter__(self):
        """Async context manager entry."""
        if self._own_session:
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._own_session and self.session:
            await self.session.close()

    def _generate_signature(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: str = ""
    ) -> str:
        """Generate HMAC-SHA256 signature for Tuya API request."""
        # Extract path from full URL
        path = url.replace(self.endpoint, "")

        # Create string to sign
        string_to_sign = method + "\n"
        string_to_sign += hashlib.sha256(body.encode()).hexdigest() + "\n"

        # Add headers in specific order
        for key in sorted(headers.keys()):
            if key.startswith("Sign"):
                continue
            string_to_sign += f"{key}:{headers[key]}\n"

        string_to_sign += path

        # Generate signature
        signature = hmac.new(
            self.client_secret.encode(),
            string_to_sign.encode(),
            hashlib.sha256
        ).hexdigest().upper()

        return signature

    def _build_headers(self, method: str, url: str, body: str = "") -> Dict[str, str]:
        """Build headers with authentication and signature."""
        timestamp = str(int(time.time() * 1000))

        headers = {
            "client_id": self.client_id,
            "t": timestamp,
            "sign_method": "HMAC-SHA256",
            "Content-Type": "application/json",
        }

        # Add access token if available
        if self._access_token:
            headers["access_token"] = self._access_token

        # Generate and add signature
        signature = self._generate_signature(method, url, headers, body)
        headers["sign"] = signature

        return headers

    async def _make_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None
    ) -> Dict:
        """Make authenticated request to Tuya API."""
        if not self.session:
            raise TuyaAPIError("Session not initialized. Use async context manager.")

        url = f"{self.endpoint}{path}"
        body = json.dumps(data) if data else ""
        headers = self._build_headers(method, url, body)

        _LOGGER.debug(f"Making {method} request to {path}")

        try:
            async with self.session.request(
                method, url, headers=headers, data=body
            ) as response:
                response_data = await response.json()

                # Check for API errors
                if not response_data.get("success", False):
                    error_code = response_data.get("code")
                    error_msg = response_data.get("msg", "Unknown API error")

                    # Enhanced error logging for debugging
                    _LOGGER.error(
                        f"Tuya API Error - Code: {error_code}, Message: {error_msg}, "
                        f"Endpoint: {self.endpoint}, Path: {path}"
                    )

                    # Common error codes
                    if error_code == 1010:
                        raise TuyaAuthenticationError(
                            f"{error_msg} (Check client_id and client_secret)",
                            error_code
                        )
                    elif error_code == 1011:
                        raise TuyaRateLimitError(error_msg)
                    elif error_code == 1004:
                        raise TuyaAuthenticationError(
                            f"Sign validation failed. Possible causes:\n"
                            f"1. Client Secret is incorrect\n"
                            f"2. System time is not synchronized\n"
                            f"3. Endpoint {self.endpoint} is wrong for your region",
                            error_code
                        )
                    else:
                        raise TuyaAPIError(f"{error_msg} (Code: {error_code})", error_code)

                return response_data

        except aiohttp.ClientError as err:
            raise TuyaAPIError(f"HTTP request failed: {err}")

    async def authenticate(self) -> str:
        """Authenticate and get access token."""
        _LOGGER.debug("Authenticating with Tuya Cloud API")

        response = await self._make_request("GET", "/v1.0/token?grant_type=1")

        result = response.get("result", {})
        self._access_token = result.get("access_token")
        expires_in = result.get("expire_time", 7200)  # Default 2 hours
        self._token_expires_at = time.time() + expires_in

        if not self._access_token:
            raise TuyaAuthenticationError("No access token in response")

        _LOGGER.info("Successfully authenticated with Tuya Cloud API")
        return self._access_token

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token."""
        if (
            not self._access_token
            or not self._token_expires_at
            or time.time() >= self._token_expires_at - 300  # Refresh 5 min early
        ):
            await self.authenticate()

    def _normalize_device_response(self, device: Dict, api_version: str) -> Dict:
        """Normalize device response to consistent format.

        v2.0 API uses camelCase, v1.0 uses snake_case.
        This ensures consistent field names across API versions.
        """
        if api_version == "v2.0":
            # Convert v2.0 camelCase to v1.0 snake_case format
            normalized = {
                "id": device.get("id"),
                "name": device.get("name"),
                "local_key": device.get("localKey"),  # camelCase → snake_case
                "product_id": device.get("productId"),  # camelCase → snake_case
                "product_name": device.get("productName"),  # camelCase → snake_case
                "category": device.get("category"),
                "online": device.get("isOnline", False),  # isOnline → online
                "ip": device.get("ip"),
                "lat": device.get("lat"),
                "lon": device.get("lon"),
                "model": device.get("model"),
                "uuid": device.get("uuid"),
                "time_zone": device.get("timeZone"),  # camelCase → snake_case
            }
        else:
            # v1.0 already uses snake_case
            normalized = device

        return normalized

    async def get_device_list(self) -> List[Dict]:
        """Get list of all devices from Tuya API.

        Uses v2.0 API endpoint for better compatibility with Free tier accounts.
        Falls back to v1.0 if v2.0 fails.
        Returns normalized device data with consistent field names.
        """
        await self._ensure_authenticated()

        _LOGGER.debug("Fetching device list from Tuya Cloud API")

        # Try v2.0 API first (Free tier compatible)
        try:
            response = await self._make_request("GET", "/v2.0/cloud/thing/device?page_size=100")
            devices = response.get("result", [])

            # Normalize v2.0 response to v1.0 format (camelCase → snake_case)
            normalized_devices = [
                self._normalize_device_response(device, "v2.0")
                for device in devices
            ]

            _LOGGER.info(f"Retrieved {len(normalized_devices)} devices from API v2.0")
            return normalized_devices

        except TuyaAPIError as e:
            _LOGGER.debug(f"v2.0 API failed, trying v1.0 fallback: {e}")

            # Fallback to v1.0 API (older accounts)
            try:
                response = await self._make_request("GET", "/v1.0/devices")
                devices = response.get("result", [])
                _LOGGER.info(f"Retrieved {len(devices)} devices from API v1.0")
                return devices  # v1.0 already in correct format
            except TuyaAPIError as fallback_error:
                _LOGGER.error(f"Both v2.0 and v1.0 device list APIs failed")
                raise

    async def get_device_properties(self, device_id: str) -> Dict:
        """Get device properties using Things Data Model.

        Uses v2.0 Things Data Model API for Free tier compatibility.
        Falls back to v1.0 if v2.0 fails.

        Returns device functions/properties with metadata (type, range, min/max).
        """
        await self._ensure_authenticated()

        _LOGGER.debug(f"Fetching properties for device {device_id}")

        # Try v2.0 Things Data Model API first (Free tier compatible)
        try:
            response = await self._make_request(
                "GET",
                f"/v2.0/cloud/thing/{device_id}/model"
            )

            result = response.get("result", {})
            model_str = result.get("model", "{}")

            # Parse JSON string in model field
            try:
                model_data = json.loads(model_str)

                # Extract properties from services
                properties = []
                services = model_data.get("services", [])
                for service in services:
                    service_props = service.get("properties", [])
                    properties.extend(service_props)

                _LOGGER.debug(f"Retrieved {len(properties)} properties from v2.0 Things Data Model")

                # Convert to v1.0 functions format for compatibility
                functions = {
                    "category": result.get("category", ""),
                    "functions": [
                        {
                            "code": prop.get("code"),
                            "type": prop.get("typeSpec", {}).get("type"),
                            "values": json.dumps(prop.get("typeSpec", {})),
                            "dp_id": prop.get("abilityId"),
                        }
                        for prop in properties
                    ]
                }

                return functions

            except (json.JSONDecodeError, KeyError) as parse_err:
                _LOGGER.warning(f"Failed to parse v2.0 model data: {parse_err}")
                raise TuyaAPIError("Failed to parse Things Data Model")

        except TuyaAPIError as v2_error:
            _LOGGER.debug(f"v2.0 Things Data Model failed, trying v1.0 fallback: {v2_error}")

            # Fallback to v1.0 iot-03 device functions
            try:
                response = await self._make_request(
                    "GET",
                    f"/v1.0/iot-03/devices/{device_id}/functions"
                )

                result = response.get("result", {})
                _LOGGER.debug(f"Retrieved properties from v1.0 iot-03 API")
                return result

            except TuyaAPIError as iot03_error:
                _LOGGER.debug(f"v1.0 iot-03 failed, trying legacy v1.0: {iot03_error}")

                # Final fallback to legacy v1.0 API
                try:
                    response = await self._make_request(
                        "GET",
                        f"/v1.0/devices/{device_id}/functions"
                    )

                    return response.get("result", {})

                except TuyaAPIError as err:
                    if "device not found" in str(err).lower():
                        raise TuyaDeviceNotFoundError(device_id)
                    raise

    async def get_device_status(self, device_id: str) -> Dict:
        """Get current device status.

        Uses v2.0 Shadow Properties API for Free tier compatibility.
        Falls back to v1.0 if v2.0 fails.
        """
        await self._ensure_authenticated()

        _LOGGER.debug(f"Fetching status for device {device_id}")

        # Try v2.0 Shadow Properties API first (Free tier compatible)
        try:
            response = await self._make_request(
                "GET",
                f"/v2.0/cloud/thing/{device_id}/shadow/properties"
            )

            # v2.0 nests properties: result.properties[]
            result = response.get("result", {})
            properties = result.get("properties", [])

            _LOGGER.debug(f"Retrieved {len(properties)} properties from v2.0 API")
            return properties

        except TuyaAPIError as v2_error:
            _LOGGER.debug(f"v2.0 shadow properties failed, trying v1.0 fallback: {v2_error}")

            # Fallback to v1.0 Device Status API
            try:
                response = await self._make_request(
                    "GET",
                    f"/v1.0/devices/{device_id}/status"
                )

                status = response.get("result", [])
                _LOGGER.debug(f"Retrieved {len(status)} status values from v1.0 API")
                return status

            except TuyaAPIError as err:
                if "device not found" in str(err).lower():
                    raise TuyaDeviceNotFoundError(device_id)
                raise

    async def test_connection(self) -> bool:
        """Test API connection and authentication."""
        try:
            # Ensure session is initialized
            if not self.session:
                async with self:
                    await self.authenticate()
                    devices = await self.get_device_list()
                    _LOGGER.info(f"Connection test successful. Found {len(devices)} devices.")
                    return True
            else:
                await self.authenticate()
                devices = await self.get_device_list()
                _LOGGER.info(f"Connection test successful. Found {len(devices)} devices.")
                return True

        except TuyaAuthenticationError as err:
            _LOGGER.error(
                f"Connection test failed - Authentication Error: {err}\n"
                f"Endpoint: {self.endpoint}\n"
                f"Client ID: {self.client_id[:8]}...\n"
                f"Please verify your credentials in Tuya IoT Platform"
            )
            return False
        except Exception as err:
            _LOGGER.error(
                f"Connection test failed: {err}\n"
                f"Endpoint: {self.endpoint}"
            )
            return False