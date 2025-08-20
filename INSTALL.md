# vibeMK - Installationsanleitung

Eine Schritt-für-Schritt Anleitung zur Installation und Konfiguration von vibeMK für LLM-Interfaces.

## 📋 Voraussetzungen

### System-Anforderungen

- **Betriebssystem**: macOS, Linux, oder Windows
- **Python**: Version 3.8 oder höher
- **CheckMK**: Version 2.1.0 oder höher (CE/CEE/CCE/CRE)
- **LLM Client**: Z.B. Claude Desktop, OpenAI API Client, etc.

### Software-Dependencies

- Python Virtual Environment Support
- Git (für Repository-Kloning)
- Zugriff auf CheckMK-Instanz (lokal oder remote)

## 🚀 vibeMK Features (Version 0.1)

### ✨ Aktuelle Features
- **🏷️ Einheitliche Tool-Benennung**: Alle 82 Tools mit `vibemk_` Präfix für bessere Identifikation
- **🔧 Modulare Architektur**: Saubere Handler-Struktur für verschiedene CheckMK-Bereiche
- **⚡ Optimierte Performance**: Effiziente API-Clients und Verbindungsmanagement
- **🛡️ Robuste Sicherheit**: Umfassende Input-Validierung und Fehlerbehandlung
- **🧪 Zero Dependencies**: Verwendet ausschließlich Python Standard-Bibliothek

### 📊 Tool-Übersicht (82 Tools)
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

## 🔧 Schritt 1: Repository Setup

### Repository klonen

```bash
# Repository klonen
git clone https://github.com/your-username/vibeMK.git
cd vibeMK

# Oder: ZIP-Download und extrahieren
# wget https://github.com/.../archive/main.zip
# unzip main.zip && cd vibeMK-main
```

### Python Virtual Environment erstellen

```bash
# Virtual Environment erstellen
python3 -m venv venv

# Virtual Environment aktivieren
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# Aktivierung überprüfen
which python  # sollte venv/bin/python zeigen
```

## 📦 Schritt 2: Dependencies installieren

### ⚡ Zero-Dependency Installation (Empfohlen)

```bash
# Keine zusätzlichen Pakete nötig!
# vibeMK nutzt nur Python Standard-Bibliothek

# Installation überprüfen
python -c "import json, urllib.request, asyncio; print('✅ All dependencies available')"
```

### Legacy Installation (falls requirements.txt vorhanden)

```bash
# Falls vorhanden, aber nicht zwingend nötig
pip install -r requirements.txt 2>/dev/null || echo "No requirements.txt - using built-in modules"
```

## ⚙️ Schritt 3: CheckMK konfigurieren

### 3.1 CheckMK API-Benutzer erstellen

1. **CheckMK Web-Interface öffnen**:
   ```
   http://your-checkmk-server/cmk/
   ```

2. **Automation-Benutzer anlegen**:
   ```
   Setup → Users → Add user
   
   Einstellungen:
   - Username: automation  
   - Full name: vibeMK MCP Automation
   - Email: (optional)
   - Role: Automation user ✅
   - Disable password login: ✅
   ```

3. **API-Schlüssel generieren**:
   ```
   User bearbeiten → Automation secrets → Add secret
   
   - Description: "vibeMK LLM Server"
   - Copy the generated key ➡️ Wichtig für Claude Config!
   ```

### 3.2 Benutzer-Berechtigungen prüfen

```
Setup → Users → [automation user] → Effective permissions

Benötigte Berechtigungen:
✅ Use the REST API
✅ See hosts in monitoring  
✅ See services in monitoring
✅ See folder structure
✅ Configure rules and parameters
✅ Activate configuration changes
```

## 🔐 Schritt 4: LLM Client Konfiguration

### 4.1 Wichtiger Hinweis

✅ **Keine .env-Datei nötig!** Credentials werden direkt in der LLM Client Config gespeichert.

## 🔎 Schritt 5: vibeMK in LLM Client einrichten

### 5.1 Konfigurationsdatei finden

```bash
# macOS: Config-Datei öffnen
open -e ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Oder mit anderem Editor:
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

### 5.2 Absolute Pfade ermitteln

```bash
# Aktuelles Verzeichnis  
CURRENT_DIR=$(pwd)
echo "Server Path: $CURRENT_DIR/main.py"

