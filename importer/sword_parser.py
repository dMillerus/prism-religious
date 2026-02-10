"""SWORD module parser for extracting original Hebrew and Greek texts.

Parses Westminster Leningrad Codex (WLC) and SBL Greek New Testament (SBLGNT)
to extract original language text with optional Strong's numbers for interlinear
display and word studies.

SWORD modules: https://www.crosswire.org/sword/
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from pysword.modules import SwordModules

# Set up logging
logger = logging.getLogger(__name__)


class SwordParser:
    """Parser for SWORD Bible modules (Hebrew OT, Greek NT)."""

    # Book name normalization mapping
    BOOK_NAME_MAP = {
        # Roman numerals to numbers
        "I Samuel": "1 Samuel",
        "II Samuel": "2 Samuel",
        "I Kings": "1 Kings",
        "II Kings": "2 Kings",
        "I Chronicles": "1 Chronicles",
        "II Chronicles": "2 Chronicles",
        "I Corinthians": "1 Corinthians",
        "II Corinthians": "2 Corinthians",
        "I Thessalonians": "1 Thessalonians",
        "II Thessalonians": "2 Thessalonians",
        "I Timothy": "1 Timothy",
        "II Timothy": "2 Timothy",
        "I Peter": "1 Peter",
        "II Peter": "2 Peter",
        "I John": "1 John",
        "II John": "2 John",
        "III John": "3 John",

        # Special cases
        "Song of Solomon": "Song of Songs",
        "Revelation of John": "Revelation",
        "Psalm": "Psalms",  # Singular to plural
    }

    # Old Testament books (use WLC Hebrew module)
    OT_BOOKS = {
        "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
        "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
        "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles",
        "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
        "Ecclesiastes", "Song of Songs", "Isaiah", "Jeremiah",
        "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
        "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
        "Zephaniah", "Haggai", "Zechariah", "Malachi"
    }

    # New Testament books (use SBLGNT Greek module)
    NT_BOOKS = {
        "Matthew", "Mark", "Luke", "John", "Acts",
        "Romans", "1 Corinthians", "2 Corinthians", "Galatians",
        "Ephesians", "Philippians", "Colossians",
        "1 Thessalonians", "2 Thessalonians",
        "1 Timothy", "2 Timothy", "Titus", "Philemon",
        "Hebrews", "James", "1 Peter", "2 Peter",
        "1 John", "2 John", "3 John", "Jude", "Revelation"
    }

    def __init__(self, modules_dir: Path = Path("data_sources/sword_modules")):
        """
        Initialize SWORD parser.

        Args:
            modules_dir: Path to SWORD modules directory
        """
        self.modules_dir = modules_dir
        self.modules: Optional[SwordModules] = None
        self.wlc: Optional[Any] = None  # Hebrew OT module
        self.sblgnt: Optional[Any] = None  # Greek NT module

    def initialize(self) -> None:
        """
        Initialize SWORD modules (lazy loading).

        Raises:
            FileNotFoundError: If modules directory doesn't exist
            RuntimeError: If modules cannot be loaded
        """
        if not self.modules_dir.exists():
            raise FileNotFoundError(
                f"SWORD modules directory not found: {self.modules_dir}. "
                "Download modules first."
            )

        try:
            self.modules = SwordModules(str(self.modules_dir))

            # Parse available modules
            available = self.modules.parse_modules()
            logger.info(f"Available SWORD modules: {available}")

            # Load Hebrew OT (WLC - Westminster Leningrad Codex)
            if "WLC" in available:
                self.wlc = self.modules.get_bible_from_module("WLC")
                logger.info("Loaded WLC (Hebrew OT) module")
            else:
                logger.warning("WLC module not found")

            # Load Greek NT (SBLGNT - SBL Greek New Testament)
            if "SBLGNT" in available:
                self.sblgnt = self.modules.get_bible_from_module("SBLGNT")
                logger.info("Loaded SBLGNT (Greek NT) module")
            else:
                logger.warning("SBLGNT module not found")

        except Exception as e:
            raise RuntimeError(f"Failed to initialize SWORD modules: {e}")

    def normalize_book_name(self, book_name: str) -> str:
        """
        Normalize book name to SWORD format.

        Converts Roman numerals (I, II, III) to numbers (1, 2, 3)
        and handles special cases like "Song of Solomon" → "Song of Songs".

        Args:
            book_name: Book name from CSV (e.g., "I Samuel", "Song of Solomon")

        Returns:
            Normalized book name (e.g., "1 Samuel", "Song of Songs")
        """
        # Check mapping first
        if book_name in self.BOOK_NAME_MAP:
            return self.BOOK_NAME_MAP[book_name]

        # Generic Roman numeral replacement
        book_name = book_name.replace("I ", "1 ")
        book_name = book_name.replace("II ", "2 ")
        book_name = book_name.replace("III ", "3 ")

        return book_name

    def get_testament(self, book_name: str) -> str:
        """
        Determine if book is Old Testament or New Testament.

        Args:
            book_name: Normalized book name

        Returns:
            "OT" or "NT"

        Raises:
            ValueError: If book name not recognized
        """
        normalized = self.normalize_book_name(book_name)

        if normalized in self.OT_BOOKS:
            return "OT"
        elif normalized in self.NT_BOOKS:
            return "NT"
        else:
            raise ValueError(f"Unknown book: {book_name} (normalized: {normalized})")

    def _clean_sword_markup(self, text: str) -> str:
        """
        Remove OSIS XML markup from verse text.

        SWORD modules use OSIS (Open Scripture Information Standard) XML.
        This removes common tags like <w>, <divineName>, <transChange>, etc.

        Args:
            text: Raw text from SWORD module with markup

        Returns:
            Clean text without markup
        """
        if not text:
            return ""

        # Remove OSIS XML tags (simple approach - good enough for display)
        # More sophisticated parsing would use an XML parser
        text = re.sub(r'<[^>]+>', '', text)

        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def _extract_strongs_numbers(self, text: str) -> List[str]:
        """
        Extract Strong's numbers from OSIS markup.

        OSIS format uses lemma attributes like:
        <w lemma="strong:H7225">בְּרֵאשִׁית</w>

        Args:
            text: Raw text from SWORD module with markup

        Returns:
            List of Strong's numbers (e.g., ["H7225", "H1254", "H430"])
        """
        if not text:
            return []

        # Pattern: lemma="strong:H####" or lemma="strong:G####"
        pattern = r'lemma="strong:([HG]\d+)"'
        matches = re.findall(pattern, text)

        # Return unique Strong's numbers in order of appearance
        seen = set()
        result = []
        for match in matches:
            if match not in seen:
                seen.add(match)
                result.append(match)

        return result

    def get_verse_text(
        self,
        book: str,
        chapter: int,
        verse: int,
        testament: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get original language text for a single verse.

        Args:
            book: Book name (will be normalized)
            chapter: Chapter number
            verse: Verse number
            testament: Optional "OT" or "NT" (auto-detected if None)

        Returns:
            Dictionary with original_text, language, and optional strongs_numbers,
            or None if verse not found or module not loaded

        Raises:
            RuntimeError: If modules not initialized
        """
        if self.modules is None:
            raise RuntimeError("SWORD modules not initialized. Call initialize() first.")

        # Normalize book name
        normalized_book = self.normalize_book_name(book)

        # Determine testament
        if testament is None:
            try:
                testament = self.get_testament(normalized_book)
            except ValueError as e:
                logger.error(f"Cannot determine testament for {book}: {e}")
                return None

        # Select module
        if testament == "OT":
            if self.wlc is None:
                logger.warning("WLC module not loaded")
                return None
            module = self.wlc
            language = "hebrew"
        else:  # NT
            if self.sblgnt is None:
                logger.warning("SBLGNT module not loaded")
                return None
            module = self.sblgnt
            language = "greek"

        # Fetch verse
        try:
            # pysword returns raw text with OSIS markup
            raw_text = module.get(
                books=[normalized_book],
                chapters=[chapter],
                verses=[verse]
            )

            if not raw_text:
                logger.warning(
                    f"No text found for {normalized_book} {chapter}:{verse}"
                )
                return None

            # Extract Strong's numbers (before cleaning)
            strongs = self._extract_strongs_numbers(raw_text)

            # Clean markup for display
            clean_text = self._clean_sword_markup(raw_text)

            result = {
                "original_text": clean_text,
                "language": language,
            }

            # Add Strong's numbers if present
            if strongs:
                result["strongs_numbers"] = strongs

            return result

        except Exception as e:
            logger.error(
                f"Error fetching {normalized_book} {chapter}:{verse}: {e}"
            )
            return None

    def get_chapter_verses(
        self,
        book: str,
        chapter: int,
        verse_start: int = 1,
        verse_end: int = 200,
    ) -> Dict[int, Dict[str, Any]]:
        """
        Get original texts for a range of verses (batch operation).

        More efficient than calling get_verse_text() repeatedly.

        Args:
            book: Book name
            chapter: Chapter number
            verse_start: Starting verse (default: 1)
            verse_end: Ending verse (default: 200, will stop at actual end)

        Returns:
            Dictionary mapping verse numbers to verse data
        """
        results = {}

        for verse in range(verse_start, verse_end + 1):
            verse_data = self.get_verse_text(book, chapter, verse)
            if verse_data is None:
                # Stop when we hit the end of the chapter
                break
            results[verse] = verse_data

        return results


