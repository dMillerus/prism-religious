"""Unit tests for CSV parser module."""

import pytest
from pathlib import Path

from csv_parser import (
    BibleVerse,
    parse_bible_csv,
    group_by_chapter,
    validate_verse_integrity,
    get_testament,
    BOOK_TO_ID,
)


class TestParseBibleCSV:
    """Test CSV parsing functionality."""

    def test_parse_valid_csv(self, sample_verses_csv_path):
        """Parse valid CSV successfully."""
        verses = parse_bible_csv(sample_verses_csv_path, "KJV")

        assert len(verses) == 13  # 5 Genesis + 6 Psalms + 2 John
        assert verses[0].book_name == "Genesis"
        assert verses[0].chapter == 1
        assert verses[0].verse == 1
        assert "In the beginning" in verses[0].text

    def test_parse_maintains_canonical_order(self, sample_verses_csv_path):
        """Verses should be sorted in canonical order."""
        verses = parse_bible_csv(sample_verses_csv_path, "KJV")

        # Genesis (book 1) should come before Psalms (book 19) and John (book 43)
        genesis_verses = [v for v in verses if v.book_name == "Genesis"]
        psalm_verses = [v for v in verses if v.book_name == "Psalms"]
        john_verses = [v for v in verses if v.book_name == "John"]

        assert genesis_verses[0].book_id < psalm_verses[0].book_id < john_verses[0].book_id

    def test_parse_unknown_books_raises_error(self, malformed_verses_csv_path):
        """Reject books not in 66-book canon."""
        with pytest.raises(ValueError) as exc_info:
            parse_bible_csv(malformed_verses_csv_path, "KJV")

        assert "Unknown books found" in str(exc_info.value)
        assert "UnknownBook" in str(exc_info.value)

    def test_parse_nonexistent_file_raises_error(self):
        """FileNotFoundError when CSV doesn't exist."""
        with pytest.raises(FileNotFoundError):
            parse_bible_csv(Path("/nonexistent/file.csv"), "KJV")

    def test_parse_filter_books(self, sample_verses_csv_path):
        """Filter specific books during parsing."""
        verses = parse_bible_csv(
            sample_verses_csv_path,
            "KJV",
            filter_books=["Genesis"]
        )

        assert len(verses) == 5
        assert all(v.book_name == "Genesis" for v in verses)

    def test_parse_strips_whitespace(self, sample_verses_csv_path):
        """Verse text should be stripped of leading/trailing whitespace."""
        verses = parse_bible_csv(sample_verses_csv_path, "KJV")

        for verse in verses:
            assert verse.text == verse.text.strip()
            assert not verse.text.startswith(" ")
            assert not verse.text.endswith(" ")


class TestGroupByChapter:
    """Test chapter grouping functionality."""

    def test_group_by_chapter_single_chapter(self, genesis_1_verses):
        """Single chapter returns one group."""
        groups = list(group_by_chapter(genesis_1_verses))

        assert len(groups) == 1
        assert len(groups[0]) == 5
        assert all(v.chapter == 1 for v in groups[0])

    def test_group_by_chapter_multiple_chapters(self, mixed_chapter_verses):
        """Multiple chapters grouped correctly."""
        groups = list(group_by_chapter(mixed_chapter_verses))

        # Should have 3 groups: Genesis 1, Genesis 2, Psalms 23
        assert len(groups) == 3

        # First group: Genesis 1
        assert groups[0][0].book_name == "Genesis"
        assert groups[0][0].chapter == 1
        assert len(groups[0]) == 5

        # Second group: Genesis 2
        assert groups[1][0].book_name == "Genesis"
        assert groups[1][0].chapter == 2
        assert len(groups[1]) == 1

        # Third group: Psalms 23
        assert groups[2][0].book_name == "Psalms"
        assert groups[2][0].chapter == 23
        assert len(groups[2]) == 6

    def test_group_by_chapter_preserves_order(self, genesis_1_verses):
        """Verses within chapter maintain order."""
        groups = list(group_by_chapter(genesis_1_verses))

        verses = groups[0]
        for i in range(len(verses) - 1):
            assert verses[i].verse < verses[i + 1].verse

    def test_group_by_chapter_empty_input(self):
        """Empty input returns no groups."""
        groups = list(group_by_chapter([]))
        assert len(groups) == 0


