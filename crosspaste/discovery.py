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
HELLO_MSG = b"crosspaste-hello"
ACK_MSG = b"crosspaste-ack"


class PeerDiscovery:
    def __init__(self, port: int, hostname: Optional[str] = None) -> None:
        self.port = port
        self.hostname = hostname or socket.gethostname()
        self._known_peers: dict[str, float] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._sock: Optional[socket.socket] = None

    def start(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("", DISCOVERY_PORT))
        self._sock.settimeout(1.0)

        send_thread = threading.Thread(target=self._send_loop, daemon=True, name="discovery-send")
        recv_thread = threading.Thread(target=self._recv_loop, daemon=True, name="discovery-recv")
        send_thread.start()
        recv_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._sock:
            self._sock.close()

    def get_known_peers(self) -> list[str]:
        cutoff = time.time() - (BROADCAST_INTERVAL * 3)
        with self._lock:
            active = {ip: ts for ip, ts in self._known_peers.items() if ts > cutoff}
            self._known_peers = active
        return list(active.keys())

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

            if data == HELLO_MSG:
                reply = json.dumps({"type": "ack", "port": self.port, "host": self.hostname}).encode()
                try:
                    self._sock.sendto(reply, (addr[0], DISCOVERY_PORT))
                except OSError:
                    pass
                continue

            if data == ACK_MSG:
                continue

            try:
                payload = json.loads(data.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

            if payload.get("type") in ("hello", "ack"):
                peer_ip = addr[0]
                peer_port = payload.get("port", self.port)
                with self._lock:
                    self._known_peers[peer_ip] = time.time()
                LOGGER.info("Discovered peer: %s:%s", peer_ip, peer_port)
