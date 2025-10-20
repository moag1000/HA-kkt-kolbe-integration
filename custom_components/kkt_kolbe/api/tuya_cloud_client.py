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

                    if error_code == 1010:
                        raise TuyaAuthenticationError(error_msg, error_code)
                    elif error_code == 1011:
                        raise TuyaRateLimitError(error_msg)
                    else:
                        raise TuyaAPIError(error_msg, error_code)

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

    async def get_device_list(self) -> List[Dict]:
        """Get list of all devices from Tuya API."""
        await self._ensure_authenticated()

        _LOGGER.debug("Fetching device list from Tuya Cloud API")

        response = await self._make_request("GET", "/v1.0/devices")

        devices = response.get("result", [])
        _LOGGER.info(f"Retrieved {len(devices)} devices from API")

        return devices

    async def get_device_properties(self, device_id: str) -> Dict:
        """Get device properties using 'Query Things Data Model'."""
        await self._ensure_authenticated()

        _LOGGER.debug(f"Fetching properties for device {device_id}")

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
        """Get current device status."""
        await self._ensure_authenticated()

        _LOGGER.debug(f"Fetching status for device {device_id}")

        try:
            response = await self._make_request(
                "GET",
                f"/v1.0/devices/{device_id}/status"
            )

            return response.get("result", [])

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

        except Exception as err:
            _LOGGER.error(f"Connection test failed: {err}")
            return False