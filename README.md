# KKT Kolbe Home Assistant Integration

<div align="center">
  <img src="./icon.png" alt="KKT Kolbe Logo" width="128" height="128">

### Home Assistant Integration - Gold Tier
</div>

[![GitHub Release][releases-shield]][releases]
[![Validate][validate-shield]][validate]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license-url]
[![hacs][hacsbadge]][hacs]

[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

**Zuverlässige Home Assistant Integration für KKT Kolbe Küchengeräte**

Unterstützt Dunstabzugshauben und Induktionskochfelder über Tuya Local Protocol mit Cloud API Fallback.

> **🤖 KI-Generiert:** Diese Integration wurde mit Anthropic's Claude entwickelt. Der Code ist Open Source und wurde ausgiebig getestet, aber **Verwendung erfolgt auf eigene Verantwortung** - besonders bei der Kochfeld-Steuerung!

> **✨ Quality:** Diese Integration folgt Home Assistant Best Practices mit vollständiger Typ-Annotation, async I/O, robustem Error Handling, automatischer Wiederherstellung und Tests.

## 🚀 Unterstützte Geräte

### 🌬️ Dunstabzugshauben (4 Modelle)

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

#### **SOLO HCM Hood** ✅ Konfiguration verfügbar
- **Lüftersteuerung**
- **Beleuchtung** (Main, LED)
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

---

### 🔍 Weitere Modelle - Hilfe benötigt!

Die Integration könnte weitere KKT Kolbe Modelle unterstützen, aber dafür werden **Gerätedaten** benötigt:

#### **Gesucht: VIVA Hood** 🔎
- Vermutlich ähnlich zu HERMES (basierend auf Firmware)
- Kategorie: `yyj` (Dunstabzugshaube)
- **Status**: Konfiguration fehlt

#### **Gesucht: SANDRA Hood** 🔎
- Vermutlich ähnlich zu HERMES/VIVA
- Kategorie: `yyj` (Dunstabzugshaube)
- **Status**: Konfiguration fehlt

**Hast du ein VIVA oder SANDRA Modell?**
→ Bitte [öffne ein Issue](https://github.com/moag1000/HA-kkt-kolbe-integration/issues/new) mit:
- Gerätemodell
- Device ID aus der Smart Life App
- Screenshot der verfügbaren Funktionen
- Optional: Debug-Logs mit aktivierten Entities

Mit deiner Hilfe können wir diese Modelle zur Integration hinzufügen! 🙏

---

## ✨ Integration Features

### 🆕 **Neu in v3.0.0: Home Assistant 2025.1+ Optimierungen** 🚀

> ⚠️ **Breaking Change:** Erfordert Home Assistant 2025.1.0 oder höher

#### **Moderne HA 2025 Features**
- ✅ **`suggested_display_precision`**: Saubere Anzeige ohne unnötige Dezimalstellen
- ✅ **`_unrecorded_attributes`**: Reduzierte Datenbankgröße durch Ausschluss nicht-historischer Attribute
- ✅ **`ConfigFlowResult`**: Modernisierte Type-Annotations für Config Flow
- ✅ **Model ID aus KNOWN_DEVICES**: Bessere Geräteidentifikation in der UI

#### **Verbesserungen**
- 🔧 Timer, Filter-Tage, Power-Level werden als ganze Zahlen angezeigt
- 🌡️ Temperatur-Sensoren zeigen 1 Dezimalstelle
- 💾 Weniger Datenbank-Einträge für diagnostische Attribute

#### **Reconfigure Flow** 🔧
Bestehende Geräte können jetzt über die UI neu konfiguriert werden:
- 🔌 **Connection**: IP-Adresse und Local Key ändern
- 📱 **Device Type**: Gerätetyp korrigieren
- ☁️ **API Settings**: Cloud API aktivieren/deaktivieren
- 🔧 **All Settings**: Alle Einstellungen auf einmal

---

### 🔌 **Konnektivität & Stabilität**

- ✅ **Tuya Local Protocol**: Direkte Verbindung ohne Cloud (Protocol 3.1 - 3.5)
- ✅ **TCP Keep-Alive**: Socket-Level Keepalive-Probes verhindern stille Verbindungsabbrüche
- ✅ **Circuit Breaker Pattern**: Intelligente Wiederverbindung nach Fehlern
- ✅ **Adaptive Update-Intervalle**: Automatische Anpassung bei Verbindungsproblemen
- ✅ **Quick Pre-Check**: Schnelle TCP-Prüfung vor Protokollerkennung

### ☁️ **Tuya Cloud API**

- ✅ **Smart Home Industry Support**: Free Tier & Paid Tier kompatibel
- ✅ **Nonce-basierte Authentifizierung**: Moderne API-Versionen
- ✅ **Global API Key Management**: Credentials einmal eingeben, für alle Geräte nutzen
- ✅ **Automatische Fallbacks**: Local → Cloud bei Verbindungsproblemen

### 🔧 **Automatische Wartung**

- **Repair Flows**: Automatisierte Reparatur-Workflows für Auth-Fehler
- **Stale Device Cleanup**: Automatisches Entfernen inaktiver Geräte (30+ Tage)
- **IP-Updates via Discovery**: Automatische IP-Aktualisierung bei Netzwerkänderungen

### 🎨 **Light Effects & HomeKit**

**RGB-Effekte für Dunstabzugshauben:**
- HERMES/STYLE: Weiß, Rot, Grün, Blau, Gelb, Lila, Orange, Cyan, Grasgrün
- SOLO/ECCO HCM: white, colour, scene, music

**HomeKit/Siri Integration:**
- Fan: Vollständige Geschwindigkeitssteuerung
- Light: An/Aus + Effekte

## 📘 Blueprints

Fertige Automations-Vorlagen zum Importieren:

| Blueprint | Beschreibung | Import |
|-----------|--------------|--------|
| Hood Auto-Off | Schaltet Haube nach X Min aus | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmoag1000%2FHA-kkt-kolbe-integration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fhood_auto_off.yaml) |
| Hood Light Auto-Off | Schaltet Licht nach X Min aus | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmoag1000%2FHA-kkt-kolbe-integration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fhood_light_auto_off.yaml) |
| Hood with Cooktop | Synchronisiert Haube mit Kochfeld | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmoag1000%2FHA-kkt-kolbe-integration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fhood_with_cooktop.yaml) |

