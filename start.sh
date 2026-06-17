#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

PORT="${PORT:-23457}"
MODE="${1:-tui}"

BANNER="Formbricks Studio by MG"

if [ "$MODE" = "web" ] || [ "$MODE" = "serve" ]; then
    echo "🌐 $BANNER — Web UI at http://localhost:$PORT"
    echo "   Opening browser..."
    python3 -c "import webbrowser; webbrowser.open('http://localhost:$PORT')" 2>/dev/null || true
    python3 main.py serve
elif [ "$MODE" = "tui" ]; then
    echo "🖥️  $BANNER — TUI"
    python3 main.py
else
    echo "Usage: ./start.sh [tui|web]"
    echo ""
    echo "  tui   - Interactive terminal UI (default)"
    echo "  web   - Web UI (opens browser automatically)"
    exit 1
fi
