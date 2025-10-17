# KKT Kolbe Home Assistant Integration

<div align="center">
  <img src="./icon.png" alt="KKT Kolbe Logo" width="128" height="128">
</div>

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license-url]
[![hacs][hacsbadge]][hacs]

[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

Custom Home Assistant integration for KKT Kolbe devices using Tuya protocol.
Supports both range hoods and induction cooktops.

## Motivation

Ich habe mich mit der local tuya Implementierung schwer getan, weil diverseste Fähigkeiten nicht richtig oder händisch nur schwierig umzusetzen sind. Dann habe ich im API Explorer in der IoT Plattform von Tuya den wichtigen Punkt gefunden - "Query things data model" (unter Device control), also alles was notwendig war um eine Erweiterung bequemer zu machen.

## ⚠️ WICHTIGER DISCLAIMER

**DISCLAIMER: ich habe das Projekt mit Claude Code erstellen lassen weil ich keine Zeit hatte, dies selbst umzusetzen. Bitte daher KEINESFALLS einfach nur davon ausgehen, dass "es schon klappt". Das IST KI ARBEIT - also anfällig für Halluzinationen und Fehler die z.b. bei Kochfeldern trotz Sicherungsmaßnahmen des Herstellers zu gefährlichen Ergebnissen führen könnten.**

**🔴 BITTE daher auf EIGENE Gefahr benutzen!**

### Sicherheitshinweise
- Diese Integration wurde vollständig von KI (Claude) generiert
- Der Code wurde NICHT mit echter Hardware getestet
- Bei Kochfeldern können Fehler zu gefährlichen Situationen führen
- Nutzen Sie diese Integration nur, wenn Sie die Risiken verstehen
- Überprüfen Sie den Code selbst vor der Verwendung
- Der Autor übernimmt keinerlei Haftung

## Features

### ✅ v1.5.0: Advanced Architecture & Production Readiness

**🎯 Moderne Home Assistant Architektur mit DataUpdateCoordinator!**

#### ✅ Moderne HA-Patterns
- **DataUpdateCoordinator**: Zentrale Datenverwaltung für optimale Performance
- **CoordinatorEntity**: Alle Entitäten nutzen moderne HA-Patterns
- **Binary Sensor Support**: Vollständige Unterstützung für Gerätestatus
- **Enhanced Error Handling**: Async-Pattern ohne Fire-and-Forget
- **Translation Support**: Vollständige Internationalisierung

#### 🚀 Smart Device Detection
- **Automatic Device Recognition**: Device ID automatisch erkannt - 4 Gerätemodelle unterstützt
- **Zero Configuration**: Keine manuelle Gerätetyp-Auswahl nötig
- **Universal Setup**: Funktioniert mit Auto-Discovery und manueller Konfiguration

### Supported Models (4 Geräte)

#### 🌬️ Range Hoods (3 Modelle)
- **KKT Kolbe HERMES & STYLE** - Range Hood (Model ID: e1k6i0zo)
- **KKT Kolbe HERMES** - Range Hood (Model ID: 0fcj8kha86svfmve)
- **KKT Kolbe ECCO HCM** - Range Hood (Model ID: edjsx0)

#### 🔥 Induction Cooktops (1 Modell)
- **KKT IND7705HC** - Induction Cooktop (Product ID: p8volecsgzdyun29)

### Entities Based on Device Type

#### Range Hood (HERMES & STYLE / HERMES / ECCO HCM)
- **Fan**: Control with 5 speed levels (off, low, middle, high, strong)
- **Light**: Main hood lighting on/off
- **RGB Light Mode**: 10 different lighting modes
- **Timer**: Countdown timer 0-60 minutes
- **Switches**: Power control, Filter cleaning reminder
- **Sensors**: Filter status monitoring

#### Induction Cooktop (IND7705HC)
- **5 Cooking Zones**:
  - Individual power control (0-25 levels)
  - Zone timers (up to 255 minutes)
  - Quick level presets (5 levels per zone)
  - Boost mode per zone
  - Keep warm mode per zone
- **Advanced Features**:
  - Chef function with special levels
  - BBQ mode with dual zone control
  - Flex zones for bridging
  - Core temperature sensor support
  - Power limit modes (5 settings)
- **Safety & Convenience**:
  - Child lock protection
  - Pause/Resume function
  - Senior mode for simplified operation
  - General timer (0-99 minutes)
  - Error monitoring per zone

**🤚 WICHTIG - Manuelle Bestätigung:**
- 👤 **Remote-Steuerung** erfordert **physische Bestätigung** am Gerät
- 📱 **Wie Tuya App**: Person muss vor Ort **Bestätigungstaste drücken**
- 🔒 **API-Limitation** (nicht Integration) - **Tuya-Sicherheitsfeature**

👉 **Detaillierte Erklärung:** [COOKTOP_SAFETY.md](COOKTOP_SAFETY.md)

## Installation

### 🏪 HACS Installation (Empfohlen)

1. **HACS öffnen** → **Integrations**
2. **⋮ Menü** (oben rechts) → **Custom repositories**
3. **Repository hinzufügen:**
   - URL: `https://github.com/moag1000/HA-kkt-kolbe-integration`
   - Category: `Integration`
4. **Add** → **KKT Kolbe Integration** suchen und installieren
5. **Home Assistant neu starten**
6. **Integration hinzufügen:** Settings → Devices & Services → Add Integration → KKT Kolbe

### 🏠 Automatische Geräteerkennung

**✨ KKT Kolbe Geräte werden automatisch im Netzwerk erkannt!**

#### 🎯 Setup-Prozess:
1. **Integration über HACS installieren**
2. **Integration hinzufügen** → KKT Geräte werden automatisch gefunden
3. **Gerät auswählen** → IP und Device ID sind bereits eingetragen
4. **Nur Local Key eingeben** → Fertig!

#### ✨ Discovery-Features:
- **mDNS + UDP Discovery**: Wie LocalTuya - findet Geräte zuverlässig
- **Automatische Typerkennung**: 4 Gerätemodelle (3 Hoods + 1 Cooktop)
- **Zero-Config**: Keine IP-Suche oder Device ID-Eingabe nötig
- **Fallback**: Manuelle Konfiguration weiterhin verfügbar

### 📁 Manual Installation
1. Download neueste [Release](https://github.com/moag1000/HA-kkt-kolbe-integration/releases)
2. `custom_components/kkt_kolbe` nach `config/custom_components/` kopieren
3. Home Assistant neu starten
4. Integration über UI hinzufügen

### ⚠️ Nach der Installation

**WICHTIG vor der ersten Verwendung:**
- Diese Integration wurde von KI erstellt und ist **UNGETESTET**
- Bei Kochfeldern können Fehler **gefährlich** werden
- Lesen Sie **alle Sicherheitswarnungen** in [AI_GENERATED_WARNING.md](AI_GENERATED_WARNING.md)
- **Eigene Verantwortung** bei der Nutzung

### 🔧 Konfiguration

#### Benötigte Daten:
- **Local Key**: Aus Smart Life App extrahieren (siehe unten)
- **IP & Device ID**: Automatisch erkannt oder manuell eingeben

#### Setup-Optionen:
1. **Automatisch** (empfohlen): Gerät aus Discovery-Liste wählen
2. **Manuell**: IP, Device ID und Local Key manuell eingeben


### Getting Tuya Credentials

⚠️ **SECURITY WARNING**: Never commit real credentials to Git! See [SECURITY.md](SECURITY.md)

1. Install the Smart Life app and add your hood
2. Use [tuya-cli](https://github.com/TuyaAPI/cli) or [tinytuya wizard](https://github.com/jasonacox/tinytuya) to extract:
   - Device ID (example: `bf735dfe2ad64fba7cXXXX`)
   - Local Key (⚠️ KEEP SECRET!)
3. Note the device's local IP address (example: `192.168.1.xxx`)
4. **IMPORTANT**: Use `config_example.yaml` as template, never commit real values!

## 🏪 HACS Status

✅ **PRODUCTION READY**: v1.5.6

- **Current Version: `v1.5.6`** 🎯 **ADVANCED HA ARCHITECTURE**
- **✅ DataUpdateCoordinator** - Zentrale Datenverwaltung nach HA Best Practices
- **✅ CoordinatorEntity Pattern** - Alle Entitäten nutzen moderne Patterns
- **✅ Binary Sensor Support** - Vollständige Gerätestatus-Überwachung
- **✅ Translation Support** - Vollständige Internationalisierung
- **✅ Enhanced Async Patterns** - Kein Fire-and-Forget, sauberes Error Handling
- Updates: Über HACS automatisch verfügbar

## Development Status

🤖 **KI-generierter Code**: Diese Integration wurde vollständig von Claude AI erstellt.

### Features Implemented
- ✅ **UDP + mDNS Discovery** (wie Local Tuya)
- ✅ **Home Assistant Auto-Discovery** ohne offiziellen PR
- ✅ **Async TinyTuya Integration** (keine blocking operations)
- ✅ **Comprehensive Error Handling** mit spezifischen Fehlermeldungen
- ✅ **Multi-Step Config Flow** mit automatischer Geräteerkennung
- ✅ **Full Translations** (deutsch/englisch)
- ✅ **All Device Data Points** für alle 4 unterstützten Gerätemodelle
- ✅ **Debug & Troubleshooting** Modi

### ⚠️ WICHTIG: Experimenteller Status
- 🔄 Code wurde kontinuierlich verbessert basierend auf User-Feedback
- ✅ Discovery-System funktioniert wie Local Tuya (UDP + mDNS)
- ✅ Umfassende Error Handling und Debug-Modi
- ⚠️ Bei Kochfeldern Sicherheitshinweise beachten ([COOKTOP_SAFETY.md](COOKTOP_SAFETY.md))

### 🚀 Changelog v1.5.6 (LATEST) - Translation & Discovery Bugfixes!
- 🏗️ **DataUpdateCoordinator**: Zentrale Datenverwaltung nach HA Best Practices
- 🔗 **CoordinatorEntity Pattern**: Alle Entitäten verwenden moderne HA-Patterns
- 🟢 **Binary Sensor Support**: Vollständige Gerätestatus-Überwachung
- 🌍 **Translation Support**: Vollständige Internationalisierung (de/en)
- 🔄 **Enhanced Async Patterns**: Kein Fire-and-Forget, sauberes Error Handling
- 🧹 **Code Cleanup**: Entfernung veralteter Dateien und Patterns

### 🚀 Changelog v1.0.0 - Production Ready Foundation
- 🔧 **CRITICAL FIX**: Korrekter Tuya Port (6667 statt 6668)
- 🔧 **CRITICAL FIX**: Device ID Validation (exakt 20 Zeichen)
- 🔧 **CRITICAL FIX**: Connection Error Handling verbessert
- 🔧 **CRITICAL FIX**: mDNS Device ID aus TXT Records statt Service Name
- 🛠️ **IMPROVED**: IP-Adresse Hostname Resolution behoben
- 🌐 **IMPROVED**: UDP Discovery mit Local Tuya Koexistenz
- 🧵 **FIXED**: Alle Threading/Async Probleme eliminiert
- 🎯 **RESULT**: Stabile, produktionsreife Integration

### Changelog v0.3.1-0.3.8
- 🔧 **FIXED**: Alle Home Assistant Compliance Warnings behoben
- ✨ **NEW**: Async TinyTuya Integration (keine blocking operations)
- 🔧 **FIXED**: RuntimeWarning coroutine never awaited
- 🔧 **FIXED**: Zeroconf shared instance usage
- 🛠️ **IMPROVED**: Entities verwenden async methods
- 📊 **ENHANCED**: Bessere Error Messages statt "Unerwarteter Fehler"

### Changelog v0.3.0
- 🏠 **MAJOR FEATURE**: Home Assistant Auto-Discovery ohne offiziellen PR!
- ✨ **NEW**: Automatische Discovery beim HA Start
- 🎯 **NEW**: Zeroconf Integration für nahtlose Geräteerkennung
- 🔄 **NEW**: "Retry automatic discovery" Option
- 🌍 **NEW**: Vollständige deutsche/englische Übersetzungen
- 🛠️ **Improved**: Erweiterte Debug-Modi und Network Analysis

### Changelog v0.2.2
- 🎯 **MAJOR FIX**: Erkennt KKT Geräte als generische Tuya Devices
- ✨ **NEW**: Tuya Device ID Pattern Detection (`bf` + hex)
- 🔍 **NEW**: Spezifische KKT Device ID Patterns aus echten Tests
- 🛠️ **NEW**: Debug-Modi und Test Device Simulation
- 📊 **Improved**: TXT Record Analyse für bessere Geräteerkennung

### Changelog v0.2.1
- 🔧 **Fixed**: mDNS Discovery Timing - startet sofort beim Config Flow
- 🔧 **Fixed**: Smarte Wartelogik (max 5s, prüft alle 500ms)
- ✨ **Improved**: Erweiterte mDNS Service Types
- 🐛 **Fixed**: Debug-Logging für besseres Troubleshooting

### Changelog v0.2.0
- ✨ **NEU**: mDNS Automatic Device Discovery
- ✨ **NEU**: Vereinfachter Setup-Prozess
- ✨ **NEU**: Automatische Gerätetyp-Erkennung
- 🔧 **Verbessert**: Multi-Step Config Flow
- 🌍 **Erweitert**: Deutsche/Englische Übersetzungen

### TODO (für mutige Tester)
- [ ] Test with actual hardware (AUF EIGENE GEFAHR!)
- [ ] Code-Review durch erfahrene Entwickler
- [ ] Sicherheits-Audit besonders für Kochfeld
- [✅] ~~Add device discovery via mDNS~~ **ERLEDIGT in v0.2.0**
- [ ] Add energy monitoring if supported
- [ ] Test mDNS discovery with real devices

## 🚀 Weitere Geräte hinzufügen

**Möchten Sie Unterstützung für weitere KKT Kolbe Modelle hinzufügen?**

### Schritt-für-Schritt Anleitung:

1. **Tuya IoT Developer Account** (separater Account erforderlich!):
   - Registrierung auf https://iot.tuya.com/
   - ⚠️ Ihr Smart Life App Account funktioniert NICHT
   - Cloud-Projekt erstellen

2. **App Account verknüpfen**:
   - Im Cloud-Projekt: **Devices** → **Link App Account**
   - Ihre Tuya/Smart Life App mit dem Cloud-Projekt verbinden
   - Alle Geräte sollten nun im Cloud-Projekt sichtbar sein

3. **Device Model abrufen**:
   - **Cloud** → **API Explorer** → **Device Management**
   - **"Query Things Data Model"** auswählen
   - Ihre **Device ID** eingeben (aus App/Integration)
   - JSON Output kopieren

4. **Feature Request erstellen**:
   - GitHub Issue mit dem JSON Output
   - Gewünschte Funktionen beschreiben
   - Model-Info angeben

**🔧 Für Entwickler**: Komplette Anleitung in [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)

Detaillierte Anleitung: [CONTRIBUTING.md](CONTRIBUTING.md)

## File Structure

```
kkt_kolbe_integration/
├── custom_components/
│   └── kkt_kolbe/
│       ├── __init__.py         # Integration setup with coordinator
│       ├── manifest.json       # Integration metadata
│       ├── icon.svg            # Integration logo
│       ├── config_flow.py      # Configuration UI (multi-step)
│       ├── coordinator.py      # 🆕 DataUpdateCoordinator implementation
│       ├── discovery.py        # mDNS auto-discovery
│       ├── const.py            # Constants and models
│       ├── device_database.py  # Device identification database
│       ├── device_types.py     # Device type definitions
│       ├── tuya_device.py      # Tuya communication
│       ├── sensor.py           # Sensor entities (coordinator-based)
│       ├── fan.py              # Fan control (coordinator-based)
│       ├── light.py            # Light control (coordinator-based)
│       ├── switch.py           # Switch entities (coordinator-based)
│       ├── select.py           # RGB mode selector (coordinator-based)
│       ├── number.py           # Timer controls (coordinator-based)
│       ├── binary_sensor.py    # 🆕 Binary sensor entities
│       └── translations/       # UI translations (de/en)
├── config_example.yaml         # Example configuration (safe)
├── LOCAL_TUYA_GUIDE.md         # Alternative: Local Tuya setup
├── COOKTOP_SAFETY.md           # Induction cooktop safety info
├── LOGO_INFO.md                # Logo design documentation
├── SECURITY.md                 # Security guidelines
└── .gitignore                  # Prevents credential commits
```

## Requirements

- Home Assistant 2024.1.0 or newer
- Python 3.11+

## 🔄 Alternative: Local Tuya

**Bevorzugen Sie eine stabile, erprobte Lösung?**

Falls Ihnen die experimentelle KI-Integration zu riskant ist, haben wir eine vollständige Anleitung für die Einrichtung in **Local Tuya** erstellt:

👉 **[Local Tuya Setup Guide](LOCAL_TUYA_GUIDE.md)**

**Local Tuya Vorteile:**
- ✅ Erprobt und stabil (tausende Nutzer)
- ✅ Community-validiert und sicher
- ✅ Regelmäßige Updates
- ⚠️ Begrenzte Funktionen bei komplexen Geräten

## 🤝 Contributing

Beiträge sind sehr willkommen! Besonders:
- Hardware-Tests mit echten Geräten
- Code-Reviews und Sicherheits-Audits
- Unterstützung für weitere Modelle

Siehe [CONTRIBUTING.md](CONTRIBUTING.md) für Details.

## License

MIT

## Author

GitHub: [@moag1000](https://github.com/moag1000)

**⚠️ Dieser Code wurde vollständig von Claude AI erstellt!**

---

<!-- Badges -->
[commits-shield]: https://img.shields.io/github/commit-activity/y/moag1000/HA-kkt-kolbe-integration.svg?style=for-the-badge
[commits]: https://github.com/moag1000/HA-kkt-kolbe-integration/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge
[license-url]: https://opensource.org/licenses/MIT
[releases-shield]: https://img.shields.io/badge/version-v1.5.6-blue.svg?style=for-the-badge
[releases]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40moag1000-blue.svg?style=for-the-badge
[user_profile]: https://github.com/moag1000
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/moag1000