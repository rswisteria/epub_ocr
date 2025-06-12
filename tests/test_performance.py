import pytest
import time
import asyncio
import tempfile
import os
import zipfile
import io
import threading
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch
from fastapi.testclient import TestClient
from PIL import Image
import psutil
import gc
from statistics import mean, median

from main import app
from epub_processor import EPUBProcessor


class TestPerformance:
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    @pytest.fixture
    def processor(self):
        """Create EPUBProcessor with mocked OCR for consistent performance testing."""
        with patch('epub_processor.PaddleOCR') as mock_ocr_class:
            mock_ocr = mock_ocr_class.return_value
            mock_ocr.ocr.return_value = [[
                [[[100, 50], [200, 50], [200, 80], [100, 80]], ('Performance test OCR', 0.95)]
            ]]
            return EPUBProcessor()
    
    @pytest.fixture
    def small_epub(self):
        """Create a small EPUB file (<1MB) for performance testing."""
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
        <dc:title>Small Performance Test</dc:title>
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
                
                # Small chapter
                chapter_html = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Performance Test</title></head>
<body><h1>Small File</h1><p>Performance test content.</p></body>
</html>'''
                zip_file.writestr('OEBPS/chapter1.xhtml', chapter_html)
                
                zip_file.writestr('OEBPS/toc.ncx', '''<?xml version="1.0" encoding="UTF-8"?>
<ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/">
    <head><meta name="dtb:uid" content="small-perf-test"/></head>
    <docTitle><text>Small Performance Test</text></docTitle>
    <navMap><navPoint id="chapter1"><navLabel><text>Chapter 1</text></navLabel><content src="chapter1.xhtml"/></navPoint></navMap>
</ncx>''')
            
            yield temp_file.name
            
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    @pytest.fixture
    def medium_epub(self):
        """Create a medium EPUB file (1-10MB) for performance testing."""
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
                
                # Create content.opf with multiple chapters
                manifest_items = []
                spine_items = []
                for i in range(10):
                    manifest_items.append(f'<item id="chapter{i+1}" href="chapter{i+1}.xhtml" media-type="application/xhtml+xml"/>')
                    spine_items.append(f'<itemref idref="chapter{i+1}"/>')
                
                content_opf = f'''<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>Medium Performance Test</dc:title>
    </metadata>
    <manifest>
        {chr(10).join(manifest_items)}
        <item id="toc" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="toc">
        {chr(10).join(spine_items)}
    </spine>
</package>'''
                zip_file.writestr('OEBPS/content.opf', content_opf)
                
                # Add multiple chapters with substantial content
                for i in range(10):
                    chapter_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter {i+1}</title></head>
<body>
    <h1>Chapter {i+1}: Medium File Performance Test</h1>
    {'<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.</p>' * 50}
</body>
</html>'''
                    zip_file.writestr(f'OEBPS/chapter{i+1}.xhtml', chapter_content)
                
                # Add 3 images
                for i in range(3):
                    image = Image.new('RGB', (200, 150), color=(i*80, i*80, i*80))
                    image_buffer = io.BytesIO()
                    image.save(image_buffer, format='PNG')
                    zip_file.writestr(f'OEBPS/image{i+1}.png', image_buffer.getvalue())
                
                zip_file.writestr('OEBPS/toc.ncx', '''<?xml version="1.0" encoding="UTF-8"?>
<ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/">
    <head><meta name="dtb:uid" content="medium-perf-test"/></head>
    <docTitle><text>Medium Performance Test</text></docTitle>
    <navMap><navPoint id="chapter1"><navLabel><text>Chapter 1</text></navLabel><content src="chapter1.xhtml"/></navPoint></navMap>
</ncx>''')
            
            yield temp_file.name
            
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    @pytest.fixture
    def large_epub(self):
        """Create a large EPUB file (10-40MB) for performance testing."""
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
                
                # Create content.opf with many chapters
                manifest_items = []
                spine_items = []
                for i in range(30):
                    manifest_items.append(f'<item id="chapter{i+1}" href="chapter{i+1}.xhtml" media-type="application/xhtml+xml"/>')
                    spine_items.append(f'<itemref idref="chapter{i+1}"/>')
                
                content_opf = f'''<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>Large Performance Test</dc:title>
    </metadata>
    <manifest>
        {chr(10).join(manifest_items)}
        <item id="toc" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="toc">
        {chr(10).join(spine_items)}
    </spine>
</package>'''
                zip_file.writestr('OEBPS/content.opf', content_opf)
                
                # Add many chapters with large content
                for i in range(30):
                    chapter_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter {i+1}</title></head>
