"""Tests of the pending-write overlay."""

from __future__ import annotations

import pytest

from custom_components.kkt_kolbe.pending_writes import PendingWrites
from custom_components.kkt_kolbe.pending_writes import same_dp_value


@pytest.mark.parametrize(
    ("reported", "written"),
    [(True, True), ("true", True), ("True", True), (1, True), ("0", False), ("3", 3), (3.0, 3), ("low", "low")],
)
def test_same_value_in_other_representation(reported, written) -> None:
    """The device's own representation of a written value confirms it."""
    assert same_dp_value(reported, written)


@pytest.mark.parametrize(
    ("reported", "written"),
    [(None, False), (False, True), ("2", 3), (2, True), ("AQ==", "aq=="), ("LOW", "low"), ("x", 0)],
)
def test_different_values_do_not_confirm(reported, written) -> None:
    """Base64 RAW and enum strings are compared exactly; None never confirms."""
    assert not same_dp_value(reported, written)


def test_apply_releases_on_text_confirmation() -> None:
    """Overlay until the device reports the value, also as text."""
    pending = PendingWrites()
    pending.set(1, True)
    assert pending.apply({"1": False})["1"] is True
    assert pending.apply({"1": "true"})["1"] == "true"
    assert pending.get(1) is None
