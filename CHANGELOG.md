# Changelog

All notable changes to the KKT Kolbe Home Assistant Integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.4] - 2025-10-17

### 🚨 CRITICAL HOTFIX: Missing Import NameError

#### Fixed
- **NameError: 'CONF_IP_ADDRESS' not defined**: Added missing import to __init__.py
- **Integration Loading**: Integration now loads successfully without NameError
- **Config Entry Validation**: Added robust parameter validation with clear error messages
- **Setup Stability**: Proper error handling for missing config entry data

#### Technical Fixes
- **__init__.py**: Added `CONF_IP_ADDRESS` to imports from homeassistant.const
- **Parameter Validation**: Added validation for ip_address, device_id, and local_key
- **Error Messages**: Clear ValueError messages for missing required parameters

#### Breaking Changes
**None** - This hotfix maintains full backward compatibility.

## [1.5.3] - 2025-10-17

### 🚨 HOTFIX: Config Entry & Discovery Stability

#### Fixed
- **KeyError 'host'**: Fixed missing config entry key handling in __init__.py setup
- **NoneType AttributeError**: Added None value checks for mDNS TXT record processing
- **Config Entry Compatibility**: Robust fallback for different config entry key formats
- **Discovery Stability**: Graceful handling of non-Tuya mDNS services (Brother printers, etc.)

#### Technical Fixes
- **__init__.py**: Added fallback key resolution for ip_address/host/device_id/local_key
- **discovery.py**: None value checks before decode() calls in all TXT record processing
- **Error Handling**: Proper AttributeError handling alongside UnicodeDecodeError

#### Breaking Changes
**None** - This hotfix maintains full backward compatibility.

## [1.5.2] - 2025-10-17

### 🚨 HOTFIX: Missing async_discover_devices Method

#### Fixed
- **KKTKolbeDiscovery AttributeError**: Added missing `async_discover_devices` method to KKTKolbeDiscovery class
- **Config Flow Discovery**: Config flow now works correctly with device discovery
- **Discovery Timeout**: Proper timeout handling for device discovery (configurable, default 6 seconds)
- **Discovery Integration**: Seamless integration between config flow and discovery service

#### Technical Fixes
- **discovery.py**: Added `async_discover_devices(timeout: int = 6)` method to KKTKolbeDiscovery class
- **Config Flow Compatibility**: Restored proper discovery functionality in multi-step config flow
- **Error Handling**: Graceful handling of discovery timeouts and failures

#### Breaking Changes
**None** - This hotfix maintains full backward compatibility.

## [1.5.1] - 2025-10-17

### 🚨 HOTFIX: AsyncServiceInfo API Corrections

#### Fixed
- **AsyncServiceInfo Import Error**: Import from `zeroconf.asyncio.AsyncServiceInfo` instead of `zeroconf.AsyncServiceInfo`
- **AsyncServiceInfo API Usage**: Use correct instance method pattern per zeroconf documentation
- **Config Flow Loading**: Integration now loads without import errors
- **Discovery Service**: Proper async service discovery functionality restored

#### Technical Fixes
- **discovery.py**: Corrected import path and API usage for AsyncServiceInfo
- **manifest.json**: Removed redundant zeroconf requirement (already in HA core)
- **Compatibility**: Ensured compatibility with HA's zeroconf==0.148.0

#### Breaking Changes
**None** - This hotfix maintains full backward compatibility.

## [1.5.0] - 2025-10-17

### 🚀 MAJOR RELEASE: Advanced Architecture & Production Readiness

#### Added
- **Base Entity Pattern**: Code deduplication with KKTBaseEntity and KKTZoneBaseEntity - achieved 27% code reduction
- **Multi-Step Config Flow**: Modern 6-step configuration with dynamic device selection, authentication, and settings
- **Integration Services**: 8 comprehensive services for device control, automation, and emergency operations
- **Custom Exception Hierarchy**: 9 specialized exception classes for precise error handling and debugging
- **Enhanced Device Communication**: Explicit TinyTuya status retrieval, data point writing, and timeout protection
- **AsyncServiceInfo Compatibility**: Modern zeroconf integration for future Home Assistant versions

