"""Export book-level metadata to Prism as searchable documents.

Creates one document per Bible book (66 total) with comprehensive metadata
optimized for RAG (Retrieval-Augmented Generation) workflows.
"""

import asyncio
from typing import Dict, List, Any, Optional
import logging

from metadata_enrichment import (
    BOOK_AUTHORS,
    BOOK_DATES,
    BOOK_AUDIENCES,
    BOOK_LANGUAGES,
    BIBLICAL_ERAS,
    THEOLOGICAL_THEMES,
)
from csv_parser import BOOK_GENRES
from prism_client import import_documents_in_batches

# Set up logging
logger = logging.getLogger(__name__)

# Canonical book order with testament position
BIBLE_BOOKS = [
    # Old Testament (39 books)
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "I Samuel", "II Samuel",
    "I Kings", "II Kings", "I Chronicles", "II Chronicles",
    "Ezra", "Nehemiah", "Esther",
    "Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon",
    "Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel",
    "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah",
    "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
    # New Testament (27 books)
    "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "I Corinthians", "II Corinthians",
    "Galatians", "Ephesians", "Philippians", "Colossians",
    "I Thessalonians", "II Thessalonians",
    "I Timothy", "II Timothy", "Titus", "Philemon",
    "Hebrews", "James", "I Peter", "II Peter",
    "I John", "II John", "III John", "Jude",
    "Revelation of John",
]

# Book categories for classification
BOOK_CATEGORIES = {
    # Old Testament
    "Genesis": "Torah/Law", "Exodus": "Torah/Law", "Leviticus": "Torah/Law",
    "Numbers": "Torah/Law", "Deuteronomy": "Torah/Law",
    "Joshua": "Historical", "Judges": "Historical", "Ruth": "Historical",
    "I Samuel": "Historical", "II Samuel": "Historical",
    "I Kings": "Historical", "II Kings": "Historical",
    "I Chronicles": "Historical", "II Chronicles": "Historical",
    "Ezra": "Historical", "Nehemiah": "Historical", "Esther": "Historical",
    "Job": "Poetry/Wisdom", "Psalms": "Poetry/Wisdom",
    "Proverbs": "Poetry/Wisdom", "Ecclesiastes": "Poetry/Wisdom",
    "Song of Solomon": "Poetry/Wisdom",
    "Isaiah": "Major Prophets", "Jeremiah": "Major Prophets",
    "Lamentations": "Major Prophets", "Ezekiel": "Major Prophets",
    "Daniel": "Major Prophets",
    "Hosea": "Minor Prophets", "Joel": "Minor Prophets",
    "Amos": "Minor Prophets", "Obadiah": "Minor Prophets",
    "Jonah": "Minor Prophets", "Micah": "Minor Prophets",
    "Nahum": "Minor Prophets", "Habakkuk": "Minor Prophets",
    "Zephaniah": "Minor Prophets", "Haggai": "Minor Prophets",
    "Zechariah": "Minor Prophets", "Malachi": "Minor Prophets",
    # New Testament
    "Matthew": "Gospels", "Mark": "Gospels", "Luke": "Gospels", "John": "Gospels",
    "Acts": "History",
    "Romans": "Pauline Epistles", "I Corinthians": "Pauline Epistles",
    "II Corinthians": "Pauline Epistles", "Galatians": "Pauline Epistles",
    "Ephesians": "Pauline Epistles", "Philippians": "Pauline Epistles",
    "Colossians": "Pauline Epistles", "I Thessalonians": "Pauline Epistles",
    "II Thessalonians": "Pauline Epistles", "I Timothy": "Pastoral Epistles",
    "II Timothy": "Pastoral Epistles", "Titus": "Pastoral Epistles",
    "Philemon": "Pauline Epistles",
    "Hebrews": "General Epistles", "James": "General Epistles",
    "I Peter": "General Epistles", "II Peter": "General Epistles",
    "I John": "Johannine Epistles", "II John": "Johannine Epistles",
    "III John": "Johannine Epistles", "Jude": "General Epistles",
    "Revelation of John": "Apocalyptic",
}