class TestValidateVerseIntegrity:
    """Test verse data validation."""

    def test_validate_verse_integrity_valid_data(self, genesis_1_verses):
        """Valid verses pass integrity check."""
        result = validate_verse_integrity(genesis_1_verses)

        assert result["total_verses"] == 5
        assert result["books_found"] == 1
        assert result["chapters_found"] == 1
        assert "Genesis" in result["books"]
        assert len(result["issues"]) == 0

    def test_validate_verse_integrity_finds_empty_text(self):
        """Detect verses with empty text."""
        verses = [
            BibleVerse(
                book_id=1,
                book_name="Genesis",
                chapter=1,
                verse=1,
                text="Valid text",
            ),
            BibleVerse(
                book_id=1,
                book_name="Genesis",
                chapter=1,
                verse=2,
                text="",  # Empty text
            ),
            BibleVerse(
                book_id=1,
                book_name="Genesis",
                chapter=1,
                verse=3,
                text="   ",  # Whitespace only
            ),
        ]

        result = validate_verse_integrity(verses)

        assert len(result["issues"]) == 2
        assert "Empty text" in result["issues"][0]
        assert "Genesis 1:2" in result["issues"][0]
        assert "Genesis 1:3" in result["issues"][1]

    def test_validate_verse_integrity_multiple_books(
        self, genesis_1_verses, psalm_23_verses
    ):
        """Count multiple books correctly."""
        all_verses = genesis_1_verses + psalm_23_verses
        result = validate_verse_integrity(all_verses)

        assert result["books_found"] == 2
        assert result["chapters_found"] == 2
        assert "Genesis" in result["books"]
        assert "Psalms" in result["books"]


class TestGetTestament:
    """Test testament classification."""

    def test_get_testament_old_testament(self):
        """Books 1-39 are Old Testament."""
        assert get_testament(1) == "OT"  # Genesis
        assert get_testament(19) == "OT"  # Psalms
        assert get_testament(39) == "OT"  # Malachi

    def test_get_testament_new_testament(self):
        """Books 40-66 are New Testament."""
        assert get_testament(40) == "NT"  # Matthew
        assert get_testament(43) == "NT"  # John
        assert get_testament(66) == "NT"  # Revelation


class TestBibleVerse:
    """Test BibleVerse dataclass functionality."""

    def test_verse_testament_property(self):
        """Testament property returns correct value."""
        ot_verse = BibleVerse(1, "Genesis", 1, 1, "Text")
        nt_verse = BibleVerse(43, "John", 3, 16, "Text")

        assert ot_verse.testament == "OT"
        assert nt_verse.testament == "NT"

    def test_verse_reference_property(self):
        """Reference property formats correctly."""
        verse = BibleVerse(1, "Genesis", 1, 1, "Text")
        assert verse.reference == "Genesis 1:1"

        verse2 = BibleVerse(19, "Psalms", 23, 1, "Text")
        assert verse2.reference == "Psalms 23:1"

    def test_verse_sorting(self):
        """Verses sort by canonical order."""
        verse1 = BibleVerse(1, "Genesis", 1, 1, "Text")
        verse2 = BibleVerse(1, "Genesis", 1, 2, "Text")
        verse3 = BibleVerse(19, "Psalms", 23, 1, "Text")

        verses = [verse3, verse2, verse1]
        verses.sort()

        assert verses == [verse1, verse2, verse3]


class TestBibleBooks:
    """Test Bible book constants."""

    def test_book_to_id_mapping(self):
        """BOOK_TO_ID contains all 66 books."""
        assert len(BOOK_TO_ID) == 66

        # Test specific mappings
        assert BOOK_TO_ID["Genesis"] == 1
        assert BOOK_TO_ID["Psalms"] == 19
        assert BOOK_TO_ID["Malachi"] == 39
        assert BOOK_TO_ID["Matthew"] == 40
        assert BOOK_TO_ID["John"] == 43
        assert BOOK_TO_ID["Revelation of John"] == 66

    def test_book_ids_sequential(self):
        """Book IDs are sequential from 1-66."""
        ids = sorted(BOOK_TO_ID.values())
        assert ids == list(range(1, 67))
