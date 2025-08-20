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

### ✨ What makes vibeMK special

- **🏗️ Modular Architecture**: Clean separation of concerns with dedicated modules
- **🔌 Zero Dependencies**: No external packages required - uses Python standard library only
- **⚡ Better Performance**: Improved HTTP client with retry logic and connection pooling
- **🛡️ Enhanced Security**: Comprehensive input validation and error handling
- **📝 Type Safety**: Full type hints for better IDE support and code quality
- **🔍 Advanced Debugging**: Built-in debugging tools and comprehensive logging
- **🧪 Testable Design**: Modular structure enables comprehensive unit testing
- **📚 Better Documentation**: Complete API documentation and examples

## 🚀 Quick Start

### 1. Installation

**Option A: Package Installation (Recommended)**
```bash
# Clone repository
git clone https://github.com/chexma/vibeMK.git
cd vibeMK

# Install package
pip install -e .

# Optional: Install development dependencies
pip install -e ".[dev]"
```

**Option B: Standalone (No Dependencies)**
```bash
# Clone repository
git clone https://github.com/chexma/vibeMK.git
cd vibeMK

# Ready to use! No additional dependencies required
python main.py
```

### 2. Configuration

**Important**: Configuration is done directly in your LLM client config file (e.g., `claude_desktop_config.json` for Claude Desktop)!

**For installed package:**
```json
{
  "mcpServers": {
    "checkmk-server": {
      "command": "vibeMK",
      "env": {
        "CHECKMK_SERVER_URL": "http://your-checkmk-server:8080",
        "CHECKMK_SITE": "cmk",
        "CHECKMK_USERNAME": "automation",
        "CHECKMK_PASSWORD": "your_automation_password"
      }
    }
  }
}
```

**Quick Configuration:**
```bash
# Copy example configuration
cp claude_desktop_config.example.json your_llm_config.json

# Edit with your CheckMK details
nano your_llm_config.json
```

**Example Configuration:**
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

📁 **More Examples**: See `examples/llm_configs/` for different scenarios (production, development, localhost)

### 3. LLM Integration

Configuration is already included in step 2. Simply restart your LLM client (e.g., Claude Desktop, OpenAI API, etc.).

### 4. First Steps

```bash
# 1. Test connection
debug_checkmk_connection

# 2. List hosts
get_checkmk_hosts

# 3. Check current problems
get_current_problems

# 4. Add new host
create_host("new-server", "/servers", {"ipaddress": "192.168.1.100", "alias": "New Server"})
```

## 📚 Verfügbare Funktionen

### 🔍 Verbindung & Diagnose (3 Funktionen)
| Funktion | Beschreibung |
|----------|--------------|
| `debug_checkmk_connection` | Umfassende Verbindungsdiagnose |
| `test_all_endpoints` | Alle API-Endpunkte testen |
| `get_checkmk_version` | Version und Systeminfo anzeigen |

### 🖥️ Host-Management (8 Funktionen)
| Funktion | Beschreibung |
|----------|--------------|
| `get_checkmk_hosts` | Hosts auflisten (mit Filterung) |
| `get_host_status` | Host-Status und Zustand |
| `get_host_details` | Detaillierte Host-Informationen |
| `get_host_config` | Host-Konfiguration anzeigen |
| `create_host` | Neuen Host erstellen |
| `delete_host` | Host permanent entfernen |
| `update_host` | Host-Konfiguration ändern |
| `move_host` | Host in anderen Ordner verschieben |

### ⚙️ Service-Management (6 Funktionen)
| Funktion | Beschreibung |
|----------|--------------|
| `get_checkmk_services` | Services eines Hosts auflisten |
| `get_service_status` | Service-Status abfragen |
| `get_service_config` | Service-Konfiguration anzeigen |
| `discover_services` | Services auf Host entdecken |
| `get_service_discovery` | Discovery-Ergebnisse anzeigen |
| `bulk_discovery` | Bulk-Discovery für mehrere Hosts |

### 🚨 Monitoring & Probleme (5 Funktionen)
| Funktion | Beschreibung |
|----------|--------------|
| `get_current_problems` | Aktuelle Probleme anzeigen |
| `acknowledge_problem` | Problem als bekannt markieren |
| `schedule_downtime` | Wartungsfenster planen |
| `remove_downtime` | Downtime vorzeitig beenden |
| `reschedule_check` | Sofortige Überprüfung erzwingen |

## 💡 Praktische Beispiele

### Tägliche Monitoring-Routinen

```bash
# Morgen-Check
"Zeige mir alle aktuellen Probleme und geplanten Downtimes für heute"

# Neuen Server hinzufügen
"Erstelle einen neuen Host 'web-server-05' im Ordner '/servers/web' 
mit der IP 192.168.1.105 und entdecke alle Services"

# Wartung planen
"Plane eine 2-stündige Downtime für 'db-server-01' ab 22:00 heute 
für Datenbank-Wartung"
```

### Automatisierte Workflows