<body>
    <h1>Chapter {i+1}: Large File Performance Test</h1>
    {'<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>' * 100}
</body>
</html>'''
                    zip_file.writestr(f'OEBPS/chapter{i+1}.xhtml', chapter_content)
                
                # Add 10 larger images
                for i in range(10):
                    image = Image.new('RGB', (400, 300), color=(i*25, i*25, i*25))
                    image_buffer = io.BytesIO()
                    image.save(image_buffer, format='PNG')
                    zip_file.writestr(f'OEBPS/large_image{i+1}.png', image_buffer.getvalue())
                
                zip_file.writestr('OEBPS/toc.ncx', '''<?xml version="1.0" encoding="UTF-8"?>
<ncx version="2005-1" xmlns="http://www.daisy.org/z3986/2005/ncx/">
    <head><meta name="dtb:uid" content="large-perf-test"/></head>
    <docTitle><text>Large Performance Test</text></docTitle>
    <navMap><navPoint id="chapter1"><navLabel><text>Chapter 1</text></navLabel><content src="chapter1.xhtml"/></navPoint></navMap>
</ncx>''')
            
            yield temp_file.name
            
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    def test_small_file_response_time(self, client, small_epub):
        """Test response time for small files (<1MB) - target <2 seconds."""
        response_times = []
        
        for i in range(5):
            start_time = time.time()
            
            with open(small_epub, 'rb') as epub_file:
                response = client.post(
                    "/upload-epub",
                    files={"file": (f"small_test_{i}.epub", epub_file, "application/epub+zip")}
                )
            
            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)
            
            assert response.status_code == 200
        
        avg_response_time = mean(response_times)
        median_response_time = median(response_times)
        max_response_time = max(response_times)
        
        print(f"Small file performance - Avg: {avg_response_time:.2f}s, Median: {median_response_time:.2f}s, Max: {max_response_time:.2f}s")
        
        # Performance target: <2 seconds for small files
        assert avg_response_time < 2.0, f"Average response time {avg_response_time:.2f}s exceeds 2s target"
        assert max_response_time < 3.0, f"Max response time {max_response_time:.2f}s exceeds 3s threshold"
    
    def test_medium_file_response_time(self, client, medium_epub):
        """Test response time for medium files (1-10MB) - target <10 seconds."""
        response_times = []
        
        for i in range(3):
            start_time = time.time()
            
            with open(medium_epub, 'rb') as epub_file:
                response = client.post(
                    "/upload-epub",
                    files={"file": (f"medium_test_{i}.epub", epub_file, "application/epub+zip")}
                )
            
            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)
            
            assert response.status_code == 200
        
        avg_response_time = mean(response_times)
        median_response_time = median(response_times)
        max_response_time = max(response_times)
        
        print(f"Medium file performance - Avg: {avg_response_time:.2f}s, Median: {median_response_time:.2f}s, Max: {max_response_time:.2f}s")
        
        # Performance target: <10 seconds for medium files
        assert avg_response_time < 10.0, f"Average response time {avg_response_time:.2f}s exceeds 10s target"
        assert max_response_time < 15.0, f"Max response time {max_response_time:.2f}s exceeds 15s threshold"
    
    def test_large_file_response_time(self, client, large_epub):
        """Test response time for large files (10-50MB) - target <30 seconds."""
        response_times = []
        
        for i in range(2):  # Only 2 iterations for large files
            start_time = time.time()
            
            with open(large_epub, 'rb') as epub_file:
                response = client.post(
                    "/upload-epub",
                    files={"file": (f"large_test_{i}.epub", epub_file, "application/epub+zip")}
                )
            
            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)
            
            assert response.status_code == 200
        
        avg_response_time = mean(response_times)
        max_response_time = max(response_times)
        
        print(f"Large file performance - Avg: {avg_response_time:.2f}s, Max: {max_response_time:.2f}s")
        
        # Performance target: <30 seconds for large files
        assert avg_response_time < 30.0, f"Average response time {avg_response_time:.2f}s exceeds 30s target"
        assert max_response_time < 45.0, f"Max response time {max_response_time:.2f}s exceeds 45s threshold"
    
    def test_memory_usage_small_file(self, client, small_epub):
        """Test memory usage for small file processing."""
        process = psutil.Process()
        
        # Force garbage collection before test
        gc.collect()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        with open(small_epub, 'rb') as epub_file:
            response = client.post(
                "/upload-epub",
                files={"file": ("memory_test_small.epub", epub_file, "application/epub+zip")}
            )
        
        gc.collect()
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before
        
        assert response.status_code == 200
        
        # Small file should use minimal memory (less than 50MB increase)
        print(f"Small file memory usage: {memory_increase:.2f}MB increase")
        assert memory_increase < 50, f"Memory increase {memory_increase:.2f}MB exceeds 50MB threshold"
    
    def test_memory_usage_medium_file(self, client, medium_epub):
        """Test memory usage for medium file processing."""
        process = psutil.Process()
        
        gc.collect()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        with open(medium_epub, 'rb') as epub_file:
            response = client.post(
                "/upload-epub",
                files={"file": ("memory_test_medium.epub", epub_file, "application/epub+zip")}
            )
        
        gc.collect()
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before
        
        assert response.status_code == 200
        
        # Medium file should use reasonable memory (less than 150MB increase)
        print(f"Medium file memory usage: {memory_increase:.2f}MB increase")
        assert memory_increase < 150, f"Memory increase {memory_increase:.2f}MB exceeds 150MB threshold"
    
    def test_concurrent_request_performance(self, client, small_epub):
        """Test performance with concurrent requests - target 10 concurrent."""
        num_concurrent = 10
        response_times = []
        
        def make_request(request_id):
            start_time = time.time()
            
            with open(small_epub, 'rb') as epub_file:
                response = client.post(
                    "/upload-epub",
                    files={"file": (f"concurrent_test_{request_id}.epub", epub_file, "application/epub+zip")}
                )
            
            end_time = time.time()
            return response, end_time - start_time
        
        start_total = time.time()
        
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_concurrent)]
            results = [future.result() for future in as_completed(futures)]
        
        end_total = time.time()
        total_time = end_total - start_total
        
        # Check all responses succeeded
        for response, response_time in results:
            assert response.status_code == 200
            response_times.append(response_time)
        
        avg_response_time = mean(response_times)
        max_response_time = max(response_times)
        
        print(f"Concurrent performance - {num_concurrent} requests in {total_time:.2f}s")
        print(f"Average response time: {avg_response_time:.2f}s, Max: {max_response_time:.2f}s")
        
        # All concurrent requests should complete reasonably quickly
        assert total_time < 15.0, f"Total time {total_time:.2f}s for {num_concurrent} concurrent requests exceeds 15s"
        assert avg_response_time < 5.0, f"Average response time {avg_response_time:.2f}s exceeds 5s under load"
    
    @pytest.mark.asyncio
    async def test_processing_performance_breakdown(self, processor, medium_epub):
        """Test performance breakdown of different processing stages."""
        # Test text extraction performance
        start_time = time.time()
        
        from ebooklib import epub
        book = epub.read_epub(medium_epub)
        text_result = await processor._extract_text_content(book)
        
        text_extraction_time = time.time() - start_time
        
        # Test image extraction performance
        start_time = time.time()
        image_result = await processor._extract_image_text(medium_epub)
        image_extraction_time = time.time() - start_time
        
        # Test overall performance
        start_time = time.time()
        full_result = await processor.extract_text(medium_epub)
        full_extraction_time = time.time() - start_time
        
        print(f"Performance breakdown:")
        print(f"  Text extraction: {text_extraction_time:.2f}s")
        print(f"  Image extraction: {image_extraction_time:.2f}s") 
        print(f"  Full extraction: {full_extraction_time:.2f}s")
        
        # Verify results
        assert len(text_result) > 0
        assert len(image_result) > 0
        assert len(full_result) > 0
        
        # Performance expectations
        assert text_extraction_time < 2.0, f"Text extraction took {text_extraction_time:.2f}s"
        assert image_extraction_time < 5.0, f"Image extraction took {image_extraction_time:.2f}s"
        assert full_extraction_time < 10.0, f"Full extraction took {full_extraction_time:.2f}s"
    
    def test_cpu_usage_monitoring(self, client, medium_epub):
        """Test CPU usage during processing."""
        process = psutil.Process()
        
        # Monitor CPU usage during processing
        cpu_percentages = []
        
        def monitor_cpu():
            for _ in range(20):  # Monitor for ~2 seconds
                cpu_percentages.append(process.cpu_percent(interval=0.1))
        
        # Start CPU monitoring in background
        monitor_thread = threading.Thread(target=monitor_cpu)
        monitor_thread.start()
        
        # Process file
        with open(medium_epub, 'rb') as epub_file:
            response = client.post(
                "/upload-epub",
                files={"file": ("cpu_test.epub", epub_file, "application/epub+zip")}
            )
        
        monitor_thread.join()
        
        assert response.status_code == 200
        
        if cpu_percentages:
            avg_cpu = mean(cpu_percentages)
            max_cpu = max(cpu_percentages)
            
            print(f"CPU usage - Average: {avg_cpu:.1f}%, Max: {max_cpu:.1f}%")
            
            # CPU usage should be reasonable (not constantly at 100%)
            assert avg_cpu < 80.0, f"Average CPU usage {avg_cpu:.1f}% too high"
    
    def test_throughput_measurement(self, client, small_epub):
        """Test system throughput (requests per second)."""
        num_requests = 20
        start_time = time.time()
        
        successful_requests = 0
        
        for i in range(num_requests):
            with open(small_epub, 'rb') as epub_file:
                response = client.post(
                    "/upload-epub",
                    files={"file": (f"throughput_test_{i}.epub", epub_file, "application/epub+zip")}
                )
                
                if response.status_code == 200:
                    successful_requests += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        
        throughput = successful_requests / total_time
        
        print(f"Throughput: {throughput:.2f} requests/second ({successful_requests}/{num_requests} successful)")
        
        # Should handle at least 2 requests per second for small files
        assert throughput >= 2.0, f"Throughput {throughput:.2f} req/s below 2 req/s target"
        assert successful_requests >= num_requests * 0.9, f"Success rate {successful_requests/num_requests:.1%} below 90%"
    
    def test_benchmark_recording(self, client, small_epub, medium_epub):
        """Record benchmark results for tracking performance over time."""
        benchmark_results = {
            "timestamp": time.time(),
            "small_file": {},
            "medium_file": {},
            "system_info": {
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total / 1024 / 1024 / 1024  # GB
            }
        }
        
        # Benchmark small file
        start_time = time.time()
        with open(small_epub, 'rb') as epub_file:
            response = client.post(
                "/upload-epub",
                files={"file": ("benchmark_small.epub", epub_file, "application/epub+zip")}
            )
        small_time = time.time() - start_time
        
        benchmark_results["small_file"] = {
            "response_time": small_time,
            "status_code": response.status_code,
            "file_size": os.path.getsize(small_epub) / 1024 / 1024  # MB
        }
        
        # Benchmark medium file
        start_time = time.time()
        with open(medium_epub, 'rb') as epub_file:
            response = client.post(
                "/upload-epub",
                files={"file": ("benchmark_medium.epub", epub_file, "application/epub+zip")}
            )
        medium_time = time.time() - start_time
        
        benchmark_results["medium_file"] = {
            "response_time": medium_time,
            "status_code": response.status_code,
            "file_size": os.path.getsize(medium_epub) / 1024 / 1024  # MB
        }
        
        # Save benchmark results (in real scenario, this would be saved to a file)
        print("Benchmark Results:")
        print(json.dumps(benchmark_results, indent=2))
        
        # Verify benchmarks meet targets
        assert benchmark_results["small_file"]["response_time"] < 2.0
        assert benchmark_results["medium_file"]["response_time"] < 10.0
        assert benchmark_results["small_file"]["status_code"] == 200
        assert benchmark_results["medium_file"]["status_code"] == 200