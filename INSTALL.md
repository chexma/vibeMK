# vibeMK - Installation Guide

A step-by-step guide for installing and configuring vibeMK for LLM interfaces.

## 📋 Prerequisites

### System Requirements

- **Operating System**: macOS, Linux, or Windows
- **Python**: Version 3.8 or higher
- **CheckMK**: Version 2.1.0 or higher (CE/CEE/CCE/CRE)
- **LLM Client**: E.g., Claude Desktop, OpenAI API Client, etc.

### CheckMK Requirements

⚠️ **IMPORTANT**: You need **Administrator access** to your CheckMK instance to:
- Create an automation user with Administrator role
- Set up API access
- Configure all vibeMK functions properly

### Software Dependencies

- Python Virtual Environment Support
- Git (for repository cloning)
- Access to CheckMK instance (local or remote)

## 🚀 vibeMK Features (Version 0.1)

### ✨ Current Features
- **🏷️ Unified Tool Naming**: All 82 tools with `vibemk_` prefix for better identification
- **🔧 Modular Architecture**: Clean handler structure for different CheckMK areas
- **⚡ Optimized Performance**: Efficient API clients and connection management
- **🛡️ Robust Security**: Comprehensive input validation and error handling
- **🧪 Zero Dependencies**: Uses exclusively Python standard library

### 📊 Tool Overview (82 Tools)
- **CheckMK Core**: `vibemk_get_checkmk_version`, `vibemk_debug_checkmk_connection`
- **Host Management**: `vibemk_get_checkmk_hosts`, `vibemk_create_host`, `vibemk_delete_host`
- **Service Management**: `vibemk_get_checkmk_services`, `vibemk_discover_services`
- **Monitoring & Alerting**: `vibemk_get_current_problems`, `vibemk_acknowledge_problem`
- **Folder Management**: `vibemk_get_folders`, `vibemk_create_folder`
- **Rule Management**: `vibemk_get_rulesets`, `vibemk_create_rule`
- **User & Contact Management**: `vibemk_get_users`, `vibemk_create_contact_group`
- **Group Management**: `vibemk_get_host_groups`, `vibemk_create_host_group`
- **Configuration Management**: `vibemk_activate_changes`, `vibemk_get_pending_changes`
- **Metrics & Performance**: `vibemk_get_host_metrics`, `vibemk_get_service_metrics`
- **Password Management**: `vibemk_get_passwords`, `vibemk_create_password`
- **Time Period Management**: `vibemk_get_timeperiods`, `vibemk_create_timeperiod`
- **Debug & Diagnostics**: `vibemk_debug_api_endpoints`, `vibemk_test_all_endpoints`

## 🔧 Step 1: Repository Setup

### Clone Repository

```bash
# Clone repository
git clone https://github.com/chexma/vibeMK.git
cd vibeMK

# Or: Download ZIP and extract
# wget https://github.com/.../archive/main.zip
# unzip main.zip && cd vibeMK-main
```


## 📦 Step 2: Verify Dependencies

### ⚡ Zero Dependencies Required

vibeMK uses **only Python standard library** - no external packages needed!

```bash
# Verify all required modules are available
python -c "import json, urllib.request, asyncio; print('✅ All dependencies available')"
```

**Optional: Development Dependencies (only for contributors)**

```bash
# Only needed for development/testing
pip install -e ".[dev]"  # Installs pytest, black, mypy, etc.
```

## ⚙️ Step 3: Configure CheckMK

### 3.1 Create CheckMK API User

1. **Open CheckMK Web Interface**:
   ```
   http://your-checkmk-server/cmk/
   ```

2. **Create Automation User**:
   ```
   Setup → Users → Add user
   
   Settings:
   - Username: automation  
   - Full name: vibeMK MCP Automation
   - Email: (optional)
   - Role: Administrator ✅ (IMPORTANT: Not just "Automation user"!)
   - Disable password login: ✅
   ```

   ⚠️ **Important**: The user must have **Administrator role** to access all CheckMK functions like:
   - Creating/deleting hosts and services
   - Managing folders and rules
   - Activating configuration changes
   - Accessing all monitoring data

