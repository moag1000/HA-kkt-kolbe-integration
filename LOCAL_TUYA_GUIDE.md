# KKT Kolbe Geräte in Local Tuya einrichten

## 🏠 Alternative: Local Tuya Integration

Falls Sie lieber die etablierte **Local Tuya Integration** verwenden möchten statt unserer experimentellen KI-Integration, finden Sie hier die komplette Anleitung für beide KKT Kolbe Modelle.

## ⚖️ Local Tuya vs. KKT Kolbe Integration (v0.2.0)

| Aspekt | Local Tuya | KKT Kolbe Integration v0.2.0 |
|--------|------------|------------------------------|
| **Stabilität** | ✅ Erprobt, tausende Nutzer | ❌ KI-generiert, ungetestet |
| **Sicherheit** | ✅ Community-validiert | ⚠️ Potenzielle KI-Fehler |
| **Funktionsumfang** | ⚠️ Manuell konfigurieren | ✅ Alle Funktionen vorkonfiguriert |
| **Setup-Aufwand** | ⚠️ DP-Mapping erforderlich | ✅ **NEU**: mDNS Auto-Discovery |
| **Device Discovery** | ✅ Automatische Erkennung | ✨ **Automatische Erkennung** |
| **Konfiguration** | ⚠️ Alle Werte manuell | ✅ Nur Local Key bei Discovery |
| **Updates** | ✅ Regelmäßig | ❓ Experimentell |

### 🆕 Was ist neu in v0.2.0?

**KKT Kolbe Integration** hat mit **mDNS Discovery** deutlich aufgeholt:
- **🔍 Automatic Discovery**: Findet Geräte automatisch im Netzwerk
- **⚡ Simplified Setup**: Nur noch Local Key eingeben
- **🎯 Smart Detection**: Erkennt Modelltypen automatisch

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
- **Model:** KKT Kolbe HERMES & STYLE
- **Model ID:** e1k6i0zo
- **Product ID:** ypaixllljc2dcpae
- **Category:** yyj (Dunstabzugshaube)
- **Protocol:** 3.3
- **Manufacturer:** KKT Kolbe

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

#### Schritt 1: Integration hinzufügen
1. **Home Assistant** → **Settings** → **Devices & Services**
2. **Add Integration** (unten rechts) → Suche nach **"LocalTuya"**
3. Falls nicht gefunden: Integration zuerst über HACS installieren

#### Schritt 2: Device hinzufügen
1. **Add a new device** klicken
2. **Manually add device** wählen (nicht Cloud API)
3. **Device Configuration:**
   - **Device ID:** `bf735dfe2ad64fba7c[XXXX]` (Ihre echte Device ID)
   - **Host:** `192.168.1.XXX` (Ihre lokale IP)
   - **Device Key:** `[Ihr Local Key]` (geheim halten!)
   - **Protocol Version:** `3.3`
   - **Device Name:** `KKT HERMES & STYLE`
   - **Model:** `HERMES & STYLE`
4. **Submit** klicken

#### Schritt 3: Entities konfigurieren

**Wichtig:** Schließen Sie die Smart Life App während der Konfiguration!

#### Entity 1: Main Power Switch
1. **Add Entity** klicken
2. **Platform:** `switch`
3. **Entity DP:** `1`
4. **Friendly name:** `Hood Power`
5. **Current/On value:** `True`
6. **Submit**

#### Entity 2: Light Control
1. **Add Entity** klicken
2. **Platform:** `light`
3. **Entity DP:** `4`
4. **Friendly name:** `Hood Light`
5. **Current/On value:** `True`
6. **Submit**

#### Entity 3: Fan Control
1. **Add Entity** klicken
2. **Platform:** `fan`
3. **Entity DP:** `10`
4. **Friendly name:** `Hood Fan`
5. **Speed List DP:** `10` (gleiche DP)
6. **Speed List Values:** `off,low,middle,high,strong`
7. **Submit**

#### Entity 4: Timer Control
1. **Add Entity** klicken
2. **Platform:** `number`
3. **Entity DP:** `13`
4. **Friendly name:** `Hood Timer`
5. **Min Value:** `0`
6. **Max Value:** `60`
7. **Step Size:** `1`
8. **Submit**

