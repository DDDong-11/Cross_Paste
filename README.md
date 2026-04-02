# CrossPaste MVP

CrossPaste is a minimal LAN clipboard sync tool for one-way text copy/paste from macOS to Windows.

## Scope

- Only works inside the same local network.
- Only syncs text.
- Only keeps the latest copied text from the Mac.
- One-way only: `Mac -> Windows`.

## Project layout

- `crosspaste/__main__.py`: command line entry point
- `crosspaste/app.py`: macOS server and Windows client
- `crosspaste/clipboard.py`: platform clipboard helpers
- `crosspaste/state.py`: latest-text in-memory state

## How it works

1. The Mac process polls the local clipboard with `pbpaste`.
2. When the text changes, it stores only the newest text in memory.
3. The Mac process exposes `GET /latest` over HTTP.
4. The Windows process polls that endpoint.
5. When it sees a new digest, it writes the text into the local Windows clipboard.

## Run on Mac

```bash
python3 -m crosspaste mac-server --host 0.0.0.0 --port 45892
```

Then find your Mac's LAN IP, for example `192.168.1.23`.

The latest-text endpoint will look like:

```text
http://192.168.1.23:45892/latest
```

## Run on Windows

Open PowerShell or Command Prompt in this project directory and run:

```powershell
py -3 -m crosspaste windows-client --server-url http://192.168.1.23:45892/latest
```

You can also use the included startup scripts:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows\start_client.ps1 -ServerUrl http://192.168.1.23:45892/latest
```

```bat
scripts\windows\start_client.bat http://192.168.1.23:45892/latest
```

## Notes

- If the Mac clipboard is empty, the server keeps serving the last non-empty text.
- If the Mac copies non-text content, `pbpaste` returns empty content, so the current latest text is unchanged.
- `windows-client` uses PowerShell `Set-Clipboard`, so PowerShell needs to be available on the Windows machine.
- The Windows machine needs a copy of this project directory, or at least the `crosspaste` and `scripts/windows` folders.
