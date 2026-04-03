#!/bin/sh

PEER_URL="${1:-}"
PORT="${2:-45892}"

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"

echo "CrossPaste Mac agent starting..."
echo "Local port: $PORT"
echo "Project root: $PROJECT_ROOT"

cd "$PROJECT_ROOT" || exit 1

if [ -n "$PEER_URL" ]; then
    echo "Peer URL: $PEER_URL"
    python3 -m crosspaste mac-agent --peer-url "$PEER_URL" --port "$PORT"
else
    echo "Auto-discovery mode (may not work across subnets)..."
    python3 -m crosspaste mac-agent --auto-discover --port "$PORT"
fi