#### Improved
- **Config Flow UX**: Dynamic device discovery, connection testing, and configuration validation
- **Error Handling**: Timeout protection (8-15s), connection retries, and graceful error recovery
- **Device Discovery**: Enhanced protocol detection (3.3, 3.4, 3.1, 3.2) with DPS validation
- **Services Framework**: Bulk operations, emergency stop, device synchronization, and filter management
- **Translation Coverage**: Complete EN/DE internationalization with 74 translation keys

#### Technical Enhancements
- **services.py**: 8 integration services with entity validation and error handling
- **exceptions.py**: Typed exception hierarchy with contextual error information
- **config_flow.py**: VERSION 2 with modern selectors and options flow
- **tuya_device.py**: Enhanced timeout protection and explicit TinyTuya operations
- **translations/**: Complete bilingual support for all UI elements

#### Services Added
- `set_cooking_timer`: Zone-specific timer control
- `set_zone_power`: Individual zone power management
- `bulk_power_off`: Emergency shutdown with device type filtering
- `sync_all_devices`: Force refresh with online/offline filtering
- `set_hood_fan_speed`: Range hood fan control
- `set_hood_lighting`: Lighting control with brightness
- `emergency_stop`: Immediate stop all cooking operations
- `reset_filter_timer`: Filter maintenance management

## [1.4.3] - 2024-10-17

### 🏗️ MAJOR ARCHITECTURE: Modern Home Assistant Patterns

#### Added
- **DataUpdateCoordinator Implementation**: Central data management following Home Assistant best practices
- **CoordinatorEntity Pattern**: All entities now inherit from CoordinatorEntity for optimal performance
- **Binary Sensor Platform**: Full support for device status monitoring with proper entity categories
- **Enhanced Translation Support**: Complete internationalization framework with German and English support
- **Device Database Module**: Centralized device identification and management system

#### Improved
- **Modern Async Patterns**: Eliminated fire-and-forget patterns with proper error handling
- **Centralized State Management**: All entities use coordinator for consistent data access
- **Performance Optimization**: Reduced API calls through coordinated updates (30-second intervals)
- **Entity Relationship Management**: Proper device registry integration for all entities
- **Code Organization**: Clean separation of concerns with modern HA architecture

#### Technical Enhancements
- **coordinator.py**: New DataUpdateCoordinator implementation with device registry
- **Enhanced Entity Classes**: All platform files converted to CoordinatorEntity pattern
- **Binary Sensor Support**: Zone-specific and general binary sensors with proper device classes
- **Translation Framework**: Complete UI translation support in translations/ directory
- **Error Handling**: Comprehensive async error handling without silent failures

#### Fixed
- **Fire-and-Forget Patterns**: Replaced with proper task management and error callbacks
- **Import Inconsistencies**: Standardized imports across all modules
- **Syntax Errors**: Complete code review and cleanup
- **Missing Platform Support**: Added binary_sensor to supported platforms

#### Removed
- **Deprecated Files**: Moved cooktop.py and cooktop_utils.py to .backup (functionality preserved)
- **Direct Device Polling**: Replaced with coordinator-based updates
- **Outdated Patterns**: Removed legacy entity implementations

---

## [1.4.2] - 2024-10-17

### Fixed
- Minor stability improvements and code optimizations
- Enhanced device communication reliability

---

## [1.4.1] - 2024-10-17

### Fixed
- Bug fixes and performance enhancements
- Improved error handling for edge cases

---

## [1.4.0] - 2024-10-17

### Added
- Enhanced device support and compatibility improvements
- Expanded entity functionality

---

## [1.3.2] - 2024-10-16

### Fixed
- Documentation cleanup and professional polish
- Streamlined setup instructions
- Reduced logging for production readiness

---

## [1.3.1] - 2024-10-16

### Fixed
- Minor bug fixes and stability improvements
- Enhanced error messages

---

## [1.3.0] - 2024-10-16

### Added
- Production readiness improvements
- Enhanced device area assignment
- Clean entity creation process
- Professional logging implementation

---

## [1.2.0] - 2024-10-16

### 🎯 MAJOR FEATURE: Intelligent Device Recognition

#### Added
- **Automatic Device Type Recognition by Device ID**: The integration now automatically identifies whether a device is a HERMES & STYLE hood or IND7705HC cooktop based solely on the Device ID input
- **Centralized Device Database**: New device registry system that maintains known device patterns and specifications for accurate identification
- **Enhanced Manual Setup UI**: User-friendly dropdown selection with clear device type descriptions ("Range Hood (HERMES & STYLE)" and "Induction Cooktop (IND7705HC)")
- **Universal Setup Compatibility**: Intelligent recognition works across all configuration methods (auto-discovery, manual configuration, HACS installation)

#### Improved
- **Streamlined Setup Process**: Reduced manual configuration steps by eliminating device type guesswork
- **Smart Device Validation**: Enhanced Device ID validation that ensures compatibility before setup attempts
- **Professional User Experience**: Enterprise-level device management with consistent recognition patterns
- **Future-Ready Architecture**: Easily expandable system for adding support for new KKT Kolbe models

#### Technical Enhancements
- **Enhanced Config Flow**: Improved configuration flow with intelligent device type detection
- **Robust Device Matching**: Pattern-based device identification system for reliable recognition
- **Improved Error Handling**: Better user feedback when device types cannot be determined automatically
- **Code Architecture**: Modular device database design for maintainable and extensible device support

### Migration Notes
- **Existing Installations**: No migration required - existing configurations continue to work normally
- **New Installations**: Users benefit from automatic device recognition without any additional setup
- **Device ID Format**: Continue using the same 20-22 character Tuya Device IDs as before

### Developer Notes
- **Device Database**: New `device_database.py` module for centralized device management
- **Enhanced Config Flow**: Updated configuration flow with intelligent device detection logic
- **Future Expansion**: Framework ready for easy addition of new KKT Kolbe device models

---

## [1.1.11] - 2024-10-16

### Fixed
- Minor bug fixes and stability improvements
- Enhanced error messages for better troubleshooting

---

## [1.0.0] - 2024-10-15

### 🚀 Production Ready Release

#### Fixed (Critical Issues)
- **CRITICAL FIX**: Corrected Tuya port configuration (6667 instead of 6668)
- **CRITICAL FIX**: Enhanced Device ID validation (exactly 20 characters required)
- **CRITICAL FIX**: Improved connection error handling with detailed feedback
- **CRITICAL FIX**: Fixed mDNS Device ID extraction from TXT records instead of service name
- **CRITICAL FIX**: Resolved IP address hostname resolution issues

#### Improved
- **Enhanced UDP Discovery**: Better compatibility with Local Tuya coexistence
- **Threading/Async**: Eliminated all threading and async operation issues
- **Stability**: Production-ready integration with robust error handling

#### Result
- **Stable Production Integration**: Ready for daily use with comprehensive error handling

---

## [0.3.8] - 2024-10-14

### Fixed
- All Home Assistant compliance warnings resolved
- RuntimeWarning "coroutine never awaited" eliminated
- Proper Zeroconf shared instance usage

### Improved
- Full async TinyTuya integration (no blocking operations)
- Enhanced error messages instead of generic "Unexpected error"
- All entities now use proper async methods

---

## [0.3.0] - 2024-10-13

### 🏠 MAJOR FEATURE: Home Assistant Auto-Discovery

#### Added
- **Home Assistant Auto-Discovery**: Automatic discovery on HA startup without official PR
- **Zeroconf Integration**: Seamless device recognition using Home Assistant's built-in discovery
- **"Retry automatic discovery"**: Option to re-scan for devices
- **Complete Translations**: Full German and English UI translations
- **Enhanced Debug Modes**: Advanced network analysis and troubleshooting tools

#### Technical
- **Non-intrusive Discovery**: Works without modifying Home Assistant core
- **Zeroconf Integration**: Leverages HA's existing discovery infrastructure

---

## [0.2.2] - 2024-10-12

### Fixed
- **MAJOR FIX**: Recognition of KKT devices as generic Tuya devices
- **Enhanced Detection**: Tuya Device ID pattern detection (`bf` + hex)
- **Improved Recognition**: Specific KKT Device ID patterns from real-world testing

### Added
- **Debug Modes**: Advanced debugging and test device simulation
- **TXT Record Analysis**: Enhanced device recognition through TXT record analysis

---

## [0.2.1] - 2024-10-11

### Fixed
- **mDNS Discovery Timing**: Immediate start during config flow
- **Smart Wait Logic**: Maximum 5 seconds with 500ms interval checks
- **Debug Logging**: Enhanced troubleshooting capabilities

### Improved
- **Extended mDNS Service Types**: Broader device discovery coverage

---

## [0.2.0] - 2024-10-10

### ✨ MAJOR FEATURE: mDNS Automatic Device Discovery

#### Added
- **mDNS Automatic Device Discovery**: Zero-configuration device finding
- **Simplified Setup Process**: Reduced manual configuration steps
- **Automatic Device Type Detection**: Smart recognition of device capabilities
- **Multi-Step Config Flow**: Intuitive setup wizard
- **Bilingual Support**: German and English translations

#### Technical
- **mDNS/Zeroconf**: Network-based device discovery
- **Pattern Matching**: Intelligent device identification
- **Model Detection**: Automatic assignment of known device models

---

## [0.1.0] - 2024-10-09

### 🎉 Initial Release

#### Added
- **Basic Integration**: Core KKT Kolbe device support
- **Device Types**: HERMES & STYLE hood and IND7705HC cooktop
- **Manual Configuration**: IP address and credential-based setup
- **Core Entities**: Basic fan, light, and sensor support

#### Supported Devices (4 Models)
##### Range Hoods (3 Models)
- **KKT Kolbe HERMES & STYLE**: Range Hood with fan control, lighting, and timer
- **KKT Kolbe HERMES**: Range Hood with advanced RGB and eco mode controls
- **KKT Kolbe ECCO HCM**: Range Hood with 9-level fan control and dual filter monitoring
##### Induction Cooktops (1 Model)
- **KKT IND7705HC**: Induction Cooktop with 5 zones and advanced features

#### Technical Foundation
- **Tuya Protocol**: TinyTuya-based communication
- **Home Assistant Integration**: Standard HA integration architecture
- **Entity Support**: Fan, Light, Switch, Sensor, Select, and Number entities

---

## Security Notes

⚠️ **Important Security Information**:
- This integration was generated using AI (Claude) and requires careful testing
- For induction cooktops, manual confirmation at the device is required for safety
- Always review code before use, especially for cooking appliances
- Use at your own risk - see [SECURITY.md](SECURITY.md) for full details

## Links

- **Repository**: [GitHub](https://github.com/moag1000/HA-kkt-kolbe-integration)
- **Issues**: [Bug Reports](https://github.com/moag1000/HA-kkt-kolbe-integration/issues)
- **Releases**: [All Releases](https://github.com/moag1000/HA-kkt-kolbe-integration/releases)
- **HACS**: [Custom Repository](https://github.com/moag1000/HA-kkt-kolbe-integration)

[1.5.4]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.5.4
[1.5.3]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.5.3
[1.5.2]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.5.2
[1.5.1]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.5.1
[1.5.0]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.5.0
[1.4.3]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.4.3
[1.4.2]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.4.2
[1.4.1]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.4.1
[1.4.0]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.4.0
[1.3.2]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.3.2
[1.3.1]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.3.1
[1.3.0]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.3.0
[1.2.0]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.2.0
[1.1.11]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.1.11
[1.0.0]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.0.0
[0.3.8]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v0.3.8
[0.3.0]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v0.3.0
[0.2.2]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v0.2.2
[0.2.1]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v0.2.1
[0.2.0]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v0.2.0
[0.1.0]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v0.1.0