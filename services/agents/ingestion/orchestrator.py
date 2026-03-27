# app/services/ingestion/orchestrator.py
from typing import Optional, List, Dict, Any
from fastapi import UploadFile
import uuid
import logging
from datetime import datetime
from ingestion.pdf import PDFProcessor
from ingestion.web import WebScraper
from ingestion.chunking import chunk_text
from services.rag.rag import RAGService
from core.config import settings

logger = logging.getLogger(__name__)

class IngestionOrchestrator:
    def __init__(self, tenant_id: int):
        """Initialize ingestion orchestrator for a specific tenant"""
        self.tenant_id = tenant_id
        self.pdf_processor = PDFProcessor()
        self.web_scraper = WebScraper()
        self.rag_service = RAGService(tenant_id)
    
    async def process_document(
        self, 
        file: UploadFile, 
        user_id: int,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Process an uploaded document"""
        try:
            # Validate file
            if not file.filename:
                raise ValueError("File has no filename")
            
            # Extract text based on file type
            file_extension = file.filename.split('.')[-1].lower()
            
            if file_extension == 'pdf':
                text = await self.pdf_processor.extract_text(file)
                file_type = "pdf"
            elif file_extension in ['txt', 'md', 'text']:
                text = await self.pdf_processor.extract_text_from_text(file)
                file_type = "text"
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            if not text or len(text.strip()) == 0:
                raise ValueError("No text content extracted from file")
            
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Chunk the text
            chunks = chunk_text(text)
            
            if not chunks:
                logger.warning(f"No chunks generated for {file.filename}")
                return {
                    "document_id": doc_id,
                    "filename": file.filename,
                    "chunks_processed": 0,
                    "status": "warning",
                    "message": "No chunks generated from document"
                }
            
            # Prepare documents for vector store
            documents = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                documents.append(chunk)
                metadatas.append({
                    "tenant_id": self.tenant_id,
                    "user_id": user_id,
                    "document_id": doc_id,
                    "filename": file.filename,
                    "file_type": file_type,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "uploaded_at": datetime.utcnow().isoformat(),
                    **(metadata or {})
                })
                ids.append(chunk_id)
            
            # Add to vector store (using async method)
            await self.rag_service.process_and_store(
                text=text,
                source=file.filename,
                doc_id_prefix=doc_id,
                user_id=user_id,
                metadata=metadata
            )
            
            logger.info(f"Processed {file.filename} for tenant {self.tenant_id}: {len(chunks)} chunks")
            
            return {
                "document_id": doc_id,
                "filename": file.filename,
                "chunks_processed": len(chunks),
                "status": "success",
                "file_type": file_type,
                "tenant_id": self.tenant_id
            }
        
        except Exception as e:
            logger.error(f"Document processing error for tenant {self.tenant_id}: {str(e)}")
            return {
                "document_id": None,
                "filename": file.filename if file else "unknown",
                "chunks_processed": 0,
                "status": "error",
                "error": str(e),
                "tenant_id": self.tenant_id
            }
    
    async def process_url(
        self, 
        url: str, 
        user_id: int,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Process a URL for web scraping"""
        try:
            # Scrape the URL
            text = await self.web_scraper.scrape(url)
            
            if not text or len(text.strip()) == 0:
                raise ValueError(f"No content extracted from URL: {url}")
            
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Chunk the text
            chunks = chunk_text(text)
            
            if not chunks:
                logger.warning(f"No chunks generated for URL: {url}")
                return {
                    "document_id": doc_id,
                    "url": url,
                    "chunks_processed": 0,
                    "status": "warning",
                    "message": "No chunks generated from URL"
                }
            
            # Prepare documents
            documents = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                documents.append(chunk)
                metadatas.append({
                    "tenant_id": self.tenant_id,
                    "user_id": user_id,
                    "document_id": doc_id,
                    "url": url,
                    "source_type": "web",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "scraped_at": datetime.utcnow().isoformat(),
                    **(metadata or {})
                })
                ids.append(chunk_id)
            
            # Add to vector store
            await self.rag_service.process_and_store(
                text=text,
                source=url,
                doc_id_prefix=doc_id,
                user_id=user_id,
                metadata={"source_type": "web", **metadata} if metadata else {"source_type": "web"}
            )
            
            logger.info(f"Processed URL {url} for tenant {self.tenant_id}: {len(chunks)} chunks")
            
            return {
                "document_id": doc_id,
                "url": url,
                "chunks_processed": len(chunks),
                "status": "success",
                "tenant_id": self.tenant_id
            }
        
        except Exception as e:
            logger.error(f"URL processing error for tenant {self.tenant_id}: {str(e)}")
            return {
                "document_id": None,
                "url": url,
                "chunks_processed": 0,
                "status": "error",
                "error": str(e),
                "tenant_id": self.tenant_id
            }
    
    async def process_text(
        self,
        text: str,
        source: str,
        user_id: int,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Process raw text"""
        try:
            if not text or len(text.strip()) == 0:
                raise ValueError("No text content provided")
            
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Chunk the text
            chunks = chunk_text(text)
            
            if not chunks:
                return {
                    "document_id": doc_id,
                    "source": source,
                    "chunks_processed": 0,
                    "status": "warning",
                    "message": "No chunks generated from text"
                }
            
            # Add to vector store
            await self.rag_service.process_and_store(
                text=text,
                source=source,
                doc_id_prefix=doc_id,
                user_id=user_id,
                metadata=metadata
            )
            
            logger.info(f"Processed text from {source} for tenant {self.tenant_id}: {len(chunks)} chunks")
            
            return {
                "document_id": doc_id,
                "source": source,
                "chunks_processed": len(chunks),
                "status": "success",
                "tenant_id": self.tenant_id
            }
        
        except Exception as e:
            logger.error(f"Text processing error: {str(e)}")
            return {
                "document_id": None,
                "source": source,
                "chunks_processed": 0,
                "status": "error",
                "error": str(e),
                "tenant_id": self.tenant_id
            }
    
    async def process_batch(
        self,
        files: List[UploadFile],
        user_id: int,
        metadata: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Process multiple documents in batch"""
        results = []
        for file in files:
            result = await self.process_document(file, user_id, metadata)
            results.append(result)
        
        return results