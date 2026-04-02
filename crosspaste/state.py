from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import time
from typing import Optional

from .content import ClipboardContent


@dataclass(frozen=True)
class ClipboardSnapshot:
    version: int
    content: ClipboardContent
    digest: str
    updated_at: float


class LatestClipboardState:
    def __init__(self) -> None:
        self._lock = Lock()
        self._version = 0
        self._content: Optional[ClipboardContent] = None
        self._digest = ""
        self._updated_at = 0.0

    def update_if_changed(self, content: ClipboardContent) -> Optional[ClipboardSnapshot]:
        digest = content.digest()

        with self._lock:
            if digest == self._digest:
                return None

            self._version += 1
            self._content = content
            self._digest = digest
            self._updated_at = time()
            return ClipboardSnapshot(
                version=self._version,
                content=content,
                digest=self._digest,
                updated_at=self._updated_at,
            )

    def snapshot(self) -> Optional[ClipboardSnapshot]:
        with self._lock:
            if self._version == 0 or self._content is None:
                return None

            return ClipboardSnapshot(
                version=self._version,
                content=self._content,
                digest=self._digest,
                updated_at=self._updated_at,
            )

    def current_digest(self) -> Optional[str]:
        with self._lock:
            if self._version == 0:
                return None

            return self._digest
