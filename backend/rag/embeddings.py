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
from typing import Optional

from google import genai

logger = logging.getLogger(__name__)

# Lazy singleton for Gemini client
_gemini_client: Optional[genai.Client] = None


def get_gemini_client() -> genai.Client:
    """
    Get or create Gemini API client singleton.
    
    Reads GEMINI_API_KEY from environment variable.
    
    Returns:
        Configured Gemini client
    
    Raises:
        ValueError: If GEMINI_API_KEY is not set
    """
    global _gemini_client
    
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required but not set. "
                "Set it in your .env file or environment."
            )
        _gemini_client = genai.Client(api_key=api_key)
        logger.info("Gemini API client created successfully")
    
    return _gemini_client


def embed_text_sync(text: str) -> list[float]:
    """
    Generate embedding using Gemini gemini-embedding-001 (3072 dimensions).
    
    NOTE: The new google-genai SDK uses synchronous calls for embeddings.
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
        client = get_gemini_client()
        
        # Call Gemini embeddings API using new SDK
        # Note: 'contents' parameter (not 'content'), model name without 'models/' prefix
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text
        )
        
        # Extract embedding from response
        # New SDK returns EmbedContentResponse with embeddings list
        embedding = result.embeddings[0].values
        
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
