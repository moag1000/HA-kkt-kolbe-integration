# Experimental

Reverse-engineered protocol documentation and proof-of-concept code.
Not integrated into the main KKT Kolbe Home Assistant integration.

## Contents

### `ble_pairing/` - Tuya BLE Device Pairing Protocol

Source: KKT.Control v2.0.9 APK (com.KKTControl.com), Tuya ThingClips SDK v4.4.0.

The KKT Kolbe app is an OEM-branded Tuya SmartLife app (App-ID: 258744435).
Device pairing uses Tuya's proprietary BLE+WiFi combo protocol. This directory
documents the protocol for potential future implementation of BLE device pairing
directly from Home Assistant.

### Current State

**Implemented in Python (`session_key.py`):**
- Session key derivation (disassembled from `libBleLib.so`, ARM64)
- Packet encryption/decryption (AES-128-CBC, from Java layer `bppdpdq.java`)

**Documented but not verified with real devices:**
- GATT service/characteristic UUIDs (from APK, may differ for BLE+WiFi vs Mesh)
- Cloud API pairing sequence (6 endpoints)
- BLE advertisement format (field structure known, byte-level parsing not implemented)

**Unknown (requires BLE traffic capture to resolve):**
- Which GATT UUIDs KKT devices actually expose during pairing
- How the ECDH shared secret maps to `made_session_key()` arguments
- Exact KLV wire format for WiFi credential transfer
- Whether KKT devices use SECURITY_LEVEL_OLD or SECURITY_LEVEL_NEW

## Contributing

A BLE traffic capture during KKT Kolbe device pairing (using nRF Connect HCI logger)
would resolve all remaining unknowns. See `ble_pairing/PROTOCOL.md` for instructions.
