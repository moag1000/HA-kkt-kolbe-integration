"""Diagnostics support for KKT Kolbe integration."""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from homeassistant.core import HomeAssistant

if TYPE_CHECKING:
    from . import KKTKolbeConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: KKTKolbeConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime_data = entry.runtime_data

    # Get coordinator data from runtime_data
    coordinator = runtime_data.coordinator
    device = runtime_data.device
    api_client = runtime_data.api_client

    # Build diagnostics data
    diagnostics_data = {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "unique_id": entry.unique_id,
            "domain": entry.domain,
        },
        "config": {
            "integration_mode": runtime_data.integration_mode,
            "product_name": runtime_data.product_name,
            "device_type": runtime_data.device_type,
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

        # Add connection state tracking info if available
        if hasattr(coordinator, "connection_info"):
            conn_info = coordinator.connection_info
            diagnostics_data["coordinator"]["connection_state"] = conn_info.get("state", "unknown")
            diagnostics_data["coordinator"]["consecutive_failures"] = conn_info.get("consecutive_failures", 0)
            diagnostics_data["coordinator"]["last_successful_update"] = (
                conn_info.get("last_update").isoformat()
                if conn_info.get("last_update")
                else None
            )

            # Add circuit breaker info if using ReconnectCoordinator
            if "circuit_breaker_retries" in conn_info:
                diagnostics_data["coordinator"]["circuit_breaker"] = {
                    "retries": conn_info.get("circuit_breaker_retries", 0),
                    "next_retry": (
                        conn_info.get("circuit_breaker_next_retry").isoformat()
                        if conn_info.get("circuit_breaker_next_retry")
                        else None
                    ),
                    "adaptive_interval_active": conn_info.get("adaptive_interval_active", False),
                }

        # Add device state if available
        if hasattr(coordinator, "device_state"):
            diagnostics_data["coordinator"]["device_state"] = coordinator.device_state.value

        # Add device availability if available
        if hasattr(coordinator, "is_device_available"):
            diagnostics_data["coordinator"]["is_device_available"] = coordinator.is_device_available

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

        # Add connection statistics if available
        if hasattr(device, "connection_stats"):
            stats = device.connection_stats
            diagnostics_data["device"]["connection_statistics"] = {
                "total_connects": stats.get("total_connects", 0),
                "total_disconnects": stats.get("total_disconnects", 0),
                "total_reconnects": stats.get("total_reconnects", 0),
                "total_timeouts": stats.get("total_timeouts", 0),
                "total_errors": stats.get("total_errors", 0),
                "last_connect_time": stats.get("last_connect_time"),
                "last_disconnect_time": stats.get("last_disconnect_time"),
                "protocol_version_detected": stats.get("protocol_version_detected"),
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

    # Add device info from runtime_data
    diagnostics_data["device_info"] = runtime_data.device_info

    return diagnostics_data
