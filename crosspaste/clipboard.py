from __future__ import annotations

import base64
import subprocess


def read_macos_clipboard_text() -> str:
    result = subprocess.run(
        ["pbpaste"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or "pbpaste failed")

    return result.stdout.decode("utf-8", errors="replace")


def write_windows_clipboard_text(text: str) -> None:
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

