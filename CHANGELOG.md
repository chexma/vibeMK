# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.6] - 2025-08-23

### Tested
- **Cross-Version User Roles Compatibility** - Comprehensive testing across CheckMK versions
  - Verified full compatibility of user roles management handler with CheckMK 2.3 and 2.4
  - All CRUD operations (Create, Read, Update, Delete) work identically on both versions
  - Documented permission count differences: Admin (576→580), User (446→448)
  - Confirmed API endpoint stability and response structure consistency
  - Enhanced cross-version testing methodology for future handler development

### Technical Improvements
- Complete test coverage for user roles handler across both CheckMK test instances
- Validated seamless operation without code modifications between versions
- Documented version differences for monitoring expansion in CheckMK 2.4

## [0.3.5] - 2025-08-23

### Fixed
- **CheckMK Acknowledgement Handler** - Complete compatibility fix for both CheckMK 2.3 and 2.4
  - Fixed version detection using API version endpoint with port fallback
  - Unified endpoint usage: both versions use `domain-types/acknowledge/collections/host` and `domain-types/acknowledge/collections/service`
  - Resolved HTTP 404 errors by removing incorrect legacy endpoint assumptions
  - Proper handling of HTTP 422 responses for services not in problem state (correct behavior)

### Enhanced
- **Cross-Version Compatibility** - Seamless operation across CheckMK versions
  - Automatic version detection (2.3 vs 2.4+) with fallback mechanisms
  - Port-based version inference (8080 = 2.3, 8081 = 2.4+)
  - CheckMK 2.4+ exclusive features (expire_on parameter) properly handled

### Technical Improvements
- Improved error handling with proper CheckMK API response interpretation
- Enhanced logging for version detection and endpoint selection
- Comprehensive test coverage against both CheckMK test instances
- Updated documentation with working API endpoint patterns

## [0.3.3] - 2025-08-22

### Added
- **Complete Service Group Management System** - Create, manage, and organize service groups
  - `vibemk_create_service_group` - Create new service groups with name and alias
  - `vibemk_list_service_groups` - List all configured service groups with details
  - `vibemk_get_service_group` - Get detailed information about specific service groups
  - `vibemk_update_service_group` - Update service group aliases and configurations
  - `vibemk_delete_service_group` - Remove service groups from CheckMK
  - `vibemk_bulk_create_service_groups` - Create multiple service groups efficiently
  - `vibemk_bulk_update_service_groups` - Update multiple service groups at once
  - `vibemk_bulk_delete_service_groups` - Delete multiple service groups in bulk

### Features
- **Service Organization** - Logical grouping of services for better monitoring structure
- **Bulk Operations** - Efficient management of multiple service groups simultaneously
- **Input Validation** - Comprehensive name validation (letters, numbers, hyphens, underscores)
- **Existence Checks** - Prevent duplicate creation and handle missing groups gracefully
- **ETag Support** - Proper handling of concurrent updates with If-Match headers
- **CheckMK Integration** - Full integration with CheckMK configuration activation workflow

### Technical Improvements
- Service group name pattern validation with regex
- Structured error handling for API operations
- Comprehensive response formatting with operation status
- Integration with CheckMK REST API service_group_config endpoints

## [0.3.2] - 2025-08-22

### Added
- **Enhanced Host Management System** - Advanced host operations with comprehensive validation
  - `vibemk_validate_host_config` - Pre-deployment validation with IP and hostname checks
  - `vibemk_compare_host_states` - Compare desired vs current host configuration  
  - `vibemk_get_host_effective_attributes` - Show host attributes including folder inheritance
  - `vibemk_create_cluster_host` - Create multi-node cluster hosts with automatic agent configuration

### Enhanced
- **Flexible Attribute Management** - Extended `vibemk_update_host` with multiple update modes
  - `update` mode - Merge attributes with existing configuration (default)
  - `overwrite` mode - Replace all attributes completely
  - `remove` mode - Delete specific attributes by name
- **Advanced Host Creation** - Enhanced `vibemk_create_host` with comprehensive validation
  - Pre-creation existence checks to prevent duplicates
  - Detailed success reports with attribute summaries
  - Better folder path handling with CheckMK format conversion (/ → ~)
  - Enhanced error reporting with structured feedback

### Features
- **State Management** - Desired state comparison and idempotency
- **Inheritance System** - Folder attribute inheritance with source tracking
- **Cluster Support** - Multi-node cluster host configurations with proper agent settings
- **Validation Pipeline** - Comprehensive pre-deployment checks (hostname, IP, folder existence)
- **Change Detection** - Granular change tracking (added/modified/removed attributes)

### Technical Improvements
- Enhanced error handling with specific CheckMK API error mapping
- Improved type hints and documentation with enhanced structure
- Modular validation helpers for reusable checks
- Structured response formats for better user feedback

## [0.3.1] - 2025-08-21

### Added
- **Complete Time Period Management System** - Create, list, update, and delete CheckMK time periods
  - `vibemk_get_timeperiods` - List all configured time periods with active ranges
  - `vibemk_create_timeperiod` - Create new time periods with weekly schedules
  - `vibemk_update_timeperiod` - Modify existing time period configurations
  - `vibemk_delete_timeperiod` - Remove time periods from CheckMK

### Features
- Support for complex weekly schedules (Monday-Friday 8-17 format)
- Proper CheckMK API format with day/time_ranges structure
- Validation for time range data integrity
- Enhanced display formatting for time period schedules
- Integration with CheckMK configuration activation workflow

### Semantic Versioning
- Adopted semantic versioning third digit for smaller feature releases
- Consistent version management across __init__.py and pyproject.toml

## Previous Releases

### [0.3.0] - 2025-08-21
- **Complete Downtime Management System** - Schedule, list, and delete CheckMK downtimes
  - `vibemk_schedule_host_downtime` - Schedule host maintenance windows
  - `vibemk_schedule_service_downtime` - Schedule service maintenance windows  
  - `vibemk_list_downtimes` - View all downtimes with detailed information
  - `vibemk_get_active_downtimes` - Filter currently active downtimes
  - `vibemk_delete_downtime` - Remove downtimes by ID or patterns
- **Downtime Features** - Duplicate prevention, UTC timestamp handling, flexible duration parsing

### [0.2.0] - 2025-08-21
- **Performance Metrics System** - Complete metrics retrieval and analysis with REST API
  - Fixed deprecated webapi.py → domain-types/metric/actions/get/invoke endpoint
  - Datetime string timestamps (not Unix timestamps)
  - Handle metrics list response structure with data_points
  - Verified working with all 4 HTTPS Webservice metrics
- **Host/Service Status Monitoring** - Live monitoring data with hard state support
- **Folder Management** - CheckMK folder operations with proper API format
- **Ruleset Management** - Rule creation/retrieval with Python string literal support

### [0.1.0] - 2025-08-20
- **Initial MCP Server Implementation** - Basic CheckMK integration
- **Automated Development Tools** - Pre-push hooks and formatting automation
- **CI/CD Pipeline** - GitHub Actions with comprehensive quality checks
- **Code Quality Standards** - Black, isort, mypy integration
- **Authentication System** - Automation user support
- **Core API Client** - HTTP client with proper error handling
- **Tool Registration** - vibemk_ namespace for all tools