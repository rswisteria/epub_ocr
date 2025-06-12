import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import os
import tempfile
import zipfile
from PIL import Image
import io
import asyncio
from concurrent.futures import ThreadPoolExecutor
from paddleocr import PaddleOCR
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EPUBProcessor:
    def __init__(self):
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en')
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def extract_text(self, epub_path: str) -> str:
        """Extract text from EPUB file with OCR support for images"""
        try:
            book = epub.read_epub(epub_path)
            all_text = []
            
            # Process text-based content
            text_content = await self._extract_text_content(book)
            if text_content:
                all_text.append(text_content)
            
            # Process image-based content with OCR
            image_text = await self._extract_image_text(epub_path)
            if image_text:
                all_text.append(image_text)
            
            return "\n\n".join(all_text)
        
        except Exception as e:
            logger.error(f"Error extracting text from EPUB: {e}")
            raise
    
    async def _extract_text_content(self, book) -> str:
        """Extract text from HTML content in EPUB"""
        text_parts = []
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                text = soup.get_text(separator=' ', strip=True)
                if text:
                    text_parts.append(text)
        
        return "\n\n".join(text_parts)
    
    async def _extract_image_text(self, epub_path: str) -> str:
        """Extract text from images in EPUB using OCR"""
        image_texts = []
        
        try:
            with zipfile.ZipFile(epub_path, 'r') as zip_file:
                image_files = [f for f in zip_file.namelist() 
                             if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
                
                if not image_files:
                    return ""
                
                # Process images in parallel
                tasks = []
                for image_file in image_files:
                    task = self._process_image_from_zip(zip_file, image_file)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, str) and result:
                        image_texts.append(result)
                    elif isinstance(result, Exception):
                        logger.warning(f"Error processing image: {result}")
        
        except Exception as e:
            logger.error(f"Error extracting images from EPUB: {e}")
        
        return "\n\n".join(image_texts)
    
    async def _process_image_from_zip(self, zip_file, image_file: str) -> str:
        """Process a single image file with OCR"""
        try:
            image_data = zip_file.read(image_file)
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Run OCR in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            ocr_result = await loop.run_in_executor(
                self.executor, 
                self._run_ocr, 
                image
            )
            
            return ocr_result
        
        except Exception as e:
            logger.warning(f"Error processing image {image_file}: {e}")
            return ""
    
    def _run_ocr(self, image: Image.Image) -> str:
        """Run OCR on image"""
        try:
            # Convert PIL Image to numpy array for PaddleOCR
            import numpy as np
            img_array = np.array(image)
            
            result = self.ocr.ocr(img_array, cls=True)
            
            if not result or not result[0]:
                return ""
            
            # Extract text from OCR result
            text_parts = []
            for line in result[0]:
                if line and len(line) > 1:
                    text_parts.append(line[1][0])
            
            return " ".join(text_parts)
        
        except Exception as e:
            logger.warning(f"OCR processing failed: {e}")
            return ""