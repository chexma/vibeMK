#!/bin/bash

# vibeMK Code Quality Checker
# Run all formatting and type checks manually

echo "🔍 vibeMK Code Quality Checks"
echo "============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track if any checks fail
CHECKS_FAILED=0

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        CHECKS_FAILED=1
    fi
}

# Check if we're in the project root
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ Error: Please run from project root directory${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Running all code quality checks...${NC}"
echo ""

# 1. Format code with black
echo "🔧 Step 1: Formatting code with black..."
black .
print_status $? "Black formatting applied"
echo ""

# 2. Sort imports with isort
echo "📦 Step 2: Sorting imports with isort..."
isort .
print_status $? "Import sorting applied"
echo ""

# 3. Verify black formatting
echo "🔍 Step 3: Verifying black formatting..."
black --check .
print_status $? "Black formatting verification"
echo ""

# 4. Verify isort formatting  
echo "🔍 Step 4: Verifying import sorting..."
isort --check-only .
print_status $? "Import sorting verification"
echo ""

# 5. Type checking with mypy
echo "🏷️  Step 5: Running type checks..."
mypy . --ignore-missing-imports --disable-error-code=no-untyped-def --disable-error-code=no-untyped-call
print_status $? "Type checking"
echo ""

# 6. Run tests
echo "🧪 Step 6: Running test suite..."
if command -v pytest &> /dev/null; then
    pytest -v --tb=short
    print_status $? "Test suite"
else
    echo -e "${YELLOW}⚠️  pytest not found - skipping tests${NC}"
fi
echo ""

# Summary
echo "================================"
if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL CHECKS PASSED!${NC}"
    echo -e "${GREEN}✅ Code is ready for commit and push${NC}"
else
    echo -e "${RED}💥 SOME CHECKS FAILED!${NC}"
    echo -e "${YELLOW}🔧 Please fix the issues above before committing${NC}"
fi
echo "================================"

exit $CHECKS_FAILED