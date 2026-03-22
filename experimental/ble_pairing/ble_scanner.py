"""Proof-of-concept: Scan for Tuya BLE devices using bleak.

STATUS: Stub / starting point. The advertisement parser is NOT implemented.
Tuya BLE advertisement parsing requires knowledge of the exact byte-level
format which varies by firmware version. A real implementation needs
captured BLE traffic to validate against.

What this CAN do:
- Scan for BLE devices and show raw advertisement data
- Filter by service UUID 0xA201 (Tuya BLE standard)

What this CANNOT do:
- Parse Tuya advertisement fields (productId, uuid, flags, isBind)
- Detect KKT Kolbe devices specifically (needs advertisement parsing)

Usage:
    pip install bleak
    python3 ble_scanner.py
"""

from __future__ import annotations

import asyncio
import logging

try:
    from bleak import BleakScanner
    from bleak.backends.device import BLEDevice
    from bleak.backends.scanner import AdvertisementData
except ImportError:
    print("Error: bleak not installed. Run: pip install bleak")
    raise SystemExit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
_LOGGER = logging.getLogger(__name__)

# Tuya BLE service UUIDs to scan for
# NOTE: It's unknown which UUID KKT Kolbe devices actually use.
# Candidates from APK decompilation:
TUYA_SERVICE_UUIDS = [
    "0000a201-0000-1000-8000-00805f9b34fb",  # Tuya BLE standard (0xA201)
    "0000fd50-0000-1000-8000-00805f9b34fb",  # Tuya BLE alternate (0xFD50)
    "00010203-0405-0607-0809-0a0b0c0d1910",  # Telink BLE Mesh (from APK)
]


async def scan_raw(duration: float = 15.0) -> None:
    """Scan and print raw BLE advertisement data.

    This is the starting point for reverse engineering. Run this while
    a KKT Kolbe device is in pairing mode to see what it actually
    advertises. Then use the output to build a proper parser.
    """
    seen: set[str] = set()

    def callback(device: BLEDevice, adv: AdvertisementData) -> None:
        if device.address in seen:
            return

        # Check if any known Tuya UUID is in the advertisement
        has_tuya_uuid = any(
            uuid.lower() in [u.lower() for u in (adv.service_uuids or [])]
            for uuid in TUYA_SERVICE_UUIDS
        )

        # Also show devices with manufacturer data that could be Tuya
        # Tuya uses various company IDs; we can't filter precisely without captures
        has_mfr = bool(adv.manufacturer_data)

        if not has_tuya_uuid and not has_mfr:
            return

        seen.add(device.address)

        # Print raw data for analysis
        marker = " *** TUYA UUID MATCH ***" if has_tuya_uuid else ""
        print(f"\n{'='*60}{marker}")
        print(f"  Address:  {device.address}")
        print(f"  Name:     {device.name or '(none)'}")
        print(f"  RSSI:     {adv.rssi} dBm")

        if adv.service_uuids:
            print(f"  UUIDs:    {adv.service_uuids}")

        if adv.manufacturer_data:
            for company_id, data in adv.manufacturer_data.items():
                print(f"  MfrData:  company=0x{company_id:04X} data={data.hex()} ({len(data)} bytes)")

        if adv.service_data:
            for uuid, data in adv.service_data.items():
                print(f"  SvcData:  uuid={uuid} data={data.hex()} ({len(data)} bytes)")

    print("=" * 60)
    print("Raw BLE Scanner - Looking for Tuya devices")
    print(f"Scanning for {duration:.0f} seconds...")
    print("Put your KKT Kolbe device in pairing mode now!")
    print("=" * 60)

    scanner = BleakScanner(detection_callback=callback)
    await scanner.start()
    await asyncio.sleep(duration)
    await scanner.stop()

    print(f"\n{'='*60}")
    print(f"Scan complete. Found {len(seen)} devices with manufacturer data or Tuya UUIDs.")
    print()
    print("NEXT STEPS:")
    print("1. Identify which device is your KKT Kolbe (by name, RSSI, or UUID match)")
    print("2. Note the company ID and raw manufacturer data bytes")
    print("3. These bytes contain: productId, deviceUUID, flags, isBind, etc.")
    print("4. Share the output (redact MAC if desired) in a GitHub issue")


if __name__ == "__main__":
    asyncio.run(scan_raw())
