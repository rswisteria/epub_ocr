import pytest
import asyncio
import tempfile
import os
import zipfile
import io
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch
from fastapi.testclient import TestClient
from PIL import Image
import psutil
import gc

from main import app
from epub_processor import EPUBProcessor


class TestIntegration:
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def processor(self):
        """Create real EPUBProcessor for integration tests."""
        with patch('epub_processor.PaddleOCR') as mock_ocr_class:
            mock_ocr = mock_ocr_class.return_value
            mock_ocr.ocr.return_value = [[
                [[[100, 50], [200, 50], [200, 80], [100, 80]], ('Integration test OCR', 0.95)]
            ]]
            return EPUBProcessor()
    
    @pytest.fixture
    def complex_epub(self):
        """Create a complex EPUB with multiple chapters and images."""
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
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
        <dc:title>Complex Test Book</dc:title>
        <dc:creator>Integration Test</dc:creator>
        <dc:identifier id="bookid">complex-test-book-123</dc:identifier>
        <dc:language>en</dc:language>
    </metadata>
    <manifest>
        <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
        <item id="chapter2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
        <item id="chapter3" href="chapter3.xhtml" media-type="application/xhtml+xml"/>
        <item id="image1" href="images/image1.png" media-type="image/png"/>
        <item id="image2" href="images/image2.jpg" media-type="image/jpeg"/>
        <item id="toc" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="toc">
        <itemref idref="chapter1"/>
        <itemref idref="chapter2"/>
        <itemref idref="chapter3"/>
    </spine>
</package>'''
                zip_file.writestr('OEBPS/content.opf', content_opf)
                
                # Add multiple chapters
                for i in range(1, 4):
                    chapter_html = f'''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Chapter {i}</title>
</head>
<body>
    <h1>Chapter {i}: Integration Test Chapter</h1>
    <p>This is chapter {i} of the integration test EPUB.</p>
    <p>It contains substantial text content for testing purposes.</p>
    <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
    {"<img src='images/image1.png' alt='Test image'/>" if i == 2 else ""}
    {"<img src='images/image2.jpg' alt='Another test image'/>" if i == 3 else ""}
