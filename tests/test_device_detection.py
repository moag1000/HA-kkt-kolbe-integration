"""Tests for hood model detection (EASY HCM vs. EASY/PLOOM)."""

from __future__ import annotations

import pytest

from custom_components.kkt_kolbe.device_types import KNOWN_DEVICES
from custom_components.kkt_kolbe.device_types import find_device_by_product_name
from custom_components.kkt_kolbe.helpers.device_detection import detect_device_type_from_api


def test_easy_hcm_product_id_uses_hcm_layout() -> None:
    """EASY HCM (xfw4ckzxljs4ncta, make-all/tuya-local#5332) has the HCM DPs, not the HERMES ones."""
    info = find_device_by_product_name("xfw4ckzxljs4ncta")
    assert info is KNOWN_DEVICES["easy_hcm_hood"]
    assert info["model_id"] == "edfc1c"
    assert info["data_points"] == KNOWN_DEVICES["ecco_hcm_hood"]["data_points"]
    assert 10 not in info["data_points"]  # no fan_speed_enum like on EASY9005SM/PLOOM


def test_easy_hcm_names_moved_out_of_easy_hood() -> None:
    """Only one entry may claim a product name, otherwise lookup order decides."""
    easy = KNOWN_DEVICES["easy_hood"]["product_names"]
    assert "KKT Kolbe EASY909SHCM" not in easy
    assert "KKT Kolbe EASY609SHCM" not in easy
    assert "KKT Kolbe EASY9005SM" in easy
    seen: dict[str, str] = {}
    for key, info in KNOWN_DEVICES.items():
        for name in info["product_names"]:
            assert name not in seen, f"{name} in {seen.get(name)} and {key}"
            seen[name] = key


@pytest.mark.parametrize(
    ("device", "expected"),
    [
        ({"category": "yyj", "product_id": "xfw4ckzxljs4ncta", "id": "bf00"}, "easy_hcm_hood"),
        ({"category": "yyj", "product_name": "KKT Kolbe EASY HCM", "id": "bf00"}, "easy_hcm_hood"),
        ({"category": "", "product_name": "EASY909SHCM", "id": "bf00"}, "easy_hcm_hood"),
        ({"category": "yyj", "product_id": "e1my0pj8", "id": "bf00"}, "easy_hood"),
    ],
)
def test_detect_easy_variants(device: dict[str, str], expected: str) -> None:
    """Product id and name keywords pick the right EASY variant."""
    assert detect_device_type_from_api(device)[0] == expected
