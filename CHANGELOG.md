# Changelog

All notable changes to the KKT Kolbe Home Assistant Integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.11] - 2025-10-18

### 🔧 HOTFIX: Exception Handling & Entity Status

#### Fixed
- **CRITICAL FIX**: Fixed `KKTTimeoutError` and `KKTConnectionError` constructor signatures
- **Exception Handling**: Proper parameter mapping for timeout and connection exceptions
- **Entity Availability**: Enhanced availability detection with detailed logging for debugging
- **Status Visibility**: Improved coordinator timeout handling - maintains last known state instead of failing

#### Improved
- **Better Diagnostics**: Added detailed logging for "unknown" entity status troubleshooting
- **Connection Resilience**: Timeout errors no longer cause complete entity unavailability
- **Data Point Debugging**: Enhanced logging when data points are missing from device data
- **UI Enhancement**: Power switch now uses lightning bolt icon (⚡) instead of power icon

#### Technical Fixes
- **exceptions.py**: Fixed constructor signatures to match usage in tuya_device.py
- **coordinator.py**: Graceful timeout handling - keeps last state on connection errors
- **base_entity.py**: Enhanced availability checks and data point value logging
- **switch.py**: Updated power switch icon to `mdi:lightning-bolt`

#### Root Cause
- Exception constructors had mismatched parameter names vs actual usage
- Coordinator was failing completely on timeouts instead of preserving state
- Missing diagnostic logging made "unknown" status difficult to troubleshoot

---

## [1.5.10] - 2025-10-18

### 🚨 EMERGENCY HOTFIX: Duplicate device_info Property

#### Fixed
- **CRITICAL FIX**: Removed duplicate `device_info` property definition causing AttributeError
- **Entity Loading**: All entity platforms now load correctly without property conflicts
- **Property Implementation**: Fixed device_info property overriding correct lazy-loading implementation

#### Root Cause
- Duplicate `device_info` property on lines 168-170 was overriding the correct implementation
- Second property referenced non-existent `self._device_info` attribute
- Result: `AttributeError: 'KKTKolbeSwitch' object has no attribute '_device_info'`

#### Technical Fix
- **base_entity.py**: Removed duplicate property definition (lines 168-170)
- **Property Access**: Correct lazy-loading implementation with `_device_info_cached` now works
- **All Platforms**: Switch, sensor, number, select, binary_sensor platforms now load correctly

---

## [1.5.9] - 2025-10-18

### 🚨 CRITICAL HOTFIX: Entity Platform Setup Failures

#### Fixed
- **CRITICAL FIX**: Fixed `AttributeError: 'NoneType' object has no attribute 'data'` in entity initialization
- **CRITICAL FIX**: Fixed UDP port conflicts (6666/6667 in use) causing discovery failures
- **Platform Setup**: All entity platforms (switch, sensor, number, etc.) now load correctly
- **Device Info Access**: Implemented safe `device_info` property pattern for CoordinatorEntity
- **Entity Loading**: Entities now properly initialize and appear in Home Assistant
- **Discovery Stability**: Fixed multiple discovery instance creation causing port conflicts

#### Technical Fixes
- **base_entity.py**: Converted `device_info` from `__init__` attribute to property with lazy loading
- **Safe hass.data Access**: All `self.hass.data` access now safely handles None values
- **CoordinatorEntity Pattern**: Proper implementation following Home Assistant best practices
- **Entity Lifecycle**: Fixed entity initialization order to prevent None access errors
- **config_flow.py**: Fixed UDP port conflicts by using global discovery instance instead of creating multiple instances
- **Discovery Singleton**: Config flow now uses `async_start_discovery()` instead of creating `KKTKolbeDiscovery()` instances

#### Root Cause
- `self.hass` is not available during entity `__init__` in CoordinatorEntity pattern
- Device info was being built too early, causing AttributeError on all entity platforms
- Solution: Device info now built as property when first accessed (after hass is available)

#### Breaking Changes
**None** - This hotfix restores entity functionality without breaking existing configurations.

## [1.5.8] - 2025-10-18

### 🚨 CRITICAL HOTFIX: Invalid Button Selector Type

#### Fixed
- **CRITICAL FIX**: Replaced unsupported `selector.button()` with proper `bool` fields in config flow
- **Import Error**: Fixed "Unknown selector type button found" that prevented integration loading
- **Config Flow Compatibility**: All navigation now uses Home Assistant supported selector types

