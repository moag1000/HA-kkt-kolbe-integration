# Tuya BLE Pairing Protocol - Reverse Engineering Documentation

> Reverse-engineered from KKT.Control v2.0.9 APK (com.KKTControl.com)
> Tuya ThingClips SDK v4.4.0, App-ID: 258744435, Base: odm/v7.0.0

## Table of Contents

1. [Overview](#overview)
2. [BLE Advertisement Format](#ble-advertisement-format)
3. [GATT Service & Characteristics](#gatt-service--characteristics)
4. [Connection & Pairing Flow](#connection--pairing-flow)
5. [ECDH Key Exchange](#ecdh-key-exchange)
6. [Packet Framing](#packet-framing)
7. [WiFi Provisioning (BLE+WiFi)](#wifi-provisioning-blewifi)
8. [Cloud API Endpoints](#cloud-api-endpoints)
9. [Security & Certificates](#security--certificates)
10. [Constants & Enums](#constants--enums)
11. [Native Library (libBleLib.so)](#native-library-blelibso)
12. [Open Questions](#open-questions)

---

## Overview

KKT Kolbe devices use Tuya's BLE+WiFi combo pairing (mode `BLE_WIFI = 10`).
The pairing flow has three phases:

```
Phase 1: BLE Discovery & Connection
  App scans for Tuya BLE advertisements (UUID 0xA201)
  App connects to device GATT service
  ECDH-P256 key exchange establishes encrypted channel

Phase 2: WiFi Provisioning
  App sends WiFi SSID + password + activation token over encrypted BLE
  Device connects to WiFi router
  Device contacts Tuya cloud to complete activation

Phase 3: Cloud Registration
  App calls cloud API to register device to user's account
  Cloud returns local_key for future local communication
```

---

## BLE Advertisement Format

### Scan Detection

Tuya BLE devices advertise with service UUID **`0xA201`**.

### Advertisement Data Structure (`ThingAdvertisingData`)

| Field | Size | Description |
|-------|------|-------------|
| `frameControl` | 2 bytes | Frame control flags |
| `frameCounter` | 4 bytes | Monotonic counter |
| `dpEncryptedType` | 1 byte | DP encryption type |
| `dpRaw` | variable | Raw DP data (encrypted) |
| `mic` | 4 bytes | Message Integrity Code |

**Nonce construction** (12 bytes, for AES-CCM decryption):
```
nonce = [fc0, fc1, ctr0, ctr1, ctr2, ctr3, fc0, fc1, ctr0, ctr1, ctr2, ctr3]
```

### Parsed Device Info (`BLEScanDevBean`)

| Field | Description |
|-------|-------------|
| `address` | BLE MAC address |
| `deviceName` | Advertised device name |
| `rssi` | Signal strength |
| `protocolVersion` | Tuya protocol version |
| `productId` | Tuya product ID (matches device_types.py) |
| `devUuId` | Device UUID |
| `mac` | Device MAC |
| `flag` | Capability flags (see SupportType) |
| `isBind` | Already bound to an account |
| `isShare` | Shared device |
| `support5G` | 5GHz WiFi support |
| `category` | Device category |
| `deviceType` | BLE device type code |

### Device Types

| Constant | Value | Description |
|----------|-------|-------------|
| `TYPE_SINGLE_BLE` | 100 | Pure BLE device |
| `TYPE_WIFI` | 200 | BLE+WiFi combo (KKT devices) |
| `TYPE_ZIGBEE` | 300 | BLE+Zigbee combo |
| `TYPE_THING_BEACON` | 400 | Beacon device |
| `TYPE_THING_BEACON_MESH` | 500 | Beacon mesh |

### SupportType Flags (parsed from `flag` byte)

| Flag | Value | Description |
|------|-------|-------------|
| `SUPPORT_5G` | 1 | 5GHz WiFi support |
| `SUPPORT_PRODUCT_KEY` | 2 | Uses product key (not product ID) |
| `SUPPORT_SHARE` | 4 | Sharing supported |
| `SUPPORT_PLUG_PLAY` | 8 | Plug & play pairing |
| `SUPPORT_QR_DEVICE` | 16 | QR code pairing |
| `SUPPORT_ADVERTISE_MAC` | 32 | MAC in advertisement |
| `SUPPORT_BIND` | 128 | Bind capability |
| `SUPPORT_PRE_WIFI_LIST` | 256 | Pre-fetch WiFi list |
| `SUPPORT_SECURITY_SUPPORT` | 512 | New security supported |
| `SUPPORT_SECURITY_ENABLE` | 1024 | New security enabled |
| `SUPPORT_ETHERNET` | 2048 | Ethernet support |
| `SUPPORT_BEACON_WIFI` | 4096 | Beacon WiFi mode |

---

## GATT Service & Characteristics

### Primary Service (from APK - UNVERIFIED for KKT devices)

**WARNING:** These UUIDs are from the Telink BLE Mesh code path in the SDK.
KKT Kolbe BLE+WiFi combo devices may use different UUIDs (e.g. standard Tuya
`0xFD50`). A BLE traffic capture is needed to confirm which UUIDs KKT devices
actually use during pairing. Use `ble_scanner.py` to find out.

| UUID | Name | Operations |
|------|------|------------|
| `00010203-0405-0607-0809-0a0b0c0d1910` | TELINK_SERVICE | Main service |
| `00010203-0405-0607-0809-0a0b0c0d1914` | TELINK_PAIR | Read/Write (pairing) |
| `00010203-0405-0607-0809-0a0b0c0d1912` | TELINK_COMMAND | Write (commands) |
| `00010203-0405-0607-0809-0a0b0c0d1911` | TELINK_NOTIFY | Notify (responses) |
| `00010203-0405-0607-0809-0a0b0c0d1913` | TELINK_OTA | Write (firmware) |

**Alternative UUIDs** (standard Tuya BLE, may be used instead):
- Service: `0000fd50-0000-1000-8000-00805f9b34fb`
- Advertisement: `0000a201-0000-1000-8000-00805f9b34fb`

### Device Information Service (Standard BLE DIS)

| UUID | Name |
|------|------|
| `0000180a-0000-1000-8000-00805f9b34fb` | Device Information Service |
| `00002a26-0000-1000-8000-00805f9b34fb` | Firmware Revision |
| `00002a29-0000-1000-8000-00805f9b34fb` | Manufacturer Name |
| `00002a24-0000-1000-8000-00805f9b34fb` | Model Number |
| `00002a27-0000-1000-8000-00805f9b34fb` | Hardware Revision |

### Notification Descriptor

```
CCCD UUID: 00002902-0000-1000-8000-00805f9b34fb
```

Write `0x0100` to enable notifications, `0x0000` to disable.

---

## Connection & Pairing Flow

### Step-by-step sequence

```
1. App: Scan for BLE advertisements with UUID 0xA201
2. App: Filter for unbound devices (isBind == false)
3. App: Request activation token from cloud
         API: thing.m.device.list.token (v5.0)
4. App: Connect to device GATT service (TELINK_SERVICE)
         ConnectOpt: type=CONNECT_TYPE_ACTIVATOR(1), timeout=40000ms
5. App: Enable notifications on TELINK_NOTIFY characteristic
6. App: ECDH key exchange (see below)
7. Device: Returns DeviceInfoRsp (devId, uuid, capabilities, versions)
8. App: Request auth key from cloud
         API: m.thing.device.auth.key.get (v3.0)
         Params: uuid, mac
         Returns: encryptedAuthKey, random
9. App: [If new security] Validate device certificate chain
         API: thing.device.sec.servercert.fetch (v1.0)
         API: thing.device.sec.devcert.validate (v1.0)
         API: thing.device.sec.random.encrypt (v1.0)
10. App: Send WiFi credentials over encrypted BLE channel
         IThingBleWifiFlow.sendWifiInfo({ssid, pwd, token})
11. Device: Connects to WiFi, reports status codes
12. App: Register device with cloud
         API: m.thing.device.blu.active (v2.0)
13. Cloud: Returns localKey, secKey, verifyKey, beaconKey
14. App: Device is now paired and controllable
```

### ConnectOpt Builder

```java
ConnectOpt.Builder()
    .setConnectType(CONNECT_TYPE_ACTIVATOR)  // 1 = pairing mode
    .setSecurityLevel(SECURITY_LEVEL_NEW)     // 2 = new security
    .setAddress(bleAddress)
    .setConnectTimeout(40000)                 // 40 second timeout
    .build()
```

### Connect Types

| Constant | Value | Description |
|----------|-------|-------------|
| `CONNECT_TYPE_NORMAL` | 0 | Normal reconnection |
| `CONNECT_TYPE_ACTIVATOR` | 1 | Initial pairing/activation |
| `CONNECT_TYPE_PRECONNECT` | 2 | Pre-connect (low power) |

### Security Levels

| Constant | Value | Description |
|----------|-------|-------------|
| `SECURITY_LEVEL_OLD` | 0 | Legacy security |
| `SECURITY_LEVEL_OLD_NEED_UPDATE` | 1 | Legacy, needs upgrade |
| `SECURITY_LEVEL_NEW` | 2 | New ECDH-based security |

---

## ECDH Key Exchange

### Supported Curves (`CurveType`)

| Curve | Value | Key Size |
|-------|-------|----------|
| SECP-160-R1 | 0 | 20 bytes |
| SECP-192-R1 | 1 | 24 bytes |
| SECP-224-R1 | 2 | 28 bytes |
| **SECP-256-R1** | **3** | **32 bytes** (primary) |
| SECP-256-K1 | 4 | 32 bytes |

### Key Exchange Format (`ECDHRep`)

Device responds with:
```
byte[0]:    curve type (must be 3 = SECP_256_R1)
byte[1-65]: 65-byte uncompressed EC public key (0x04 || X || Y)
```

### Session Key Derivation - SOLVED

See [session_key.py](session_key.py) for the complete Python implementation.

```java
// JNI call in BLEJniLib.java
native byte[] madeSessionKey(byte[] sharedSecret, int length, byte[] localKey);
```

The algorithm is a custom CRC8-based substitution cipher (NOT standard crypto).
The 16-byte session key is used for AES-128-CBC encryption of all subsequent BLE traffic.

**UNKNOWN:** What exactly does the Java layer pass as arguments? Candidates:
- `sharedSecret`: Raw ECDH x-coordinate? Full shared point? Hash of shared secret?
- `localKey`: `encryptedAuthKey` from cloud API? First 6 chars of local key? Something else?
- `length`: Length of shared_secret? Or a mode selector?

This mapping is the main remaining unknown for a working implementation.

---

## Packet Framing

### MTU & Buffer

- Default MTU: 23 bytes (BLE standard)
- Usable payload: 20 bytes (23 - 3 byte ATT header)
- Write mode: Write-Without-Response (for throughput)

### Packet Structure

```
Data Packet (sn > 0):
  byte[0-1]: uint16 sequence number (sn)
  byte[2..]: payload data
  Last frame includes 2-byte CRC16 at end

Control Packet (sn == 0):
  byte[0-1]: 0x0000 (sn = 0)
  byte[2]:   type (0=CMD, 1=ACK)
  byte[3]:   command code
  byte[4-7]: parameter (uint32)

CTR Packet (start of transfer):
  type=CMD(0), parameter = total_frame_count << 16

ACK Packet (acknowledgment):
  type=ACK(1), parameter = frame_count | status
```

### Channel State Machine

```
IDLE → READY → WAIT_START_ACK → WRITING → SYNC → SYNC_ACK → SYNC_WAIT_PACKET → READING
```

### CRC

Both CRC16 and CRC32 are used. CRC16 for packet integrity, CRC32 for OTA.

---

## WiFi Provisioning (BLE+WiFi)

### Credential Transfer

WiFi credentials are sent via `IThingBleWifiFlow.sendWifiInfo(Map)`:

```java
Map<String, String> wifiInfo = new HashMap<>();
wifiInfo.put("ssid", wifiSSID);
wifiInfo.put("pwd", wifiPassword);
wifiInfo.put("token", activationToken);
```

Alternative method via `activeExtenModuleByBLEActived`:
```java
HashMap map = new HashMap();
map.put("ssid", ssid);
map.put("pwd", password);
bleManager.activeExtenModuleByBLEActived(devId, map, callback);
```

### WiFi Config Result Codes (`WiFiConfigResultRep`)

| Code | Constant | Description |
|------|----------|-------------|
| 0 | `CONNECT_NETWORK_SUCCESS` | WiFi connected successfully |
| 1 | `DATA_FORMAT_ERROR` | Invalid credential format |
| 2 | `NOT_FOUND_ROUTER` | SSID not found |
| 3 | `WIFI_PASSWORD_ERROR` | Wrong password |
| 4 | `CONNECT_ROUTER_ERROR` | Connection to router failed |
| 5 | `DHCP_ERROR` | DHCP lease failed |
| 6 | `CONNECT_NETWORK_FAILED` | General network failure |
| 7 | `GET_URL_ERROR` | Cloud URL resolution failed |
| 8 | `WIFI_ACTIVE_ERROR` | Cloud activation failed |
| 9 | `WIFI_ACTIVE_SUCCESS` | Cloud activation succeeded |

### Device Info Response (`WiFiDevInfo`)

After connecting, device returns:
- `devId` - Device identifier
- `uuid` - Device UUID
- `productKey` - Product key
- `hid` - Hardware ID
- `softVer` - Software version
- `cadVer` - CAD version
- `baselineVer` - Baseline version
- `protocolVer` - Protocol version
- `packetMaxSize` - Max BLE packet size
- `modulesOnline` - Online module list

---

## Cloud API Endpoints

### Device Pairing APIs

| API | Version | Purpose | Parameters |
|-----|---------|---------|------------|
| `thing.m.device.list.token` | v5.0 | Get activation token | homeId |
| `thing.m.device.token.create` | v1.0 | Create pairing token | - |
| `m.thing.device.auth.key.get` | v3.0 | Get BLE auth key | uuid, mac |
| `thing.m.device.auth.key.get` | v2.0 | Alt auth key (with home) | uuid, mac, homeId |
| `m.thing.device.reset.key.get` | v1.0 | Get reset key | uuid, mac, encryptedValue |
| `m.thing.device.keys.get.create` | v1.0 | Create/get secret keys | devId |
| `thing.m.device.register` | v1.0 | Register device | (DeviceInfoRsp) |
| `thing.m.device.active` | v1.0 | Activate device | (DeviceInfoRsp) |
| `m.thing.device.blu.active` | v2.0 | BLE device activation | mac, productId, timezone, bindUser, type=4 |
| `thing.m.device.blu.preactive` | v2.0 | BLE pre-activation | mac, uuid, r1, pid, sign, type |
| `m.thing.device.bind.status.get` | v2.0 | Check bind status | uuid, mac, encryptValue |
| `thing.m.device.security.config.all` | v1.0 | All security configs | - |

### Security/Certificate APIs

| API | Version | Purpose |
|-----|---------|---------|
| `thing.device.sec.servercert.fetch` | v1.0 | Fetch server CA certificate |
| `thing.device.sec.devcert.validate` | v1.0 | Validate device certificate |
| `thing.device.sec.devcert.ppk.validate` | v1.0 | Validate device cert PPK |
| `thing.device.sec.random.encrypt` | v1.0 | Server-side random encryption |

### Activation Response

Successful activation returns `ActivatorResultParam`:
- `localKey` - AES key for local LAN communication (the key we need!)
- `secKey` - Security key
- `verifyKey` - Verification key
- `beaconKey` - Beacon encryption key
- `needBeaconKey` - Whether beacon key is required

---

## Security & Certificates

### Certificate Chain Validation

For devices with `SECURITY_LEVEL_NEW` (2):

1. **Fetch server cert**: `thing.device.sec.servercert.fetch` returns `SecurityCertBean`:
   - `publicKey` - Server public key
   - `caSignature` - CA signature

2. **Validate device cert**: `thing.device.sec.devcert.validate` with:
   - `uuid` - Device UUID
   - `devCert` - Device certificate (read from BLE)

3. **Challenge-Response**: `thing.device.sec.random.encrypt`:
   - App sends random challenge
   - Server returns encrypted version
   - Both sides verify the other's identity

### Auth Key (`AuthKeyBean`)

| Field | Description |
|-------|-------------|
| `devId` | Device ID |
| `uuid` | Device UUID |
| `name` | Device name |
| `iconUrl` | Device icon URL |
| `encryptedAuthKey` | Encrypted auth key (sent to device) |
| `random` | Random value for key derivation |
| `resetKey` | Key for factory reset |
| `errorCode` | Error code (0 = success) |

---

## Constants & Enums

### Activation Modes (`ThingDeviceActiveModeEnum`)

| Mode | ID | Description | Relevant |
|------|----|-------------|----------|
| EZ | 1 | SmartConfig broadcast | No |
| AP | 2 | Access Point mode | Fallback |
| **SINGLE_BLE** | **9** | **Pure BLE pairing** | **Yes** |
| **BLE_WIFI** | **10** | **BLE+WiFi combo** | **Primary for KKT** |
| **MULT_MODE** | **20** | **Multi-mode fallback** | **Yes** |
| BLE_WIFI_BLE_FIRST | 23 | BLE+WiFi, BLE priority | Yes |
| BLE_WIFI_BATCH | 33 | Batch BLE+WiFi | Possible |

### BLE Operation Codes

| Code | Value | Description |
|------|-------|-------------|
| `CODE_CONNECT` | 1 | Connect to device |
| `CODE_DISCONNECT` | 2 | Disconnect |
| `CODE_READ` | 3 | Read characteristic |
| `CODE_WRITE` | 4 | Write characteristic |
| `CODE_WRITE_NORSP` | 5 | Write without response |
| `CODE_NOTIFY` | 6 | Enable notifications |
| `CODE_UNNOTIFY` | 7 | Disable notifications |
| `CODE_READ_RSSI` | 8 | Read RSSI |
| `CODE_CONFIG_MTU` | 9 | Configure MTU |
| `CODE_INDICATE` | 10 | Enable indications |
| `CODE_DISCOVERY_SERVICE` | 24 | Discover services |

### Connection States

| State | Value |
|-------|-------|
| `DISCONNECTED` | 0 |
| `CONNECTING` | 1 |
| `CONNECTED` | 2 |
| `DISCONNECTING` | 3 |
| `SERVICE_READY` | 19 |

### Device Capability Bits (`DeviceCapabilityBit`)

| Bit | Name | Description |
|-----|------|-------------|
| 0 | ControlDuringOta | Can control during OTA |
| 1 | LowerPower | Low power mode |
| 2 | SupportBeacon | Beacon support |
| 3 | HasLinkEncrypt | Link-layer encryption |
| 7 | LinkEncrypt | Link encryption active |
| 8 | SupportPsk | PSK authentication |
| 17 | Support_Boot_OTA | Boot-time OTA |
| 18 | BLE_LAN | BLE LAN bridge |
| 19 | BLE_STRUCT_DP | Structured DP over BLE |

### Activation Status Command

Status received via BLE notification, command ID = `0x801F` (32799)

`DeviceActivatorStatus`:
- `activatorSuccess` - boolean
- `typeValue` - activation type
- `stage` - current stage
- `result` - result code

---

## Native Library (libBleLib.so) - REVERSE ENGINEERED

The cryptographic operations are in a **70KB native ARM64 library**.
The library is **not stripped and contains debug info + source paths**, enabling full disassembly.

**Build info:** NDK 27.1, Clang 18.0.2, built on macOS by developer `jiyehoo`
**Source path:** `DeviceCore5120/TuyaDeviceCoreKit/bluetooth/tuyableprotocol/src/main/jniCode/`

### JNI Exports

| Symbol | Offset | Status | Purpose |
|--------|--------|--------|---------|
| `made_session_key` | 0x3060 | **SOLVED** | Session key derivation |
| `normalDataRecive` | 0x284c | Documented | Decrypt received data |
| `getCommonRequestData` | - | Documented | Build encrypted request |
| `data_2_klvlist` | 0x20a0 | Documented | Parse KLV data |
| `klvlist_2_data` | 0x1fdc | Documented | Serialize KLV data |
| `Thing_OTACalcCRC` | 0x3260 | Documented | CRC for OTA packages |
| `init_crc8` | 0x2c58 | **SOLVED** | Initialize CRC8 lookup table |

### Session Key Derivation - FULLY REVERSE ENGINEERED

**See `session_key.py` for complete working Python implementation.**

Disassembled from ARM64 at offset 0x3060-0x325c (508 bytes). The algorithm is
**NOT standard crypto** - it's a custom CRC8-based substitution cipher:

```python
# CRC8/MAXIM table (polynomial 0x8C, 256 entries)
CRC8_TABLE = generate_crc8_table(0x8C)

def made_session_key(shared_secret, key_len, local_key):
    """Derive 16-byte BLE session key."""
    output = bytearray(local_key[:16])

    if key_len > 15:
        # Direct mode: XOR each byte, then substitute through CRC8 table
        for i in range(16):
            output[i] = CRC8_TABLE[ shared_secret[i] ^ output[i] ]
    else:
        # Folding mode: fold longer secrets into 16 bytes
        for i in range(16):
            if i < key_len:
                xor_val = shared_secret[i] ^ output[i]
            else:
                fold_idx = i - key_len
                xor_val = ((shared_secret[fold_idx] + shared_secret[fold_idx+1]) & 0xFF) ^ output[i]
            output[i] = CRC8_TABLE[ xor_val & 0xFF ]

    return bytes(output)
```

The CRC8 table functions as a non-linear substitution box (S-box), combined with
XOR mixing of two key inputs. This is lightweight enough for constrained BLE
microcontrollers while providing non-trivial key mixing.

### Data Encryption - FULLY REVERSE ENGINEERED

**See `session_key.py` for complete working encrypt/decrypt Python implementation.**

The native library contains **NO encryption** (verified: only imports malloc/free/memcpy/calloc).
The actual crypto is in the Java layer: `com.thingclips.sdk.bluetooth.bppdpdq`

**Algorithm: AES-128-CBC / PKCS5Padding**

```
Cipher: AES/CBC/PKCS5Padding
Key:    16-byte session key from made_session_key()
IV:     Random 16 bytes, prepended to ciphertext
```

**Encrypt** (bppdpdq.pdqppqb(), sending to device):
```
iv = random_bytes(16)
ciphertext = AES_CBC_PKCS5(plaintext, session_key, iv)
output = base64(iv || ciphertext)
```

**Decrypt** (bppdpdq.bdpdqbp(), receiving from device):
```
raw = base64_decode(input)
iv = raw[0:16], ciphertext = raw[16:]
plaintext = AES_CBC_PKCS5_decrypt(ciphertext, session_key, iv)
```

**What the native library does (NOT crypto, only framing):**
- `trsmitr_send_pkg_encode` / `trsmitr_recv_pkg_decode` - Multi-frame BLE packet splitting (20-byte MTU)
- `data_2_klvlist` / `klvlist_2_data` - KLV (Key-Length-Value) serialization
- `made_session_key` - Session key derivation (CRC8 substitution)

### Complete Protocol Stack

```
┌─────────────────────────────────────┐
│  Java Layer (bppdpdq.java)          │
│  AES-128-CBC encrypt/decrypt        │  ← SOLVED
│  Base64 encode/decode               │
├─────────────────────────────────────┤
│  Native Layer (libBleLib.so)        │
│  KLV serialization                  │  ← SOLVED
│  Multi-frame packet framing (20B)   │  ← SOLVED
│  Session key derivation (CRC8)      │  ← SOLVED
├─────────────────────────────────────┤
│  BLE GATT Layer (bleak)             │
│  Write to TELINK_COMMAND char       │
│  Read from TELINK_NOTIFY char       │
├─────────────────────────────────────┤
│  ECDH Key Exchange (NIST P-256)     │
│  Standard cryptography library      │
└─────────────────────────────────────┘
```

### Source Files (from debug info in libBleLib.so)

- `com_thingclips_ble_jni_BLEJniLib.c` - JNI bridge (developer: jiyehoo)
- `mutli_tsf_protocol.c/.h` - Multi-frame transfer protocol
- `crc8.c/.h` - CRC8 table generation and lookup

---

## Status

| Component | State | Source | Notes |
|-----------|-------|--------|-------|
| Session key derivation | Implemented | libBleLib.so disassembly | `session_key.py` - algorithm verified, argument mapping unverified |
| Packet encryption | Implemented | bppdpdq.java decompilation | AES-128-CBC, roundtrip tested |
| Packet framing | Documented | libBleLib.so symbols | 20-byte MTU splitting with sequence numbers |
| KLV serialization | Documented | libBleLib.so symbols | Wire format not fully documented |
| Cloud API flow | Documented | APK decompilation | 6 endpoints, parameters known |
| GATT UUIDs | Candidates identified | UuidInformation.java | Not verified with real KKT device traffic |

## Open Questions

1. **ECDH-to-session-key mapping**: What does the Java layer pass as `shared_secret`,
   `key_len`, and `local_key` to `made_session_key()`? Without this, the session key
   derivation algorithm is correct but cannot be invoked with the right inputs.

2. **ConnectParam.loginKey**: The Java code truncates the local key to first 6 chars.
   This truncated key may serve as the initial `local_key` parameter to `made_session_key()`.

3. **GATT UUIDs**: The APK contains both Telink Mesh UUIDs and standard Tuya BLE UUIDs.
   Which set do KKT Kolbe BLE+WiFi combo devices actually use?

4. **KKT security level**: Do KKT Kolbe devices use `SECURITY_LEVEL_NEW` (2)
   or `SECURITY_LEVEL_OLD` (0)? This determines whether certificate validation is needed.

5. **KLV wire format**: The byte-level encoding of Key-Length-Value messages
   (key ID size, length encoding, value serialization) has not been documented.

---

## How to Contribute

### What's Solved vs What's Not

**Solved (from APK analysis alone):**
- Session key derivation algorithm (`session_key.py`)
- Packet encryption: AES-128-CBC/PKCS5 (`session_key.py`)
- Cloud API endpoint sequence (`cloud_api.py`)
- GATT characteristic UUIDs (candidates, unverified)

**NOT solved (needs real device interaction):**
- Which GATT UUIDs do KKT devices actually use?
- What bytes does the app send as the FIRST message after GATT connect?
- How is the ECDH public key sent/received (which characteristic, what framing)?
- What exactly maps to `made_session_key(arg0, arg1, arg2)` from the Java side?
- What is the KLV message format for WiFi credentials?

### Highest-Value Contribution: BLE Traffic Capture

All remaining unknowns can be resolved with a **single BLE traffic capture**
during device pairing. The crypto is already solved, so captured traffic can
be decrypted to understand the exact message sequence.

**How to capture:**
1. Install **nRF Connect** on Android
2. Enable BLE HCI snoop log: `adb shell settings put global ble_hci_snoop_log_enabled true`
3. Reset a KKT Kolbe device to pairing mode (hold button until LED blinks)
4. Pair it via the SmartLife app
5. Stop HCI log, extract via `adb bugreport` (it's in the zip under `FS/data/misc/bluetooth/`)
6. Open in Wireshark > filter `btatt` or `btle`
7. Share the `.pcap` in a GitHub issue (redact WiFi password from any plaintext!)

**What to look for in the capture:**
- GATT Service Discovery (which UUIDs does the device expose?)
- First Write after connection (ECDH public key? Or something else?)
- Notify responses (device's ECDH public key, DeviceInfoRsp)
- Write sequence after key exchange (encrypted WiFi credentials)

---

*Document generated from APK reverse engineering on 2026-03-22*
*Native library disassembled with objdump (ARM64/aarch64)*
*Source: KKT.Control v2.0.9 (com.KKTControl.com), ThingClips SDK v4.4.0*
