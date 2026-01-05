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

> **Neu in v4.0.0:** Setup jetzt noch einfacher - **kein Tuya Developer Account mehr nötig!** Einfach SmartLife App nutzen und QR-Code scannen.

> **KI-Generiert:** Diese Integration wurde mit Anthropic's Claude entwickelt. Der Code ist Open Source und wurde ausgiebig getestet, aber **Verwendung erfolgt auf eigene Verantwortung** - besonders bei der Kochfeld-Steuerung!

> **Quality:** Diese Integration folgt Home Assistant Best Practices mit vollständiger Typ-Annotation, async I/O, robustem Error Handling, automatischer Wiederherstellung und Tests.

---

## Quick Start (Empfohlen)

Die **einfachste Methode** - kein Tuya Developer Account erforderlich!

1. **SmartLife** oder **Tuya Smart** App installieren und KKT-Geräte hinzufügen
2. In der App: **Ich** → **Einstellungen** (Zahnrad) → **Konto und Sicherheit** → **User Code** kopieren
3. In Home Assistant: **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen** → **KKT Kolbe**
4. **SmartLife / Tuya Smart** als Setup-Methode auswählen (Standard)
5. **User Code** eingeben und **QR-Code** mit der App scannen
6. KKT Kolbe Gerät auswählen - **fertig!**

**[Ausführliche SmartLife Setup-Anleitung →](docs/SMARTLIFE_SETUP.md)**

### Setup-Methoden im Vergleich

| Methode | Developer Account | Local Key | Schwierigkeit | Setup-Zeit |
|---------|-------------------|-----------|---------------|------------|
| **SmartLife QR-Code** (empfohlen) | Nein | Automatisch | Einfach | ~1 Min |
| Smart Discovery (IoT Platform) | Ja | Automatisch | Mittel | ~15 Min |
| Manual Setup | Nein | Manuell (tinytuya) | Schwer | ~5 Min |

---

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

### 🆕 **Neu in v4.0.0: SmartLife App Integration** 🚀

> **Kein Developer Account mehr nötig!** Setup in unter 1 Minute.

#### **SmartLife / Tuya Smart App Setup**
- ✅ **QR-Code Authentifizierung**: Einfaches Setup ohne Tuya IoT Platform
- ✅ **Automatischer Local Key Abruf**: Kein manuelles Kopieren mehr nötig
- ✅ **Keine API-Subscription**: Keine 30-Tage Trial die abläuft
- ✅ **Automatische Token-Erneuerung**: Nahtlose Re-Authentifizierung

**[Vollständige SmartLife Setup-Anleitung →](docs/SMARTLIFE_SETUP.md)**

---

### Home Assistant 2025.1+ Optimierungen

> ⚠️ **Breaking Change:** Erfordert Home Assistant 2025.1.0 oder höher

#### **Moderne HA 2025 Features**
- ✅ **`suggested_display_precision`**: Saubere Anzeige ohne unnötige Dezimalstellen
- ✅ **`_unrecorded_attributes`**: Reduzierte Datenbankgröße durch Ausschluss nicht-historischer Attribute
- ✅ **`ConfigFlowResult`**: Modernisierte Type-Annotations für Config Flow
- ✅ **Model ID aus KNOWN_DEVICES**: Bessere Geräteidentifikation in der UI

#### **Verbesserungen**
- Timer, Filter-Tage, Power-Level werden als ganze Zahlen angezeigt
- Temperatur-Sensoren zeigen 1 Dezimalstelle
- Weniger Datenbank-Einträge für diagnostische Attribute

#### **Reconfigure Flow**
Bestehende Geräte können jetzt über die UI neu konfiguriert werden:
- **Connection**: IP-Adresse und Local Key ändern
- **Device Type**: Gerätetyp korrigieren
- **API Settings**: Cloud API aktivieren/deaktivieren
- **All Settings**: Alle Einstellungen auf einmal

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
- Fan: Vollständige Geschwindigkeitssteuerung via HomeKit
- Light: An/Aus Steuerung
- RGB-Modi: Via Szenen in Apple Home steuerbar

> **Hinweis:** HomeKit unterstützt keine Light-Effects direkt. RGB-Modi können über Home Assistant Szenen gesteuert werden, die dann in Apple Home verfügbar sind.
> → [Vollständige HomeKit-Anleitung mit Szenen-Setup](docs/HOMEKIT.md)

## 📘 Blueprints

Fertige Automations-Vorlagen zum Importieren:

