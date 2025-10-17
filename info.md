# KKT Kolbe Integration

<div align="center">
  <img src="https://raw.githubusercontent.com/moag1000/HA-kkt-kolbe-integration/main/icon.png" alt="KKT Kolbe Logo" width="128" height="128">
</div>

[![GitHub Release][releases-shield]][releases]
[![hacs][hacsbadge]][hacs]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license-url]

## 🚀 Smart Home Integration für KKT Kolbe Geräte

Diese Integration bringt deine **KKT Kolbe Dunstabzugshauben** und **Induktionskochfelder** in Home Assistant!

### ✨ Unterstützte Geräte (4 Modelle)

#### 🌬️ Dunstabzugshauben (3 Modelle)

**HERMES & STYLE Hood**
- **Lüftersteuerung** mit 5 Stufen
- **RGB Beleuchtung** mit 10 Modi
- **Timer-Funktion** (0-60 Minuten)
- **Filterüberwachung**

**HERMES Hood**
- **Lüftersteuerung** mit 5 Stufen
- **RGB Beleuchtung** mit Helligkeitssteuerung
- **Erweiterte Timer- und Filterverwaltung**
- **Eco-Modus** und Lärmkontrolle

**ECCO HCM Hood**
- **9-Stufen Lüftersteuerung** (0-9)
- **RGB Farbdaten** mit Arbeitsmodi (weiß/farbe/szene/musik)
- **Duale Filterüberwachung** (Kohle & Metall)
- **Wasch-Modus** und LED-Beleuchtung

#### 🔥 Induktionskochfeld IND7705HC
- **5 Kochzonen** mit individueller Steuerung
- **Timer pro Zone** (bis 255 Minuten)
- **Erweiterte Features**: Chef-Funktion, BBQ-Modus, Flex-Zonen
- **Sicherheit**: Kindersicherung, Pause/Resume

### 📦 Installation

1. **HACS** → **Integrations** → **⋮** → **Custom repositories**
2. Repository: `https://github.com/moag1000/HA-kkt-kolbe-integration`
3. Kategorie: `Integration`
4. **Installieren** → **Home Assistant neustarten**
5. **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen** → **KKT Kolbe**

### 🔧 Konfiguration

#### Option 1: Automatische Erkennung
Die Integration findet KKT Geräte automatisch im Netzwerk!

#### Option 2: Manuelle Konfiguration
- **IP-Adresse**: Lokale IP des Geräts
- **Device ID**: 20-22 Zeichen Tuya ID
- **Local Key**: Aus der Tuya/Smart Life App

### 🎯 Features

#### 🆕 NEU in v1.2.8: LocalTuya-Optimierte Authentifizierung
- ✨ **Automatische Geräteerkennung anhand Device ID** - Keine manuelle Typauswahl mehr nötig
- 🎭 **Benutzerfreundliches Setup** - Klare Geräteauswahl mit Dropdown-Menü
- 🗄️ **Zentrale Gerätedatenbank** - Zuverlässige Erkennung aller unterstützten Modelle
- 🔄 **Universelle Kompatibilität** - Funktioniert mit allen Setup-Methoden

#### 🏠 Bewährte Features
- ✅ **Automatische Geräteerkennung** (mDNS + UDP)
- ✅ **Vollständige Home Assistant Integration**
- ✅ **Deutsche & Englische Übersetzung**
- ✅ **Robuste Fehlerbehandlung**
- ✅ **Async/Await für beste Performance**

### ⚠️ Wichtiger Hinweis

Diese Integration wurde von KI (Claude) erstellt. Bei Kochfeldern ist besondere Vorsicht geboten. Verwendung auf eigene Gefahr!

### 📝 Links

- [Dokumentation](https://github.com/moag1000/HA-kkt-kolbe-integration#readme)
- [Bug Reports](https://github.com/moag1000/HA-kkt-kolbe-integration/issues)
- [Releases](https://github.com/moag1000/HA-kkt-kolbe-integration/releases)

---

**Version**: 1.5.6 | **Lizenz**: MIT | **Autor**: [@moag1000](https://github.com/moag1000)

[commits-shield]: https://img.shields.io/github/commit-activity/y/moag1000/HA-kkt-kolbe-integration.svg?style=for-the-badge
[commits]: https://github.com/moag1000/HA-kkt-kolbe-integration/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge
[license-url]: https://opensource.org/licenses/MIT
[releases-shield]: https://img.shields.io/badge/version-v1.5.6-blue.svg?style=for-the-badge
[releases]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases