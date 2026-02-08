"""CSV parser for scrollmapper Bible database format."""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, List, Optional, Set, Dict, Any


# Bible book order and testament mapping (standard 66-book canon)
BIBLE_BOOKS = [
    # Old Testament (1-39)
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "I Samuel", "II Samuel",
    "I Kings", "II Kings", "I Chronicles", "II Chronicles",
    "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
    "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations",
    "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
    "Zephaniah", "Haggai", "Zechariah", "Malachi",
    # New Testament (40-66)
    "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "I Corinthians", "II Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "I Thessalonians", "II Thessalonians",
    "I Timothy", "II Timothy", "Titus", "Philemon",
    "Hebrews", "James", "I Peter", "II Peter",
    "I John", "II John", "III John", "Jude", "Revelation of John",
]

BOOK_TO_ID = {book: idx + 1 for idx, book in enumerate(BIBLE_BOOKS)}


def get_testament(book_id: int) -> str:
    """Get testament (OT/NT) from book ID."""
    return "OT" if book_id <= 39 else "NT"


@dataclass
class BibleBook:
    """Metadata for a Bible book."""

    book_id: int
    name: str
    testament: str

    @property
    def normalized_name(self) -> str:
        """Get standardized book name for display."""
        return self.name


@dataclass
class BibleVerse:
    """A single Bible verse with metadata."""

    book_id: int
    book_name: str
    chapter: int
    verse: int
    text: str

    @property
    def testament(self) -> str:
        """Get testament for this verse."""
        return get_testament(self.book_id)

    @property
    def reference(self) -> str:
        """Get human-readable reference (e.g., 'Genesis 1:1')."""
        return f"{self.book_name} {self.chapter}:{self.verse}"

    def __lt__(self, other: "BibleVerse") -> bool:
        """Enable sorting by canonical order."""
        return (self.book_id, self.chapter, self.verse) < (
            other.book_id,
            other.chapter,
            other.verse,
        )


def parse_bible_csv(
    verses_path: Path,
    translation: str,
    filter_books: Optional[List[str]] = None,
) -> List[BibleVerse]:
    """
    Parse scrollmapper Bible CSV format.

    Args:
        verses_path: Path to verses CSV file (e.g., KJV.csv)
        translation: Translation identifier (e.g., "KJV")
        filter_books: Optional list of book names to import (for testing)

    Returns:
        List of BibleVerse objects in canonical order

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV format is invalid or contains unknown books
    """
    if not verses_path.exists():
        raise FileNotFoundError(f"Verses CSV not found: {verses_path}")

    verses: List[BibleVerse] = []
    unknown_books: Set[str] = set()

    with open(verses_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if not all(col in reader.fieldnames for col in ["Book", "Chapter", "Verse", "Text"]):
            raise ValueError(
                f"Invalid CSV format in {verses_path}. "
                "Expected columns: Book, Chapter, Verse, Text"
            )

        for row in reader:
            book_name = row["Book"]

            # Skip books not in filter if provided
            if filter_books and book_name not in filter_books:
                continue

            # Track unknown books
            if book_name not in BOOK_TO_ID:
                unknown_books.add(book_name)
                continue

            verse = BibleVerse(
                book_id=BOOK_TO_ID[book_name],
                book_name=book_name,
                chapter=int(row["Chapter"]),
                verse=int(row["Verse"]),
                text=row["Text"].strip(),
            )
            verses.append(verse)

    if unknown_books:
        raise ValueError(
            f"Unknown books found in {translation} CSV: {sorted(unknown_books)}. "
            "These books are not in the standard 66-book canon."
        )

    if not verses:
        raise ValueError(f"No verses found in {verses_path}")

    # Sort by canonical order
    verses.sort()

    return verses


def get_available_books(verses_path: Path) -> List[str]:
    """Get list of all book names in a verses CSV file."""
    if not verses_path.exists():
        raise FileNotFoundError(f"Verses CSV not found: {verses_path}")

    books: Set[str] = set()
    with open(verses_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            books.add(row["Book"])

    return sorted(books)


def group_by_chapter(verses: List[BibleVerse]) -> Generator[List[BibleVerse], None, None]:
    """
    Group verses by chapter.

    Yields:
        Lists of verses for each chapter in canonical order
    """
    if not verses:
        return

    current_chapter_verses: List[BibleVerse] = []
    current_book_id = verses[0].book_id
    current_chapter = verses[0].chapter

    for verse in verses:
        # Check if we've moved to a new chapter
        if verse.book_id != current_book_id or verse.chapter != current_chapter:
            if current_chapter_verses:
                yield current_chapter_verses
            current_chapter_verses = []
            current_book_id = verse.book_id
            current_chapter = verse.chapter

        current_chapter_verses.append(verse)

    # Yield final chapter
    if current_chapter_verses:
        yield current_chapter_verses


def validate_verse_integrity(verses: List[BibleVerse]) -> Dict[str, Any]:
    """
    Validate verse data integrity.

    Returns:
        Dict with validation statistics and any issues found
    """
    issues: List[str] = []
    total_verses = len(verses)
    books_found: Set[str] = set()
    chapters_by_book: Dict[str, Set[int]] = {}

    for verse in verses:
        books_found.add(verse.book_name)
        if verse.book_name not in chapters_by_book:
            chapters_by_book[verse.book_name] = set()
        chapters_by_book[verse.book_name].add(verse.chapter)

        # Check for empty text
        if not verse.text or not verse.text.strip():
            issues.append(f"Empty text in {verse.reference}")

    return {
        "total_verses": total_verses,
        "books_found": len(books_found),
        "chapters_found": sum(len(chapters) for chapters in chapters_by_book.values()),
        "books": sorted(books_found),
        "issues": issues,
    }