#### Entity 5: Filter Alert
1. **Add Entity** klicken
2. **Platform:** `binary_sensor`
3. **Entity DP:** `6`
4. **Friendly name:** `Filter Alert`
5. **Current/On value:** `True`
6. **Submit**

#### Entity 6: RGB Light Mode
1. **Add Entity** klicken
2. **Platform:** `select`
3. **Entity DP:** `101`
4. **Friendly name:** `RGB Mode`
5. **Select Options:** `Off,White,Warm White,Cool White,Red,Green,Blue,Yellow,Purple,Rainbow`
6. **Select Options Values:** `0,1,2,3,4,5,6,7,8,9`
7. **Submit**

#### Schritt 4: Konfiguration abschließen
1. **Submit** (Device-Konfiguration)
2. Das Gerät sollte nun unter **Devices & Services** → **LocalTuya** erscheinen
3. Alle 6 Entities sollten funktionieren

## 🔥 KKT IND7705HC (Induktionskochfeld)

### Device Information
- **Model:** KKT IND7705HC
- **Model ID:** e1kc5q64
- **Product ID:** p8volecsgzdyun29
- **Category:** dcl (Induktionskochfeld)
- **Protocol:** 3.3
- **Manufacturer:** KKT Kolbe

### ⚠️ SICHERHEITSWARNUNG
**Bei Kochfeldern können Konfigurationsfehler zu gefährlichen Situationen führen!**
- Testen Sie jede Funktion einzeln
- Überwachen Sie das Gerät während der Tests
- Haben Sie einen Notausschalter bereit

### 🤚 WICHTIG: Manuelle Bestätigung erforderlich

**Sicherheitsfeature des Kochfelds:**
- 📱 **Wie in der Tuya App**: Remote-Befehle erfordern **physische Bestätigung**
- 👤 **Person vor Ort**: Jemand muss am Gerät stehen und **Bestätigungstaste drücken**
- 🔒 **API-Limitation**: Dies ist **KEINE** Einschränkung der Integration, sondern ein **Tuya-Sicherheitsfeature**
- ⏰ **Timeout**: Ohne Bestätigung werden Remote-Befehle nach ca. 30 Sekunden abgebrochen

**Praktisches Beispiel:**
1. Sie senden "Zone 1 auf Stufe 5" über Home Assistant
2. Das Kochfeld **piept** und zeigt Warnung im Display
3. Sie müssen **physisch die Bestätigungstaste** am Gerät drücken
4. Erst dann wird der Befehl ausgeführt

**➡️ Das ist KEIN Bug, sondern gewollte Sicherheit!**

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

#### Schritt 1: Device hinzufügen
1. **Home Assistant** → **Settings** → **Devices & Services** → **LocalTuya**
2. **Add a new device** → **Manually add device**
3. **Device Configuration:**
   - **Device ID:** `bf5592b47738c5b46e[XXXX]` (Ihre echte Device ID)
   - **Host:** `192.168.1.XXX` (Ihre lokale IP)
   - **Device Key:** `[Ihr Local Key]` (geheim halten!)
   - **Protocol Version:** `3.3`
   - **Device Name:** `KKT IND7705HC`
   - **Model:** `IND7705HC`

#### Schritt 2: Basis Entities (SICHER):

**⚠️ WARNUNG:** Testen Sie jede Entity einzeln und überwachen Sie das Gerät!

#### Entity 1: Main Power (START HIER)
1. **Add Entity** klicken
2. **Platform:** `switch`
3. **Entity DP:** `101`
4. **Friendly name:** `Cooktop Power`
5. **Current/On value:** `True`
6. **Submit**
7. **⚠️ TESTEN:** Ein-/Ausschalten und physisch prüfen!

#### Entity 2: Child Lock (SICHERHEIT)
1. **Add Entity** klicken
2. **Platform:** `switch`
3. **Entity DP:** `103`
4. **Friendly name:** `Child Lock`
5. **Current/On value:** `True`
6. **Submit**
7. **🔒 TESTEN:** Kindersicherung aktivieren/deaktivieren

