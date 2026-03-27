# from fastapi import APIRouter, HTTPException
# from models.schemas import DeleteResponse
# from services.rag.vector_store import get_vector_store
# from typing import List

# router = APIRouter(prefix="/documents", tags=["Documents"])

# @router.get("/count")
# async def get_document_count():
#     vector_store = get_vector_store()
#     return {"chunks_count": vector_store.count()}

# @router.delete("/all", response_model=DeleteResponse)
# async def delete_all_documents(confirmation: str = "true"):
#     print(f"Received request to delete all documents with confirmation={confirmation}")
#     if confirmation.lower() != "true":
#         raise HTTPException(
#             status_code=400,
#             detail="Confirmation required. Set confirmation=true to delete all documents"
#         )
    
#     vector_store = get_vector_store()
#     count = vector_store.delete_all()
    
#     return DeleteResponse(
#         message="All documents deleted successfully",
#         count=count
#     )

# @router.delete("/{document_id}", response_model=DeleteResponse)
# async def delete_document(document_id: str):
#     vector_store = get_vector_store()
#     deleted = vector_store.delete_document(document_id)
    
#     if not deleted:
#         raise HTTPException(status_code=404, detail="Document not found")
    
#     return DeleteResponse(message="Document deleted successfully")

# @router.delete("", response_model=DeleteResponse)
# async def delete_multiple_documents(document_ids: List[str]):
#     vector_store = get_vector_store()
#     deleted_count = 0
#     failed_ids = []
    
#     for doc_id in document_ids:
#         if vector_store.delete_document(doc_id):
#             deleted_count += 1
#         else:
#             failed_ids.append(doc_id)
    
#     return DeleteResponse(
#         message=f"Deleted {deleted_count} out of {len(document_ids)} documents",
#         deleted_count=deleted_count,
#         failed_ids=failed_ids
#     )

# app/api/v1/endpoints/documents.py
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from models.schemas import DeleteResponse, DocumentUploadResponse, DocumentInfo
from services.rag.vector_store import TenantAwareVectorStore
from services.agents.ingestion.orchestrator import IngestionOrchestrator
from core.database import get_db
from core.security import get_current_tenant, get_current_user
from models.tenant import Tenant, User
import logging
from fastapi import UploadFile, File

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])

# Initialize vector store (tenant-aware)
def get_vector_store():
    """Get vector store instance (will be tenant-aware when used)"""
    return TenantAwareVectorStore()

@router.get("/count")
async def get_document_count(
    tenant: Tenant = Depends(get_current_tenant),
    collection_name: Optional[str] = None
):
    """Get document count for the current tenant"""
    try:
        vector_store = get_vector_store()
        
        # Get collection stats
        stats = vector_store.get_collection_stats(
            tenant_id=tenant.id,
            collection_name=collection_name
        )
        
        return {
            "chunks_count": stats.get("document_count", 0),
            "tenant_id": tenant.id,
            "tenant_name": tenant.name,
            "collection_name": stats.get("collection_name"),
            "exists": stats.get("exists", False)
        }
    except Exception as e:
        logger.error(f"Error getting document count for tenant {tenant.id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting document count: {str(e)}"
        )

@router.get("/collections")
async def list_collections(
    tenant: Tenant = Depends(get_current_tenant)
):
    """List all collections for the current tenant"""
    try:
        vector_store = get_vector_store()
        collections = vector_store.client.list_collections()
        
        # Filter collections for this tenant
        tenant_collections = [
            {
                "name": col.name,
                "count": col.count()
            }
            for col in collections
            if col.name.startswith(f"tenant_{tenant.id}_")
        ]
        
        return {
            "collections": tenant_collections,
            "total": len(tenant_collections),
            "tenant_id": tenant.id
        }
    except Exception as e:
        logger.error(f"Error listing collections: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error listing collections: {str(e)}"
        )

@router.get("/info")
async def get_document_info(
    tenant: Tenant = Depends(get_current_tenant),
    collection_name: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100)
):
    """Get information about documents in the tenant's collection"""
    try:
        vector_store = get_vector_store()
        collection = vector_store.get_or_create_collection(tenant.id, collection_name)
        
        # Get a sample of documents (peek at first few)
        try:
            peek_results = collection.peek(limit=limit)
            
            documents = []
            if peek_results and peek_results.get('ids'):
                for i, doc_id in enumerate(peek_results['ids']):
                    doc_info = {
                        "id": doc_id,
                        "metadata": peek_results['metadatas'][i] if peek_results.get('metadatas') else {},
                        "document_preview": peek_results['documents'][i][:200] if peek_results.get('documents') else ""
                    }
                    documents.append(doc_info)
            
            return {
                "tenant_id": tenant.id,
                "collection_name": vector_store.get_collection_name(tenant.id, collection_name),
                "total_documents": collection.count(),
                "documents": documents,
                "sample_size": len(documents)
            }
        
        except Exception as e:
            logger.error(f"Error peeking collection: {str(e)}")
            return {
                "tenant_id": tenant.id,
                "collection_name": vector_store.get_collection_name(tenant.id, collection_name),
                "total_documents": collection.count(),
                "documents": [],
                "error": str(e)
            }
    
    except Exception as e:
        logger.error(f"Error getting document info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting document info: {str(e)}"
        )

