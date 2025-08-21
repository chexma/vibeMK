# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Complete Downtime Management System** - Full CheckMK downtime lifecycle management
  - `vibemk_schedule_host_downtime` - Schedule maintenance windows for hosts
  - `vibemk_schedule_service_downtime` - Schedule maintenance windows for specific services
  - `vibemk_list_downtimes` - View all active and scheduled downtimes with detailed information
  - `vibemk_get_active_downtimes` - Filter and display only currently active downtimes
  - `vibemk_delete_downtime` - Remove downtimes by ID or query-based patterns

### Features
- **Intelligent Duplicate Prevention** - Automatically checks for existing downtimes before creation
- **Force Parameter Support** - Override duplicate checking when needed
- **UTC Timestamp Handling** - Proper timezone management following CheckMK patterns
- **Query-Based Deletion** - Advanced filtering for bulk downtime management using comment patterns
- **Comprehensive Error Handling** - Robust error management with detailed feedback
- **Flexible Duration Parsing** - Support for human-readable time formats (1h, 90m, 2h30m)
- **Host and Service Support** - Full support for both host-level and service-specific downtimes

### Technical Implementation
- **handlers/downtimes.py** - Complete downtime handler implementation
  - UTC timestamp handling with `datetime.utcnow()` pattern
  - CheckMK API integration with proper authentication
  - Query-based filtering using CheckMK's JSON query syntax
  - Timestamp format compatibility (ISO strings and Unix timestamps)
- **MCP Integration** - All downtime tools registered with vibemk_ namespace
- **Production Ready** - Intensive testing completed with host "downtimehost" and "Check_MK" service

### API Endpoints Used
- `POST /cmk/check_mk/api/1.0/domain-types/downtime/collections/host` - Host downtime creation
- `POST /cmk/check_mk/api/1.0/domain-types/downtime/collections/service` - Service downtime creation
- `GET /cmk/check_mk/api/1.0/domain-types/downtime/collections/all` - Downtime retrieval
- `POST /cmk/check_mk/api/1.0/domain-types/downtime/actions/delete/invoke` - Downtime deletion

### Key Fixes
- **Timestamp Format Handling** - Fixed compatibility between ISO strings and Unix timestamps
- **Deletion Parameter Requirements** - Added required `host_name` parameter for comment-pattern deletion
- **Active Downtime Filtering** - Resolved timestamp calculation errors in remaining time display

## Previous Releases

### [0.3.0] - 2025-08-21
- **Performance Metrics System** - Complete metrics retrieval and analysis
- **Host/Service Status Monitoring** - Live monitoring data with hard state support
- **Folder Management** - CheckMK folder operations with proper API format
- **Ruleset Management** - Rule creation/retrieval with Python string literal support

### [0.2.0] - 2025-08-20
- **Automated Development Tools** - Pre-push hooks and formatting automation
- **CI/CD Pipeline** - GitHub Actions with comprehensive quality checks
- **Code Quality Standards** - Black, isort, mypy integration

### [0.1.0] - 2025-08-19
- **Initial MCP Server Implementation** - Basic CheckMK integration
- **Authentication System** - Automation user support
- **Core API Client** - HTTP client with proper error handling
- **Tool Registration** - vibemk_ namespace for all tools