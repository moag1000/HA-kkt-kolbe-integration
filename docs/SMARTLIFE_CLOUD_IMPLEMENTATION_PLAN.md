# SmartLife/Tuya Smart App Integration - Implementierungsplan

**Erstellt:** 2026-01-05
**Branch:** `feature/tuya-cloud-integration`
**Ziel:** QR-Code basierte Einrichtung via SmartLife/Tuya Smart App - **OHNE Developer Account** - mit automatischem Local Key Abruf

> **Wichtig:** SmartLife und Tuya Smart sind funktional identische Apps, die regional unterschiedlich vermarktet werden. Diese Integration unterstützt **beide Apps** gleichwertig.

---

## Inhaltsverzeichnis

1. [Übersicht & Motivation](#1-übersicht--motivation)
2. [Technische Analyse](#2-technische-analyse)
3. [Architektur-Design](#3-architektur-design)
4. [Implementierungsschritte](#4-implementierungsschritte)
5. [Config Flow Design](#5-config-flow-design)
6. [API Client Implementation](#6-api-client-implementation)
7. [Coordinator Integration](#7-coordinator-integration)
8. [Error Handling & Edge Cases](#8-error-handling--edge-cases)
9. [Testing Strategy](#9-testing-strategy)
10. [README & Dokumentation Updates](#10-readme--dokumentation-updates)
11. [Migration & Backwards Compatibility](#11-migration--backwards-compatibility)
12. [Quellen & Referenzen](#12-quellen--referenzen)

---

## 1. Übersicht & Motivation

### 1.1 Problemstellung

Die aktuelle KKT Kolbe Integration erfordert für Cloud-Funktionalität:
- **Tuya IoT Developer Account** (iot.tuya.com)
- **Cloud Project Setup** mit API-Subscription
- **Manuelle Extraktion** von Client ID, Client Secret
- **QR-Code Verknüpfung** zwischen App und IoT Platform

**Kritisches Problem:** Die IoT Core API-Subscription läuft nach **einem Monat** ab und kann nur alle **6 Monate** erneuert werden.

### 1.2 Lösung: SmartLife/Tuya App QR-Code Login

Die `tuya-device-sharing-sdk` Library ermöglicht:

| Feature | Bisherige Methode | Neue Methode |
|---------|-------------------|--------------|
| Account erforderlich | Tuya IoT Developer | SmartLife/Tuya App (Consumer) |
| Setup-Aufwand | ~15 Minuten | ~1 Minute |
| API-Subscription | Erforderlich (1 Monat Limit) | Nicht erforderlich |
| Local Key Zugriff | Via IoT Platform | Automatisch via SDK |
| Token-Erneuerung | Manuell | Automatisch |

### 1.3 Referenz-Implementierungen

| Integration | Methode | Repository |
|-------------|---------|------------|
| **tuya-local** (make-all) | QR-Code ohne Dev Account | [GitHub](https://github.com/make-all/tuya-local) |
| **HA Core Tuya** | User Code + QR-Code | [GitHub](https://github.com/home-assistant/core/tree/dev/homeassistant/components/tuya) |
| **LocalTuya** | IoT Platform (mit Dev Account) | [GitHub](https://github.com/rospogrigio/localtuya) |

---

## 2. Technische Analyse

### 2.1 tuya-device-sharing-sdk Struktur

```
tuya_sharing/
├── __init__.py          # Exports: Manager, CustomerDevice, LoginControl, etc.
├── const.py             # URL_PATH, CONF_* constants
├── user.py              # LoginControl class - QR code auth
├── manager.py           # Manager class - device management
├── device.py            # CustomerDevice - device model with local_key
├── customerapi.py       # CustomerApi - authenticated HTTP requests
├── mq.py                # Message Queue for Cloud Push
├── home.py              # Home management
├── scenes.py            # Scene management
└── strategy.py          # Local strategy for device communication
```

### 2.2 Authentifizierungsablauf

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Home          │     │   Tuya Cloud    │     │   SmartLife     │
│   Assistant     │     │   Server        │     │   App           │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │ 1. POST /qrcode/tokens                        │
         │   (client_id, user_code, schema)              │
         │ ─────────────────────>│                       │
         │                       │                       │
         │ 2. Return QR token    │                       │
         │ <─────────────────────│                       │
         │                       │                       │
         │ 3. Display QR Code    │                       │
         │   "tuyaSmart--qrLogin?token=xxx"              │
         │                       │                       │
         │                       │   4. User scans QR    │
         │                       │ <─────────────────────│
         │                       │                       │
         │                       │   5. User authorizes  │
         │                       │ <─────────────────────│
         │                       │                       │
         │ 6. GET /qrcode/tokens/{token}                 │
         │   (polling for result)                        │
         │ ─────────────────────>│                       │
         │                       │                       │
         │ 7. Return auth tokens │                       │
         │   (access_token, refresh_token,               │
         │    terminal_id, endpoint, uid)                │
         │ <─────────────────────│                       │
         │                       │                       │
         │ 8. Initialize Manager │                       │
         │   with tokens         │                       │
         │ ─────────────────────>│                       │
         │                       │                       │
         │ 9. Fetch device list  │                       │
         │   with local_keys     │                       │
         │ <─────────────────────│                       │
         │                       │                       │
```

### 2.3 LoginControl API (aus tuya_sharing/user.py)

```python
class LoginControl:
    """Handles QR code authentication flow."""

    def __init__(self):
        self.session = requests.session()

    def qr_code(self, client_id: str, schema: str, user_code: str) -> Dict[str, Any]:
        """Generate QR code token for authentication.

        Args:
            client_id: Fixed client ID for Home Assistant integration
            schema: App schema ("tuyaSmart" or "smartlife")
            user_code: User's code from SmartLife/Tuya app

        Returns:
            {"success": True, "result": {"qrcode": "token_string"}}
        """
        response = self.session.request(
            "POST",
            f"https://{URL_PATH}/v1.0/m/life/home-assistant/qrcode/tokens"
            f"?clientid={client_id}&usercode={user_code}&schema={schema}",
            params=None, json=None, headers=None
        )
        return response.json()

    def login_result(
        self, token: str, client_id: str, user_code: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Poll for QR code scan result.

        Returns:
            (success, result_dict) where result_dict contains:
            - terminal_id: Unique terminal identifier
            - endpoint: API endpoint URL
            - token_info: {access_token, refresh_token, expire_time, uid}
            - t: Timestamp
        """
        response = self.session.request(
            "GET",
            f"https://{URL_PATH}/v1.0/m/life/home-assistant/qrcode/tokens/{token}"
            f"?clientid={client_id}&usercode={user_code}",
            params=None, json=None, headers=None
        )
        response = response.json()
        if response.get("success"):
            ret = response.get("result", {})
            ret["t"] = response.get("t")
            return True, ret
        return False, response
```

### 2.4 CustomerDevice Attribute (aus tuya_sharing/device.py)

```python
@dataclass
class CustomerDevice:
    """Device model with all relevant attributes."""

    # Identifiers
    id: str                    # Device ID (20-22 chars)
    name: str                  # User-assigned name
    local_key: str             # ← WICHTIG: Encryption key for local control
    category: str              # Device category (yyj=hood, dcl=cooktop)
    product_id: str            # Tuya product ID
    product_name: str          # Product name
    uuid: str                  # Device UUID
    asset_id: str              # Asset identifier

    # Status & Connectivity
    online: bool               # Online status
    ip: str                    # Local IP address (if available)
    time_zone: str             # Device timezone

    # Timestamps
    active_time: int           # First activation timestamp
    create_time: int           # Creation timestamp
    update_time: int           # Last update timestamp

    # Capabilities
    sub: bool                  # Is sub-device (of a hub)
    icon: str                  # Device icon URL
    set_up: bool               # Setup completed
    support_local: bool        # Supports local control

    # Data Collections
    status: dict               # Current status DPs
    function: list[DeviceFunction]   # Available functions
    status_range: dict         # Status value ranges
    local_strategy: dict       # Local communication strategy
```

### 2.5 Manager Device Retrieval (aus tuya_sharing/manager.py)

```python
class Manager:
    """Central manager for device operations."""

    def __init__(
        self,
        client_id: str,
        user_code: str,
        terminal_id: str,
        endpoint: str,
        token_info: dict,
        listener: SharingTokenListener | None = None
    ):
        self.device_map: dict[str, CustomerDevice] = {}
        # ... initialization

    def update_device_cache(self) -> None:
        """Fetch all devices from cloud and populate device_map.

        After calling this, access devices via:
        - self.device_map[device_id] for single device
        - self.device_map.values() for all devices

        Each device has .local_key attribute for local control.
        """
        # Queries homes, then devices per home
        # Populates self.device_map with CustomerDevice objects
```

---

## 3. Architektur-Design

### 3.1 Neue Komponenten-Struktur

```
custom_components/kkt_kolbe/
├── clients/
│   ├── __init__.py
│   ├── tuya_sharing_client.py    # NEU: QR-Code auth client
│   └── tuya_iot_client.py        # Bestehend: IoT Platform client
├── config_flow.py                 # ERWEITERT: SmartLife + Parent-Child Pattern
├── const.py                       # ERWEITERT: Neue Konstanten
├── strings.json                   # ERWEITERT: Neue Translations
├── translations/
│   ├── en.json                    # ERWEITERT
│   └── de.json                    # ERWEITERT
└── ...
```

### 3.2 Parent-Child Entry Architektur

> **Kernkonzept:** SmartLife Account als Parent Entry, Geräte als Child Entries.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Home Assistant                                    │
│                                                                          │
│  Geräte & Dienste                                                       │
│  ────────────────                                                       │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 📱 SmartLife Account                          [Parent Entry]     │   │
│  │    user_code: EU12345678                                        │   │
│  │    app: SmartLife                                               │   │
│  │    token_status: ✅ Gültig (läuft ab in 89 Tagen)               │   │
│  │                                                                  │   │
│  │    Verbundene Geräte: 2                                         │   │
│  │    ─────────────────────────────────────────────────────────    │   │
│  │    [+ Gerät hinzufügen]  [Token erneuern]  [Account entfernen]  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 🌬️ HERMES Dunstabzugshaube                   [Child Entry]      │   │
│  │    via SmartLife Account                                        │   │
│  │    IP: 192.168.1.50                                             │   │
│  │    Status: 🟢 Online                                            │   │
│  │                                                                  │   │
│  │    Entities: Fan, Light, RGB Mode, Timer, Filter...            │   │
│  │    ─────────────────────────────────────────────────────────    │   │
│  │    [Konfigurieren]  [Gerät entfernen]                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 🔥 IND7705HC Kochfeld                        [Child Entry]      │   │
│  │    via SmartLife Account                                        │   │
│  │    IP: 192.168.1.51                                             │   │
│  │    Status: 🟢 Online                                            │   │
│  │                                                                  │   │
│  │    Entities: Zones, Timers, Child Lock...                      │   │
│  │    ─────────────────────────────────────────────────────────    │   │
│  │    [Konfigurieren]  [Gerät entfernen]                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 3.2.1 Datenstruktur: Parent Entry (SmartLife Account)

```python
# Parent Entry - speichert Account-Daten und Tokens
PARENT_ENTRY_DATA = {
    "entry_type": "account",  # Markierung als Parent
    "setup_mode": SETUP_MODE_SMARTLIFE,
    "user_code": "EU12345678",
    "app_schema": "smartlife",
    CONF_SMARTLIFE_TOKEN_INFO: {
        "access_token": "...",
        "refresh_token": "...",
        "expire_time": 1234567890,
        "uid": "...",
    },
    CONF_SMARTLIFE_TERMINAL_ID: "...",
    CONF_SMARTLIFE_ENDPOINT: "https://openapi.tuyaeu.com",
}

# Parent Entry hat KEINE Entities - nur Account-Management
```

#### 3.2.2 Datenstruktur: Child Entry (Device)

```python
# Child Entry - speichert Gerätedaten, referenziert Parent
CHILD_ENTRY_DATA = {
    "entry_type": "device",  # Markierung als Child
    "parent_entry_id": "abc123...",  # Referenz zum Parent Entry
    "setup_mode": SETUP_MODE_SMARTLIFE,  # Woher kommt das Gerät
    "device_id": "bf1234567890abcd",
    "device_name": "HERMES Dunstabzugshaube",
    "local_key": "1234567890abcdef",
    "ip_address": "192.168.1.50",
    "category": "yyj",
    "product_id": "ypaixllljc2dcpae",
}

# Child Entry hat ALLE Entities (Fan, Light, Sensors, etc.)
```

#### 3.2.3 Vorteile des Parent-Child Patterns

| Aspekt | Ohne Parent-Child | Mit Parent-Child |
|--------|-------------------|------------------|
| **Token-Speicherung** | Dupliziert pro Gerät | Einmal im Parent |
| **Token-Refresh** | Alle Entries updaten | Nur Parent updaten |
| **Neues Gerät hinzufügen** | Kompletter Flow nochmal | Nur Gerät auswählen |
| **Account entfernen** | Jedes Gerät einzeln | Parent löscht alle Children |
| **Übersichtlichkeit** | Viele einzelne Entries | Klare Hierarchie |
| **Reauth Flow** | Pro Gerät | Einmal für Account |
| **Local Key Update** | Jedes Gerät einzeln | Parent holt alle Keys |

#### 3.2.4 Config Entry Lifecycle

```python
# In __init__.py

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up KKT Kolbe from a config entry."""

    entry_type = entry.data.get("entry_type", "device")

    if entry_type == "account":
        # Parent Entry: SmartLife Account
        return await _async_setup_account_entry(hass, entry)
    else:
        # Child Entry: Device
        return await _async_setup_device_entry(hass, entry)


async def _async_setup_account_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SmartLife account (parent entry)."""

    # Initialize SmartLife client
    token_info = entry.data.get(CONF_SMARTLIFE_TOKEN_INFO, {})

    try:
        smartlife_client = await TuyaSharingClient.async_from_stored_tokens(
            hass, token_info
        )
    except KKTAuthenticationError as err:
        raise ConfigEntryAuthFailed(f"SmartLife auth failed: {err}") from err

    # Store client for child entries to use
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "smartlife_client": smartlife_client,
        "type": "account",
    }

    # No platforms to forward - account has no entities
    return True


async def _async_setup_device_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up device (child entry)."""

    parent_entry_id = entry.data.get("parent_entry_id")

    # Get SmartLife client from parent (if SmartLife setup)
    if parent_entry_id:
        parent_data = hass.data.get(DOMAIN, {}).get(parent_entry_id, {})
        smartlife_client = parent_data.get("smartlife_client")
    else:
        smartlife_client = None

    # Connect to local device
    device = await async_connect_device(hass, entry.data)

    # Create coordinator
    coordinator = KKTKolbeUpdateCoordinator(
        hass=hass,
        entry=entry,
        device=device,
        smartlife_client=smartlife_client,  # For local_key refresh
    )

    # ... rest of device setup
```

#### 3.2.5 Automatisches Cleanup bei Parent-Löschung

```python
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    entry_type = entry.data.get("entry_type", "device")

    if entry_type == "account":
        # Parent Entry wird gelöscht → alle Children auch löschen
        child_entries = [
            e for e in hass.config_entries.async_entries(DOMAIN)
            if e.data.get("parent_entry_id") == entry.entry_id
        ]

        for child_entry in child_entries:
            await hass.config_entries.async_remove(child_entry.entry_id)

        # Cleanup parent data
        hass.data[DOMAIN].pop(entry.entry_id, None)
        return True

    else:
        # Device Entry - normal unload
        # ... existing cleanup code
```

### 3.3 Config Flow Konzept: QR-Code als Standard

**Kernprinzip:** Der SmartLife/Tuya Smart App QR-Code Weg ist der **STANDARD**.
Der Developer-Weg (Tuya IoT Platform) ist nur eine optionale Abzweigung für Nutzer mit bestehendem Account.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         KKT Kolbe Setup                                 │
│                                                                         │
│   📱 Einrichtung via SmartLife / Tuya Smart App                        │
│                                                                         │
│   Kein Developer Account erforderlich!                                 │
│   Der Local Key wird automatisch abgerufen.                            │
│                                                                         │
│   ┌───────────────────────────────────────────────────────────────┐    │
│   │ User Code: [________________________]                         │    │
│   │                                                               │    │
│   │ Welche App verwendest du?                                     │    │
│   │   ● SmartLife                                                 │    │
│   │   ○ Tuya Smart                                               │    │
│   └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│   ℹ️ So findest du den User Code:                                      │
│      App öffnen → Ich → ⚙️ → Konto und Sicherheit → User Code         │
│                                                                         │
│   ─────────────────────────────────────────────────────────────────    │
│                                                                         │
│   ▼ Erweiterte Optionen (optional)                                     │
│   ┌───────────────────────────────────────────────────────────────┐    │
│   │ ○ Ich habe bereits einen Tuya IoT Developer Account          │    │
│   │ ○ Manuelles Setup (IP, Device ID, Local Key bekannt)         │    │
│   └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│                                              [Weiter →]                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Flow-Diagramm: Parent-Child Pattern

```
                    ┌──────────────────────────────┐
                    │      async_step_user         │
                    │  (SmartLife QR-Code Setup)   │
                    └─────────────┬────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              │ [Standard]        │ [Erweitert]       │ [Erweitert]
              │ SmartLife         │ Developer         │ Manuell
              │ QR-Code           │ Account           │ Setup
              │                   │                   │
              ▼                   ▼                   ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │ User Code +     │  │ IoT Platform    │  │ IP/DeviceID/    │
    │ QR-Code Scan    │  │ (kein Parent)   │  │ LocalKey        │
    └────────┬────────┘  └────────┬────────┘  │ (kein Parent)   │
             │                    │           └────────┬────────┘
             ▼                    │                    │
    ┌─────────────────┐           │                    │
    │ PARENT ENTRY    │           │                    │
    │ erstellen       │           │                    │
    │ (SmartLife      │           │                    │
    │  Account)       │           │                    │
    └────────┬────────┘           │                    │
             │                    │                    │
             ▼                    ▼                    │
    ┌─────────────────────────────────────────────────┐│
    │           Geräte auswählen                      ││
    │   (Multi-Select: alle Geräte auf einmal)       ││
    └─────────────────────┬───────────────────────────┘│
                          │                            │
                          ▼                            │
    ┌─────────────────────────────────────────────────┐│
    │    Für jedes gewählte Gerät:                    ││
    │    CHILD ENTRY erstellen                        │◄┘
    │    (referenziert Parent)                        │
    └─────────────────────────────────────────────────┘

                    ┌──────────────────────────────┐
                    │   Später: Gerät hinzufügen   │
                    │   (über Parent Options Flow) │
                    │   → kein neuer QR-Scan nötig │
                    └──────────────────────────────┘
```

**Wichtige Unterschiede:**

| Szenario | Entry-Typ | Parent nötig? |
|----------|-----------|---------------|
| SmartLife Setup | Parent + Child(ren) | Ja, Parent wird erstellt |
| IoT Platform | Device Entry | Nein (standalone) |
| Manuell | Device Entry | Nein (standalone) |
| Gerät nachträglich hinzufügen | Child Entry | Nutzt bestehenden Parent |

### 3.4 SmartLife vs. Tuya Smart App

> **Beide Apps sind funktional identisch!** Die Unterschiede sind nur regional/Marketing-bedingt.

| Aspekt | SmartLife | Tuya Smart |
|--------|-----------|------------|
| Verbreitung | Europa, USA | Asien, global |
| App Store Name | "Smart Life" | "Tuya Smart" |
| Logo | Grün | Blau |
| Backend | Tuya Cloud | Tuya Cloud |
| API | Identisch | Identisch |
| User Code | ✅ Vorhanden | ✅ Vorhanden |
| QR-Login | ✅ Unterstützt | ✅ Unterstützt |

**Im Code:** Der `app_schema` Parameter bestimmt die App:
- `"smartlife"` → SmartLife App
- `"tuyaSmart"` → Tuya Smart App

### 3.3 SmartLife Setup Flow

```
Schritt 1: User Code Eingabe
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  📱 SmartLife/Tuya App Setup                               │
│                                                             │
│  So findest du deinen User Code:                           │
│                                                             │
│  1. Öffne die SmartLife oder Tuya Smart App               │
│  2. Gehe zu: Ich → ⚙️ Einstellungen                        │
│  3. Tippe auf "Konto und Sicherheit"                       │
│  4. Scrolle nach unten zu "User Code"                      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ User Code: [________________________]               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ App auswählen:                                      │   │
│  │   ○ SmartLife (Standard)                           │   │
│  │   ○ Tuya Smart                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│                                    [Weiter →]              │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Schritt 2: QR-Code Scannen
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  📷 QR-Code scannen                                        │
│                                                             │
│  Scanne diesen Code mit der SmartLife/Tuya App:           │
│                                                             │
│        ┌───────────────────────────────┐                   │
│        │ ██████████████████████████████│                   │
│        │ ██                          ██│                   │
│        │ ██  ████████    ████████  ██│                   │
│        │ ██  ██    ██    ██    ██  ██│                   │
│        │ ██  ██    ██    ██    ██  ██│                   │
│        │ ██  ████████    ████████  ██│                   │
│        │ ██                          ██│                   │
│        │ ██████████████████████████████│                   │
│        └───────────────────────────────┘                   │
│                                                             │
│  ℹ️ In der App: Ich → QR-Code Symbol (oben rechts)         │
│                                                             │
│  ⏳ Warte auf Bestätigung in der App...                    │
│     [████████████░░░░░░░░] 60s                             │
│                                                             │
│                         [Abbrechen]                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Schritt 3: Geräte auswählen (Multi-Select)
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ✅ SmartLife Account verbunden!                           │
│                                                             │
│  Wähle die Geräte, die du hinzufügen möchtest:            │
│  (Du kannst mehrere auswählen)                             │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ☑ HERMES Dunstabzugshaube                          │   │
│  │   IP: 192.168.1.50                                 │   │
│  │   Local Key: ✅ Abgerufen                          │   │
│  │   Status: 🟢 Online                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ☑ IND7705HC Kochfeld                               │   │
│  │   IP: 192.168.1.51                                 │   │
│  │   Local Key: ✅ Abgerufen                          │   │
│  │   Status: 🟢 Online                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ℹ️ Es werden erstellt:                                    │
│     • 1× SmartLife Account (für Token-Verwaltung)         │
│     • 2× Geräte-Einträge (mit allen Entities)             │
│                                                             │
│  💡 Weitere Geräte können später über den Account         │
│     hinzugefügt werden - ohne erneuten QR-Scan!           │
│                                                             │
│                              [Hinzufügen →]                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 KKT Kolbe Geräte-Filterung

**Problem:** Nutzer, die bereits die Core Tuya Integration verwenden, haben viele SmartLife-Geräte. Wir wollen nur KKT Kolbe Geräte anzeigen, nicht alle.

#### 3.4.1 Erkennungsmethoden (Priorität)

| Priorität | Methode | Feld | Beispiel | Zuverlässigkeit |
|-----------|---------|------|----------|-----------------|
| 1 | **product_id Match** | `product_names` in KNOWN_DEVICES | `"ypaixllljc2dcpae"` | ✅ Höchste |
| 2 | **device_id Pattern** | `device_id_patterns` | `"bf735dfe2ad64fba7c"` | ✅ Hoch |
| 3 | **model_id Match** | `model_id` | `"e1k6i0zo"`, `"edjszs"` | ✅ Hoch |
| 4 | **product_name Prefix** | `product_name.startswith("KKT")` | `"KKT Kolbe HERMES"` | ✅ **NEU** |
| 5 | **Tuya Kategorie** | `category` | `"yyj"`, `"dcl"` | ⚠️ Zu generisch |

> **Wichtig:** Die `tuya_sharing` SDK liefert das `product_name` Attribut direkt!
> Laut Nutzer-Feedback beginnen **alle KKT Kolbe Produkte** mit `"KKT "`.

#### 3.4.1.1 Fallback: product_name mit "KKT" Prefix (Unbekannte Modelle)

**Anwendungsfall:** Neues KKT-Gerät, das noch nicht in KNOWN_DEVICES ist.

```python
# CustomerDevice Attribute aus tuya_sharing SDK
device.product_id    # "newproductid123" (Tuya ID - evtl. noch nicht bekannt)
device.product_name  # "KKT Kolbe NEW MODEL" ✅ Startet mit "KKT"!
device.category      # "yyj"
device.local_key     # "..." (für lokale Steuerung)
```

**Erkennungslogik:**

```python
def _is_kkt_device(device: CustomerDevice) -> tuple[bool, str | None]:
    """
    Check if device is a KKT Kolbe device.

    Returns:
        tuple: (is_kkt, device_type_key or None)
        - (True, "hermes_style_hood") = Bekanntes Gerät
        - (True, None) = KKT-Gerät aber unbekanntes Modell
        - (False, None) = Kein KKT-Gerät
    """
    # Method 1: Match by product_id (exact match in KNOWN_DEVICES)
    if device.product_id:
        for device_key, info in KNOWN_DEVICES.items():
            if device.product_id in info.get("product_names", []):
                return (True, device_key)

    # Method 2: Match by device_id pattern
    device_info = find_device_by_device_id(device.id)
    if device_info:
        return (True, device_info.get("model_id"))

    # Method 3: NEW - Check product_name prefix
    # All KKT Kolbe devices start with "KKT "
    if device.product_name and device.product_name.upper().startswith("KKT"):
        _LOGGER.info(
            f"Found KKT device by product_name: {device.product_name} "
            f"(product_id={device.product_id} not in KNOWN_DEVICES)"
        )
        return (True, None)  # KKT device, but unknown model

    return (False, None)  # Not a KKT device
```

**Flow bei unbekanntem KKT-Gerät:**

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ℹ️ Neues KKT Kolbe Gerät erkannt                          │
│                                                             │
│  Das Gerät "KKT Kolbe NEW MODEL" wurde gefunden, aber      │
│  ist noch nicht in der Geräte-Datenbank.                   │
│                                                             │
│  Bitte wähle den passenden Gerätetyp:                      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ○ HERMES & STYLE Hood (RGB-Beleuchtung, 5 Stufen)  │   │
│  │ ○ FLAT Hood (Einfache Beleuchtung, 5 Stufen)       │   │
│  │ ○ SOLO/ECCO HCM Hood (9 Stufen, Filter-Tracking)   │   │
│  │ ○ IND7705HC Cooktop (5-Zonen Induktion)            │   │
│  │ ○ Default Hood (Generisch)                         │   │
│  │ ○ Gerät nicht unterstützt                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  💡 Wähle "Default Hood" wenn du unsicher bist.            │
│     Die meisten Funktionen sollten funktionieren.          │
│                                                             │
│                              [Weiter →]                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Datenstruktur für unbekanntes KKT-Gerät:**

```python
# Config Entry Data für unbekanntes KKT-Gerät
{
    "device_id": "bf...",
    "local_key": "...",
    "ip_address": "192.168.1.50",
    "device_type": "hermes_style_hood",  # User-selected fallback type
    "product_name": "KKT Kolbe NEW MODEL",  # Original product_name from API
    "product_id": "newproductid123",  # Für spätere KNOWN_DEVICES Ergänzung
    "detected_by": "product_name_prefix",  # Tracking how it was detected
    "is_unknown_model": True,  # Flag für potenzielle Issues
}
```

#### 3.4.2 Bestehende Erkennungsfunktion

Die Funktion `detect_device_type()` in `config_flow.py:71` implementiert bereits diese Logik:

```python
def detect_device_type(device: dict) -> tuple[str, str] | None:
    """Detect KKT Kolbe device type from Tuya API device data."""
    product_id = device.get("product_id", "")
    device_id = device.get("id", "")

    # Method 1: Match by Tuya product_id (most accurate)
    if product_id:
        device_info = find_device_by_product_name(product_id)
        if device_info:
            for device_key, info in KNOWN_DEVICES.items():
                if product_id in info.get("product_names", []):
                    return (device_key, product_id)

    # Method 2: Match by device_id pattern
    device_info = find_device_by_device_id(device_id)
    if device_info:
        return (device_info.get("model_id", "unknown"), device_id)

    return None  # Not a KKT device
```

#### 3.4.3 Filterung im SmartLife Flow

```python
async def _filter_kkt_devices(self, all_devices: list[TuyaSharingDevice]) -> list[TuyaSharingDevice]:
    """Filter devices to only show KKT Kolbe devices."""
    kkt_devices = []

    for device in all_devices:
        device_dict = {
            "product_id": device.product_id,
            "id": device.device_id,
            "category": device.category,
            "name": device.name,
        }

        # Use existing detection logic
        detected = detect_device_type(device_dict)
        if detected:
            device_key, product_name = detected
            device.kkt_device_type = device_key  # Store for later use
            device.kkt_product_name = product_name
            kkt_devices.append(device)
        else:
            _LOGGER.debug(
                f"Skipping non-KKT device: {device.name} "
                f"(product_id={device.product_id}, category={device.category})"
            )

    if not kkt_devices:
        _LOGGER.warning(
            f"No KKT Kolbe devices found in {len(all_devices)} SmartLife devices"
        )
    else:
        _LOGGER.info(
            f"Found {len(kkt_devices)} KKT Kolbe devices out of {len(all_devices)} total"
        )

    return kkt_devices
```

#### 3.4.4 UI bei keinen KKT Geräten

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ⚠️ Keine KKT Kolbe Geräte gefunden                        │
│                                                             │
│  In deinem SmartLife Account wurden 12 Geräte gefunden,    │
│  aber keines davon ist ein bekanntes KKT Kolbe Gerät.      │
│                                                             │
│  Mögliche Ursachen:                                        │
│  • Gerät ist mit einem anderen Account verknüpft           │
│  • Gerät ist ein neues, noch unbekanntes Modell            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Gerät manuell hinzufügen                            │   │
│  │ (Device ID und Local Key aus SmartLife kopieren)    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Alle Tuya-Geräte anzeigen (Fortgeschritten)         │   │
│  │ ⚠️ Nur für Entwickler - nicht alle Geräte werden    │   │
│  │    von dieser Integration unterstützt               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│                         [Zurück]                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 3.4.5 Bekannte KKT Kolbe Product IDs

| Gerät | product_id | model_id | Kategorie |
|-------|------------|----------|-----------|
| HERMES & STYLE Hood | `ypaixllljc2dcpae` | `e1k6i0zo` | yyj |
| FLAT Hood | `luoxakxm2vm9azwu` | `luoxakxm2vm9azwu` | yyj |
| HERMES Hood | (wird gemeldet) | `0fcj8kha86svfmve` | yyj |
| SOLO HCM Hood | `bgvbvjwomgbisd8x` | `edjszs` | yyj |
| ECCO HCM Hood | `gwdgkteknzvsattn` | `edjsx0` | yyj |
| IND7705HC Cooktop | `p8volecsgzdyun29` | `e1kc5q64` | dcl |

---

## 4. Implementierungsschritte

### Phase 1: Grundlagen (Dependency & Constants)

#### 4.1.1 manifest.json aktualisieren

```json
{
  "domain": "kkt_kolbe",
  "name": "KKT Kolbe Integration",
  "requirements": [
    "tinytuya>=1.14.0",
    "pycryptodome>=3.19.0",
    "aiohttp>=3.9.0",
    "tuya-device-sharing-sdk>=0.2.0"
  ],
  "version": "4.0.0"
}
```

#### 4.1.2 const.py erweitern

```python
# === SMARTLIFE/TUYA SHARING CONFIGURATION ===
# Client ID for Home Assistant integration (fixed by Tuya)
SMARTLIFE_CLIENT_ID: Final = "HA_3y9q8zge868vdm7k"

# App schemas
SMARTLIFE_SCHEMA: Final = "smartlife"
TUYA_SMART_SCHEMA: Final = "tuyaSmart"

# QR Code format
QR_CODE_FORMAT: Final = "tuyaSmart--qrLogin?token={token}"

# Polling configuration
QR_LOGIN_POLL_INTERVAL: Final = 2  # seconds
QR_LOGIN_TIMEOUT: Final = 120  # seconds (2 minutes)

# Token cache keys
CONF_SMARTLIFE_TOKEN_INFO: Final = "smartlife_token_info"
CONF_SMARTLIFE_TERMINAL_ID: Final = "smartlife_terminal_id"
CONF_SMARTLIFE_ENDPOINT: Final = "smartlife_endpoint"
CONF_SMARTLIFE_USER_CODE: Final = "smartlife_user_code"

# Setup modes
SETUP_MODE_SMARTLIFE: Final = "smartlife"
SETUP_MODE_DISCOVERY: Final = "discovery"
SETUP_MODE_IOT_PLATFORM: Final = "iot_platform"
SETUP_MODE_MANUAL: Final = "manual"
```

### Phase 2: TuyaSharingClient Implementierung

#### 4.2.1 clients/tuya_sharing_client.py erstellen

```python
"""Tuya Sharing SDK Client for SmartLife/Tuya App QR-Code authentication."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant

from ..const import (
    QR_CODE_FORMAT,
    QR_LOGIN_POLL_INTERVAL,
    QR_LOGIN_TIMEOUT,
    SMARTLIFE_CLIENT_ID,
    SMARTLIFE_SCHEMA,
    TUYA_SMART_SCHEMA,
)
from ..exceptions import (
    KKTAuthenticationError,
    KKTConnectionError,
    KKTTimeoutError,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class TuyaSharingDevice:
    """Represents a device discovered via Tuya Sharing SDK."""

    device_id: str
    name: str
    local_key: str
    category: str
    product_id: str
    product_name: str
    ip: str | None
    online: bool
    support_local: bool

    @classmethod
    def from_customer_device(cls, device: Any) -> TuyaSharingDevice:
        """Create from tuya_sharing.CustomerDevice."""
        return cls(
            device_id=device.id,
            name=device.name,
            local_key=getattr(device, "local_key", "") or "",
            category=device.category,
            product_id=device.product_id,
            product_name=getattr(device, "product_name", ""),
            ip=getattr(device, "ip", None),
            online=getattr(device, "online", False),
            support_local=getattr(device, "support_local", True),
        )


@dataclass
class TuyaSharingAuthResult:
    """Authentication result from QR code login."""

    terminal_id: str
    endpoint: str
    access_token: str
    refresh_token: str
    expire_time: int
    uid: str
    timestamp: int


class TuyaSharingClient:
    """Client for SmartLife/Tuya App QR-Code authentication.

    This client uses the tuya-device-sharing-sdk to authenticate
    via QR code scanning without requiring a Tuya IoT Developer account.

    Flow:
    1. User provides their User Code from SmartLife/Tuya app
    2. Client generates QR code token
    3. User scans QR code with app
    4. User authorizes in app
    5. Client retrieves auth tokens and device list with local_keys

    Reference: https://github.com/make-all/tuya-local
    """

    def __init__(
        self,
        hass: HomeAssistant,
        user_code: str,
        app_schema: str = SMARTLIFE_SCHEMA,
    ) -> None:
        """Initialize the client.

        Args:
            hass: Home Assistant instance
            user_code: User code from SmartLife/Tuya app
            app_schema: "smartlife" or "tuyaSmart"
        """
        self.hass = hass
        self.user_code = user_code
        self.app_schema = app_schema
        self._login_control: Any = None
        self._manager: Any = None
        self._qr_token: str | None = None
        self._auth_result: TuyaSharingAuthResult | None = None

    async def async_generate_qr_code(self) -> str:
        """Generate QR code for authentication.

        Returns:
            QR code string in format "tuyaSmart--qrLogin?token=xxx"

        Raises:
            KKTConnectionError: If unable to connect to Tuya cloud
            KKTAuthenticationError: If user_code is invalid
        """
        from tuya_sharing import LoginControl

        def _generate() -> dict[str, Any]:
            self._login_control = LoginControl()
            return self._login_control.qr_code(
                SMARTLIFE_CLIENT_ID,
                self.app_schema,
                self.user_code,
            )

        try:
            response = await self.hass.async_add_executor_job(_generate)
        except Exception as err:
            raise KKTConnectionError(
                operation="qr_code_generation",
                reason=str(err),
            ) from err

        if not response.get("success"):
            error_code = response.get("code", "unknown")
            error_msg = response.get("msg", "Unknown error")
            raise KKTAuthenticationError(
                message=f"QR code generation failed: {error_msg} (code: {error_code})",
            )

        self._qr_token = response.get("result", {}).get("qrcode")
        if not self._qr_token:
            raise KKTAuthenticationError(
                message="No QR token in response",
            )

        return QR_CODE_FORMAT.format(token=self._qr_token)

    async def async_poll_login_result(
        self,
        timeout: float = QR_LOGIN_TIMEOUT,
    ) -> TuyaSharingAuthResult:
        """Poll for QR code scan and authorization result.

        Args:
            timeout: Maximum time to wait for authorization (seconds)

        Returns:
            Authentication result with tokens

        Raises:
            KKTTimeoutError: If user doesn't scan/authorize within timeout
            KKTAuthenticationError: If authorization fails
        """
        if not self._qr_token or not self._login_control:
            raise KKTAuthenticationError(
                message="Must call async_generate_qr_code first",
            )

        def _poll() -> tuple[bool, dict[str, Any]]:
            return self._login_control.login_result(
                self._qr_token,
                SMARTLIFE_CLIENT_ID,
                self.user_code,
            )

        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                raise KKTTimeoutError(
                    operation="qr_login",
                    timeout=timeout,
                )

            try:
                success, result = await self.hass.async_add_executor_job(_poll)
            except Exception as err:
                _LOGGER.debug("Poll error (retrying): %s", err)
                await asyncio.sleep(QR_LOGIN_POLL_INTERVAL)
                continue

            if success:
                token_info = result.get("token_info", {})
                self._auth_result = TuyaSharingAuthResult(
                    terminal_id=result.get("terminal_id", ""),
                    endpoint=result.get("endpoint", ""),
                    access_token=token_info.get("access_token", ""),
                    refresh_token=token_info.get("refresh_token", ""),
                    expire_time=token_info.get("expire_time", 0),
                    uid=token_info.get("uid", ""),
                    timestamp=result.get("t", 0),
                )
                _LOGGER.info("QR code login successful")
                return self._auth_result

            # Check for specific error codes
            error_code = result.get("code")
            if error_code == "login_failed":
                raise KKTAuthenticationError(
                    message="User denied authorization",
                )

            # Not yet authorized, continue polling
            await asyncio.sleep(QR_LOGIN_POLL_INTERVAL)

    async def async_get_devices(self) -> list[TuyaSharingDevice]:
        """Get all devices with local keys after authentication.

        Returns:
            List of devices with local_key populated

        Raises:
            KKTAuthenticationError: If not authenticated
            KKTConnectionError: If unable to fetch devices
        """
        if not self._auth_result:
            raise KKTAuthenticationError(
                message="Must authenticate first via QR code",
            )

        from tuya_sharing import Manager, SharingTokenListener

        class TokenListener(SharingTokenListener):
            """Token update listener."""

            def __init__(self, client: TuyaSharingClient):
                self.client = client

            def update_token(self, token_info: dict[str, Any]) -> None:
                """Handle token updates."""
                if self.client._auth_result:
                    self.client._auth_result.access_token = token_info.get(
                        "access_token", ""
                    )
                    self.client._auth_result.refresh_token = token_info.get(
                        "refresh_token", ""
                    )
                    self.client._auth_result.expire_time = token_info.get(
                        "expire_time", 0
                    )

        def _init_manager() -> Any:
            token_info = {
                "access_token": self._auth_result.access_token,
                "refresh_token": self._auth_result.refresh_token,
                "expire_time": self._auth_result.expire_time,
                "uid": self._auth_result.uid,
            }
            return Manager(
                SMARTLIFE_CLIENT_ID,
                self.user_code,
                self._auth_result.terminal_id,
                self._auth_result.endpoint,
                token_info,
                TokenListener(self),
            )

        def _fetch_devices() -> list[Any]:
            self._manager.update_device_cache()
            return list(self._manager.device_map.values())

        try:
            self._manager = await self.hass.async_add_executor_job(_init_manager)
            devices = await self.hass.async_add_executor_job(_fetch_devices)
        except Exception as err:
            raise KKTConnectionError(
                operation="fetch_devices",
                reason=str(err),
            ) from err

        result = []
        for device in devices:
            sharing_device = TuyaSharingDevice.from_customer_device(device)

            # Log local key availability
            if sharing_device.local_key:
                _LOGGER.debug(
                    "Device %s (%s): local_key available",
                    sharing_device.name,
                    sharing_device.device_id[:8],
                )
            else:
                _LOGGER.warning(
                    "Device %s (%s): local_key NOT available (hub or restricted device)",
                    sharing_device.name,
                    sharing_device.device_id[:8],
                )

            result.append(sharing_device)

        return result

    async def async_get_kkt_devices(self) -> list[TuyaSharingDevice]:
        """Get only KKT Kolbe devices (hoods and cooktops).

        Filters devices by category:
        - yyj: Dunstabzugshaube (Hood)
        - dcl: Induktionskochfeld (Cooktop)

        Returns:
            List of KKT Kolbe devices
        """
        all_devices = await self.async_get_devices()

        kkt_categories = {"yyj", "dcl"}
        kkt_devices = [
            d for d in all_devices
            if d.category.lower() in kkt_categories
        ]

        _LOGGER.info(
            "Found %d KKT Kolbe devices out of %d total devices",
            len(kkt_devices),
            len(all_devices),
        )

        return kkt_devices

    def get_token_info_for_storage(self) -> dict[str, Any]:
        """Get token info for storage in config entry.

        Returns:
            Dictionary with all auth info for later restoration
        """
        if not self._auth_result:
            return {}

        return {
            "terminal_id": self._auth_result.terminal_id,
            "endpoint": self._auth_result.endpoint,
            "access_token": self._auth_result.access_token,
            "refresh_token": self._auth_result.refresh_token,
            "expire_time": self._auth_result.expire_time,
            "uid": self._auth_result.uid,
            "user_code": self.user_code,
            "app_schema": self.app_schema,
            "timestamp": self._auth_result.timestamp,
        }

    @classmethod
    async def async_from_stored_tokens(
        cls,
        hass: HomeAssistant,
        token_info: dict[str, Any],
    ) -> TuyaSharingClient:
        """Create client from stored tokens.

        Args:
            hass: Home Assistant instance
            token_info: Stored token info from get_token_info_for_storage()

        Returns:
            Initialized client with restored authentication
        """
        client = cls(
            hass=hass,
            user_code=token_info.get("user_code", ""),
            app_schema=token_info.get("app_schema", SMARTLIFE_SCHEMA),
        )

        client._auth_result = TuyaSharingAuthResult(
            terminal_id=token_info.get("terminal_id", ""),
            endpoint=token_info.get("endpoint", ""),
            access_token=token_info.get("access_token", ""),
            refresh_token=token_info.get("refresh_token", ""),
            expire_time=token_info.get("expire_time", 0),
            uid=token_info.get("uid", ""),
            timestamp=token_info.get("timestamp", 0),
        )

        return client

    async def async_close(self) -> None:
        """Close the client and cleanup resources."""
        if self._manager:
            try:
                await self.hass.async_add_executor_job(self._manager.unload)
            except Exception as err:
                _LOGGER.debug("Error unloading manager: %s", err)
        self._manager = None
        self._login_control = None
```

### Phase 3: Config Flow Erweiterung

#### 4.3.1 Config Flow Steps für SmartLife

Die folgenden Steps müssen zu `config_flow.py` hinzugefügt werden:

```python
# In config_flow.py - neue Imports
from homeassistant.helpers.selector import (
    QrCodeSelector,
    QrCodeSelectorConfig,
    QrErrorCorrectionLevel,
)
from .clients.tuya_sharing_client import TuyaSharingClient, TuyaSharingDevice
from .const import (
    SETUP_MODE_SMARTLIFE,
    SETUP_MODE_DISCOVERY,
    SETUP_MODE_IOT_PLATFORM,
    SETUP_MODE_MANUAL,
    SMARTLIFE_SCHEMA,
    TUYA_SMART_SCHEMA,
    CONF_SMARTLIFE_TOKEN_INFO,
)


class KKTKolbeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KKT Kolbe."""

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        # SmartLife state
        self._smartlife_client: TuyaSharingClient | None = None
        self._smartlife_qr_code: str | None = None
        self._smartlife_devices: list[TuyaSharingDevice] = []
        self._selected_device: TuyaSharingDevice | None = None
        # ... existing state

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step - QR-Code setup as DEFAULT.

        The SmartLife/Tuya Smart App QR-Code method is the STANDARD.
        Developer and Manual options are only available via "Erweiterte Optionen".
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if user selected an advanced option
            advanced_mode = user_input.get("advanced_mode")

            if advanced_mode == "developer":
                # Redirect to existing Developer/IoT Platform flow
                return await self.async_step_api_config()
            elif advanced_mode == "manual":
                # Redirect to manual setup
                return await self.async_step_manual()

            # DEFAULT: SmartLife/Tuya Smart App QR-Code Setup
            user_code = user_input.get("user_code", "").strip()
            app_schema = user_input.get("app_schema", SMARTLIFE_SCHEMA)

            if not user_code:
                errors["user_code"] = "user_code_required"
            else:
                # Initialize client and generate QR code
                self._smartlife_client = TuyaSharingClient(
                    self.hass,
                    user_code,
                    app_schema,
                )

                try:
                    self._smartlife_qr_code = await self._smartlife_client.async_generate_qr_code()
                    return await self.async_step_smartlife_scan()
                except KKTAuthenticationError as err:
                    _LOGGER.error("User code invalid: %s", err)
                    errors["user_code"] = "invalid_user_code"
                except KKTConnectionError as err:
                    _LOGGER.error("Connection error: %s", err)
                    errors["base"] = "cannot_connect"

        # QR-Code Setup as DEFAULT with optional advanced modes
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                # MAIN: SmartLife/Tuya Smart App fields (shown by default)
                vol.Required("user_code"): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required("app_schema", default=SMARTLIFE_SCHEMA): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=SMARTLIFE_SCHEMA,
                                label="SmartLife",
                            ),
                            selector.SelectOptionDict(
                                value=TUYA_SMART_SCHEMA,
                                label="Tuya Smart",
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                # OPTIONAL: Advanced modes (collapsed/expandable in UI)
                vol.Optional("advanced_mode"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value="developer",
                                label="Ich habe einen Tuya IoT Developer Account",
                            ),
                            selector.SelectOptionDict(
                                value="manual",
                                label="Manuelles Setup (IP, Device ID, Local Key bekannt)",
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            errors=errors,
            description_placeholders={
                "user_code_help": "App öffnen → Ich → ⚙️ → Konto und Sicherheit → User Code",
            },
        )

    async def async_step_smartlife_user_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Collect user code from SmartLife/Tuya app."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_code = user_input.get("user_code", "").strip()
            app_schema = user_input.get("app_schema", SMARTLIFE_SCHEMA)

            if not user_code:
                errors["user_code"] = "user_code_required"
            else:
                # Initialize client and generate QR code
                self._smartlife_client = TuyaSharingClient(
                    self.hass,
                    user_code,
                    app_schema,
                )

                try:
                    self._smartlife_qr_code = await self._smartlife_client.async_generate_qr_code()
                    return await self.async_step_smartlife_scan()
                except KKTAuthenticationError as err:
                    _LOGGER.error("User code invalid: %s", err)
                    errors["user_code"] = "invalid_user_code"
                except KKTConnectionError as err:
                    _LOGGER.error("Connection error: %s", err)
                    errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="smartlife_user_code",
            data_schema=vol.Schema({
                vol.Required("user_code"): str,
                vol.Required("app_schema", default=SMARTLIFE_SCHEMA): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=SMARTLIFE_SCHEMA,
                                label="SmartLife",
                            ),
                            selector.SelectOptionDict(
                                value=TUYA_SMART_SCHEMA,
                                label="Tuya Smart",
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            errors=errors,
            description_placeholders={
                "user_code_instructions": "Öffne SmartLife/Tuya App → Ich → ⚙️ → Konto und Sicherheit → User Code",
            },
        )

    async def async_step_smartlife_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: Display QR code and wait for scan."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # User clicked submit - poll for result
            try:
                await self._smartlife_client.async_poll_login_result()

                # Get devices after successful authentication
                self._smartlife_devices = await self._smartlife_client.async_get_kkt_devices()

                if not self._smartlife_devices:
                    errors["base"] = "no_devices_found"
                else:
                    return await self.async_step_smartlife_select_device()

            except KKTTimeoutError:
                errors["base"] = "qr_scan_timeout"
            except KKTAuthenticationError as err:
                _LOGGER.error("Authentication failed: %s", err)
                errors["base"] = "authentication_failed"
            except KKTConnectionError as err:
                _LOGGER.error("Connection error: %s", err)
                errors["base"] = "cannot_connect"

        # Show QR code
        return self.async_show_form(
            step_id="smartlife_scan",
            data_schema=vol.Schema({
                vol.Optional("qr_code"): QrCodeSelector(
                    QrCodeSelectorConfig(
                        data=self._smartlife_qr_code,
                        scale=5,
                        error_correction_level=QrErrorCorrectionLevel.QUARTILE,
                    )
                ),
            }),
            errors=errors,
            description_placeholders={
                "scan_instructions": "Scanne den QR-Code mit der SmartLife/Tuya App und bestätige die Autorisierung",
                "qr_help": "In der App: Ich → QR-Code Symbol (oben rechts)",
            },
        )

    async def async_step_smartlife_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3: Select device to add."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_id = user_input.get("device")

            # Find selected device
            for device in self._smartlife_devices:
                if device.device_id == selected_id:
                    self._selected_device = device
                    break

            if self._selected_device:
                # Check if already configured
                await self.async_set_unique_id(self._selected_device.device_id)
                self._abort_if_unique_id_configured()

                # Try to discover local IP if not provided
                local_ip = self._selected_device.ip
                if not local_ip or not _is_private_ip(local_ip):
                    # Try mDNS/UDP discovery
                    local_ip = await _try_discover_local_ip(
                        self.hass,
                        self._selected_device.device_id,
                    )

                if not local_ip:
                    # Ask user for IP
                    return await self.async_step_smartlife_manual_ip()

                # Create config entry
                return await self._async_create_smartlife_entry(local_ip)
            else:
                errors["device"] = "device_not_found"

        # Build device options
        device_options = []
        for device in self._smartlife_devices:
            status = "🟢 Online" if device.online else "🔴 Offline"
            key_status = "✅" if device.local_key else "⚠️"
            ip_info = f" ({device.ip})" if device.ip else ""

            device_options.append(
                selector.SelectOptionDict(
                    value=device.device_id,
                    label=f"{device.name}{ip_info} - {status} - Key: {key_status}",
                )
            )

        return self.async_show_form(
            step_id="smartlife_select_device",
            data_schema=vol.Schema({
                vol.Required("device"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=device_options,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }),
            errors=errors,
            description_placeholders={
                "device_count": str(len(self._smartlife_devices)),
            },
        )

    async def async_step_smartlife_manual_ip(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3b: Manual IP entry if discovery failed."""
        errors: dict[str, str] = {}

        if user_input is not None:
            ip_address = user_input.get("ip_address", "").strip()

            if not ip_address:
                errors["ip_address"] = "ip_required"
            elif not _is_private_ip(ip_address):
                errors["ip_address"] = "invalid_ip"
            else:
                return await self._async_create_smartlife_entry(ip_address)

        return self.async_show_form(
            step_id="smartlife_manual_ip",
            data_schema=vol.Schema({
                vol.Required("ip_address"): str,
            }),
            errors=errors,
            description_placeholders={
                "device_name": self._selected_device.name if self._selected_device else "Unknown",
                "ip_help": "Die IP-Adresse findest du in deinem Router unter DHCP-Clients",
            },
        )

    async def _async_create_smartlife_entry(
        self, ip_address: str
    ) -> ConfigFlowResult:
        """Create the config entry for SmartLife device."""
        device = self._selected_device

        # Detect device type
        device_type, product_name, friendly_name = _detect_device_type_from_device_id(
            device.device_id
        )
        if device_type == "auto":
            # Try category-based detection
            if device.category == "yyj":
                device_type = "default_hood"
            elif device.category == "dcl":
                device_type = "ind7705hc_cooktop"

        # Build config data
        data = {
            CONF_IP_ADDRESS: ip_address,
            CONF_DEVICE_ID: device.device_id,
            "local_key": device.local_key,
            "device_type": device_type,
            "product_name": product_name,
            "setup_mode": SETUP_MODE_SMARTLIFE,
            CONF_SMARTLIFE_TOKEN_INFO: self._smartlife_client.get_token_info_for_storage(),
        }

        # Cleanup
        if self._smartlife_client:
            await self._smartlife_client.async_close()

        return self.async_create_entry(
            title=device.name or friendly_name,
            data=data,
        )
```

### Phase 4: Translations

#### 4.4.1 strings.json erweitern

```json
{
  "config": {
    "step": {
      "user": {
        "title": "KKT Kolbe Setup",
        "description": "Einrichtung via **SmartLife** oder **Tuya Smart** App.\n\n**Kein Developer Account erforderlich!**\nDer Local Key wird automatisch abgerufen.\n\n**So findest du den User Code:**\nApp öffnen → Ich → ⚙️ → Konto und Sicherheit → User Code",
        "data": {
          "user_code": "User Code",
          "app_schema": "Welche App verwendest du?",
          "advanced_mode": "Erweiterte Optionen (optional)"
        },
        "data_description": {
          "user_code": "Den User Code findest du in der SmartLife/Tuya Smart App unter Konto und Sicherheit",
          "app_schema": "SmartLife und Tuya Smart sind funktional identisch - wähle die App, die du installiert hast",
          "advanced_mode": "Nur für Nutzer mit bestehendem Tuya IoT Developer Account oder bekannten Gerätedaten"
        }
      },
      "smartlife_scan": {
        "title": "QR-Code scannen",
        "description": "Scanne diesen QR-Code mit der **SmartLife** oder **Tuya Smart** App:\n\n1. Öffne die App\n2. Gehe zu **Ich** (Profil-Tab)\n3. Tippe auf das **QR-Code Symbol** (oben rechts)\n4. Scanne den Code unten\n5. **Bestätige die Autorisierung** in der App\n\nKlicke dann auf **Absenden** um fortzufahren.",
        "data": {
          "qr_code": ""
        }
      },
      "smartlife_select_device": {
        "title": "Gerät auswählen",
        "description": "Verbindung erfolgreich! Es wurden {device_count} KKT Kolbe Geräte gefunden.\n\nWähle das Gerät aus, das du hinzufügen möchtest:",
        "data": {
          "device": "Gerät"
        },
        "data_description": {
          "device": "🟢 = Online, ✅ = Local Key verfügbar"
        }
      },
      "smartlife_manual_ip": {
        "title": "IP-Adresse eingeben",
        "description": "Die IP-Adresse von **{device_name}** konnte nicht automatisch ermittelt werden.\n\nBitte gib die lokale IP-Adresse manuell ein.\n\n**Tipp:** Du findest die IP in deinem Router unter DHCP-Clients oder in der SmartLife App unter Geräteinfo.",
        "data": {
          "ip_address": "IP-Adresse"
        }
      }
    },
    "error": {
      "user_code_required": "User Code ist erforderlich",
      "invalid_user_code": "Ungültiger User Code - bitte prüfe die Eingabe",
      "qr_scan_timeout": "Zeitüberschreitung - bitte scanne den QR-Code und bestätige in der App",
      "authentication_failed": "Autorisierung fehlgeschlagen - bitte versuche es erneut",
      "no_devices_found": "Keine KKT Kolbe Geräte gefunden. Stelle sicher, dass deine Geräte in der SmartLife App eingerichtet sind.",
      "device_not_found": "Gerät nicht gefunden",
      "ip_required": "IP-Adresse ist erforderlich",
      "invalid_ip": "Ungültige IP-Adresse - muss eine lokale Adresse sein (z.B. 192.168.1.100)"
    },
    "abort": {
      "already_configured": "Dieses Gerät ist bereits konfiguriert"
    }
  }
}
```

#### 4.4.2 translations/de.json erweitern

```json
{
  "config": {
    "step": {
      "user": {
        "title": "KKT Kolbe Setup",
        "description": "Einrichtung via **SmartLife** oder **Tuya Smart** App.\n\n**Kein Developer Account erforderlich!**\nDer Local Key wird automatisch abgerufen.\n\n**So findest du den User Code:**\nApp öffnen → Ich → ⚙️ → Konto und Sicherheit → User Code",
        "data": {
          "user_code": "User Code",
          "app_schema": "Welche App verwendest du?",
          "advanced_mode": "Erweiterte Optionen (optional)"
        },
        "data_description": {
          "user_code": "Den User Code findest du in der SmartLife/Tuya Smart App unter Konto und Sicherheit",
          "app_schema": "SmartLife und Tuya Smart sind funktional identisch - wähle die App, die du installiert hast",
          "advanced_mode": "Nur für Nutzer mit bestehendem Tuya IoT Developer Account oder bekannten Gerätedaten"
        }
      },
      "smartlife_scan": {
        "title": "QR-Code scannen",
        "description": "Scanne diesen QR-Code mit der **SmartLife** oder **Tuya Smart** App:\n\n1. Öffne die App\n2. Gehe zu **Ich** (Profil-Tab)\n3. Tippe auf das **QR-Code Symbol** (oben rechts)\n4. Scanne den Code unten\n5. **Bestätige die Autorisierung** in der App\n\nKlicke dann auf **Absenden** um fortzufahren.",
        "data": {
          "qr_code": ""
        }
      },
      "smartlife_select_device": {
        "title": "Gerät auswählen",
        "description": "Verbindung erfolgreich! Es wurden {device_count} KKT Kolbe Geräte gefunden.\n\nWähle das Gerät aus, das du hinzufügen möchtest:",
        "data": {
          "device": "Gerät"
        },
        "data_description": {
          "device": "🟢 = Online, ✅ = Local Key verfügbar"
        }
      },
      "smartlife_manual_ip": {
        "title": "IP-Adresse eingeben",
        "description": "Die IP-Adresse von **{device_name}** konnte nicht automatisch ermittelt werden.\n\nBitte gib die lokale IP-Adresse manuell ein.\n\n**Tipp:** Du findest die IP in deinem Router unter DHCP-Clients oder in der SmartLife App unter Geräteinfo.",
        "data": {
          "ip_address": "IP-Adresse"
        }
      }
    },
    "error": {
      "user_code_required": "User Code ist erforderlich",
      "invalid_user_code": "Ungültiger User Code - bitte prüfe die Eingabe",
      "qr_scan_timeout": "Zeitüberschreitung - bitte scanne den QR-Code und bestätige in der App",
      "authentication_failed": "Autorisierung fehlgeschlagen - bitte versuche es erneut",
      "no_devices_found": "Keine KKT Kolbe Geräte gefunden. Stelle sicher, dass deine Geräte in der SmartLife App eingerichtet sind.",
      "device_not_found": "Gerät nicht gefunden",
      "ip_required": "IP-Adresse ist erforderlich",
      "invalid_ip": "Ungültige IP-Adresse - muss eine lokale Adresse sein (z.B. 192.168.1.100)"
    },
    "abort": {
      "already_configured": "Dieses Gerät ist bereits konfiguriert"
    }
  }
}
```

#### 4.4.3 translations/en.json erweitern

```json
{
  "config": {
    "step": {
      "user": {
        "title": "KKT Kolbe Setup",
        "description": "Setup via **SmartLife** or **Tuya Smart** app.\n\n**No developer account required!**\nThe Local Key is retrieved automatically.\n\n**How to find your User Code:**\nOpen app → Me → ⚙️ → Account and Security → User Code",
        "data": {
          "user_code": "User Code",
          "app_schema": "Which app do you use?",
          "advanced_mode": "Advanced options (optional)"
        },
        "data_description": {
          "user_code": "You can find the User Code in the SmartLife/Tuya Smart app under Account and Security",
          "app_schema": "SmartLife and Tuya Smart are functionally identical - choose the app you have installed",
          "advanced_mode": "Only for users with existing Tuya IoT Developer account or known device data"
        }
      },
      "smartlife_scan": {
        "title": "Scan QR Code",
        "description": "Scan this QR code with the **SmartLife** or **Tuya Smart** app:\n\n1. Open the app\n2. Go to **Me** (Profile tab)\n3. Tap the **QR code icon** (top right)\n4. Scan the code below\n5. **Confirm the authorization** in the app\n\nThen click **Submit** to continue.",
        "data": {
          "qr_code": ""
        }
      },
      "smartlife_select_device": {
        "title": "Select Device",
        "description": "Connection successful! Found {device_count} KKT Kolbe devices.\n\nSelect the device you want to add:",
        "data": {
          "device": "Device"
        },
        "data_description": {
          "device": "🟢 = Online, ✅ = Local Key available"
        }
      },
      "smartlife_manual_ip": {
        "title": "Enter IP Address",
        "description": "The IP address for **{device_name}** could not be determined automatically.\n\nPlease enter the local IP address manually.\n\n**Tip:** You can find the IP in your router under DHCP clients or in the SmartLife app under device info.",
        "data": {
          "ip_address": "IP Address"
        }
      }
    },
    "error": {
      "user_code_required": "User Code is required",
      "invalid_user_code": "Invalid User Code - please check your input",
      "qr_scan_timeout": "Timeout - please scan the QR code and confirm in the app",
      "authentication_failed": "Authorization failed - please try again",
      "no_devices_found": "No KKT Kolbe devices found. Make sure your devices are set up in the SmartLife app.",
      "device_not_found": "Device not found",
      "ip_required": "IP address is required",
      "invalid_ip": "Invalid IP address - must be a local address (e.g. 192.168.1.100)"
    },
    "abort": {
      "already_configured": "This device is already configured"
    }
  }
}
```

---

## 5. Config Flow Design

### 5.1 Flow-Diagramm

```
                              ┌──────────────────┐
                              │   async_step_    │
                              │      user        │
                              └────────┬─────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
           ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
           │  SmartLife    │  │   Discovery   │  │  IoT Platform │
           │  (empfohlen)  │  │               │  │               │
           └───────┬───────┘  └───────┬───────┘  └───────┬───────┘
                   │                  │                  │
                   ▼                  │                  │
           ┌───────────────┐          │                  │
           │ User Code     │          │                  │
           │   eingeben    │          │                  │
           └───────┬───────┘          │                  │
                   │                  │                  │
                   ▼                  │                  │
           ┌───────────────┐          │                  │
           │  QR-Code      │          │                  │
           │  anzeigen     │          │                  │
           └───────┬───────┘          │                  │
                   │                  │                  │
                   ▼                  │                  │
           ┌───────────────┐          │                  │
           │  Auf Scan     │          │                  │
           │   warten      │◄─────────┤                  │
           └───────┬───────┘          │                  │
                   │                  │                  │
                   ▼                  ▼                  ▼
           ┌───────────────────────────────────────────────┐
           │              Gerät auswählen                  │
           └───────────────────────┬───────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │ IP gefunden?                │
                    └──────────────┬──────────────┘
                         │                │
                        Ja               Nein
                         │                │
                         │                ▼
                         │        ┌───────────────┐
                         │        │  IP manuell   │
                         │        │   eingeben    │
                         │        └───────┬───────┘
                         │                │
                         ▼                ▼
                   ┌─────────────────────────────────┐
                   │        Config Entry             │
                   │          erstellen              │
                   └─────────────────────────────────┘
```

### 5.2 Reauth Flow für SmartLife

```python
async def async_step_reauth(
    self, entry_data: Mapping[str, Any]
) -> ConfigFlowResult:
    """Handle reauth when tokens expire."""
    self._reauth_entry = self.hass.config_entries.async_get_entry(
        self.context["entry_id"]
    )

    setup_mode = entry_data.get("setup_mode")

    if setup_mode == SETUP_MODE_SMARTLIFE:
        # For SmartLife, we need to re-authenticate with QR code
        return await self.async_step_reauth_smartlife()
    else:
        # Existing reauth flows
        return await self.async_step_reauth_confirm()

async def async_step_reauth_smartlife(
    self, user_input: dict[str, Any] | None = None
) -> ConfigFlowResult:
    """Handle SmartLife reauth."""
    errors: dict[str, str] = {}

    if user_input is not None:
        # Similar to initial setup, but update existing entry
        # ... (implementation similar to smartlife_user_code)
        pass

    return self.async_show_form(
        step_id="reauth_smartlife",
        data_schema=vol.Schema({
            vol.Required("user_code"): str,
        }),
        errors=errors,
        description_placeholders={
            "device_name": self._reauth_entry.title if self._reauth_entry else "Unknown",
        },
    )
```

### 5.3 UI/UX Best Practices & HA Patterns

#### 5.3.1 Progress Indicator während QR-Scan (HA 2024.8+)

**WICHTIG:** Ab HA 2024.8 muss `progress_task` verwendet werden!

```python
async def async_step_smartlife_scan(
    self, user_input: dict[str, Any] | None = None
) -> ConfigFlowResult:
    """Show QR code and wait for scan with proper progress indicator."""

    if not hasattr(self, "_scan_task"):
        # Start background task for polling
        self._scan_task = self.hass.async_create_task(
            self._async_wait_for_qr_scan()
        )

    if not self._scan_task.done():
        # Show progress while waiting
        return self.async_show_progress(
            step_id="smartlife_scan",
            progress_action="wait_for_scan",
            progress_task=self._scan_task,  # REQUIRED in HA 2024.8+
            description_placeholders={
                "qr_code": self._smartlife_qr_code,
            },
        )

    # Task completed - check result
    try:
        result = self._scan_task.result()
        return self.async_show_progress_done(next_step_id="smartlife_select_device")
    except KKTTimeoutError:
        return self.async_show_progress_done(next_step_id="smartlife_scan_timeout")
    except Exception as err:
        _LOGGER.error("QR scan failed: %s", err)
        return self.async_show_progress_done(next_step_id="smartlife_scan_error")

async def _async_wait_for_qr_scan(self) -> TuyaSharingAuthResult:
    """Background task that polls for QR scan completion."""
    return await self._smartlife_client.async_poll_login_result(
        timeout=QR_LOGIN_TIMEOUT
    )
```

#### 5.3.2 Ein Gerät pro Config Entry (Best Practice)

**WICHTIG:** Jedes Gerät sollte seinen eigenen Config Entry haben!

```python
async def async_step_smartlife_select_device(
    self, user_input: dict[str, Any] | None = None
) -> ConfigFlowResult:
    """Select a SINGLE device to add."""

    if user_input is not None:
        device_id = user_input.get("device")
        selected_device = next(
            (d for d in self._devices if d.device_id == device_id),
            None
        )

        if selected_device:
            # Create entry for THIS device
            return self.async_create_entry(
                title=selected_device.name,
                data={
                    "device_id": selected_device.device_id,
                    "local_key": selected_device.local_key,
                    "setup_mode": SETUP_MODE_SMARTLIFE,
                    CONF_SMARTLIFE_TOKEN_INFO: self._smartlife_client.get_token_info_for_storage(),
                    # ... more config
                },
            )

    # Show dropdown with SINGLE selection (not multi-select!)
    device_options = [
        selector.SelectOptionDict(
            value=d.device_id,
            label=f"{d.name} ({d.category})",
        )
        for d in self._devices
        if d.category in SUPPORTED_CATEGORIES
    ]

    return self.async_show_form(
        step_id="smartlife_select_device",
        data_schema=vol.Schema({
            vol.Required("device"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=device_options,
                    mode=selector.SelectSelectorMode.LIST,  # Bessere UX als Dropdown
                )
            ),
        }),
        description_placeholders={
            "device_count": str(len(device_options)),
        },
    )
```

#### 5.3.3 ConfigEntryNotReady & ConfigEntryAuthFailed

**Für robuste Fehlerbehandlung in `__init__.py`:**

```python
from homeassistant.exceptions import ConfigEntryNotReady, ConfigEntryAuthFailed

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up KKT Kolbe from a config entry."""

    setup_mode = entry.data.get("setup_mode", SETUP_MODE_MANUAL)

    # Initialize SmartLife client if needed
    if setup_mode == SETUP_MODE_SMARTLIFE:
        token_info = entry.data.get(CONF_SMARTLIFE_TOKEN_INFO, {})

        try:
            smartlife_client = await TuyaSharingClient.async_from_stored_tokens(
                hass, token_info
            )
        except KKTAuthenticationError as err:
            # Token invalid/expired → triggers automatic reauth flow
            raise ConfigEntryAuthFailed(
                f"SmartLife authentication failed: {err}"
            ) from err
        except KKTConnectionError as err:
            # Network issue → HA will retry automatically
            raise ConfigEntryNotReady(
                f"Cannot connect to SmartLife cloud: {err}"
            ) from err

    # Try to connect to local device
    try:
        device = await async_connect_device(hass, entry.data)
    except KKTConnectionError as err:
        # Device offline → HA retries with exponential backoff
        raise ConfigEntryNotReady(
            f"Device not responding: {err}"
        ) from err
    except KKTAuthenticationError as err:
        # Local key invalid → trigger reauth
        raise ConfigEntryAuthFailed(
            f"Invalid local key: {err}"
        ) from err

    # ... rest of setup
```

#### 5.3.4 Reconfigure Flow für SmartLife

**Ermöglicht Änderung von Connection-Einstellungen ohne Neukonfiguration:**

```python
async def async_step_reconfigure(
    self, user_input: dict[str, Any] | None = None
) -> ConfigFlowResult:
    """Handle reconfiguration of the integration."""

    reconfigure_entry = self.hass.config_entries.async_get_entry(
        self.context["entry_id"]
    )
    setup_mode = reconfigure_entry.data.get("setup_mode")

    if user_input is not None:
        action = user_input.get("action")

        if action == "refresh_token":
            # Refresh SmartLife tokens
            return await self.async_step_reconfigure_smartlife_refresh()
        elif action == "change_ip":
            # Change device IP
            return await self.async_step_reconfigure_ip()
        elif action == "change_local_key":
            # Manual local key update
            return await self.async_step_reconfigure_local_key()

    # Show reconfigure options
    options = [
        selector.SelectOptionDict(value="change_ip", label="IP-Adresse ändern"),
        selector.SelectOptionDict(value="change_local_key", label="Local Key ändern"),
    ]

    # SmartLife-specific option
    if setup_mode == SETUP_MODE_SMARTLIFE:
        options.insert(0, selector.SelectOptionDict(
            value="refresh_token",
            label="SmartLife Token erneuern"
        ))

    return self.async_show_form(
        step_id="reconfigure",
        data_schema=vol.Schema({
            vol.Required("action"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        }),
    )
```

#### 5.3.5 Accessibility Considerations

**Für Screen Reader und kognitive Barrierefreiheit:**

```python
# In strings.json - Klare, beschreibende Texte

{
  "config": {
    "step": {
      "smartlife_user_code": {
        "title": "SmartLife App verbinden",
        "description": "Gib deinen User Code aus der SmartLife oder Tuya Smart App ein.\n\n**So findest du den Code:**\n1. Öffne die App\n2. Gehe zu 'Ich' (Profil)\n3. Tippe auf Einstellungen (⚙️)\n4. Wähle 'Konto und Sicherheit'\n5. Scrolle zu 'User Code'",
        "data": {
          "user_code": "User Code (z.B. EU12345678)",
          "app_schema": "Welche App verwendest du?"
        },
        "data_description": {
          "user_code": "Der User Code ist eine Kombination aus Buchstaben und Zahlen, z.B. EU12345678",
          "app_schema": "Wähle die App, die du auf deinem Smartphone installiert hast"
        }
      },
      "smartlife_scan": {
        "title": "QR-Code scannen",
        "description": "Scanne den unten angezeigten QR-Code mit deiner SmartLife/Tuya App.\n\n**Anleitung:**\n1. Öffne die App auf deinem Handy\n2. Tippe auf 'Ich' (Profil)\n3. Tippe auf das QR-Symbol oben rechts\n4. Richte die Kamera auf diesen Bildschirm\n5. Bestätige die Autorisierung in der App",
        "progress_action": {
          "wait_for_scan": "Warte auf QR-Code Scan... Bitte scanne den Code mit deiner App."
        }
      }
    },
    "error": {
      "qr_scan_timeout": "Der QR-Code ist abgelaufen. Bitte starte den Vorgang erneut.",
      "invalid_user_code": "Der User Code ist ungültig. Bitte überprüfe die Eingabe.",
      "cannot_connect": "Verbindung zum SmartLife Server fehlgeschlagen. Bitte prüfe deine Internetverbindung."
    }
  }
}
```

**Accessibility Checkliste:**

- [ ] Alle Formularfelder haben beschreibende Labels (`data_description`)
- [ ] Fehlermeldungen sind spezifisch und handlungsorientiert
- [ ] Keine zeitkritischen Aktionen ohne ausreichend Zeit (QR-Code: 2 Minuten)
- [ ] Alternativen für QR-Code anbieten (manueller Weg verfügbar)
- [ ] Visuelle Indikatoren haben Text-Äquivalente
- [ ] Logische Tab-Reihenfolge in Formularen

#### 5.3.6 Browser Cache Hinweis (für Entwickler)

> ⚠️ **Entwickler-Hinweis:** Nach Änderungen am Config Flow:
> - Browser-Cache leeren (Hard Refresh: Ctrl+Shift+R / Cmd+Shift+R)
> - Oder: Inkognito-Fenster verwenden
> - HA Frontend kann alte Flow-Definitionen cachen

---

## 6. API Client Implementation

### 6.1 Token Refresh Handling

```python
class TuyaSharingTokenManager:
    """Manages token refresh for SmartLife authentication."""

    def __init__(
        self,
        hass: HomeAssistant,
        token_info: dict[str, Any],
        on_token_update: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        self.hass = hass
        self._token_info = token_info
        self._on_token_update = on_token_update
        self._refresh_lock = asyncio.Lock()

    @property
    def is_token_expired(self) -> bool:
        """Check if current token is expired or about to expire."""
        expire_time = self._token_info.get("expire_time", 0)
        current_time = int(datetime.now().timestamp())
        # Refresh 5 minutes before expiry
        return current_time >= (expire_time - 300)

    async def async_ensure_valid_token(self) -> str:
        """Ensure we have a valid access token, refreshing if needed."""
        if not self.is_token_expired:
            return self._token_info.get("access_token", "")

        async with self._refresh_lock:
            # Double-check after acquiring lock
            if not self.is_token_expired:
                return self._token_info.get("access_token", "")

            await self._async_refresh_token()
            return self._token_info.get("access_token", "")

    async def _async_refresh_token(self) -> None:
        """Refresh the access token using refresh token."""
        from tuya_sharing import Manager

        # The Manager class handles token refresh internally
        # We just need to trigger an API call
        # Token updates come through the SharingTokenListener
        _LOGGER.info("Refreshing SmartLife access token")
```

### 6.2 Local Key Update Detection

```python
async def async_check_local_key_update(
    self,
    device_id: str,
    current_local_key: str,
) -> str | None:
    """Check if local key has changed (e.g., after device re-pairing).

    Returns:
        New local key if changed, None otherwise
    """
    devices = await self.async_get_devices()

    for device in devices:
        if device.device_id == device_id:
            if device.local_key and device.local_key != current_local_key:
                _LOGGER.info(
                    "Local key changed for device %s",
                    device_id[:8],
                )
                return device.local_key
            return None

    return None
```

---

## 7. Coordinator Integration

### 7.1 Coordinator mit SmartLife Fallback

```python
# In coordinator.py - erweiterte _async_update_data

async def _async_update_data(self) -> dict[str, Any]:
    """Fetch data from the device with SmartLife fallback."""

    # Try local connection first
    try:
        if await self._async_try_local_update():
            return self._dps_cache
    except KKTConnectionError:
        _LOGGER.debug("Local connection failed, trying SmartLife cloud")

    # Fallback to SmartLife cloud if configured
    if self._has_smartlife_config():
        try:
            return await self._async_smartlife_update()
        except Exception as err:
            _LOGGER.error("SmartLife cloud update failed: %s", err)

    # Both failed
    raise UpdateFailed("Unable to connect locally or via cloud")

def _has_smartlife_config(self) -> bool:
    """Check if SmartLife tokens are configured."""
    return bool(self._entry.data.get(CONF_SMARTLIFE_TOKEN_INFO))

async def _async_smartlife_update(self) -> dict[str, Any]:
    """Update via SmartLife cloud API."""
    token_info = self._entry.data.get(CONF_SMARTLIFE_TOKEN_INFO, {})

    client = await TuyaSharingClient.async_from_stored_tokens(
        self.hass,
        token_info,
    )

    try:
        devices = await client.async_get_devices()

        for device in devices:
            if device.device_id == self._device_id:
                # Update local key if changed
                if device.local_key != self._local_key:
                    await self._async_update_local_key(device.local_key)

                # Return status from cloud
                # Note: Cloud status may have different DP format
                return self._convert_cloud_status(device)

        raise UpdateFailed("Device not found in cloud")
    finally:
        await client.async_close()
```

---

## 8. Error Handling & Edge Cases

### 8.1 Error Scenarios

| Szenario | Ursache | Lösung |
|----------|---------|--------|
| `invalid_user_code` | User Code falsch eingegeben | Klare Fehlermeldung, erneute Eingabe |
| `qr_scan_timeout` | User hat nicht rechtzeitig gescannt | Timeout erhöhen (120s), Retry ermöglichen |
| `authentication_failed` | User hat Autorisierung abgelehnt | Erneuter Versuch mit neuem QR-Code |
| `no_devices_found` | Keine KKT Geräte im Account | Hinweis auf SmartLife App Setup |
| `local_key_empty` | Hub-Device oder eingeschränktes Gerät | Warnung anzeigen, trotzdem fortfahren |
| `token_expired` | Token abgelaufen | Automatische Erneuerung oder Reauth |

### 8.2 Rate Limiting

Das `tuya-device-sharing-sdk` verwendet die selben Rate Limits wie die normale Tuya API:

```python
# In const.py
SMARTLIFE_MIN_REQUEST_INTERVAL: Final = 1.0  # Sekunden zwischen Requests
SMARTLIFE_MAX_REQUESTS_PER_MINUTE: Final = 60

# Rate Limiter Implementierung
class SmartLifeRateLimiter:
    """Simple rate limiter for SmartLife API calls."""

    def __init__(self):
        self._last_request_time: float = 0
        self._request_count: int = 0
        self._minute_start: float = 0

    async def async_wait(self) -> None:
        """Wait if necessary to respect rate limits."""
        current_time = asyncio.get_event_loop().time()

        # Reset counter every minute
        if current_time - self._minute_start >= 60:
            self._request_count = 0
            self._minute_start = current_time

        # Check requests per minute
        if self._request_count >= SMARTLIFE_MAX_REQUESTS_PER_MINUTE:
            wait_time = 60 - (current_time - self._minute_start)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                self._request_count = 0
                self._minute_start = asyncio.get_event_loop().time()

        # Minimum interval between requests
        elapsed = current_time - self._last_request_time
        if elapsed < SMARTLIFE_MIN_REQUEST_INTERVAL:
            await asyncio.sleep(SMARTLIFE_MIN_REQUEST_INTERVAL - elapsed)

        self._last_request_time = asyncio.get_event_loop().time()
        self._request_count += 1
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

```python
# tests/test_tuya_sharing_client.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.kkt_kolbe.clients.tuya_sharing_client import (
    TuyaSharingClient,
    TuyaSharingDevice,
    TuyaSharingAuthResult,
)
from custom_components.kkt_kolbe.exceptions import (
    KKTAuthenticationError,
    KKTConnectionError,
    KKTTimeoutError,
)


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(side_effect=lambda f, *a: f(*a))
    return hass


@pytest.fixture
def mock_login_control():
    """Create mock LoginControl."""
    with patch("custom_components.kkt_kolbe.clients.tuya_sharing_client.LoginControl") as mock:
        instance = MagicMock()
        instance.qr_code.return_value = {
            "success": True,
            "result": {"qrcode": "test_token_123"},
        }
        instance.login_result.return_value = (True, {
            "terminal_id": "term_123",
            "endpoint": "https://api.example.com",
            "token_info": {
                "access_token": "access_123",
                "refresh_token": "refresh_123",
                "expire_time": 9999999999,
                "uid": "uid_123",
            },
            "t": 1234567890,
        })
        mock.return_value = instance
        yield mock


class TestTuyaSharingClient:
    """Test TuyaSharingClient class."""

    async def test_generate_qr_code_success(self, mock_hass, mock_login_control):
        """Test successful QR code generation."""
        client = TuyaSharingClient(mock_hass, "user_code_123")

        qr_code = await client.async_generate_qr_code()

        assert qr_code == "tuyaSmart--qrLogin?token=test_token_123"
        mock_login_control.return_value.qr_code.assert_called_once()

    async def test_generate_qr_code_invalid_user_code(self, mock_hass, mock_login_control):
        """Test QR code generation with invalid user code."""
        mock_login_control.return_value.qr_code.return_value = {
            "success": False,
            "code": "invalid_user_code",
            "msg": "User code not found",
        }

        client = TuyaSharingClient(mock_hass, "invalid_code")

        with pytest.raises(KKTAuthenticationError):
            await client.async_generate_qr_code()

    async def test_poll_login_result_success(self, mock_hass, mock_login_control):
        """Test successful login result polling."""
        client = TuyaSharingClient(mock_hass, "user_code_123")
        await client.async_generate_qr_code()

        result = await client.async_poll_login_result(timeout=5)

        assert result.terminal_id == "term_123"
        assert result.access_token == "access_123"

    async def test_poll_login_result_timeout(self, mock_hass, mock_login_control):
        """Test login result polling timeout."""
        mock_login_control.return_value.login_result.return_value = (False, {})

        client = TuyaSharingClient(mock_hass, "user_code_123")
        await client.async_generate_qr_code()

        with pytest.raises(KKTTimeoutError):
            await client.async_poll_login_result(timeout=0.1)

    async def test_get_devices_filters_kkt(self, mock_hass, mock_login_control):
        """Test that get_kkt_devices filters correctly."""
        # Setup mock manager with devices
        mock_device_hood = MagicMock()
        mock_device_hood.id = "device_hood_123"
        mock_device_hood.name = "HERMES Hood"
        mock_device_hood.local_key = "local_key_hood"
        mock_device_hood.category = "yyj"
        mock_device_hood.product_id = "product_123"
        mock_device_hood.online = True

        mock_device_other = MagicMock()
        mock_device_other.id = "device_other_456"
        mock_device_other.name = "Other Device"
        mock_device_other.local_key = "local_key_other"
        mock_device_other.category = "light"
        mock_device_other.product_id = "product_456"
        mock_device_other.online = True

        with patch("custom_components.kkt_kolbe.clients.tuya_sharing_client.Manager") as mock_manager:
            manager_instance = MagicMock()
            manager_instance.device_map = {
                "device_hood_123": mock_device_hood,
                "device_other_456": mock_device_other,
            }
            mock_manager.return_value = manager_instance

            client = TuyaSharingClient(mock_hass, "user_code_123")
            await client.async_generate_qr_code()
            await client.async_poll_login_result(timeout=5)

            kkt_devices = await client.async_get_kkt_devices()

            assert len(kkt_devices) == 1
            assert kkt_devices[0].device_id == "device_hood_123"
            assert kkt_devices[0].category == "yyj"


class TestTuyaSharingDevice:
    """Test TuyaSharingDevice dataclass."""

    def test_from_customer_device(self):
        """Test creating from CustomerDevice."""
        mock_device = MagicMock()
        mock_device.id = "device_123"
        mock_device.name = "Test Device"
        mock_device.local_key = "key_123"
        mock_device.category = "yyj"
        mock_device.product_id = "prod_123"
        mock_device.product_name = "HERMES"
        mock_device.ip = "192.168.1.100"
        mock_device.online = True
        mock_device.support_local = True

        device = TuyaSharingDevice.from_customer_device(mock_device)

        assert device.device_id == "device_123"
        assert device.local_key == "key_123"
        assert device.ip == "192.168.1.100"
```

### 9.2 Config Flow Tests

```python
# tests/test_config_flow_smartlife.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.kkt_kolbe.const import (
    DOMAIN,
    SETUP_MODE_SMARTLIFE,
)


@pytest.fixture
def mock_smartlife_client():
    """Create mock TuyaSharingClient."""
    with patch(
        "custom_components.kkt_kolbe.config_flow.TuyaSharingClient"
    ) as mock:
        instance = MagicMock()
        instance.async_generate_qr_code = AsyncMock(
            return_value="tuyaSmart--qrLogin?token=test123"
        )
        instance.async_poll_login_result = AsyncMock()
        instance.async_get_kkt_devices = AsyncMock(return_value=[
            MagicMock(
                device_id="device_123",
                name="HERMES Hood",
                local_key="key_123",
                category="yyj",
                ip="192.168.1.100",
                online=True,
            )
        ])
        instance.get_token_info_for_storage = MagicMock(return_value={
            "terminal_id": "term_123",
            "access_token": "access_123",
        })
        instance.async_close = AsyncMock()
        mock.return_value = instance
        yield mock


class TestSmartLifeConfigFlow:
    """Test SmartLife config flow."""

    async def test_full_flow_success(self, hass, mock_smartlife_client):
        """Test complete SmartLife setup flow."""
        # Step 1: Select setup mode
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"setup_mode": SETUP_MODE_SMARTLIFE},
        )
        assert result["step_id"] == "smartlife_user_code"

        # Step 2: Enter user code
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"user_code": "test_user_code", "app_schema": "smartlife"},
        )
        assert result["step_id"] == "smartlife_scan"

        # Step 3: Submit after QR scan
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
        assert result["step_id"] == "smartlife_select_device"

        # Step 4: Select device
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"device": "device_123"},
        )

        # Should create entry
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "HERMES Hood"
        assert result["data"]["local_key"] == "key_123"
```

---

## 10. README & Dokumentation Updates

### 10.1 README.md Struktur-Update

Die README sollte wie `tuya-local` strukturiert sein:

```markdown
# KKT Kolbe Home Assistant Integration

<div align="center">
  <img src="./icon.png" alt="KKT Kolbe Logo" width="128" height="128">

  ### Home Assistant Integration für KKT Kolbe Küchengeräte

  [![GitHub Release][releases-shield]][releases]
  [![HACS][hacs-shield]][hacs]
  [![License][license-shield]][license]
</div>

---

## ✨ Features

- 📱 **Einfaches Setup** via SmartLife/Tuya App QR-Code
- 🔑 **Kein Developer Account** erforderlich
- 🏠 **100% lokale Steuerung** nach Einrichtung
- ☁️ **Cloud Fallback** bei Verbindungsproblemen
- 🔄 **Automatische Local Key Updates**

## 🚀 Quick Start

### Installation via HACS

[![Open HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=moag1000&repository=HA-kkt-kolbe-integration&category=integration)

### Setup in 3 Schritten

1. **Integration hinzufügen**
   - Einstellungen → Geräte & Dienste → Integration hinzufügen
   - Suche nach "KKT Kolbe"

2. **SmartLife/Tuya App auswählen** (empfohlen)
   - Wähle "📱 SmartLife/Tuya App"
   - Gib deinen User Code ein
   - Scanne den QR-Code mit der App
   - Bestätige die Autorisierung

3. **Gerät auswählen**
   - Wähle dein KKT Gerät aus der Liste
   - Fertig!

<details>
<summary>📱 Wo finde ich den User Code?</summary>

1. Öffne die SmartLife oder Tuya Smart App
2. Gehe zu: **Ich** → ⚙️ **Einstellungen**
3. Tippe auf **Konto und Sicherheit**
4. Scrolle nach unten zu **User Code**

</details>

## 📦 Unterstützte Geräte

| Kategorie | Modelle | Status |
|-----------|---------|--------|
| 🌬️ Dunstabzugshauben | HERMES, STYLE, ECCO HCM, SOLO HCM | ✅ Vollständig |
| 🔥 Kochfelder | IND7705HC | ✅ Vollständig |

[Vollständige Geräteliste →](docs/SUPPORTED_DEVICES.md)

## 🔧 Setup-Methoden

### 📱 SmartLife/Tuya App (Empfohlen)

Die einfachste Methode - kein Tuya Developer Account erforderlich!

**Vorteile:**
- ✅ Kein Developer Account nötig
- ✅ Local Key automatisch abgerufen
- ✅ Automatische Key-Updates bei Gerät-Re-Pairing
- ✅ Setup in unter 1 Minute

**Nachteile:**
- ⚠️ Erfordert einmaligen Internet-Zugang für Setup
- ⚠️ SmartLife/Tuya App muss installiert sein

### 🔍 Automatische Erkennung

Findet KKT Geräte automatisch im lokalen Netzwerk.

**Vorteile:**
- ✅ Kein Cloud-Zugang nötig
- ✅ Funktioniert offline

**Nachteile:**
- ⚠️ Erfordert manuellen Local Key
- ⚠️ mDNS muss im Netzwerk aktiviert sein

### ☁️ Tuya IoT Platform

Für Nutzer mit bestehendem Tuya Developer Account.

**Vorteile:**
- ✅ Volle API-Kontrolle
- ✅ Mehr Debugging-Optionen

**Nachteile:**
- ⚠️ Developer Account erforderlich
- ⚠️ API-Subscription läuft nach 1 Monat ab

### 🔧 Manuell

Für Experten mit bekannter IP, Device ID und Local Key.

---

## 📚 Dokumentation

- [Unterstützte Geräte](docs/SUPPORTED_DEVICES.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Automation Beispiele](docs/AUTOMATION_EXAMPLES.md)
- [Developer Guide](docs/DEVELOPER_GUIDE.md)
- [API Referenz](docs/API_REFERENCE.md)

## 🐛 Bekannte Einschränkungen

- **Nur lokales Netzwerk:** Nach Setup funktioniert die Steuerung nur im Heimnetzwerk
- **Ein Local Key pro Gerät:** Bei Re-Pairing in der App ändert sich der Key
- **Hub-Geräte:** Einige Hub-gekoppelte Geräte haben keinen Local Key

## 🤝 Contributing

Contributions sind willkommen! Siehe [CONTRIBUTING.md](docs/CONTRIBUTING.md).

## 📄 License

MIT License - siehe [LICENSE](LICENSE).

---

**Made with ❤️ by [@moag1000](https://github.com/moag1000) & Claude Code**

Basierend auf Patterns von:
- [tuya-local](https://github.com/make-all/tuya-local)
- [LocalTuya](https://github.com/rospogrigio/localtuya)
- [HA Core Tuya](https://github.com/home-assistant/core/tree/dev/homeassistant/components/tuya)
```

### 10.2 Neue Dokumentations-Dateien

#### docs/SMARTLIFE_SETUP.md

```markdown
# SmartLife/Tuya App Setup Guide

Diese Anleitung erklärt das Setup der KKT Kolbe Integration über die SmartLife/Tuya App.

## Voraussetzungen

- SmartLife oder Tuya Smart App installiert
- KKT Kolbe Gerät in der App eingerichtet
- Home Assistant 2025.1.0 oder höher

## Schritt-für-Schritt Anleitung

### 1. User Code finden

Der User Code ist eine eindeutige Kennung deines SmartLife/Tuya Accounts.

1. Öffne die **SmartLife** oder **Tuya Smart** App
2. Gehe zu **Ich** (Profil-Tab unten)
3. Tippe auf das **⚙️ Zahnrad** (oben rechts)
4. Wähle **Konto und Sicherheit**
5. Scrolle nach unten zu **User Code**
6. Kopiere oder notiere den Code

### 2. Integration hinzufügen

1. Öffne Home Assistant
2. Gehe zu **Einstellungen** → **Geräte & Dienste**
3. Klicke auf **+ Integration hinzufügen**
4. Suche nach **KKT Kolbe**
5. Wähle **📱 SmartLife/Tuya App**

### 3. User Code eingeben

1. Gib den User Code aus Schritt 1 ein
2. Wähle deine App (SmartLife oder Tuya Smart)
3. Klicke auf **Weiter**

### 4. QR-Code scannen

1. Ein QR-Code wird angezeigt
2. Öffne die SmartLife/Tuya App auf deinem Handy
3. Gehe zu **Ich** → Tippe auf das **QR-Code Symbol** (oben rechts)
4. Scanne den angezeigten QR-Code
5. **Bestätige die Autorisierung** in der App
6. Klicke in Home Assistant auf **Absenden**

### 5. Gerät auswählen

1. Deine KKT Kolbe Geräte werden angezeigt
2. Wähle das Gerät, das du hinzufügen möchtest
3. Die IP-Adresse wird automatisch ermittelt
4. Klicke auf **Hinzufügen**

### Fertig!

Dein KKT Kolbe Gerät ist jetzt in Home Assistant verfügbar.

## Häufige Fragen

### Warum SmartLife statt Tuya IoT Platform?

Die SmartLife-Methode hat mehrere Vorteile:

| | SmartLife App | Tuya IoT Platform |
|---|---|---|
| Developer Account | ❌ Nicht nötig | ✅ Erforderlich |
| API Subscription | ❌ Nicht nötig | ⚠️ Läuft ab (1 Monat) |
| Setup-Zeit | ~1 Minute | ~15 Minuten |
| Local Key | ✅ Automatisch | ✅ Automatisch |

### Was passiert mit meinen Daten?

- Die Authentifizierung erfolgt über Tuya's offizielle Server
- Home Assistant erhält nur Zugriff auf deine Geräte
- Nach dem Setup erfolgt die Kommunikation **lokal** ohne Cloud
- Tokens werden sicher in Home Assistant gespeichert

### Mein Gerät wird nicht gefunden

Mögliche Ursachen:
1. **App**: Stelle sicher, dass das Gerät in der SmartLife/Tuya App funktioniert
2. **Kategorie**: Nur KKT Geräte (Dunstabzugshauben, Kochfelder) werden angezeigt
3. **Region**: Die App und dein Account müssen in der gleichen Region sein

### Der QR-Code funktioniert nicht

- Verwende die **richtige App** (SmartLife oder Tuya Smart - nicht beides gemischt)
- Prüfe, ob die App aktuell ist
- Versuche es mit der anderen App (z.B. Tuya Smart statt SmartLife)
```

### 10.3 Zusätzliche Dokumentations-Updates

Die folgenden Dateien müssen ebenfalls aktualisiert werden:

#### 10.3.1 info.md (HACS Info-Datei)

**Problem:** Aktuell Version 2.3.0, SmartLife nicht erwähnt.

**Änderungen:**
- Version auf 4.0.0 aktualisieren
- SmartLife als primäre Setup-Methode erwähnen
- "Kein Developer Account nötig" als Highlight

```markdown
## Home Assistant Integration für KKT Kolbe Geräte

Diese Integration bringt **KKT Kolbe Dunstabzugshauben** und **Induktionskochfelder** in Home Assistant.

### 🆕 NEU: SmartLife/Tuya App Setup

**Kein Tuya Developer Account erforderlich!**

Einfach die SmartLife oder Tuya Smart App nutzen - Local Key wird automatisch abgerufen.

### Installation

1. **HACS** → **Integrations** → **Custom repositories**
2. Repository: `https://github.com/moag1000/HA-kkt-kolbe-integration`
...
```

#### 10.3.2 TROUBLESHOOTING.md Erweiterung

**Neuer Abschnitt hinzufügen:**

```markdown
---

### 4. SmartLife/Tuya App Probleme

#### QR-Code wird nicht erkannt

**Symptome:**
- App zeigt "Unbekannter QR-Code"
- Scan-Bildschirm reagiert nicht

**Lösungen:**

1. **Richtige App verwenden:**
   - Verwende die GLEICHE App (SmartLife ODER Tuya Smart)
   - Die im Setup gewählte App muss zum Scannen verwendet werden

2. **App aktualisieren:**
   - App Store / Play Store → SmartLife/Tuya Smart → Update

3. **QR-Code Timeout:**
   - QR-Codes sind 2 Minuten gültig
   - Bei Timeout: Zurück und erneut starten

#### User Code nicht gefunden

**Symptome:**
- "User Code" Feld ist leer
- Kein User Code in App-Einstellungen

**Lösungen:**

1. **App-Einstellungen prüfen:**
   - **Ich** → ⚙️ → **Konto und Sicherheit** → **User Code**
   - Falls nicht vorhanden: App neu installieren

2. **Account-Region:**
   - Manche Regionen zeigen den User Code nicht
   - Versuch mit der anderen App (SmartLife ↔ Tuya Smart)

#### Token abgelaufen

**Symptome:**
- Integration zeigt "Re-Authentifizierung erforderlich"
- Gerät war lange offline

**Lösung:**
- Folge dem Reauth-Flow (QR-Code erneut scannen)
- Tokens werden automatisch erneuert
```

#### 10.3.3 GitHub Issue Templates

**Neue Felder in `.github/ISSUE_TEMPLATE/bug_report.yml`:**

```yaml
  - type: dropdown
    id: setup_mode
    attributes:
      label: Setup-Methode
      description: Wie wurde die Integration eingerichtet?
      options:
        - SmartLife/Tuya App (QR-Code)
        - Tuya IoT Platform (Developer Account)
        - Automatische Erkennung (mDNS)
        - Manuell (IP, Device ID, Local Key)
    validations:
      required: true

  - type: dropdown
    id: token_status
    attributes:
      label: SmartLife Token Status (falls SmartLife Setup)
      description: Falls SmartLife Setup verwendet wurde
      options:
        - Token gültig (keine Warnung in HA)
        - Token abgelaufen (Reauth-Meldung)
        - Nicht zutreffend (anderes Setup)
    validations:
      required: false
```

#### 10.3.4 RELEASE_CHECKLIST.md Erweiterung

**Neue Checks hinzufügen:**

```markdown
### SmartLife-spezifische Validierung

- [ ] SmartLife QR-Code Flow manuell getestet
  - [ ] User Code Eingabe
  - [ ] QR-Code Anzeige
  - [ ] App-Scan und Autorisierung
  - [ ] Geräteauswahl
  - [ ] Erfolgreiche Verbindung

- [ ] Reauth Flow getestet
  - [ ] Token-Ablauf simuliert
  - [ ] Reauth-Benachrichtigung erscheint
  - [ ] Erneute QR-Code Authentifizierung funktioniert

- [ ] Backwards Compatibility
  - [ ] Bestehende IoT Platform Setups funktionieren
  - [ ] Bestehende manuelle Setups funktionieren
  - [ ] Keine Breaking Changes für Automations
```

#### 10.3.5 known_configs/tinytuya_cloud_api_guide.md

**Hinweis am Anfang hinzufügen:**

```markdown
> ⚠️ **Hinweis:** Diese Anleitung beschreibt den Tuya IoT Platform Weg,
> der einen Developer Account erfordert.
>
> **Einfachere Alternative:** Nutze die [SmartLife/Tuya App Methode](../docs/SMARTLIFE_SETUP.md) -
> kein Developer Account erforderlich!
```

### 10.4 CI/CD & Validierung

#### 10.4.1 HACS Validation

Die HACS Validation erfolgt automatisch via GitHub Actions (`.github/workflows/validate.yml`).

**Lokaler Test vor Commit:**

```bash
# HACS Action lokal ausführen
docker run --rm -v $(pwd):/github/workspace ghcr.io/hacs/action:main
```

**Prüfpunkte:**
- [ ] `hacs.json` enthält gültige Konfiguration
- [ ] `manifest.json` hat alle Pflichtfelder
- [ ] Keine HACS-Warnungen in der Ausgabe

#### 10.4.2 Hassfest Validation

Hassfest prüft die Integration gegen Home Assistant Core Standards.

**Lokaler Test:**

```bash
# Hassfest lokal ausführen
pip install homeassistant
python -m homeassistant.scripts.hassfest \
    --integration-path custom_components/kkt_kolbe
```

**Kritische Prüfpunkte für SmartLife:**

1. **manifest.json Dependency:**
   ```json
   {
     "requirements": [
       "tuya-device-sharing-sdk>=0.2.0"
     ]
   }
   ```
   - SDK muss auf PyPI verfügbar sein
   - Version muss existieren

2. **Services:**
   - Keine Breaking Changes in `services.yaml`
   - Neue Services (falls vorhanden) dokumentiert

3. **Strings:**
   - Alle neuen Config Flow Steps in `strings.json`
   - Translations vollständig (de.json, en.json)

#### 10.4.3 Python Tests

```bash
# Alle Tests ausführen
pytest tests/ -v

# Nur SmartLife Tests
pytest tests/test_tuya_sharing_client.py tests/test_config_flow.py -v -k smartlife

# Mit Coverage
pytest tests/ -v --cov=custom_components/kkt_kolbe --cov-report=term-missing
```

**Minimum Coverage Ziel:** 80% für neue SmartLife-Module

#### 10.4.4 hacs.json Prüfung

Aktuelle Konfiguration:

```json
{
  "name": "KKT Kolbe Integration",
  "content_in_root": false,
  "country": ["DE", "AT", "CH"],
  "homeassistant": "2025.12.0",
  "render_readme": true
}
```

**Für SmartLife v4.0.0:**
- `homeassistant`: Bleibt bei `2025.12.0` (keine Erhöhung nötig)
- Keine weiteren Änderungen erforderlich

---

## 11. Migration & Backwards Compatibility

### 11.1 Bestehende Installationen

Bestehende Installationen mit IoT Platform oder manuellem Setup bleiben funktionsfähig:

```python
# In __init__.py - async_setup_entry

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up KKT Kolbe from a config entry."""

    setup_mode = entry.data.get("setup_mode", SETUP_MODE_MANUAL)

    if setup_mode == SETUP_MODE_SMARTLIFE:
        # Initialize SmartLife cloud client for token management
        token_info = entry.data.get(CONF_SMARTLIFE_TOKEN_INFO, {})
        if token_info:
            smartlife_client = await TuyaSharingClient.async_from_stored_tokens(
                hass, token_info
            )
            # Store for later use (e.g., local key refresh)
            hass.data[DOMAIN][entry.entry_id]["smartlife_client"] = smartlife_client

    # Continue with existing setup logic...
    # Local device connection works the same regardless of setup mode
```

### 11.2 Options Flow Update

```python
# Neue Option zum Wechsel der Setup-Methode

async def async_step_setup_mode_change(
    self, user_input: dict[str, Any] | None = None
) -> ConfigFlowResult:
    """Allow changing setup mode."""
    if user_input is not None:
        new_mode = user_input.get("setup_mode")

        if new_mode == SETUP_MODE_SMARTLIFE:
            # Redirect to SmartLife setup
            return await self.async_step_smartlife_user_code()

        # Update mode in data
        new_data = {**self.config_entry.data, "setup_mode": new_mode}
        self.hass.config_entries.async_update_entry(
            self.config_entry, data=new_data
        )
        return self.async_create_entry(title="", data={})

    return self.async_show_form(
        step_id="setup_mode_change",
        data_schema=vol.Schema({
            vol.Required(
                "setup_mode",
                default=self.config_entry.data.get("setup_mode", SETUP_MODE_MANUAL),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[...],  # Same as in async_step_user
                )
            ),
        }),
    )
```

---

## 12. Quellen & Referenzen

### 12.1 Offizielle Dokumentation

| Ressource | URL |
|-----------|-----|
| Tuya Device Sharing SDK | [GitHub](https://github.com/tuya/tuya-device-sharing-sdk) |
| Tuya Open API | [Developer Docs](https://developer.tuya.com/en/docs/cloud/device-management?id=K9g6rfntdz78a) |
| Home Assistant Config Flow | [Developer Docs](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/) |
| Home Assistant QrCodeSelector | [Docs](https://www.home-assistant.io/integrations/qr_code/) |

### 12.2 Referenz-Implementierungen

| Integration | Beschreibung | Repository |
|-------------|--------------|------------|
| **tuya-local** | QR-Code Login ohne Dev Account | [GitHub](https://github.com/make-all/tuya-local) |
| **HA Core Tuya** | Offizielle Tuya Integration | [GitHub](https://github.com/home-assistant/core/tree/dev/homeassistant/components/tuya) |
| **LocalTuya** | Lokale Tuya-Steuerung | [GitHub](https://github.com/rospogrigio/localtuya) |
| **TinyTuya** | Python Tuya Library | [GitHub](https://github.com/jasonacox/tinytuya) |

### 12.3 Community-Ressourcen

| Ressource | URL |
|-----------|-----|
| HA Community - Tuya QR | [Forum](https://community.home-assistant.io/t/tuya-integration-ha-2024-02-qr-code/686633) |
| Tuya Local Key Extraction | [Guide](https://www.remcokersten.nl/posts/get-tuya-localkey/) |
| QR Code Authorization Flow | [Tuya Docs](https://developer.tuya.com/en/docs/iot/authorization-code-page-usage?id=Kdkyz44dz6a7r) |

### 12.4 SDK-Klassen Referenz

| Klasse | Modul | Funktion |
|--------|-------|----------|
| `LoginControl` | `tuya_sharing.user` | QR-Code Authentifizierung |
| `Manager` | `tuya_sharing.manager` | Device Management |
| `CustomerDevice` | `tuya_sharing.device` | Device Model mit `local_key` |
| `CustomerApi` | `tuya_sharing.customerapi` | Authentifizierte HTTP Requests |
| `SharingTokenListener` | `tuya_sharing` | Token Update Callbacks |

---

## 13. Home Assistant Quality Tier Compliance

### 13.1 Bronze Tier (Pflicht) ✅

Die folgenden Anforderungen sind bereits in der KKT Kolbe Integration erfüllt und müssen für SmartLife erweitert werden:

| Anforderung | Status | SmartLife Implementierung |
|-------------|--------|---------------------------|
| Config Flow | ✅ Vorhanden | QR-Code als Standard hinzufügen |
| Unique IDs | ✅ Vorhanden | Bestehende unique_id Logik wiederverwenden |
| RuntimeData | ✅ Vorhanden | SmartLife Token Info zu RuntimeData hinzufügen |
| `_attr_has_entity_name` | ✅ Vorhanden | Keine Änderung nötig |
| manifest.json | ✅ Vorhanden | Dependency hinzufügen |

### 13.2 Silver Tier (Produktion) ✅

| Anforderung | Status | SmartLife Implementierung |
|-------------|--------|---------------------------|
| **Reauth Flow** | 🔄 Erweitern | `async_step_reauth_smartlife` für Token-Erneuerung |
| Options Flow | ✅ Vorhanden | Option zum Wechsel zwischen Setup-Modi |
| `async_unload_entry` | ✅ Vorhanden | SmartLife Client Cleanup hinzufügen |
| Exception-Hierarchie | ✅ Vorhanden | Bestehende Exceptions nutzen |
| Test Coverage | 🔄 Erweitern | SmartLife Client Tests hinzufügen |

#### 13.2.1 Reauth Flow Implementierung

```python
async def async_step_reauth(
    self, entry_data: Mapping[str, Any]
) -> ConfigFlowResult:
    """Handle reauth when SmartLife tokens expire."""
    self._reauth_entry = self.hass.config_entries.async_get_entry(
        self.context["entry_id"]
    )
    setup_mode = entry_data.get("setup_mode")

    if setup_mode == SETUP_MODE_SMARTLIFE:
        # SmartLife tokens expired - need new QR code scan
        return await self.async_step_reauth_smartlife()
    else:
        # Existing reauth for other setup modes
        return await self.async_step_reauth_confirm()

async def async_step_reauth_smartlife(
    self, user_input: dict[str, Any] | None = None
) -> ConfigFlowResult:
    """Reauth specifically for SmartLife token expiry."""
    errors: dict[str, str] = {}

    if user_input is not None:
        user_code = user_input.get("user_code", "").strip()
        app_schema = user_input.get("app_schema", SMARTLIFE_SCHEMA)

        if not user_code:
            errors["user_code"] = "user_code_required"
        else:
            self._smartlife_client = TuyaSharingClient(
                self.hass,
                user_code,
                app_schema,
            )

            try:
                self._smartlife_qr_code = await self._smartlife_client.async_generate_qr_code()
                return await self.async_step_reauth_smartlife_scan()
            except KKTAuthenticationError:
                errors["user_code"] = "invalid_user_code"
            except KKTConnectionError:
                errors["base"] = "cannot_connect"

    return self.async_show_form(
        step_id="reauth_smartlife",
        data_schema=vol.Schema({
            vol.Required("user_code"): str,
            vol.Required("app_schema", default=SMARTLIFE_SCHEMA): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=SMARTLIFE_SCHEMA, label="SmartLife"),
                        selector.SelectOptionDict(value=TUYA_SMART_SCHEMA, label="Tuya Smart"),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }),
        errors=errors,
        description_placeholders={
            "device_name": self._reauth_entry.title if self._reauth_entry else "Unknown",
            "reason": "Die SmartLife/Tuya Tokens sind abgelaufen. Bitte erneut authentifizieren.",
        },
    )

async def async_step_reauth_smartlife_scan(
    self, user_input: dict[str, Any] | None = None
) -> ConfigFlowResult:
    """Reauth QR code scan step."""
    errors: dict[str, str] = {}

    if user_input is not None:
        try:
            await self._smartlife_client.async_poll_login_result()

            # Update existing entry with new tokens
            new_token_info = self._smartlife_client.get_token_info_for_storage()

            new_data = {**self._reauth_entry.data}
            new_data[CONF_SMARTLIFE_TOKEN_INFO] = new_token_info

            self.hass.config_entries.async_update_entry(
                self._reauth_entry,
                data=new_data,
            )

            await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)

            return self.async_abort(reason="reauth_successful")

        except KKTTimeoutError:
            errors["base"] = "qr_scan_timeout"
        except KKTAuthenticationError:
            errors["base"] = "authentication_failed"

    return self.async_show_form(
        step_id="reauth_smartlife_scan",
        data_schema=vol.Schema({
            vol.Optional("qr_code"): QrCodeSelector(
                QrCodeSelectorConfig(
                    data=self._smartlife_qr_code,
                    scale=5,
                    error_correction_level=QrErrorCorrectionLevel.QUARTILE,
                )
            ),
        }),
        errors=errors,
    )
```

### 13.3 Gold Tier (Exzellenz) ✅

| Anforderung | Status | SmartLife Implementierung |
|-------------|--------|---------------------------|
| **Diagnostics** | ✅ Vorhanden | SmartLife Token Status hinzufügen |
| **Repairs Flow** | ✅ Vorhanden | SmartLife-spezifische Issues |
| Zeroconf Discovery | ✅ Vorhanden | Keine Änderung nötig |
| Vollständige Translations | 🔄 Erweitern | DE/EN für SmartLife Steps |
| Entity Categories | ✅ Vorhanden | Keine Änderung nötig |
| `_unrecorded_attributes` | ✅ Vorhanden | Keine Änderung nötig |
| `translation_key` | ✅ Vorhanden | Keine Änderung nötig |

#### 13.3.1 Diagnostics Erweiterung

```python
# In diagnostics.py - async_get_config_entry_diagnostics erweitern

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    # ... bestehender Code ...

    # SmartLife Token Status hinzufügen
    smartlife_token_info = entry.data.get(CONF_SMARTLIFE_TOKEN_INFO, {})
    if smartlife_token_info:
        diagnostics["smartlife"] = {
            "setup_mode": entry.data.get("setup_mode"),
            "token_status": "valid" if _is_token_valid(smartlife_token_info) else "expired",
            "token_expires_in_hours": _get_token_expiry_hours(smartlife_token_info),
            "endpoint": smartlife_token_info.get("endpoint", "N/A"),
            "app_schema": smartlife_token_info.get("app_schema", "N/A"),
            # WICHTIG: Keine sensitiven Daten wie access_token!
            "terminal_id": "REDACTED" if smartlife_token_info.get("terminal_id") else "N/A",
            "uid": "REDACTED" if smartlife_token_info.get("uid") else "N/A",
        }

    return diagnostics

def _is_token_valid(token_info: dict[str, Any]) -> bool:
    """Check if SmartLife token is still valid."""
    expire_time = token_info.get("expire_time", 0)
    current_time = int(datetime.now().timestamp())
    return current_time < expire_time

def _get_token_expiry_hours(token_info: dict[str, Any]) -> float:
    """Get hours until token expires."""
    expire_time = token_info.get("expire_time", 0)
    current_time = int(datetime.now().timestamp())
    seconds_remaining = max(0, expire_time - current_time)
    return round(seconds_remaining / 3600, 1)
```

#### 13.3.2 Repairs Flow für SmartLife

```python
# In repairs.py - SmartLife-spezifische Issues hinzufügen

SMARTLIFE_TOKEN_EXPIRED = "smartlife_token_expired"
SMARTLIFE_LOCAL_KEY_CHANGED = "smartlife_local_key_changed"

async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create a fix flow for the given issue."""
    if issue_id.startswith("smartlife_token_expired"):
        return SmartLifeTokenExpiredRepairFlow()
    elif issue_id.startswith("smartlife_local_key_changed"):
        return SmartLifeLocalKeyChangedRepairFlow()
    # ... bestehende Issues ...


class SmartLifeTokenExpiredRepairFlow(RepairsFlow):
    """Handler for SmartLife token expiry issues."""

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the first step of the repair flow."""
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
            description_placeholders={
                "info": "Die SmartLife/Tuya Tokens sind abgelaufen. Bitte starte die Re-Authentifizierung über die Integration.",
            },
        )

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle confirmation and trigger reauth."""
        # Trigger reauth flow for the affected entry
        entry_id = self.data.get("entry_id")
        if entry_id:
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if entry:
                entry.async_start_reauth(self.hass)

        return self.async_create_entry(title="", data={})
```

### 13.4 Debug & Logging

#### 13.4.1 Strukturiertes Logging für SmartLife

```python
# In clients/tuya_sharing_client.py

_LOGGER = logging.getLogger(__name__)

class TuyaSharingClient:
    """Client with comprehensive debug logging."""

    async def async_generate_qr_code(self) -> str:
        """Generate QR code with debug logging."""
        _LOGGER.debug(
            "Generating QR code for SmartLife/Tuya auth (schema=%s, user_code=%s...)",
            self.app_schema,
            self.user_code[:4] if len(self.user_code) > 4 else "***",
        )

        try:
            qr_code = await self._internal_generate_qr()
            _LOGGER.info(
                "QR code generated successfully for %s authentication",
                self.app_schema,
            )
            return qr_code
        except Exception as err:
            _LOGGER.error(
                "QR code generation failed: %s (schema=%s)",
                err,
                self.app_schema,
            )
            raise

    async def async_poll_login_result(self, timeout: float = QR_LOGIN_TIMEOUT) -> TuyaSharingAuthResult:
        """Poll with progress logging."""
        _LOGGER.debug("Starting QR login poll (timeout=%ss)", timeout)
        start_time = asyncio.get_event_loop().time()
        poll_count = 0

        while True:
            poll_count += 1
            elapsed = asyncio.get_event_loop().time() - start_time

            if elapsed >= timeout:
                _LOGGER.warning(
                    "QR login timeout after %d polls (%.1fs)",
                    poll_count,
                    elapsed,
                )
                raise KKTTimeoutError(operation="qr_login", timeout=timeout)

            success, result = await self._internal_poll()

            if success:
                _LOGGER.info(
                    "QR login successful after %d polls (%.1fs)",
                    poll_count,
                    elapsed,
                )
                return self._parse_auth_result(result)

            # Log every 10 polls to avoid spam
            if poll_count % 10 == 0:
                _LOGGER.debug(
                    "Still waiting for QR scan... (poll=%d, elapsed=%.1fs)",
                    poll_count,
                    elapsed,
                )

            await asyncio.sleep(QR_LOGIN_POLL_INTERVAL)

    async def async_get_devices(self) -> list[TuyaSharingDevice]:
        """Get devices with detailed logging."""
        _LOGGER.debug("Fetching devices from SmartLife/Tuya cloud")

        devices = await self._internal_get_devices()

        # Log device summary
        categories = {}
        for d in devices:
            categories[d.category] = categories.get(d.category, 0) + 1

        _LOGGER.info(
            "Retrieved %d devices: %s",
            len(devices),
            ", ".join(f"{k}={v}" for k, v in categories.items()),
        )

        # Warn about devices without local key
        no_key_devices = [d for d in devices if not d.local_key]
        if no_key_devices:
            _LOGGER.warning(
                "%d devices have no local_key (may be hub devices): %s",
                len(no_key_devices),
                ", ".join(d.name for d in no_key_devices),
            )

        return devices
```

#### 13.4.2 Debug Logging Konfiguration

```yaml
# configuration.yaml - Empfohlene Debug-Konfiguration
logger:
  default: info
  logs:
    custom_components.kkt_kolbe: debug
    custom_components.kkt_kolbe.clients.tuya_sharing_client: debug
    tuya_sharing: warning  # SDK ist sehr verbose
```

### 13.5 Translations für Reauth & Repairs

#### strings.json Erweiterungen

```json
{
  "config": {
    "step": {
      "reauth_smartlife": {
        "title": "SmartLife/Tuya Re-Authentifizierung",
        "description": "Die Authentifizierung für **{device_name}** ist abgelaufen.\n\nBitte gib deinen User Code erneut ein und scanne den QR-Code.",
        "data": {
          "user_code": "User Code",
          "app_schema": "App"
        }
      },
      "reauth_smartlife_scan": {
        "title": "QR-Code scannen",
        "description": "Scanne den QR-Code mit der SmartLife/Tuya Smart App, um die Verbindung wiederherzustellen."
      }
    },
    "abort": {
      "reauth_successful": "Re-Authentifizierung erfolgreich! Die Verbindung wurde wiederhergestellt."
    }
  },
  "issues": {
    "smartlife_token_expired": {
      "title": "SmartLife Token abgelaufen",
      "description": "Die SmartLife/Tuya Authentifizierung für {device_name} ist abgelaufen.\n\nBitte starte die Re-Authentifizierung, um die Verbindung wiederherzustellen."
    },
    "smartlife_local_key_changed": {
      "title": "Local Key geändert",
      "description": "Der Local Key für {device_name} hat sich geändert (z.B. nach Gerät-Neukopplung in der App).\n\nDie Integration wird den neuen Key automatisch abrufen."
    }
  }
}
```

### 13.6 Quality Tier Checkliste für SmartLife

#### Bronze (Pflicht)
- [ ] Config Flow mit QR-Code als Standard
- [ ] Unique IDs für SmartLife-Geräte
- [ ] RuntimeData mit Token Info
- [ ] manifest.json mit `tuya-device-sharing-sdk`

#### Silver (Produktion)
- [ ] Reauth Flow: `async_step_reauth_smartlife`
- [ ] Reauth Flow: `async_step_reauth_smartlife_scan`
- [ ] Options Flow: Setup-Modus Wechsel
- [ ] `async_unload_entry`: SmartLife Client Cleanup
- [ ] Unit Tests: TuyaSharingClient
- [ ] Unit Tests: Config Flow Steps
- [ ] Token Refresh Handling

#### Gold (Exzellenz)
- [ ] Diagnostics: SmartLife Token Status
- [ ] Repairs: `smartlife_token_expired`
- [ ] Repairs: `smartlife_local_key_changed`
- [ ] Vollständige DE Translations
- [ ] Vollständige EN Translations
- [ ] Debug Logging mit strukturierten Messages
- [ ] Error History für SmartLife Fehler

---

## Anhang A: Vollständige Dateiliste

### Neue Dateien

| Datei | Beschreibung |
|-------|--------------|
| `clients/__init__.py` | Package Init |
| `clients/tuya_sharing_client.py` | SmartLife/Tuya SDK Client |
| `docs/SMARTLIFE_SETUP.md` | Setup-Anleitung |
| `docs/SMARTLIFE_CLOUD_IMPLEMENTATION_PLAN.md` | Dieser Plan |

### Geänderte Dateien

| Datei | Änderungen |
|-------|------------|
| `manifest.json` | Neue Dependency `tuya-device-sharing-sdk` |
| `const.py` | SmartLife Konstanten |
| `config_flow.py` | SmartLife Setup Steps |
| `strings.json` | Neue Translations |
| `translations/de.json` | Deutsche Übersetzungen |
| `translations/en.json` | Englische Übersetzungen |
| `coordinator.py` | SmartLife Fallback Integration |
| `README.md` | Aktualisierte Dokumentation |

---

## Anhang B: Implementierungs-Checkliste

### Phase 1: Grundlagen
- [ ] `tuya-device-sharing-sdk` zu manifest.json hinzufügen
- [ ] Neue Konstanten in const.py
- [ ] clients/ Verzeichnis erstellen
- [ ] TuyaSharingClient Basis-Klasse

### Phase 2: Config Flow
- [ ] async_step_user mit Setup-Modi
- [ ] async_step_smartlife_user_code
- [ ] async_step_smartlife_scan (QR-Code)
- [ ] async_step_smartlife_select_device
- [ ] async_step_smartlife_manual_ip
- [ ] Reauth Flow für SmartLife

### Phase 3: Translations
- [ ] strings.json erweitern
- [ ] translations/de.json
- [ ] translations/en.json

### Phase 4: Coordinator Integration
- [ ] SmartLife Token Manager
- [ ] Cloud Fallback in Coordinator
- [ ] Local Key Update Detection

### Phase 5: Testing
- [ ] Unit Tests für TuyaSharingClient
- [ ] Config Flow Tests
- [ ] Integration Tests

### Phase 6: Dokumentation
- [ ] README.md aktualisieren
- [ ] docs/SMARTLIFE_SETUP.md erstellen
- [ ] CHANGELOG.md Update

### Phase 7: Release
- [ ] Version auf 4.0.0 erhöhen
- [ ] Git Tag erstellen
- [ ] GitHub Release mit Changelog

---

**Erstellt mit Claude Code**
**Letzte Aktualisierung:** 2026-01-05
