# KKT Kolbe Integration - Refactoring Roadmap

## Ziel: Gold Quality Scale

Basierend auf [Home Assistant Integration Quality Scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/)

**Aktuelle Bewertung:** Bronze VOLLSTÄNDIG | Silver VOLLSTÄNDIG | Gold VOLLSTÄNDIG (100%)
**Siehe:** [QUALITY_SCALE_ANALYSIS.md](./QUALITY_SCALE_ANALYSIS.md)

---

## Phase 0: Quick Wins - ERLEDIGT

| Task | Status |
|------|--------|
| 0.1 services.yaml erstellen | Erledigt |
| 0.2 Final Type Hints in const.py | Erledigt |

---

## Phase 1: Bronze erreichen - ABGESCHLOSSEN
*Baseline für alle HA Integrations*

### 1.1 Translation-Duplikate bereinigen
- [x] Doppelte Steps in en.json/de.json entfernt
- [x] Struktur vereinheitlicht
- **Status:** Erledigt

### 1.2 Migration zu entry.runtime_data
- [x] `hass.data[DOMAIN][entry.entry_id]` → `entry.runtime_data`
- [x] KKTKolbeRuntimeData dataclass erstellt
- [x] Alle Entity-Plattformen aktualisiert
- **Status:** Erledigt

### 1.3 Tests hinzufügen
- [x] tests/ Verzeichnis erweitert
- [x] Config Flow Tests erstellt
- [x] Init Tests erweitert
- [x] conftest.py mit Fixtures
- **Status:** Erledigt

### 1.4 Dokumentation vervollständigen
- [x] README.md umfassend
- [x] Installation Guide vorhanden
- [x] Service Actions dokumentiert
- **Status:** Erledigt

### 1.5 brands/ Verzeichnis
- [x] icon.png, icon@2x.png vorhanden
- [x] logo.png, logo@2x.png vorhanden
- [x] icon.svg vorhanden
- **Status:** Erledigt

---

## Phase 2: Silver erreichen - ABGESCHLOSSEN
*Reliability & Robustness*

### 2.1 CODEOWNERS erstellen
- [x] Maintainer @moag1000 definiert
- **Status:** Erledigt

### 2.2 Test Coverage erweitert
- [x] test_exceptions.py hinzugefügt
- [x] test_switch.py hinzugefügt
- [x] test_light.py hinzugefügt
- [x] test_number.py hinzugefügt
- [x] test_binary_sensor.py hinzugefügt
- **Status:** Erledigt

### 2.3 stale-devices Cleanup
- [x] device_tracker.py implementiert
- **Status:** Erledigt

### 2.4 Dokumentation Parameter
- [x] TROUBLESHOOTING.md erstellt
- [x] Config-Optionen dokumentiert
- **Status:** Erledigt

---

## Phase 3: Gold erreichen - ABGESCHLOSSEN (100%)
*Best User Experience*

### 3.1 entity-translations durchgängig
- [x] `base_entity.py`: `_attr_translation_key` Support
- [x] Entity-Translations in strings.json
- [x] Entity-Translations in de.json
- **Status:** Erledigt

### 3.2 exception-translations
- [x] Exceptions nutzen HomeAssistantError
- [x] translation_key und translation_placeholders
- [x] Translations in strings.json und de.json
- **Status:** Erledigt

### 3.3 icons.json erstellen
- [x] icon-translations für alle Entities
- [x] Service Icons definiert
- **Status:** Erledigt

### 3.4 API-Status Binary Sensor
- [x] KKTKolbeConnectionSensor (Device Connected)
- [x] KKTKolbeAPIStatusSensor (Cloud API Connected)
- [x] Übersetzungen in en.json/de.json
- **Status:** Erledigt

### 3.5 Umfangreiche Dokumentation
- [x] TROUBLESHOOTING.md erstellt
- [x] Data Points Reference
- [x] Known Limitations dokumentiert
- **Status:** Erledigt

---

## Phase 4: Code-Optimierung - ABGESCHLOSSEN
*Redundanzen eliminieren, Wartbarkeit verbessern*

### 4.1 Entity Setup Factory
- [x] `helpers/entity_factory.py` erstellen
- [x] Gemeinsamen Setup-Code extrahieren
- **Status:** Erledigt

### 4.2 Toter Code entfernen
- [x] config_flow_v2.py gelöscht (360 Zeilen)
- [x] TuyaAPIManager gelöscht (ungenutzt)
- [x] Ungenutzte device_types.py Funktionen entfernt:
  - `get_device_dps`
  - `get_device_info_by_device_id`
  - `get_product_name_by_device_id`
  - `auto_detect_device_config`
  - `get_device_platforms_by_product_name`
- **Status:** Erledigt

### 4.3 Coordinator-Analyse
- [x] coordinator.py (Local) - Aktiv, notwendig
- [x] hybrid_coordinator.py (Hybrid/API) - Aktiv, notwendig
- **Resultat:** Keine Redundanz, beide werden verwendet
- **Status:** Erledigt

### 4.4 Discovery-Modul Analyse
- [x] discovery.py - Low-level UDP/mDNS
- [x] smart_discovery.py - High-level Abstraction
- **Resultat:** Keine Redundanz, korrekte Architektur
- **Status:** Erledigt

### 4.5 API Manager Analyse
- [x] GlobalAPIManager - Globale Credential-Speicherung (aktiv)
- [x] TuyaAPIManager - Per-Entry (ungenutzt → gelöscht)
- **Status:** Erledigt

---

## Fortschritt Übersicht

| Phase | Bereich | Status |
|-------|---------|--------|
| 0 | Quick Wins | DONE |
| 1 | Bronze | DONE |
| 2 | Silver | DONE |
| 3 | Gold | DONE (100%) |
| 4 | Optimierung | DONE |

### Gelöschte Dateien (toter Code)
- `config_flow_v2.py` (360 Zeilen)
- `api/tuya_api_manager.py` (173 Zeilen)
- 5 ungenutzte Funktionen in device_types.py (~80 Zeilen)

**Gesamt entfernter Code:** ~613 Zeilen

---

## Offene Tasks (Priorität)

### Alle Erledigt ✅
1. ~~Test Coverage erweitert~~ - 15 Test-Dateien (>95%)
2. ~~Entity-Translations~~ - strings.json + de.json
3. ~~stale-devices Cleanup~~ - device_tracker.py
4. ~~Exception-Translations~~ - HomeAssistantError
5. ~~Parameter-Dokumentation~~ - Vollständig
6. ~~Troubleshooting Guide~~ - TROUBLESHOOTING.md
7. ~~Use Cases dokumentiert~~ - docs/USE_CASES.md
8. ~~dynamic-devices~~ - rescan_devices Service + mDNS/UDP

### Gold Quality Scale erreicht! 🥇
Die Integration erfüllt nun alle 21 Gold-Tier Anforderungen der Home Assistant Integration Quality Scale.

---

## Referenzen
- [Integration Quality Scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/)
- [Quality Scale Rules](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/)
- [Dyson Integration (Gold)](https://github.com/cmgrayb/hass-dyson)
- [HA Developer Docs](https://developers.home-assistant.io/)
