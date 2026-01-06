# KKT Kolbe Integration

<div align="center">
  <img src="https://raw.githubusercontent.com/moag1000/HA-kkt-kolbe-integration/main/icon.png" alt="KKT Kolbe Logo" width="128" height="128">

  **Home Assistant Integration für KKT Kolbe Küchengeräte**

  [![GitHub Release][releases-shield]][releases]
  [![HACS][hacsbadge]][hacs]
  [![License][license-shield]][license-url]

  *Dunstabzugshauben und Induktionskochfelder lokal steuern*
</div>

---

## Highlights v4.0.0

- **Kein Developer Account nötig** - Setup via SmartLife/Tuya Smart App
- **Auto-Power-On** - Hood schaltet automatisch ein bei Fan/Licht-Steuerung
- **Account Wiederverwendung** - Neue Geräte ohne Re-Authentifizierung
- **Lokale Steuerung** - Tuya Protocol ohne Cloud-Abhängigkeit

---

## Quick Start

```
1. SmartLife/Tuya Smart App → KKT-Gerät hinzufügen
2. App: Ich → Einstellungen → Konto und Sicherheit → User Code kopieren
3. Home Assistant: Integration hinzufügen → "KKT Kolbe"
4. User Code eingeben → QR-Code mit App scannen → Fertig!
```

---

## Unterstützte Geräte

### Dunstabzugshauben

| Modell | Lüfter | Licht | RGB | Timer |
|--------|--------|-------|-----|-------|
| **HERMES & STYLE** | 5 Stufen | ✅ | 10 Modi | ✅ |
| **HERMES** | 5 Stufen | ✅ | 10 Modi | ✅ |
| **ECCO HCM** | 9 Stufen | Multi | 4 Modi | ✅ |
| **SOLO HCM** | 5 Stufen | ✅ | - | ✅ |

### Induktionskochfeld

| Modell | Zonen | Features |
|--------|-------|----------|
| **IND7705HC** | 5 | Power, Timer, Temp, Boost, Flex |

---

## Installation (HACS)

1. **HACS** → **Integrations** → ⋮ → **Custom repositories**
2. URL: `https://github.com/moag1000/HA-kkt-kolbe-integration`
3. Kategorie: **Integration** → Installieren → Neustarten

---

## Setup-Methoden

| Methode | Developer Account | Empfohlen |
|---------|-------------------|-----------|
| **SmartLife QR-Code** | Nein | ✅ |
| IoT Platform API | Ja | - |
| Manual (tinytuya) | Nein | - |

---

## Voraussetzungen

| Komponente | Version |
|------------|---------|
| Home Assistant | ≥ 2025.12.0 |
| Python | ≥ 3.12 |

---

## Links

- [Vollständige Dokumentation](https://github.com/moag1000/HA-kkt-kolbe-integration#readme)
- [SmartLife Setup Guide](https://github.com/moag1000/HA-kkt-kolbe-integration/blob/main/docs/SMARTLIFE_SETUP.md)
- [Troubleshooting](https://github.com/moag1000/HA-kkt-kolbe-integration/blob/main/TROUBLESHOOTING.md)
- [Bug Reports](https://github.com/moag1000/HA-kkt-kolbe-integration/issues)

---

**Version**: 4.0.0 | **Lizenz**: MIT | **Autor**: [@moag1000](https://github.com/moag1000)

> Entwickelt mit [Claude Code](https://claude.ai/code) - Verwendung auf eigene Verantwortung.

[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge
[license-url]: https://opensource.org/licenses/MIT
[releases-shield]: https://img.shields.io/github/v/release/moag1000/HA-kkt-kolbe-integration?style=for-the-badge
[releases]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases
