# Changelog

All notable changes to the KKT Kolbe Home Assistant Integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.7.1] - 2025-10-18

### 🔧 CRITICAL: Home Assistant Best Practices Implementation

#### Fixed "Unknown" Entity Status Issue
- **Property Performance**: Entity properties no longer perform I/O operations
- **State Caching**: All entities now cache state in memory for instant property access
- **Coordinator Updates**: State updates only happen during coordinator refresh cycles
- **Standards Compliance**: Full adherence to Home Assistant entity development guidelines

#### Technical Architecture Improvements
- **Memory-Based Properties**: All entity properties (is_on, native_value, etc.) now return cached values
- **Smart State Updates**: `_update_cached_state()` method updates cached values from coordinator data
- **Enhanced Debugging**: Improved logging for data key compatibility (string vs integer keys)
- **Coordinator Integration**: Proper `_handle_coordinator_update()` implementation

#### Affected Entity Types
- **Switch Entities**: `is_on` property now returns cached boolean state
- **Number Entities**: `native_value` property now returns cached numeric values
- **Sensor Entities**: `native_value` property now returns cached sensor readings
- **Binary Sensor Entities**: `is_on` property now returns cached boolean status
- **Zone Entities**: All zone-specific entities use cached bitfield-decoded values

#### User Impact
- **Instant Response**: Entity states display immediately without delays
- **No More "Unknown"**: Entities should no longer show "Unknown" status due to I/O blocking
- **Better Performance**: Faster UI updates and reduced system load
- **Reliable States**: Consistent entity state reporting across all platforms

#### Compatibility
- **Backward Compatible**: No breaking changes to existing functionality
- **Enhanced Bitfield Support**: Zone entities still use full bitfield decoding
- **Debug Improvements**: Better coordinator data logging for troubleshooting

## [1.7.0] - 2025-10-18

### 🚀 MAJOR: Complete RAW Bitfield Implementation for IND7705HC

#### New Features
- **Full Bitfield Decoding**: Complete implementation for Base64-encoded RAW data points
- **All Zone Entities**: All 5 cooking zones now have full individual control
- **Professional Implementation**: Proper encoding/decoding instead of simplified configuration

#### Technical Implementation
- **New Bitfield Utils**: `bitfield_utils.py` with full Base64 ↔ Zone value conversion
- **Enhanced Entity Classes**: Zone-aware Number, Sensor, and BinarySensor entities
- **Smart Data Point Handling**: Automatic detection of bitfield vs. simple data points
- **Robust Error Handling**: Fallback to legacy methods for unknown configurations

#### Bitfield Data Points (Now Working)
- **DP 162**: Zone 1-5 Power Levels (0-25) ✅
- **DP 167**: Zone 1-5 Timers (0-255 min) ✅
- **DP 168**: Zone 1-5 Target Temperatures (0-300°C) ✅
- **DP 169**: Zone 1-5 Current Temperatures (read-only) ✅
- **DP 161**: Zone 1-5 Selection Status (bit-based) ✅
- **DP 163**: Zone 1-5 Boost Status (bit-based) ✅
- **DP 164**: Zone 1-5 Keep Warm Status (bit-based) ✅
- **DP 165**: Flex Zone Left/Right (bit-based) ✅
- **DP 166**: BBQ Mode Left/Right (bit-based) ✅
- **DP 105**: Zone 1-5 Error Status (bit-based) ✅

#### Entity Additions (Total: 42 new entities)
**Number Entities (15):**
- Zone 1-5: Power Level sliders (0-25)
- Zone 1-5: Timer sliders (0-255 min)
- Zone 1-5: Target Temperature sliders (0-300°C)

**Sensor Entities (5):**
- Zone 1-5: Current Temperature displays

**Binary Sensor Entities (22):**
- Zone 1-5: Error status indicators
- Zone 1-5: Selection status indicators
- Zone 1-5: Boost active indicators
- Zone 1-5: Keep Warm active indicators
- Flex Zone Left/Right status
- BBQ Mode Left/Right status

#### User Experience
- **Complete Zone Control**: Individual control for all 5 cooking zones
- **Professional UI**: Organized by zones with proper icons and device classes
- **Real-time Status**: Live updates for all zone states and temperatures
- **Error Monitoring**: Zone-specific error indicators
- **Mode Detection**: Visual indicators for boost, keep warm, flex, and BBQ modes

#### Compatibility
- **Backward Compatible**: Existing simple entities (DP 101-104, 108, 134, 145, 148-155) unchanged
- **Smart Detection**: Automatic detection between bitfield and simple data points
- **Fallback Support**: Legacy integer bitfield handling preserved

## [1.6.3] - 2025-10-18 [SUPERSEDED by 1.7.0]

### 🔧 HOTFIX: IND7705HC Cooktop "Unknown" Status Fix [TEMPORARY]

This release was superseded by v1.7.0 which implements proper bitfield decoding instead of removing entities.

