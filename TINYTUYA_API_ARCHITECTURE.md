# TinyTuya API Integration - Architektur Plan

## 🎯 Überblick

Diese Neuentwicklung erweitert die KKT Kolbe Integration um direkte TinyTuya Cloud API Unterstützung für automatische Geräteerkennung und dynamische Konfiguration.

## 🏗️ Architektur Komponenten

### 1. API Client Layer (`tuya_cloud_client.py`)
```python
class TuyaCloudClient:
    """TinyTuya Cloud API Client für Geräteabfragen"""

    def __init__(self, client_id: str, client_secret: str, endpoint: str)
    async def authenticate() -> str  # Access Token
    async def get_device_list() -> List[Dict]  # Alle Geräte
    async def get_device_properties(device_id: str) -> Dict  # "Query Things Data Model"
    async def get_device_status(device_id: str) -> Dict  # Aktueller Status
    async def test_connection() -> bool  # Verbindungstest
```

### 2. Dynamic Device Factory (`dynamic_device_factory.py`)
```python
class DynamicDeviceFactory:
    """Erstellt Gerätekonfigurationen basierend auf API-Daten"""

    async def analyze_device_properties(properties: Dict) -> DeviceConfig
    async def create_entity_configurations(device_config: DeviceConfig) -> List[EntityConfig]
    async def detect_device_type(properties: Dict) -> str  # hood, cooktop, unknown
    async def map_data_points_to_entities(dps: Dict) -> Dict
```

### 3. Enhanced Config Flow (`config_flow_v2.py`)
```python
class KKTKolbeConfigFlowV2(ConfigFlow):
    """Erweiterte Konfiguration mit API-Unterstützung"""

    # Bestehende manuelle Konfiguration
    async def async_step_manual_config()

    # Neue API-basierte Konfiguration
    async def async_step_api_config()  # API Credentials eingeben
    async def async_step_api_discovery()  # Geräte über API laden
    async def async_step_device_selection()  # Gerät aus API-Liste wählen
    async def async_step_entity_customization()  # Entities anpassen
```

### 4. Hybrid Coordinator (`hybrid_coordinator.py`)
```python
class KKTKolbeHybridCoordinator:
    """Unterstützt sowohl lokale als auch API-basierte Datenabrufe"""

    def __init__(self, local_device: TuyaDevice, api_client: TuyaCloudClient)

    # Lokale Kommunikation (bisherig)
    async def async_update_local() -> Dict

    # API-basierte Kommunikation (neu)
    async def async_update_via_api() -> Dict

    # Hybrid-Modus
    async def async_update_hybrid() -> Dict  # Local first, API fallback
```

## 🔧 Implementierungsdetails

### API Credentials Management
```python
# In config_flow.py
CONF_API_CLIENT_ID = "api_client_id"
CONF_API_CLIENT_SECRET = "api_client_secret"
CONF_API_ENDPOINT = "api_endpoint"
CONF_API_ENABLED = "api_enabled"

# Standardwerte
DEFAULT_API_ENDPOINT = "https://openapi.tuyaeu.com"  # EU endpoint
```

### Datenfluss
```
1. Config Flow:
   User Input → API Credentials → Test Connection → Device Discovery

2. Device Setup:
   API Properties → Dynamic Analysis → Entity Creation → Coordinator Setup

3. Runtime:
   Local Communication (primary) ↔ API Communication (fallback/verification)
```

### Fehlerbehandlung
```python
class TuyaAPIError(Exception): pass
class TuyaAuthenticationError(TuyaAPIError): pass
class TuyaRateLimitError(TuyaAPIError): pass
class TuyaDeviceNotFoundError(TuyaAPIError): pass
```

## 📁 Datei-Struktur Erweiterung

```
custom_components/kkt_kolbe/
├── api/                           # 🆕 API Integration
│   ├── __init__.py
│   ├── tuya_cloud_client.py      # TinyTuya Cloud API Client
│   ├── dynamic_device_factory.py # Dynamische Geräteerstellung
│   └── api_exceptions.py         # API-spezifische Exceptions
├── config_flow_v2.py             # 🆕 Erweiterte Konfiguration
├── hybrid_coordinator.py         # 🆕 Hybrid Local/API Coordinator
├── config_flow.py                # Bestehend (Legacy)
├── coordinator.py                # Bestehend (Local only)
└── ...
```

## 🔄 Migration Strategy

### Phase 1: Parallel Implementation
- Bestehende Konfiguration bleibt unverändert
- Neue API-Konfiguration als separate Option
- Beide Modi koexistieren

### Phase 2: Hybrid Mode
- Existing devices können API-Funktionen hinzufügen
- Graceful fallback zwischen Local/API

### Phase 3: Full Integration
- API wird Standard für neue Geräte
- Legacy-Modus weiterhin verfügbar

## 🚀 Vorteile

### Für Entwickler:
- **Automatische Device Discovery**: Keine manuelle DP-Konfiguration
- **Real-time Verification**: API-Daten als Referenz
- **Dynamic Updates**: Neue DPs automatisch erkannt

### Für Benutzer:
- **Einfachere Einrichtung**: Ein-Klick Device Discovery
- **Mehr Geräte**: Automatische Unterstützung neuer Modelle
- **Bessere Zuverlässigkeit**: API als Backup für lokale Verbindung

## 🧪 Beta Testing Strategy

### Branch Management:
- `feature/tinytuya-api-integration` - Entwicklung
- `beta/api-integration` - Community Testing
- `main` - Stable release

### Testing Approach:
1. **Developer Testing**: Core functionality
2. **Community Beta**: Real device testing
3. **Gradual Rollout**: Optional feature first

## 🔒 Sicherheitsüberlegungen

### API Credentials:
- Sichere Speicherung in HA config
- Verschlüsselung von Client Secret
- Rate limiting compliance

### Datenschutz:
- Nur notwendige API-Aufrufe
- Lokale Kommunikation bevorzugt
- Transparenz über API-Nutzung

## 📋 Implementation Roadmap

### Sprint 1: Foundation
- [ ] TuyaCloudClient basic implementation
- [ ] API authentication flow
- [ ] Basic error handling

### Sprint 2: Device Discovery
- [ ] Device list retrieval
- [ ] Properties analysis
- [ ] Dynamic device factory

### Sprint 3: Integration
- [ ] Enhanced config flow
- [ ] Hybrid coordinator
- [ ] Entity creation

### Sprint 4: Polish
- [ ] Error handling improvement
- [ ] Documentation
- [ ] Beta testing preparation

Soll ich mit der Implementierung des TuyaCloudClient beginnen?