#### Technical Fixes
- **config_flow.py**: Replaced all `selector.selector({"button": {}})` with `vol.Optional(..., default=False/True): bool`
- **Navigation Logic**: Maintained existing navigation behavior with proper boolean fields
- **Test Connection**: Kept `default=True` for `test_connection` fields to maintain expected behavior
- **All Platforms**: Ensured compatibility with all Home Assistant versions

#### Breaking Changes
**None** - This hotfix maintains full functionality while fixing critical loading errors.

## [1.5.7] - 2025-10-18

### 🎯 ENHANCEMENT: Advanced Config Flow & Device Selection

#### Added
- **Device Type Selection**: Manual configuration now includes specific device type selection (HERMES & STYLE, HERMES, ECCO HCM, IND7705HC)
- **Proper Button Navigation**: All config flow navigation now uses proper button selectors instead of boolean fields
- **Enhanced Device Information**: Manual device setup now creates proper device names and categories based on selected type

#### Fixed
- **Config Flow UX**: Replaced confusing boolean checkboxes with proper action buttons for navigation
- **Device Type Logic**: Fixed manual configuration device type mapping to work with new specific device selection
- **Translation Completeness**: Added missing translation keys for device type selector in both German and English

#### Technical Improvements
- **config_flow.py**: Updated all navigation schemas to use `selector.button()` instead of boolean fields
- **config_flow.py**: Enhanced manual step with proper device type mapping and naming
- **translations/**: Added complete translation support for new device type selector
- **Better UX**: Navigation buttons now appear as clickable buttons rather than toggle switches

#### Breaking Changes
**None** - This enhancement maintains full backward compatibility while significantly improving user experience.

## [1.5.6] - 2025-10-18

### 🐛 BUGFIX: Translation & Discovery Issues

#### Fixed
- **Translation Error**: Fixed missing `fallback_info` variable in German discovery step translation
- **"Unknown IP" Display**: Fixed config flow showing "Unknown IP" instead of actual device IP addresses
- **Discovery Key Consistency**: Standardized all discovery methods to use consistent "ip" key instead of mixed "ip"/"host" usage
- **UDP Port Conflicts**: Fixed duplicate UDP discovery startup causing "Address in use" errors

#### Technical Fixes
- **config_flow.py**: Always provide `fallback_info` variable, even when empty, to prevent translation errors
- **config_flow.py**: Enhanced IP address resolution with fallback logic for both "ip" and "host" keys
- **discovery.py**: Standardized all device info dictionaries to use "ip" key consistently across UDP, mDNS, and test methods
- **discovery.py**: Added duplicate startup protection to prevent UDP port conflicts
- **__init__.py**: Removed redundant discovery startup in config entry setup
- **Improved Discovery**: Better handling of device information extraction from different discovery sources

#### Breaking Changes
**None** - This bugfix maintains full backward compatibility.

## [1.5.5] - 2025-10-18

### 🚀 MAJOR IMPROVEMENT: Config Flow Navigation & UX

#### Added
- **Bi-directional Navigation**: Full back/forward navigation between all config flow steps
- **Discovery ↔ Manual Switching**: Switch between automatic discovery and manual configuration at any time
- **Navigation Buttons**: "Back to..." buttons in all config flow steps for intuitive navigation
- **Smart Discovery Caching**: Discovery results cached between navigation to avoid re-scanning
- **Improved UX**: Logical flow progression with escape routes at every step

#### Enhanced Config Flow Steps
- **Discovery Step**: Added "Use Manual Configuration" option when no devices found
- **Manual Step**: Added "Back to Discovery" option for easy switching
- **Authentication Step**: Added "Back to Previous Step" with smart routing
- **Settings Step**: Added "Back to Authentication" option
- **Confirmation Step**: Added "Back to Settings" option for final review

#### Technical Improvements
- **Optimized Discovery**: Discovery only runs on first visit or explicit retry request
- **State Preservation**: User choices preserved during navigation between steps
- **Error Recovery**: Better error handling with navigation alternatives
- **Flow Logic**: Improved step routing logic for intuitive user experience

#### Breaking Changes
**None** - This enhancement maintains full backward compatibility.

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

[1.5.11]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.5.11
[1.5.10]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.5.10
[1.5.9]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.5.9
[1.5.8]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.5.8
[1.5.7]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.5.7
[1.5.6]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.5.6
[1.5.5]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.5.5
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