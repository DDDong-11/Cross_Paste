#!/bin/sh

MODE="${1:-}"
PEER_URL="${2:-}"
PORT="${3:-45892}"

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"

echo "CrossPaste Mac agent starting..."
echo "Local port: $PORT"
echo "Project root: $PROJECT_ROOT"

cd "$PROJECT_ROOT" || exit 1

if [ "$MODE" = "auto" ]; then
    echo "Auto-discovery mode..."
    python3 -m crosspaste mac-agent --auto-discover --port "$PORT"
elif [ -n "$PEER_URL" ]; then
    echo "Peer URL: $PEER_URL"
    python3 -m crosspaste mac-agent --peer-url "$PEER_URL" --port "$PORT"
elif echo "$MODE" | grep -q '^http'; then
    echo "Peer URL: $MODE"
    python3 -m crosspaste mac-agent --peer-url "$MODE" --port "$PORT"
else
    echo "Usage: $0 auto"
    echo "   or: $0 http://<peer-ip>:45892/latest [port]"
    exit 1
fi
