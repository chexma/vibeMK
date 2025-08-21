# vibeMK Development Makefile
# Provides convenient commands for code quality checks

.PHONY: format check test lint clean help

# Default target
help:
	@echo "🔧 vibeMK Development Commands"
	@echo "============================="
	@echo ""
	@echo "make format     - Format code with black and isort"
	@echo "make check      - Run all quality checks (format + type + test)"
	@echo "make lint       - Run only linting/formatting checks"
	@echo "make test       - Run test suite"
	@echo "make clean      - Clean up temporary files"
	@echo "make push-ready - Prepare code for push (format + check)"
	@echo ""

# Format code automatically
format:
	@echo "🔧 Formatting code..."
	@black .
	@isort .
	@echo "✅ Code formatted successfully"

# Run only linting checks (no tests)
lint:
	@echo "🔍 Running linting checks..."
	@black --check .
	@isort --check-only .
	@echo "✅ Linting checks passed"

# Run type checking
typecheck:
	@echo "🏷️ Running type checks..."
	@mypy . --ignore-missing-imports --disable-error-code=no-untyped-def --disable-error-code=no-untyped-call

# Run test suite
test:
	@echo "🧪 Running tests..."
	@pytest -v

# Run all quality checks
check: format lint typecheck test
	@echo "🎉 All quality checks completed!"

# Prepare for git push
push-ready: format lint
	@echo "✅ Code is ready for git push!"
	@echo "You can now run: git add . && git commit && git push"

# Clean temporary files
clean:
	@echo "🧹 Cleaning temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup completed"

# Install development dependencies
install-dev:
	@echo "📦 Installing development dependencies..."
	@pip install black isort mypy pytest pytest-asyncio
	@echo "✅ Development dependencies installed"

# Show git status after formatting
status: format
	@echo "📊 Git status after formatting:"
	@git status --short