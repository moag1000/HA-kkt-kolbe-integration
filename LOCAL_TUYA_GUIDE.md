# KKT Kolbe Geräte in Local Tuya einrichten

## 🏠 Alternative: Local Tuya Integration

Falls Sie lieber die etablierte **Local Tuya Integration** verwenden möchten statt unserer experimentellen KI-Integration, finden Sie hier die komplette Anleitung für beide KKT Kolbe Modelle.

## ⚖️ Local Tuya vs. KKT Kolbe Integration

| Aspekt | Local Tuya | KKT Kolbe Integration |
|--------|------------|----------------------|
| **Stabilität** | ✅ Erprobt, tausende Nutzer | ❌ KI-generiert, ungetestet |
| **Sicherheit** | ✅ Community-validiert | ⚠️ Potenzielle KI-Fehler |
| **Funktionsumfang** | ⚠️ Manuell konfigurieren | ✅ Alle Funktionen vorkonfiguriert |
| **Setup-Aufwand** | ⚠️ DP-Mapping erforderlich | ✅ Plug-and-Play |
| **Updates** | ✅ Regelmäßig | ❓ Experimentell |

## 📋 Voraussetzungen

Gleiche Tuya-Credentials wie für unsere Integration:
- Device ID
- Local Key
- IP-Adresse
- [Tuya Credentials Anleitung](README.md#getting-tuya-credentials)

## 🏪 Local Tuya Installation

### Via HACS (Empfohlen)
1. **HACS** → **Integrations** → **⋮ Menü** → **Custom repositories**
2. Repository: `https://github.com/rospogrigio/localtuya`
3. Category: `Integration`
4. **LocalTuya** installieren und Home Assistant neu starten

### Manual Installation
1. Download von [GitHub](https://github.com/rospogrigio/localtuya)
2. `custom_components/localtuya` nach `config/custom_components/` kopieren

## 🍳 KKT Kolbe HERMES & STYLE (Dunstabzugshaube)

### Device Information
- **Model ID:** e1k6i0zo
- **Category:** yyj (Dunstabzugshaube)
- **Protocol:** 3.3

### Data Points (DPs) Mapping

| DP | Funktion | Typ | Werte | LocalTuya Entity |
|----|----------|-----|-------|------------------|
| 1 | Main Power | bool | true/false | Switch |
| 4 | Light | bool | true/false | Light |
| 6 | Filter Alert | bool | true/false | Binary Sensor |
| 10 | Fan Speed | enum | off, low, middle, high, strong | Fan |
| 13 | Timer | value | 0-60 (min) | Number |
| 101 | RGB Mode | value | 0-9 | Select |

### LocalTuya Konfiguration

1. **Integration hinzufügen:** Settings → Devices & Services → Add Integration → LocalTuya
2. **Device hinzufügen:**
   - Device ID: `[Ihre Device ID]`
   - Host: `[Ihre IP]`
   - Device Key: `[Ihr Local Key]`
   - Protocol Version: `3.3`
   - Device Name: `KKT Kolbe Hood`

3. **Entities konfigurieren:**

#### Main Power Switch
- **Platform:** Switch
- **DP:** 1
- **Name:** Hood Power

#### Light Control
- **Platform:** Light
- **DP:** 4
- **Name:** Hood Light

#### Fan Control
- **Platform:** Fan
- **DP:** 10
- **Name:** Hood Fan

#### Timer
- **Platform:** Number
- **DP:** 13
- **Min Value:** 0
- **Max Value:** 60
- **Name:** Hood Timer

#### Filter Alert
- **Platform:** Binary Sensor
- **DP:** 6
- **Name:** Filter Alert

#### RGB Mode
- **Platform:** Select
- **DP:** 101
- **Options:** `0,1,2,3,4,5,6,7,8,9`
- **Name:** RGB Mode

## 🔥 KKT IND7705HC (Induktionskochfeld)

### Device Information
- **Model ID:** e1kc5q64
- **Category:** dcl (Induktionskochfeld)
- **Protocol:** 3.3

### ⚠️ SICHERHEITSWARNUNG
**Bei Kochfeldern können Konfigurationsfehler zu gefährlichen Situationen führen!**
- Testen Sie jede Funktion einzeln
- Überwachen Sie das Gerät während der Tests
- Haben Sie einen Notausschalter bereit

### Basis Data Points

| DP | Funktion | Typ | Werte | LocalTuya Entity |
|----|----------|-----|-------|------------------|
| 101 | Main Power | bool | true/false | Switch |
| 102 | Pause | bool | true/false | Switch |
| 103 | Child Lock | bool | true/false | Switch |
| 134 | General Timer | value | 0-99 (min) | Number |
| 145 | Senior Mode | bool | true/false | Switch |

### Erweiterte Zone-Steuerung (Komplex!)

**⚠️ Diese DPs verwenden Bitmasken und sind schwierig in LocalTuya umzusetzen:**

| DP | Funktion | Typ | Beschreibung |
|----|----------|-----|--------------|
| 162 | Zone Power Levels | raw | Bitfeld: 8 Bits pro Zone (1-5) |
| 163 | Zone Boost | raw | Bitfeld: 1 Bit pro Zone |
| 164 | Zone Warm | raw | Bitfeld: 1 Bit pro Zone |
| 167 | Zone Timers | raw | Bitfeld: 8 Bits pro Zone |

### LocalTuya Basis-Konfiguration

1. **Device hinzufügen:**
   - Device ID: `[Ihre Device ID]`
   - Host: `[Ihre IP]`
   - Device Key: `[Ihr Local Key]`
   - Protocol Version: `3.3`
   - Device Name: `KKT Cooktop`

2. **Basis Entities:**

#### Main Power
- **Platform:** Switch
- **DP:** 101
- **Name:** Cooktop Power

#### Child Lock
- **Platform:** Switch
- **DP:** 103
- **Name:** Child Lock

#### Pause Function
- **Platform:** Switch
- **DP:** 102
- **Name:** Cooktop Pause

#### General Timer
- **Platform:** Number
- **DP:** 134
- **Min Value:** 0
- **Max Value:** 99
- **Name:** General Timer

#### Senior Mode
- **Platform:** Switch
- **DP:** 145
- **Name:** Senior Mode

### 🚫 Limitierungen in LocalTuya

**Schwierig umsetzbar:**
- Individuelle Zone-Steuerung (DP 162)
- Pro-Zone Boost/Warm Modi (DP 163/164)
- Zone-spezifische Timer (DP 167)
- Quick Level Presets (DP 148-152)

**Grund:** Diese DPs verwenden komplexe Bitmasken, die in LocalTuya manuell dekodiert werden müssten.

## 🔧 Debugging

Falls Probleme auftreten:

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.localtuya: debug
    custom_components.localtuya.pytuya: debug
```

## 🆚 Fazit

### Local Tuya wählen wenn:
- ✅ Sie Stabilität über Features priorisieren
- ✅ Sie nur Basis-Funktionen benötigen
- ✅ Sie Erfahrung mit DP-Mapping haben

### KKT Kolbe Integration wählen wenn:
- ✅ Sie alle Geräte-Features nutzen möchten
- ✅ Sie bereit sind, experimentellen Code zu testen
- ✅ Sie zur Entwicklung beitragen möchten

---

**💡 Tipp:** Sie können beide Integrationen parallel testen, um zu vergleichen welche besser für Ihre Bedürfnisse geeignet ist. Verwenden Sie dafür unterschiedliche Device-Namen.