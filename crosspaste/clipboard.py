from __future__ import annotations

import base64
import subprocess
import sys
from typing import Optional

from .content import ClipboardContent


def read_macos_clipboard_content() -> Optional[ClipboardContent]:
    result = subprocess.run(
        ["pbpaste"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or "pbpaste failed")

    text = result.stdout.decode("utf-8", errors="replace")
    if not text:
        return None

    return ClipboardContent.from_text(text)


def write_macos_clipboard_content(content: ClipboardContent) -> None:
    text = content.to_text()
    result = subprocess.run(
        ["pbcopy"],
        input=text.encode("utf-8"),
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or "pbcopy failed")


def read_windows_clipboard_content() -> Optional[ClipboardContent]:
    script = (
        "$clipboard = Get-Clipboard -Raw; "
        "if ($null -eq $clipboard) { exit 0 }; "
        "$bytes = [System.Text.Encoding]::UTF8.GetBytes([string]$clipboard); "
        "[System.Convert]::ToBase64String($bytes)"
    )

    last_error = None
    for command in ("powershell", "pwsh"):
        try:
            result = subprocess.run(
                [command, "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            last_error = exc
            continue

        if result.returncode != 0:
            stderr = result.stderr.strip()
            last_error = RuntimeError(stderr or f"{command} failed")
            continue

        payload = result.stdout.strip()
        if not payload:
            return None

        text = base64.b64decode(payload.encode("ascii")).decode("utf-8", errors="replace")
        if not text:
            return None

        return ClipboardContent.from_text(text)

    raise RuntimeError(str(last_error) if last_error else "clipboard read failed")


def write_windows_clipboard_content(content: ClipboardContent) -> None:
    text = content.to_text()
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    script = (
        "$bytes = [System.Convert]::FromBase64String('{encoded}'); "
        "$text = [System.Text.Encoding]::UTF8.GetString($bytes); "
        "Set-Clipboard -Value $text"
    ).format(encoded=encoded)

    last_error = None
    for command in ("powershell", "pwsh"):
        try:
            result = subprocess.run(
                [command, "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            last_error = exc
            continue

        if result.returncode == 0:
            return

        stderr = result.stderr.strip()
        last_error = RuntimeError(stderr or f"{command} failed")

    raise RuntimeError(str(last_error) if last_error else "clipboard write failed")


def read_local_clipboard_content() -> Optional[ClipboardContent]:
    if sys.platform == "darwin":
        return read_macos_clipboard_content()

    if sys.platform == "win32":
        return read_windows_clipboard_content()

    raise RuntimeError(f"Unsupported local platform: {sys.platform}")


def write_local_clipboard_content(content: ClipboardContent) -> None:
    if sys.platform == "darwin":
        write_macos_clipboard_content(content)
        return

    if sys.platform == "win32":
        write_windows_clipboard_content(content)
        return

    raise RuntimeError(f"Unsupported local platform: {sys.platform}")