3. **Generate API Key**:
   ```
   Edit user → Automation secrets → Add secret
   
   - Description: "vibeMK LLM Server"
   - Copy the generated key ➡️ Important for LLM config!
   ```

### 3.2 Check User Permissions

```
Setup → Users → [automation user] → Effective permissions

Required permissions (Administrator role provides all of these):
✅ Use the REST API
✅ See hosts in monitoring  
✅ See services in monitoring
✅ See folder structure
✅ Configure rules and parameters
✅ Activate configuration changes
✅ Create and delete hosts
✅ Manage user accounts and contact groups
✅ Access BI (Business Intelligence) - Enterprise Edition
✅ Agent Bakery access - Enterprise Edition
```

## 🔐 Step 4: LLM Client Configuration

### 4.1 Important Note

✅ **No .env file needed!** Credentials are stored directly in the LLM client config.

## 🔎 Step 5: Setup vibeMK in LLM Client

### 5.1 Find Configuration File

```bash
# macOS: Open config file
open -e ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Or with other editor:
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows**:
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Linux**:
```
~/.config/claude/claude_desktop_config.json
```

### 5.2 Determine Absolute Paths

```bash
# Current directory  
CURRENT_DIR=$(pwd)
echo "Server Path: $CURRENT_DIR/main.py"

# Python path
echo "Python Path: $(which python3)"
```

### 5.3 Register MCP Server

**Basic Configuration:**
```json
{
  "mcpServers": {
    "vibemk": {
      "command": "python3",
      "args": ["/Users/andre/data/Entwicklung/claude/vibeMK/main.py"],
      "env": {
        "CHECKMK_SERVER_URL": "http://localhost:8080",
        "CHECKMK_SITE": "cmk",
        "CHECKMK_USERNAME": "automation",
        "CHECKMK_PASSWORD": "Your_real_API_key_here"
      }
    }
  }
}
```

**Advanced Configuration:**
```json
{
  "mcpServers": {
    "vibemk": {
      "command": "python3",
      "args": ["/absolute/path/to/vibeMK/main.py"],
      "env": {
        "CHECKMK_SERVER_URL": "https://checkmk.example.com",
        "CHECKMK_SITE": "mysite",
        "CHECKMK_USERNAME": "automation",
        "CHECKMK_PASSWORD": "cmk_api_key_here",
        "CHECKMK_VERIFY_SSL": "true",
        "CHECKMK_TIMEOUT": "30",
        "CHECKMK_MAX_RETRIES": "3"
      }
    }
  }
}
```

⚠️ **Important**: 
- Use absolute paths for main.py!
- Insert real API key!
- Use `python3` command (no virtual environment needed)

## 🧪 Step 6: Test Installation

### 6.1 Basic Connection Test

```bash
# Is CheckMK server reachable?
curl -s http://localhost:8080/cmk/ | grep -i checkmk

# Test API endpoint  
curl -H "Authorization: Bearer automation YOUR_API_KEY" \
     -H "Accept: application/json" \
     http://localhost:8080/cmk/check_mk/api/1.0/version
```

### 6.2 Test vibeMK Server

```bash
# Start server (test mode)
CHECKMK_SERVER_URL="http://localhost:8080" \
CHECKMK_SITE="cmk" \
CHECKMK_USERNAME="automation" \
CHECKMK_PASSWORD="your_api_key" \
python main.py
```

**Send test request:**
```bash
# In another terminal:
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | \
CHECKMK_SERVER_URL="http://localhost:8080" \
CHECKMK_SITE="cmk" \
CHECKMK_USERNAME="automation" \
CHECKMK_PASSWORD="your_api_key" \
python main.py
```

**Expected output:**
```json
{
  "jsonrpc": "2.0", 
  "id": 1,
  "result": {
    "tools": [
      {"name": "vibemk_debug_checkmk_connection", ...},
      {"name": "vibemk_get_checkmk_version", ...},
      ...
    ]
  }
}
```

## 🖥️ Step 7: LLM Client Integration

### 7.1 Quit LLM Client

```bash
# macOS: Completely quit Claude
osascript -e 'quit app "Claude"'

