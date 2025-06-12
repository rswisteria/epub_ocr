import pytest
import asyncio
import zipfile
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from PIL import Image
import io
import numpy as np

from epub_processor import EPUBProcessor


class TestEPUBProcessor:
    
    @pytest.fixture
    def processor(self, mock_paddleocr):
        """Create EPUBProcessor with mocked OCR."""
        with patch('epub_processor.PaddleOCR') as mock_ocr_class:
            mock_ocr_class.return_value = mock_paddleocr
            processor = EPUBProcessor()
            return processor
    
    @pytest.mark.asyncio
    async def test_extract_text_from_text_based_epub(self, processor, sample_epub_text):
        """Test extracting text from a text-based EPUB file."""
        result = await processor.extract_text(sample_epub_text)
        
        assert "Chapter 1: Introduction" in result
        assert "This is a test chapter" in result
        assert "testing the text extraction" in result
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_extract_text_from_epub_with_images(self, processor, sample_epub_with_images):
        """Test extracting text from EPUB with images using OCR."""
        result = await processor.extract_text(sample_epub_with_images)
        
        # Should contain both HTML text and OCR text
        assert "Chapter 1: Images" in result
        assert "Sample OCR text" in result
        assert "More OCR text" in result
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_extract_text_content_only(self, processor, sample_epub_text):
        """Test _extract_text_content method specifically."""
        from ebooklib import epub
        
        book = epub.read_epub(sample_epub_text)
        result = await processor._extract_text_content(book)
        
        assert "Chapter 1: Introduction" in result
        assert "This is a test chapter" in result
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_extract_text_content_empty_book(self, processor):
        """Test _extract_text_content with empty book."""
        mock_book = Mock()
        mock_book.get_items.return_value = []
        
        result = await processor._extract_text_content(mock_book)
        
        assert result == ""
    
    @pytest.mark.asyncio
    async def test_extract_image_text_with_images(self, processor, sample_epub_with_images):
        """Test _extract_image_text method with actual images."""
        result = await processor._extract_image_text(sample_epub_with_images)
        
        assert "Sample OCR text" in result
        assert "More OCR text" in result
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_extract_image_text_no_images(self, processor, sample_epub_text):
        """Test _extract_image_text with EPUB that has no images."""
        result = await processor._extract_image_text(sample_epub_text)
        
        assert result == ""
    
    @pytest.mark.asyncio
    async def test_extract_image_text_invalid_zip(self, processor):
        """Test _extract_image_text with invalid ZIP file."""
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
            temp_file.write(b"not a valid zip file")
            temp_file.flush()
            
            try:
                result = await processor._extract_image_text(temp_file.name)
                assert result == ""
            finally:
                os.unlink(temp_file.name)
    
    @pytest.mark.asyncio
    async def test_process_image_from_zip_success(self, processor):
        """Test _process_image_from_zip with valid image."""
        # Create a test ZIP file with an image
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, 'w') as zip_file:
                # Create a simple test image
                image = Image.new('RGB', (100, 50), color='white')
                image_buffer = io.BytesIO()
                image.save(image_buffer, format='PNG')
                zip_file.writestr('test_image.png', image_buffer.getvalue())
            
            try:
                with zipfile.ZipFile(temp_file.name, 'r') as zip_file:
                    result = await processor._process_image_from_zip(zip_file, 'test_image.png')
                    
                    assert "Sample OCR text" in result
                    assert isinstance(result, str)
            finally:
                os.unlink(temp_file.name)
    
    @pytest.mark.asyncio
    async def test_process_image_from_zip_missing_image(self, processor):
        """Test _process_image_from_zip with missing image file."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, 'w') as zip_file:
                zip_file.writestr('dummy.txt', 'dummy content')
            
            try:
                with zipfile.ZipFile(temp_file.name, 'r') as zip_file:
                    result = await processor._process_image_from_zip(zip_file, 'missing_image.png')
                    
                    assert result == ""
            finally:
                os.unlink(temp_file.name)
    
    @pytest.mark.asyncio
    async def test_process_image_from_zip_corrupted_image(self, processor):
        """Test _process_image_from_zip with corrupted image data."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, 'w') as zip_file:
                zip_file.writestr('corrupted.png', b'not an image')
            
            try:
                with zipfile.ZipFile(temp_file.name, 'r') as zip_file:
                    result = await processor._process_image_from_zip(zip_file, 'corrupted.png')
                    
                    assert result == ""
            finally:
                os.unlink(temp_file.name)
    
    def test_run_ocr_success(self, processor):
        """Test _run_ocr method with valid image."""
        image = Image.new('RGB', (100, 50), color='white')
        
        result = processor._run_ocr(image)
        
        assert "Sample OCR text" in result
        assert "More OCR text" in result
        assert isinstance(result, str)
    
    def test_run_ocr_empty_result(self, processor):
        """Test _run_ocr when OCR returns empty result."""
        image = Image.new('RGB', (100, 50), color='white')
        processor.ocr.ocr.return_value = None
        
        result = processor._run_ocr(image)
        
        assert result == ""
    
    def test_run_ocr_malformed_result(self, processor):
        """Test _run_ocr when OCR returns malformed result."""
        image = Image.new('RGB', (100, 50), color='white')
        processor.ocr.ocr.return_value = [[]]
        
        result = processor._run_ocr(image)
        
        assert result == ""
    
    def test_run_ocr_ocr_exception(self, processor):
        """Test _run_ocr when OCR raises an exception."""
        image = Image.new('RGB', (100, 50), color='white')
        processor.ocr.ocr.side_effect = Exception("OCR failed")
        
        result = processor._run_ocr(image)
        
        assert result == ""
    
    @pytest.mark.asyncio
    async def test_extract_text_epub_read_exception(self, processor):
        """Test extract_text when epub.read_epub raises an exception."""
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
            temp_file.write(b"invalid epub content")
            temp_file.flush()
            
            try:
                with pytest.raises(Exception):
                    await processor.extract_text(temp_file.name)
            finally:
                os.unlink(temp_file.name)
    
    @pytest.mark.asyncio
    async def test_extract_text_file_not_found(self, processor):
        """Test extract_text with non-existent file."""
        with pytest.raises(Exception):
            await processor.extract_text("/non/existent/file.epub")
    
    @pytest.mark.asyncio
    async def test_concurrent_image_processing(self, processor, sample_epub_with_images):
        """Test that multiple images are processed concurrently."""
        # Create EPUB with multiple images
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add basic EPUB structure
                zip_file.writestr('mimetype', 'application/epub+zip')
                
                # Add multiple test images
                for i in range(3):
                    image = Image.new('RGB', (100, 50), color='white')
                    image_buffer = io.BytesIO()
                    image.save(image_buffer, format='PNG')
                    zip_file.writestr(f'image_{i}.png', image_buffer.getvalue())
            
            try:
                result = await processor._extract_image_text(temp_file.name)
                
                # Should have processed all images
                text_lines = result.split('\n\n')
                assert len(text_lines) == 3  # One result per image
                assert all("Sample OCR text" in line for line in text_lines)
            finally:
                os.unlink(temp_file.name)
    
    @pytest.mark.asyncio
    async def test_image_format_conversion(self, processor):
        """Test that images are properly converted to RGB format."""
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, 'w') as zip_file:
                # Create a CMYK image (should be converted to RGB)
                image = Image.new('CMYK', (100, 50), color=(100, 0, 100, 0))
                image_buffer = io.BytesIO()
                image.save(image_buffer, format='JPEG')
                zip_file.writestr('cmyk_image.jpg', image_buffer.getvalue())
            
            try:
                with zipfile.ZipFile(temp_file.name, 'r') as zip_file:
                    result = await processor._process_image_from_zip(zip_file, 'cmyk_image.jpg')
                    
                    # Should successfully process and return OCR text
                    assert "Sample OCR text" in result
            finally:
                os.unlink(temp_file.name)
    
    def test_processor_initialization(self):
        """Test that EPUBProcessor initializes correctly."""
        with patch('epub_processor.PaddleOCR') as mock_ocr_class:
            with patch('epub_processor.ThreadPoolExecutor') as mock_executor_class:
                mock_ocr = Mock()
                mock_executor = Mock()
                mock_ocr_class.return_value = mock_ocr
                mock_executor_class.return_value = mock_executor
                
                processor = EPUBProcessor()
                
                assert processor.ocr == mock_ocr
                assert processor.executor == mock_executor
                mock_ocr_class.assert_called_once_with(use_angle_cls=True, lang='en')
                mock_executor_class.assert_called_once_with(max_workers=4)
    
    @pytest.mark.asyncio
    async def test_extract_text_combines_content_and_images(self, processor, sample_epub_with_images):
        """Test that extract_text properly combines text content and OCR results."""
        result = await processor.extract_text(sample_epub_with_images)
        
        # Should contain both parts separated by double newlines
        parts = result.split('\n\n')
        
        # Should have text content and image text
        assert len(parts) >= 2
        
        # Find the text content part
        text_content_found = False
        ocr_content_found = False
        
        for part in parts:
            if "Chapter 1: Images" in part:
                text_content_found = True
            if "Sample OCR text" in part:
                ocr_content_found = True
        
        assert text_content_found, "Text content not found in result"
        assert ocr_content_found, "OCR content not found in result"
    
    @pytest.mark.asyncio
    async def test_extract_image_text_image_file_filtering(self, processor):
        """Test that only image files are processed for OCR."""
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
            with zipfile.ZipFile(temp_file.name, 'w') as zip_file:
                # Add various file types
                zip_file.writestr('document.txt', 'text file')
                zip_file.writestr('style.css', 'css file')
                zip_file.writestr('script.js', 'js file')
                
                # Add image files
                image = Image.new('RGB', (100, 50), color='white')
                image_buffer = io.BytesIO()
                image.save(image_buffer, format='PNG')
                zip_file.writestr('image1.png', image_buffer.getvalue())
                zip_file.writestr('image2.jpg', image_buffer.getvalue())
                zip_file.writestr('image3.gif', image_buffer.getvalue())
            
            try:
                result = await processor._extract_image_text(temp_file.name)
                
                # Should have processed 3 images
                text_lines = [line for line in result.split('\n\n') if line.strip()]
                assert len(text_lines) == 3
            finally:
                os.unlink(temp_file.name)