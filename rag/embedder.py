"""
Gemini embedding wrapper for generating text embeddings.

Uses Google's Gemini embedding model to convert text into vector representations
for storage in pgvector and similarity search.
"""
from google import genai
from google.genai import types
from django.conf import settings

import time

# Use the active recommended embedding model
EMBEDDING_MODEL = getattr(settings, 'GEMINI_EMBEDDING_MODEL', 'gemini-embedding-001')

# Load API keys list from Django settings
API_KEYS = getattr(settings, 'GEMINI_API_KEYS', [])
if not API_KEYS:
    single_key = getattr(settings, 'GEMINI_API_KEY', '')
    API_KEYS = [single_key] if single_key else []

# Current active key index
_key_index = 0


def get_client():
    """Instantiate a new Client using the current active key."""
    global _key_index
    if not API_KEYS:
        raise ValueError("No GEMINI_API_KEY or GEMINI_API_KEYS configured in settings.")
    return genai.Client(api_key=API_KEYS[_key_index])


def rotate_key(sleep_on_cycle: bool = False):
    """Rotate to the next API key in the list."""
    global _key_index
    if len(API_KEYS) > 1:
        _key_index = (_key_index + 1) % len(API_KEYS)
        print(f"🔄 Rotating Gemini API key to index {_key_index} of {len(API_KEYS)}...")
        if _key_index == 0 and sleep_on_cycle:
            print("⏳ Cycle completed for all API keys. Waiting 20 seconds to reset quota...")
            time.sleep(20)
    else:
        print("⚠️ Only 1 API key configured. Cannot rotate.")


def _embed_with_rotation(contents, task_type: str, output_dimensionality: int = 768):
    """
    Generate embeddings with automatic API key rotation.
    Rotates keys after every successful batch call.
    If all keys have been used in a cycle, waits 60 seconds.
    If a key fails, it immediately rotates to the next and retries.
    """
    attempts = 0
    max_attempts = len(API_KEYS) * 2  # Try each key twice
    
    # Only wait 60s during indexing (bulk document embedding)
    sleep_on_cycle = (task_type == "RETRIEVAL_DOCUMENT")
    
    while True:
        try:
            client = get_client()
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=contents,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=output_dimensionality,
                )
            )
            # Success: rotate key for the next batch
            rotate_key(sleep_on_cycle=sleep_on_cycle)
            return result
        except Exception as e:
            attempts += 1
            print(f"❌ Gemini API key index {_key_index} failed: {e}")
            
            # Rotate key immediately on error (do not trigger 60s wait on error rotation)
            rotate_key(sleep_on_cycle=False)
            
            if attempts >= max_attempts:
                # All keys tried twice, wait for a short duration to let quotas reset
                sleep_time = 10
                print(f"⏳ All API keys exhausted. Sleeping for {sleep_time}s...")
                time.sleep(sleep_time)
                attempts = 0


def get_embedding(text: str) -> list[float]:
    """
    Generate a single embedding vector for the given text.

    Args:
        text: The text to embed.

    Returns:
        A list of floats representing the embedding vector (768 dimensions).
    """
    result = _embed_with_rotation(text, "RETRIEVAL_DOCUMENT", 768)
    if hasattr(result, 'embeddings') and result.embeddings:
        return result.embeddings[0].values
    return result.embedding.values


def get_query_embedding(text: str) -> list[float]:
    """
    Generate an embedding optimized for search queries.

    Args:
        text: The search query text.

    Returns:
        A list of floats representing the query embedding vector.
    """
    result = _embed_with_rotation(text, "RETRIEVAL_QUERY", 768)
    if hasattr(result, 'embeddings') and result.embeddings:
        return result.embeddings[0].values
    return result.embedding.values


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts.

    Args:
        texts: List of text strings to embed.

    Returns:
        A list of embedding vectors, one per input text.
    """
    result = _embed_with_rotation(texts, "RETRIEVAL_DOCUMENT", 768)
    if hasattr(result, 'embeddings') and result.embeddings:
        return [e.values for e in result.embeddings]
    return [e.values for e in result.embedding]


def get_active_api_key() -> str:
    """Get the currently active API key from the rotation list."""
    if API_KEYS:
        return API_KEYS[_key_index]
    return ""


