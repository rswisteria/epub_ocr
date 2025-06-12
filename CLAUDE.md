# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an EPUB to text conversion API project built with Python. The API accepts EPUB files and returns their textual content, supporting both text-based and image-based EPUBs with OCR capability.

## Technology Stack

- **FastAPI**: Modern Python web framework for the API
- **PaddleOCR**: Deep learning-based OCR for image text extraction
- **ebooklib**: EPUB file parsing and processing
- **Pillow**: Image processing for OCR preparation
- **BeautifulSoup4**: HTML content parsing from EPUB files

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server
python main.py

# Run with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Architecture

- **main.py**: FastAPI application with upload endpoint
- **epub_processor.py**: Core EPUB processing and OCR functionality
- **EPUBProcessor class**: Handles both text extraction and OCR processing
- Async processing for better performance with large files
- Thread pool for OCR operations to prevent blocking

## API Endpoints

- `POST /upload-epub`: Upload EPUB file and get extracted text
- `GET /`: Health check endpoint

## Important Notes

- Files are temporarily stored and automatically cleaned up
- 50MB file size limit for uploads
- Supports parallel OCR processing for multiple images
- PaddleOCR configured for English text (can be extended for other languages)