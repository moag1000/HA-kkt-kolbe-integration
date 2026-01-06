# KKT Kolbe Integration

<div align="center">
  <img src="https://raw.githubusercontent.com/moag1000/HA-kkt-kolbe-integration/main/icon.png" alt="KKT Kolbe Logo" width="128" height="128">
</div>

[![GitHub Release][releases-shield]][releases]
[![hacs][hacsbadge]][hacs]
[![License][license-shield]][license-url]

## Home Assistant Integration für KKT Kolbe Geräte

Diese Integration bringt **KKT Kolbe Dunstabzugshauben** und **Induktionskochfelder** in Home Assistant mit einfachem SmartLife/Tuya Smart Setup.

### Highlights v4.0.0

✨ **QR-Code Setup mit SmartLife/Tuya Smart App**
- Kein Developer Account erforderlich
- Local Key wird automatisch erkannt
- Setup in unter 1 Minute

🔄 **Auto-Power-On für Dunstabzugshauben**
- Hood wird automatisch eingeschaltet wenn Fan/Licht gesteuert wird
- Intelligente Zustandsanzeige (Fan/Licht zeigen "aus" wenn Hood aus)

🔑 **SmartLife Account Wiederverwendung**
- Neue Geräte ohne Re-Authentifizierung hinzufügen
- Token werden automatisch aktualisiert

### Unterstützte Geräte

#### Dunstabzugshauben
- **HERMES & STYLE** - 5-Stufen Lüfter, RGB Beleuchtung, Timer
- **HERMES** - 5-Stufen Lüfter, RGB Beleuchtung, Filterverwaltung
- **ECCO HCM** - 9-Stufen Lüfter, Multi-Light Control, Wasch-Modus
- **SOLO HCM** - Lüfter, Beleuchtung, Wasch-Modus

#### Induktionskochfeld
- **IND7705HC** - 5 Kochzonen, Timer pro Zone, Kindersicherung

### Installation

1. **HACS** → **Integrations** → **Custom repositories**
2. Repository: `https://github.com/moag1000/HA-kkt-kolbe-integration`
3. Kategorie: `Integration`
4. **Installieren** → **Home Assistant neustarten**
5. **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen** → **KKT Kolbe**

### Setup-Methoden

#### SmartLife/Tuya Smart (Empfohlen)
- Einfaches QR-Code Setup
- Kein Tuya Developer Account nötig
- Local Key automatisch abgerufen
- Multi-Device Support
- Automatische Geräteerkennung

#### Manuelle Konfiguration
- IP-Adresse, Device ID, Local Key manuell eingeben
- Für Experten ohne Cloud-Zugang

#### IoT Platform (Fortgeschritten)
- Für bestehende Tuya Developer Accounts
- Erweiterte Debugging-Möglichkeiten

Weitere Details im [SmartLife Setup Guide](https://github.com/moag1000/HA-kkt-kolbe-integration/blob/main/docs/SMARTLIFE_SETUP.md).

### Hinweis

Diese Integration wurde mit Claude (Anthropic) entwickelt. Der Code ist Open Source und getestet, aber **Verwendung erfolgt auf eigene Verantwortung** - besonders bei der Kochfeld-Steuerung.

### Links

- [Vollständige Dokumentation](https://github.com/moag1000/HA-kkt-kolbe-integration#readme)
- [SmartLife Setup Guide](https://github.com/moag1000/HA-kkt-kolbe-integration/blob/main/docs/SMARTLIFE_SETUP.md)
- [Bug Reports](https://github.com/moag1000/HA-kkt-kolbe-integration/issues)
- [Releases](https://github.com/moag1000/HA-kkt-kolbe-integration/releases)

---

**Version**: 4.0.0 | **Lizenz**: MIT | **Autor**: [@moag1000](https://github.com/moag1000)

[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge
[license-url]: https://opensource.org/licenses/MIT
[releases-shield]: https://img.shields.io/github/v/release/moag1000/HA-kkt-kolbe-integration?style=for-the-badge
[releases]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases
