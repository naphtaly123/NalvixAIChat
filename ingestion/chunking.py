# from typing import List
# import re
# from core.config import get_settings

# settings = get_settings()

# def chunk_text(text: str) -> List[str]:
#     """Split text into chunks using multiple strategies"""
    
#     # First, clean the text
#     text = clean_text(text)
    
#     # Strategy 1: Try paragraph-based splitting first
#     chunks = chunk_by_paragraphs(text)
    
#     # Debug: Print chunking results
#     print(f"\n=== Chunking Debug ===")
#     print(f"Paragraph-based chunks: {len(chunks)}")
    
#     # If paragraph-based chunking gave poor results, try other strategies
#     if len(chunks) == 0:
#         print("No paragraph chunks found, trying sentence-based chunking...")
#         chunks = chunk_by_sentences(text)
    
#     if len(chunks) == 0:
#         print("No sentence chunks found, trying fixed-size chunking...")
#         chunks = chunk_by_fixed_size(text)
    
#     print(f"Final chunks count: {len(chunks)}")
#     if chunks:
#         print(f"First chunk sample: {chunks[0][:200]}...")
#     print("=" * 50)
    
#     return chunks

# def clean_text(text: str) -> str:
#     """Clean and normalize text"""
#     # Replace multiple newlines with double newline
#     import re
#     text = re.sub(r'\n\s*\n', '\n\n', text)
#     # Replace multiple spaces with single space
#     text = re.sub(r' +', ' ', text)
#     # Replace multiple tabs with single space
#     text = re.sub(r'\t+', ' ', text)
#     return text.strip()

# def chunk_by_paragraphs(text: str) -> List[str]:
#     """Split text by paragraphs (double newlines)"""
#     if not text:
#         return []
    
#     # Split by double newlines
#     paragraphs = text.split('\n\n')
    
#     # Clean and filter paragraphs
#     chunks = []
#     for p in paragraphs:
#         p = p.strip()
#         # Remove single newlines within paragraphs
#         p = re.sub(r'\n', ' ', p)
#         if len(p) > settings.MIN_CHUNK_SIZE:
#             chunks.append(p)
    
#     return chunks

# def chunk_by_sentences(text: str, max_chunk_size: int = 1000) -> List[str]:
#     """Split text into chunks by sentences"""
#     if not text:
#         return []
    
#     # Improved sentence splitting
#     # Handle common abbreviations to avoid false splits
#     text = re.sub(r'(Mr|Mrs|Ms|Dr|Prof|Capt|Gen|Sen|Rep|St|Ave|Blvd)\.', r'\1<DOT>', text)
    
#     # Split by sentence endings
#     sentences = re.split(r'[.!?]+', text)
    
#     # Restore periods in abbreviations
#     sentences = [s.replace('<DOT>', '.') for s in sentences]
    
#     chunks = []
#     current_chunk = ""
    
#     for sentence in sentences:
#         sentence = sentence.strip()
#         if not sentence:
#             continue
        
#         # If adding this sentence would exceed max chunk size, save current chunk and start new one
#         if len(current_chunk) + len(sentence) + 1 > max_chunk_size and current_chunk:
#             if len(current_chunk) > settings.MIN_CHUNK_SIZE:
#                 chunks.append(current_chunk.strip())
#             current_chunk = sentence
#         else:
#             if current_chunk:
#                 current_chunk += " " + sentence
#             else:
#                 current_chunk = sentence
    
#     # Add the last chunk
#     if current_chunk and len(current_chunk) > settings.MIN_CHUNK_SIZE:
#         chunks.append(current_chunk.strip())
    
#     return chunks

# def chunk_by_fixed_size(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
#     """Split text into fixed-size chunks with overlap - FIXED version"""
#     if not text:
#         return []
    
#     chunks = []
#     start = 0
#     text_length = len(text)
    
#     # FIX: Added maximum iterations protection
#     max_iterations = (text_length // (chunk_size - overlap)) + 10
#     iteration = 0
    
