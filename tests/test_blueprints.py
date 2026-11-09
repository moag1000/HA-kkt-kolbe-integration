"""Validate the shipped automation blueprints against Home Assistant."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from homeassistant.components.automation.config import async_validate_config_item
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.yaml import load_yaml

BLUEPRINT_DIR = Path(__file__).parent.parent / "blueprints" / "automation"
BLUEPRINTS = sorted(BLUEPRINT_DIR.glob("*.yaml"))


def _required_inputs(blueprint: dict) -> dict:
    """Fill every input without a default with a plausible value."""
    inputs = {}
    for key, spec in blueprint["blueprint"]["input"].items():
        if "default" in spec:
            continue
        selector, options = next(iter(spec["selector"].items()))
        options = options or {}
        domain = options.get("domain") or next(iter(options.get("filter", [])), {}).get("domain") or "sensor"
        if isinstance(domain, list):
            domain = domain[0]
        inputs[key] = f"{domain}.test" if selector == "entity" else 1
    return inputs


@pytest.mark.asyncio
@pytest.mark.parametrize("path", BLUEPRINTS, ids=[p.name for p in BLUEPRINTS])
async def test_blueprint_is_valid(hass: HomeAssistant, path: Path) -> None:
    """Each blueprint renders into a valid automation."""
    target = Path(hass.config.path("blueprints/automation/kkt_kolbe"))
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, target / path.name)
    assert await async_setup_component(hass, "blueprint", {})

    config = {
        "id": path.stem,
        "use_blueprint": {"path": f"kkt_kolbe/{path.name}", "input": _required_inputs(load_yaml(path))},
    }
    result = await async_validate_config_item(hass, path.stem, config)
    assert result is not None
    assert result.validation_error is None
