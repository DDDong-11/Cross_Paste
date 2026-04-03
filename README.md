# CrossPaste

CrossPaste is a minimal LAN clipboard sync tool for macOS and Windows.

## Features

- **Text & Image Sync**: Copy text or images on one machine, paste on the other.
- **Auto-Discovery**: No need to know peer IP — agents find each other via UDP broadcast.
- **Smart Compression**: Large images (>500KB) auto-compress to JPEG for faster transfer.
- **Bidirectional**: One agent per machine handles both send and receive.

## Scope

- Only works inside the same local network.
- Only keeps the latest clipboard item.
- Supports text, PNG, and JPEG content end to end.
- When the clipboard contains both text and image, only the image is synced.
- Images larger than 10MB are skipped.
- Large images (>500KB) are compressed to JPEG (85%→30% quality) before transfer.

## Project layout

- `crosspaste/__main__.py`: command line entry point
- `crosspaste/app.py`: generic server, client, and bidirectional agent modes
- `crosspaste/clipboard.py`: platform clipboard helpers (text + image)
- `crosspaste/content.py`: extensible clipboard content model
- `crosspaste/state.py`: latest-item in-memory state
- `crosspaste/discovery.py`: UDP broadcast peer auto-discovery

## How it works

1. Each machine watches its own clipboard.
2. The latest item is stored in memory and exposed through `GET /latest`.
3. The peer machine polls that endpoint.
4. If the digest changed, the peer writes the new content into its local clipboard.
5. In `agent` mode, one process handles local watching, local serving, and remote polling together.
6. With `--auto-discover`, agents broadcast via UDP to find each other — no manual IP config needed.

## Quick Start (Auto-Discovery)

The easiest way — no need to know the peer's IP address.

### On Mac

```bash
sh ./scripts/mac/start_agent.sh auto
```

### On Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start_agent.ps1 -Mode auto
```

Once both agents discover each other, start copying text or images — they sync automatically.

## Manual Mode (Specify Peer IP)

If you prefer to specify the peer address directly.

### On Mac

```bash
python3 -m crosspaste mac-agent --peer-url http://WINDOWS_IP:45892/latest --port 45892
```

Or use the helper script:

```bash
sh ./scripts/mac/start_agent.sh http://WINDOWS_IP:45892/latest 45892
```

### On Windows

```powershell
py -3 -m crosspaste windows-agent --peer-url http://MAC_IP:45892/latest --port 45892
```

Or use the helper script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start_agent.ps1 -Mode manual -PeerUrl http://MAC_IP:45892/latest -Port 45892
```

When both agents are running:

- Copy text on Mac and paste on Windows (and vice versa).
- Copy image on Mac and paste on Windows (and vice versa).
- The latest clipboard item is synced — if you copy an image, the image syncs; if you copy text next, the text syncs.

## Legacy: One-Way Modes

If you only want one direction, the old split modes still work.

### Mac as server

```bash
python3 -m crosspaste mac-server --host 0.0.0.0 --port 45892
```

### Windows as client

```powershell
py -3 -m crosspaste windows-client --server-url http://MAC_IP:45892/latest
```

### Windows as server

```powershell
py -3 -m crosspaste windows-server --host 0.0.0.0 --port 45892
```

### Mac as client

```bash
python3 -m crosspaste mac-client --server-url http://WINDOWS_IP:45892/latest
```

The endpoint still looks like:

```text
http://192.168.1.23:45892/latest
```

## Existing Windows Client Script

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start_client.ps1 -ServerUrl http://192.168.1.23:45892/latest
```

```bat
scripts\windows\start_client.bat http://192.168.1.23:45892/latest
```

## Notes

- If the local clipboard is empty, the server keeps serving the last non-empty item it captured.
- The Windows machine needs a copy of this project directory, or at least the `crosspaste` and `scripts` folders.
- Windows clipboard access uses PowerShell `Get-Clipboard` / `Set-Clipboard` with `System.Windows.Forms.Clipboard` for image handling.
- macOS clipboard access uses `osascript` with AppKit `NSPasteboard` for both text and image.
- Small images are transferred as PNG (lossless). Large images (>500KB) are compressed to JPEG for efficiency.
- Maximum image size is 10MB (before compression).
- When the clipboard contains both text and image, only the image is synced.
- The wire format includes `kind`, `mimeType`, `encoding`, and `payloadBase64` to support both text and image content.
