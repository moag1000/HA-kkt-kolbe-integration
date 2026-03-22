"""Runtime data types for the KKT Kolbe integration.

Based on the data.py pattern from https://github.com/ludeeus/integration_blueprint
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Any

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .api import TuyaCloudClient
    from .coordinator import KKTKolbeUpdateCoordinator
    from .hybrid_coordinator import KKTKolbeHybridCoordinator
    from .tuya_device import KKTKolbeTuyaDevice


@dataclass
class KKTKolbeRuntimeData:
    """Runtime data for KKT Kolbe device entries."""

    coordinator: KKTKolbeUpdateCoordinator | KKTKolbeHybridCoordinator
    device: KKTKolbeTuyaDevice | None
    api_client: TuyaCloudClient | None
    device_info: dict[str, Any]
    product_name: str
    device_type: str
    integration_mode: str


@dataclass
class KKTKolbeAccountRuntimeData:
    """Runtime data for SmartLife account entries (Parent Entry).

    Account entries manage token information and don't have devices directly.
    They serve as parent entries for device entries.
    """

    token_info: dict[str, Any]
    user_code: str
    app_schema: str  # "smartlife" or "tuyaSmart"
    child_entry_ids: list[str]  # IDs of device entries linked to this account


type KKTKolbeConfigEntry = ConfigEntry[KKTKolbeRuntimeData]
type KKTKolbeAccountConfigEntry = ConfigEntry[KKTKolbeAccountRuntimeData]