[Alle Blueprints →](blueprints/README.md)

## 📚 Documentation & Examples

- **[Troubleshooting](TROUBLESHOOTING.md)** - Comprehensive troubleshooting guide
- **[Quality Scale](QUALITY_SCALE_ANALYSIS.md)** - Integration quality analysis (Gold 90%)
- **[Blueprints](blueprints/README.md)** - One-click automation templates
- **[Automation Examples](docs/AUTOMATION_EXAMPLES.md)** - 15+ ready-to-use automation examples
- **[Use Cases](docs/USE_CASES.md)** - Practical scenarios and implementation guides
- **[Gold Tier Checklist](docs/GOLD_TIER_CHECKLIST.md)** - Quality compliance status
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Integration development documentation
- **[Contributing](docs/CONTRIBUTING.md)** - How to contribute to this project
- **[Security](docs/SECURITY.md)** - Security policy and vulnerability reporting

### 🏠 **Home Assistant Integration**

- **Native HA Entities**: Fan, Light, Switch, Number, Select, Binary Sensor
- **Device Registry**: Device Information mit Modell und Firmware
- **Entity Categories**: Konfiguration und Diagnostik richtig kategorisiert
- **Lokalisierung**: Deutsche und englische Übersetzungen
- **mDNS Discovery**: Automatisches Auffinden von KKT Geräten
- **Options Flow**: Einstellungen nach Setup über UI änderbar
- **Diagnostics Download**: Debug-Informationen für Support

### ✅ **Qualität**

- **Gold Tier Compliance**: 100% Home Assistant Best Practices
- **Test Coverage**: Umfangreiche automatisierte Tests
- **Advanced Error Handling**: Automatische Repair Flows
- **46 Entities**: Davon viele optional aktivierbar

## ⚙️ Voraussetzungen

| Komponente | Mindestversion |
|------------|----------------|
| **Home Assistant** | 2025.1.0 |
| **Python** | 3.12 |
| **HACS** | Empfohlen (nicht zwingend) |

> **Hinweis:** Version 3.0.0 erfordert Home Assistant 2025.1.0 oder höher. Für ältere HA-Versionen bitte Version 2.9.x verwenden.

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

### 🚀 3-Wege Setup-Architektur (v2.0.0+)

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
- **Device ID**: 20-22 Zeichen Tuya Device ID
- **Local Key**: 16+ Zeichen Local Key aus Tuya/Smart Life App

### 🔑 Tuya API Setup - Vollstaendige Anleitung

Die Integration unterstützt sowohl **Tuya IoT Core** als auch **Smart Home Industry** Projekte. Smart Home Industry ist für die meisten Nutzer die richtige Wahl.

