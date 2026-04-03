import base64
import pytest


@pytest.fixture
def sample_text():
    return "Hello, CrossPaste!"


@pytest.fixture
def sample_text_content(sample_text):
    from crosspaste.content import ClipboardContent
    return ClipboardContent.from_text(sample_text)


@pytest.fixture
def sample_png_bytes():
    # This is a real minimal PNG file (67 bytes)
    import struct
    import zlib

    def create_minimal_png():
        # PNG signature
        signature = b'\x89PNG\r\n\x1a\n'

        # IHDR chunk: 1x1 pixel, 8-bit RGBA
        width, height = 1, 1
        bit_depth = 8
        color_type = 6  # RGBA
        ihdr_data = struct.pack('>IIBBBBB', width, height, bit_depth, color_type, 0, 0, 0)
        ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
        ihdr_chunk = struct.pack('>I', len(ihdr_data)) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)

        # IDAT chunk: single pixel with filter byte
        raw_data = b'\x00\x00\x00\x00\x00'  # filter=0, R=0, G=0, B=0, A=0
        compressed = zlib.compress(raw_data)
        idat_crc = zlib.crc32(b'IDAT' + compressed) & 0xffffffff
        idat_chunk = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc)

        # IEND chunk
        iend_crc = zlib.crc32(b'IEND') & 0xffffffff
        iend_chunk = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)

        return signature + ihdr_chunk + idat_chunk + iend_chunk

    return create_minimal_png()


@pytest.fixture
def sample_image_content(sample_png_bytes):
    from crosspaste.content import ClipboardContent
    return ClipboardContent.from_image(sample_png_bytes)


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    import subprocess

    class MockResult:
        def __init__(self, returncode=0, stdout=b'', stderr=b''):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    calls = []

    def mock_run(*args, **kwargs):
        calls.append({'args': args, 'kwargs': kwargs})
        return MockResult()

    monkeypatch.setattr(subprocess, 'run', mock_run)
    return calls