#     while start < text_length and iteration < max_iterations:
#         iteration += 1
        
#         # Calculate end position
#         end = min(start + chunk_size, text_length)
        
#         # If we're not at the end, try to find a good breaking point
#         if end < text_length:
#             # Look for sentence end or space within the last 50 characters
#             search_start = max(start, end - 50)
#             search_text = text[search_start:end + 50]
            
#             # Try to find a period followed by space
#             period_pos = search_text.find('. ')
#             if period_pos != -1 and period_pos < 50:
#                 end = search_start + period_pos + 1
#             else:
#                 # Look for space
#                 space_pos = search_text.rfind(' ', 0, 50)
#                 if space_pos != -1:
#                     end = search_start + space_pos
        
#         # Extract chunk
#         chunk = text[start:end].strip()
#         if len(chunk) > settings.MIN_CHUNK_SIZE:
#             chunks.append(chunk)
        
#         # Move start position for next chunk (with overlap)
#         start = end - overlap
        
#         # FIX: Prevent infinite loop if start doesn't progress
#         if start >= end:
#             start = end
        
#         # FIX: Prevent getting stuck at the end
#         if start >= text_length - 1:
#             break
    
#     return chunks

# def chunk_by_words(text: str, words_per_chunk: int = 100, overlap_words: int = 20) -> List[str]:
#     """Alternative: Split by words instead of characters"""
#     words = text.split()
#     chunks = []
    
#     i = 0
#     while i < len(words):
#         # Get chunk of words
#         chunk_words = words[i:i + words_per_chunk]
#         chunk = ' '.join(chunk_words)
        
#         if len(chunk) > settings.MIN_CHUNK_SIZE:
#             chunks.append(chunk)
        
#         # Move index with overlap
#         i += words_per_chunk - overlap_words
        
#         # Prevent infinite loop
#         if i >= len(words):
#             break
    
#     return chunks

# app/services/ingestion/chunking.py
from typing import List
import re
from core.config import settings
import logging

logger = logging.getLogger(__name__)

def chunk_text(text: str) -> List[str]:
    """Split text into chunks using multiple strategies"""
    
    # First, clean the text
    text = clean_text(text)
    
    # Strategy 1: Try paragraph-based splitting first
    chunks = chunk_by_paragraphs(text)
    
    # Debug: Log chunking results
    logger.debug(f"Paragraph-based chunks: {len(chunks)}")
    
    # If paragraph-based chunking gave poor results, try other strategies
    if len(chunks) == 0:
        logger.debug("No paragraph chunks found, trying sentence-based chunking...")
        chunks = chunk_by_sentences(text)
    
    if len(chunks) == 0:
        logger.debug("No sentence chunks found, trying fixed-size chunking...")
        chunks = chunk_by_fixed_size(text)
    
    # If still no chunks, try word-based chunking as last resort
    if len(chunks) == 0:
        logger.debug("No chunks from other methods, trying word-based chunking...")
        chunks = chunk_by_words(text)
    
    logger.debug(f"Final chunks count: {len(chunks)}")
    if chunks:
        logger.debug(f"First chunk sample: {chunks[0][:200]}...")
    
    return chunks

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    # Replace multiple newlines with double newline
    text = re.sub(r'\n\s*\n', '\n\n', text)
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    # Replace multiple tabs with single space
    text = re.sub(r'\t+', ' ', text)
    # Remove excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def chunk_by_paragraphs(text: str) -> List[str]:
    """Split text by paragraphs (double newlines)"""
    if not text:
        return []
    
    # Split by double newlines
    paragraphs = text.split('\n\n')
    
    # Clean and filter paragraphs
    chunks = []
    for p in paragraphs:
        p = p.strip()
        # Remove single newlines within paragraphs
        p = re.sub(r'\n', ' ', p)
        # Remove extra whitespace
        p = re.sub(r'\s+', ' ', p)
        if len(p) > settings.MIN_CHUNK_SIZE:
            chunks.append(p)
    
    return chunks

