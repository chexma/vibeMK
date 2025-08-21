# vibeMK - Claude Development Notes

## Project Overview
CheckMK MCP Server implementation for integrating CheckMK monitoring with LLM interfaces.

## Environment Setup
- **CheckMK Instance:** http://localhost:8080/cmk/check_mk/
- **Site:** cmk
- **Automation User:** automation / Passw0rdPassw0rd
- **API Base:** http://localhost:8080/cmk/check_mk/api/1.0/

## Fixed Issues

### 1. Folder Operations (SOLVED ✅)
**Problem:** HTTP 400 errors when creating/deleting folders

**Root Cause:** Incorrect API data format
- Wrong: `{"folder": "name", "parent": "/"}`
- Correct: `{"name": "name", "parent": "~", "attributes": {}}`

**Solution:** Updated `/handlers/folders.py:69-231`
- Use `name` instead of `folder` field
- Use `~` instead of `/` for root folder
- Add required `attributes: {}` field
- Proper path encoding: `/api` → `~api`

### 2. Ruleset API Format (SOLVED ✅)
**Problem:** HTTP 400 errors when creating rules due to format issues

**Root Cause:** CheckMK expects Python string literals for `value_raw`
- Wrong: `"value_raw": ["admins"]` (JSON array)
- Correct: `"value_raw": "'admins'"` (Python string literal)

**Working Format Example:**
```json
{
  "properties": {"disabled": false},
  "value_raw": "'admins'",
  "conditions": {},
  "ruleset": "host_contactgroups",
  "folder": "~"
}
```

**Solution:** Updated `/handlers/rules.py:109-128` and `/handlers/host_group_rules.py:117-195`

### 3. Rule Retrieval Issue (SOLVED ✅)
**Problem:** Rule queries returned 0 rules instead of actual count

**Root Cause:** Wrong API endpoint
- Wrong: `GET objects/ruleset/{name}` (metadata only)
- Correct: `GET domain-types/rule/collections/all?ruleset_name={name}` (actual rules)

**Solution:** Updated `/handlers/rules.py:73-133`

### 4. Host Status Issue (SOLVED ✅)
**Problem:** Host status showing incorrect state - DOWN hosts showing as UP

**Root Cause:** Using soft state instead of hard state for monitoring status
- Wrong: Using only `state` column which shows soft state
- Correct: `GET objects/host/{name}?columns=state,hard_state,state_type,plugin_output,last_check,last_state_change`
- **Key Fix**: Use `hard_state` when `state_type=1` for accurate current monitoring status

**Working API Example:**
```bash
GET /cmk/check_mk/api/1.0/objects/host/myshinyserver?columns=state&columns=hard_state&columns=state_type&columns=plugin_output&columns=last_check
# Returns: state=1, hard_state=1, state_type=1 -> Use hard_state=1 (DOWN)
```

**Solution:** Updated `/handlers/hosts.py:73-268`
- Uses documented CheckMK API with columns parameter including hard_state and state_type
- **Critical Fix**: Uses hard_state instead of soft state when state_type=1 for accurate monitoring status
- Maps numeric state codes (0=UP, 1=DOWN, 2=UNREACHABLE)
- Proper timestamp formatting and error handling
- Fallback methods for edge cases

### 5. Service Status Issue (SOLVED ✅)
**Problem:** Service status showing "unknown" instead of actual state

**Root Cause:** REST API configuration endpoints don't include live monitoring data
- Wrong: Using configuration endpoints
- Correct: `GET objects/host/{host}/actions/show_service/invoke?service_description={service}`

**Solution:** Updated `/handlers/services.py` (previously documented)
- Uses show_service action with query parameters
- Maps numeric state codes (0=OK, 1=WARNING, 2=CRITICAL, 3=UNKNOWN)

## Key Technical Insights

### CheckMK API Patterns
1. **Folder Paths:** Use tilde notation (`~` for root, `~folder~subfolder`)
2. **Rule Values:** Must be Python string literals (`'value'` not `"value"`)
3. **Authentication:** Basic Auth with automation user
4. **Headers:** Always include `Accept: application/json`

### Ruleset Format Requirements
- **Single values:** `'admin'` (quoted string)
- **Multiple values:** `['admin1', 'admin2']` (Python list string)
- **Dict values:** `{'key': 'value'}` (Python dict string)

