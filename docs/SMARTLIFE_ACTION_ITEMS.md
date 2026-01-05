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

### 3.2 SmartLife Flow Steps
> Referenz: Plan Section 5.3-5.5

- [ ] `async_step_smartlife_scan()` - QR-Code anzeigen, auf Scan warten
- [ ] `async_step_smartlife_select_device()` - Gerät aus Liste wählen
- [ ] `async_step_smartlife_manual_ip()` - IP manuell eingeben (falls nötig)

### 3.3 Reauth Flow
> Referenz: Plan Section 13.2.1

- [ ] `async_step_reauth()` - Dispatch nach Setup-Modus
- [ ] `async_step_reauth_smartlife()` - User Code erneut eingeben
- [ ] `async_step_reauth_smartlife_scan()` - QR-Code erneut scannen

---

## Phase 4: Translations

### 4.1 Deutsche Übersetzungen
> Referenz: Plan Section 5.6

- [ ] `strings.json` erweitern (Config Flow Steps)
- [ ] `translations/de.json` erweitern

### 4.2 Englische Übersetzungen
> Referenz: Plan Section 5.6

- [ ] `translations/en.json` erweitern

---

## Phase 5: Integration

### 5.1 Entry Setup
> Referenz: Plan Section 11.1

- [ ] `__init__.py`: SmartLife Client bei Setup initialisieren
- [ ] Token-Info in RuntimeData speichern

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
  - [ ] Device Selection Step
  - [ ] Reauth Flow

---

## Phase 7: Dokumentation

### 7.1 User-Dokumentation
> Referenz: Plan Section 10

- [ ] `README.md` aktualisieren
  - [ ] SmartLife Setup als primäre Methode
  - [ ] Screenshots für QR-Code Flow
  - [ ] FAQ erweitern

- [ ] `docs/SMARTLIFE_SETUP.md` erstellen (User Guide)

### 7.2 Changelog
- [ ] `CHANGELOG.md` für v4.0.0
  - Breaking Changes (falls vorhanden)
  - Neue Features
  - Dokumentation

---

## Phase 8: Release

### 8.1 Finale Checks
- [ ] Alle Tests grün
- [ ] HACS Validation bestanden
- [ ] Manual Test: Kompletter SmartLife Flow

### 8.2 Release erstellen
- [ ] Git Tag `v4.0.0`
- [ ] GitHub Release mit Changelog
- [ ] HACS Update prüfen

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
| 7. Dokumentation | 1 h | Phase 1-5 |
| 8. Release | 30 min | Alles |

**Gesamt:** ~8-10 Stunden

---

## Fortschritt

| Phase | Status | Notizen |
|-------|--------|---------|
| 1. Grundlagen | ⬜ Offen | |
| 2. Client | ⬜ Offen | |
| 3. Config Flow | ⬜ Offen | |
| 4. Translations | ⬜ Offen | |
| 5. Integration | ⬜ Offen | |
| 6. Testing | ⬜ Offen | |
| 7. Dokumentation | ⬜ Offen | |
| 8. Release | ⬜ Offen | |

---

*Letzte Aktualisierung: 2026-01-05*
