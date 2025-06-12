from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import os
import tempfile
import shutil
from epub_processor import EPUBProcessor

app = FastAPI(
    title="EPUB to Text API",
    description="Extract text from EPUB files with OCR support for image-based content",
    version="1.0.0"
)

epub_processor = EPUBProcessor()

@app.post("/upload-epub")
async def upload_epub(file: UploadFile = File(...)):
    """
    Upload an EPUB file and extract its text content.
    Supports both text-based and image-based EPUBs with OCR.
    """
    if not file.filename.lower().endswith('.epub'):
        raise HTTPException(status_code=400, detail="File must be an EPUB file")
    
    if file.size > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.epub') as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name
        
        extracted_text = await epub_processor.extract_text(temp_path)
        
        os.unlink(temp_path)
        
        return JSONResponse(content={
            "filename": file.filename,
            "text": extracted_text,
            "status": "success"
        })
    
    except Exception as e:
        if 'temp_path' in locals():
            os.unlink(temp_path)
        raise HTTPException(status_code=500, detail=f"Error processing EPUB: {str(e)}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "EPUB to Text API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)