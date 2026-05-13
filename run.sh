#!/usr/bin/env bash
# Run the Political Compass Test evaluation.
# Works in Google Colab (pip) and locally (conda).
#
# Usage:
#   bash run.sh [--model MODEL_ID] [--output FILE] [--device DEVICE]
#
# Examples:
#   bash run.sh
#   bash run.sh --output results.json
#   bash run.sh --model talkie-lm/talkie-1930-13b-base --output results.json

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Install dependencies ────────────────────────────────────────────────────
if [ -n "${CONDA_DEFAULT_ENV:-}" ]; then
    echo "[run.sh] conda env: $CONDA_DEFAULT_ENV"
    pip install -q -r requirements.txt
elif command -v conda &>/dev/null; then
    echo "[run.sh] activating conda env llm-politics"
    # shellcheck disable=SC1091
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate llm-politics 2>/dev/null || conda run -n llm-politics pip install -q -r requirements.txt
else
    echo "[run.sh] no conda found, installing with pip"
    pip install -q --force-reinstall -r requirements.txt
fi

# ── Run evaluation ──────────────────────────────────────────────────────────
python evaluate.py "$@"
