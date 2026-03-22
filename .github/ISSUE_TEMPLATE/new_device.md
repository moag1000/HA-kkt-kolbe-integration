---
name: Neues KKT Kolbe Gerät
about: Unterstützung für ein neues KKT Kolbe Modell hinzufügen
title: '[DEVICE] Unterstützung für KKT [Modellname]'
labels: enhancement, new-device
---

## Geräteinformationen

**Modell:** KKT [Modellname]
**Kategorie:** [z.B. Dunstabzugshaube, Kochfeld, Backofen, etc.]
**Device ID:** `bf...........` (anonymisiert - letzten 4 Zeichen entfernt)

## Tuya Things Data Model

Die Integration benötigt die Tuya Data Points (DPs) deines Gerätes. Es gibt zwei Wege diese auszulesen:

### Option A: Über die Tuya IoT Platform (empfohlen)

1. Tuya IoT Account erstellen: https://iot.tuya.com
2. Cloud-Projekt anlegen (Region: EU)
3. SmartLife-App mit dem Cloud-Projekt verknüpfen
4. API Explorer > "Query Things Data Model" > Geräte-ID eingeben
5. JSON-Ergebnis hier einfügen:

```json
{
  "result": {
    "model": "JSON_OUTPUT_HIER_EINFÜGEN"
  },
  "success": true
}
```

### Option B: Über die Integration (Debug-Log)

1. Home Assistant Logger auf Debug setzen:
   ```yaml
   logger:
     logs:
       custom_components.kkt_kolbe: debug
   ```
2. Gerät einrichten (manuell oder SmartLife)
3. In den Logs nach `DP` und `data_point` Einträgen suchen
4. Relevante Log-Zeilen hier einfügen

## Funktionen in der SmartLife/KKT Control App

Bitte beschreibe alle Steuerungsmöglichkeiten die in der App verfügbar sind:

- [ ] Ein/Aus
- [ ] Temperatureinstellung (Bereich: __ bis __ °C)
- [ ] Betriebsmodi (welche: __________________)
- [ ] Timer/Countdown
- [ ] Kindersicherung
- [ ] Licht
- [ ] Sonstiges: __________________

**SmartLife Screenshots** (optional, hilfreich): Steuerungsbildschirm der App.

## Speziell für Backofen-Besitzer (EB8313HC, EB8317HC, EB8313ED)

Die Integration hat bereits eine vorbereitete Backofen-Konfiguration mit geschätzten DPs.
Mit deinen Things Data Model Daten können wir die korrekten DPs einpflegen.

Zusätzliche Angaben:
- [ ] Welche Kochmodi/Programme sind verfügbar?
- [ ] Temperaturbereich (min/max)?
- [ ] Hat dein Modell einen Kerntemperaturfühler?
- [ ] Gibt es eine Vorheizfunktion in der App?
- [ ] Gibt es eine Dampfreinigungsfunktion in der App?

## Verfügbarkeit

- [ ] Ich habe Zugang zu diesem Gerät und kann testen
- [ ] Ich kann bei der Entwicklung helfen
- [ ] Ich verstehe die Risiken bei experimenteller Gerätesteuerung

---

**Hinweis:** Besonders bei Backöfen und Kochfeldern ist Vorsicht geboten. Erste Tests nur unter Aufsicht und bei niedrigen Leistungsstufen/Temperaturen durchführen.
