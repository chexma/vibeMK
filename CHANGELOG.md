# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Complete Downtime Management System** - Schedule, list, and delete CheckMK downtimes
  - `vibemk_schedule_host_downtime` - Schedule host maintenance windows
  - `vibemk_schedule_service_downtime` - Schedule service maintenance windows  
  - `vibemk_list_downtimes` - View all downtimes with detailed information
  - `vibemk_get_active_downtimes` - Filter currently active downtimes
  - `vibemk_delete_downtime` - Remove downtimes by ID or patterns

### Features
- Duplicate prevention with force override option
- UTC timestamp handling and flexible duration parsing (1h, 90m, 2h30m)
- Query-based deletion with comment pattern matching
- Support for both host and service downtimes

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