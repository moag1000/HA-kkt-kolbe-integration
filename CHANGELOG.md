# Changelog

All notable changes to the KKT Kolbe Home Assistant Integration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0-beta.1] - 2024-10-20

### 🎯 Major Beta Release: TinyTuya API & Enhanced Stability

This release introduces significant architectural improvements and new features while maintaining backward compatibility for existing users.

### Added
- **TinyTuya Cloud API Integration**
  - Full API client implementation with authentication
  - Hybrid coordinator supporting local/cloud fallback
  - Shadow properties for real-time synchronization
  - Dynamic device factory from API metadata
  - API discovery for automatic device detection

- **Enhanced Reconnection System**
  - Automatic reconnection with exponential backoff
  - Device state tracking (ONLINE, OFFLINE, RECONNECTING, UNREACHABLE)
  - Health monitoring with periodic checks
  - Manual reconnection service
  - Connection status service

- **Improved Authentication**
  - Reauth flow for expired credentials
  - Local key update service for device resets
  - API credential management
  - Support for multiple auth methods

- **New Services**
  - `reconnect_device`: Manually trigger device reconnection
  - `update_local_key`: Update local key after device reset
  - `get_connection_status`: Query current connection state

### Changed
- Updated to modern asyncio APIs (`get_running_loop()`)
- Enhanced state caching mechanism for all entity types
- Improved error handling order (error → log)
- Refactored coordinator architecture for better modularity
- Updated all dependencies to latest versions
- Enhanced timeout handling with `async_timeout`

### Fixed
- Deprecated `config_entry` usage (HA 2025.12 compatibility)
- `asyncio.get_event_loop()` deprecation warnings
- Error handling order throughout codebase
- State caching for all entity types
- Falsy value handling (0, False) in bitfield utils
- Connection stability issues with retry logic

### Technical Improvements
- Full Home Assistant best practices compliance
- Comprehensive type hints throughout codebase
- Enhanced logging with proper error context
- Improved resource management and cleanup
- Better exception handling and recovery

## [1.7.10] - 2024-10-19

### Fixed
- **HOTFIX**: JSON syntax error in English translation file
- Missing commas in translation structure causing parsing failures

## [1.7.9] - 2024-10-19

### Added
- **State Caching System**
  - Intelligent value storage preventing "unknown" states
  - Timestamp tracking for last successful updates
  - Cached values persist during temporary disconnections

### Changed
- Enhanced config flow with full device ID display
- Improved UI with proper newline rendering
- Selective advanced entities (only for induction cooktops)

### Fixed
- All device configurations standardized
- RGB mode values corrected (0-9 range)
- Light switch entities consistent across all hood models

## [1.7.8] - 2024-10-18

### Fixed
- Complete fix for all unknown entity states
- Enhanced data point availability checking
- Improved zone-specific entity handling

## [1.7.7] - 2024-10-18

### Fixed
- **CRITICAL**: Falsy values (0, False) incorrectly treated as None
- Bitfield utilities now properly handle all valid values
- Power level 0 and temperature 0 now work correctly

## [1.7.6] - 2024-10-18

### Added
- Enhanced debug logging for troubleshooting unknown entities
- Detailed data point availability reporting

## [1.7.5] - 2024-10-17

### Fixed
- HERMES & STYLE fan entity configuration
- IND7705HC zone entity mappings
- Improved entity availability detection

## [1.7.4] - 2024-10-17

### Fixed
- HERMES & STYLE hood fan speed control
- Proper DP mapping for fan operations

## [1.7.2] - 2024-10-17

### Fixed
- **HOTFIX**: Temperature unit configuration
- Celsius as default unit for cooktop zones

## [1.7.1] - 2024-10-17

### Added
- Critical Home Assistant best practices implementation
- Enhanced error handling and logging

## [1.6.2] - 2024-10-16

### Fixed
- **HOTFIX**: ECCO HCM fan entity configuration
- Corrected fan speed mappings

## [1.6.1] - 2024-10-16

### Fixed
- **HOTFIX**: Fan entity fix for HERMES & STYLE hood
- Proper speed level handling

## [1.6.0] - 2024-10-16

### Added
- Zone-organized entities for better user experience
- Enhanced entity categorization
- Improved device organization

## [1.5.16] - 2024-10-15

### Fixed
- **HOTFIX**: Enhanced connection stability
- Improved timeout handling
- Better error recovery

## Earlier Versions

For changes prior to v1.5.16, please refer to the git commit history.

---

[2.0.0-beta.1]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v2.0.0-beta.1
[1.7.10]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.7.10
[1.7.9]: https://github.com/moag1000/HA-kkt-kolbe-integration/releases/tag/v1.7.9