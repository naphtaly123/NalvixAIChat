from langchain_core.tools import BaseTool
from typing import Optional, Type, List, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from models.tenant import Tenant
from services.rag.vector_store import TenantAwareVectorStore
from core.config import settings

logger = logging.getLogger(__name__)

class RAGInput(BaseModel):
    """Input schema for RAG tool"""
    query: str = Field(
        ...,
        description="The question or search query to retrieve relevant information"
    )
    top_k: Optional[int] = Field(
        default=5,
        description="Number of relevant documents to retrieve (default: 5)"
    )
    score_threshold: Optional[float] = Field(
        default=0.5,
        description="Minimum similarity score threshold (0-1, default: 0.5)"
    )
    filter_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata filters (e.g., {'source': 'manual', 'category': 'faq'})"
    )

class RAGTool(BaseTool):
    """
    RAG (Retrieval-Augmented Generation) Tool for retrieving relevant documents
    from the vector store based on user queries.
    """
    
    name: str = "rag_retrieval"
    description: str = """
    Search the official BOCRA knowledge base to provide accurate, authoritative information.
    Use this tool when you need to:
    - Answer questions about BOCRA policies, regulations, and services
    - Provide information about telecommunications, broadcasting, and postal services
    - Explain licensing requirements and procedures
    - Share official guidelines and standards
    - Answer frequently asked questions about BOCRA's mandate

    IMPORTANT: 
    - You are BOCRA's official AI assistant. Own the information you provide.
    - Present information as BOCRA's official position or guidance
    - If information is not found, say: "I don't have that specific information in my knowledge base. Would you like me to connect you with a human agent who can help with your question?"

    Input should be a clear question or search query about BOCRA's services, regulations, or policies.
    The tool returns relevant information from BOCRA's official knowledge base with sources.
    """
    args_schema: Type[BaseModel] = RAGInput
    
    # Dependencies
    tenant: Optional[Tenant] = None
    tenant_id: Optional[int] = None
    db: Optional[Session] = None
    vector_store: Optional[TenantAwareVectorStore] = None
    
    def __init__(self, tenant: Optional[Tenant] = None, tenant_id: Optional[int] = None, db_session: Optional[Session] = None, vector_store: Optional[TenantAwareVectorStore] = None, **kwargs):
        """Initialize RAG tool with tenant context"""
        super().__init__(**kwargs)
        self.tenant = tenant
        self.tenant_id = tenant_id if tenant_id else (tenant.id if tenant else None)
        self.db = db_session
        self.vector_store = TenantAwareVectorStore()
    
    def _run(self, **kwargs) -> str:
        """
        Execute RAG retrieval with kwargs parameters
        """
        try:
            # Extract parameters
            query = kwargs.get("query")
            top_k = kwargs.get("top_k", 5)
            score_threshold = kwargs.get("score_threshold", 0.5)
            filter_metadata = kwargs.get("filter_metadata", None)
            
            # Validate query
            if not query or not query.strip():
                return "Error: Query cannot be empty"
            
            # Get tenant ID
            if not self.tenant_id:
                return "Error: No tenant context provided. Please specify tenant."
            
            # Perform search using your vector store
            logger.info(f"Searching for: {query} (top_k={top_k}, threshold={score_threshold})")
            
            # Search returns a dictionary
            search_results = self.vector_store.search(
                tenant_id=self.tenant_id,
                query=query,
                n_results=top_k,
                filter_criteria=filter_metadata
            )
            
            # Check if we got results
            documents = search_results.get('documents', [[]])[0] if search_results.get('documents') else []
            metadatas = search_results.get('metadatas', [[]])[0] if search_results.get('metadatas') else []
            distances = search_results.get('distances', [[]])[0] if search_results.get('distances') else []
            
            if not documents:
                return "No relevant information found. Please try rephrasing your question or check if content exists in the knowledge base."
            
            # Convert distances to similarity scores (lower distance = higher similarity)
            # ChromaDB uses L2 distance by default, so we convert to similarity score between 0-1
            scores = []
            for distance in distances:
                if distance is not None:
                    # Convert distance to similarity score (1 - normalized distance)
                    # Max possible distance depends on embedding dimension, but we'll use a reasonable cap
                    similarity = max(0, min(1, 1 - (distance / 10)))  # Adjust divisor based on your distances
                    scores.append(similarity)
                else:
                    scores.append(0.5)  # Default if no distance
            
            # Apply score threshold
            filtered_results = []
            for doc, metadata, score, distance in zip(documents, metadatas, scores, distances):
                if score >= score_threshold:
                    # Create a document-like object with page_content and metadata
                    class Document:
                        def __init__(self, page_content, metadata):
                            self.page_content = page_content
                            self.metadata = metadata
                    
                    doc_obj = Document(doc, metadata)
                    filtered_results.append((doc_obj, score))
            
            if not filtered_results:
                return f"No results above threshold {score_threshold}. Try lowering the threshold or rephrasing your query."
            
            # Format results
            formatted_results = self._format_results(filtered_results, query)
            
            # Log retrieval
            logger.info(f"Retrieved {len(filtered_results)} documents with scores: {[score for _, score in filtered_results]}")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in RAG retrieval: {str(e)}", exc_info=True)
            return f"Error retrieving information: {str(e)}"
    
    async def _arun(self, **kwargs) -> str:
        """Async version of RAG retrieval"""
        return self._run(**kwargs)
    def _format_results(self, results: List[tuple], query: str) -> str:
        """
        Format retrieval results into authoritative, official responses
        """
        if not results:
            return ""
        # Instead of just returning search results, format them as official information
        formatted = f"Based on official {self._get_company_name()} documentation:\n\n"
    
        # Group by document type for better organization
        by_type = {}
        for idx, (doc, score) in enumerate(results):
            doc_type = doc.metadata.get('type', 'document')
        if doc_type not in by_type:
            by_type[doc_type] = []
        by_type[doc_type].append((doc, score, idx))
    
        # Format by type
        for doc_type, docs in by_type.items():

            if doc_type == 'policy':

                formatted += "**Official Policy Guidance:**\n\n"
            elif doc_type == 'regulation':
                formatted += "**Regulatory Requirements:**\n\n"
            elif doc_type == 'faq':
                formatted += "**Official FAQ:**\n\n"
            else:
                formatted += f"**{doc_type.upper()} Information:**\n\n"
        
            for doc, score, idx in docs:
                content = doc.page_content[:500] if hasattr(doc, 'page_content') else str(doc)[:500]
                formatted += f"{content}"
                if len(content) >= 500:
                    formatted += "..."
                formatted += "\n\n"
    
        # Add confidence disclaimer
        avg_score = sum(score for _, score in results) / len(results)
        if avg_score > 0.7:
            formatted += "\n*This information reflects current {COMPANY_NAME} policies and procedures.*"
        else:
            formatted += "\n*Based on available information. For complex cases, a human agent can provide detailed guidance.*"
        
        return formatted
    def _get_company_name(self) -> str:
        
        """Get company name from settings or config"""
        return getattr(settings, 'COMPANY_NAME', 'BOCRA')


