from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from threading import Lock
from time import time
from typing import Optional


@dataclass(frozen=True)
class ClipboardSnapshot:
    version: int
    text: str
    digest: str
    updated_at: float


class LatestClipboardState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._version = 0
        self._text = ""
        self._digest = ""
        self._updated_at = 0.0

    def update_if_changed(self, text: str) -> Optional[ClipboardSnapshot]:
        normalized = text.replace("\r\n", "\n")
        digest = sha256(normalized.encode("utf-8")).hexdigest()

        with self._lock:
            if digest == self._digest:
                return None

            self._version += 1
            self._text = normalized
            self._digest = digest
            self._updated_at = time()
            return ClipboardSnapshot(
                version=self._version,
                text=self._text,
                digest=self._digest,
                updated_at=self._updated_at,
            )

    def snapshot(self) -> Optional[ClipboardSnapshot]:
        with self._lock:
            if self._version == 0:
                return None

            return ClipboardSnapshot(
                version=self._version,
                text=self._text,
                digest=self._digest,
                updated_at=self._updated_at,
            )