#### Entity 3: Pause Function
1. **Add Entity** klicken
2. **Platform:** `switch`
3. **Entity DP:** `102`
4. **Friendly name:** `Cooktop Pause`
5. **Current/On value:** `True`
6. **Submit**
7. **⏸️ TESTEN:** Pause-Funktion testen

#### Entity 4: General Timer
1. **Add Entity** klicken
2. **Platform:** `number`
3. **Entity DP:** `134`
4. **Friendly name:** `General Timer`
5. **Min Value:** `0`
6. **Max Value:** `99`
7. **Step Size:** `1`
8. **Submit**
9. **⏰ TESTEN:** Timer auf 5 Min setzen und prüfen

#### Entity 5: Senior Mode
1. **Add Entity** klicken
2. **Platform:** `switch`
3. **Entity DP:** `145`
4. **Friendly name:** `Senior Mode`
5. **Current/On value:** `True`
6. **Submit**
7. **👤 TESTEN:** Senioren-Modus aktivieren

### 🚫 Limitierungen in LocalTuya

**Schwierig umsetzbar:**
- Individuelle Zone-Steuerung (DP 162)
- Pro-Zone Boost/Warm Modi (DP 163/164)
- Zone-spezifische Timer (DP 167)
- Quick Level Presets (DP 148-152)

**Grund:** Diese DPs verwenden komplexe Bitmasken, die in LocalTuya manuell dekodiert werden müssten.

## 🔧 Debugging und Problemlösung

### Schritt 1: Logging aktivieren

```yaml
# configuration.yaml
logger:
  default: warning
  logs:
    custom_components.localtuya: debug
    custom_components.localtuya.pytuya: debug
```

### Schritt 2: DP-Status prüfen

1. **Developer Tools** → **Services**
2. Service: `localtuya.reload`
3. **Call Service** (refresht alle LocalTuya Geräte)

### Schritt 3: Manuelle DP-Tests

#### Für HERMES & STYLE:
```yaml
# Test DP 1 (Power)
service: localtuya.set_dp
data:
  device_id: "bf735dfe2ad64fba7c[XXXX]"
  dp: 1
  value: true
```

#### Für IND7705HC:
```yaml
# Test DP 101 (Power) - VORSICHTIG!
service: localtuya.set_dp
data:
  device_id: "bf5592b47738c5b46e[XXXX]"
  dp: 101
  value: true
```

### Häufige Probleme:

**Problem:** "Device not responding"
- ➡️ Smart Life App schließen
- ➡️ IP-Adresse prüfen (Router-Interface)
- ➡️ Local Key erneut extrahieren

**Problem:** "Protocol version mismatch"
- ➡️ Versuchen Sie 3.1, 3.2, 3.3, 3.4
- ➡️ Bei KKT meist 3.3 korrekt

**Problem:** "Entity not updating"
- ➡️ DP-Nummer doppelt prüfen
- ➡️ Gerät physisch betätigen und Logs prüfen

## 🆚 Fazit

### 🔴 Local Tuya wählen wenn:
- ✅ **Stabilität** über Features priorisieren
- ✅ **Production Environment** (kritische Systeme)
- ✅ **Nur Basis-Funktionen** benötigt
- ✅ **Erfahrung** mit DP-Mapping vorhanden
- ✅ **Community-Support** bevorzugt

### 🔵 KKT Kolbe Integration v0.2.0 wählen wenn:
- ✨ **Automatic Discovery** gewünscht (NEUES KILLER-FEATURE!)
- ✅ **Alle Geräte-Features** nutzen möchten
- ✅ **Einfaches Setup** bevorzugen (nur Local Key)
- ✅ **Experimentellen Code** testen bereit
- ✅ **Zur Entwicklung** beitragen möchten
- ⚡ **Moderne UX** mit automatischer Erkennung

### 🎆 Empfehlung für v0.2.0:
**Für Test-Umgebungen**: KKT Integration (wegen mDNS Discovery)
**Für Production**: Local Tuya (wegen Stabilität)

---

**💡 Tipp:** Sie können beide Integrationen parallel testen, um zu vergleichen welche besser für Ihre Bedürfnisse geeignet ist. Verwenden Sie dafür unterschiedliche Device-Namen.