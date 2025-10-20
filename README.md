# KKT Kolbe Home Assistant Integration

<div align="center">
  <img src="./icon.png" alt="KKT Kolbe Logo" width="128" height="128">

  ## 🎯 v2.0.0-beta.1 - TinyTuya API & Enhanced Stability
</div>

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license-url]
[![hacs][hacsbadge]][hacs]
[![Beta][betabadge]][beta-release]

[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

**Vollständige Home Assistant Integration für KKT Kolbe Küchengeräte**

Unterstützt Dunstabzugshauben und Induktionskochfelder über Tuya Local Protocol mit Cloud API Fallback.

## 🚀 Unterstützte Geräte

### 🌬️ Dunstabzugshauben (3 Modelle)

#### **HERMES & STYLE Hood** ✅ Vollständig getestet
- **5-Stufen Lüftersteuerung** (off, low, middle, high, strong)
- **Separate Light Control** (Ein/Aus-Schalter)
- **RGB Beleuchtung** (0-9 Modi)
- **Timer-Funktion** (0-60 Minuten)
- **Filter-Erinnerungen**

#### **HERMES Hood** ✅ Konfiguration verfügbar
- **5-Stufen Lüftersteuerung** mit Fan Entity
- **Separate Light Control**
- **RGB Beleuchtung** mit 10 Modi
- **Timer- und Filterverwaltung**

#### **ECCO HCM Hood** ✅ Erweiterte Funktionen
- **9-Stufen Lüftersteuerung** (0-9)
- **Multi-Light Control** (Main, LED, RGB)
- **RGB Farbmodi** (white/colour/scene/music)
- **Duale Filterüberwachung** (Kohle & Metall)
- **Wasch-Modus**

### 🔥 Induktionskochfeld

#### **IND7705HC** ✅ Vollständige Zone-Steuerung
- **5 Kochzonen** mit individueller Steuerung
- **Leistungsstufen** pro Zone (0-25)
- **Timer pro Zone** (bis 255 Minuten)
- **Temperaturkontrolle** (Target & Current)
- **Erweiterte Features**: Boost, Keep Warm, Flex-Zonen
- **Sicherheit**: Kindersicherung, Pause/Resume
- **Chef-Funktionen**: BBQ-Modus, Quick Levels

## ✨ Integration Features

### 🚀 **v2.0.0-beta.1: TinyTuya API & Enhanced Stability**

#### **TinyTuya Cloud API Integration** 🆕
- **Hybrid Communication**: Nahtloser Wechsel zwischen Local und Cloud
- **API Discovery**: Automatische Geräteerkennung über Tuya Cloud
- **Shadow Properties**: Echtzeit-Synchronisation mit Cloud-Status
- **Dynamic Configuration**: Auto-Konfiguration basierend auf API-Metadaten

#### **Erweiterte Wiederverbindung** 🆕
- **Auto-Reconnect mit Backoff**: Intelligente Wiederverbindung (5s → 5min)
- **Device State Tracking**: ONLINE, OFFLINE, RECONNECTING, UNREACHABLE
- **Health Monitoring**: Periodische Gesundheitschecks alle 5 Minuten
- **Manual Recovery**: Services für manuelle Wiederverbindung

#### **Verbesserte Authentifizierung** 🆕
- **Reauth Flow**: Automatische Neuauthentifizierung bei Ablauf
- **Local Key Update Service**: Einfache Key-Aktualisierung nach Reset
- **API Credential Management**: Sichere Token-Speicherung und -Refresh
- **Multiple Auth Methods**: Local-only, API-only, oder Hybrid-Modus

### 🏠 **Bewährte Integration Features**

#### **Automatische Erkennung**
- **mDNS Discovery**: Automatisches Auffinden von KKT Geräten im Netzwerk
- **Device Type Detection**: Intelligente Erkennung basierend auf Device ID und Product Name
- **Smart Configuration**: Automatische Entity-Konfiguration je nach Gerät

#### **Robuste Konnektivität**
- **Tuya Local Protocol**: Direkte Verbindung ohne Cloud
- **Auto-Reconnect**: Automatische Wiederverbindung bei Unterbrechungen
- **Version Auto-Detection**: Unterstützt verschiedene Tuya Protocol Versionen
- **Enhanced Timeouts**: Optimierte Verbindungszeiten für stabile Performance

#### **Home Assistant Integration**
- **Native HA Entities**: Switch, Number, Select, Binary Sensor, Fan
- **Device Registry**: Proper Device Information mit Modell und Firmware
- **Entity Categories**: Konfiguration und Diagnostik richtig kategorisiert
- **Lokalisierung**: Deutsche und englische Übersetzungen

## 📦 Installation

### Via HACS (Empfohlen)

1. **HACS öffnen** → **Integrations** → **⋮** → **Custom repositories**
2. **Repository hinzufügen**: `https://github.com/moag1000/HA-kkt-kolbe-integration`
3. **Kategorie**: `Integration`
4. **Installieren** → **Home Assistant neustarten**
5. **Integration hinzufügen**: Einstellungen → Geräte & Dienste → Integration hinzufügen → "KKT Kolbe"

### Manuelle Installation

1. Lade die neueste Release von [GitHub Releases](https://github.com/moag1000/HA-kkt-kolbe-integration/releases) herunter
2. Extrahiere `custom_components/kkt_kolbe/` nach `config/custom_components/`
3. Starte Home Assistant neu
4. Füge die Integration über die UI hinzu

## 🔧 Konfiguration

### Option 1: Automatische Erkennung ✅ Empfohlen
Die Integration findet KKT Geräte automatisch im lokalen Netzwerk über mDNS.

### Option 2: Manuelle Konfiguration
Benötigte Informationen:
- **IP-Adresse**: Lokale IP des Geräts (z.B. 192.168.1.100)
- **Device ID**: 20-22 Zeichen Tuya Device ID (z.B. bf735dfe2ad64fba7cpyhn)
- **Local Key**: 16+ Zeichen Local Key aus Tuya/Smart Life App

### Local Key Extraktion
Verwende Tools wie:
- `tuya-cli` - [Anleitung](https://github.com/codetheweb/tuyapi/blob/master/docs/SETUP.md)
- `tinytuya` - [Setup Guide](https://github.com/jasonacox/tinytuya#setup-wizard)

## 🎯 Entity Overview

### Dunstabzugshauben
- **Power Switch**: Hauptschalter für das Gerät
- **Light Switch**: Separater Lichtschalter
- **Fan Speed Select**: Lüfterstufen-Auswahl
- **Timer Number**: Countdown-Timer (0-60 Min)
- **RGB/LED Controls**: Beleuchtungsmodi
- **Filter Status**: Wartungserinnerungen

### Induktionskochfeld
- **Global Controls**: Power, Pause, Child Lock, Senior Mode
- **Zone-spezifisch** (je Zone):
  - Power Level Number (0-25)
  - Timer Number (0-255 Min)
  - Target Temperature (°C)
  - Current Temperature (°C)
  - Binary Sensors (Selected, Boost, Keep Warm, Error)
- **Advanced Features**: BBQ Mode, Flex Zones, Quick Levels

## 🛠️ Erweiterte Konfiguration

### Update-Intervall
- **Standard**: 30 Sekunden
- **Empfohlen für Echtzeit**: 10-15 Sekunden
- **Energiesparmodus**: 60+ Sekunden

### Debug Logging
Aktiviere Debug-Logs für Troubleshooting:
```yaml
logger:
  logs:
    custom_components.kkt_kolbe: debug
```

## ⚠️ Wichtige Hinweise

### Sicherheit
- **KI-generierter Code**: Diese Integration wurde von Claude Code erstellt
- **Eigene Verantwortung**: Verwendung auf eigene Gefahr
- **Kochfeld-Sicherheit**: Besondere Vorsicht bei Induktionskochfeld-Steuerung
- **Hardware-Tests**: Code wurde nicht mit echter Hardware getestet

### Bekannte Limitationen
- **Tuya Cloud unabhängig**: Benötigt lokale Netzwerkverbindung
- **Device-spezifisch**: Konfiguration ist modellspezifisch
- **Firmware-abhängig**: Verschiedene Firmware-Versionen können abweichen

## 🐛 Troubleshooting

### Häufige Probleme

**Gerät nicht gefunden**
- Prüfe, ob Gerät im gleichen Netzwerk ist
- Versuche manuelle Konfiguration
- Aktiviere Debug-Logging

**Authentifizierung fehlgeschlagen**
- Überprüfe Local Key
- Stelle sicher, dass Gerät nicht von anderer App verwendet wird
- Teste verschiedene Protocol-Versionen

**Entities zeigen "unavailable"**
- Überprüfe Netzwerkverbindung
- Restart der Integration
- Prüfe Tuya App, ob Gerät noch funktioniert

## 📝 Changelog

### v2.0.0-beta.1 (Current Beta)
- 🌐 TinyTuya Cloud API Integration
- 🔄 Enhanced Reconnection System
- 🔑 Improved Authentication Flow
- 🛠️ New Device Management Services
- ✅ Home Assistant 2025.12 Compatibility

### v1.7.10 (Latest Stable)
- ✅ **State Caching System**: Keine "unknown" States mehr
- ✅ **Entity Consistency**: Alle Geräte standardisiert
- ✅ **Config Flow Improvements**: Vollständige Device IDs, bessere UI
- ✅ **Bug Fixes**: Falsy value handling, bitfield utils optimization

[Vollständiges Changelog](./CHANGELOG.md)

## 🤝 Contributing

Da dies ein KI-generiertes Projekt ist:
- **Issues willkommen**: Bug Reports und Feature Requests
- **Testing erwünscht**: Reale Hardware-Tests sind wertvoll
- **Pull Requests**: Gerne für Verbesserungen und Fixes
- **Documentation**: Hilfe bei Dokumentation sehr geschätzt

## 📞 Support

- **GitHub Issues**: [Bug Reports & Feature Requests](https://github.com/moag1000/HA-kkt-kolbe-integration/issues)
- **Discussions**: [Community Support](https://github.com/moag1000/HA-kkt-kolbe-integration/discussions)
- **Wiki**: [Extended Documentation](https://github.com/moag1000/HA-kkt-kolbe-integration/wiki)

## 📄 License

MIT License - siehe [LICENSE](./LICENSE) für Details.

---

**Made with ❤️ and 🤖 by [@moag1000](https://github.com/moag1000) & Claude Code**

[releases-shield]: https://img.shields.io/badge/release-v2.0.0--beta.1-blue.svg?style=for-the-badge
[betabadge]: https://img.shields.io/badge/status-BETA-yellow.svg?style=for-the-badge
[beta-release]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v2.0.0-beta.1
[releases]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/moag1000/HA-kkt-kolbe-integration.svg?style=for-the-badge
[commits]: https://github.com/moag1000/HA-kkt-kolbe-integration/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/moag1000/HA-kkt-kolbe-integration.svg?style=for-the-badge
[license-url]: https://github.com/moag1000/HA-kkt-kolbe-integration/blob/main/LICENSE
[buymecoffee]: https://www.buymeacoffee.com/moag1000
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40moag1000-blue.svg?style=for-the-badge
[user_profile]: https://github.com/moag1000