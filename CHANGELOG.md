# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Fixed
- `activate_changes` works again on host, service parameter, active check and
  auxiliary tag writes; it raised an internal error instead of activating
- Custom graph and metric search results render again instead of failing

## [0.5.0] - 2026-10-02

### Added
- Host centrally: `--transport http` serves Streamable HTTP, so clients need
  neither Python nor a checkout. Requires a bearer token (`VIBEMK_HTTP_TOKEN`)
- Tools now say what they do before they run — read-only, writing or
  destructive — so a client knows what to confirm
- Notification rule management: list, show, create, update and delete
- Service params, agent bakery, active checks, audit log, aux tags, event
  console and site management
- Host status, host lists and pending changes also return machine-readable data

### Changed
- MCP is served through the official SDK: a current protocol revision is
  negotiated, and a failing tool now reports a failure the model can act on
- Requires Python 3.10 or newer, and one dependency (the MCP SDK)
- A server URL without `http://` or `https://` now assumes HTTPS
- Error messages include CheckMK's own explanation, not just the HTTP status
- Discovery offers all seven modes CheckMK documents

### Fixed
- Deleting one downtime no longer deletes others on the same host
- Acknowledgement lists show acknowledgements, not similar-looking comments
- Bulk discovery no longer removes services unless asked to
- A failed write is no longer retried, so it cannot take effect twice
- Concurrent edits are detected again: writes send the object's real ETag
- Acknowledgement tools are reachable (they were built but never offered)
- CheckMK 2.4 and 2.5 compatibility for monitoring data and host listings

### Removed
- Three tools whose CheckMK endpoints do not exist: `vibemk_reschedule_check`,
  `vibemk_discover_services` (use `vibemk_start_service_discovery`) and
  `vibemk_test_notification`

## [0.3.10] - 2025-08-23
### Added
- Enhanced Host Attribute Updates for ipaddress, alias and tags

## [0.3.9] - 2025-08-23
### Changed  
- Version increment

## [0.3.6] - 2025-08-23
### Fixed
- User roles management now works correctly across CheckMK 2.3 and 2.4

## [0.3.5] - 2025-08-23  
### Fixed
- Problem acknowledgements now work correctly across CheckMK 2.3 and 2.4
- Automatic version detection for better compatibility

## [0.3.3] - 2025-08-22
### Added
- Service group management - create, list, update, and delete service groups
- Bulk operations for managing multiple service groups at once

## [0.3.2] - 2025-08-22
### Added
- Advanced host management - validate configs, compare states, create cluster hosts
- Enhanced host updates with merge, overwrite, and remove modes

## [0.3.1] - 2025-08-21
### Added  
- Time period management - create and manage notification schedules
- Support for complex weekly schedules (e.g., Monday-Friday 8-17)

## [0.3.0] - 2025-08-21
### Added
- Complete downtime management - schedule, list, and delete maintenance windows
- Flexible duration parsing (e.g., "2h", "1h30m")

## [0.2.0] - 2025-08-21
### Added
- Performance metrics retrieval and analysis
- Live host and service status monitoring  
- Folder management for organizing hosts
- Rule creation and management

## [0.1.0] - 2025-08-20
### Added
- Initial CheckMK integration with MCP server
- Basic monitoring tools and authentication