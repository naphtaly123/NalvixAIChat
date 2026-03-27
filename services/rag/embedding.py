# from typing import List
# import requests
# from sentence_transformers import SentenceTransformer
# from fastapi import HTTPException
# from core.config import get_settings

# settings = get_settings()

# # Initialize once, reuse
# _local_embedding_model = None

# def get_local_embedding_model():
#     global _local_embedding_model
#     if _local_embedding_model is None:
#         _local_embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
#     return _local_embedding_model

# def get_embeddings(texts: List[str]) -> List[List[float]]:
#     """Unified embedding function"""
#     if settings.USE_DEEPSEEK_EMBEDDINGS:
#         return _get_deepseek_embeddings(texts)
#     return _get_local_embeddings(texts)

# def _get_local_embeddings(texts: List[str]) -> List[List[float]]:
#     model = get_local_embedding_model()
#     return model.encode(texts).tolist()

# def _get_deepseek_embeddings(texts: List[str]) -> List[List[float]]:
#     response = requests.post(
#         "https://api.deepseek.com/embeddings",
#         headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
#         json={"model": "deepseek-embedding", "input": texts}
#     )
    
#     if response.status_code != 200:
#         raise HTTPException(500, "Embedding API error")
    
#     return [item["embedding"] for item in response.json()["data"]]

# app/services/rag/embedding.py
from typing import List
import requests
from sentence_transformers import SentenceTransformer
from fastapi import HTTPException
from core.config import settings
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Initialize once, reuse
_local_embedding_model = None
_executor = ThreadPoolExecutor(max_workers=4)

def get_local_embedding_model():
    """Get or initialize the local embedding model"""
    global _local_embedding_model
    if _local_embedding_model is None:
        logger.info("Loading local embedding model: all-MiniLM-L6-v2")
        _local_embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _local_embedding_model

async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Unified embedding function with async support"""
    if settings.USE_DEEPSEEK_EMBEDDINGS:
        return await _get_deepseek_embeddings(texts)
    return await _get_local_embeddings(texts)

async def get_embedding_single(text: str) -> List[float]:
    """Get embedding for a single text"""
    embeddings = await get_embeddings([text])
    return embeddings[0]

async def _get_local_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using local SentenceTransformer model"""
    try:
        # Run in thread pool since sentence-transformers can be blocking
        loop = asyncio.get_event_loop()
        model = get_local_embedding_model()
        
        def encode():
            return model.encode(texts).tolist()
        
        embeddings = await loop.run_in_executor(_executor, encode)
        return embeddings
    except Exception as e:
        logger.error(f"Local embedding error: {str(e)}")
        raise HTTPException(500, f"Local embedding error: {str(e)}")

async def _get_deepseek_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using DeepSeek API"""
    try:
        # Run in thread pool for network requests
        loop = asyncio.get_event_loop()
        
        def call_deepseek():
            response = requests.post(
                "https://api.deepseek.com/embeddings",
                headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
                json={"model": "deepseek-embedding", "input": texts},
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"DeepSeek API error: {response.text}")
                raise HTTPException(500, f"DeepSeek embedding API error: {response.status_code}")
            
            return [item["embedding"] for item in response.json()["data"]]
        
        embeddings = await loop.run_in_executor(_executor, call_deepseek)
        return embeddings
    except Exception as e:
        logger.error(f"DeepSeek embedding error: {str(e)}")
        raise HTTPException(500, f"DeepSeek embedding error: {str(e)}")

# Synchronous wrapper for backward compatibility
def get_embeddings_sync(texts: List[str]) -> List[List[float]]:
    """Synchronous version for non-async contexts"""
    if settings.USE_DEEPSEEK_EMBEDDINGS:
        return _get_deepseek_embeddings_sync(texts)
    return _get_local_embeddings_sync(texts)

def _get_local_embeddings_sync(texts: List[str]) -> List[List[float]]:
    """Synchronous local embeddings"""
    model = get_local_embedding_model()
    return model.encode(texts).tolist()

def _get_deepseek_embeddings_sync(texts: List[str]) -> List[List[float]]:
    """Synchronous DeepSeek embeddings"""
    response = requests.post(
        "https://api.deepseek.com/embeddings",
        headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
        json={"model": "deepseek-embedding", "input": texts},
        timeout=30
    )
    
    if response.status_code != 200:
        raise HTTPException(500, f"DeepSeek embedding API error: {response.status_code}")
    
    return [item["embedding"] for item in response.json()["data"]]