from __future__ import annotations

import logging
import socket
import struct
import threading
import time
from typing import Optional

LOGGER = logging.getLogger("crosspaste.discovery")

DISCOVERY_PORT = 45893
SCAN_INTERVAL = 10.0


def _get_local_ips() -> list[str]:
    ips = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET, socket.SOCK_DGRAM):
            ips.append(info[4][0])
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 53))
        ips.append(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    return ips


def _generate_scan_targets(local_ips: list[str]) -> list[str]:
    targets = set()
    for ip in local_ips:
        parts = ip.split(".")
        if len(parts) == 4:
            subnet = ".".join(parts[:3])
            for i in range(1, 255):
                targets.add(f"{subnet}.{i}")
    return sorted(targets)


class PeerDiscovery:
    def __init__(self, port: int, hostname: Optional[str] = None) -> None:
        self.port = port
        self.hostname = hostname or socket.gethostname()
        self._known_peers: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._peer_found_event = threading.Event()
        self._local_ips = _get_local_ips()
        self._scan_targets = _generate_scan_targets(self._local_ips)
        LOGGER.info("Local IPs: %s", self._local_ips)
        LOGGER.info("Will scan %d addresses for peers", len(self._scan_targets))

    def start(self) -> None:
        threading.Thread(target=self._scan_loop, daemon=True, name="discovery-scan").start()

    def stop(self) -> None:
        self._stop_event.set()

    def wait_for_peer(self, timeout: Optional[float] = None) -> bool:
        return self._peer_found_event.wait(timeout=timeout)

    def get_peer_url(self) -> Optional[str]:
        cutoff = time.time() - (SCAN_INTERVAL * 3)
        with self._lock:
            for ip, info in self._known_peers.items():
                if info["ts"] > cutoff:
                    return f"http://{ip}:{info['port']}/latest"
        return None

    def _scan_loop(self) -> None:
        while not self._stop_event.is_set():
            self._scan_once()
            self._stop_event.wait(SCAN_INTERVAL)

    def _scan_once(self) -> None:
        for target_ip in self._scan_targets:
            if self._stop_event.is_set():
                return
            if target_ip in self._local_ips:
                continue
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.5)
                result = s.connect_ex((target_ip, self.port))
                s.close()
                if result == 0:
                    with self._lock:
                        self._known_peers[target_ip] = {"port": self.port, "ts": time.time()}
                    self._peer_found_event.set()
                    LOGGER.info("Discovered peer: %s:%s", target_ip, self.port)
            except OSError:
                pass
