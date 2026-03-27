# from typing import List
# from services.rag.embedding import get_embeddings
# from services.rag.vector_store import get_vector_store
# from services.rag.llm import get_llm_service
# from ingestion.chunking import chunk_text
# from core.config import get_settings

# settings = get_settings()

# class RAGService:
#     def __init__(self):
#         self.vector_store = get_vector_store()
#         self.llm = get_llm_service()
    
#     def retrieve_relevant_chunks(self, query: str) -> List[str]:
#         query_embedding = get_embeddings([query])[0]
#         return self.vector_store.query(query_embedding)
    
#     def generate_response(self, query: str, chunks: List[str]) -> str:
#         context = "\n\n".join(chunks)
#         prompt = f"""
# You are a professional and confident customer support and sales representative for our company.

# Your job is to answer the user's question using the information provided in the context. 
# Speak as if you work for the company. Own the information. 
# Be friendly, helpful, confident, and slightly persuasive where appropriate.

# TONE & STYLE RULES:
# - Speak in first person plural (we, our, us).
# - Sound natural and conversational.
# - Be clear and concise.
# - If relevant, subtly highlight benefits or value.
# - Do NOT say phrases like:
#   - "Based on the context provided"
#   - "According to the information above"
#   - "The document states"
# - Do NOT mention "context" at all.
# - Do NOT sound like an AI.
# - Do NOT hedge unnecessarily.

# IMPORTANT:
# - If the answer is clearly supported by the context, answer confidently.
# - If the context does NOT contain enough information to answer properly, say:
#   "I’m sorry, I don’t have that information at the moment, but I’d be happy to help you further if you can provide more details."
# - Do NOT make up information that is not in the context.
# - Always be truthful and do not fabricate details.

# Context:
# {context}

# User Question:
# {query}

# Answer:
# """
#         return self.llm.chat(prompt)
    
#     def process_and_store(self, text: str, source: str, doc_id_prefix: str) -> int:
#         chunks = chunk_text(text)
#         if not chunks:
#             return 0
            
#         embeddings = get_embeddings(chunks)
#         return self.vector_store.add_documents(chunks, embeddings, source, doc_id_prefix)

# # Singleton
# _rag_service = None

# def get_rag_service():
#     global _rag_service
#     if _rag_service is None:
#         _rag_service = RAGService()
#     return _rag_service

# app/services/rag/rag.py

