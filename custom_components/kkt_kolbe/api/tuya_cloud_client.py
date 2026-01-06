"""TinyTuya Cloud API Client for KKT Kolbe integration."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
from collections import deque
from typing import Any

import aiohttp
from aiohttp import ClientSession

from .api_exceptions import TuyaAPIError
from .api_exceptions import TuyaAuthenticationError
from .api_exceptions import TuyaDeviceNotFoundError
from .api_exceptions import TuyaRateLimitError

_LOGGER = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_REQUESTS_PER_MINUTE = 15  # Conservative limit for Tuya Free tier
RATE_LIMIT_MIN_INTERVAL = 0.5  # Minimum seconds between requests
RATE_LIMIT_BACKOFF_BASE = 5  # Base seconds for backoff after rate limit hit
RATE_LIMIT_BACKOFF_MAX = 300  # Max backoff (5 minutes)


class TuyaCloudClient:
    """TinyTuya Cloud API Client für Geräteabfragen."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        endpoint: str = "https://openapi.tuyaeu.com",
        session: ClientSession | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.endpoint = endpoint.rstrip("/")
        self.session = session
        self._own_session = session is None
        self._access_token: str | None = None
        self._token_expires_at: float | None = None

        # Rate limiting state
        self._request_times: deque[float] = deque(maxlen=RATE_LIMIT_REQUESTS_PER_MINUTE)
        self._last_request_time: float = 0
        self._rate_limit_backoff: float = 0
        self._rate_limit_until: float = 0
        self._request_lock = asyncio.Lock()

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
        headers: dict[str, str],
        body: str = "",
        nonce: str = ""
    ) -> str:
        """Generate HMAC-SHA256 signature for Tuya API request.

        For Smart Home Industry projects, the signature format is:
        sign = HMAC-SHA256(client_id + t + nonce + stringToSign, secret)

        Where stringToSign = HTTPMethod + "\n" + Content-SHA256 + "\n" + Headers + "\n" + Url
        """
        # Extract path from full URL
        path = url.replace(self.endpoint, "")

        # Build stringToSign according to Tuya spec
        content_sha256 = hashlib.sha256(body.encode('utf-8')).hexdigest()

        # Build headers section - empty string for all requests per Tuya docs
        # (Headers are included in sign calculation separately)
        headers_str = ""

        string_to_sign = f"{method}\n{content_sha256}\n{headers_str}\n{path}"

        # Generate signature: client_id + timestamp + nonce + stringToSign
        # For requests WITH access_token, include it in the payload
        timestamp = headers.get("t", "")
        access_token = headers.get("access_token", "")

        if access_token:
            # Authenticated request: client_id + access_token + timestamp + nonce + stringToSign
            sign_payload = self.client_id + access_token + timestamp + nonce + string_to_sign
        else:
            # Token request: client_id + timestamp + nonce + stringToSign
            sign_payload = self.client_id + timestamp + nonce + string_to_sign

        signature = hmac.new(
            self.client_secret.encode('utf-8'),
            sign_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()

        return signature

    def _build_headers(self, method: str, url: str, body: str = "") -> dict[str, str]:
        """Build headers with authentication and signature.

        For Smart Home Industry projects:
        - Token requests (no access_token): Include nonce in signature
        - API requests (with access_token): No nonce needed
        """
        timestamp = str(int(time.time() * 1000))

        headers = {
            "client_id": self.client_id,
            "t": timestamp,
            "sign_method": "HMAC-SHA256",
        }

        # Only add Content-Type for POST/PUT requests with body
        if method in ["POST", "PUT"] and body:
            headers["Content-Type"] = "application/json"

        # Determine if this is a token request (no access_token yet)
        is_token_request = not self._access_token
        nonce = ""

        if is_token_request:
            # Token requests require nonce for Smart Home Industry projects
            nonce = str(uuid.uuid4())
            headers["nonce"] = nonce
        else:
            # API requests with access_token don't use nonce
            # We know _access_token is not None here because is_token_request is False
            headers["access_token"] = self._access_token or ""

        # Generate and add signature
        signature = self._generate_signature(method, url, headers, body, nonce)
        headers["sign"] = signature

        return headers

    async def _ensure_session(self) -> None:
        """Ensure aiohttp session is available."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
            self._own_session = True

    async def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limits."""
        async with self._request_lock:
            current_time = time.time()

            # Check backoff period
            if current_time < self._rate_limit_until:
                wait_time = self._rate_limit_until - current_time
                _LOGGER.warning(f"Rate limit backoff active, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                current_time = time.time()

            # Enforce minimum interval
            time_since_last = current_time - self._last_request_time
            if time_since_last < RATE_LIMIT_MIN_INTERVAL:
                await asyncio.sleep(RATE_LIMIT_MIN_INTERVAL - time_since_last)
                current_time = time.time()

            # Sliding window check
            window_start = current_time - 60
            while self._request_times and self._request_times[0] < window_start:
                self._request_times.popleft()

            if len(self._request_times) >= RATE_LIMIT_REQUESTS_PER_MINUTE:
                oldest = self._request_times[0]
                wait_time = oldest + 60 - current_time + 0.1
                if wait_time > 0:
                    _LOGGER.debug(f"Rate limit reached, waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                    current_time = time.time()

            self._request_times.append(current_time)
            self._last_request_time = current_time

    def _handle_rate_limit_error(self) -> int:
        """Handle rate limit error with exponential backoff.

        Returns the calculated backoff time in seconds for use with retry_after.
        """
        if self._rate_limit_backoff == 0:
            self._rate_limit_backoff = RATE_LIMIT_BACKOFF_BASE
        else:
            self._rate_limit_backoff = min(self._rate_limit_backoff * 2, RATE_LIMIT_BACKOFF_MAX)
        self._rate_limit_until = time.time() + self._rate_limit_backoff
        _LOGGER.warning(f"Rate limit hit! Backing off for {self._rate_limit_backoff}s")
        return int(self._rate_limit_backoff)

    def _reset_rate_limit_backoff(self) -> None:
        """Reset backoff after successful request."""
        if self._rate_limit_backoff > 0:
            self._rate_limit_backoff = 0
            _LOGGER.debug("Rate limit backoff reset")

    async def _make_request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make authenticated request to Tuya API with rate limiting."""
        await self._ensure_session()
        await self._wait_for_rate_limit()

        url = f"{self.endpoint}{path}"
        body = json.dumps(data) if data else ""
        headers = self._build_headers(method, url, body)

        _LOGGER.debug(f"Making {method} request to {path}")

        assert self.session is not None  # Guaranteed by _ensure_session()
        try:
            async with self.session.request(
                method, url, headers=headers, data=body
            ) as response:
                response_data: dict[str, Any] = await response.json()

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
                        retry_after = self._handle_rate_limit_error()
                        raise TuyaRateLimitError(error_msg, retry_after=retry_after)
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

                # Success - reset rate limit backoff
                self._reset_rate_limit_backoff()
                return response_data

        except aiohttp.ClientError as err:
            raise TuyaAPIError(f"HTTP request failed: {err}") from err

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

    def _normalize_device_response(self, device: dict[str, Any], api_version: str) -> dict[str, Any]:
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
                "icon": device.get("icon"),  # Device icon path from Tuya
            }
        else:
            # v1.0 already uses snake_case, but ensure icon is included
            normalized = dict(device)
            if "icon" not in normalized:
                normalized["icon"] = device.get("icon")

        return normalized

    async def get_device_list(self) -> list[dict[str, Any]]:
        """Get list of all devices from Tuya API.

        Uses v2.0 API endpoint for better compatibility with Free tier accounts.
        Falls back to v1.0 if v2.0 fails.
        Returns normalized device data with consistent field names.
        """
        await self._ensure_authenticated()

        _LOGGER.debug("Fetching device list from Tuya Cloud API")

        # Try v2.0 API first (Free tier compatible)
        # Note: Free tier has lower page_size limit, use conservative value
        try:
            response = await self._make_request("GET", "/v2.0/cloud/thing/device?page_size=20")
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
                v1_devices: list[dict[str, Any]] = response.get("result", [])
                _LOGGER.info(f"Retrieved {len(v1_devices)} devices from API v1.0")
                return v1_devices  # v1.0 already in correct format
            except TuyaAPIError:
                _LOGGER.error("Both v2.0 and v1.0 device list APIs failed")
                raise

    async def get_device_details(self, device_id: str) -> dict[str, Any]:
        """Get full device details including product_id and local_key.

        Tries /v1.0/devices/{device_id} first (most complete data).
        Falls back to /v2.0/cloud/thing/{device_id} if v1.0 fails.

        Returns:
            Device dict with: id, name, local_key, product_id, product_name,
            category, online, ip, model, uuid, time_zone, etc.
        """
        await self._ensure_authenticated()

        _LOGGER.debug(f"Fetching device details for {device_id}")

        # Try v1.0 API first (returns local_key, product_id, etc.)
        try:
            response = await self._make_request("GET", f"/v1.0/devices/{device_id}")
            device: dict[str, Any] = response.get("result", {})

            if device:
                has_local_key = bool(device.get('local_key'))
                _LOGGER.info(f"Retrieved device details (v1.0): product_id={device.get('product_id', 'N/A')}, "
                            f"local_key={'present' if has_local_key else 'MISSING'}")
                return device

        except TuyaAPIError as e:
            _LOGGER.debug(f"v1.0 device details failed, trying v2.0: {e}")

        # Fallback to v2.0 API
        try:
            response = await self._make_request("GET", f"/v2.0/cloud/thing/{device_id}")
            result = response.get("result", {})

            # v2.0 uses camelCase, normalize to snake_case
            if result:
                device = {
                    "id": result.get("id"),
                    "name": result.get("name"),
                    "local_key": result.get("localKey"),
                    "product_id": result.get("productId"),
                    "product_name": result.get("productName"),
                    "category": result.get("category"),
                    "online": result.get("isOnline", False),
                    "ip": result.get("ip"),
                    "model": result.get("model"),
                    "uuid": result.get("uuid"),
                    "time_zone": result.get("timeZone"),
                }
                has_local_key = bool(device.get('local_key'))
                _LOGGER.info(f"Retrieved device details (v2.0): product_id={device.get('product_id', 'N/A')}, "
                            f"local_key={'present' if has_local_key else 'MISSING'}")
                return device

        except TuyaAPIError as e:
            _LOGGER.warning(f"Both v1.0 and v2.0 device details failed for {device_id}: {e}")

        return {}

    async def get_device_list_with_details(self) -> list[dict[str, Any]]:
        """Get device list with full details for each device.

        First gets basic device list, then enriches each device with
        full details from /v1.0/devices/{id} to get product_id, local_key, etc.

        Returns:
            List of fully populated device dicts.
        """
        # Get basic device list
        devices = await self.get_device_list()

        # Enrich each device with full details
        enriched_devices = []
        for device in devices:
            device_id = device.get("id")
            if device_id:
                try:
                    details = await self.get_device_details(device_id)
                    if details:
                        # Merge: details take priority, keep any fields from list that aren't in details
                        merged = {**device, **details}
                        enriched_devices.append(merged)
                        _LOGGER.debug(f"Enriched device {device_id[:8]}: product_id={details.get('product_id', 'N/A')}")
                    else:
                        enriched_devices.append(device)
                except Exception as e:
                    _LOGGER.debug(f"Could not enrich device {device_id[:8]}: {e}")
                    enriched_devices.append(device)
            else:
                enriched_devices.append(device)

        _LOGGER.info(f"Retrieved {len(enriched_devices)} devices with full details")
        return enriched_devices

    async def get_device_properties(self, device_id: str) -> dict[str, Any]:
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
                raise TuyaAPIError("Failed to parse Things Data Model") from parse_err

        except TuyaAPIError as v2_error:
            _LOGGER.debug(f"v2.0 Things Data Model failed, trying v1.0 fallback: {v2_error}")

            # Fallback to v1.0 iot-03 device functions
            try:
                response = await self._make_request(
                    "GET",
                    f"/v1.0/iot-03/devices/{device_id}/functions"
                )

                iot03_result: dict[str, Any] = response.get("result", {})
                _LOGGER.debug("Retrieved properties from v1.0 iot-03 API")
                return iot03_result

            except TuyaAPIError as iot03_error:
                _LOGGER.debug(f"v1.0 iot-03 failed, trying legacy v1.0: {iot03_error}")

                # Final fallback to legacy v1.0 API
                try:
                    response = await self._make_request(
                        "GET",
                        f"/v1.0/devices/{device_id}/functions"
                    )

                    legacy_result: dict[str, Any] = response.get("result", {})
                    return legacy_result

                except TuyaAPIError as err:
                    if "device not found" in str(err).lower():
                        raise TuyaDeviceNotFoundError(device_id) from err
                    raise

    async def get_device_status(self, device_id: str) -> dict[str, Any] | list[dict[str, Any]]:
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
            result: dict[str, Any] = response.get("result", {})
            properties: list[dict[str, Any]] = result.get("properties", [])

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

                status: list[dict[str, Any]] = response.get("result", [])
                _LOGGER.debug(f"Retrieved {len(status)} status values from v1.0 API")
                return status

            except TuyaAPIError as err:
                if "device not found" in str(err).lower():
                    raise TuyaDeviceNotFoundError(device_id) from err
                raise

    async def send_commands(self, device_id: str, commands: list[dict[str, Any]]) -> bool:
        """Send commands to a device via Tuya Cloud API.

        Args:
            device_id: The device ID
            commands: List of commands, each with 'code' and 'value' keys
                     Example: [{"code": "switch_1", "value": True}]

        Returns:
            True if command was sent successfully, False otherwise
        """
        await self._ensure_authenticated()

        _LOGGER.debug(f"Sending commands to device {device_id}: {commands}")

        try:
            response = await self._make_request(
                "POST",
                f"/v1.0/devices/{device_id}/commands",
                data={"commands": commands}
            )

            success: bool = response.get("success", False)
            if success:
                _LOGGER.info(f"Commands sent successfully to device {device_id}")
            else:
                _LOGGER.warning(f"Command response indicates failure: {response}")

            return success

        except TuyaAPIError as err:
            _LOGGER.error(f"Failed to send commands to device {device_id}: {err}")
            return False

    async def send_dp_commands(self, device_id: str, dps: dict[str, Any]) -> bool:
        """Send DP (Data Point) commands to a device via Tuya Cloud API.

        Uses the iot-03 API which accepts DPs directly.

        Args:
            device_id: The device ID
            dps: Dictionary of DP ID to value, e.g., {"1": True, "2": 50}

        Returns:
            True if command was sent successfully, False otherwise
        """
        await self._ensure_authenticated()

        _LOGGER.debug(f"Sending DP commands to device {device_id}: {dps}")

        # Convert DP dict to commands format
        # The iot-03 API uses "commands" with "code" being the DP ID as string
        commands = [{"code": str(dp_id), "value": value} for dp_id, value in dps.items()]

        try:
            # Try iot-03 API first (supports DPs directly)
            response = await self._make_request(
                "POST",
                f"/v1.0/iot-03/devices/{device_id}/commands",
                data={"commands": commands}
            )

            success: bool = response.get("success", False)
            if success:
                _LOGGER.info(f"DP commands sent successfully to device {device_id}")
                return True

        except TuyaAPIError as err:
            _LOGGER.debug(f"iot-03 commands failed, trying standard API: {err}")

        # Fallback to standard commands API
        try:
            response = await self._make_request(
                "POST",
                f"/v1.0/devices/{device_id}/commands",
                data={"commands": commands}
            )

            std_success: bool = response.get("success", False)
            if std_success:
                _LOGGER.info(f"DP commands sent via standard API to device {device_id}")
            return std_success

        except TuyaAPIError as err:
            _LOGGER.error(f"Failed to send DP commands to device {device_id}: {err}")
            return False

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
