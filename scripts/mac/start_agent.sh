#!/bin/sh

MODE="${1:-auto}"
PEER_URL="${2:-}"
PORT="${3:-45892}"

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"

echo "CrossPaste Mac agent starting..."
echo "Mode: $MODE"
echo "Local port: $PORT"
echo "Project root: $PROJECT_ROOT"

cd "$PROJECT_ROOT" || exit 1

if [ "$MODE" = "auto" ]; then
    echo "Auto-discovery: enabled"
    python3 -m crosspaste mac-agent --auto-discover --port "$PORT"
elif [ -n "$PEER_URL" ]; then
    echo "Peer URL: $PEER_URL"
    python3 -m crosspaste mac-agent --peer-url "$PEER_URL" --port "$PORT"
else
    echo "Error: specify peer URL or use 'auto' mode"
    echo "Usage: $0 [auto|<peer-url>] [port]"
    exit 1
fi
else
    echo "Error: specify peer URL or use 'auto' mode"
    echo "Usage: $0 [auto|<peer-url>] [port]"
    exit 1
fi
else
    echo "Error: specify peer URL or use 'auto' mode"
    echo "Usage: $0 [auto|<peer-url>] [port]"
    exit 1
fi
