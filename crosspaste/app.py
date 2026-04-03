from __future__ import annotations

import argparse
import json
import logging
import socket
import sys
import threading
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib import error, request

from .clipboard import read_local_clipboard_content, write_local_clipboard_content
from .content import ClipboardContent
from .state import ClipboardSnapshot, LatestClipboardState
from .discovery import PeerDiscovery
from .discovery import PeerDiscovery


LOGGER = logging.getLogger("crosspaste")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crosspaste",
        description="Minimal LAN clipboard sync for macOS and Windows.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_server_parser(
        subparsers,
        "mac-server",
        "Run on macOS. Watches the local clipboard and exposes the latest item over HTTP.",
    )
    add_server_parser(
        subparsers,
        "windows-server",
        "Run on Windows. Watches the local clipboard and exposes the latest item over HTTP.",
    )
    add_client_parser(
        subparsers,
        "mac-client",
        "Run on macOS. Polls a peer server and writes new content into the local clipboard.",
    )
    add_client_parser(
        subparsers,
        "windows-client",
        "Run on Windows. Polls a peer server and writes new content into the local clipboard.",
    )
    add_agent_parser(
        subparsers,
        "mac-agent",
        "Run on macOS. Watches the local clipboard, serves it, and also pulls from Windows.",
    )
    add_agent_parser(
        subparsers,
        "windows-agent",
        "Run on Windows. Watches the local clipboard, serves it, and also pulls from macOS.",
    )

    return parser


def add_server_parser(subparsers, name: str, help_text: str) -> None:
    parser = subparsers.add_parser(name, help=help_text)
    parser.add_argument("--host", default="0.0.0.0", help="Bind host for the HTTP server.")
    parser.add_argument("--port", type=int, default=45892, help="Bind port for the HTTP server.")
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.5,
        help="Seconds between clipboard polls on the local machine.",
    )


def add_client_parser(subparsers, name: str, help_text: str) -> None:
    parser = subparsers.add_parser(name, help=help_text)
    parser.add_argument(
        "--server-url",
        required=True,
        help="Peer server URL, for example http://192.168.1.10:45892/latest",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.8,
        help="Seconds between HTTP polls.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=3.0,
        help="HTTP request timeout in seconds.",
    )


def add_agent_parser(subparsers, name: str, help_text: str) -> None:
    parser = subparsers.add_parser(name, help=help_text)
    parser.add_argument("--peer-url", default=None, help="Peer server URL, for example http://192.168.1.10:45892/latest")
    parser.add_argument("--auto-discover", action="store_true", help="Auto-discover peers on the local network via UDP broadcast.")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host for the local HTTP server.")
    parser.add_argument("--port", type=int, default=45892, help="Bind port for the local HTTP server.")
    parser.add_argument(
        "--watch-interval",
        type=float,
        default=0.5,
        help="Seconds between local clipboard polls.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.8,
        help="Seconds between peer HTTP polls.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=3.0,
        help="HTTP request timeout in seconds.",
    )


def run_server(platform_name: str, host: str, port: int, poll_interval: float) -> int:
    validate_platform(platform_name)
    state = LatestClipboardState()
    device_id = build_device_id(platform_name)
    return run_watcher_and_server(
        state=state,
        host=host,
        port=port,
        watch_interval=poll_interval,
        startup_label=f"{platform_name} server",
        local_device_id=device_id,
    )


def run_client(platform_name: str, server_url: str, poll_interval: float, request_timeout: float) -> int:
    validate_platform(platform_name)
    state = LatestClipboardState()
    device_id = build_device_id(platform_name)
    LOGGER.info("%s client polling %s", platform_name.capitalize(), server_url)
    return run_poll_loop(
        state=state,
        server_url=server_url,
        poll_interval=poll_interval,
        request_timeout=request_timeout,
        write_incoming=True,
        local_device_id=device_id,
    )