# app/services/rag/rag.py
from typing import List, Dict, Optional, Any
from services.rag.embedding import get_embeddings, get_embeddings_sync
from services.rag.vector_store import TenantAwareVectorStore
from services.rag.llm import LLMService
from ingestion.chunking import chunk_text
from core.config import settings
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self, tenant_id: int):
        """Initialize RAG service for a specific tenant"""
        self.tenant_id = tenant_id
        self.vector_store = TenantAwareVectorStore()
        self.llm = LLMService()
    
    async def retrieve_relevant_chunks(
        self, 
        query: str, 
        top_k: int = None,
        filter_criteria: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks for a query with tenant isolation"""
        try:
            # Generate query embedding
            query_embedding = await get_embeddings([query])
            
            # Query vector store with tenant isolation
            results = self.vector_store.search(
                tenant_id=self.tenant_id,
                query=query,
                n_results=top_k or settings.TOP_K_RESULTS,
                filter_criteria=filter_criteria
            )
            
            # Format results
            chunks = []
            if results and results.get('documents') and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    chunks.append({
                        "text": doc,
                        "metadata": results['metadatas'][0][i] if results.get('metadatas') else {},
                        "distance": results['distances'][0][i] if results.get('distances') else None
                    })
            
            return chunks
        
        except Exception as e:
            logger.error(f"Retrieval error for tenant {self.tenant_id}: {str(e)}")
            raise
    
    async def generate_response(
        self, 
        query: str, 
        chunks: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """Generate a response using retrieved chunks"""
        try:
            # Build context from chunks
            context = "\n\n".join([chunk["text"] for chunk in chunks])
            
            # Use the enhanced prompt template
            prompt = self._build_prompt(query, context, conversation_history)
            
            # Generate response using LLM
            response = await self.llm.generate_response([{
                "role": "user",
                "content": prompt
            }])
            
            return response
        
        except Exception as e:
            logger.error(f"Response generation error: {str(e)}")
            return "I'm sorry, I encountered an error while generating a response. Please try again."
    
    def _build_prompt(
        self, 
        query: str, 
        context: str, 
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """Build the prompt with proper formatting"""
        
        # Base system prompt
        system_prompt = """You are a professional and confident customer support and sales representative for our company.

Your job is to answer the user's question using the information provided in the context. 
Speak as if you work for the company. Own the information. 
Be friendly, helpful, confident, and slightly persuasive where appropriate.

TONE & STYLE RULES:
- Speak in first person plural (we, our, us).
- Sound natural and conversational.
- Be clear and concise.
- If relevant, subtly highlight benefits or value.
- Do NOT say phrases like:
  - "Based on the context provided"
  - "According to the information above"
  - "The document states"
- Do NOT mention "context" at all.
- Do NOT sound like an AI.
- Do NOT hedge unnecessarily.

IMPORTANT:
- If the answer is clearly supported by the context, answer confidently.
- If the context does NOT contain enough information to answer properly, say:
  "I'm sorry, I don't have that information at the moment, but I'd be happy to help you further if you can provide more details."
- Do NOT make up information that is not in the context.
- Always be truthful and do not fabricate details."""

        # Build the prompt
        prompt_parts = [system_prompt]
        
        # Add conversation history if available
        if conversation_history:
            prompt_parts.append("\nPrevious conversation:")
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                role = "User" if msg["role"] == "user" else "Assistant"
                prompt_parts.append(f"{role}: {msg['content']}")
        
        # Add context and query
        prompt_parts.extend([
            f"\nContext:\n{context}\n" if context else "",
            f"User Question:\n{query}\n",
            "Answer:"
        ])
        
        return "\n".join(prompt_parts)
    
    async def process_and_store(
        self, 
        text: str, 
        source: str, 
        doc_id_prefix: str,
        user_id: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """Process text and store in vector database with tenant isolation"""
        try:
            # Chunk the text
            chunks = chunk_text(text)
            if not chunks:
                logger.warning(f"No chunks generated for {source}")
                return 0
            
            # Prepare metadata for each chunk
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                doc_id = f"{doc_id_prefix}_{uuid.uuid4()}_{i}"
                chunk_metadata = {
                    "tenant_id": self.tenant_id,
                    "source": source,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "created_at": datetime.utcnow().isoformat(),
                    **({"user_id": user_id} if user_id else {}),
                    **(metadata or {})
                }
                metadatas.append(chunk_metadata)
                ids.append(doc_id)
            
            # Generate embeddings (async)
            embeddings = await get_embeddings(chunks)
            
            # Add to vector store
            self.vector_store.add_documents(
                tenant_id=self.tenant_id,
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Stored {len(chunks)} chunks for tenant {self.tenant_id} from {source}")
            return len(chunks)
        
        except Exception as e:
            logger.error(f"Storage error for tenant {self.tenant_id}: {str(e)}")
            raise
    
    async def process_and_store_sync_compat(
        self, 
        text: str, 
        source: str, 
        doc_id_prefix: str
    ) -> int:
        """Synchronous compatibility wrapper for existing code"""
        # Use sync embedding function
        chunks = chunk_text(text)
        if not chunks:
            return 0
        
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            doc_id = f"{doc_id_prefix}_{uuid.uuid4()}_{i}"
            metadatas.append({
                "tenant_id": self.tenant_id,
                "source": source,
                "chunk_index": i,
                "total_chunks": len(chunks)
            })
            ids.append(doc_id)
        
        # Use sync embeddings
        embeddings = get_embeddings_sync(chunks)
        
        # Add to vector store
        self.vector_store.add_documents(
            tenant_id=self.tenant_id,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        
        return len(chunks)
    
    async def search_and_answer(
        self, 
        query: str,
        conversation_history: Optional[List[Dict]] = None,
        top_k: int = None
    ) -> Dict[str, Any]:
        """Complete RAG pipeline: retrieve and generate answer"""
        try:
            # Retrieve relevant chunks
            chunks = await self.retrieve_relevant_chunks(query, top_k)
            
            # Generate response
            if chunks:
                answer = await self.generate_response(query, chunks, conversation_history)
            else:
                answer = "I'm sorry, I don't have that information at the moment, but I'd be happy to help you further if you can provide more details."
            
            return {
                "answer": answer,
                "chunks_used": len(chunks),
                "sources": list(set([chunk["metadata"].get("source", "unknown") for chunk in chunks])),
                "tenant_id": self.tenant_id
            }
        
        except Exception as e:
            logger.error(f"RAG pipeline error: {str(e)}")
            return {
                "answer": "I encountered an error while processing your request. Please try again.",
                "error": str(e),
                "tenant_id": self.tenant_id
            }

# Factory function to create RAG service for a tenant
def get_rag_service(tenant_id: int) -> RAGService:
    """Create a RAG service instance for a specific tenant"""
    return RAGService(tenant_id)