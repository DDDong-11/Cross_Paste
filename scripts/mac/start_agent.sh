#!/bin/sh

PEER_URL="${1:-http://192.168.1.24:45892/latest}"
PORT="${2:-45892}"

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"

echo "CrossPaste Mac agent starting..."
echo "Peer URL: $PEER_URL"
echo "Local port: $PORT"
echo "Project root: $PROJECT_ROOT"

cd "$PROJECT_ROOT" || exit 1
python3 -m crosspaste mac-agent --peer-url "$PEER_URL" --port "$PORT"

