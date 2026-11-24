"""Every translated exception the integration raises has a message."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from custom_components.kkt_kolbe import exceptions as kkt_exceptions

COMPONENT = Path(__file__).parent.parent / "custom_components" / "kkt_kolbe"
TRANSLATION_FILES = [
    COMPONENT / "strings.json",
    COMPONENT / "translations" / "en.json",
    COMPONENT / "translations" / "de.json",
]


_TRANSLATION_KEY = re.compile(r'(?<!_attr_)translation_key\s*=\s*"([a-z_]+)"')
_VALIDATION_ERROR = re.compile(r'_validation_error\(\s*"([a-z_]+)"')


def _raised_keys() -> set[str]:
    """All exception translation keys used in the integration's code.

    Repair issues use translation_key too; their keys live under "issues".
    """
    keys: set[str] = set()
    for path in COMPONENT.rglob("*.py"):
        text = path.read_text()
        keys.update(_TRANSLATION_KEY.findall(text))
        keys.update(_VALIDATION_ERROR.findall(text))
    issues = json.loads((COMPONENT / "strings.json").read_text()).get("issues", {})
    return keys - set(issues)


def _exception_classes() -> list[type[kkt_exceptions.KKTKolbeError]]:
    return [
        cls
        for cls in vars(kkt_exceptions).values()
        if isinstance(cls, type)
        and issubclass(cls, kkt_exceptions.KKTKolbeError)
        and cls is not kkt_exceptions.KKTKolbeError
    ]


@pytest.mark.parametrize("path", TRANSLATION_FILES, ids=lambda p: p.name)
def test_every_raised_key_is_translated(path: Path) -> None:
    """A key without a message shows up as the bare key in the UI."""
    exceptions = json.loads(path.read_text())["exceptions"]
    raised = _raised_keys()
    assert "no_matching_devices" in raised  # the pattern finds service errors
    assert "connection_failed" in raised  # ... and the exceptions.py classes
    missing = raised - set(exceptions)
    assert missing == set(), f"{path.name} lacks exception messages for {sorted(missing)}"


@pytest.mark.parametrize("cls", _exception_classes(), ids=lambda c: c.__name__)
def test_exception_placeholders_cover_messages(cls) -> None:
    """Placeholders used in a message are always passed, whatever the call."""
    err = cls()
    for path in TRANSLATION_FILES:
        message = json.loads(path.read_text())["exceptions"][err.translation_key]["message"]
        used = set(re.findall(r"{(\w+)}", message))
        assert used <= set(err.translation_placeholders), (path.name, err.translation_key, used)
