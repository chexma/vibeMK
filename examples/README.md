# vibeMK Configuration Examples

This directory contains example configurations for different use cases.

## LLM Client Configuration

### 📁 `claude_desktop_configs/`

**Basic Configuration (`basic_config.json`)**
- Simple single-server setup
- Minimal configuration options
- Perfect for getting started

**Advanced Configuration (`advanced_config.json`)**
- Multi-environment setup (production + development)
- All configuration options shown
- SSL verification enabled/disabled per environment

**Localhost Configuration (`localhost_config.json`)**
- Local CheckMK development setup
- Relaxed timeouts and SSL settings
- Ideal for testing and development

### 🔧 Setup Instructions

1. **Choose Your Configuration**
   ```bash
   cp examples/claude_desktop_configs/basic_config.json claude_desktop_config.json
   ```

2. **Edit Configuration**
   - Replace `/Users/yourname/vibemk/main.py` with your actual path
   - Update CheckMK server details
   - Set your automation credentials

3. **Install in LLM Client**
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`

4. **Restart LLM Client**

### 🔒 Security Notes

- **Never commit your actual `claude_desktop_config.json`** (already in .gitignore)
- Use strong automation passwords
- Enable SSL verification in production
- Consider using environment-specific automation users

### 🛠️ Configuration Options

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `CHECKMK_SERVER_URL` | CheckMK server URL | - | `https://checkmk.company.com` |
| `CHECKMK_SITE` | CheckMK site name | - | `production` |
| `CHECKMK_USERNAME` | Automation username | - | `automation` |
| `CHECKMK_PASSWORD` | Automation password | - | `secure-password` |
| `CHECKMK_VERIFY_SSL` | SSL verification | `true` | `true`/`false` |
| `CHECKMK_TIMEOUT` | Request timeout (sec) | `30` | `45` |
| `CHECKMK_MAX_RETRIES` | Max retry attempts | `3` | `5` |

### 🧪 Testing Your Setup

After configuration, test in your LLM client:

```
Test my CheckMK connection and show server version
```

Expected response:
```
✅ Connection successful
CheckMK Version: 2.3.0
Site: production
Tools available: 82
```

### 🐛 Troubleshooting

**Connection Issues:**
- Check server URL and credentials
- Verify SSL settings
- Test network connectivity

**Tool Loading Issues:**
- Ensure Python path is correct
- Check file permissions
- Verify environment variables

**Performance Issues:**
- Adjust timeout settings
- Check CheckMK server load
- Review network latency