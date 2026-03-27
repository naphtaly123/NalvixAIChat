# app/api/v1/endpoints/ingestion.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from models.schemas import DocumentResponse, WebScrapeRequest, BatchProcessResponse
from services.agents.ingestion.orchestrator import IngestionOrchestrator
from core.database import get_db
from core.security import get_current_tenant, get_current_user
from models.tenant import Tenant, User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Ingestion"])

@router.post("/upload-pdf", response_model=DocumentResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and process a PDF document for the current tenant
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400, 
            detail="Only PDF files are allowed"
        )
    
    # Validate file size (e.g., 10MB limit)
    max_size = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {max_size // (1024*1024)}MB"
        )
    
    try:
        # Initialize ingestion orchestrator for this tenant
        ingestion = IngestionOrchestrator(tenant.id)
        
        # Process the document
        result = await ingestion.process_document(
            file=file,
            user_id=user.id,
            metadata={
                "uploaded_by": user.email,
                "tenant_name": tenant.name,
                "file_size": len(content)
            }
        )
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Error processing document")
            )
        
        return DocumentResponse(
            status=result["status"],
            document_id=result["document_id"],
            filename=result["filename"],
            chunks_processed=result["chunks_processed"],
            tenant_id=tenant.id,
            message=result.get("message")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF upload error for tenant {tenant.id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {str(e)}"
        )

@router.post("/upload-text", response_model=DocumentResponse)
async def upload_text(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and process a text file (.txt, .md) for the current tenant
    """
    # Validate file type
    allowed_extensions = ['.txt', '.md', '.text']
    if not any(file.filename.endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Only text files are allowed: {', '.join(allowed_extensions)}"
        )
    
    try:
        ingestion = IngestionOrchestrator(tenant.id)
        
        result = await ingestion.process_document(
            file=file,
            user_id=user.id,
            metadata={
                "uploaded_by": user.email,
                "tenant_name": tenant.name
            }
        )
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Error processing document")
            )
        
        return DocumentResponse(
            status=result["status"],
            document_id=result["document_id"],
            filename=result["filename"],
            chunks_processed=result["chunks_processed"],
            tenant_id=tenant.id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text upload error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing text file: {str(e)}"
        )

@router.post("/scrape-website", response_model=DocumentResponse)
async def scrape_website_endpoint(
    request: WebScrapeRequest,
    background_tasks: BackgroundTasks = None,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Scrape a website and add the content to the knowledge base
    """
    try:
        ingestion = IngestionOrchestrator(tenant.id)
        
        # Validate URL format
        if not request.url.startswith(('http://', 'https://')):
            request.url = 'https://' + request.url
        
        result = await ingestion.process_url(
            url=request.url,
            user_id=user.id,
            metadata={
                "scraped_by": user.email,
                "tenant_name": tenant.name
            }
        )
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Error scraping website")
            )
        
        return DocumentResponse(
            status=result["status"],
            document_id=result["document_id"],
            filename=request.url,
            chunks_processed=result["chunks_processed"],
            tenant_id=tenant.id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Website scraping error for tenant {tenant.id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error scraping website: {str(e)}"
        )

@router.post("/upload-batch", response_model=BatchProcessResponse)
async def upload_batch(
    files: List[UploadFile] = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload and process multiple documents in batch
    """
    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 files per batch upload"
        )
    
    try:
        ingestion = IngestionOrchestrator(tenant.id)
        
        results = await ingestion.process_batch(
            files=files,
            user_id=user.id,
            metadata={
                "uploaded_by": user.email,
                "tenant_name": tenant.name,
                "batch_upload": True
            }
        )
        
        successful = [r for r in results if r["status"] == "success"]
        failed = [r for r in results if r["status"] == "error"]
        
        return BatchProcessResponse(
            total=len(results),
            successful=len(successful),
            failed=len(failed),
            results=results,
            tenant_id=tenant.id
        )
    
    except Exception as e:
        logger.error(f"Batch upload error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing batch: {str(e)}"
        )

@router.post("/process-text", response_model=DocumentResponse)
async def process_raw_text(
    text: str,
    source: str = "manual",
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process raw text directly
    """
    try:
        ingestion = IngestionOrchestrator(tenant.id)
        
        result = await ingestion.process_text(
            text=text,
            source=source,
            user_id=user.id,
            metadata={
                "processed_by": user.email,
                "tenant_name": tenant.name
            }
        )
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Error processing text")
            )
        
        return DocumentResponse(
            status=result["status"],
            document_id=result["document_id"],
            filename=source,
            chunks_processed=result["chunks_processed"],
            tenant_id=tenant.id
        )
    
    except Exception as e:
        logger.error(f"Text processing error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing text: {str(e)}"
        )

@router.get("/status/{document_id}")
async def get_ingestion_status(
    document_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get the status of a document ingestion
    """
    try:
        # Query document status from database
        # This would require a DocumentStatus table
        # For now, return basic info
        return {
            "document_id": document_id,
            "tenant_id": tenant.id,
            "status": "processing",
            "message": "Document is being processed"
        }
    
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting status: {str(e)}"
        )