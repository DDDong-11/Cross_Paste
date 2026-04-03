import base64
import pytest

from crosspaste.content import ClipboardContent


class TestClipboardContentFromImage:
    def test_from_image_sets_correct_kind(self, sample_png_bytes):
        content = ClipboardContent.from_image(sample_png_bytes)
        assert content.kind == "image"

    def test_from_image_sets_correct_mime_type(self, sample_png_bytes):
        content = ClipboardContent.from_image(sample_png_bytes)
        assert content.mime_type == "image/png"

    def test_from_image_sets_correct_encoding(self, sample_png_bytes):
        content = ClipboardContent.from_image(sample_png_bytes)
        assert content.encoding == "base64"

    def test_from_image_encodes_png_to_base64(self, sample_png_bytes):
        content = ClipboardContent.from_image(sample_png_bytes)
        decoded = base64.b64decode(content.payload_base64)
        assert decoded == sample_png_bytes

    def test_from_image_rejects_oversized_image(self, sample_png_bytes):
        # Create 11MB of fake image data
        large_data = b'\x89PNG' + b'\x00' * (11 * 1024 * 1024)
        with pytest.raises(ValueError, match="exceeds maximum size"):
            ClipboardContent.from_image(large_data)

    def test_from_image_accepts_10mb_image(self):
        # Exactly 10MB should be accepted
        data = b'\x89PNG' + b'\x00' * (10 * 1024 * 1024 - 4)
        content = ClipboardContent.from_image(data)
        assert content.kind == "image"


class TestClipboardContentToImageBytes:
    def test_to_image_bytes_roundtrip(self, sample_png_bytes):
        content = ClipboardContent.from_image(sample_png_bytes)
        result = content.to_image_bytes()
        assert result == sample_png_bytes

    def test_to_image_bytes_raises_on_text(self, sample_text_content):
        with pytest.raises(ValueError, match="not an image"):
            sample_text_content.to_image_bytes()


class TestClipboardContentWireRoundtrip:
    def test_image_content_wire_roundtrip(self, sample_png_bytes):
        original = ClipboardContent.from_image(sample_png_bytes)
        wire = original.to_wire()
        restored = ClipboardContent.from_wire(wire)
        assert restored.kind == original.kind
        assert restored.mime_type == original.mime_type
        assert restored.encoding == original.encoding
        assert restored.payload_base64 == original.payload_base64

    def test_image_to_wire_includes_size(self, sample_png_bytes):
        content = ClipboardContent.from_image(sample_png_bytes)
        wire = content.to_wire()
        assert wire["size"] == len(sample_png_bytes)

    def test_image_to_wire_has_empty_preview(self, sample_png_bytes):
        content = ClipboardContent.from_image(sample_png_bytes)
        wire = content.to_wire()
        assert wire["preview"] == ""

    def test_text_content_still_works(self, sample_text):
        content = ClipboardContent.from_text(sample_text)
        wire = content.to_wire()
        assert wire["kind"] == "text"
        assert wire["preview"] == sample_text[:80]
        restored = ClipboardContent.from_wire(wire)
        assert restored.to_text() == sample_text


class TestClipboardContentDigest:
    def test_image_digest_is_stable(self, sample_png_bytes):
        c1 = ClipboardContent.from_image(sample_png_bytes)
        c2 = ClipboardContent.from_image(sample_png_bytes)
        assert c1.digest() == c2.digest()

    def test_image_digest_differs_from_text(self, sample_png_bytes, sample_text):
        image_content = ClipboardContent.from_image(sample_png_bytes)
        text_content = ClipboardContent.from_text(sample_text)
        assert image_content.digest() != text_content.digest()
