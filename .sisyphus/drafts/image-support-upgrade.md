# Draft: CrossPaste Image Support Upgrade

## Current State Analysis

### Architecture
- Python-based LAN clipboard sync tool (macOS + Windows)
- Wire protocol already supports typed content: `kind`, `mime_type`, `encoding`, `payload_base64`
- Currently only handles `kind="text"` — images are explicitly skipped in `app.py:346-352`
- `ClipboardContent` is a frozen dataclass with `from_text()` / `to_text()` methods

### Files to Modify
1. **`crosspaste/content.py`** — Add `from_image()` factory, `to_image()` method, image MIME types
2. **`crosspaste/clipboard.py`** — Platform-specific image read/write (macOS + Windows)
3. **`crosspaste/app.py`** — Remove text-only filter in poll loop
4. **`crosspaste/state.py`** — No changes needed (content-agnostic)
5. **`crosspaste/__main__.py`** — No changes needed
6. **Scripts** — No changes needed (same launch commands)

### User Decisions (Confirmed)
- **Image Format**: PNG lossless (quality over size)
- **Content Priority**: Read only the latest clipboard item (either text OR image, not both)
- **Size Limit**: 10MB max (before base64 encoding)

## Technical Decisions
#### 1. Image Read/Write Strategy
**macOS:**
- **Decision**: Use `osascript` + AppleScript with NSPasteboard (no dependencies)
- Read: Check for image types first (`NSPasteboardTypePNG`, `NSPasteboardTypeTIFF`), fallback to text
- Write: Save PNG to temp file, then use `NSPasteboard` to set image

**Windows:**
- **Decision**: Use PowerShell `Get-Clipboard -Format Image` + `Set-Clipboard` (built-in, no deps)
- Read: Get image as PNG bytes, base64 encode
- Write: Decode base64, save temp PNG, Set-Clipboard with image

#### 2. Content Detection
- Read image first, if no image then read text
- Single `read_clipboard_content()` returns either image or text
- `kind` field distinguishes: `"image"` vs `"text"`

#### 3. Size Limit
- 10MB max for raw image bytes (before base64)
- If exceeded, log warning and skip (don't crash)

## Research Findings

### macOS Clipboard Image (from bg_e4a078de)
**Reading:**
- Use `osascript -l AppleScript` with `use framework "AppKit"` to access NSPasteboard
- Detect image: check `pb's types()` for `NSPasteboardTypePNG` or `NSPasteboardTypeTIFF`
- Extract: `pb's dataForType:(current application's NSPasteboardTypePNG)` returns NSData
- Write to file: `theData's writeToFile:atomically:` or use `pngpaste` CLI tool

**Writing:**
- Load image: `NSImage's imageWithContentsOfFile:path`
- Set to clipboard: `pb's clearContents()` then `pb's writeObjects:(NSArray's arrayWithObject:theImage)`

**Type Detection:**
```applescript
use framework "AppKit"
set pb to current application's NSPasteboard's generalPasteboard()
set tTypes to pb's types() as list
if (tTypes's contains:(current application's NSPasteboardTypePNG as string)) or (tTypes's contains:(current application's NSPasteboardTypeTIFF as string)) then
    return "image"
else
    return "not image"
end if
```

### Windows Clipboard Image (from bg_e06632c1)
**Reading:**
- `Get-Clipboard -Format Image` returns `System.Drawing.Image` (typically `Bitmap`)
- Save to PNG: `$clipImg.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)`
- To Base64: Save to MemoryStream, get bytes, `[Convert]::ToBase64String($bytes)`
- Fallback: `[System.Windows.Forms.Clipboard]::GetImage()` for PS Core

**Writing:**
- From file: `$img = [System.Drawing.Image]::FromFile($path); Set-Clipboard -Value $img -Format Image`
- From bytes: Load to MemoryStream, create Image, Set-Clipboard

**Type Detection:**
```powershell
try { $img = Get-Clipboard -Format Image -ErrorAction Stop; $hasImage = $true } catch { $hasImage = $false }
```

### Test Infrastructure
- No test framework exists in project
- User chose TDD approach
- Need to add: pytest + pytest-cov for Python testing

### Implementation Strategy
1. Add test infrastructure (pytest)
2. Extend `content.py` with image support (`from_image`, `to_image`)
3. Extend `clipboard.py` with platform image read/write
4. Update `app.py` to handle image content type
5. Update README with image usage docs

## Scope Boundaries
- INCLUDE: Image copy/paste between Mac ↔ Windows
- INCLUDE: Auto-detect clipboard content type (text vs image)
- INCLUDE: Base64 encoding for wire transport (already supported)
- EXCLUDE: File transfer, RTF, HTML clipboard content
- EXCLUDE: Image compression/transcoding (v1 — raw transfer)