### Working Endpoints
```
✅ Folders: POST domain-types/folder_config/collections/all
✅ Rules: POST domain-types/rule/collections/all  
✅ Rule Query: GET domain-types/rule/collections/all?ruleset_name=X
✅ Host Status: GET objects/host/{name}?columns=state,plugin_output,last_check
✅ Service Status: GET objects/host/{host}/actions/show_service/invoke?service_description={service}
✅ Service Collections: GET objects/host/{host}/collections/services?columns=state,hard_state,state_type,plugin_output
✅ Performance Metrics: POST domain-types/metric/actions/get/invoke (with Unix timestamps)
❌ Avoid: GET objects/ruleset/{name} (metadata only)
❌ Avoid: webapi.py endpoints (deprecated in newer CheckMK versions)
```

### 6. Performance Metrics Implementation (SOLVED ✅)
**Problem:** Performance metrics retrieval was not working due to incorrect API endpoint usage

**Root Cause:** 
- Wrong API endpoints being used (webapi.py is deprecated)
- Incorrect timestamp format for time_range parameter
- Missing Unix timestamp conversion

**Working API Endpoint:**
```
POST /cmk/check_mk/api/1.0/domain-types/metric/actions/get/invoke
```

**Correct Format:**
```json
{
    "time_range": {
        "start": 1724234567,  // Unix timestamp
        "end": 1724238167     // Unix timestamp  
    },
    "reduce": "max",
    "site": "cmk",
    "host_name": "www.google.de",
    "service_description": "HTTPS Webservice",
    "type": "single_metric",
    "metric_id": "response_time"
}
```

**Solution:** Updated `/handlers/metrics.py:37-474`
- Fixed `_parse_time_range()` to return Unix timestamps instead of datetime strings
- Updated service metrics to use correct REST API endpoint with proper format
- Added automatic metric discovery - shows available metrics when no metric_name specified
- Added comprehensive error handling with helpful metric suggestions
- Improved response formatting with detailed statistics (min/max/avg values)

**Key Features:**
- **Service Metrics:** `vibemk_get_service_metrics` - Shows available metrics or retrieves specific metric data
- **Host Metrics:** `vibemk_get_host_metrics` - Lists common host metric IDs and retrieves data
- **Metric Discovery:** Automatically shows available performance metrics for services
- **Time Ranges:** Supports 1h, 4h, 24h, 7d, 30d time periods
- **Data Analysis:** Shows latest value, min/max/avg statistics, and data point counts

## Current Status
- ✅ Folder creation/deletion working
- ✅ Rule creation working with correct format
- ✅ Rule retrieval showing actual rules (3/3 for host_contactgroups)
- ✅ Host status showing correct state (UP/DOWN/UNREACHABLE) with live data
- ✅ Service status showing correct state (OK/WARNING/CRITICAL/UNKNOWN) with live data (verified with hard states)
- ✅ Performance metrics retrieval working with automatic metric discovery and detailed analysis
- ✅ Tool routing optimized for direct access
- ✅ All 82 tools renamed with vibemk_ prefix for namespace separation

## Test Commands
```bash
# Test folder operations
CHECKMK_SERVER_URL="http://localhost:8080" CHECKMK_SITE="cmk" CHECKMK_USERNAME="automation" CHECKMK_PASSWORD="Passw0rdPassw0rd" python3 -c "from handlers.folders import FolderHandler; ..."

# Test rule operations  
CHECKMK_SERVER_URL="http://localhost:8080" CHECKMK_SITE="cmk" CHECKMK_USERNAME="automation" CHECKMK_PASSWORD="Passw0rdPassw0rd" python3 -c "from handlers.rules import RulesHandler; ..."
```

## Next Steps
- [ ] Test rule creation with existing contact groups
- [ ] Implement format detection for remaining ~2000 rulesets
- [ ] Add comprehensive error handling

## Documentation Standards

### Language Policy
- **All documentation must be written in English only**
- This ensures international accessibility and consistency
- Apply this to:
  - All README files
  - Installation guides
  - Code comments
  - Error messages
  - Configuration examples
  - User-facing text

### Code Standards
- Use English for all variable names, function names, and class names
- Write all comments in English
- Use English in all user-facing strings and error messages

---
*Generated during Claude collaboration - Contains sensitive testing information*