# or manually: Press Cmd+Q
```

### 7.2 Restart LLM Client

```bash
# macOS: Start Claude again
open -a Claude

# Wait for startup (approx. 5-10 seconds)
```

### 7.3 Verify vibeMK Integration

**Test Questions for Claude**:

1. **Tools available?**
   ```
   "Which vibeMK tools do you have available?"
   ```

2. **Test connection**:
   ```  
   "Use vibemk_debug_checkmk_connection to test the connection"
   ```

3. **Get version**:
   ```
   "Show me the CheckMK version with vibemk_get_checkmk_version"
   ```

4. **Show hosts**:
   ```
   "List all CheckMK hosts with vibemk_get_checkmk_hosts"
   ```

## 🐛 Step 8: Troubleshooting

### 8.1 Common Issues

| Problem | Symptom | Solution |
|---------|---------|----------|
| "No vibemk tools available" | Claude doesn't know vibemk_* tools | Check config paths, restart Claude |
| "Connection failed" | API connection failed | Check server URL and port |
| "Authentication failed" | 401 Unauthorized | Check API key and username |
| "Permission denied" | 403 Forbidden | Check user permissions in CheckMK |
| "Python not found" | Server won't start | Check python3 installation |
| "Module not found" | Import error | Verify Python 3.8+ installation |

### 8.2 Enable Debug Logs

**Monitor MCP logs** (macOS):
```bash
# Monitor log file
tail -f ~/Library/Logs/Claude/mcp.log

# All Claude logs
ls -la ~/Library/Logs/Claude/
```

**Server debug mode**:
```bash
# Enable debug-level logging
export CHECKMK_DEBUG=true
export CHECKMK_SERVER_URL="http://localhost:8080"
export CHECKMK_SITE="cmk"  
export CHECKMK_USERNAME="automation"
export CHECKMK_PASSWORD="your_api_key"

python main.py 2>&1 | tee vibemk-debug.log
```

### 8.3 Connection Diagnostics

```bash
# Step-by-step diagnosis

# 1. Check Python environment
which python
python --version
python -c "import json, urllib.request, asyncio; print('✅ Modules OK')"

# 2. Is CheckMK server reachable?
curl -v http://localhost:8080/cmk/

# 3. Is API endpoint available?
curl -v -H "Authorization: Bearer automation YOUR_KEY" \
        http://localhost:8080/cmk/check_mk/api/1.0/version

# 4. Can vibeMK server start?
timeout 10s python main.py

# 5. Is LLM client config valid?
python -m json.tool ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### 8.4 Check Tool Availability

```bash
# Show all available tools
python -c "
from mcp.tools import get_all_tools
tools = get_all_tools()
print(f'Total tools: {len(tools)}')
for tool in tools[:5]:
    print(f'- {tool[\"name\"]}: {tool[\"description\"][:50]}...')
"
```

### 8.5 Reset Configuration

```bash
# 1. Quit LLM client
osascript -e 'quit app "Claude"'

# 2. Backup MCP config
cp ~/Library/Application\ Support/Claude/claude_desktop_config.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json.backup

# 3. Create minimal config
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {}
}
EOF

# 4. Restart Claude and add servers step by step
```

## ✅ Step 9: Verify Installation

### 9.1 Success Criteria

- ✅ CheckMK API responds to version request
- ✅ vibeMK server starts without errors  
- ✅ LLM client recognizes all 82 vibemk_* tools
- ✅ Connection diagnostics successful
- ✅ Host and service data retrievable

### 9.2 Test Sequence