## [1.6.2] - 2025-10-18

### 🔧 HOTFIX: ECCO HCM Fan Entity Configuration

#### Fixed
- **ECCO HCM Fan Entity Conflict**: Removed incorrect fan entity for ECCO HCM hood
- **Duplicate DP Issue**: DP 102 was configured for both fan and number entities
- **Correct Control Type**: ECCO HCM uses number slider (0-9) not fan entity with speeds

#### Technical Details
- **ECCO HCM Hood**: DP 102 is `fan_speed` VALUE (0-9), not ENUM
- **Removed fan entity** for ECCO HCM to prevent conflicts
- **Number entity remains** for proper slider-based speed control (0-9 levels)
- **Other hoods unchanged**: HERMES & STYLE, FLAT, and HERMES still use fan entities

#### User Impact
- **ECCO HCM users**: Use "Fan Speed" number slider instead of fan entity
- **Other hood users**: No change, fan entities work as expected
- **Cleaner entity list**: No more duplicate/conflicting entities

#### Hood Model Summary
- **HERMES & STYLE** (ypaixllljc2dcpae): ✅ Fan entity (DP 10, 5 speeds)
- **FLAT Hood** (luoxakxm2vm9azwu): ✅ Fan entity (DP 10, 5 speeds)
- **HERMES Hood** (0fcj8kha86svfmve): ✅ Fan entity (DP 10, 5 speeds)
- **ECCO HCM Hood** (gwdgkteknzvsattn): ✅ Number entity (DP 102, 0-9 slider)

---

## [1.6.1] - 2025-10-18

### 🔧 HOTFIX: Fan Entity Not Loading for HERMES & STYLE

#### Fixed
- **Fan Entity Not Loading**: Fixed fan entity not appearing for HERMES & STYLE hood (product_name: ypaixllljc2dcpae)
- **Wrong Data Point**: Corrected fan control from DP 2 to DP 10 (fan_speed_enum)
- **Enum Value Handling**: Fixed sending string values ("off", "low", "middle", "high", "strong") instead of numeric
- **Product Name Detection**: Removed hardcoded product name check, now uses device_types.py configuration

#### Technical Details
- Updated `fan.py` to use configuration from `device_types.py`
- Fixed data point mapping from DP 2 to DP 10
- Proper enum string value handling for fan_speed_enum
- Dynamic configuration loading based on product_name

#### User Impact
- **Fan control now works** for HERMES & STYLE hood
- **Speed control available** with 5 levels (off, low, middle, high, strong)
- **Proper UI integration** with percentage-based speed control

---

## [1.6.0] - 2025-10-18

### 🎯 FEATURE: Zone-Organized Entities & Optimized User Experience

#### Added
- **Zone-Grouped Entity Names**: IND7705HC entities now organized by cooking zone for better usability
  - Example: "Zone 1: Power Level", "Zone 1: Timer", "Zone 1: Current Temp"
  - Logical grouping instead of type-based grouping (all Zone 1 controls together)
- **Optimized Device Classes**: Correct Home Assistant device classes for better UI integration
  - Number entities: `device_class: "duration"` for timers, `device_class: "temperature"` for temps
  - Switch entities: Proper `device_class: "switch"` (not "outlet" for appliances)
  - Sensor entities: `device_class: "temperature"` for temperature readings
  - Binary sensor entities: `device_class: "problem"` for errors, `device_class: "running"` for status
- **Material Design Icons**: Intuitive icons for all entities
  - Power: `mdi:power`, Timer: `mdi:timer`, Temperature: `mdi:thermometer`
  - Zone numbers: `mdi:numeric-1-circle`, Boost: `mdi:flash`, Keep Warm: `mdi:thermometer-low`
- **Slider UI Mode**: Number entities use `mode: "slider"` for better touch control

#### Improved
- **User Experience**: Entities appear in logical cooking workflow order
  - Per zone: Power Level → Timer → Target Temp → Quick Level → Status → Error
  - Much more intuitive than scattered type-based grouping
- **Entity Naming**: Consistent "Zone X: Function" pattern for easy identification
- **UI Integration**: Better Home Assistant dashboard appearance with proper icons and device classes
- **Timer Ranges**: Confirmed 255-minute maximum (4+ hours) for zone timers - perfect for slow cooking

#### Technical Details
- Updated `device_types.py` with zone-organized entity configurations
- Added proper device classes for all entity types
- Implemented Material Design icon assignments
- Maintained backward compatibility with existing configurations

#### User Benefits
- **Logical Cooking Workflow**: All controls for Zone 1 grouped together, then Zone 2, etc.
- **Better Visual Appearance**: Proper icons and device classes in Home Assistant UI
- **Intuitive Controls**: Slider controls for power levels, timers, and temperatures
- **Professional Look**: Entity cards appear with appropriate icons and styling

---

## [1.5.16] - 2025-10-18

### 🔧 HOTFIX: Enhanced Connection Stability

