from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib import error, request

from .clipboard import read_macos_clipboard_text, write_windows_clipboard_text
from .state import LatestClipboardState


LOGGER = logging.getLogger("crosspaste")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crosspaste",
        description="Minimal LAN clipboard sync for Mac to Windows text copy/paste.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    mac_server = subparsers.add_parser(
        "mac-server",
        help="Run on macOS. Watches the local clipboard and exposes the latest text over HTTP.",
    )
    mac_server.add_argument("--host", default="0.0.0.0", help="Bind host for the HTTP server.")
    mac_server.add_argument("--port", type=int, default=45892, help="Bind port for the HTTP server.")
    mac_server.add_argument(
        "--poll-interval",
        type=float,
        default=0.5,
        help="Seconds between clipboard polls on macOS.",
    )

    windows_client = subparsers.add_parser(
        "windows-client",
        help="Run on Windows. Polls the macOS server and writes new text into the local clipboard.",
    )
    windows_client.add_argument(
        "--server-url",
        required=True,
        help="Mac server URL, for example http://192.168.1.10:45892/latest",
    )
    windows_client.add_argument(
        "--poll-interval",
        type=float,
        default=0.8,
        help="Seconds between HTTP polls from Windows.",
    )
    windows_client.add_argument(
        "--request-timeout",
        type=float,
        default=3.0,
        help="HTTP request timeout in seconds.",
    )

    return parser


def run_mac_server(host: str, port: int, poll_interval: float) -> int:
    if sys.platform != "darwin":
        LOGGER.error("mac-server must run on macOS.")
        return 1

    state = LatestClipboardState()
    stop_event = threading.Event()

    def watcher() -> None:
        while not stop_event.is_set():
            try:
                text = read_macos_clipboard_text()
                if text:
                    snapshot = state.update_if_changed(text)
                    if snapshot:
                        LOGGER.info(
                            "Captured new clipboard text: version=%s chars=%s",
                            snapshot.version,
                            len(snapshot.text),
                        )
            except Exception as exc:  # pragma: no cover - defensive logging for local OS calls
                LOGGER.warning("Clipboard poll failed: %s", exc)

            stop_event.wait(poll_interval)

    handler = make_http_handler(state)
    server = ThreadingHTTPServer((host, port), handler)
    watcher_thread = threading.Thread(target=watcher, name="clipboard-watcher", daemon=True)
    watcher_thread.start()

    LOGGER.info("Mac server listening on http://%s:%s/latest", host, port)
    LOGGER.info("Use your Mac LAN IP from the Windows machine, for example http://192.168.x.x:%s/latest", port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down mac server.")
    finally:
        stop_event.set()
        server.shutdown()
        server.server_close()

    return 0


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

            payload = {
                "version": snapshot.version,
                "digest": snapshot.digest,
                "text": snapshot.text,
                "updatedAt": snapshot.updated_at,
            }
            body = json.dumps(payload).encode("utf-8")

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:
            LOGGER.debug("HTTP %s - %s", self.address_string(), fmt % args)

    return LatestHandler


def run_windows_client(server_url: str, poll_interval: float, request_timeout: float) -> int:
    if sys.platform != "win32":
        LOGGER.error("windows-client must run on Windows.")
        return 1

    last_digest: Optional[str] = None

    LOGGER.info("Windows client polling %s", server_url)

    while True:
        try:
            snapshot = fetch_latest_snapshot(server_url, request_timeout)
            if snapshot is None:
                time.sleep(poll_interval)
                continue

            digest = snapshot["digest"]
            text = snapshot["text"]
            version = snapshot["version"]

            if digest != last_digest:
                write_windows_clipboard_text(text)
                last_digest = digest
                LOGGER.info("Updated Windows clipboard: version=%s chars=%s", version, len(text))
        except KeyboardInterrupt:
            LOGGER.info("Stopping Windows client.")
            return 0
        except Exception as exc:  # pragma: no cover - defensive logging for network/OS calls
            LOGGER.warning("Poll failed: %s", exc)

        time.sleep(poll_interval)


def fetch_latest_snapshot(server_url: str, request_timeout: float) -> Optional[dict]:
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
    if not isinstance(payload.get("text"), str):
        raise ValueError("Server returned invalid text payload")

    return payload


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
        return run_mac_server(args.host, args.port, args.poll_interval)

    if args.command == "windows-client":
        return run_windows_client(args.server_url, args.poll_interval, args.request_timeout)

    parser.error("unknown command")
    return 2

