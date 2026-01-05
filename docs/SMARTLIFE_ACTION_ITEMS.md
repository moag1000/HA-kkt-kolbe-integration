# SmartLife Integration - Action Items

**Referenz:** [SMARTLIFE_CLOUD_IMPLEMENTATION_PLAN.md](./SMARTLIFE_CLOUD_IMPLEMENTATION_PLAN.md)
**Branch:** `feature/tuya-cloud-integration`
**Zielversion:** 4.0.0

---

## Phase 1: Grundlagen

### 1.1 Dependency hinzufügen
> Referenz: Plan Section 4.1.1

- [ ] `manifest.json`: `tuya-device-sharing-sdk>=0.2.0` zu requirements hinzufügen
- [ ] Version auf `4.0.0` setzen

### 1.2 Konstanten definieren
> Referenz: Plan Section 4.1.2

- [ ] `const.py`: SmartLife/Tuya Konstanten hinzufügen
  - `SMARTLIFE_CLIENT_ID`
  - `SMARTLIFE_SCHEMA`, `TUYA_SMART_SCHEMA`
  - `QR_CODE_FORMAT`, `QR_LOGIN_POLL_INTERVAL`, `QR_LOGIN_TIMEOUT`
  - `CONF_SMARTLIFE_*` Keys
  - `SETUP_MODE_*` Konstanten
  - `ENTRY_TYPE_ACCOUNT`, `ENTRY_TYPE_DEVICE` (Parent-Child Pattern)

---

## Phase 2: TuyaSharingClient

### 2.1 Client-Struktur erstellen
> Referenz: Plan Section 4.2.1, 6

- [ ] `clients/__init__.py` erstellen
- [ ] `clients/tuya_sharing_client.py` erstellen mit:
  - [ ] `TuyaSharingDevice` dataclass
  - [ ] `TuyaSharingAuthResult` dataclass
  - [ ] `TuyaSharingClient` class

### 2.2 Client-Methoden implementieren
> Referenz: Plan Section 6.1-6.4

- [ ] `async_generate_qr_code()` - QR-Token von Tuya Cloud holen
- [ ] `async_poll_login_result()` - Auf QR-Scan warten
- [ ] `async_get_devices()` - Geräteliste mit local_key abrufen
- [ ] `get_token_info_for_storage()` - Token-Daten für Config Entry
- [ ] `async_from_stored_tokens()` - Client aus gespeicherten Tokens erstellen

---

## Phase 3: Config Flow

### 3.1 Haupt-Flow (QR-Code als Standard)
> Referenz: Plan Section 5.1-5.2

- [ ] `async_step_user()` - QR-Code Setup als DEFAULT
  - User Code Eingabe
  - App-Auswahl (SmartLife/Tuya Smart)
  - "Erweiterte Optionen" für Developer/Manual

### 3.2 SmartLife Flow Steps (Parent-Child Pattern)
> Referenz: Plan Section 3.2, 3.4, 5.3

- [ ] `async_step_smartlife_scan()` - QR-Code mit Progress Indicator
  - [ ] `async_show_progress()` mit `progress_task` (HA 2024.8+)
  - [ ] Background Task für Polling
  - [ ] Timeout-Handling
- [ ] `_is_kkt_device()` - **KKT Kolbe Geräte erkennen**
  - [ ] Priorität 1: product_id Match in KNOWN_DEVICES
  - [ ] Priorität 2: device_id Pattern Match
  - [ ] Priorität 3: **product_name.startswith("KKT")** (NEU!)
  - [ ] Rückgabe: `(is_kkt, device_type_key | None)`
- [ ] `async_step_smartlife_select_device_type()` - **Gerätetyp wählen**
  - [ ] Nur anzeigen wenn `device_type_key` is None (unbekanntes Modell)
  - [ ] Liste bekannter Gerätetypen zur Auswahl
  - [ ] Speichern von `product_id` für spätere KNOWN_DEVICES Ergänzung