#### 📋 Schritt 1: Tuya IoT Platform Account erstellen

1. Gehe zu **[Tuya IoT Platform](https://iot.tuya.com)**
2. Klicke auf **"Sign Up"** (oben rechts)
3. Registriere dich mit E-Mail-Adresse
4. Bestätige deine E-Mail und melde dich an

#### 🏗️ Schritt 2: Smart Home Project erstellen

1. Nach dem Login auf **Tuya IoT Platform**:
   - Klicke auf **"Cloud"** → **"Development"**
   - Wähle **"Create Cloud Project"**

2. **Projekt-Details konfigurieren**:
   - **Project Name**: `Home Assistant` (oder beliebiger Name)
   - **Description**: `KKT Kolbe Integration for Home Assistant`
   - **Industry**: **`Smart Home`** ⚠️ WICHTIG!
   - **Development Method**: Wird automatisch gesetzt
   - **Data Center**: ⚠️ **WICHTIG** - Wähle deine Region:
     - 🇪🇺 **Central Europe** (Deutschland, Österreich, Schweiz)
     - 🇪🇺 **Western Europe** (Frankreich, Spanien, UK)
     - 🇺🇸 **Eastern America** (USA Ost)
     - 🇺🇸 **Western America** (USA West)
     - 🇨🇳 **China**
     - 🇮🇳 **India**

3. Klicke auf **"Create"**

> **💡 Hinweis**: Das Data Center **muss** mit der Region übereinstimmen, in der deine Smart Life App registriert ist!

#### 🔗 Schritt 3: Smart Life Account verknüpfen

Damit das API-Projekt deine Geräte sehen kann:

1. In deinem neuen Projekt → **"Devices"** Tab
2. Klicke auf **"Link Tuya App Account"** oder **"Add Device"**
3. Es öffnet sich ein QR-Code
4. **Smart Life App öffnen** auf deinem Handy:
   - Gehe zu **"Me"** (Profil) → **"Settings"** (⚙️)
   - Tippe auf **"Account and Security"**
   - Wähle **"Link"** oder **"Scan QR Code"**
5. Scanne den QR-Code vom Computer-Bildschirm
6. Bestätige die Verknüpfung

Nach erfolgreicher Verknüpfung sollten deine KKT-Geräte unter **"Devices"** erscheinen.

#### 🔐 Schritt 4: API Credentials abrufen

1. Gehe zu deinem Projekt → **"Overview"** Tab
2. Unter **"Authorization Key"** findest du:
   - **Access ID/Client ID**: `3wehyyv43tjqqm54qwst` (Beispiel, ~20 Zeichen)
   - **Access Secret/Client Secret**: `82f2cc1ec50f4a34abd8e1ff5df42508` (Beispiel, 32 Zeichen)
   - **Data Center**: `Central Europe Data Center` (oder deine gewählte Region)

3. **💾 Kopiere diese Werte** - du brauchst sie für die Integration!

#### 📝 Schritt 5: API Credentials in Home Assistant eingeben

1. **Home Assistant** öffnen
2. **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen**
3. Suche nach **"KKT Kolbe"**
4. Wähle **Setup Method**: `☁️ API-Only`
5. Gib deine API Credentials ein:
   - **Client ID**: Access ID aus Schritt 4
   - **Client Secret**: Access Secret aus Schritt 4
   - **Region**: Dein Data Center (z.B. `Central Europe`)
6. Wähle dein KKT-Gerät aus der Liste
7. **Fertig!** ✅

#### 💾 Credentials werden gespeichert

Nach der ersten Einrichtung:
- ✅ API Credentials werden **global gespeichert**
- ✅ Bei weiteren KKT-Geräten: Wähle **"Use Stored API Credentials"**
- ✅ Keine erneute Eingabe nötig

---

### 🆓 Free Tier vs Paid Tier

Die Integration funktioniert mit **Tuya Free Tier** Accounts:

| Feature | Free Tier | Paid Tier |
|---------|-----------|-----------|
| **API Calls/Monat** | Begrenzt (~1.000) | Unbegrenzt |
| **Device List** | ✅ Max. 20 Geräte | ✅ Unbegrenzt |
| **Authentication** | ✅ Unterstützt | ✅ Unterstützt |
| **Device Control** | ✅ Lokal (Offline) | ✅ Lokal & Cloud |
| **Status Updates** | ✅ Lokal Push | ✅ Cloud + Push |

> **💡 Empfehlung**: Die Integration nutzt hauptsächlich **lokale Kommunikation**, daher ist Free Tier für die meisten Nutzer ausreichend!

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

### 🤖 KI-Generierter Code - Sicherheitshinweise

> **WICHTIG:** Diese Integration wurde vollständig mit Anthropic's Claude Code entwickelt und ist Open Source.

**Verwendung auf eigene Verantwortung:**
- ✅ Der Code wurde **ausgiebig getestet** und erfüllt Home Assistant Gold Tier Standard (21/21 Anforderungen)
- ✅ **Open Source** - vollständiger Quellcode einsehbar
- ✅ **Aktiv entwickelt** - regelmäßige Updates und Bug-Fixes
- ⚠️ **Kochfeld-Steuerung**: Besondere Vorsicht geboten - niemals unbeaufsichtigt lassen
- 📖 Lies die **[Cooktop Safety Guide](docs/COOKTOP_SAFETY.md)** vor der ersten Verwendung
- 🔒 Security Issues melden via **[Security Policy](docs/SECURITY.md)**

**Was getestet wurde:**
- ✅ Dunstabzugshauben HERMES & STYLE, HERMES, ECCO HCM
- ✅ Induktionskochfeld IND7705HC
- ✅ Tuya API v2.0 & v1.0 (Free & Paid Tier)
- ✅ Smart Home Industry & IoT Core Projekte
- ✅ Lokale Kommunikation (Tuya Protocol 3.1, 3.3, 3.4, 3.5)

### Bekannte Limitationen
- **Netzwerkabhängig**: Funktioniert nur im lokalen Netzwerk (mit optional Cloud Fallback)
- **Device-spezifisch**: Konfigurationen sind modellspezifisch - andere KKT Modelle benötigen Anpassung
- **Firmware-abhängig**: Verschiedene Firmware-Versionen können unterschiedliche DPs haben

## 🐛 Troubleshooting

Für ausführliche Troubleshooting-Anleitungen siehe **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)**.