def run_agent(
    platform_name: str,
    peer_url: Optional[str],
    host: str,
    port: int,
    watch_interval: float,
    poll_interval: float,
    request_timeout: float,
    auto_discover: bool = False,
) -> int:
    validate_platform(platform_name)
    state = LatestClipboardState()
    stop_event = threading.Event()
    device_id = build_device_id(platform_name)

    discovery: Optional[PeerDiscovery] = None
    if auto_discover:
        discovery = PeerDiscovery(port)
        discovery.start()
        LOGGER.info("Auto-discovery started, waiting for peers...")

    server_thread = threading.Thread(
        target=run_server_background,
        kwargs={
            "state": state,
            "host": host,
            "port": port,
            "watch_interval": watch_interval,
            "stop_event": stop_event,
            "startup_label": f"{platform_name} agent",
            "local_device_id": device_id,
        },
        name=f"{platform_name}-agent-server",
        daemon=True,
    )
    server_thread.start()

    actual_peer_url = peer_url
    if auto_discover and not peer_url:
        assert discovery is not None
        LOGGER.info("Waiting for peer discovery (timeout 30s)...")
        found = discovery.wait_for_peer(timeout=30.0)
        LOGGER.info("wait_for_peer returned: %s", found)
        actual_peer_url = discovery.get_peer_url()
        LOGGER.info("get_peer_url returned: %s", actual_peer_url)
        if actual_peer_url:
            LOGGER.info("Auto-discovered peer: %s", actual_peer_url)

    if not actual_peer_url:
        LOGGER.error("No peer URL provided and no peers discovered. Exiting.")
        stop_event.set()
        if discovery:
            discovery.stop()
        return 1

    LOGGER.info("%s agent polling peer %s", platform_name.capitalize(), actual_peer_url)
    try:
        return run_poll_loop(
            state=state,
            server_url=actual_peer_url,
            poll_interval=poll_interval,
            request_timeout=request_timeout,
            write_incoming=True,
            local_device_id=device_id,
        )
    finally:
        stop_event.set()
        if discovery:
            discovery.stop()


def run_watcher_and_server(
    state: LatestClipboardState,
    host: str,
    port: int,
    watch_interval: float,
    startup_label: str,
    local_device_id: str,
) -> int:
    stop_event = threading.Event()
    return run_server_background(
        state=state,
        host=host,
        port=port,
        watch_interval=watch_interval,
        stop_event=stop_event,
        startup_label=startup_label,
        local_device_id=local_device_id,
    )


def run_server_background(
    state: LatestClipboardState,
    host: str,
    port: int,
    watch_interval: float,
    stop_event: threading.Event,
    startup_label: str,
    local_device_id: str,
) -> int:
    watcher_thread = threading.Thread(
        target=watch_local_clipboard,
        kwargs={
            "state": state,
            "stop_event": stop_event,
            "poll_interval": watch_interval,
            "local_device_id": local_device_id,
        },
        name="clipboard-watcher",
        daemon=True,
    )
    watcher_thread.start()

    handler = make_http_handler(state)
    server = ThreadingHTTPServer((host, port), handler)

    LOGGER.info("%s listening on http://%s:%s/latest", startup_label.capitalize(), host, port)

    try:
        while not stop_event.is_set():
            server.timeout = 0.5
            server.handle_request()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down %s.", startup_label)
    finally:
        stop_event.set()
        server.server_close()

    return 0


def watch_local_clipboard(
    state: LatestClipboardState,
    stop_event: threading.Event,
    poll_interval: float,
    local_device_id: str,
) -> None:
    while not stop_event.is_set():
        try:
            content = read_local_clipboard_content()
            if content is not None:
                snapshot = state.update_if_changed(content, local_device_id)
                if snapshot:
                    LOGGER.info(
                        "Captured local clipboard: kind=%s version=%s bytes=%s",
                        content.kind,
                        snapshot.version,
                        len(content.payload_base64),
                    )
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("Clipboard poll failed: %s", exc)

        stop_event.wait(poll_interval)


def make_http_handler(state: LatestClipboardState):
    class LatestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/latest":
                self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                return

            snapshot = state.snapshot()
            if snapshot is None:
                self.send_response(HTTPStatus.NO_CONTENT)
                self.end_headers()
                return

            payload = snapshot_to_wire(snapshot)
            body = json.dumps(payload).encode("utf-8")

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:
            LOGGER.debug("HTTP %s - %s", self.address_string(), fmt % args)

    return LatestHandler


def snapshot_to_wire(snapshot: ClipboardSnapshot) -> dict:
    return {
        "protocolVersion": 2,
        "version": snapshot.version,
        "digest": snapshot.digest,
        "updatedAt": snapshot.updated_at,
        "sourceDeviceId": snapshot.source_device_id,
        "content": snapshot.content.to_wire(),
    }


