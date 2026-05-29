"""
Vector similarity search for Bible verses using pgvector.

Retrieves the most semantically similar Bible verses to a given query
using cosine similarity search over Gemini embeddings stored in PostgreSQL.
"""
from chat.models import BibleVerse
from rag.embedder import get_query_embedding
from pgvector.django import CosineDistance


# Common book name aliases — maps user input variations to the canonical DB name
BOOK_ALIASES = {
    # Singular/plural
    'psalm': 'Psalms',
    'psalms': 'Psalms',
    'proverb': 'Proverbs',
    'proverbs': 'Proverbs',
    'lamentations': 'Lamentations',
    'lamentation': 'Lamentations',
    'revelation': 'Revelation',
    'revelations': 'Revelation',
    'chronicles': 'Chronicles',
    # Common abbreviations
    'gen': 'Genesis',
    'exod': 'Exodus',
    'lev': 'Leviticus',
    'num': 'Numbers',
    'deut': 'Deuteronomy',
    'josh': 'Joshua',
    'judg': 'Judges',
    'sam': 'Samuel',
    'matt': 'Matthew',
    'mk': 'Mark',
    'lk': 'Luke',
    'jn': 'John',
    'rom': 'Romans',
    'cor': 'Corinthians',
    'gal': 'Galatians',
    'eph': 'Ephesians',
    'phil': 'Philippians',
    'col': 'Colossians',
    'thess': 'Thessalonians',
    'tim': 'Timothy',
    'heb': 'Hebrews',
    'jas': 'James',
    'pet': 'Peter',
    'rev': 'Revelation',
    # Alternate names
    'song of songs': 'Song of Solomon',
    'canticles': 'Song of Solomon',
}


def normalize_book_name(book: str) -> str:
    """
    Normalize a book name using the alias map.

    Args:
        book: Raw book name from user input.

    Returns:
        Canonical book name if an alias exists, otherwise the original input.
    """
    return BOOK_ALIASES.get(book.lower().strip(), book)


def retrieve_similar_verses(query: str, top_k: int = 5) -> list[dict]:
    """
    Find the most similar Bible verses to the user's query.

    Args:
        query: The user's question or search text.
        top_k: Number of top results to return.

    Returns:
        A list of dicts with 'reference', 'text', and 'score' keys,
        ordered by similarity (most similar first).
    """
    # Generate query embedding
    query_embedding = get_query_embedding(query)

    # Cosine similarity search using pgvector (only verses that have embeddings)
    results = (
        BibleVerse.objects
        .exclude(embedding=None)
        .annotate(distance=CosineDistance('embedding', query_embedding))
        .order_by('distance')[:top_k]
    )

    verses = []
    for verse in results:
        verses.append({
            'reference': verse.reference,
            'book': verse.book,
            'chapter': verse.chapter,
            'verse': verse.verse,
            'text': verse.text,
            'score': round(1 - verse.distance, 4),  # Convert distance to similarity
        })

    return verses


def verify_verse_exists(book: str, chapter: int, verse: int) -> dict | None:
    """
    Check if a specific Bible verse exists in the database.
    Handles common name variations (e.g., Psalm → Psalms).

    Args:
        book: Book name (e.g., 'John', 'Psalm')
        chapter: Chapter number
        verse: Verse number

    Returns:
        A dict with verse details if found, None otherwise.
    """
    # Try with normalized alias first
    normalized_book = normalize_book_name(book)

    try:
        result = BibleVerse.objects.get(
            book__iexact=normalized_book,
            chapter=chapter,
            verse=verse,
        )
        return {
            'reference': result.reference,
            'text': result.text,
            'exists': True,
        }
    except BibleVerse.DoesNotExist:
        pass

    # Fallback: try fuzzy match with icontains (handles partial names)
    if normalized_book.lower() == book.lower():
        try:
            result = BibleVerse.objects.filter(
                book__icontains=book,
                chapter=chapter,
                verse=verse,
            ).first()
            if result:
                return {
                    'reference': result.reference,
                    'text': result.text,
                    'exists': True,
                }
        except Exception:
            pass

    return None
