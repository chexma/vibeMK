# vibeMK 🚀

**CheckMK Monitoring via LLM - Professional MCP Server**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![CheckMK 2.1+](https://img.shields.io/badge/CheckMK-2.1+-green.svg)](https://checkmk.com/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-purple.svg)](https://spec.modelcontextprotocol.io/)
[![No Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](https://github.com/your-username/vibemk)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Typed](https://img.shields.io/badge/typed-mypy-blue.svg)](https://mypy-lang.org/)

## 🎯 Overview

vibeMK enables complete management of your CheckMK monitoring environment directly through LLM interfaces using natural language. With **106+ available functions** and a completely refactored architecture, you can automate all important CheckMK operations efficiently and reliably.

### ✨ Key Features

- 🖥️ **Host Management**: Create, configure, move, and delete hosts
- ⚙️ **Service Management**: Service discovery, status monitoring, and configuration  
- 🚨 **Problem Management**: View problems, acknowledge issues, and schedule downtimes
- 📁 **Organization**: Folders, groups, and structured management
- 👥 **User Management**: Manage users and contact groups
- 🔄 **Configuration**: Activate changes and monitor system status
- 📜 **Rule Management**: Configure monitoring rules and rulesets
- 📊 **Enterprise Features**: BI, Agent Bakery, metrics (Enterprise Edition)

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/chexma/vibeMK.git
cd vibeMK

# Ready to use! No dependencies needed - uses Python standard library only
python main.py
```

📖 **Complete Installation Guide**: See [INSTALL.md](INSTALL.md) for detailed step-by-step instructions including:
- CheckMK automation user setup (Administrator role required)
- LLM client configuration
- Troubleshooting and testing

### 2. Configuration Example

Configure your LLM client (e.g., Claude Desktop) with:

```json
{
  "mcpServers": {
    "vibemk": {
      "command": "python",
      "args": ["/path/to/your/vibemk/main.py"],
      "env": {
        "CHECKMK_SERVER_URL": "https://your-checkmk-server.example.com",
        "CHECKMK_SITE": "mysite",
        "CHECKMK_USERNAME": "automation",
        "CHECKMK_PASSWORD": "your-automation-password"
      }
    }
  }
}
```

📁 **More Examples**: See `examples/llm_configs/` and [INSTALL.md](INSTALL.md)  
📸 **Visual Examples**: See `examples/Screenshots/` for example prompts and usage patterns  
💡 **Advanced Usage**: See `examples/ExamplePrompts.md` for complex scenarios and tips

### 3. First Steps

```bash
# 1. Test connection
debug_checkmk_connection

# 2. List hosts
get_checkmk_hosts

# 3. Check current problems
get_current_problems
```

## 📚 Available Functions

### 🔍 Connection & Diagnostics (3 Functions)
| Function | Description |
|----------|-------------|
| `debug_checkmk_connection` | Comprehensive connection diagnostics |
| `test_all_endpoints` | Test all API endpoints |
| `get_checkmk_version` | Display version and system information |

### 🖥️ Host Management (8 Functions)
| Function | Description |
|----------|-------------|
| `get_checkmk_hosts` | List hosts (with filtering) |
| `get_host_status` | Get host status and state |
| `get_host_details` | Detailed host information |
| `get_host_config` | Display host configuration |
| `create_host` | Create new host |
| `delete_host` | Permanently remove host |
| `update_host` | Modify host configuration |
| `move_host` | Move host to different folder |

### ⚙️ Service Management (6 Functions)
| Function | Description |
|----------|-------------|
| `get_checkmk_services` | List services of a host |
| `get_service_status` | Query service status |
| `get_service_config` | Display service configuration |
| `discover_services` | Discover services on host |
| `get_service_discovery` | Show discovery results |
| `bulk_discovery` | Bulk discovery for multiple hosts |

### 🚨 Monitoring & Problems (5 Functions)
| Function | Description |
|----------|-------------|
| `get_current_problems` | Display current problems |
| `acknowledge_problem` | Mark problem as acknowledged |
| `schedule_downtime` | Schedule maintenance window |
| `remove_downtime` | End downtime early |
| `reschedule_check` | Force immediate check |

## 💡 Practical Examples

### Daily Monitoring Routines

```bash
# Morning check
"Show me all current problems and scheduled downtimes for today"

# Add new server
"Create a new host 'web-server-05' in folder '/servers/web' 
with IP 192.168.1.105 and discover all services"

# Schedule maintenance
"Schedule a 2-hour downtime for 'db-server-01' starting at 22:00 today 
for database maintenance"
```

### Automated Workflows

```bash
# Complete server setup
"Create host 'app-server-03' in '/production/apps', IP 10.0.1.50,
run service discovery, activate all changes"

# Problem management
"Show all critical problems, acknowledge the MySQL problem on db-01 
with comment 'DBA is working on it'"
```

### 📚 More Examples & Resources

- **📸 Visual Examples**: Check `examples/Screenshots/` for real LLM conversation examples with screenshots
- **💡 Advanced Prompts**: See `examples/ExamplePrompts.md` for complex scenarios, tips, and best practices  
- **⚙️ Configuration Examples**: Browse `examples/llm_configs/` for different LLM client setups

## 🏗️ Architecture

vibeMK features a clean, modular architecture:

```
vibeMK/
├── main.py                     # Entry point
├── config/                     # Configuration management
│   ├── __init__.py
│   └── settings.py
├── api/                        # HTTP client and exceptions
│   ├── __init__.py
│   ├── client.py               # Robust HTTP client with retry logic
│   └── exceptions.py           # Custom exception classes
├── mcp/                        # MCP protocol handling
│   ├── __init__.py
│   ├── server.py              # MCP server implementation
│   └── tools.py               # Tool definitions
├── handlers/                   # Business logic handlers
│   ├── __init__.py
│   ├── base.py                # Base handler class
│   ├── connection.py          # Connection & diagnostics
│   ├── hosts.py              # Host management  
│   ├── services.py           # Service management
│   ├── monitoring.py         # Problem management
│   └── configuration.py      # Configuration management
└── utils/                      # Utilities
    ├── __init__.py
    └── logging.py             # Logging configuration
```

| CheckMK Version | Compatibility | Features |
|-----------------|---------------|----------|
| **2.3.x** | ✅ Full | All features available |
| **2.2.x** | ✅ Full | All features available |
| **2.1.x** | ✅ Full | All features available |
| **2.0.x** | ✅ Full | Basic REST API |
| **1.6.x** | ⚠️ Limited | Web API only (legacy) |

### Edition Support

- **Raw Edition**: Basic functions available
- **Enterprise Edition**: All features including BI, Agent Bakery, Metrics
- **Cloud Edition**: All Enterprise features

## 🔍 Troubleshooting

### Common Issues

#### Connection Errors
```bash
# Test command
debug_checkmk_connection

# Common solutions:
# 1. Check server URL
# 2. Test network connection: ping checkmk-server
# 3. Check firewall rules
```

#### Authentication Errors
```bash
# Check automation user
get_users

# Validate permissions:
# 1. User exists in CheckMK
# 2. Password is correct
# 3. User has API access
```

## 📚 Documentation

- 📖 [Complete Installation Guide](INSTALL.md) - Step-by-step setup instructions
- 📚 [Complete User Manual](USER_GUIDE.md)

## 🤝 Contributing

### Contribution Guidelines

1. **Fork** the repository
2. **Create branch**: `git checkout -b feature/new-feature`
3. **Commit changes**: `git commit -m 'Add new feature'`
4. **Push**: `git push origin feature/new-feature`
5. **Create Pull Request**

### Code Standards

- **Python 3.8+** compatibility
- **Use Type Hints**
- **Async/Await** for I/O operations
- **Comprehensive Error Handling**
- **Unit Tests** for new features

## 📄 License

This project is licensed under the [GNU General Public License v3.0](LICENSE).

### Documentation
- 📖 [Complete Installation Guide](INSTALL.md) - CheckMK setup, user creation, troubleshooting
- 📚 [Complete User Manual](USER_GUIDE.md)
- 💡 [Advanced Example Prompts](examples/ExamplePrompts.md) - Complex scenarios and best practices
- 📸 [Visual Examples](examples/Screenshots/) - Real conversation screenshots and usage patterns  
- ⚙️ [Configuration Examples](examples/llm_configs/) - LLM client setup examples

### Get Help
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/chexma/vibeMK/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/chexma/vibeMK/discussions)
- 📧 **Email**: chexma@gmx.de

### Community
- 🌟 **Star** the repository if it's helpful
- 🔄 **Fork** for your own customizations
- 📢 **Share** with other CheckMK users

---

**Happy Monitoring with CheckMK and LLMs!** 🎉

*Automate your monitoring, save time, and focus on what matters.*# Test formatting fix