@router.delete("/all", response_model=DeleteResponse)
async def delete_all_documents(
    confirmation: str = Query(..., description="Set to 'true' to confirm deletion"),
    tenant: Tenant = Depends(get_current_tenant),
    collection_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Delete ALL documents for the current tenant"""
    logger.info(f"Received request to delete all documents for tenant {tenant.id} with confirmation={confirmation}")
    
    if confirmation.lower() != "true":
        raise HTTPException(
            status_code=400,
            detail="Confirmation required. Set confirmation=true to delete all documents"
        )
    
    try:
        vector_store = get_vector_store()
        
        # Get collection
        collection = vector_store.get_or_create_collection(tenant.id, collection_name)
        initial_count = collection.count()
        
        if initial_count == 0:
            return DeleteResponse(
                message="No documents to delete",
                deleted_count=0,
                tenant_id=tenant.id
            )
        
        # Delete all documents in the collection
        # Option 1: Delete the entire collection and recreate it
        full_collection_name = vector_store.get_collection_name(tenant.id, collection_name)
        
        try:
            # Delete the collection
            vector_store.client.delete_collection(full_collection_name)
            logger.info(f"Deleted collection {full_collection_name} for tenant {tenant.id}")
            
            # Recreate empty collection
            vector_store.get_or_create_collection(tenant.id, collection_name)
            
            return DeleteResponse(
                message="All documents deleted successfully",
                deleted_count=initial_count,
                tenant_id=tenant.id
            )
        
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting documents: {str(e)}"
            )
    
    except Exception as e:
        logger.error(f"Error in delete_all_documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting documents: {str(e)}"
        )

@router.delete("/{document_id}", response_model=DeleteResponse)
async def delete_document(
    document_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    collection_name: Optional[str] = None
):
    """Delete a specific document by ID"""
    try:
        vector_store = get_vector_store()
        collection = vector_store.get_or_create_collection(tenant.id, collection_name)
        
        # Check if document exists by trying to get it
        try:
            # Peek to see if document exists (we can also use get)
            collection.get(ids=[document_id])
        except Exception:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete the document
        collection.delete(ids=[document_id])
        
        logger.info(f"Deleted document {document_id} for tenant {tenant.id}")
        
        return DeleteResponse(
            message="Document deleted successfully",
            deleted_count=1,
            tenant_id=tenant.id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting document: {str(e)}"
        )

@router.delete("", response_model=DeleteResponse)
async def delete_multiple_documents(
    document_ids: List[str],
    tenant: Tenant = Depends(get_current_tenant),
    collection_name: Optional[str] = None
):
    """Delete multiple documents by their IDs"""
    vector_store = get_vector_store()
    collection = vector_store.get_or_create_collection(tenant.id, collection_name)
    
    deleted_count = 0
    failed_ids = []
    
    for doc_id in document_ids:
        try:
            # Check if document exists
            try:
                collection.get(ids=[doc_id])
                collection.delete(ids=[doc_id])
                deleted_count += 1
                logger.debug(f"Deleted document {doc_id}")
            except Exception:
                failed_ids.append(doc_id)
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {str(e)}")
            failed_ids.append(doc_id)
    
    return DeleteResponse(
        message=f"Deleted {deleted_count} out of {len(document_ids)} documents",
        deleted_count=deleted_count,
        failed_ids=failed_ids,
        tenant_id=tenant.id
    )

@router.delete("/collection/{collection_name}")
async def delete_collection(
    collection_name: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Delete an entire collection for the tenant"""
    try:
        vector_store = get_vector_store()
        full_collection_name = vector_store.get_collection_name(tenant.id, collection_name)
        
        # Check if collection exists
        collections = vector_store.client.list_collections()
        collection_exists = any(col.name == full_collection_name for col in collections)
        
        if not collection_exists:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        # Delete the collection
        vector_store.client.delete_collection(full_collection_name)
        
        logger.info(f"Deleted collection {full_collection_name} for tenant {tenant.id}")
        
        return {
            "message": "Collection deleted successfully",
            "collection_name": full_collection_name,
            "tenant_id": tenant.id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting collection: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting collection: {str(e)}"
        )

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and process a document for RAG"""
    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.txt', '.md']
        file_extension = '.' + file.filename.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Process the document
        ingestion = IngestionOrchestrator(tenant.id)
        result = await ingestion.process_document(
            file=file,
            user_id=user.id,
            metadata={
                "uploaded_by": user.email,
                "tenant_name": tenant.name
            }
        )
        
        return DocumentUploadResponse(
            document_id=result["document_id"],
            filename=result["filename"],
            chunks_processed=result["chunks_processed"],
            status=result["status"],
            tenant_id=tenant.id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading document: {str(e)}"
        )

@router.get("/search")
async def search_documents(
    query: str,
    tenant: Tenant = Depends(get_current_tenant),
    n_results: int = Query(5, ge=1, le=20),
    collection_name: Optional[str] = None
):
    """Search documents for the current tenant"""
    try:
        vector_store = get_vector_store()
        
        # Search with tenant isolation
        results = vector_store.search(
            tenant_id=tenant.id,
            query=query,
            n_results=n_results,
            collection_name=collection_name
        )
        
        # Format results
        formatted_results = []
        if results and results.get('documents') and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    "text": doc,
                    "metadata": results['metadatas'][0][i] if results.get('metadatas') else {},
                    "distance": results['distances'][0][i] if results.get('distances') else None
                })
        
        return {
            "query": query,
            "results": formatted_results,
            "count": len(formatted_results),
            "tenant_id": tenant.id
        }
    
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error searching documents: {str(e)}"
        )