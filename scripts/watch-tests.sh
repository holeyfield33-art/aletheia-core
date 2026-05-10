#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Aletheia Core — CI Test Watch & Auto-Repair Script
#
# Usage:
#   ./scripts/watch-tests.sh                 # Run once
#   ./scripts/watch-tests.sh --watch         # Watch mode (re-run on file changes)
#   ./scripts/watch-tests.sh --quick         # Quick mode (core tests only)
#   ./scripts/watch-tests.sh --fix           # Attempt auto-fixes
#
# Watches tests continuously and alerts on failures
# Creates reports in .ci-reports/ directory

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${REPO_ROOT}/.ci-reports"
WATCH_INTERVAL=5
QUICK_MODE=0
AUTO_FIX=0
WATCH_MODE=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --watch) WATCH_MODE=1; shift ;;
        --quick) QUICK_MODE=1; shift ;;
        --fix) AUTO_FIX=1; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

init_report_dir() {
    mkdir -p "${REPORT_DIR}"
    touch "${REPORT_DIR}/.gitkeep"
}

print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Aletheia Core — CI Test Suite${NC}"
    echo -e "${BLUE}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

run_linting() {
    echo -e "\n${YELLOW}[1/4]${NC} Running linting checks..."
    if cd "${REPO_ROOT}" && python -m ruff check --select=E,W,F tests/ core/ agents/ bridge/ 2>&1 | tee -a "${REPORT_DIR}/lint.log"; then
        echo -e "${GREEN}✓ Linting passed${NC}"
        return 0
    else
        echo -e "${RED}✗ Linting failed${NC}"
        return 1
    fi
}

run_type_check() {
    echo -e "\n${YELLOW}[2/4]${NC} Running type checks (mypy)..."
    if cd "${REPO_ROOT}" && python -m mypy core/ agents/ bridge/ --ignore-missing-imports 2>&1 | tee -a "${REPORT_DIR}/types.log"; then
        echo -e "${GREEN}✓ Type check passed${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Type check warnings (non-blocking)${NC}"
        return 0  # Non-blocking for now
    fi
}

run_quick_tests() {
    echo -e "\n${YELLOW}[3/4]${NC} Running core tests (quick mode)..."
    cd "${REPO_ROOT}"
    python -m pytest \
        tests/test_config.py \
        tests/test_manifest_cache.py \
        tests/test_embeddings.py \
        tests/test_semantic_manifest.py \
        -v --tb=short --timeout=10 2>&1 | tee -a "${REPORT_DIR}/tests-quick.log"
}

run_full_tests() {
    echo -e "\n${YELLOW}[3/4]${NC} Running full test suite..."
    cd "${REPO_ROOT}"

    # Run tests in parallel where possible
    python -m pytest \
        tests/ \
        -v \
        --tb=short \
        --timeout=30 \
        -n auto \
        --dist loadscope \
        2>&1 | tee "${REPORT_DIR}/tests-full.log"
}

run_security_checks() {
    echo -e "\n${YELLOW}[4/4]${NC} Running security checks..."

    # Check for hardcoded secrets
    if cd "${REPO_ROOT}" && grep -r "password\|api_key\|secret" --include="*.py" core/ agents/ bridge/ 2>/dev/null | grep -v "# noqa" | grep -v test | head -5 > "${REPORT_DIR}/secrets.log"; then
        if [ -s "${REPORT_DIR}/secrets.log" ]; then
            echo -e "${YELLOW}⚠ Potential hardcoded secrets found:${NC}"
            head -5 "${REPORT_DIR}/secrets.log"
            return 1
        fi
    fi

    echo -e "${GREEN}✓ Security checks passed${NC}"
    return 0
}

generate_report() {
    local report_file="${REPORT_DIR}/test-report-$(date +%s).md"

    cat > "${report_file}" << 'EOF'
# Aletheia Core — Test Report

## Summary

EOF

    # Count test results
    if [ -f "${REPORT_DIR}/tests-full.log" ]; then
        local passed=$(grep -c "PASSED" "${REPORT_DIR}/tests-full.log" || echo 0)
        local failed=$(grep -c "FAILED" "${REPORT_DIR}/tests-full.log" || echo 0)
        echo "- **Passed**: $passed" >> "${report_file}"
        echo "- **Failed**: $failed" >> "${report_file}"
    fi

    echo "" >> "${report_file}"
    echo "## Test Results Details" >> "${report_file}"
    echo "" >> "${report_file}"

    if [ -f "${REPORT_DIR}/tests-full.log" ]; then
        echo '```' >> "${report_file}"
        tail -50 "${REPORT_DIR}/tests-full.log" >> "${report_file}"
        echo '```' >> "${report_file}"
    fi

    echo -e "\n${BLUE}Report generated: ${report_file}${NC}"
}

run_once() {
    init_report_dir
    print_header

    local failed=0

    run_linting || failed=$((failed + 1))
    run_type_check || failed=$((failed + 1))

    if [ $QUICK_MODE -eq 1 ]; then
        run_quick_tests || failed=$((failed + 1))
    else
        run_full_tests || failed=$((failed + 1))
    fi

    run_security_checks || failed=$((failed + 1))

    generate_report

    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}✓ All checks passed!${NC}"
        return 0
    else
        echo -e "${RED}✗ $failed check(s) failed${NC}"
        return 1
    fi
}

watch_mode() {
    echo -e "${BLUE}Watching for file changes...${NC}"
    echo "Press Ctrl+C to stop"

    local last_run=0

    while true; do
        # Check if any Python files have changed
        local current_hash=$(find "${REPO_ROOT}/core" "${REPO_ROOT}/agents" "${REPO_ROOT}/bridge" "${REPO_ROOT}/tests" -name "*.py" -type f -newer "${REPORT_DIR}/.watch-marker" 2>/dev/null | wc -l)

        if [ "$current_hash" -gt 0 ] || [ $last_run -eq 0 ]; then
            clear
            run_once
            last_run=$((last_run + 1))
            touch "${REPORT_DIR}/.watch-marker"
        fi

        sleep $WATCH_INTERVAL
    done
}

# Main
if [ $WATCH_MODE -eq 1 ]; then
    watch_mode
else
    run_once
fi
