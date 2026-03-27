import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
import os
from core.config import settings
import logging

logger = logging.getLogger(__name__)

class TenantAwareVectorStore:
    def __init__(self):
        """Initialize ChromaDB client"""
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
    
    def get_collection_name(self, tenant_id: int, collection_name: str = None) -> str:
        """Generate tenant-isolated collection name"""
        collection_name = collection_name or settings.COLLECTION_NAME
        return f"tenant_{tenant_id}_{collection_name}"
    
    def get_or_create_collection(self, tenant_id: int, collection_name: str = None):
        """Get or create a tenant-specific collection"""
        full_name = self.get_collection_name(tenant_id, collection_name)
        
        try:
            collection = self.client.get_collection(full_name)
            logger.debug(f"Retrieved existing collection: {full_name}")
        except:
            collection = self.client.create_collection(full_name)
            logger.info(f"Created new collection: {full_name}")
        
        return collection
    
    def add_documents(
        self, 
        tenant_id: int, 
        documents: List[str], 
        metadatas: List[Dict], 
        ids: List[str],
        collection_name: str = None
    ):
        """Add documents with tenant isolation"""
        try:
            collection = self.get_or_create_collection(tenant_id, collection_name)
            
            # Ensure tenant_id is in metadata for additional filtering
            for metadata in metadatas:
                metadata["tenant_id"] = tenant_id
            
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to tenant {tenant_id}")
        
        except Exception as e:
            logger.error(f"Error adding documents for tenant {tenant_id}: {str(e)}")
            raise

    def search(
        self, 
        tenant_id: int, 
        query: str, 
        n_results: int = 10,
        collection_name: str = None,
        filter_criteria: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Search with tenant isolation"""
        try:
            collection = self.get_or_create_collection(tenant_id, collection_name)
            
            # Always filter by tenant_id
            where_filter = {"tenant_id": tenant_id}
            if filter_criteria:
                where_filter.update(filter_criteria)
            
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            return results
        
        except Exception as e:
            logger.error(f"Search error for tenant {tenant_id}: {str(e)}")
            return {"documents": [], "metadatas": [], "distances": []}
    
    def delete_documents(
        self, 
        tenant_id: int, 
        ids: List[str],
        collection_name: str = None
    ):
        """Delete specific documents"""
        try:
            collection = self.get_or_create_collection(tenant_id, collection_name)
            collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents from tenant {tenant_id}")
        
        except Exception as e:
            logger.error(f"Error deleting documents: {str(e)}")
            raise
    
    def delete_tenant_collections(self, tenant_id: int):
        """Delete all collections for a tenant"""
        try:
            collections = self.client.list_collections()
            tenant_prefix = f"tenant_{tenant_id}_"
            
            deleted_count = 0
            for collection in collections:
                if collection.name.startswith(tenant_prefix):
                    self.client.delete_collection(collection.name)
                    deleted_count += 1
            
            logger.info(f"Deleted {deleted_count} collections for tenant {tenant_id}")
        
        except Exception as e:
            logger.error(f"Error deleting tenant collections: {str(e)}")
            raise
    
    def get_collection_stats(self, tenant_id: int, collection_name: str = None) -> Dict:
        """Get statistics about a tenant's collection"""
        try:
            collection = self.get_or_create_collection(tenant_id, collection_name)
            count = collection.count()
            
            return {
                "tenant_id": tenant_id,
                "collection_name": self.get_collection_name(tenant_id, collection_name),
                "document_count": count,
                "exists": True
            }
        
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {
                "tenant_id": tenant_id,
                "error": str(e),
                "exists": False
            } 