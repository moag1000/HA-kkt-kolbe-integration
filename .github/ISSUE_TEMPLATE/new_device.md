---
name: Neues KKT Kolbe Gerät
about: Unterstützung für ein neues KKT Kolbe Modell hinzufügen
title: '[DEVICE] Unterstützung für KKT [Modellname]'
labels: enhancement, new-device
---

## Geräteinformationen

**Modell:** KKT [Modellname]
**Kategorie:** [z.B. Dunstabzugshaube, Kochfeld, etc.]
**Device ID:** `bf...........` (anonymisiert - letzten 4 Zeichen entfernt)

## Tuya IoT Platform - Query Things Data Model

**WICHTIG:** Verwenden Sie einen separaten Tuya IoT Developer Account (nicht Smart Life App Account)

```json
{
  "result": {
    "model": "JSON_OUTPUT_HIER_EINFÜGEN"
  },
  "success": true
}
```

## Gewünschte Funktionen

- [ ] Funktion 1 (z.B. Lüftersteuerung)
- [ ] Funktion 2 (z.B. Beleuchtung)
- [ ] Funktion 3 (z.B. Timer)

## Zusätzliche Informationen

- **Smart Life App Features:** [Was kann die App steuern?]
- **Besonderheiten:** [Spezielle Modi, Einstellungen, etc.]
- **Sicherheitsaspekte:** [Besonders wichtig bei Kochfeldern!]

## Verfügbarkeit für Tests

- [ ] Ich habe Zugang zu diesem Gerät für Tests
- [ ] Ich kann bei der Entwicklung helfen
- [ ] Ich verstehe die Sicherheitsrisiken bei KI-generiertem Code

---

**⚠️ WARNUNG:** Alle Tests erfolgen auf eigene Gefahr! Besonders bei Kochfeldern können Fehler zu gefährlichen Situationen führen.