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
elif [ "$MODE" = "set" ]; then
    echo "Setting peer URL: $PEER_URL"
    python3 -c "
import json, os
config_path = os.path.join('$PROJECT_ROOT', 'peers.json')
with open(config_path, 'w') as f:
    json.dump({'peer_url': '$PEER_URL'}, f)
print('Saved peer URL to peers.json')
"
    exit 0
elif [ -n "$PEER_URL" ]; then
    echo "Peer URL: $PEER_URL"
    python3 -m crosspaste mac-agent --peer-url "$PEER_URL" --port "$PORT"
elif echo "$MODE" | grep -q '^http'; then
    echo "Peer URL: $MODE"
    python3 -m crosspaste mac-agent --peer-url "$MODE" --port "$PORT"
else
    PEER_URL=$(python3 -c "
import json, os, sys
config_path = os.path.join('$PROJECT_ROOT', 'peers.json')
try:
    with open(config_path) as f:
        cfg = json.load(f)
    url = cfg.get('peer_url', '')
    if url:
        print(url)
except:
    pass
" 2>/dev/null)
    if [ -n "$PEER_URL" ]; then
        echo "Using peer URL from peers.json: $PEER_URL"
        python3 -m crosspaste mac-agent --peer-url "$PEER_URL" --port "$PORT"
    else
        echo "No peer configured. Set one with:"
        echo "  $0 set http://<peer-ip>:45892/latest"
        echo "Or use auto-discovery (same subnet only):"
        echo "  $0 auto"
        exit 1
    fi
fi