- [ ] UI für "Keine KKT Geräte gefunden" mit manuellem Fallback
- [ ] `async_step_smartlife_select_devices()` - **Multi-Select** für Geräte
  - [ ] Checkbox-Liste aller **gefilterten KKT** Geräte
  - [ ] Parent Entry (Account) erstellen
  - [ ] Child Entries (Devices) mit `parent_entry_id` erstellen
- [ ] `async_step_smartlife_manual_ip()` - IP manuell eingeben (falls nötig)

### 3.3 Reauth Flow
> Referenz: Plan Section 5.2, 13.2.1

- [ ] `async_step_reauth()` - Dispatch nach Setup-Modus
- [ ] `async_step_reauth_smartlife()` - User Code erneut eingeben
- [ ] `async_step_reauth_smartlife_scan()` - QR-Code erneut scannen

### 3.4 Reconfigure Flow (NEU)
> Referenz: Plan Section 5.3.4

- [ ] `async_step_reconfigure()` - Menü für Änderungen
  - [ ] SmartLife Token erneuern
  - [ ] IP-Adresse ändern
  - [ ] Local Key ändern

### 3.5 Error Handling
> Referenz: Plan Section 5.3.3

- [ ] `ConfigEntryNotReady` für Netzwerkfehler
- [ ] `ConfigEntryAuthFailed` für Token/Key-Fehler

---

## Phase 4: Translations & Accessibility

### 4.1 Deutsche Übersetzungen
> Referenz: Plan Section 5.3.5, 5.6

- [ ] `strings.json` erweitern (Config Flow Steps)
  - [ ] `data_description` für alle Felder (Accessibility!)
  - [ ] Klare, handlungsorientierte Fehlermeldungen
  - [ ] `progress_action` für QR-Scan Step
- [ ] `translations/de.json` erweitern

### 4.2 Englische Übersetzungen
> Referenz: Plan Section 5.6

- [ ] `translations/en.json` erweitern

### 4.3 Accessibility Checkliste
> Referenz: Plan Section 5.3.5

- [ ] Alle Formularfelder haben `data_description`
- [ ] Fehlermeldungen sind spezifisch und handlungsorientiert
- [ ] QR-Code Timeout: 2 Minuten (ausreichend Zeit)
- [ ] Alternative zum QR-Code vorhanden (manueller Weg)

---

## Phase 5: Integration

### 5.1 Entry Setup (Parent-Child Pattern)
> Referenz: Plan Section 3.2.4, 11.1

- [ ] `__init__.py`: Entry-Type Dispatch implementieren
  - [ ] `async_setup_entry()` prüft `entry_type` (account/device)
  - [ ] `_async_setup_account_entry()` - Token-Verwaltung, kein Device Setup
  - [ ] `_async_setup_device_entry()` - Token von Parent holen, Device verbinden
- [ ] `async_unload_entry()` mit Child-Cleanup wenn Parent entladen wird
- [ ] Token-Info in RuntimeData speichern (Account Entry)

### 5.2 Coordinator Updates
> Referenz: Plan Section 7

- [ ] Optional: Cloud-Fallback für local_key Refresh
- [ ] Token-Refresh Handling

### 5.3 Diagnostics & Repairs
> Referenz: Plan Section 13.3

- [ ] `diagnostics.py`: SmartLife Token-Status hinzufügen
- [ ] `repairs.py`: `smartlife_token_expired` Issue

---

## Phase 6: Testing

### 6.1 Unit Tests
> Referenz: Plan Section 9

- [ ] `tests/test_tuya_sharing_client.py`
  - [ ] QR-Code Generation
  - [ ] Login Polling
  - [ ] Device Retrieval
  - [ ] Token Storage/Restore

### 6.2 Config Flow Tests
> Referenz: Plan Section 9

- [ ] `tests/test_config_flow.py` erweitern
  - [ ] SmartLife User Code Step
  - [ ] QR-Code Scan Step
  - [ ] Multi-Device Selection Step
  - [ ] Parent-Child Entry Creation
  - [ ] Reauth Flow (Account Entry)
  - [ ] Child Cleanup when Parent deleted

