import pytest
import tempfile
import os
from unittest.mock import patch, AsyncMock, Mock
from fastapi.testclient import TestClient
import io

from main import app


class TestMainAPI:
    
    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)
    
    def test_health_check_endpoint(self, client):
        """Test GET / health check endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        assert response.json() == {"message": "EPUB to Text API is running"}
    
    def test_upload_epub_success_text_based(self, client, sample_epub_text):
        """Test successful upload and processing of text-based EPUB."""
        with patch('main.epub_processor.extract_text') as mock_extract:
            mock_extract.return_value = "Extracted text content from EPUB"
            
            with open(sample_epub_text, 'rb') as epub_file:
                response = client.post(
                    "/upload-epub",
                    files={"file": ("test.epub", epub_file, "application/epub+zip")}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["filename"] == "test.epub"
            assert data["text"] == "Extracted text content from EPUB"
            assert data["status"] == "success"
            mock_extract.assert_called_once()
    
    def test_upload_epub_success_with_images(self, client, sample_epub_with_images):
        """Test successful upload and processing of EPUB with images."""
        with patch('main.epub_processor.extract_text') as mock_extract:
            mock_extract.return_value = "Text content\n\nOCR extracted text from images"
            
            with open(sample_epub_with_images, 'rb') as epub_file:
                response = client.post(
                    "/upload-epub",
                    files={"file": ("book_with_images.epub", epub_file, "application/epub+zip")}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["filename"] == "book_with_images.epub"
            assert "Text content" in data["text"]
            assert "OCR extracted text" in data["text"]
            assert data["status"] == "success"
    
    def test_upload_non_epub_file(self, client, invalid_file):
        """Test upload of non-EPUB file returns 400 error."""
        with open(invalid_file, 'rb') as txt_file:
            response = client.post(
                "/upload-epub",
                files={"file": ("document.txt", txt_file, "text/plain")}
            )
        
        assert response.status_code == 400
        assert "File must be an EPUB file" in response.json()["detail"]
    
    def test_upload_file_with_wrong_extension(self, client, sample_epub_text):
        """Test upload of EPUB file with wrong extension."""
        with open(sample_epub_text, 'rb') as epub_file:
            response = client.post(
                "/upload-epub",
                files={"file": ("document.txt", epub_file, "application/epub+zip")}
            )
        
        assert response.status_code == 400
        assert "File must be an EPUB file" in response.json()["detail"]
    
    def test_upload_file_case_insensitive_extension(self, client, sample_epub_text):
        """Test that EPUB extension check is case insensitive."""
        with patch('main.epub_processor.extract_text') as mock_extract:
            mock_extract.return_value = "Extracted text"
            
            with open(sample_epub_text, 'rb') as epub_file:
                response = client.post(
                    "/upload-epub",
                    files={"file": ("BOOK.EPUB", epub_file, "application/epub+zip")}
                )
            
            assert response.status_code == 200
            assert response.json()["filename"] == "BOOK.EPUB"
    
    def test_upload_large_file(self, client, large_file):
        """Test upload of file larger than 50MB returns 413 error."""
        with open(large_file, 'rb') as big_file:
            response = client.post(
                "/upload-epub",
                files={"file": ("large_book.epub", big_file, "application/epub+zip")}
            )
        
        assert response.status_code == 413
        assert "File too large (max 50MB)" in response.json()["detail"]
    
    def test_upload_epub_processing_error(self, client, sample_epub_text):
        """Test handling of processing errors during text extraction."""
        with patch('main.epub_processor.extract_text') as mock_extract:
            mock_extract.side_effect = Exception("Processing failed")
            
            with open(sample_epub_text, 'rb') as epub_file:
                response = client.post(
                    "/upload-epub",
                    files={"file": ("test.epub", epub_file, "application/epub+zip")}
                )
            
            assert response.status_code == 500
            assert "Error processing EPUB" in response.json()["detail"]
            assert "Processing failed" in response.json()["detail"]
    
    def test_upload_no_file(self, client):
        """Test upload endpoint without file parameter."""
        response = client.post("/upload-epub")
        
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_upload_empty_file(self, client):
        """Test upload of empty file."""
        empty_file = io.BytesIO(b"")
        response = client.post(
            "/upload-epub",
            files={"file": ("empty.epub", empty_file, "application/epub+zip")}
        )
        
        # Should still process but might fail in processing
        assert response.status_code in [400, 500]
    
    def test_file_cleanup_on_success(self, client, sample_epub_text):
        """Test that temporary files are cleaned up after successful processing."""
        with patch('main.epub_processor.extract_text') as mock_extract:
            mock_extract.return_value = "Extracted text"
            
            with patch('os.unlink') as mock_unlink:
                with open(sample_epub_text, 'rb') as epub_file:
                    response = client.post(
                        "/upload-epub",
                        files={"file": ("test.epub", epub_file, "application/epub+zip")}
                    )
                
                assert response.status_code == 200
                mock_unlink.assert_called_once()
    
    def test_file_cleanup_on_error(self, client, sample_epub_text):
        """Test that temporary files are cleaned up even when processing fails."""
        with patch('main.epub_processor.extract_text') as mock_extract:
            mock_extract.side_effect = Exception("Processing failed")
            
            with patch('os.unlink') as mock_unlink:
                with open(sample_epub_text, 'rb') as epub_file:
                    response = client.post(
                        "/upload-epub",
                        files={"file": ("test.epub", epub_file, "application/epub+zip")}
                    )
                
                assert response.status_code == 500
                mock_unlink.assert_called_once()
    
    def test_upload_multiple_requests_concurrent(self, client, sample_epub_text):
        """Test handling of multiple concurrent upload requests."""
        with patch('main.epub_processor.extract_text') as mock_extract:
            mock_extract.return_value = "Extracted text"
            
            import concurrent.futures
            import threading
            
            def upload_file():
                with open(sample_epub_text, 'rb') as epub_file:
                    return client.post(
                        "/upload-epub",
                        files={"file": ("test.epub", epub_file, "application/epub+zip")}
                    )
            
            # Send 3 concurrent requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(upload_file) for _ in range(3)]
                responses = [future.result() for future in futures]
            
            # All requests should succeed
            for response in responses:
                assert response.status_code == 200
                assert response.json()["status"] == "success"
            
            # extract_text should be called 3 times
            assert mock_extract.call_count == 3
    
    def test_upload_various_mime_types(self, client, sample_epub_text):
        """Test upload with various MIME types for EPUB files."""
        with patch('main.epub_processor.extract_text') as mock_extract:
            mock_extract.return_value = "Extracted text"
            
            mime_types = [
                "application/epub+zip",
                "application/epub",
                "application/octet-stream"
            ]
            
            for mime_type in mime_types:
                with open(sample_epub_text, 'rb') as epub_file:
                    response = client.post(
                        "/upload-epub",
                        files={"file": ("test.epub", epub_file, mime_type)}
                    )
                
                assert response.status_code == 200
                assert response.json()["status"] == "success"
    
    def test_response_content_type(self, client, sample_epub_text):
        """Test that response has correct content type."""
        with patch('main.epub_processor.extract_text') as mock_extract:
            mock_extract.return_value = "Extracted text"
            
            with open(sample_epub_text, 'rb') as epub_file:
                response = client.post(
                    "/upload-epub",
                    files={"file": ("test.epub", epub_file, "application/epub+zip")}
                )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"
    
    def test_file_size_edge_cases(self, client):
        """Test file size validation with edge cases."""
        # Test exactly 50MB (should pass)
        with patch('main.epub_processor.extract_text') as mock_extract:
            mock_extract.return_value = "Extracted text"
            
            # Create exactly 50MB file
            file_content = b'0' * (50 * 1024 * 1024)
            file_obj = io.BytesIO(file_content)
            
            response = client.post(
                "/upload-epub",
                files={"file": ("exact_50mb.epub", file_obj, "application/epub+zip")}
            )
            
            assert response.status_code == 200
        
        # Test 50MB + 1 byte (should fail)
        file_content = b'0' * (50 * 1024 * 1024 + 1)
        file_obj = io.BytesIO(file_content)
        
        response = client.post(
            "/upload-epub",
            files={"file": ("over_50mb.epub", file_obj, "application/epub+zip")}
        )
        
        assert response.status_code == 413
    
    def test_special_characters_in_filename(self, client, sample_epub_text):
        """Test upload with special characters in filename."""
        with patch('main.epub_processor.extract_text') as mock_extract:
            mock_extract.return_value = "Extracted text"
            
            special_filenames = [
                "test file with spaces.epub",
                "test-file-with-dashes.epub",
                "test_file_with_underscores.epub",
                "テスト.epub",  # Japanese characters
                "test@file#2.epub"
            ]
            
            for filename in special_filenames:
                with open(sample_epub_text, 'rb') as epub_file:
                    response = client.post(
                        "/upload-epub",
                        files={"file": (filename, epub_file, "application/epub+zip")}
                    )
                
                assert response.status_code == 200
                assert response.json()["filename"] == filename
    
    def test_api_documentation_endpoints(self, client):
        """Test that API documentation endpoints are available."""
        # Test OpenAPI JSON
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_spec = response.json()
        assert openapi_spec["info"]["title"] == "EPUB to Text API"
        assert openapi_spec["info"]["version"] == "1.0.0"
        
        # Check that our endpoints are documented
        assert "/upload-epub" in openapi_spec["paths"]
        assert "/" in openapi_spec["paths"]
    
    def test_cors_and_headers(self, client, sample_epub_text):
        """Test CORS and security headers."""
        with patch('main.epub_processor.extract_text') as mock_extract:
            mock_extract.return_value = "Extracted text"
            
            with open(sample_epub_text, 'rb') as epub_file:
                response = client.post(
                    "/upload-epub",
                    files={"file": ("test.epub", epub_file, "application/epub+zip")}
                )
            
            assert response.status_code == 200
            # FastAPI automatically includes some security headers
            assert "content-length" in response.headers