</body>
</html>'''
                    zip_file.writestr(f'OEBPS/chapter{i}.xhtml', chapter_html)
                
                # Add test images
                for i, fmt in enumerate(['PNG', 'JPEG'], 1):
                    image = Image.new('RGB', (200, 100), color=(255, 255, 255))
                    image_buffer = io.BytesIO()
                    image.save(image_buffer, format=fmt)
                    ext = 'png' if fmt == 'PNG' else 'jpg'
                    zip_file.writestr(f'OEBPS/images/image{i}.{ext}', image_buffer.getvalue())
                
                # Add toc.ncx
                toc_ncx = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/">
    <head>
        <meta name="dtb:uid" content="complex-test-book-123"/>
    </head>
    <docTitle>
        <text>Complex Test Book</text>
    </docTitle>
    <navMap>
        <navPoint id="chapter1">
            <navLabel><text>Chapter 1</text></navLabel>
            <content src="chapter1.xhtml"/>
        </navPoint>
        <navPoint id="chapter2">
            <navLabel><text>Chapter 2</text></navLabel>
            <content src="chapter2.xhtml"/>
        </navPoint>
        <navPoint id="chapter3">
            <navLabel><text>Chapter 3</text></navLabel>
            <content src="chapter3.xhtml"/>
        </navPoint>
    </navMap>
</ncx>'''
                zip_file.writestr('OEBPS/toc.ncx', toc_ncx)
            
            yield temp_file.name
            
            # Cleanup
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    @pytest.mark.asyncio
    async def test_end_to_end_text_and_ocr_processing(self, processor, complex_epub):
        """Test complete end-to-end processing of EPUB with text and images."""
        result = await processor.extract_text(complex_epub)
        
        # Verify text content from all chapters
        assert "Chapter 1: Integration Test Chapter" in result
        assert "Chapter 2: Integration Test Chapter" in result
        assert "Chapter 3: Integration Test Chapter" in result
        assert "Lorem ipsum dolor sit amet" in result
        
        # Verify OCR content
        assert "Integration test OCR" in result
        
        # Verify structure (text and OCR should be separated)
        assert "\n\n" in result
        assert len(result) > 500  # Should have substantial content
    
    def test_api_end_to_end_workflow(self, client, complex_epub):
        """Test complete API workflow from upload to response."""
        with open(complex_epub, 'rb') as epub_file:
            response = client.post(
                "/upload-epub",
                files={"file": ("complex_book.epub", epub_file, "application/epub+zip")}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["filename"] == "complex_book.epub"
        assert data["status"] == "success"
        assert "Chapter 1: Integration Test Chapter" in data["text"]
        assert "Chapter 2: Integration Test Chapter" in data["text"]
        assert "Chapter 3: Integration Test Chapter" in data["text"]
        assert len(data["text"]) > 500
    
    def test_concurrent_request_handling(self, client, complex_epub):
        """Test handling of multiple concurrent API requests."""
        def make_request(file_suffix):
            with open(complex_epub, 'rb') as epub_file:
                return client.post(
                    "/upload-epub",
                    files={"file": (f"book_{file_suffix}.epub", epub_file, "application/epub+zip")}
                )
        
        # Send 5 concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(5)]
            responses = [future.result() for future in as_completed(futures)]
        
        # All requests should succeed
        assert len(responses) == 5
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "Chapter 1: Integration Test Chapter" in data["text"]
    
    def test_memory_usage_large_files(self, client):
        """Test memory usage with large EPUB files."""
        # Create a large EPUB with many images
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add basic EPUB structure
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
        <dc:title>Large Test Book</dc:title>
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
                
                # Add many small images to test memory handling
                for i in range(10):
                    image = Image.new('RGB', (100, 100), color=(i*25, i*25, i*25))
                    image_buffer = io.BytesIO()
                    image.save(image_buffer, format='PNG')
                    zip_file.writestr(f'OEBPS/image_{i}.png', image_buffer.getvalue())
                
                # Add chapter
                zip_file.writestr('OEBPS/chapter1.xhtml', '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Large Book</title></head>
<body><h1>Large Book Test</h1><p>Memory test content</p></body>
</html>''')
                
                zip_file.writestr('OEBPS/toc.ncx', '''<?xml version="1.0" encoding="UTF-8"?>
<ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/">
    <head><meta name="dtb:uid" content="large-book"/></head>
    <docTitle><text>Large Book</text></docTitle>
    <navMap><navPoint id="chapter1"><navLabel><text>Chapter 1</text></navLabel><content src="chapter1.xhtml"/></navPoint></navMap>
</ncx>''')
        
        try:
            # Measure memory before
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            with open(temp_file.name, 'rb') as epub_file:
                response = client.post(
                    "/upload-epub",
                    files={"file": ("large_book.epub", epub_file, "application/epub+zip")}
                )
            
            # Force garbage collection
            gc.collect()
            
            # Measure memory after
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = memory_after - memory_before
            
            assert response.status_code == 200
            # Memory increase should be reasonable (less than 100MB for this test)
            assert memory_increase < 100, f"Memory increased by {memory_increase}MB"
            
        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    def test_temporary_file_cleanup(self, client, complex_epub):
        """Test that temporary files are properly cleaned up."""
        import tempfile
        temp_dir = tempfile.gettempdir()
        
        # Count temporary files before
        temp_files_before = [f for f in os.listdir(temp_dir) if f.endswith('.epub')]
        
        # Make multiple requests
        for i in range(3):
            with open(complex_epub, 'rb') as epub_file:
                response = client.post(
                    "/upload-epub",
                    files={"file": (f"test_{i}.epub", epub_file, "application/epub+zip")}
                )
                assert response.status_code == 200
        
        # Count temporary files after
        temp_files_after = [f for f in os.listdir(temp_dir) if f.endswith('.epub')]
        
        # Should have the same number of temp files (all cleaned up)
        assert len(temp_files_after) == len(temp_files_before)
    
    def test_error_recovery_and_cleanup(self, client, complex_epub):
        """Test that system recovers properly from errors and cleans up resources."""
        # Test with processing error
        with patch('main.epub_processor.extract_text', side_effect=Exception("Simulated error")):
            with open(complex_epub, 'rb') as epub_file:
                response = client.post(
                    "/upload-epub",
                    files={"file": ("error_test.epub", epub_file, "application/epub+zip")}
                )
            
            assert response.status_code == 500
            assert "Error processing EPUB" in response.json()["detail"]
        
        # Subsequent request should work normally
        with open(complex_epub, 'rb') as epub_file:
            response = client.post(
                "/upload-epub",
                files={"file": ("recovery_test.epub", epub_file, "application/epub+zip")}
            )
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_parallel_image_processing_integration(self, processor):
        """Test that multiple images are processed in parallel correctly."""
        # Create EPUB with many images
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, 'w') as zip_file:
                # Add 8 images to test parallel processing
                for i in range(8):
                    image = Image.new('RGB', (100, 50), color=(i*30, i*30, i*30))
                    image_buffer = io.BytesIO()
                    image.save(image_buffer, format='PNG')
                    zip_file.writestr(f'image_{i}.png', image_buffer.getvalue())
            
            try:
                start_time = time.time()
                result = await processor._extract_image_text(temp_file.name)
                end_time = time.time()
                
                # Should have processed all 8 images
                image_results = [r for r in result.split('\n\n') if r.strip()]
                assert len(image_results) == 8
                
                # Processing time should be reasonable (parallel processing should be faster)
                processing_time = end_time - start_time
                assert processing_time < 5.0, f"Processing took too long: {processing_time}s"
                
            finally:
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
    
    def test_stress_test_rapid_requests(self, client, sample_epub_text):
        """Test system behavior under rapid successive requests."""
        responses = []
        
        # Send 20 requests in rapid succession
        for i in range(20):
            with open(sample_epub_text, 'rb') as epub_file:
                response = client.post(
                    "/upload-epub",
                    files={"file": (f"stress_test_{i}.epub", epub_file, "application/epub+zip")}
                )
                responses.append(response)
        
        # All requests should eventually succeed or fail gracefully
        success_count = sum(1 for r in responses if r.status_code == 200)
        error_count = sum(1 for r in responses if r.status_code >= 400)
        
        assert success_count + error_count == 20
        # Most requests should succeed (allow for some rate limiting/errors)
        assert success_count >= 15
    
    def test_different_epub_formats_compatibility(self, client):
        """Test compatibility with different EPUB format variations."""
        epub_formats = [
            # EPUB 2.0 format
            {
                'version': '2.0',
                'namespace': 'http://www.idpf.org/2007/opf',
                'dtd': '<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx.dtd">'
            },
            # EPUB 3.0 format
            {
                'version': '3.0',
                'namespace': 'http://www.idpf.org/2007/opf',
                'dtd': ''
            }
        ]
        
        for format_spec in epub_formats:
            with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
                with zipfile.ZipFile(temp_file.name, 'w') as zip_file:
                    zip_file.writestr('mimetype', 'application/epub+zip')
                    
                    container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
                    zip_file.writestr('META-INF/container.xml', container_xml)
                    
                    content_opf = f'''<?xml version="1.0" encoding="UTF-8"?>
<package version="{format_spec['version']}" xmlns="{format_spec['namespace']}" unique-identifier="bookid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>Format Test Book</dc:title>
        <dc:identifier id="bookid">format-test-{format_spec['version']}</dc:identifier>
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
                    
                    zip_file.writestr('OEBPS/chapter1.xhtml', f'''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Format Test</title></head>
<body><h1>EPUB {format_spec['version']} Test</h1><p>Format compatibility test</p></body>
</html>''')
                    
                    toc_content = f'''{format_spec['dtd']}
<ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/">
    <head><meta name="dtb:uid" content="format-test-{format_spec['version']}"/></head>
    <docTitle><text>Format Test</text></docTitle>
    <navMap><navPoint id="chapter1"><navLabel><text>Chapter 1</text></navLabel><content src="chapter1.xhtml"/></navPoint></navMap>
</ncx>'''
                    zip_file.writestr('OEBPS/toc.ncx', toc_content)
                
                try:
                    with open(temp_file.name, 'rb') as epub_file:
                        response = client.post(
                            "/upload-epub",
                            files={"file": (f"format_test_{format_spec['version']}.epub", epub_file, "application/epub+zip")}
                        )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert f"EPUB {format_spec['version']} Test" in data["text"]
                    assert "Format compatibility test" in data["text"]
                    
                finally:
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)