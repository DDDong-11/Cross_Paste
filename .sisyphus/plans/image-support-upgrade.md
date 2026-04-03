# Work Plan: CrossPaste Image Support Upgrade

## Goal
Upgrade CrossPaste from text-only clipboard sync to support **image copy/paste** between macOS and Windows over LAN, while maintaining backward compatibility with existing text sync.

## User Decisions (Confirmed)
- **Image Format**: PNG lossless
- **Content Priority**: Read only the latest clipboard item (either text OR image, not both)
- **Size Limit**: 10MB max for raw image bytes (before base64 encoding)
- **Test Strategy**: TDD with pytest

## Scope Boundaries
- **INCLUDE**: Image copy/paste between Mac ↔ Windows
- **INCLUDE**: Auto-detect clipboard content type (text vs image)
- **INCLUDE**: Base64 encoding for wire transport (already supported by protocol)
- **EXCLUDE**: File transfer, RTF, HTML clipboard content
- **EXCLUDE**: Image compression/transcoding (v1 — raw PNG transfer)

## Work Breakdown

### Phase 0: Test Infrastructure
**Task 0.1**: Add pytest infrastructure
- Create `tests/` directory with `__init__.py`
- Add `pyproject.toml` with pytest + pytest-cov dependencies
- Add `conftest.py` with shared fixtures
- Create `tests/test_content.py` as first test file

### Phase 1: Content Model Extension (content.py)
**Task 1.1**: TDD — Write tests for image content
- Test `ClipboardContent.from_image(png_bytes: bytes)` factory method
- Test `to_image_bytes() -> bytes` method
- Test `to_wire()` includes correct mimeType for images
- Test `from_wire()` roundtrip for image content
- Test size validation (10MB limit)

**Task 1.2**: Implement image content support
- Add `from_image(png_bytes: bytes)` classmethod
  - Validate size ≤ 10MB
  - Set `kind="image"`, `mime_type="image/png"`, `encoding="base64"`
  - Encode PNG bytes to base64
- Add `to_image_bytes() -> bytes` method
  - Decode base64 payload back to PNG bytes
  - Raise ValueError if kind != "image"
- Update `to_wire()` to include image preview (dimensions or "image" label)
- No changes to `digest()` — already covers all fields

### Phase 2: Clipboard Platform Extensions (clipboard.py)
**Task 2.1**: TDD — Write tests for macOS clipboard image (mocked)
- Test `read_macos_clipboard_content()` with image mock
- Test `write_macos_clipboard_content()` with image mock
- Test content type detection (image vs text priority)

**Task 2.2**: TDD — Write tests for Windows clipboard image (mocked)
- Test `read_windows_clipboard_content()` with image mock
- Test `write_windows_clipboard_content()` with image mock
- Test content type detection (image vs text priority)

**Task 2.3**: Implement macOS image clipboard
- Add `_macos_has_image_in_clipboard() -> bool`
  - Use osascript with AppKit to check NSPasteboard types
  - Check for `NSPasteboardTypePNG` or `NSPasteboardTypeTIFF`
- Add `_macos_read_clipboard_image() -> bytes`
  - Use osascript to extract PNG data from NSPasteboard
  - Save to temp file, read bytes, clean up
  - Return raw PNG bytes
- Add `_macos_write_clipboard_image(png_bytes: bytes) -> None`
  - Save bytes to temp PNG file
  - Use osascript with NSImage to set clipboard
- Update `read_macos_clipboard_content()`:
  - Check for image first → return `ClipboardContent.from_image(png_bytes)`
  - Fallback to text → return `ClipboardContent.from_text(text)`
- Update `write_macos_clipboard_content()`:
  - If content.kind == "image" → use image write path
  - Else → use existing text write path

**Task 2.4**: Implement Windows image clipboard
- Add `_windows_has_image_in_clipboard() -> bool`
  - Use PowerShell `Get-Clipboard -Format Image` with try/catch
- Add `_windows_read_clipboard_image() -> bytes`
  - Use PowerShell to get image, save to MemoryStream as PNG
  - Return PNG bytes
- Add `_windows_write_clipboard_image(png_bytes: bytes) -> None`
  - Save bytes to temp PNG file
  - Use PowerShell `Set-Clipboard -Value $img -Format Image`
- Update `read_windows_clipboard_content()`:
  - Check for image first → return `ClipboardContent.from_image(png_bytes)`
  - Fallback to text → return `ClipboardContent.from_text(text)`
- Update `write_windows_clipboard_content()`:
  - If content.kind == "image" → use image write path
  - Else → use existing text write path

### Phase 3: App Layer Update (app.py)
**Task 3.1**: TDD — Write tests for image content handling
- Test poll loop accepts image kind (not skipped)
- Test image content roundtrip through wire protocol

**Task 3.2**: Remove text-only filter
- Update poll loop (line 346-352) to accept both "text" and "image" kinds
- Update log messages to include content kind
- No other changes needed — wire protocol already supports typed content

### Phase 4: Documentation
**Task 4.1**: Update README
- Update scope section to include image support
- Update "How it works" to mention image detection
- Add example usage showing image copy/paste
- Update Notes section with image-specific information

## Execution Order
1. Phase 0 (test infra) → Phase 1 (content model) → Phase 2 (clipboard) → Phase 3 (app) → Phase 4 (docs)
2. Each phase follows TDD: write failing test → implement → make test pass
3. Phases 1-3 can be tested independently with mocked clipboard APIs

## Risk Mitigation
- **macOS osascript reliability**: AppleScript with AppKit is well-documented but version-dependent. Test on target macOS version.
- **Windows PowerShell image handling**: `Get-Clipboard -Format Image` requires Windows PowerShell 5.1+. PS Core may need fallback.
- **Large images**: 10MB limit prevents memory issues, but base64 encoding increases size by 33%. Monitor wire transfer times.
- **Temp file cleanup**: Image read/write uses temp files. Ensure cleanup on success and failure.

## Success Criteria
1. Copy image on Mac → paste on Windows (and vice versa)
2. Copy text on Mac → paste on Windows (backward compatibility)
3. Copy image on Mac → copy text on Mac → only text sync (latest item priority)
4. Images >10MB are skipped with warning (no crash)
5. All tests pass with pytest
6. README updated with image usage documentation
