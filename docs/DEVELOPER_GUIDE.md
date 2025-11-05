# KKT Kolbe Integration - Developer Guide

<div align="center">
  <img src="./icon.png" alt="KKT Kolbe Logo" width="128" height="128">
</div>

## 🔧 Adding New KKT Kolbe Devices - Complete Developer Guide

This guide explains how to add support for new KKT Kolbe devices to the Home Assistant integration. The process involves extracting device capabilities from the Tuya IoT platform and implementing the corresponding entities.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Device Data Extraction](#device-data-extraction)
3. [Understanding the Codebase](#understanding-the-codebase)
4. [Adding a New Device](#adding-a-new-device)
5. [Entity Implementation](#entity-implementation)
6. [Testing & Validation](#testing--validation)
7. [Contributing Guidelines](#contributing-guidelines)

---

## Prerequisites

### 🔑 Required Accounts & Tools

1. **Tuya IoT Developer Account** (⚠️ SEPARATE from Smart Life App!)
   - Register at: https://iot.tuya.com/
   - Your Smart Life app credentials **will NOT work**
   - Create a new Cloud Project

2. **Device Information**
   - Device ID from Smart Life app
   - Local Key (extracted via tuya-cli or tinytuya)
   - Physical access to the device for testing

3. **Development Environment**
   - Home Assistant development setup
   - Git for version control
   - Python 3.11+ with required dependencies

### 🔗 Link Your Device to IoT Platform

1. **In Tuya IoT Console**: Go to **Devices** → **Link App Account**
2. **Link your Smart Life App** to the Cloud Project
3. **Verify**: All your devices should appear in the IoT console

---

## Device Data Extraction

### 🎯 Getting Device Capabilities (Things Data Model)

The most crucial step is extracting the complete device capabilities from Tuya IoT platform:

#### Step 1: Access API Explorer
1. **Tuya IoT Console** → **Cloud** → **API Explorer**
2. **Select**: Device Management → **Query Things Data Model**

#### Step 2: Query Your Device
```bash
# Input your Device ID (from Smart Life app)
Device ID: bf735dfe2ad64fba7cpyhn

# Execute the API call
```

#### Step 3: Extract Complete JSON
You'll receive a comprehensive JSON response like this:

```json
{
  "result": {
    "category": "cz",
    "functions": [
      {
        "code": "switch",
        "dp_id": 1,
        "type": "Boolean",
        "values": "{}"
      },
      {
        "code": "fan_speed_enum",
        "dp_id": 2,
        "type": "Enum",
        "values": "{\"range\":[\"sleep\",\"low\",\"middle\",\"high\",\"strong\"]}"
      }
      // ... more functions
    ],
    "status": [
      {
        "code": "switch",
        "dp_id": 1,
        "type": "Boolean",
        "values": "{}"
      }
      // ... more status points
    ]
  },
  "success": true
}
```

**💾 Save this complete JSON - it contains ALL device capabilities!**

---

## Understanding the Codebase

### 🏗️ Architecture Overview

```
custom_components/kkt_kolbe/
├── device_types.py      # 🎯 Device definitions & entity configs
├── const.py            # Constants and model mappings
├── __init__.py         # Integration setup & platform loading
├── config_flow.py      # UI configuration flow
├── tuya_device.py      # Tuya communication layer
├── discovery.py        # Device discovery (mDNS/UDP)
└── platforms/
    ├── fan.py          # Fan entities
    ├── light.py        # Light entities
    ├── switch.py       # Switch entities
    ├── sensor.py       # Sensor entities
    ├── number.py       # Number entities
    ├── select.py       # Select entities
    └── binary_sensor.py # Binary sensor entities
```

### 🎯 Key Files for Device Addition

#### 1. `device_types.py` - Central Device Database
This is where ALL device definitions live:

```python
DEVICE_CONFIGS = {
    "HERMES & STYLE": {
        "category": "hood",
        "model_id": "e1k6i0zo",
        "name": "HERMES & STYLE Range Hood",
        "platforms": ["fan", "light", "switch", "number", "select", "sensor"],
        "entities": {
            # Entity definitions for each platform
        }
    }
}
```

#### 2. `const.py` - Model Mappings
Device ID patterns and model mappings:

```python
MODELS = {
    "e1k6i0zo": {
        "name": "HERMES & STYLE",
        "category": "hood"
    }
}

DEVICE_ID_PATTERNS = {
    'bf735dfe2ad64fba7c': "HERMES & STYLE"
}
```

#### 3. Platform Files (`fan.py`, `switch.py`, etc.)
Each platform implements specific entity types with dynamic creation based on device configurations.

---

## Adding a New Device

### 🎯 Step-by-Step Implementation

Let's add a hypothetical new device "KKT SuperCook Pro" (IND8000HC):

#### Step 1: Analyze the Things Data Model JSON

From your API call, you received functions and status. Categorize them:

```python
# Example extracted data points:
DP 1:  switch (Boolean) → Main Power Switch
DP 2:  fan_speed_enum (Enum) → Fan Speed Control
DP 3:  light (Boolean) → Main Light
DP 4:  light_mode (Enum) → RGB Light Modes
DP 5:  timer (Integer) → Timer Control
DP 6:  temp_current (Integer) → Temperature Sensor
# ... continue for all DPs
```

#### Step 2: Add to `const.py`

```python
# Add model mapping
MODELS = {
    "e1k6i0zo": {"name": "HERMES & STYLE", "category": "hood"},
    "ind8000hc": {"name": "SuperCook Pro", "category": "cooktop"},  # ← NEW
}

# Add device ID pattern (get from real device)
DEVICE_ID_PATTERNS = {
    'bf735dfe2ad64fba7c': "HERMES & STYLE",
    'bf559abc1234567890': "SuperCook Pro",  # ← NEW (example pattern)
}
```

#### Step 3: Create Device Configuration in `device_types.py`

```python
DEVICE_CONFIGS = {
    # ... existing devices

    "SuperCook Pro": {  # ← NEW DEVICE
        "category": "cooktop",
        "model_id": "ind8000hc",
        "name": "KKT SuperCook Pro Induction Cooktop",
        "platforms": ["switch", "number", "select", "sensor", "binary_sensor"],
        "entities": {
            "switch": [
                {
                    "dp": 1,
                    "name": "Main Power",
                    "device_class": "switch"
                },
                {
                    "dp": 10,
                    "name": "Child Lock",
                    "device_class": "lock"
                }
            ],
            "number": [
                {
                    "dp": 5,
                    "name": "Timer",
                    "min": 0,
                    "max": 99,
                    "step": 1,
                    "unit": "min"
                },
                {
                    "dp": 15,
                    "name": "Zone 1 Power Level",
                    "min": 0,
                    "max": 20,
                    "step": 1,
                    "zone": 1
                }
            ],
            "select": [
                {
                    "dp": 8,
                    "name": "Quick Level",
                    "options": ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5"]
                }
            ],
            "sensor": [
                {
                    "dp": 6,
                    "name": "Current Temperature",
                    "device_class": "temperature",
                    "unit": "°C"
                },
                {
                    "dp": 25,
                    "name": "Zone 1 Error",
                    "device_class": "enum",
                    "zone": 1
                }
            ],
            "binary_sensor": [
                {
                    "dp": 20,
                    "name": "Zone 1 Boost",
                    "device_class": "power",
                    "zone": 1
                }
            ]
        }
    }
}
```

#### Step 4: Implement Device-Specific Logic in `tuya_device.py`

If your device needs special handling (like bitfield operations for zones):

```python
class KKTKolbeTuyaDevice:
    # ... existing methods

    def get_zone_power_level(self, zone: int) -> int:
        """Get power level for specific zone (SuperCook Pro specific)."""
        if self.product_name == "SuperCook Pro":
            # Device-specific implementation
            power_data = self.get_dp_value(15, 0)  # DP 15 contains zone powers
            # Extract zone power from bitfield or array
            return (power_data >> ((zone - 1) * 4)) & 0xF
        return 0

    def set_zone_power_level(self, zone: int, level: int):
        """Set power level for specific zone."""
        if self.product_name == "SuperCook Pro":
            # Device-specific implementation
            current_data = self.get_dp_value(15, 0)
            # Update specific zone in bitfield
            mask = 0xF << ((zone - 1) * 4)
            new_data = (current_data & ~mask) | ((level & 0xF) << ((zone - 1) * 4))
            self.set_dp_value(15, new_data)
```

#### Step 5: Update Entity Platforms (if needed)

Most entities will work automatically with the configuration, but complex ones might need updates:

```python
# In number.py - add support for SuperCook Pro specifics
class KKTKolbeNumber(NumberEntity):

    @property
    def native_value(self) -> float:
        """Return the current value."""
        if self._dp == 15 and hasattr(self._config, 'zone'):  # Zone power levels
            return float(self._device.get_zone_power_level(self._config['zone']))
        elif self._dp == 5:  # Timer
            return float(self._device.get_dp_value(5, 0))
        # ... handle other DPs

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        int_value = int(value)

        if self._dp == 15 and hasattr(self._config, 'zone'):  # Zone power levels
            self._device.set_zone_power_level(self._config['zone'], int_value)
        elif self._dp == 5:  # Timer
            await self._device.async_set_dp(5, int_value)
        # ... handle other DPs
```

---

## Entity Implementation

### 🎛️ Entity Types & Their Use Cases

#### **Switch Entities** (`switch.py`)
For on/off controls:
- Main power
- Child lock
- Special modes (boost, keep warm, etc.)

```python
{
    "dp": 1,
    "name": "Main Power",
    "device_class": "switch"
}
```

#### **Number Entities** (`number.py`)
For numeric controls:
- Timers
- Temperature settings
- Power levels
- Zone-specific controls

```python
{
    "dp": 5,
    "name": "Timer",
    "min": 0,
    "max": 99,
    "step": 1,
    "unit": "min"
}
```

#### **Select Entities** (`select.py`)
For dropdown selections:
- RGB modes
- Quick level presets
- Operating modes

```python
{
    "dp": 8,
    "name": "Quick Level",
    "options": ["Level 1", "Level 2", "Level 3", "Level 4", "Level 5"]
}
```

#### **Sensor Entities** (`sensor.py`)
For read-only values:
- Temperature readings
- Error codes
- Status information

```python
{
    "dp": 6,
    "name": "Current Temperature",
    "device_class": "temperature",
    "unit": "°C"
}
```

#### **Binary Sensor Entities** (`binary_sensor.py`)
For on/off status:
- Zone active/inactive
- Error states
- Feature status

```python
{
    "dp": 20,
    "name": "Zone 1 Active",
    "device_class": "power",
    "zone": 1
}
```

#### **Fan Entities** (`fan.py`)
For fan controls (range hoods):
- Speed control
- On/off state

```python
{
    "dp": 2,
    "name": "Exhaust Fan",
    "speeds": ["sleep", "low", "middle", "high", "strong"]
}
```

#### **Light Entities** (`light.py`)
For lighting controls:
- Main lighting
- RGB controls
- Brightness

```python
{
    "dp": 3,
    "name": "Hood Light",
    "rgb_dp": 4  # Optional RGB control DP
}
```

### 🔧 Advanced Features

#### Zone-Specific Entities
For multi-zone devices (cooktops):

```python
{
    "dp": 162,
    "name": "Zone {zone} Power Level",  # {zone} will be replaced
    "min": 0,
    "max": 25,
    "step": 1,
    "zone": 1  # Will create entities for zones 1-5
}
```

#### Bitfield Operations
For complex data points:

```python
# In tuya_device.py
def get_zone_boost(self, zone: int) -> bool:
    """Get boost status for specific zone from bitfield."""
    boost_data = self.get_dp_value(163, 0)  # DP 163 contains boost bits
    return bool(boost_data & (1 << (zone - 1)))

def set_zone_boost(self, zone: int, enabled: bool):
    """Set boost status for specific zone."""
    current_data = self.get_dp_value(163, 0)
    if enabled:
        new_data = current_data | (1 << (zone - 1))
    else:
        new_data = current_data & ~(1 << (zone - 1))
    self.set_dp_value(163, new_data)
```

---

## Testing & Validation

### 🧪 Testing Checklist

#### 1. **Device Recognition**
- [ ] Device ID pattern matches correctly
- [ ] Auto-detection works in discovery
- [ ] Manual configuration accepts device
- [ ] Product name mapping works

#### 2. **Entity Creation**
- [ ] All configured entities are created
- [ ] Unique IDs are generated correctly
- [ ] Entity names are meaningful
- [ ] Icons are appropriate

#### 3. **Functionality Testing**
- [ ] Read operations work (sensors, binary sensors)
- [ ] Write operations work (switches, numbers, selects)
- [ ] Complex operations work (zones, bitfields)
- [ ] Error handling works

#### 4. **Home Assistant Integration**
- [ ] Entities appear in Home Assistant
- [ ] Device can be assigned to areas
- [ ] State changes are reflected
- [ ] Controls respond correctly

### 🔍 Debug Mode

Enable debug logging in Home Assistant:

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.kkt_kolbe: debug
```

### 🧪 Test Device Simulation

For initial testing without hardware:

```python
# In discovery.py - add test device
def add_test_device(device_id: str = "bf559abc1234567890"):
    """Add test device for SuperCook Pro."""
    global _discovery_instance

    if _discovery_instance:
        test_device = {
            "device_id": device_id,
            "host": "192.168.1.100",  # Fake IP
            "name": "Test KKT SuperCook Pro",
            "model": "ind8000hc",
            "device_type": "cooktop",
            "product_name": "SuperCook Pro",
            "discovered_via": "test_simulation"
        }
        _discovery_instance.discovered_devices[device_id] = test_device
```

---

## Contributing Guidelines

### 📝 Submission Process

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/add-supercook-pro
   ```

2. **Implement Device Support**
   - Follow the steps above
   - Test thoroughly with real hardware if possible
   - Add comprehensive documentation

3. **Update Documentation**
   - Add device to README.md supported devices list
   - Update CHANGELOG.md with new device
   - Include JSON data model in PR description

4. **Create Pull Request**
   - Include complete Things Data Model JSON
   - Describe testing performed
   - Note any limitations or special requirements

### 📋 Pull Request Requirements

#### Required Information:
- **Complete Tuya Things Data Model JSON**
- **Device ID patterns** (at least first 18 characters)
- **Testing results** (with/without real hardware)
- **Entity mapping rationale** (why DP X maps to entity type Y)

#### Code Quality:
- [ ] Follows existing code patterns
- [ ] No hardcoded device IDs in entity code
- [ ] Proper error handling
- [ ] Meaningful entity names and descriptions
- [ ] Appropriate icons for all entities

#### Documentation:
- [ ] Device added to supported devices list
- [ ] Configuration examples provided
- [ ] Any special setup requirements noted
- [ ] Testing instructions included

---

## 🛠️ Advanced Topics

### Custom Entity Types

If standard Home Assistant entity types don't fit your device:

```python
# Example: Custom cooktop entity with multiple zones
class KKTKolbeCooktopEntity(Entity):
    """Custom entity for complex cooktop controls."""

    @property
    def state(self):
        """Return state as JSON of all zones."""
        return {
            f"zone_{i}": {
                "power_level": self._device.get_zone_power_level(i),
                "timer": self._device.get_zone_timer(i),
                "active": self._device.is_zone_active(i)
            }
            for i in range(1, 6)  # 5 zones
        }
```

### Device Capability Auto-Detection

For dynamic device support:

```python
async def detect_device_capabilities(device_id: str, local_key: str, ip: str):
    """Auto-detect device capabilities from live device."""
    device = KKTKolbeTuyaDevice(device_id, ip, local_key)
    await device.async_connect()

    status = await device.async_get_status()
    if status and "dps" in status:
        # Analyze available DPs and create dynamic configuration
        detected_entities = []
        for dp, value in status["dps"].items():
            # Auto-create entity based on DP type and value
            entity_config = auto_detect_entity_type(dp, value)
            if entity_config:
                detected_entities.append(entity_config)

        return detected_entities
```

### Multi-Protocol Support

For devices supporting multiple protocols:

```python
class AdvancedKKTDevice(KKTKolbeTuyaDevice):
    """Advanced device with multiple communication methods."""

    def __init__(self, device_id: str, ip: str, local_key: str, protocol="tuya"):
        super().__init__(device_id, ip, local_key)
        self.protocol = protocol

    async def async_connect(self):
        """Connect using appropriate protocol."""
        if self.protocol == "tuya":
            await super().async_connect()
        elif self.protocol == "modbus":
            await self._connect_modbus()
        # ... other protocols
```

---

## 📚 References & Resources

### Official Documentation
- [Home Assistant Entity Development](https://developers.home-assistant.io/docs/core/entity/)
- [Tuya IoT Platform API](https://developer.tuya.com/en/docs/iot/)
- [TinyTuya Documentation](https://github.com/jasonacox/tinytuya)

### Community Resources
- [Local Tuya Integration](https://github.com/rospogrigio/localtuya)
- [Tuya Device Extraction Tools](https://github.com/codetheweb/tuyapi)
- [Home Assistant Community Forum](https://community.home-assistant.io/)

### Development Tools
- [Tuya CLI](https://github.com/TuyaAPI/cli) - Device credential extraction
- [TinyTuya Wizard](https://github.com/jasonacox/tinytuya) - Device discovery and setup
- [Home Assistant Supervisor](https://developers.home-assistant.io/docs/supervisor/) - Development environment

---

## 🆘 Troubleshooting Common Issues

### Device Not Detected
1. **Check Device ID Pattern**: Ensure pattern is added to `DEVICE_ID_PATTERNS`
2. **Verify Model Mapping**: Check `MODELS` dictionary in `const.py`
3. **Test Discovery**: Use debug mode to see if device is found but not recognized

### Entities Not Created
1. **Check Configuration**: Verify entity configuration in `device_types.py`
2. **Platform Loading**: Ensure required platforms are listed
3. **DP Validation**: Confirm DPs exist in actual device status

### Control Not Working
1. **DP Mapping**: Verify DP numbers match Things Data Model
2. **Data Types**: Ensure value types match (int vs string vs bool)
3. **Bitfield Logic**: Check zone/bitfield calculations for complex controls

### Performance Issues
1. **Async Operations**: Ensure all device communication is async
2. **Polling Rate**: Avoid excessive status polling
3. **Error Handling**: Implement proper timeouts and retries

---

**Ready to add your KKT Kolbe device? Follow this guide step-by-step and contribute to the growing device support!** 🚀

For questions or support, please open an issue on GitHub with your device's Things Data Model JSON.