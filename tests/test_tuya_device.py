"""Test KKTKolbeTuyaDevice protocol detection."""

from __future__ import annotations

import pytest

from custom_components.kkt_kolbe.tuya_device import KKTKolbeTuyaDevice


@pytest.mark.asyncio
async def test_auto_detect_protocol_includes_3_5():
    """Auto-detection must try Tuya protocol 3.5.

    Regression: Issue #8, dernick79 reported Error 914 on all detected
    versions. tinytuya scan of his Ploom hood revealed it speaks 3.5,
    but our auto-detection loop only tested [3.3, 3.4, 3.1, 3.2].
    Devices on 3.5 firmware (newer Tuya devices since ~2024) cannot
    connect locally without 3.5 in the test list.
    """
    import inspect

    source = inspect.getsource(KKTKolbeTuyaDevice._perform_connection)
    # The version test list must include 3.5 alongside the older versions.
    assert "3.5" in source, (
        "Protocol 3.5 missing from auto-detect list — devices on 3.5 firmware "
        "(e.g. Ploom hoods, some 2024+ models) cannot connect"
    )
