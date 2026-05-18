#!/usr/bin/env bash
# check_ai_research.sh — Verify AI research layer config and status on the VPS.
#
# Usage:
#   bash deploy/vps/check_ai_research.sh [INSTALL_DIR]
#
# INSTALL_DIR defaults to /opt/ma-scanner.

set -uo pipefail

INSTALL_DIR="${1:-/opt/ma-scanner}"
ENV_FILE="${INSTALL_DIR}/config/.env"
SUMMARY="${INSTALL_DIR}/data/ai_research/latest_ai_research_summary.md"
WATCHLIST="${INSTALL_DIR}/data/ai_research/watchlist.json"

echo "=== AI Research Layer Check ==="
echo "  Install dir : ${INSTALL_DIR}"
echo ""

# 1. Check env file
echo "[1/4] Config file: ${ENV_FILE}"
if [[ -f "${ENV_FILE}" ]]; then
    echo "      exists"
    ENABLED=$(grep -E '^AI_RESEARCH_ENABLED=' "${ENV_FILE}" | cut -d= -f2 | tr -d '"' || true)
    KEY_SET=$(grep -E '^OPENAI_API_KEY=' "${ENV_FILE}" | cut -d= -f2 | tr -d '"' || true)
    MODEL=$(grep -E '^AI_MODEL=' "${ENV_FILE}" | cut -d= -f2 | tr -d '"' || true)
    DRY_RUN=$(grep -E '^AI_RESEARCH_DRY_RUN=' "${ENV_FILE}" | cut -d= -f2 | tr -d '"' || true)

    echo "      AI_RESEARCH_ENABLED : ${ENABLED:-not set}"
    echo "      OPENAI_API_KEY set  : $([ -n "${KEY_SET}" ] && echo yes || echo NO)"
    echo "      AI_MODEL            : ${MODEL:-not set (default: gpt-4.1-mini)}"
    echo "      AI_RESEARCH_DRY_RUN : ${DRY_RUN:-not set (default: true)}"
else
    echo "      MISSING — copy config/.env.example to config/.env and fill in values"
fi

echo ""

# 2. Python status command
echo "[2/4] AI research layer --status:"
cd "${INSTALL_DIR}"
python3 src/ai_research/run_ai_research.py --status 2>&1 || true

echo ""

# 3. Latest summary
echo "[3/4] Latest summary: ${SUMMARY}"
if [[ -f "${SUMMARY}" ]]; then
    MTIME=$(stat -c '%y' "${SUMMARY}" 2>/dev/null || stat -f '%Sm' "${SUMMARY}" 2>/dev/null || echo "unknown")
    echo "      Last modified: ${MTIME}"
    head -20 "${SUMMARY}"
else
    echo "      Not found — run: python3 src/ai_research/run_ai_research.py --latest --dry-run"
fi

echo ""

# 4. Watchlist
echo "[4/4] Watchlist: ${WATCHLIST}"
if [[ -f "${WATCHLIST}" ]]; then
    ENTRIES=$(python3 -c "import json; d=json.load(open('${WATCHLIST}')); print(len(d))" 2>/dev/null || echo "?")
    echo "      ${ENTRIES} ticker(s) in watchlist"
else
    echo "      Not found — no AI runs completed yet"
fi

echo ""
echo "To run the AI layer (dry-run safe):"
echo "  cd ${INSTALL_DIR}"
echo "  python3 src/ai_research/run_ai_research.py --latest --dry-run"
echo ""
echo "To enable live LLM gating, set in config/.env:"
echo "  AI_RESEARCH_ENABLED=true"
echo "  OPENAI_API_KEY=sk-..."
echo "  AI_RESEARCH_DRY_RUN=false"