# Python im venv
echo "Python Path: $CURRENT_DIR/venv/bin/python"
```

### 5.3 MCP Server registrieren

**Basis-Konfiguration:**
```json
{
  "mcpServers": {
    "vibemk": {
      "command": "/Users/andre/data/Entwicklung/claude/vibeMK/venv/bin/python",
      "args": ["/Users/andre/data/Entwicklung/claude/vibeMK/main.py"],
      "env": {
        "CHECKMK_SERVER_URL": "http://localhost:8080",
        "CHECKMK_SITE": "cmk",
        "CHECKMK_USERNAME": "automation",
        "CHECKMK_PASSWORD": "Ihr_echter_API_Schlüssel_hier"
      }
    }
  }
}
```

**Erweiterte Konfiguration:**
```json
{
  "mcpServers": {
    "vibemk": {
      "command": "/absolute/path/to/venv/bin/python",
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

⚠️ **Wichtig**: 
- Absolute Pfade verwenden!
- Echten API-Schlüssel einsetzen!
- Server-ID ist jetzt `vibemk` (früher `checkmk`)

## 🧪 Schritt 6: Installation testen

### 6.1 Basis-Verbindungstest

```bash
# CheckMK-Server erreichbar?
curl -s http://localhost:8080/cmk/ | grep -i checkmk

# API-Endpoint testen  
curl -H "Authorization: Bearer automation YOUR_API_KEY" \
     -H "Accept: application/json" \
     http://localhost:8080/cmk/check_mk/api/1.0/version
```

### 6.2 vibeMK Server testen

```bash
# Server starten (Test-Modus)
CHECKMK_SERVER_URL="http://localhost:8080" \
CHECKMK_SITE="cmk" \
CHECKMK_USERNAME="automation" \
CHECKMK_PASSWORD="your_api_key" \
python main.py
```

**Test-Request senden:**
```bash
# In einem anderen Terminal:
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | \
CHECKMK_SERVER_URL="http://localhost:8080" \
CHECKMK_SITE="cmk" \
CHECKMK_USERNAME="automation" \
CHECKMK_PASSWORD="your_api_key" \
python main.py
```

**Erwartete Ausgabe:**
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

## 🖥️ Schritt 7: LLM Client Integration

### 7.1 LLM Client beenden

```bash
# macOS: Claude komplett beenden
osascript -e 'quit app "Claude"'

# oder manuell: Cmd+Q drücken
```

### 7.2 LLM Client neustarten

```bash
# macOS: Claude neu starten
open -a Claude

# Warten auf Startup (ca. 5-10 Sekunden)
```

### 7.3 vibeMK-Integration überprüfen

**Test-Fragen an Claude**:

1. **Tools verfügbar?**
   ```
   "Welche vibeMK-Tools hast du verfügbar?"
   ```

2. **Verbindung testen**:
   ```  
   "Verwende vibemk_debug_checkmk_connection um die Verbindung zu testen"
   ```

3. **Version abrufen**:
   ```
   "Zeige mir die CheckMK-Version mit vibemk_get_checkmk_version"
   ```

4. **Hosts anzeigen**:
   ```
   "Liste alle CheckMK-Hosts mit vibemk_get_checkmk_hosts auf"
   ```

## 🐛 Schritt 8: Troubleshooting

### 8.1 Häufige Probleme

| Problem | Symptom | Lösung |
|---------|---------|--------|
| "No vibemk tools available" | Claude kennt keine vibemk_* Tools | Config-Pfade prüfen, Claude neustarten |
| "Connection failed" | API-Verbindung fehlgeschlagen | Server-URL und Port überprüfen |
| "Authentication failed" | 401 Unauthorized | API-Schlüssel und Username prüfen |
| "Permission denied" | 403 Forbidden | Benutzer-Berechtigungen in CheckMK |
| "Python not found" | Server startet nicht | Virtual Environment-Pfad korrigieren |
| "Module not found" | Import-Fehler | `source venv/bin/activate` ausführen |

### 8.2 Debug-Logs aktivieren

**MCP-Logs überwachen** (macOS):
```bash
# Log-Datei überwachen
tail -f ~/Library/Logs/Claude/mcp.log

# Alle Claude-Logs
ls -la ~/Library/Logs/Claude/
```

**Server-Debug-Modus**:
```bash
# Debug-Level Logging aktivieren
export CHECKMK_DEBUG=true
export CHECKMK_SERVER_URL="http://localhost:8080"
export CHECKMK_SITE="cmk"  
export CHECKMK_USERNAME="automation"
export CHECKMK_PASSWORD="your_api_key"

python main.py 2>&1 | tee vibemk-debug.log
```

### 8.3 Verbindungsdiagnose

```bash
# Schritt-für-Schritt Diagnose

# 1. Python-Environment prüfen
which python
python --version
python -c "import json, urllib.request, asyncio; print('✅ Modules OK')"

# 2. CheckMK-Server erreichbar?
curl -v http://localhost:8080/cmk/

# 3. API-Endpoint verfügbar?
curl -v -H "Authorization: Bearer automation YOUR_KEY" \
        http://localhost:8080/cmk/check_mk/api/1.0/version

# 4. vibeMK Server startbar?
timeout 10s python main.py

# 5. LLM Client Config gültig?
python -m json.tool ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### 8.4 Tool-Verfügbarkeit prüfen

```bash
# Alle verfügbaren Tools anzeigen
python -c "
from mcp.tools import get_all_tools
tools = get_all_tools()
print(f'Total tools: {len(tools)}')
for tool in tools[:5]:
    print(f'- {tool[\"name\"]}: {tool[\"description\"][:50]}...')
"
```

### 8.5 Konfiguration zurücksetzen

```bash
# 1. LLM Client beenden
osascript -e 'quit app "Claude"'

# 2. MCP-Config sichern
cp ~/Library/Application\ Support/Claude/claude_desktop_config.json \
   ~/Library/Application\ Support/Claude/claude_desktop_config.json.backup

# 3. Minimal-Config erstellen
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {}
}
EOF

# 4. Claude neustarten und schrittweise Server hinzufügen
```

## ✅ Schritt 9: Installation verifizieren

### 9.1 Erfolgskriterien

- ✅ CheckMK-API antwortet auf Version-Request
- ✅ vibeMK Server startet ohne Fehler  
- ✅ LLM Client erkennt alle 82 vibemk_* Tools
- ✅ Verbindungsdiagnose erfolgreich
- ✅ Host- und Service-Daten abrufbar

### 9.2 Test-Sequenz

```
1. "vibemk_debug_checkmk_connection" → "✅ Connection successful" 
2. "vibemk_get_checkmk_version" → CheckMK-Versionsinformationen
3. "vibemk_get_checkmk_hosts" → Liste der konfigurierten Hosts
4. "vibemk_get_checkmk_services" → Service-Übersicht
5. "vibemk_get_folders" → Folder-Struktur
```

### 9.3 Performance-Test

```
"vibemk_test_all_endpoints" → Alle API-Endpoints erfolgreich getestet
```

### 9.4 Tool-Kategorien-Test

Testen Sie verschiedene Tool-Kategorien:

- **Host Management**: `vibemk_get_host_status`
- **Monitoring**: `vibemk_get_current_problems` 
- **Configuration**: `vibemk_get_pending_changes`
- **Rules**: `vibemk_get_rulesets`
- **Groups**: `vibemk_get_host_groups`

## 🚀 Schritt 10: Produktive Nutzung

### 10.1 vibeMK optimal nutzen

**Natürliche Sprache verwenden:**
```
"Zeige mir alle Hosts mit Problemen"
"Erstelle eine neue Hostgruppe namens 'Webserver'" 
"Aktiviere alle ausstehenden Änderungen"
"Welche Services auf dem Host 'server01' haben Probleme?"
```

**Erweiterte Operationen:**
```
"Erstelle einen Host in der Folder 'production' mit IP 192.168.1.100"
"Plane eine Wartungszeit für alle Webserver von heute 22:00 bis morgen 06:00"
"Zeige mir die Performance-Metriken für den Host 'database01'"
```

### 10.2 Autostart einrichten (optional)

**macOS LaunchAgent**:
```bash
# LaunchAgent-Datei erstellen
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
        <string>/path/to/venv/bin/python</string>
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

# LaunchAgent laden
launchctl load ~/Library/LaunchAgents/com.vibemk.mcp.plist
```

### 10.3 Updates verwalten

```bash
# Repository Updates
git pull origin main

# Nach Updates: LLM Client neustarten
osascript -e 'quit app "Claude"'
sleep 2
open -a Claude
```

### 10.4 Monitoring & Wartung

```bash
# Server-Status prüfen (falls LaunchAgent verwendet)
launchctl list | grep vibemk

# Log-Monitoring
tail -f ~/Library/Logs/Claude/mcp.log | grep vibemk

# Performance überwachen
ps aux | grep "main.py"
```

### 10.5 Mehrere CheckMK-Instanzen

```json
{
  "mcpServers": {
    "vibemk-prod": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/main.py"], 
      "env": {
        "CHECKMK_SERVER_URL": "https://checkmk-prod.company.com",
        "CHECKMK_SITE": "production",
        "CHECKMK_USERNAME": "automation",
        "CHECKMK_PASSWORD": "prod_api_key"
      }
    },
    "vibemk-test": {
      "command": "/path/to/venv/bin/python",
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

## 🎉 Installation abgeschlossen!

Ihr **vibeMK v0.1** Server ist jetzt bereit für die Nutzung mit beliebigen LLM Clients. Mit **82 verfügbaren Tools** können Sie Ihre komplette CheckMK-Umgebung über natürliche Sprache verwalten.

**Nächste Schritte**:
- ✅ Entdecken Sie alle `vibemk_*` Tools in Claude  
- ✅ Testen Sie verschiedene Tool-Kategorien
- ✅ Konfigurieren Sie zusätzliche CheckMK-Instanzen
- ✅ Passen Sie die Automation an Ihre Bedürfnisse an

**Support**:
- 📚 Dokumentation: [README.md](README.md)
- 🐛 Issues: GitHub Issues
- 💬 Discussions: GitHub Discussions
- 📧 Beiträge: [CONTRIBUTING.md](CONTRIBUTING.md)

**Happy Monitoring mit vibeMK! 🚀**