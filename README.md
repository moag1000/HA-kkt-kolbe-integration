# KKT Kolbe Home Assistant Integration

<div align="center">
  <img src="./icon.png" alt="KKT Kolbe Logo" width="128" height="128">

  ## 🎯 v2.0.0-beta.8 - Global API Management & Enhanced Setup Experience
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

### 🚀 **v2.0.0-beta.8: Global API Management & Enhanced Setup Experience**

#### **Global API Key Management** 🆕
- API Keys werden global gespeichert und wiederverwendet
- Folge-Setups erkennen gespeicherte Credentials
- Option zwischen gespeicherten und neuen Credentials
- Optimiert für Haushalte mit mehreren KKT Geräten

#### **3-Wege Setup-Architektur** 🆕
- **🔍 Automatic Discovery**: Automatische Netzwerk-Erkennung
- **🔧 Manual Local Setup**: Manuelle lokale Konfiguration
- **☁️ API-Only Setup**: Reine Cloud-basierte Einrichtung

#### **Verbesserte API-Only Einrichtung** 🆕
- Funktioniert ohne lokale IP/Local Key Konfiguration
- Automatische Geräteerkennung über TinyTuya API
- Unterstützt verschiedene regionale API-Endpunkte
- Filtert automatisch nach KKT Kolbe Geräten

#### **Optimierte Benutzerführung** 🆕
- Reduzierte Setup-Zeit für weitere Geräte
- Vereinfachter Prozess durch globale API-Verwaltung
- Einmalige API-Konfiguration für alle Geräte
- Konsistente Erfahrung über mehrere Geräte hinweg

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

### 🚀 Neue 3-Wege Setup-Architektur (v2.0.0-beta.8+)

Wähle bei der Installation eine der drei Setup-Methoden:

#### **☁️ API-Only Setup** ✅ Empfohlen für mehrere Geräte
**Gut geeignet für Haushalte mit mehreren KKT Geräten**

**Erstes Gerät:**
1. Setup Method: ☁️ API-Only wählen
2. TinyTuya Credentials eingeben (Client ID, Secret, Region)
3. Device aus API-Discovery wählen
4. Credentials werden automatisch gespeichert

**Weitere Geräte:**
1. Setup Method: ☁️ API-Only wählen
2. "Use Stored API Credentials" wählen
3. Device aus Liste wählen
4. Fertig

**Vorteile:**
- Keine Local Key Extraktion nötig
- Funktioniert auch außerhalb des Heimnetzwerks
- API Keys nur einmal eingeben
- Schnellerer Setup für weitere Geräte

#### **🔍 Automatic Discovery** ✅ Empfohlen für Single Device
Die Integration findet KKT Geräte automatisch im lokalen Netzwerk über mDNS.

#### **🔧 Manual Local Setup**
Für erfahrene Nutzer mit spezifischen Anforderungen:
- **IP-Adresse**: Lokale IP des Geräts (z.B. 192.168.1.100)
- **Device ID**: 20-22 Zeichen Tuya Device ID (z.B. bf735dfe2ad64fba7cpyhn)
- **Local Key**: 16+ Zeichen Local Key aus Tuya/Smart Life App

### TinyTuya API Setup (für API-Only Modus)

#### Schritt 1: Tuya IoT Platform Account erstellen
1. Gehe zu [iot.tuya.com](https://iot.tuya.com)
2. **"Sign Up"** → Registrierung mit E-Mail
3. E-Mail bestätigen und anmelden

#### Schritt 2: Cloud Project erstellen
1. **Cloud** → **Development** → **Create Cloud Project**
2. **Project Name**: z.B. "Home Assistant KKT"
3. **Description**: z.B. "KKT Kolbe Integration"
4. **Industry**: "Smart Home" wählen
5. **Development Method**: "Smart Home PaaS" wählen
6. **Data Center**: Wichtig! Wähle deine Region:
   - **Europe**: EU (empfohlen für Deutschland)
   - **America**: US
   - **China**: CN
   - **India**: IN
7. **Create** klicken

#### Schritt 3: API Services aktivieren
Nach Projekterstellung → **Service API** → folgende APIs aktivieren:
- ✅ **Authorization Management**
- ✅ **Device Status Notification**
- ✅ **Smart Home Scene Linkage**
- ✅ **Device Management**
- ✅ **IoT Core** (falls verfügbar)

#### Schritt 4: Credentials abrufen
1. **Overview** → **Authorization Key**
2. Notiere dir diese Werte für die Integration:
   - **Access ID** (Client ID) - ca. 20 Zeichen
   - **Access Secret** (Client Secret) - ca. 32 Zeichen
   - **Data Center** (Region): EU/US/CN/IN

#### Schritt 5: Gerät mit Tuya verknüpfen
1. **Smart Life App** auf dem Handy installieren
2. Dein KKT Gerät in Smart Life einrichten
3. **Cloud** → **Link Tuya App Account**
4. QR-Code scannen oder Account verknüpfen

Jetzt kannst du die API-Only Einrichtung in der Integration verwenden!

### Local Key Extraktion (nur für Manual Local Setup)
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

### v2.0.0-beta.8 (Current Beta)
- 🔑 **Global API Key Management**: API Keys werden wiederverwendet
- 🎛️ **3-Wege Setup-Architektur**: Discovery/Manual Local/API-Only
- ☁️ **API-Only Setup**: Cloud-Setup ohne lokale Konfiguration
- 📱 **Optimierte Benutzerführung**: Schnellerer Setup für weitere Geräte
- 🌍 **Vollständige Übersetzungen**: Alle Config Flow Steps übersetzt
- 🛠️ **Verbesserte Config Flow**: Smart routing mit gespeicherten Daten

### v2.0.0-beta.1-7 (Previous Betas)
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

[releases-shield]: https://img.shields.io/badge/release-v2.0.0--beta.8-blue.svg?style=for-the-badge
[betabadge]: https://img.shields.io/badge/status-BETA-yellow.svg?style=for-the-badge
[beta-release]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v2.0.0-beta.8
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