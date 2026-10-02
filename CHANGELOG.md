# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Fixed
- Active checks can be created with their options on CheckMK 2.5: thresholds,
  certificate lifetimes, passwords and host choices of the HTTP, TCP, ICMP,
  SMTP, LDAP, SMB and Event Console checks were refused
- FTP checks no longer offer a passive mode, which CheckMK does not have
- Event Console events can be acknowledged, changed and deleted again
- The agent download link points at the right address; the baking status
  shows the actual state, and Raw/Community says it has no agent bakery
- The bulk discovery status shows the job's state and per-host results
- A service group's alias is shown

## [0.6.3] - 2026-10-03

### Added
- Upgrade guide for source installations older than 0.5 (INSTALL.md → Upgrading)

### Changed
- Started with a Python older than 3.10 or without its dependencies, `main.py`
  says what to do instead of failing with a traceback

## [0.6.2] - 2026-10-03

### Added
- Listed in the official MCP Registry as `io.github.chexma/vibemk`
- Installation with `pipx`, `uv tool install` or `uvx` documented

### Changed
- The MCP SDK is held below 3.0 so an untested major version cannot break a fresh install

## [0.6.1] - 2026-10-03

### Added
- vibeMK is published on PyPI: `pip install vibemk`

## [0.6.0] - 2026-10-02

### Changed
- vibeMK installs as a single `vibemk` package and no longer adds `api`,
  `config`, `handlers` and `utils` to the Python environment, where they could
  clash with other packages. `python main.py` from a checkout keeps working

### Added
- Read-only mode: `--read-only` or `VIBEMK_READ_ONLY=1` offers only the tools
  that read and refuses every write
- Tool arguments are checked against each tool's schema; a missing or wrong
  argument is answered with every problem at once instead of reaching CheckMK
- An argument a tool does not know (such as `hostname` for `host_name`) is
  named and refused instead of being silently ignored
- Downtime scheduling takes a `force` option to add a downtime even when one
  with the same comment exists

### Security
- `vibemk_test_direct_url` only requests URLs under the configured CheckMK API
  and no longer follows redirects; it could send the CheckMK credentials to any
  address
- Host names, rule ids and other values are encoded in API paths, so a crafted
  value can no longer address a different object

### Fixed
- The `vibemk` command works after `pip install`; it previously exited
  without starting the server
- An installed vibeMK no longer places `examples`, `tmp` and stale build
  output into the Python environment
- The full GNU GPL v3 text is included; the file was previously abridged
- Over HTTP, a slow tool call no longer holds up other sessions
- Listing or deleting active checks across all types is faster
- The active check, Event Console, auxiliary tag and service parameter tools
  describe themselves and answer in English throughout
- Listing process rules no longer executes the rule values CheckMK returns
- `wait_for_discovery` waits for the job to finish instead of failing with a
  redirect error, and `start_service_discovery` no longer falls back to bulk
  discovery or starts a second job while one is running
- `start_service_discovery` accepts the `tabula_rasa` and
  `only_service_labels` modes it offered, and asks for confirmation since it
  can remove services
- `get_pending_changes` shows what changed and by whom instead of "Unknown"
- Host status shows "Never" for a state that has not changed yet, instead of
  a time 56 years ago
- `recur` on downtimes takes effect (commercial editions); it was accepted but
  never sent, and offered a `month` value CheckMK does not have
- `create_smtp_check` applies the `port` it reports; it was never sent
- `activate_changes: true` takes effect on every write tool that offers it; on
  34 of them (rules, folders, groups, passwords, tags, time periods, roles,
  contact groups) it was ignored and the changes stayed pending

## [0.5.1] - 2026-10-02

### Fixed
- `activate_changes` works again on host, service parameter, active check and
  auxiliary tag writes; it raised an internal error instead of activating
- Custom graph and metric search results render again instead of raising an
  internal error
- Metric search works: it now takes the `graph_id` or `metric_id` CheckMK
  requires, instead of always answering HTTP 400
- A metric's latest value skips a still-empty final bucket instead of
  reporting "None"

### Changed
- Checkmk 2.5 is listed as supported; 2.2 and older are not

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