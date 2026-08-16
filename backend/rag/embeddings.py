"""
Shared embeddings module for ScanTract using Google Gemini.

Uses Gemini's gemini-embedding-001 model (3072 dimensions) with exact
vector search (no IVFFlat index, as it cannot support >2000 dimensions).

Shared by:
- Stage 5A: Legal rules KB (backend/db/legal_kb/)
- Stage 5B: Reference corpus (backend/db/reference_corpus/)
"""

import os
import asyncio
import logging
import warnings
from typing import Optional

# Suppress the FutureWarning about google.generativeai deprecation
warnings.filterwarnings('ignore', message='.*google.generativeai.*deprecated.*')

import google.generativeai as genai

logger = logging.getLogger(__name__)

# Lazy singleton for Gemini configuration
_gemini_configured: bool = False


def configure_gemini() -> None:
    """
    Configure Gemini API client singleton.
    
    Reads GEMINI_API_KEY from environment variable.
    
    Raises:
        ValueError: If GEMINI_API_KEY is not set
    """
    global _gemini_configured
    
    if not _gemini_configured:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required but not set. "
                "Set it in your .env file or environment."
            )
        genai.configure(api_key=api_key)
        _gemini_configured = True
        logger.info("Gemini API configured successfully")


def embed_text_sync(text: str) -> list[float]:
    """
    Generate embedding using Gemini gemini-embedding-001 (3072 dimensions).
    
    NOTE: Gemini's Python SDK does not support async, so this is synchronous.
    The public embed_text() function wraps this in asyncio.to_thread().
    
    Args:
        text: Text to embed
    
    Returns:
        List of 3072 float values
    
    Raises:
        ValueError: If embedding dimension is not 3072
        Exception: If Gemini API call fails
    """
    try:
        configure_gemini()
        
        # Call Gemini embeddings API
        # task_type='retrieval_document' optimizes for similarity search
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type="retrieval_document"
        )
        
        # Extract embedding
        embedding = result['embedding']
        
        # Validate dimension
        if len(embedding) != 3072:
            raise ValueError(
                f"Expected Gemini embedding dimension 3072, got {len(embedding)}. "
                f"This indicates an API change or model mismatch."
            )
        
        return embedding
        
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        raise


async def embed_text(text: str) -> list[float]:
    """
    Generate embedding for a single text using Gemini.
    
    Args:
        text: Text to embed (clause text, legal rule, etc.)
    
    Returns:
        List of 3072 float values representing the embedding
    
    Raises:
        ValueError: If embedding dimension is not 3072
        Exception: If Gemini API call fails
    """
    # Gemini SDK is synchronous, wrap in thread to avoid blocking
    return await asyncio.to_thread(embed_text_sync, text)


async def embed_batch(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """
    Generate embeddings for multiple texts with batching.
    
    Processes texts in batches to avoid overwhelming the API and improve
    throughput via concurrent requests.
    
    Args:
        texts: List of texts to embed
        batch_size: Number of texts to process concurrently per batch
    
    Returns:
        List of embeddings (same order as input texts)
    
    Raises:
        Same exceptions as embed_text()
    """
    all_embeddings = []
    total_texts = len(texts)
    
    # Process in batches
    for i in range(0, total_texts, batch_size):
        batch = texts[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_texts + batch_size - 1) // batch_size
        
        logger.info(
            f"Embedding batch {batch_num}/{total_batches} "
            f"({len(batch)} texts) using Gemini"
        )
        
        # Create tasks for concurrent embedding within batch
        tasks = [embed_text(text) for text in batch]
        
        # Execute batch concurrently
        batch_embeddings = await asyncio.gather(*tasks)
        
        all_embeddings.extend(batch_embeddings)
    
    logger.info(f"Successfully embedded {total_texts} texts using Gemini")
    return all_embeddings