---

## Phase 7: Dokumentation

### 7.1 Haupt-README
> Referenz: Plan Section 10

- [ ] `README.md` aktualisieren
  - [ ] SmartLife/Tuya Smart als **primäre** Setup-Methode
  - [ ] "Kein Developer Account nötig" prominent platzieren
  - [ ] Vergleichstabelle: SmartLife vs IoT Platform
  - [ ] Screenshots für QR-Code Flow
  - [ ] FAQ erweitern (SmartLife-spezifisch)

### 7.2 HACS Info-Datei
- [ ] `info.md` aktualisieren
  - [ ] Version auf 4.0.0 aktualisieren (aktuell: 2.3.0!)
  - [ ] SmartLife Setup als primäre Methode erwähnen
  - [ ] "Kein Developer Account" als Selling Point

### 7.3 Neue User Guides
- [ ] `docs/SMARTLIFE_SETUP.md` erstellen (detaillierter User Guide)
- [ ] `docs/SMARTLIFE_FAQ.md` erstellen (häufige Fragen)

### 7.4 Troubleshooting
- [ ] `TROUBLESHOOTING.md` erweitern
  - [ ] SmartLife QR-Code Probleme
  - [ ] Token-Erneuerung Troubleshooting
  - [ ] "User Code nicht gefunden" Hilfe

### 7.5 Veraltete Dokumentation
- [ ] `known_configs/tinytuya_cloud_api_guide.md`
  - [ ] Als "Alternative Methode" markieren
  - [ ] Verweis auf SmartLife als einfachere Option

### 7.6 Changelog
- [ ] `CHANGELOG.md` für v4.0.0
  - [ ] Breaking Changes (falls vorhanden)
  - [ ] Neue Features (SmartLife QR-Code)
  - [ ] Dokumentation

---

## Phase 8: GitHub & HACS

### 8.1 Issue Templates aktualisieren
- [ ] `.github/ISSUE_TEMPLATE/bug_report.yml`
  - [ ] "Setup Mode" Dropdown hinzufügen (SmartLife/IoT Platform/Manual)
  - [ ] SmartLife-spezifische Felder (Token-Status, etc.)

- [ ] `.github/ISSUE_TEMPLATE/new_device.yml`
  - [ ] SmartLife als Option für Device Discovery erwähnen

### 8.2 HACS Konfiguration
- [ ] `hacs.json` prüfen
  - [ ] `homeassistant` Version korrekt? (aktuell: 2025.12.0 ✅)
  - [ ] Keine Änderung nötig falls SmartLife abwärtskompatibel

### 8.3 Release Checklist
- [ ] `RELEASE_CHECKLIST.md` erweitern
  - [ ] SmartLife-spezifische Validierung
  - [ ] QR-Code Flow manuell testen
  - [ ] Token-Refresh testen

---

## Phase 9: Validierung & Release

### 9.1 CI/CD Validierung
- [ ] HACS Validation (`hacs/action@main`)
  - [ ] Lokal testen: `docker run --rm -v $(pwd):/github/workspace ghcr.io/hacs/action:main`
- [ ] Hassfest Validation (`home-assistant/actions/hassfest@master`)
  - [ ] manifest.json mit neuer Dependency validieren
  - [ ] Keine Breaking Changes in Service-Definitionen
- [ ] Python Tests bestehen
  - [ ] Neue SmartLife Tests enthalten

### 9.2 Manuelle Tests
- [ ] Kompletter SmartLife QR-Code Flow (Parent-Child)
  - [ ] User Code eingeben
  - [ ] QR-Code scannen
  - [ ] Mehrere Geräte auswählen (Multi-Select)
  - [ ] Account Entry (Parent) erstellt
  - [ ] Device Entries (Children) erstellt
  - [ ] Alle Verbindungen erfolgreich
- [ ] Parent-Child Lifecycle
  - [ ] Weiteres Gerät zu bestehendem Account hinzufügen
  - [ ] Account löschen → Alle Children werden entfernt