```
1. "vibemk_debug_checkmk_connection" → "✅ Connection successful" 
2. "vibemk_get_checkmk_version" → CheckMK version information
3. "vibemk_get_checkmk_hosts" → List of configured hosts
4. "vibemk_get_checkmk_services" → Service overview
5. "vibemk_get_folders" → Folder structure
```

### 9.3 Performance Test

```
"vibemk_test_all_endpoints" → All API endpoints successfully tested
```

### 9.4 Tool Category Test

Test different tool categories:

- **Host Management**: `vibemk_get_host_status`
- **Monitoring**: `vibemk_get_current_problems` 
- **Configuration**: `vibemk_get_pending_changes`
- **Rules**: `vibemk_get_rulesets`
- **Groups**: `vibemk_get_host_groups`

## 🚀 Step 10: Production Use

### 10.1 Use vibeMK Optimally

**Use natural language:**
```
"Show me all hosts with problems"
"Create a new host group named 'Webservers'" 
"Activate all pending changes"
"Which services on host 'server01' have problems?"
```

**Advanced operations:**
```
"Create a host in folder 'production' with IP 192.168.1.100"
"Schedule maintenance for all web servers from today 22:00 to tomorrow 06:00"
"Show me performance metrics for host 'database01'"
```

### 10.2 Setup Autostart (optional)

**macOS LaunchAgent**:
```bash
# Create LaunchAgent file
mkdir -p ~/Library/LaunchAgents

cat > ~/Library/LaunchAgents/com.vibemk.mcp.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.vibemk.mcp</string>
    <key>ProgramArguments</key>
    <array>
        <string>python3</string>
        <string>/path/to/main.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>EnvironmentVariables</key>
    <dict>
        <key>CHECKMK_SERVER_URL</key>
        <string>http://localhost:8080</string>
        <key>CHECKMK_SITE</key>
        <string>cmk</string>
        <key>CHECKMK_USERNAME</key>
        <string>automation</string>
        <key>CHECKMK_PASSWORD</key>
        <string>your_api_key</string>
    </dict>
</dict>
</plist>
EOF

# Load LaunchAgent
launchctl load ~/Library/LaunchAgents/com.vibemk.mcp.plist
```

### 10.3 Manage Updates

```bash
# Repository updates
git pull origin main

# After updates: Restart LLM client
osascript -e 'quit app "Claude"'
sleep 2
open -a Claude
```

### 10.4 Monitoring & Maintenance

```bash
# Check server status (if using LaunchAgent)
launchctl list | grep vibemk

# Log monitoring
tail -f ~/Library/Logs/Claude/mcp.log | grep vibemk

# Monitor performance
ps aux | grep "main.py"
```

### 10.5 Multiple CheckMK Instances

```json
{
  "mcpServers": {
    "vibemk-prod": {
      "command": "python3",
      "args": ["/path/to/main.py"], 
      "env": {
        "CHECKMK_SERVER_URL": "https://checkmk-prod.company.com",
        "CHECKMK_SITE": "production",
        "CHECKMK_USERNAME": "automation",
        "CHECKMK_PASSWORD": "prod_api_key"
      }
    },
    "vibemk-test": {
      "command": "python3",
      "args": ["/path/to/main.py"],
      "env": {
        "CHECKMK_SERVER_URL": "https://checkmk-test.company.com", 
        "CHECKMK_SITE": "testing",
        "CHECKMK_USERNAME": "automation",
        "CHECKMK_PASSWORD": "test_api_key"
      }
    }
  }
}
```

---

## 🎉 Installation Complete!

Your **vibeMK v0.1** server is now ready for use with any LLM clients. With **82 available tools** you can manage your complete CheckMK environment using natural language.

**Next steps**:
- ✅ Discover all `vibemk_*` tools in Claude  
- ✅ Test different tool categories
- ✅ Configure additional CheckMK instances
- ✅ Customize automation to your needs

**Support**:
- 📚 Documentation: [README.md](README.md)
- 🐛 Issues: GitHub Issues
- 💬 Discussions: GitHub Discussions
- 📧 Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)

**Happy Monitoring with vibeMK! 🚀**