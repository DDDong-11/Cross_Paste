# CrossPaste MVP

CrossPaste is a minimal LAN clipboard sync tool for macOS and Windows.

## Scope

- Only works inside the same local network.
- Only keeps the latest clipboard item.
- Today it applies text content end to end.
- The wire protocol already carries typed content metadata so image support can be added later without redesigning the HTTP API.

## Project layout

- `crosspaste/__main__.py`: command line entry point
- `crosspaste/app.py`: generic server, client, and bidirectional agent modes
- `crosspaste/clipboard.py`: platform clipboard helpers
- `crosspaste/content.py`: extensible clipboard content model
- `crosspaste/state.py`: latest-item in-memory state

## How it works

1. Each machine watches its own clipboard.
2. The latest item is stored in memory and exposed through `GET /latest`.
3. The peer machine polls that endpoint.
4. If the digest changed, the peer writes the new content into its local clipboard.
5. In `agent` mode, one process handles local watching, local serving, and remote polling together, which keeps bidirectional sync simpler.

## Recommended: Bidirectional Text Sync

Run one agent on each machine.

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
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start_agent.ps1 -PeerUrl http://MAC_IP:45892/latest -Port 45892
```

When both agents are running:

- Copy text on Mac and paste on Windows.
- Copy text on Windows and paste on Mac.

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
- Windows clipboard access uses PowerShell `Get-Clipboard` and `Set-Clipboard`.
- macOS clipboard access uses `pbpaste` and `pbcopy`.
- The wire format now includes `kind`, `mimeType`, `encoding`, and `payloadBase64`.
- This prepares the transport for images later, but the current build only reads and writes text on both platforms.