| Blueprint | Beschreibung | Import |
|-----------|--------------|--------|
| Hood Auto-Off | Schaltet Haube nach X Min aus | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmoag1000%2FHA-kkt-kolbe-integration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fhood_auto_off.yaml) |
| Hood Light Auto-Off | Schaltet Licht nach X Min aus | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmoag1000%2FHA-kkt-kolbe-integration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fhood_light_auto_off.yaml) |
| Hood with Cooktop | Synchronisiert Haube mit Kochfeld | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fmoag1000%2FHA-kkt-kolbe-integration%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fhood_with_cooktop.yaml) |

[Alle Blueprints →](blueprints/README.md)

## 📚 Documentation & Examples

- **[SmartLife Setup](docs/SMARTLIFE_SETUP.md)** - Einfaches Setup ohne Developer Account (empfohlen)
- **[Blueprints](blueprints/README.md)** - One-click automation templates
- **[Automation Examples](docs/AUTOMATION_EXAMPLES.md)** - 15+ ready-to-use automation examples
- **[Use Cases](docs/USE_CASES.md)** - Practical scenarios and implementation guides
- **[Apple Home / HomeKit](docs/HOMEKIT.md)** - HomeKit integration with scenes for RGB control
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

### 🚀 4-Wege Setup-Architektur (v4.0.0)

Wähle bei der Installation eine der vier Setup-Methoden:

#### **📱 SmartLife / Tuya Smart App** ✅ Empfohlen (Neu in v4.0.0)
**Die einfachste Methode - kein Developer Account erforderlich!**

1. Setup Method: **SmartLife/Tuya Smart App** wählen
2. **User Code** aus der App eingeben
3. **QR-Code** mit der App scannen
4. Gerät auswählen - fertig!

**Vorteile:**
- Kein Tuya IoT Developer Account nötig
- Keine API-Subscription die abläuft
- Local Key wird automatisch abgerufen
- Setup in unter 1 Minute
- Automatische Token-Erneuerung

**[Ausführliche Anleitung →](docs/SMARTLIFE_SETUP.md)**

---

#### **☁️ API-Only Setup (IoT Platform)**
**Für Nutzer mit bestehendem Tuya Developer Account**

**Erstes Gerät:**
1. Setup Method: API-Only wählen
2. TinyTuya Credentials eingeben (Client ID, Secret, Region)
3. Device aus API-Discovery wählen
4. Credentials werden automatisch gespeichert

**Weitere Geräte:**
1. Setup Method: API-Only wählen
2. "Use Stored API Credentials" wählen
3. Device aus Liste wählen
4. Fertig

**Vorteile:**
- Keine Local Key Extraktion nötig
- Funktioniert auch außerhalb des Heimnetzwerks
- API Keys nur einmal eingeben
- Schnellerer Setup für weitere Geräte

#### **🔍 Automatic Discovery**
Die Integration findet KKT Geräte automatisch im lokalen Netzwerk über mDNS.

#### **🔧 Manual Local Setup**
Für erfahrene Nutzer mit spezifischen Anforderungen:
- **IP-Adresse**: Lokale IP des Geräts (z.B. 192.168.1.100)
- **Device ID**: 20-22 Zeichen Tuya Device ID
- **Local Key**: 16+ Zeichen Local Key aus Tuya/Smart Life App

### 🔑 Tuya API Setup (Alternative Methode)