def run_poll_loop(
    state: LatestClipboardState,
    server_url: str,
    poll_interval: float,
    request_timeout: float,
    write_incoming: bool,
    local_device_id: str,
) -> int:
    last_seen_remote_digest: Optional[str] = None
    LOGGER.info("Starting poll loop, peer=%s, interval=%.1fs", server_url, poll_interval)

    while True:
        try:
            snapshot = fetch_latest_snapshot(server_url, request_timeout)
            if snapshot is None:
                LOGGER.debug("Peer returned no content")
                time.sleep(poll_interval)
                continue

            LOGGER.debug(
                "Peer snapshot: kind=%s version=%s digest=%s source=%s",
                snapshot.content.kind,
                snapshot.version,
                snapshot.digest[:8],
                snapshot.source_device_id[:12],
            )

            if snapshot.digest == last_seen_remote_digest:
                time.sleep(poll_interval)
                continue

            last_seen_remote_digest = snapshot.digest

            if snapshot.source_device_id == local_device_id:
                LOGGER.debug("Skipping content from self")
                time.sleep(poll_interval)
                continue

            if snapshot.content.kind not in ("text", "image"):
                LOGGER.info(
                    "Peer sent unsupported clipboard kind '%s'. Skipping.",
                    snapshot.content.kind,
                )
                time.sleep(poll_interval)
                continue

            state.update_if_changed(snapshot.content, snapshot.source_device_id)
            if write_incoming:
                write_local_clipboard_content(snapshot.content)
                LOGGER.info(
                    "Applied peer clipboard: kind=%s version=%s bytes=%s",
                    snapshot.content.kind,
                    snapshot.version,
                    len(snapshot.content.payload_base64),
                )
        except KeyboardInterrupt:
            LOGGER.info("Stopping poll loop.")
            return 0
        except Exception as exc:
            LOGGER.warning("Poll failed: %s", exc)

        time.sleep(poll_interval)


def fetch_latest_snapshot(server_url: str, request_timeout: float) -> Optional[ClipboardSnapshot]:
    req = request.Request(server_url, method="GET")

    try:
        with request.urlopen(req, timeout=request_timeout) as resp:
            if resp.status == HTTPStatus.NO_CONTENT:
                return None

            raw = resp.read()
    except error.HTTPError as exc:
        if exc.code == HTTPStatus.NO_CONTENT:
            return None
        raise

    payload = json.loads(raw.decode("utf-8"))
    content = ClipboardContent.from_wire(payload["content"])

    return ClipboardSnapshot(
        version=int(payload["version"]),
        content=content,
        digest=str(payload["digest"]),
        updated_at=float(payload["updatedAt"]),
        source_device_id=str(payload.get("sourceDeviceId", "")),
    )


def build_device_id(platform_name: str) -> str:
    return f"{platform_name}-{socket.gethostname()}-{uuid.uuid4().hex[:8]}"


def validate_platform(platform_name: str) -> None:
    if platform_name == "mac" and sys.platform != "darwin":
        raise SystemExit("This command must run on macOS.")

    if platform_name == "windows" and sys.platform != "win32":
        raise SystemExit("This command must run on Windows.")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def main() -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "mac-server":
        return run_server("mac", args.host, args.port, args.poll_interval)

    if args.command == "windows-server":
        return run_server("windows", args.host, args.port, args.poll_interval)

    if args.command == "mac-client":
        return run_client("mac", args.server_url, args.poll_interval, args.request_timeout)

    if args.command == "windows-client":
        return run_client("windows", args.server_url, args.poll_interval, args.request_timeout)

    if args.command == "mac-agent":
        return run_agent(
            "mac",
            args.peer_url,
            args.host,
            args.port,
            args.watch_interval,
            args.poll_interval,
            args.request_timeout,
            args.auto_discover,
        )

    if args.command == "windows-agent":
        return run_agent(
            "windows",
            args.peer_url,
            args.host,
            args.port,
            args.watch_interval,
            args.poll_interval,
            args.request_timeout,
            args.auto_discover,
        )

    if args.command == "windows-agent":
        return run_agent(
            "windows",
            args.peer_url,
            args.host,
            args.port,
            args.watch_interval,
            args.poll_interval,
            args.request_timeout,
            args.auto_discover,
        )

    parser.error("unknown command")
    return 2
