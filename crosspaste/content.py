from __future__ import annotations

import base64
from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class ClipboardContent:
    kind: str
    mime_type: str
    encoding: str
    payload_base64: str

    MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB

    @classmethod
    def from_text(cls, text: str) -> "ClipboardContent":
        normalized = text.replace("\r\n", "\n")
        payload = base64.b64encode(normalized.encode("utf-8")).decode("ascii")
        return cls(
            kind="text",
            mime_type="text/plain; charset=utf-8",
            encoding="base64",
            payload_base64=payload,
        )

    @classmethod
    def from_image(cls, image_bytes: bytes, mime_type: str = "image/png") -> "ClipboardContent":
        if len(image_bytes) > cls.MAX_IMAGE_BYTES:
            raise ValueError(
                f"Image size {len(image_bytes)} bytes exceeds maximum size {cls.MAX_IMAGE_BYTES} bytes"
            )
        payload = base64.b64encode(image_bytes).decode("ascii")
        return cls(
            kind="image",
            mime_type=mime_type,
            encoding="base64",
            payload_base64=payload,
        )
        payload = base64.b64encode(image_bytes).decode("ascii")
        return cls(
            kind="image",
            mime_type=mime_type,
            encoding="base64",
            payload_base64=payload,
        )
        payload = base64.b64encode(image_bytes).decode("ascii")
        return cls(
            kind="image",
            mime_type=mime_type,
            encoding="base64",
            payload_base64=payload,
        )

    def to_wire(self) -> dict:
        payload_bytes = base64.b64decode(self.payload_base64.encode("ascii"))
        preview = ""
        if self.kind == "text":
            preview = payload_bytes.decode("utf-8", errors="replace")[:80]

        return {
            "kind": self.kind,
            "mimeType": self.mime_type,
            "encoding": self.encoding,
            "payloadBase64": self.payload_base64,
            "size": len(payload_bytes),
            "preview": preview,
        }

    @classmethod
    def from_wire(cls, payload: dict) -> "ClipboardContent":
        return cls(
            kind=payload["kind"],
            mime_type=payload["mimeType"],
            encoding=payload["encoding"],
            payload_base64=payload["payloadBase64"],
        )

    def to_text(self) -> str:
        if self.kind != "text":
            raise ValueError(f"Unsupported clipboard content kind: {self.kind}")

        return base64.b64decode(self.payload_base64.encode("ascii")).decode("utf-8", errors="replace")

    def to_image_bytes(self) -> bytes:
        if self.kind != "image":
            raise ValueError(f"Clipboard content is not an image, kind: {self.kind}")

        return base64.b64decode(self.payload_base64.encode("ascii"))

    def digest(self) -> str:
        material = "\0".join(
            [
                self.kind,
                self.mime_type,
                self.encoding,
                self.payload_base64,
            ]
        )
        return sha256(material.encode("utf-8")).hexdigest()