def verify_book_normalization() -> Dict[str, str]:
    """
    Verify book name normalization for all 66 Bible books.

    Returns:
        Dictionary mapping original names to normalized names
    """
    parser = SwordParser()

    # All 66 Bible books (as they appear in typical CSV files)
    all_books = [
        # Old Testament (39 books)
        "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
        "Joshua", "Judges", "Ruth", "I Samuel", "II Samuel",
        "I Kings", "II Kings", "I Chronicles", "II Chronicles",
        "Ezra", "Nehemiah", "Esther", "Job", "Psalms", "Proverbs",
        "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah",
        "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
        "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
        "Zephaniah", "Haggai", "Zechariah", "Malachi",

        # New Testament (27 books)
        "Matthew", "Mark", "Luke", "John", "Acts",
        "Romans", "I Corinthians", "II Corinthians", "Galatians",
        "Ephesians", "Philippians", "Colossians",
        "I Thessalonians", "II Thessalonians",
        "I Timothy", "II Timothy", "Titus", "Philemon",
        "Hebrews", "James", "I Peter", "II Peter",
        "I John", "II John", "III John", "Jude", "Revelation of John"
    ]

    normalization_map = {}
    for book in all_books:
        normalized = parser.normalize_book_name(book)
        normalization_map[book] = normalized

    return normalization_map