> **Hinweis:** Die meisten Nutzer sollten die [SmartLife App Methode](#-smartlife--tuya-smart-app--empfohlen-neu-in-v400) verwenden. Diese Anleitung ist nur für Nutzer relevant, die bereits einen Tuya Developer Account haben oder erweiterte Debugging-Möglichkeiten benötigen.

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

## ❓ Häufige Fragen (FAQ)

### Brauche ich einen Tuya Developer Account?

**Nein!** Seit Version 4.0.0 ist kein Tuya IoT Developer Account mehr erforderlich.

Mit der neuen **SmartLife / Tuya Smart App Methode** kannst du:
- Direkt über die App authentifizieren (QR-Code)
- Local Keys automatisch abrufen
- Ohne API-Subscription arbeiten

Die einzige Voraussetzung ist die **SmartLife** oder **Tuya Smart** App auf deinem Smartphone.

---

### Wo finde ich den User Code?

Der User Code ist in der SmartLife/Tuya Smart App unter:

**Ich** → **Einstellungen** (Zahnrad-Symbol) → **Konto und Sicherheit** → **User Code**

Der Code hat das Format: `XX12345678` (z.B. `EU12345678`)

**[Detaillierte Anleitung mit Screenshots →](docs/SMARTLIFE_SETUP.md#wo-finde-ich-den-user-code)**

---

### Was ist der Unterschied zwischen SmartLife und Tuya Smart?

Beide Apps sind funktional identisch und werden von Tuya entwickelt:

| App | Icon | Funktionen |
|-----|------|------------|
| **SmartLife** | Grün | Identisch |
| **Tuya Smart** | Rot | Identisch |

Du kannst **beide Apps** für das Setup verwenden. Wichtig ist nur, dass du im Setup-Dialog die **gleiche App** auswählst, die du auf deinem Smartphone nutzt.

---

### Warum SmartLife statt Tuya IoT Platform?

| Aspekt | SmartLife App | Tuya IoT Platform |
|--------|---------------|-------------------|
| **Developer Account** | Nicht nötig | Erforderlich |
| **API-Subscription** | Nicht nötig | Trial läuft nach 30 Tagen ab |
| **Setup-Zeit** | ~1 Minute | ~15 Minuten |
| **Local Key** | Automatisch | Automatisch |
| **Komplexität** | Einfach | Fortgeschritten |

Die SmartLife Methode ist für **alle Nutzer empfohlen**, außer du hast bereits einen aktiven Tuya Developer Account.

---

## 🐛 Troubleshooting

### 📱 SmartLife Setup Probleme

#### **Problem: QR-Code wird nicht erkannt**

**Lösungen:**
1. Bildschirm-Helligkeit erhöhen
2. Smartphone ca. 15-20 cm vom Bildschirm entfernen
3. Sicherstellen, dass die im Setup gewählte App verwendet wird
4. App auf neueste Version aktualisieren

---

#### **Problem: QR-Code abgelaufen / Timeout**

Der QR-Code ist nur ca. 2 Minuten gültig.

**Lösung:**
1. Setup-Vorgang in Home Assistant abbrechen
2. Erneut starten
3. Neuen QR-Code zügig scannen

---

#### **Problem: User Code nicht gefunden**

**Lösungen:**
1. App im App Store / Play Store aktualisieren
2. Alternative App versuchen (SmartLife statt Tuya Smart oder umgekehrt)
3. Prüfen ob du in der richtigen Region eingeloggt bist

**[Detaillierte Anleitung →](docs/SMARTLIFE_SETUP.md#wo-finde-ich-den-user-code)**

---

#### **Problem: "Token abgelaufen" / Re-Authentifizierung erforderlich**

**Lösung:**
1. In Home Assistant auf die Meldung klicken
2. Reauth-Flow folgen
3. User Code erneut eingeben
4. Neuen QR-Code scannen

---

### ⚠️ Allgemeine Probleme & Lösungen

#### **Problem: "Failed to connect" / "Device not responding"**

**Mögliche Ursachen:**
- Gerät ist offline oder nicht im Netzwerk erreichbar
- Falsche IP-Adresse
- Firewall blockiert Port 6668
- Device ID oder Local Key falsch

**Lösungen:**
1. **Netzwerk prüfen:**
   ```bash
   ping 192.168.1.100  # Deine Gerät-IP
   ```
2. **Port-Erreichbarkeit testen:**
   ```bash
   telnet 192.168.1.100 6668
   ```
3. **Firewall-Regel hinzufügen** (falls nötig):
   - Erlaube ausgehende Verbindungen auf Port 6668
   - Für Docker/VM: Bridge-Netzwerk prüfen

4. **IP-Adresse validieren:**
   - Router-Admin-Interface → DHCP-Clients
   - Smart Life App → Geräteinfo
   - DHCP-Reservation empfohlen!

5. **Device ID/Local Key neu extrahieren:**
   - Siehe [Local Key Extraktion](#local-key-extraktion-nur-für-manual-local-setup)
   - Bei Fehlern: Gerät in Smart Life App neu einrichten

---

#### **Problem: "Authentication failed" / "Invalid local key"**

**Symptom:** Integration startet Reauth-Flow automatisch

**Ursache:** Local Key ist falsch oder wurde geändert

**Lösung:**
1. **Neuen Local Key extrahieren:**
   - TinyTuya Wizard erneut ausführen
   - Oder Tuya IoT Platform nutzen

2. **Reauth-Flow nutzen:**
   - Benachrichtigung in Home Assistant klicken
   - Neuen Local Key eingeben
   - Integration wird automatisch neu verbunden

3. **Häufige Fehler:**
   - ❌ Local Key enthält Leerzeichen → Entfernen
   - ❌ Groß-/Kleinschreibung → Exakt kopieren
   - ❌ Unvollständiger Key → Muss 16+ Zeichen sein

---

#### **Problem: Entities zeigen "unavailable" / "unknown"**

**Temporäre Unavailable (< 5 Minuten):**
- Normal beim Home Assistant Neustart
- Gerät neu hochgefahren
- → Keine Aktion nötig, wartet auf Reconnect

**Dauerhafte Unavailable (> 5 Minuten):**

**Lösungen:**
1. **Integration neu laden:**
   - Einstellungen → Geräte & Dienste
   - KKT Kolbe → ⋮ → Integration neu laden

2. **Coordinator Status prüfen:**
   - Entwicklerwerkzeuge → Zustände
   - Suche nach `sensor.*.last_update`
   - Wenn Timestamp alt: Connection Problem

3. **Debug Logging aktivieren:**
   ```yaml
   # configuration.yaml
   logger:
     default: info
     logs:
       custom_components.kkt_kolbe: debug
   ```
   Home Assistant neustarten → Log prüfen

4. **Gerät in Tuya App prüfen:**
   - Ist es dort online?
   - Funktioniert manuelle Steuerung?
   - Falls nein: Gerät neu starten

---

#### **Problem: "Device discovery failed" / Gerät wird nicht gefunden**

**Bei Automatic Discovery:**

**Lösungen:**
1. **Zeroconf/mDNS prüfen:**
   - Einige Router blockieren mDNS
   - Multicast-Support aktivieren
   - Alternative: Manuelles Setup nutzen

2. **Gleiches Netzwerk:**
   - Home Assistant und Gerät im selben VLAN
   - Keine Netzwerk-Isolation (IoT-VLAN trennen)

3. **Gerät neu starten:**
   - Power-Cycle des Geräts
   - 30 Sekunden warten
   - Discovery erneut versuchen

**Workaround:** Nutze **Manual Local Setup** oder **API-Only Setup**

---

#### **Problem: API-Only Setup schlägt fehl**

**Error: "API authentication failed"**

**Lösungen:**
1. **Credentials prüfen:**
   - Access ID (Client ID) korrekt?
   - Access Secret korrekt kopiert?
   - Richtige Region gewählt? (EU/US/CN/IN)

2. **API Services aktiviert?**
   - [Tuya IoT Platform](https://iot.tuya.com)
   - Cloud Project → Service API
   - Alle erforderlichen APIs aktivieren

3. **App Account verknüpft?**
   - Smart Life App mit Cloud Project verbunden?
   - QR-Code gescannt?
   - Geräte sichtbar in Tuya IoT Platform?

**Error: "No devices found"**

**Lösungen:**
1. **App Account Link prüfen:**
   - Tuya IoT Platform → Cloud → Devices
   - Sind deine Geräte gelistet?
   - Falls nein: App Account erneut verknüpfen

2. **Geräte-Region:**
   - Stelle sicher, Projekt und Geräte in gleicher Region
   - EU-Geräte brauchen EU Data Center

---

### 🔍 Debug-Informationen sammeln

Für Support-Anfragen bitte folgende Infos bereitstellen:

**1. System-Info:**
```yaml
Home Assistant Version: 2025.x.x  # Mindestens 2025.1.0
KKT Kolbe Integration Version: 4.0.0
Installation Method: HACS / Manual
Python Version: 3.12+
```

**2. Gerät-Info:**
```yaml
Device Model: DH9509NP / IND7705HC / etc.
Firmware Version: (aus Smart Life App)
Setup Method: SmartLife / Discovery / Manual / API-Only
IP Address: 192.168.1.100
```

**3. Debug Log:**
```bash
# configuration.yaml aktivieren, dann:
cat home-assistant.log | grep "kkt_kolbe"
```

**4. Diagnostics Download:**
- Einstellungen → Geräte & Dienste
- KKT Kolbe Device → ⋮ → Download diagnostics
- Datei an GitHub Issue anhängen

---

### 📞 Support erhalten

**GitHub Issues:** [Issue erstellen](https://github.com/moag1000/HA-kkt-kolbe-integration/issues)
**Discussions:** [Community Diskussionen](https://github.com/moag1000/HA-kkt-kolbe-integration/discussions)

**Template für Issue:**
```markdown
## Problem Description
[Beschreibe das Problem]

## Steps to Reproduce
1. ...
2. ...

## Expected Behavior
[Was sollte passieren]

## Actual Behavior
[Was passiert tatsächlich]

## Environment
- HA Version:
- Integration Version:
- Device Model:

## Logs
[Debug logs hier einfügen]
```

## 📝 Changelog

### v4.0.0 (Aktuell) 🚀
- **SmartLife / Tuya Smart App Integration** - Kein Developer Account mehr nötig!
- QR-Code basierte Authentifizierung
- Automatischer Local Key Abruf
- Automatische Token-Erneuerung
- Vereinfachtes Setup in unter 1 Minute

### v3.1.0
- Light Effects mit `effect_offset` für korrekte RGB-Modi Indizierung
- **[Apple Home / HomeKit Dokumentation](docs/HOMEKIT.md)** mit Szenen-Setup
- RGB Mode Select für HERMES & STYLE Hauben hinzugefügt

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