#### Fixed
- **Connection Timeout**: Increased device connection timeout from 15 to 30 seconds
- **Retry Mechanism**: Added 3-attempt retry logic with 5-second delays between attempts
- **Error Logging**: Enhanced logging for better debugging of connection issues
- **Device Unreachability**: Improved handling when devices are temporarily offline

#### Technical Improvements
- **Robust Connection**: Better handling of network instability and device response delays
- **Timeout Management**: More appropriate timeout values for real-world device responses
- **Error Recovery**: Automatic retry with exponential backoff for transient connection failures
- **Debug Information**: More detailed logging for troubleshooting connection problems

#### Addresses Issues
- Resolves "Connection timeout after 15 seconds" errors in logs
- Improves reliability for devices on slow or congested networks
- Better handling of device startup/discovery phases
- Reduces false connection failures due to temporary network issues

---

## [1.5.14] - 2025-10-18

### 📋 DOCUMENTATION: Device Verification Status & Community Support

#### Improved
- **Device Status Documentation**: Clear verification status for all 5 supported devices
- **API Verification Methodology**: Documented process for ensuring device accuracy
- **Community Support Call**: Added section requesting HERMES device API verification
- **Transparency**: Clear indication of which devices are API-verified vs specification-based

#### Documentation Updates
- **Device List**: Added verification status indicators (✅/❓) for each device
- **API-Verified Devices (4/5)**: HERMES & STYLE, FLAT, ECCO HCM, IND7705HC
- **Community Needed (1/5)**: KKT HERMES requires real device API data
- **Verification Files**: Referenced actual API data files in known_configs/

#### User Benefits
- **Clear Expectations**: Users know which devices have been verified with real API data
- **Community Engagement**: HERMES users can contribute to improve integration reliability
- **Transparency**: Open about current limitations and how to address them
- **Quality Assurance**: Emphasis on API-verified configurations for best experience

---

## [1.5.13] - 2025-10-18

### 🆕 NEW DEVICE: KKT Kolbe FLAT Hood Support

#### Added
- **New Device Support**: KKT Kolbe FLAT Hood (Model ID: luoxakxm2vm9azwu)
- **Device Recognition**: Automatic detection for device pattern "bff904d332b57484da"
- **Entity Configuration**: Full entity support with 5 data points (simplified vs HERMES & STYLE)

#### Device Specifications
- **Model**: KKT Kolbe FLAT Hood
- **Category**: Range Hood (simplified version)
- **Data Points**: 5 DPs (vs 6 for HERMES & STYLE)
  - DP 1: Main Power Switch (bool)
  - DP 4: Light Control (bool) - Standard lighting only
  - DP 6: Filter Cleaning Reminder (bool)
  - DP 10: Fan Speed (enum: off/low/middle/high/strong)
  - DP 13: Timer (value: 0-60 minutes)

#### Key Differences from HERMES & STYLE
- **No RGB Lighting**: DP 101 (RGB Mode) not present
- **Simplified Design**: 5 data points instead of 6
- **Standard Light**: Only basic on/off lighting control
- **Same Core Functions**: Power, fan, timer, filter reminder identical

#### Technical Implementation
- **Automatic Discovery**: Device ID pattern recognition
- **Entity Platforms**: Fan, Light, Switch, Sensor, Number
- **API Verified**: Configuration based on actual device API data
- **Data Type Accuracy**: All entity types match device specifications

---

## [1.5.12] - 2025-10-18

### 🎯 MAJOR FIX: Correct Device Data Points Based on API Analysis

#### Fixed
- **CRITICAL**: HERMES & STYLE device configuration corrected to match actual API properties
- **Data Point Accuracy**: Removed non-existent DPs that were causing "unknown" entity states
- **Entity Cleanup**: Eliminated redundant entities that don't exist in real device model
- **Switch Consolidation**: Proper Power switch behavior vs Fan speed control separation

#### Technical Analysis
- **API Verification**: Used actual Tuya API "Query Things Data Model" to verify properties
- **HERMES & STYLE**: Reduced from 20+ DPs to actual 6 DPs (1, 4, 6, 10, 13, 101)
- **Removed Phantom Entities**: Eliminated sensors/switches for non-existent DPs (2, 3, 5, 7-9, 11-12, 14-17, 102-103)
- **Entity Optimization**: Only create entities for properties that actually exist

#### Root Cause
The integration was creating entities for data points that don't exist in the actual device firmware, causing:
- Multiple "unknown" status entities
- Redundant controls for same functionality
- Confusion between main power (DP 1) and fan speed (DP 10)

#### User Impact
- **Cleaner UI**: No more phantom entities showing "unknown" status
- **Correct Controls**: Clear separation between device power and fan speed
- **Better Performance**: Fewer unnecessary entities to update
- **Accurate Status**: All entities now reflect actual device state

---

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

[1.5.14]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.5.14
[1.5.13]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.5.13
[1.5.12]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.5.12
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