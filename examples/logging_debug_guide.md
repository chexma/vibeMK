# vibeMK MCP Server - Logging & Debugging Guide

## Overview
The vibeMK MCP server now supports comprehensive logging for debugging connection issues and server problems. This feature is especially useful when the server doesn't start or connect properly with Claude Desktop.

## How to Enable File Logging

### 1. Add LOGFILE to your claude_desktop_config.json

Add the `LOGFILE` environment variable to your MCP server configuration:

```json
{
  "mcpServers": {
    "vibeMK": {
      "command": "python3",
      "args": ["/path/to/vibeMK/main.py"],
      "env": {
        "CHECKMK_SERVER_URL": "http://localhost:8080",
        "CHECKMK_SITE": "cmk", 
        "CHECKMK_USERNAME": "automation",
        "CHECKMK_PASSWORD": "your_password_here",
        "LOGFILE": "/Users/youruser/Desktop/vibemk_debug.log"
      }
    }
  }
}
```

### 2. Logging Behavior

- **Without LOGFILE**: Only console logging to stderr (INFO level)
- **With LOGFILE**: Both console AND file logging (DEBUG level for detailed analysis)

The log file will include:
- Server startup and shutdown events
- MCP protocol communication (initialize, tools/list, tools/call)
- CheckMK connection initialization attempts
- Detailed error messages with stack traces
- All request/response flows

## Understanding Log Output

### Normal Startup Sequence
```
2025-08-23 13:24:33,908 - vibeMK.logging - INFO - File logging enabled: /path/to/logfile.log
2025-08-23 13:24:33,908 - mcp.server - INFO - Starting vibeMK Server 0.3.8
2025-08-23 13:24:33,908 - mcp.server - INFO - CheckMK connection will be initialized on first tool call
2025-08-23 13:24:33,908 - mcp.server - INFO - Server ready to accept MCP requests on stdin
```

### MCP Protocol Communication
```
2025-08-23 13:24:33,908 - mcp.server - DEBUG - Received request: {"jsonrpc": "2.0", "id": "test", "method": "initialize"...
2025-08-23 13:24:33,908 - mcp.server - INFO - Initialize request received from client, ID: test
2025-08-23 13:24:33,908 - mcp.server - INFO - Protocol version negotiation: client=2024-11-05, server=2024-11-05
```

### CheckMK Connection Issues
```
2025-08-23 13:24:33,908 - mcp.server - INFO - Initializing CheckMK connection for first tool call...
2025-08-23 13:24:33,908 - mcp.server - INFO - CheckMK config loaded: http://localhost:8080 site=cmk user=automation
2025-08-23 13:24:33,908 - mcp.server - ERROR - Failed to initialize CheckMK connection: Connection refused
2025-08-23 13:24:33,908 - mcp.server - ERROR - This is usually due to missing environment variables or unreachable CheckMK server
```

## Troubleshooting Common Issues

### 1. Server Not Starting

**Check the log for:**
- Missing `LOGFILE` entry means the feature is working, but not enabled
- Python import errors or missing dependencies
- Permission issues with the log file directory

### 2. CheckMK Connection Problems

**Look for these error patterns:**
```
Failed to initialize CheckMK connection: Connection refused
→ CheckMK server is not running or wrong URL

Failed to initialize CheckMK connection: 401 Unauthorized  
→ Wrong username/password

Failed to initialize CheckMK connection: 404 Not Found
→ Wrong site name or URL path
```

### 3. MCP Protocol Issues

**Normal flow should show:**
1. `initialize` request received
2. Protocol version negotiation
3. Server waiting for further requests

**Missing steps indicate:**
- Claude Desktop configuration problems
- Network connectivity issues
- Protocol version mismatches

## Log File Locations

### Recommended Locations

**macOS:**
```
/Users/youruser/Desktop/vibemk_debug.log
/Users/youruser/Documents/vibemk_debug.log
```

**Linux:**
```
/tmp/vibemk_debug.log  
/home/youruser/vibemk_debug.log
```

**Windows:**
```
C:\Users\youruser\Desktop\vibemk_debug.log
C:\temp\vibemk_debug.log
```

### Important Notes

- The log directory must exist (the server will create it if needed)
- The user running Claude Desktop must have write permissions
- Log files are appended to (not overwritten) for session continuity
- Large log files should be rotated or cleaned up periodically

## Testing the Logging Setup

You can test the logging configuration manually:

```bash
# Set the LOGFILE environment variable
export LOGFILE="/tmp/vibemk_test.log"

# Test with a sample MCP initialize request
echo '{"jsonrpc": "2.0", "id": "test", "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}' | python3 main.py

# Check the log file content
cat /tmp/vibemk_test.log
```

This should show detailed server startup and request handling logs in both the console and the log file.

## Next Steps for Debugging

1. **Enable logging** by adding `LOGFILE` to your configuration
2. **Restart Claude Desktop** to pick up the new configuration
3. **Attempt to use vibeMK** to trigger connection attempts
4. **Check the log file** for detailed error information
5. **Share relevant log sections** when reporting issues

The detailed logging will help identify whether the issue is:
- MCP protocol communication problems
- CheckMK server connectivity issues  
- Configuration or environment problems
- Python/dependency related errors