```bash
# Kompletter Server-Setup
"Erstelle Host 'app-server-03' in '/production/apps', IP 10.0.1.50,
führe Service-Discovery durch, aktiviere alle Änderungen"

# Problem-Management
"Zeige alle kritischen Probleme, bestätige das MySQL-Problem auf db-01 
mit Kommentar 'DBA arbeitet daran'"
```

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

### 🔧 Design Principles

- **Single Responsibility**: Each module has a clear, focused purpose
- **Dependency Injection**: Easy testing and mocking
- **Error Handling**: Comprehensive exception handling with custom exceptions
- **Type Safety**: Full type hints for better IDE support
- **Logging**: Structured logging for debugging and monitoring
- **Configuration**: Centralized configuration management
- **Extensibility**: Easy to add new handlers and tools

## 🔧 Erweiterte Konfiguration

Alle Einstellungen werden über die LLM-Konfigurationsdatei verwaltet:

```json
{
  "mcpServers": {
    "checkmk-complete": {
      "command": "python",
      "args": ["/path/to/checkmk_mcp_server.py"],
      "env": {
        // SSL/TLS Setup
        "CHECKMK_SERVER_URL": "https://checkmk.company.com:443",
        "CHECKMK_VERIFY_SSL": "true",
        "CHECKMK_CERT_FILE": "/path/to/client.crt",
        "CHECKMK_KEY_FILE": "/path/to/client.key",
        
        // Performance-Optimierung
        "CHECKMK_TIMEOUT": "60",
        "CHECKMK_MAX_RETRIES": "3",
        "CHECKMK_RATE_LIMIT_REQUESTS": "200",
        
        // Debug-Modus
        "CHECKMK_DEBUG": "true"
      }
    }
  }
}
```

## 📊 Unterstützte CheckMK-Versionen

| CheckMK Version | Kompatibilität | Features |
|-----------------|----------------|----------|
| **2.3.x** | ✅ Vollständig | Alle Features verfügbar |
| **2.2.x** | ✅ Vollständig | Alle Features verfügbar |
| **2.1.x** | ✅ Vollständig | Alle Features verfügbar |
| **2.0.x** | ✅ Vollständig | Basis-REST-API |
| **1.6.x** | ⚠️ Eingeschränkt | Nur Web-API (legacy) |

### Edition-Support

- **Raw Edition**: Grundfunktionen verfügbar
- **Enterprise Edition**: Alle Features inklusive BI, Agent Bakery, Metriken
- **Cloud Edition**: Alle Enterprise Features

## 🔍 Troubleshooting

### Häufige Probleme

#### Verbindungsfehler
```bash
# Test-Befehl
debug_checkmk_connection

# Typische Lösungen:
# 1. Server-URL prüfen
# 2. Netzwerkverbindung testen: ping checkmk-server
# 3. Firewall-Regeln überprüfen
```

#### Authentifizierungsfehler
```bash
# Automation-User prüfen
get_users

# Berechtigungen validieren:
# 1. User existiert in CheckMK
# 2. Passwort korrekt
# 3. Benutzer hat API-Zugriff
```

## 📚 Dokumentation

- 📖 [Detaillierte Installationsanleitung](INSTALLATION.md)
- 📚 [Vollständiges Benutzerhandbuch](USER_GUIDE.md)

## 🤝 Beitragen

### Contribution Guidelines

1. **Fork** das Repository
2. **Branch erstellen**: `git checkout -b feature/neue-funktion`
3. **Änderungen committen**: `git commit -m 'Neue Funktion hinzugefügt'`
4. **Push**: `git push origin feature/neue-funktion`
5. **Pull Request** erstellen

### Code-Standards

- **Python 3.8+** Kompatibilität
- **Type Hints** verwenden
- **Async/Await** für I/O-Operationen
- **Comprehensive Error Handling**
- **Unit Tests** für neue Features

## 📄 Lizenz

Dieses Projekt ist unter der [GNU General Public License v3.0](LICENSE) lizenziert.

## 🙏 Danksagungen

- **CheckMK Team** für die exzellente REST API
- **Anthropic** für Claude und das MCP Protocol
- **Python Community** für großartige Libraries
- **Contributors** für Verbesserungen und Feedback

## 📞 Support

### Dokumentation
- 📖 [Installationsanleitung](INSTALLATION.md)
- 📚 [Vollständiges Benutzerhandbuch](USER_GUIDE.md)
- 💡 [Praktische Beispiele](EXAMPLES.md)

### Hilfe erhalten
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/your-repo/issues)
- 💬 **Diskussionen**: [GitHub Discussions](https://github.com/your-repo/discussions)
- 📧 **Email**: support@your-domain.com

### Community
- 🌟 **Star** das Repository wenn es hilfreich ist
- 🔄 **Fork** für eigene Anpassungen
- 📢 **Teilen** mit anderen CheckMK-Benutzern

---

**Happy Monitoring mit CheckMK und Claude!** 🎉

*Automatisiere dein Monitoring, spare Zeit, und konzentriere dich auf das Wesentliche.*