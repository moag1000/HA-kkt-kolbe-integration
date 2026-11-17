"""Entity names, device registry fields and zone bitfield decoding.

Every entity has has_entity_name=True. If its translation_key has no entry in
the translations, Home Assistant falls back to the bare device name, so all
hood entities would show up as "HERMES & STYLE Hood". These tests make sure
each entity the integration can create has a translated name.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from homeassistant.util import slugify

from custom_components.kkt_kolbe.bitfield_utils import get_zone_value_from_coordinator
from custom_components.kkt_kolbe.device_types import KNOWN_DEVICES
from custom_components.kkt_kolbe.scene import _get_scene_definitions

COMPONENT = Path(__file__).parent.parent / "custom_components" / "kkt_kolbe"
TRANSLATION_FILES = ["strings.json", "translations/en.json", "translations/de.json"]


def _entity_translations(file: str) -> dict:
    return json.loads((COMPONENT / file).read_text(encoding="utf-8"))["entity"]


def _expected_keys() -> set[tuple[str, str, str]]:
    """(platform, translation_key, device) for every configured entity."""
    keys: set[tuple[str, str, str]] = set()
    for device_key, device in KNOWN_DEVICES.items():
        for platform, configs in device.get("entities", {}).items():
            if platform == "fan":
                keys.add(("fan", "hood_fan", device_key))
                continue
            if isinstance(configs, dict):
                configs = [configs]
            for cfg in configs:
                key = cfg.get("translation_key") or slugify(cfg["name"])
                keys.add((platform, key, device_key))
        for scene in _get_scene_definitions(device_key):
            keys.add(("scene", slugify(scene["name"]), device_key))
    return keys


@pytest.mark.parametrize("file", TRANSLATION_FILES)
def test_every_entity_has_a_translated_name(file: str) -> None:
    """No entity may fall back to the bare device name."""
    translations = _entity_translations(file)
    missing = sorted(
        f"{platform}.{key} ({device})"
        for platform, key, device in _expected_keys()
        if key not in translations.get(platform, {})
    )
    assert not missing, f"{file} lacks entity names for: {missing}"


def test_hermes_scenes_exist() -> None:
    """The HERMES hood gets the common scenes plus RGB scenes."""
    names = {slugify(s["name"]) for s in _get_scene_definitions("hermes_style_hood")}
    assert {"licht_an", "licht_aus", "haube_aus", "rgb_rot"} <= names


def test_fan_uses_hood_fan_translation() -> None:
    """The hood fan carries the hood_fan translation key."""
    from custom_components.kkt_kolbe.fan import KKTKolbeFan

    entry = MagicMock()
    entry.entry_id = "e1"
    entry.data = {"device_id": "dev1"}
    coordinator = MagicMock()
    coordinator.data = {}
    fan = KKTKolbeFan(coordinator, entry, KNOWN_DEVICES["hermes_style_hood"]["entities"]["fan"])
    assert fan.translation_key == "hood_fan"
    # unique_id must stay what it was before the translation key was added
    assert fan.unique_id == "e1_fan_dp10_fan"


def test_device_info_uses_readable_model() -> None:
    """Model is the product name, the Tuya code goes to model_id, no fake hw_version."""
    from custom_components.kkt_kolbe.base_entity import KKTBaseEntity

    entry = MagicMock()
    entry.entry_id = "e1"
    entry.data = {"device_id": "dev1"}
    entry.runtime_data = SimpleNamespace(device_type="hermes_style_hood", product_name="")
    coordinator = MagicMock()
    coordinator.data = {}
    coordinator.device = None
    entity = KKTBaseEntity(coordinator, entry, {"dp": 1, "name": "Power"}, "switch")

    info = entity._build_device_info()
    assert info["model"] == "HERMES & STYLE Hood"
    assert info["model_id"] == "e1k6i0zo"
    assert "hw_version" not in info


def _coordinator(dps: dict) -> MagicMock:
    coordinator = MagicMock()
    coordinator.data = {"dps": dps}
    return coordinator


def test_zone_value_unknown_until_reported() -> None:
    """A DP the device has not reported yet is unknown, not 0 / off."""
    assert get_zone_value_from_coordinator(_coordinator({"101": True}), 162, 1) is None
    assert get_zone_value_from_coordinator(_coordinator({"101": True}), 163, 1) is None


def test_zone_values_decoded_from_cloud_base64() -> None:
    """Levels are one byte per zone, boost/keep-warm one bit per zone."""
    # levels 9, 0, 14, 0, 25  -> 09 00 0e 00 19
    dps = {"162": "CQAOABk=", "163": "BA==", "164": "Ag=="}
    coord = _coordinator(dps)
    assert [get_zone_value_from_coordinator(coord, 162, z) for z in range(1, 6)] == [9, 0, 14, 0, 25]
    assert [get_zone_value_from_coordinator(coord, 163, z) for z in range(1, 6)] == [
        False,
        False,
        True,
        False,
        False,
    ]
    assert get_zone_value_from_coordinator(coord, 164, 2) is True


def test_zone_values_decoded_from_bytes() -> None:
    """Raw bytes are decoded as bytes, not via str() ("b'...'")."""
    coord = _coordinator({"162": bytes([3, 4, 5, 6, 7])})
    assert get_zone_value_from_coordinator(coord, 162, 4) == 6
