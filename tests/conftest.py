import pytest
import tempfile
import os
import zipfile
import io
from PIL import Image
import asyncio
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient

# Test configuration
pytest_plugins = ['pytest_asyncio']

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_paddleocr():
    """Mock PaddleOCR for testing without requiring actual OCR processing."""
    mock_ocr = Mock()
    mock_ocr.ocr.return_value = [[
        [[[100, 50], [200, 50], [200, 80], [100, 80]], ('Sample OCR text', 0.95)],
        [[[100, 100], [300, 100], [300, 130], [100, 130]], ('More OCR text', 0.90)]
    ]]
    return mock_ocr

@pytest.fixture
def sample_epub_text():
    """Create a simple text-based EPUB file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
        # Create a minimal EPUB structure
        with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add mimetype
            zip_file.writestr('mimetype', 'application/epub+zip')
            
            # Add META-INF/container.xml
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
            zip_file.writestr('META-INF/container.xml', container_xml)
            
            # Add content.opf
            content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>Test Book</dc:title>
        <dc:creator>Test Author</dc:creator>
        <dc:identifier id="bookid">test-book-123</dc:identifier>
        <dc:language>en</dc:language>
    </metadata>
    <manifest>
        <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
        <item id="toc" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="toc">
        <itemref idref="chapter1"/>
    </spine>
</package>'''
            zip_file.writestr('OEBPS/content.opf', content_opf)
            
            # Add chapter1.xhtml
            chapter_html = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Chapter 1</title>
</head>
<body>
    <h1>Chapter 1: Introduction</h1>
    <p>This is a test chapter with some sample text content.</p>
    <p>This EPUB file is used for testing the text extraction functionality.</p>
</body>
</html>'''
            zip_file.writestr('OEBPS/chapter1.xhtml', chapter_html)
            
            # Add toc.ncx
            toc_ncx = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/">
    <head>
        <meta name="dtb:uid" content="test-book-123"/>
    </head>
    <docTitle>
        <text>Test Book</text>
    </docTitle>
    <navMap>
        <navPoint id="chapter1">
            <navLabel><text>Chapter 1</text></navLabel>
            <content src="chapter1.xhtml"/>
        </navPoint>
    </navMap>
</ncx>'''
            zip_file.writestr('OEBPS/toc.ncx', toc_ncx)
        
        yield temp_file.name
        
        # Cleanup
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@pytest.fixture
def sample_epub_with_images():
    """Create an EPUB file with images for OCR testing."""
    with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
        with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add basic EPUB structure (same as text EPUB)
            zip_file.writestr('mimetype', 'application/epub+zip')
            
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
            zip_file.writestr('META-INF/container.xml', container_xml)
            
            content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>Test Book with Images</dc:title>
        <dc:creator>Test Author</dc:creator>
        <dc:identifier id="bookid">test-book-images-123</dc:identifier>
        <dc:language>en</dc:language>
    </metadata>
    <manifest>
        <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
        <item id="image1" href="images/test_image.png" media-type="image/png"/>
        <item id="toc" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="toc">
        <itemref idref="chapter1"/>
    </spine>
</package>'''
            zip_file.writestr('OEBPS/content.opf', content_opf)
            
            # Create a simple test image
            image = Image.new('RGB', (200, 100), color='white')
            image_buffer = io.BytesIO()
            image.save(image_buffer, format='PNG')
            zip_file.writestr('OEBPS/images/test_image.png', image_buffer.getvalue())
            
            # Add chapter with image reference
            chapter_html = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Chapter 1</title>
</head>
<body>
    <h1>Chapter 1: Images</h1>
    <p>This chapter contains an image that should be processed with OCR.</p>
    <img src="images/test_image.png" alt="Test image"/>
</body>
</html>'''
            zip_file.writestr('OEBPS/chapter1.xhtml', chapter_html)
            
            toc_ncx = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/">
    <head>
        <meta name="dtb:uid" content="test-book-images-123"/>
    </head>
    <docTitle>
        <text>Test Book with Images</text>
    </docTitle>
    <navMap>
        <navPoint id="chapter1">
            <navLabel><text>Chapter 1</text></navLabel>
            <content src="chapter1.xhtml"/>
        </navPoint>
    </navMap>
</ncx>'''
            zip_file.writestr('OEBPS/toc.ncx', toc_ncx)
        
        yield temp_file.name
        
        # Cleanup
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@pytest.fixture
def invalid_file():
    """Create a non-EPUB file for testing error handling."""
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
        temp_file.write(b"This is not an EPUB file")
        temp_file.flush()
        yield temp_file.name
        
        # Cleanup
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@pytest.fixture
def large_file():
    """Create a file larger than 50MB for testing size limits."""
    with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
        # Write 51MB of data
        data = b'0' * (51 * 1024 * 1024)
        temp_file.write(data)
        temp_file.flush()
        yield temp_file.name
        
        # Cleanup
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

@pytest.fixture
def api_client():
    """Create a test client for the FastAPI application."""
    from main import app
    return TestClient(app)

@pytest.fixture
def mock_epub_processor():
    """Mock EPUBProcessor for testing without dependencies."""
    mock_processor = Mock()
    mock_processor.extract_text = AsyncMock(return_value="Sample extracted text")
    return mock_processor