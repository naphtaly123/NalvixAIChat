# import fitz  # PyMuPDF
# from typing import List
# import io

# def extract_text_from_pdf(file_content: bytes) -> str:
#     """Extract all text from PDF"""
#     text = ""
#     with fitz.open(stream=file_content, filetype="pdf") as doc:
#         for page in doc:
#             text += page.get_text()
#     return text

# app/services/ingestion/pdf.py


import fitz  # PyMuPDF
from typing import List, Optional
import io
import logging
from fastapi import UploadFile

logger = logging.getLogger(__name__)

class PDFProcessor:
    """PDF processing service using PyMuPDF"""
    
    async def extract_text(self, file: UploadFile) -> str:
        """Extract text from uploaded PDF file"""
        try:
            content = await file.read()
            return self.extract_text_from_bytes(content)
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            raise
    
    def extract_text_from_bytes(self, file_content: bytes) -> str:
        """Extract all text from PDF bytes"""
        try:
            text = ""
            # Open PDF from bytes
            with fitz.open(stream=file_content, filetype="pdf") as doc:
                for page_num, page in enumerate(doc):
                    page_text = page.get_text()
                    if page_text:
                        text += page_text + "\n"
                    logger.debug(f"Extracted text from page {page_num + 1}: {len(page_text)} chars")
            
            if not text.strip():
                logger.warning("No text extracted from PDF")
                return ""
            
            return text.strip()
        
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise
    
    async def extract_text_from_text(self, file: UploadFile) -> str:
        """Extract text from plain text file"""
        try:
            content = await file.read()
            text = content.decode('utf-8')
            return text.strip()
        except UnicodeDecodeError:
            # Try different encoding
            try:
                text = content.decode('latin-1')
                return text.strip()
            except Exception as e:
                logger.error(f"Error decoding text file: {str(e)}")
                raise
    
    def extract_metadata(self, file_content: bytes) -> dict:
        """Extract metadata from PDF"""
        try:
            with fitz.open(stream=file_content, filetype="pdf") as doc:
                metadata = doc.metadata
                return {
                    "title": metadata.get("title", ""),
                    "author": metadata.get("author", ""),
                    "subject": metadata.get("subject", ""),
                    "keywords": metadata.get("keywords", ""),
                    "pages": len(doc)
                }
        except Exception as e:
            logger.error(f"Error extracting PDF metadata: {str(e)}")
            return {}
    
    def extract_text_by_pages(self, file_content: bytes) -> List[str]:
        """Extract text page by page"""
        try:
            pages_text = []
            with fitz.open(stream=file_content, filetype="pdf") as doc:
                for page in doc:
                    pages_text.append(page.get_text())
            return pages_text
        except Exception as e:
            logger.error(f"Error extracting PDF by pages: {str(e)}")
            return []