def create_book_document(book_name: str, canonical_order: int) -> Dict[str, Any]:
    """
    Create a Prism document for a single Bible book.

    Args:
        book_name: Name of the book (e.g., "Romans")
        canonical_order: Position in Bible (1-66)

    Returns:
        Prism document dict with title, content, domain, and metadata
    """
    # Determine testament
    testament = "OT" if canonical_order <= 39 else "NT"
    testament_position = canonical_order if testament == "OT" else canonical_order - 39

    # Get metadata from dictionaries
    author = BOOK_AUTHORS.get(book_name, "Unknown")
    date = BOOK_DATES.get(book_name, "Unknown")
    language = BOOK_LANGUAGES.get(book_name, "Unknown")
    genre = BOOK_GENRES.get(book_name, "narrative")
    category = BOOK_CATEGORIES.get(book_name, "Unknown")
    themes = THEOLOGICAL_THEMES.get(book_name, [])
    eras = BIBLICAL_ERAS.get(book_name, [])
    audience = BOOK_AUDIENCES.get(book_name)

    # Build rich content for embedding
    parts = []

    # Overview
    parts.append(f"**{book_name}** is a {genre} book in the {testament} ({category}).")

    # Authorship and dating
    parts.append(f"Author: {author}. Composition date: {date}. Original language: {language}.")

    # Audience (if applicable)
    if audience:
        parts.append(f"Primary audience: {audience}.")

    # Historical context
    if eras:
        era_desc = ", ".join(eras)
        parts.append(f"Historical period: {era_desc}.")

    # Theological themes
    if themes:
        theme_desc = ", ".join(themes)
        parts.append(f"Major theological themes: {theme_desc}.")

    # Literary genre description
    genre_descriptions = {
        "narrative": "Story-driven historical narrative with sequential events",
        "law": "Legal and ceremonial instructions, structured legal code",
        "poetry": "Poetic literature with parallelism, imagery, and metaphor",
        "wisdom": "Wisdom literature with proverbs and philosophical reflection",
        "gospel": "Biographical account of Jesus' life, teachings, and ministry",
        "epistle": "Letter written to a specific church or individual",
        "prophecy": "Prophetic oracles with judgment, restoration, and future hope",
        "apocalyptic": "Apocalyptic visions with symbolic imagery and eschatology",
    }
    genre_desc = genre_descriptions.get(genre, "")
    if genre_desc:
        parts.append(f"Literary style: {genre_desc}.")

    content = " ".join(parts)

    # Create title
    title = f"Book of {book_name} - Biblical Scholarship Metadata"

    # Metadata
    metadata = {
        "book_name": book_name,
        "canonical_order": canonical_order,
        "testament": testament,
        "testament_position": testament_position,
        "category": category,
        "author": author,
        "date": date,
        "language": language,
        "genre": genre,
        "themes": themes,
        "historical_eras": eras,
    }

    if audience:
        metadata["audience"] = audience

    return {
        "title": title,
        "content": content,
        "domain": "metadata/books",
        "metadata": metadata,
    }


def export_all_books(dry_run: bool = False) -> List[Dict[str, Any]]:
    """
    Export metadata for all 66 Bible books.

    Args:
        dry_run: If True, return documents without importing

    Returns:
        List of Prism document dicts
    """
    documents = []

    for i, book_name in enumerate(BIBLE_BOOKS, start=1):
        doc = create_book_document(book_name, canonical_order=i)
        documents.append(doc)

    logger.info(f"Generated {len(documents)} book metadata documents")
    return documents


async def import_book_metadata(
    batch_size: int = 100,
    embed: bool = True,
    dry_run: bool = False,
    progress_callback: Optional[callable] = None,
) -> Dict[str, Any]:
    """
    Import all book metadata documents to Prism.

    Args:
        batch_size: Documents per batch (max 100)
        embed: Whether to generate embeddings
        dry_run: If True, return documents without importing
        progress_callback: Optional callback(batch_num, total_batches, result)

    Returns:
        Import results summary
    """
    documents = export_all_books(dry_run=True)

    if dry_run:
        return {
            "total_documents": len(documents),
            "sample_documents": documents[:3],
        }

    # Import to Prism
    results = await import_documents_in_batches(
        documents,
        batch_size=batch_size,
        embed=embed,
        progress_callback=progress_callback,
    )

    return results
