"""One place that knows where a device entry stores its local key.

Setup reads ``CONF_ACCESS_TOKEN`` first and falls back to ``local_key``
(older entries only have the latter). A writer that updates only one of the
two leaves the other with the old key, and the next reload uses it again, so
every writer goes through ``entry_data_with_local_key``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.const import CONF_ACCESS_TOKEN

CONF_LOCAL_KEY = "local_key"


def entry_local_key(data: Mapping[str, Any]) -> str | None:
    """Return the local key stored in a device entry's data."""
    key = data.get(CONF_ACCESS_TOKEN) or data.get(CONF_LOCAL_KEY)
    return str(key) if key else None


def entry_data_with_local_key(data: Mapping[str, Any], local_key: str) -> dict[str, Any]:
    """Return a copy of a device entry's data with the new local key in both fields."""
    return {**data, CONF_LOCAL_KEY: local_key, CONF_ACCESS_TOKEN: local_key}
