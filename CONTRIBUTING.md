# Contributing to vibeMK

Thank you for your interest in contributing to vibeMK! This document provides guidelines for contributing to this CheckMK MCP Server project.

## 🚀 Getting Started

1. **Fork the Repository**
   ```bash
   git clone https://github.com/yourusername/vibemk.git
   cd vibemk
   ```

2. **Set Up Development Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e .
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your CheckMK credentials
   ```

## 🔧 Development Guidelines

### Code Style
- Use type hints for all functions
- Follow PEP 8 style guidelines
- Add docstrings to all public functions
- Keep functions focused and small

### Project Structure
```
vibemk/
├── api/           # CheckMK API client
├── config/        # Configuration management
├── handlers/      # Tool handlers (modular design)
├── mcp/          # MCP server implementation
└── utils/        # Utility functions
```

### Adding New Features

1. **New Handler**: Create in `handlers/` directory
2. **New Tool**: Add to `mcp/tools.py`
3. **Register Handler**: Update `mcp/server.py`

Example handler structure:
```python
from typing import Dict, Any, List
from handlers.base import BaseHandler

class MyHandler(BaseHandler):
    async def handle(self, tool_name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Implementation here
        pass
```

## 🧪 Testing

1. **Test Your Changes**
   ```bash
   python main.py
   ```

2. **Test with LLM Client**
   - Update your claude_desktop_config.json
   - Test the new functionality

## 📝 Submitting Changes

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Commit Changes**
   ```bash
   git commit -m "Add: description of your changes"
   ```

3. **Push and Create PR**
   ```bash
   git push origin feature/my-new-feature
   # Create Pull Request on GitHub
   ```

### Commit Messages
Use conventional commit format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation
- `refactor:` for code refactoring
- `test:` for tests

## 🐛 Bug Reports

When reporting bugs, please include:
- CheckMK version
- Python version
- Error messages/logs
- Steps to reproduce
- Expected vs actual behavior

## 🔒 Security

- Never commit credentials or sensitive data
- Use environment variables for configuration
- Follow secure coding practices
- Report security issues privately

## 📚 Documentation

- Update README.md for significant changes
- Add examples for new features
- Keep docstrings up to date
- Update INSTALL.md if needed

## 🤝 Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help newcomers learn
- Maintain a positive environment

## 📄 License

By contributing, you agree that your contributions will be licensed under the GPL v3 License.

## 🙋 Need Help?

- Create an issue for questions
- Check existing documentation
- Look at similar implementations in handlers/

Thank you for contributing to vibeMK! 🎉