class AdvancedRAGTool(RAGTool):
    """
    Advanced RAG Tool with additional features:
    - Multi-query retrieval
    - Context expansion
    - Source citation
    - Relevance scoring
    """
    
    def _run(self, **kwargs) -> str:
        """Enhanced RAG retrieval with advanced features"""
        try:
            query = kwargs.get("query")
            top_k = kwargs.get("top_k", 5)
            score_threshold = kwargs.get("score_threshold", 0.5)
            expand_context = kwargs.get("expand_context", True)
            
            if not query:
                return "Error: Query cannot be empty"
            
            # Get base results
            base_results = super()._run(**kwargs)
            
            if "No relevant information found" in base_results or "No results above threshold" in base_results:
                return base_results
            
            # Add context expansion if requested
            if expand_context and "Search Results" in base_results:
                expanded_context = self._expand_context(query)
                if expanded_context:
                    base_results += "\n\n" + expanded_context
            
            return base_results
            
        except Exception as e:
            logger.error(f"Error in advanced RAG: {str(e)}")
            return f"Error in advanced retrieval: {str(e)}"
    
    def _expand_context(self, query: str) -> str:
        """Expand context with related suggestions"""
        suggestions = []
        
        # Simple query analysis
        if len(query.split()) < 3:
            suggestions.append("• Try using more specific keywords")
        
        if "?" in query:
            suggestions.append("• Consider rephrasing as a statement for better matches")
        
        suggestions.append("• Check if the information exists in your knowledge base")
        suggestions.append("• Try using technical terms or synonyms")
        
        return "💡 **Suggestions to improve results:**\n" + "\n".join(suggestions)