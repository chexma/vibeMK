# vibeMK Development Makefile
# Provides convenient commands for code quality checks

.PHONY: format check test lint clean help package typecheck push-ready install-dev status

# Default target
help:
	@echo "🔧 vibeMK Development Commands"
	@echo "============================="
	@echo ""
	@echo "make format     - Format code with black and isort"
	@echo "make check      - Run all quality checks (format + type + test)"
	@echo "make lint       - Run only linting/formatting checks (black, isort, ruff)"
	@echo "make package    - Build the wheel and check it installs and runs"
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
	@ruff check .
	@echo "✅ Linting checks passed"

# Run type checking
typecheck:
	@echo "🏷️ Running type checks..."
	@mypy .

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
	@# setuptools reuses build/lib between runs and packages whatever it finds
	@# there, so a tree left over from an older configuration ends up inside
	@# the next wheel. Removing it is what keeps a build reproducible.
	@rm -rf build dist 2>/dev/null || true
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
# Mirror the CI package job: build, then prove the result installs and runs.
# Every entry-point defect this project has had was invisible from the
# checkout and only showed up here.
package: clean
	@echo "📦 Building the distribution..."
	@python -m build
	@python -m twine check dist/*
	@rm -rf /tmp/vibemk-install-check
	@python -m venv /tmp/vibemk-install-check
	@/tmp/vibemk-install-check/bin/pip install --quiet dist/*.whl
	@/tmp/vibemk-install-check/bin/vibemk --help > /dev/null
	@echo "✅ The wheel installs and the vibemk command starts"
