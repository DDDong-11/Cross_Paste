from __future__ import annotations

import json
import logging
import socket
import threading
import time
from typing import Optional

LOGGER = logging.getLogger("crosspaste.discovery")

DISCOVERY_PORT = 45893
BROADCAST_INTERVAL = 5.0
BROADCAST_ADDR = "<broadcast>"


class PeerDiscovery:
    def __init__(self, port: int, hostname: Optional[str] = None) -> None:
        self.port = port
        self.hostname = hostname or socket.gethostname()
        self._known_peers: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._peer_found_event = threading.Event()
        self._sock: Optional[socket.socket] = None

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("", DISCOVERY_PORT))
        self._sock.settimeout(1.0)

        threading.Thread(target=self._send_loop, daemon=True, name="discovery-send").start()
        threading.Thread(target=self._recv_loop, daemon=True, name="discovery-recv").start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._sock:
            self._sock.close()

    def wait_for_peer(self, timeout: Optional[float] = None) -> bool:
        return self._peer_found_event.wait(timeout=timeout)

    def get_peer_url(self) -> Optional[str]:
        cutoff = time.time() - (BROADCAST_INTERVAL * 3)
        with self._lock:
            for ip, info in self._known_peers.items():
                if info["ts"] > cutoff:
                    return f"http://{ip}:{info['port']}/latest"
        return None

    def _send_loop(self) -> None:
        assert self._sock is not None
        msg = json.dumps({"type": "hello", "port": self.port, "host": self.hostname}).encode()
        while not self._stop_event.is_set():
            try:
                self._sock.sendto(msg, (BROADCAST_ADDR, DISCOVERY_PORT))
            except OSError:
                pass
            self._stop_event.wait(BROADCAST_INTERVAL)

    def _recv_loop(self) -> None:
        assert self._sock is not None
        while not self._stop_event.is_set():
            try:
                data, addr = self._sock.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                payload = json.loads(data.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

            if payload.get("type") in ("hello", "ack"):
                peer_ip = addr[0]
                peer_port = payload.get("port", self.port)
                with self._lock:
                    self._known_peers[peer_ip] = {"port": peer_port, "ts": time.time()}
                self._peer_found_event.set()
                LOGGER.info("Discovered peer: %s:%s", peer_ip, peer_port)

                if payload.get("type") == "hello":
                    reply = json.dumps({"type": "ack", "port": self.port, "host": self.hostname}).encode()
                    try:
                        self._sock.sendto(reply, (peer_ip, DISCOVERY_PORT))
                    except OSError:
                        pass
