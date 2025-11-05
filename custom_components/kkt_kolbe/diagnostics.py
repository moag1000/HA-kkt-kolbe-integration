"""Diagnostics support for KKT Kolbe integration."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]

    # Get coordinator data
    coordinator = data.get("coordinator")
    device = data.get("device")
    api_client = data.get("api_client")

    # Build diagnostics data
    diagnostics_data = {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "unique_id": entry.unique_id,
            "domain": entry.domain,
        },
        "config": {
            "integration_mode": data.get("integration_mode", "unknown"),
            "product_name": data.get("product_name", "unknown"),
            "api_enabled": entry.data.get("api_enabled", False),
            # Redact sensitive information
            "device_id": (entry.data.get("device_id", "")[:8] + "...") if entry.data.get("device_id") else "not_set",
            "has_ip_address": bool(entry.data.get("ip_address")),
            "has_local_key": bool(entry.data.get("local_key")),
            "has_api_credentials": bool(entry.data.get("api_client_id")),
        },
        "coordinator": {},
        "device": {},
        "api": {},
    }

    # Add coordinator diagnostics
    if coordinator:
        diagnostics_data["coordinator"] = {
            "last_update_success": coordinator.last_update_success,
            "last_update_success_time": coordinator.last_update_success_time.isoformat()
            if coordinator.last_update_success_time
            else None,
            "update_interval": str(coordinator.update_interval),
            "data_available": bool(coordinator.data),
            "data_point_count": len(coordinator.data) if coordinator.data else 0,
        }

        # Add available data points (values redacted for privacy)
        if coordinator.data:
            diagnostics_data["coordinator"]["available_data_points"] = list(
                coordinator.data.keys()
            )

    # Add device diagnostics
    if device:
        diagnostics_data["device"] = {
            "connected": device.is_connected if hasattr(device, "is_connected") else False,
            "protocol_version": device.version if hasattr(device, "version") else "unknown",
            "device_id_prefix": device.device_id[:8] + "..." if hasattr(device, "device_id") else "unknown",
            "ip_address": device.ip_address if hasattr(device, "ip_address") else "unknown",
        }

    # Add API client diagnostics
    if api_client:
        diagnostics_data["api"] = {
            "enabled": True,
            "endpoint": entry.data.get("api_endpoint", "unknown"),
            "has_client_id": bool(entry.data.get("api_client_id")),
            "has_client_secret": bool(entry.data.get("api_client_secret")),
        }
    else:
        diagnostics_data["api"] = {
            "enabled": False,
        }

    # Add device info from registry
    diagnostics_data["device_info"] = data.get("device_info", {})

    return diagnostics_data
