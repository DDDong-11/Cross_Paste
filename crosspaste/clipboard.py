from __future__ import annotations

import base64
import os
import subprocess
import sys
import tempfile
from typing import Optional

from .content import ClipboardContent


def _macos_has_image_in_clipboard() -> bool:
    script = """
use framework "AppKit"
set pb to current application's NSPasteboard's generalPasteboard()
set tTypes to pb's types() as list
if (tTypes's contains:(current application's NSPasteboardTypePNG as string)) or (tTypes's contains:(current application's NSPasteboardTypeTIFF as string)) then
    return "yes"
else
    return "no"
end if
"""
    result = subprocess.run(
        ["osascript", "-l", "AppleScript", "-e", script],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    return result.stdout.decode("utf-8", errors="replace").strip() == "yes"


def _macos_read_clipboard_image() -> Optional[bytes]:
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)

        script = f"""
use framework "AppKit"
set pb to current application's NSPasteboard's generalPasteboard()
set imgData to pb's dataForType:(current application's NSPasteboardTypePNG)
if imgData is missing value then
    set imgData to pb's dataForType:(current application's NSPasteboardTypeTIFF)
end if
if imgData is not missing value then
    imgData's writeToFile:"{tmp_path}" atomically:true
end if
"""
        result = subprocess.run(
            ["osascript", "-l", "AppleScript", "-e", script],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0 or not os.path.exists(tmp_path):
            return None

        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _macos_write_clipboard_image(png_bytes: bytes) -> None:
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        with open(tmp_path, "wb") as f:
            f.write(png_bytes)

        posix_path = tmp_path
        script = f"""
use framework "AppKit"
set theImage to current application's NSImage's alloc()'s initWithContentsOfFile:"{posix_path}"
set pb to current application's NSPasteboard's generalPasteboard()
pb's clearContents()
pb's writeObjects:{{theImage}}
"""
        result = subprocess.run(
            ["osascript", "-l", "AppleScript", "-e", script],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(stderr or "osascript failed to write image to clipboard")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def read_macos_clipboard_content() -> Optional[ClipboardContent]:
    if _macos_has_image_in_clipboard():
        png_bytes = _macos_read_clipboard_image()
        if png_bytes:
            try:
                return ClipboardContent.from_image(png_bytes)
            except ValueError:
                pass

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
    if content.kind == "image":
        _macos_write_clipboard_image(content.to_image_bytes())
        return

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


def _windows_has_image_in_clipboard() -> bool:
    script = (
        "try { "
        "$img = Get-Clipboard -Format Image -ErrorAction Stop; "
        "if ($null -ne $img) { 'yes' } else { 'no' } "
        "} catch { 'no' }"
    )

    for command in ("powershell", "pwsh"):
        try:
            result = subprocess.run(
                [command, "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip() == "yes"
        except FileNotFoundError:
            continue

    return False


def _windows_read_clipboard_image() -> Optional[bytes]:
    script = (
        "Add-Type -AssemblyName System.Drawing; "
        "$img = Get-Clipboard -Format Image -ErrorAction Stop; "
        "if ($null -eq $img) { exit 0 }; "
        "$ms = New-Object System.IO.MemoryStream; "
        "$img.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png); "
        "$bytes = $ms.ToArray(); "
        "$ms.Close(); "
        "[System.Convert]::ToBase64String($bytes)"
    )

    for command in ("powershell", "pwsh"):
        try:
            result = subprocess.run(
                [command, "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            continue

        if result.returncode != 0:
            continue

        payload = result.stdout.strip()
        if not payload:
            return None

        return base64.b64decode(payload.encode("ascii"))

    return None


def _windows_write_clipboard_image(png_bytes: bytes) -> None:
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        with open(tmp_path, "wb") as f:
            f.write(png_bytes)

        escaped_path = tmp_path.replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Drawing; "
            f"$img = [System.Drawing.Image]::FromFile('{escaped_path}'); "
            "Set-Clipboard -Value $img -Format Image; "
            "$img.Dispose()"
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

            if result.returncode == 0:
                return

            stderr = result.stderr.strip()
            last_error = RuntimeError(stderr or f"{command} failed")

        raise RuntimeError(str(last_error) if last_error else "clipboard image write failed")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def read_windows_clipboard_content() -> Optional[ClipboardContent]:
    if _windows_has_image_in_clipboard():
        png_bytes = _windows_read_clipboard_image()
        if png_bytes:
            try:
                return ClipboardContent.from_image(png_bytes)
            except ValueError:
                pass

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
    if content.kind == "image":
        _windows_write_clipboard_image(content.to_image_bytes())
        return

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