def chunk_by_sentences(text: str, max_chunk_size: int = None) -> List[str]:
    """Split text into chunks by sentences"""
    if not text:
        return []
    
    if max_chunk_size is None:
        max_chunk_size = settings.CHUNK_SIZE
    
    # Improved sentence splitting
    # Handle common abbreviations to avoid false splits
    abbreviations = ['Mr', 'Mrs', 'Ms', 'Dr', 'Prof', 'Capt', 'Gen', 'Sen', 'Rep', 'St', 'Ave', 'Blvd', 'Inc', 'Ltd', 'Co']
    for abbr in abbreviations:
        text = re.sub(rf'{abbr}\.', f'{abbr}<DOT>', text)
    
    # Split by sentence endings
    sentences = re.split(r'[.!?]+', text)
    
    # Restore periods in abbreviations
    sentences = [s.replace('<DOT>', '.') for s in sentences]
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # If adding this sentence would exceed max chunk size, save current chunk and start new one
        if len(current_chunk) + len(sentence) + 1 > max_chunk_size and current_chunk:
            if len(current_chunk) > settings.MIN_CHUNK_SIZE:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
    
    # Add the last chunk
    if current_chunk and len(current_chunk) > settings.MIN_CHUNK_SIZE:
        chunks.append(current_chunk.strip())
    
    return chunks

def chunk_by_fixed_size(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """Split text into fixed-size chunks with overlap"""
    if not text:
        return []
    
    if chunk_size is None:
        chunk_size = settings.CHUNK_SIZE
    if overlap is None:
        overlap = settings.CHUNK_OVERLAP
    
    chunks = []
    start = 0
    text_length = len(text)
    
    # Protection against infinite loops
    max_iterations = (text_length // (chunk_size - overlap)) + 10
    iteration = 0
    
    while start < text_length and iteration < max_iterations:
        iteration += 1
        
        # Calculate end position
        end = min(start + chunk_size, text_length)
        
        # If we're not at the end, try to find a good breaking point
        if end < text_length:
            # Look for sentence end or space within the last 50 characters
            search_start = max(start, end - 50)
            search_text = text[search_start:end + 50]
            
            # Try to find a period followed by space
            period_pos = search_text.find('. ')
            if period_pos != -1 and period_pos < 50:
                end = search_start + period_pos + 1
            else:
                # Look for space
                space_pos = search_text.rfind(' ', 0, 50)
                if space_pos != -1:
                    end = search_start + space_pos
        
        # Extract chunk
        chunk = text[start:end].strip()
        if len(chunk) > settings.MIN_CHUNK_SIZE:
            chunks.append(chunk)
        
        # Move start position for next chunk (with overlap)
        start = end - overlap
        
        # Prevent infinite loop if start doesn't progress
        if start >= end:
            start = end
        
        # Prevent getting stuck at the end
        if start >= text_length - 1:
            break
    
    return chunks

def chunk_by_words(text: str, words_per_chunk: int = None, overlap_words: int = None) -> List[str]:
    """Alternative: Split by words instead of characters"""
    if words_per_chunk is None:
        # Estimate words per chunk based on character count (assuming avg word length 5 chars)
        words_per_chunk = settings.CHUNK_SIZE // 5
    if overlap_words is None:
        overlap_words = settings.CHUNK_OVERLAP // 5
    
    words = text.split()
    chunks = []
    
    i = 0
    while i < len(words):
        # Get chunk of words
        chunk_words = words[i:i + words_per_chunk]
        chunk = ' '.join(chunk_words)
        
        if len(chunk) > settings.MIN_CHUNK_SIZE:
            chunks.append(chunk)
        
        # Move index with overlap
        i += words_per_chunk - overlap_words
        
        # Prevent infinite loop
        if i >= len(words):
            break
    
    return chunks