"""Adaptive verse chunking for optimal LLM consumption."""

import tiktoken
from typing import Generator, List, Dict, Any

from csv_parser import BibleVerse, group_by_chapter
from config import settings


# Initialize tiktoken encoder (cl100k_base is used by GPT-4 and compatible models)
encoder = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken."""
    return len(encoder.encode(text))


def chunk_verses(
    verses: List[BibleVerse],
    translation: str,
) -> Generator[Dict[str, Any], None, None]:
    """
    Group verses into optimal chunks for LLM consumption.

    Strategy:
    - Process chapter-by-chapter (never span chapters)
    - Accumulate verses until reaching target token count (300-400)
    - Handle long verses (>max_tokens) as standalone chunks
    - Merge small trailing chunks with previous if possible

    Args:
        verses: List of verses in canonical order
        translation: Translation identifier (e.g., "KJV")

    Yields:
        Dict representations of chunks ready for Prism import
    """
    for chapter_verses in group_by_chapter(verses):
        yield from _chunk_chapter(chapter_verses, translation)


def _chunk_chapter(
    verses: List[BibleVerse],
    translation: str,
) -> Generator[Dict[str, Any], None, None]:
    """
    Chunk a single chapter using token-aware grouping.

    Args:
        verses: All verses from one chapter
        translation: Translation identifier

    Yields:
        Chunk dictadocuments ready for Prism
    """
    if not verses:
        return

    current_chunk: List[BibleVerse] = []
    current_tokens = 0

    for i, verse in enumerate(verses):
        verse_tokens = count_tokens(verse.text)

        # Case 1: Single verse exceeds max_tokens - make it standalone
        if verse_tokens > settings.max_chunk_tokens:
            # First, flush current chunk if it exists
            if current_chunk:
                yield _create_chunk_document(current_chunk, translation)
                current_chunk = []
                current_tokens = 0

            # Emit oversized verse as standalone chunk
            yield _create_chunk_document([verse], translation)
            continue

        # Case 2: Adding this verse would exceed target - decide whether to flush
        if current_tokens + verse_tokens > settings.target_chunk_tokens:
            # Only flush if we're near or above target
            # This prevents creating tiny chunks when we're close to target
            if current_tokens >= settings.target_chunk_tokens * 0.8:  # 80% threshold
                yield _create_chunk_document(current_chunk, translation)
                current_chunk = [verse]
                current_tokens = verse_tokens
            else:
                # We're below 80% of target, keep accumulating
                current_chunk.append(verse)
                current_tokens += verse_tokens
        else:
            # Case 3: Normal accumulation
            current_chunk.append(verse)
            current_tokens += verse_tokens

    # Flush final chunk
    if current_chunk:
        yield _create_chunk_document(current_chunk, translation)


def _create_chunk_document(verses: List[BibleVerse], translation: str) -> Dict[str, Any]:
    """
    Create a Prism document from a verse group.

    Args:
        verses: One or more consecutive verses
        translation: Translation identifier

    Returns:
        Dict ready for Prism corpus import API
    """
    if not verses:
        raise ValueError("Cannot create chunk from empty verse list")

    first_verse = verses[0]
    last_verse = verses[-1]

    # Build verse range (e.g., "1-5" or just "1" for single verse)
    if len(verses) == 1:
        verse_range = str(first_verse.verse)
        title = f"{first_verse.book_name} {first_verse.chapter}:{first_verse.verse} ({translation})"
    else:
        verse_range = f"{first_verse.verse}-{last_verse.verse}"
        title = (
            f"{first_verse.book_name} {first_verse.chapter}:{verse_range} ({translation})"
        )

    # Combine verse texts with verse numbers
    content_lines = []
    for verse in verses:
        content_lines.append(f"{verse.verse} {verse.text}")
    content = "\n".join(content_lines)

    # Calculate token count for verification
    token_count = count_tokens(content)

    # Build hierarchical path for navigation
    path = (
        f"{translation} > {first_verse.book_name} > "
        f"Chapter {first_verse.chapter} > Verses {verse_range}"
    )

    return {
        "title": title,
        "content": content,
        "domain": f"bible/{translation.lower()}",
        "metadata": {
            "book": first_verse.book_name,
            "book_id": first_verse.book_id,
            "chapter": first_verse.chapter,
            "verse_start": first_verse.verse,
            "verse_end": last_verse.verse,
            "testament": first_verse.testament,
            "translation": translation,
            "language": "en",  # TODO: Add language detection for other translations
            "structure": {
                "path": path,
                "book_number": first_verse.book_id,
                "total_verses": len(verses),
                "token_count": token_count,
            },
            "source": {
                "type": "corpus",
                "origin": "scrollmapper/bible_databases",
                "url": "https://github.com/scrollmapper/bible_databases",
                "format": "csv",
            },
        },
    }


def analyze_chunking_quality(verses: List[BibleVerse], translation: str) -> Dict[str, Any]:
    """
    Analyze chunking quality without creating documents.

    Returns statistics about token distribution, chunk counts, etc.

    Args:
        verses: Verses to analyze
        translation: Translation identifier

    Returns:
        Dict with quality metrics
    """
    chunks = list(chunk_verses(verses, translation))

    token_counts = [chunk["metadata"]["structure"]["token_count"] for chunk in chunks]

    return {
        "total_verses": len(verses),
        "total_chunks": len(chunks),
        "verses_per_chunk_avg": len(verses) / len(chunks) if chunks else 0,
        "token_stats": {
            "min": min(token_counts) if token_counts else 0,
            "max": max(token_counts) if token_counts else 0,
            "avg": sum(token_counts) / len(token_counts) if token_counts else 0,
        },
        "chunks_below_min": sum(1 for t in token_counts if t < settings.min_chunk_tokens),
        "chunks_above_max": sum(1 for t in token_counts if t > settings.max_chunk_tokens),
        "chunks_in_target_range": sum(
            1
            for t in token_counts
            if settings.target_chunk_tokens * 0.8
            <= t
            <= settings.target_chunk_tokens * 1.2
        ),
    }
