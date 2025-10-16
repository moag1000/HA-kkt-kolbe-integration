# KKT Kolbe Home Assistant Integration

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

### Supported Models
- **KKT Kolbe HERMES & STYLE** - Range Hood (Model ID: e1k6i0zo)
- **KKT IND7705HC** - Induction Cooktop (Product ID: p8volecsgzdyun29)

### Entities Based on Device Type

#### Range Hood (HERMES & STYLE)
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

### Configuration
The integration supports configuration via UI. You'll need:
- **IP Address**: Local IP of your KKT Kolbe device
- **Device ID**: Tuya device ID (find in Smart Life app)
- **Local Key**: Tuya local key (extract using tuya-cli or similar)
- **Type**: Device type (auto-detect, hood, or cooktop)
- **Name**: Custom name for your device (optional)

### Getting Tuya Credentials

⚠️ **SECURITY WARNING**: Never commit real credentials to Git! See [SECURITY.md](SECURITY.md)

1. Install the Smart Life app and add your hood
2. Use [tuya-cli](https://github.com/TuyaAPI/cli) or [tinytuya wizard](https://github.com/jasonacox/tinytuya) to extract:
   - Device ID (example: `bf735dfe2ad64fba7cXXXX`)
   - Local Key (⚠️ KEEP SECRET!)
3. Note the device's local IP address (example: `192.168.1.xxx`)
4. **IMPORTANT**: Use `config_example.yaml` as template, never commit real values!

## 🏪 HACS Compatibility

✅ **HACS Ready**: Installation über HACS Custom Repositories möglich

- Repository: `https://github.com/moag1000/HA-kkt-kolbe-integration`
- Current Version: `v0.1.0`
- Updates: Über HACS automatisch verfügbar

## Development Status

🤖 **KI-generierter Code**: Diese Integration wurde vollständig von Claude AI erstellt.

### Features Implemented
- ✅ Tuya device communication (theoretisch)
- ✅ All device data points mapped (basierend auf API Explorer)
- ✅ Config flow with validation
- ✅ Translations (de, en)
- ✅ Full entity support based on device capabilities

### ⚠️ WICHTIG: Nicht getestet!
- ❌ Code wurde NICHT mit echter Hardware getestet
- ❌ Funktionalität ist rein theoretisch
- ❌ Mögliche Fehler bei der Gerätesteuerung
- ❌ Sicherheitsrisiken bei Kochfeld-Steuerung

### TODO (für mutige Tester)
- [ ] Test with actual hardware (AUF EIGENE GEFAHR!)
- [ ] Code-Review durch erfahrene Entwickler
- [ ] Sicherheits-Audit besonders für Kochfeld
- [ ] Add device discovery via mDNS
- [ ] Add energy monitoring if supported

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

Detaillierte Anleitung: [CONTRIBUTING.md](CONTRIBUTING.md)

## File Structure

```
kkt_kolbe_integration/
├── custom_components/
│   └── kkt_kolbe/
│       ├── __init__.py         # Integration setup
│       ├── manifest.json       # Integration metadata
│       ├── config_flow.py      # Configuration UI
│       ├── const.py            # Constants and models
│       ├── device_types.py     # Device type definitions
│       ├── tuya_device.py      # Tuya communication
│       ├── sensor.py           # Sensor entities
│       ├── fan.py              # Fan control (hood)
│       ├── light.py            # Light control (hood)
│       ├── switch.py           # Switch entities
│       ├── select.py           # RGB mode selector
│       ├── number.py           # Timer controls
│       ├── cooktop.py          # Cooktop specific entities
│       └── translations/       # UI translations
├── config_example.yaml         # Example configuration (safe)
├── SECURITY.md                 # Security guidelines
└── .gitignore                  # Prevents credential commits
```

## Requirements

- Home Assistant 2024.1.0 or newer
- Python 3.11+

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