### Quick Reference

| Problem | Lösung |
|---------|--------|
| "Failed to connect" | Netzwerk/IP prüfen, Port 6668 freigeben |
| "Invalid local key" | Key neu extrahieren via TinyTuya |
| Entities "unavailable" | Integration neu laden, Debug-Logs prüfen |
| Discovery fehlgeschlagen | Manuelles Setup oder API-Only nutzen |
| API Setup fehlgeschlagen | Credentials und Region prüfen |

### Debug Logging aktivieren
```yaml
logger:
  logs:
    custom_components.kkt_kolbe: debug
```

### Support erhalten

- **[Troubleshooting Guide](./TROUBLESHOOTING.md)** - Ausführliche Anleitungen
- **[GitHub Issues](https://github.com/moag1000/HA-kkt-kolbe-integration/issues)** - Bug Reports
- **[Discussions](https://github.com/moag1000/HA-kkt-kolbe-integration/discussions)** - Fragen & Hilfe

## 📝 Changelog

### v3.0.2 (Aktuell) 🚀
- 🔧 **RGB Mode Select**: Farbnamen statt Zahlen (Weiß, Rot, Grün, Blau, etc.)
- 🔧 **Verbesserte Verfügbarkeit**: Entities bleiben während temporärer Verbindungsprobleme verfügbar
- 🔧 **Auto-Recovery**: Automatische Wiederherstellung bei Verbindungsverlust
- 🔧 **Dynamisches Polling**: Schnelleres Polling beim Reconnect, langsameres bei Offline
- 🔧 **Config Flow Fixes**: Keine "Flow already in progress" Fehler mehr bei Smart Discovery

### v3.0.1
- 🔧 Zeroconf Discovery Verbesserungen
- 🔧 Config Flow Konflikt-Handling

### v3.0.0
- ⚠️ **Breaking**: Mindestversion Home Assistant 2025.1.0
- Neue HA 2025 Features: `suggested_display_precision`, `_unrecorded_attributes`
- Modernisierte Type-Annotations

**[→ Vollständiges Changelog](./CHANGELOG.md)**

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

[releases-shield]: https://img.shields.io/github/v/release/moag1000/HA-kkt-kolbe-integration?style=for-the-badge
[releases]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases
[validate-shield]: https://img.shields.io/github/actions/workflow/status/moag1000/HA-kkt-kolbe-integration/validate.yml?style=for-the-badge&label=Validate
[validate]: https://github.com/moag1000/HA-kkt-kolbe-integration/actions/workflows/validate.yml
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