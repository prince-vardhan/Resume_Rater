#!/usr/bin/env bash
# One-command setup + run for the Smart Shortlisting Engine.
#
# Usage:
#   ./run.sh            -> sets up the venv/deps, then ranks whatever PDFs
#                          are in data/jd/ and data/resumes/ and prints JSON
#   ./run.sh api         -> sets up, then starts the FastAPI server
#   ./run.sh ui          -> sets up, then starts the Streamlit demo
#   ./run.sh test         -> sets up, then runs the pytest suite
#
# Safe to re-run: venv creation and pip install are skipped if already done.

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

MODE="${1:-cli}"
VENV_DIR="venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "==> Creating virtual environment in $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

INSTALLED_MARKER="$VENV_DIR/.requirements_installed"
if [ ! -f "$INSTALLED_MARKER" ] || [ requirements.txt -nt "$INSTALLED_MARKER" ]; then
    echo "==> Installing dependencies (first run downloads the embedding model on first use) ..."
    pip install --upgrade pip --quiet
    pip install -r requirements.txt
    touch "$INSTALLED_MARKER"
else
    echo "==> Dependencies already installed, skipping."
fi

case "$MODE" in
    cli)
        JD_FILE=$(find data/jd -maxdepth 1 -name '*.pdf' | head -n 1 || true)
        RESUME_FILES=$(find data/resumes -maxdepth 1 -name '*.pdf' || true)

        if [ -z "$JD_FILE" ] || [ -z "$RESUME_FILES" ]; then
            echo ""
            echo "No JD/resume PDFs found."
            echo "  Put one job description PDF in:  data/jd/"
            echo "  Put your resume PDFs in:          data/resumes/"
            echo "Then re-run ./run.sh"
            exit 1
        fi

        echo "==> Ranking $(echo "$RESUME_FILES" | wc -l | tr -d ' ') resume(s) against $JD_FILE ..."
        python3 -c "
from src.pipeline import run_pipeline
import glob, json
result = run_pipeline('$JD_FILE', glob.glob('data/resumes/*.pdf'))
print(json.dumps(result, indent=2))
"
        ;;
    api)
        echo "==> Starting API on http://localhost:8000 (POST /rank) ..."
        uvicorn api.main:app --reload --port 8000
        ;;
    ui)
        echo "==> Starting Streamlit UI ..."
        streamlit run ui/app.py
        ;;
    test)
        echo "==> Running tests ..."
        pytest tests/ -v
        ;;
    *)
        echo "Unknown mode: $MODE"
        echo "Usage: ./run.sh [cli|api|ui|test]"
        exit 1
        ;;
esac
