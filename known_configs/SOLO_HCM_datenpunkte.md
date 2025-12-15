# Datenpunkte (DPs) für KKT Kolbe SOLO HCM Dunstabzugshaube

## Geräte-Informationen

- **Modell**: KKT Kolbe SOLO HCM
- **Model-ID**: `edjszs` (ähnlich ECCO HCM `edjsx0`)
- **Produkt-ID**: `bgvbvjwomgbisd8x`
- **Device-ID**: `bf34515c4ab6ec7f9axqy8`
- **Kategorie**: `yyj` (Dunstabzugshaube)
- **Produktseite**: https://www.kolbe.de/Dunstabzugshaube-60cm-SOLO6005S

## Wichtige Erkenntnis

**Die SOLO HCM basiert auf der ECCO HCM Struktur, NICHT auf der HERMES!**

Entgegen der Produktseite hat die SOLO HCM:
- ✅ **RGB Beleuchtung** (work_mode: white/colour/scene/music)
- ✅ **9 Lüfterstufen** (0-9, nicht enum)
- ✅ **Duale Filterüberwachung** (Kohle + Metall)

## Alle Datenpunkte (verifiziert via Things Data Model)

| DP | Code | Name | Typ | Bereich | Status |
|----|------|------|-----|---------|--------|
| 1 | `switch` | ON/OFF | bool | - | ✅ Aktiv |
| 4 | `light` | Light | bool | - | ✅ Aktiv |
| 6 | `switch_lamp` | RGB-Switch | bool | - | ✅ Aktiv |
| 7 | `switch_wash` | Setting/Wash | bool | - | ✅ Aktiv |
| 102 | `fan_speed` | Lüftergeschwindigkeit | value | 0-9 | ✅ Aktiv |
| 103 | `day` | Kohlefilter Tage | value | 0-250 | ✅ Aktiv |
| 104 | `switch_led_1` | LED-Light | bool | - | ✅ Aktiv |
| 105 | `countdown_1` | Countdown Timer | value | 0-60 min | ✅ Aktiv |
| 106 | `switch_led` | Confirm | bool | - | ✅ Aktiv |
| 107 | `colour_data` | RGB Farbdaten | string | max 255 | ✅ Aktiv |
| 108 | `work_mode` | RGB Arbeitsmodus | enum | white/colour/scene/music | ✅ Aktiv |
| 109 | `day_1` | Metallfilter Tage | value | 0-40 | ✅ Aktiv |

## Vergleich mit anderen Modellen

| Feature | SOLO HCM | ECCO HCM | HERMES |
|---------|----------|----------|--------|
| Model ID | `edjszs` | `edjsx0` | `e1k6i0zo` |
| Lüfter-DP | 102 (0-9) | 102 (0-9) | 10 (enum) |
| Timer-DP | 105 | 105 | 13 |
| RGB | DP 107/108 ✅ | DP 107/108 ✅ | DP 101 |
| Kohlefilter | DP 103 ✅ | DP 103 ✅ | - |
| Metallfilter | DP 109 ✅ | DP 109 ✅ | - |

**Fazit**: SOLO HCM ≈ ECCO HCM (nur andere Model-ID)

## Home Assistant Entities

Nach erfolgreicher Einrichtung werden folgende Entities erstellt:

### Switches
- `switch.solo_hcm_power` - Hauptschalter
- `switch.solo_hcm_light` - Hauptlicht
- `switch.solo_hcm_rgb_light` - RGB Beleuchtung
- `switch.solo_hcm_led_light` - LED Streifen
- `switch.solo_hcm_wash_mode` - Reinigungsmodus (advanced)
- `switch.solo_hcm_confirm` - Bestätigen (advanced)

### Numbers
- `number.solo_hcm_fan_speed` - Lüftergeschwindigkeit (0-9)
- `number.solo_hcm_timer` - Timer (0-60 min)
- `number.solo_hcm_carbon_filter_remaining` - Kohlefilter Tage (diagnostic)
- `number.solo_hcm_metal_filter_remaining` - Metallfilter Tage (diagnostic)

### Selects
- `select.solo_hcm_rgb_mode` - RGB Modus (white/colour/scene/music)

## Things Data Model (Original)

```json
{
  "result": {
    "model": "{\"modelId\":\"edjszs\",\"services\":[{\"properties\":[{\"abilityId\":1,\"code\":\"switch\",\"name\":\"ON\\\\OFF\",\"typeSpec\":{\"type\":\"bool\"}},{\"abilityId\":4,\"code\":\"light\",\"name\":\"Light\",\"typeSpec\":{\"type\":\"bool\"}},{\"abilityId\":6,\"code\":\"switch_lamp\",\"name\":\"RGB-Switch\",\"typeSpec\":{\"type\":\"bool\"}},{\"abilityId\":7,\"code\":\"switch_wash\",\"name\":\"Setting\",\"typeSpec\":{\"type\":\"bool\"}},{\"abilityId\":102,\"code\":\"fan_speed\",\"name\":\"风速\",\"typeSpec\":{\"type\":\"value\",\"max\":9,\"min\":0}},{\"abilityId\":103,\"code\":\"day\",\"name\":\"change carborn filter\",\"typeSpec\":{\"type\":\"value\",\"max\":250,\"min\":0,\"unit\":\"day\"}},{\"abilityId\":104,\"code\":\"switch_led_1\",\"name\":\"LED-Light\",\"typeSpec\":{\"type\":\"bool\"}},{\"abilityId\":105,\"code\":\"countdown_1\",\"name\":\"Countdown\",\"typeSpec\":{\"type\":\"value\",\"max\":60,\"min\":0,\"unit\":\"min\"}},{\"abilityId\":106,\"code\":\"switch_led\",\"name\":\"Confirm\",\"typeSpec\":{\"type\":\"bool\"}},{\"abilityId\":107,\"code\":\"colour_data\",\"name\":\"彩光\",\"typeSpec\":{\"type\":\"string\",\"maxlen\":255}},{\"abilityId\":108,\"code\":\"work_mode\",\"name\":\"色盘工作模式\",\"typeSpec\":{\"type\":\"enum\",\"range\":[\"white\",\"colour\",\"scene\",\"music\"]}},{\"abilityId\":109,\"code\":\"day_1\",\"name\":\"clean metal filter\",\"typeSpec\":{\"type\":\"value\",\"max\":40,\"min\":0,\"unit\":\"day\"}}]}]}"
  },
  "success": true
}
```