- [ ] Reauth Flow testen
  - [ ] Token-Ablauf simulieren
  - [ ] Re-Authentifizierung über Account Entry
- [ ] Bestehende Installationen (Backwards Compatibility)
  - [ ] IoT Platform Setup funktioniert weiterhin
  - [ ] Manuelles Setup funktioniert weiterhin

### 9.3 Release erstellen
- [ ] Version in allen Dateien prüfen:
  - [ ] `manifest.json` → `4.0.0`
  - [ ] `const.py` → `VERSION = "4.0.0"`
  - [ ] `info.md` → Badge aktualisiert
- [ ] Git Tag `v4.0.0`
- [ ] GitHub Release mit Changelog
- [ ] HACS Update verifizieren

---

## Quick Reference

| Phase | Geschätzter Aufwand | Abhängigkeiten |
|-------|---------------------|----------------|
| 1. Grundlagen | 15 min | - |
| 2. Client | 1-2 h | Phase 1 |
| 3. Config Flow | 2-3 h | Phase 2 |
| 4. Translations | 30 min | Phase 3 |
| 5. Integration | 1 h | Phase 3 |
| 6. Testing | 1-2 h | Phase 1-5 |
| 7. Dokumentation | 2 h | Phase 1-5 |
| 8. GitHub & HACS | 30 min | Phase 7 |
| 9. Validierung & Release | 1 h | Alles |

**Gesamt:** ~10-12 Stunden

---

## Fortschritt

| Phase | Status | Notizen |
|-------|--------|---------|
| 1. Grundlagen | ⬜ Offen | inkl. Entry Type Konstanten |
| 2. Client | ⬜ Offen | |
| 3. Config Flow | ⬜ Offen | **Parent-Child Pattern** |
| 4. Translations | ⬜ Offen | |
| 5. Integration | ⬜ Offen | Entry-Type Dispatch |
| 6. Testing | ⬜ Offen | Parent-Child Lifecycle Tests |
| 7. Dokumentation | ⬜ Offen | README, info.md, Troubleshooting, etc. |
| 8. GitHub & HACS | ⬜ Offen | Issue Templates, hacs.json, Release Checklist |
| 9. Validierung & Release | ⬜ Offen | CI/CD, Manuelle Tests, Release |

> **Architektur:** Parent-Child Entry Pattern (1 Account → N Devices)

---

## Datei-Übersicht

### Neue Dateien
| Datei | Phase |
|-------|-------|
| `clients/__init__.py` | 2 |
| `clients/tuya_sharing_client.py` | 2 |
| `docs/SMARTLIFE_SETUP.md` | 7 |
| `docs/SMARTLIFE_FAQ.md` | 7 |
| `tests/test_tuya_sharing_client.py` | 6 |

### Zu aktualisierende Dateien
| Datei | Phase | Änderungsart |
|-------|-------|--------------|
| `manifest.json` | 1 | Dependency + Version |
| `const.py` | 1 | Neue Konstanten |
| `config_flow.py` | 3 | SmartLife Steps |
| `strings.json` | 4 | Translations |
| `translations/de.json` | 4 | Translations |
| `translations/en.json` | 4 | Translations |
| `__init__.py` | 5 | SmartLife Client Init |
| `diagnostics.py` | 5 | Token-Status |
| `repairs.py` | 5 | Token-Expired Issue |
| `tests/test_config_flow.py` | 6 | SmartLife Tests |
| `README.md` | 7 | SmartLife als primär |
| `info.md` | 7 | Version + SmartLife |
| `TROUBLESHOOTING.md` | 7 | SmartLife Troubleshooting |
| `CHANGELOG.md` | 7 | v4.0.0 Eintrag |
| `RELEASE_CHECKLIST.md` | 8 | SmartLife Checks |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | 8 | Setup Mode Dropdown |
| `known_configs/tinytuya_cloud_api_guide.md` | 7 | Veraltet markieren |

---

*Letzte Aktualisierung: 2026-01-05 (Parent-Child Architektur)*
