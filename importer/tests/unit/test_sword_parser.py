"""Unit tests for SWORD module parser."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from sword_parser import SwordParser, verify_book_normalization


class TestSwordParser:
    """Tests for SwordParser class."""

    @pytest.fixture
    def parser(self, tmp_path):
        """Create parser with temporary modules directory."""
        modules_dir = tmp_path / "sword_modules"
        modules_dir.mkdir()
        return SwordParser(modules_dir=modules_dir)

    def test_book_name_normalization_roman_numerals(self, parser):
        """Test Roman numeral to number conversion."""
        assert parser.normalize_book_name("I Samuel") == "1 Samuel"
        assert parser.normalize_book_name("II Samuel") == "2 Samuel"
        assert parser.normalize_book_name("I Kings") == "1 Kings"
        assert parser.normalize_book_name("II Kings") == "2 Kings"
        assert parser.normalize_book_name("I Chronicles") == "1 Chronicles"
        assert parser.normalize_book_name("II Chronicles") == "2 Chronicles"
        assert parser.normalize_book_name("I Corinthians") == "1 Corinthians"
        assert parser.normalize_book_name("II Corinthians") == "2 Corinthians"
        assert parser.normalize_book_name("I Thessalonians") == "1 Thessalonians"
        assert parser.normalize_book_name("II Thessalonians") == "2 Thessalonians"
        assert parser.normalize_book_name("I Timothy") == "1 Timothy"
        assert parser.normalize_book_name("II Timothy") == "2 Timothy"
        assert parser.normalize_book_name("I Peter") == "1 Peter"
        assert parser.normalize_book_name("II Peter") == "2 Peter"
        assert parser.normalize_book_name("I John") == "1 John"
        assert parser.normalize_book_name("II John") == "2 John"
        assert parser.normalize_book_name("III John") == "3 John"

    def test_book_name_normalization_special_cases(self, parser):
        """Test special case book names."""
        assert parser.normalize_book_name("Song of Solomon") == "Song of Songs"
        assert parser.normalize_book_name("Revelation of John") == "Revelation"
        assert parser.normalize_book_name("Psalm") == "Psalms"

    def test_book_name_normalization_unchanged(self, parser):
        """Test books that don't need normalization."""
        unchanged_books = [
            "Genesis", "Exodus", "Matthew", "Mark", "Luke", "John",
            "Acts", "Romans", "Galatians", "Ephesians", "Hebrews",
            "James", "Jude", "Revelation"
        ]
        for book in unchanged_books:
            assert parser.normalize_book_name(book) == book

    def test_get_testament_old_testament(self, parser):
        """Test Old Testament book detection."""
        ot_books = ["Genesis", "Exodus", "Psalms", "Isaiah", "Malachi"]
        for book in ot_books:
            assert parser.get_testament(book) == "OT"

    def test_get_testament_new_testament(self, parser):
        """Test New Testament book detection."""
        nt_books = ["Matthew", "Acts", "Romans", "Revelation"]
        for book in nt_books:
            assert parser.get_testament(book) == "NT"

    def test_get_testament_normalized_names(self, parser):
        """Test testament detection with names requiring normalization."""
        assert parser.get_testament("I Samuel") == "OT"
        assert parser.get_testament("II Kings") == "OT"
        assert parser.get_testament("I Corinthians") == "NT"
        assert parser.get_testament("II Peter") == "NT"

    def test_get_testament_unknown_book(self, parser):
        """Test testament detection with unknown book."""
        with pytest.raises(ValueError) as exc_info:
            parser.get_testament("Unknown Book")
        assert "Unknown book" in str(exc_info.value)

    def test_clean_sword_markup_simple_tags(self, parser):
        """Test removing simple OSIS XML tags."""
        text = "<w>word</w> <w>another</w>"
        cleaned = parser._clean_sword_markup(text)
        assert cleaned == "word another"

    def test_clean_sword_markup_nested_tags(self, parser):
        """Test removing nested OSIS tags."""
        text = "<w lemma='strong:H430'><divineName>God</divineName></w>"
        cleaned = parser._clean_sword_markup(text)
        assert cleaned == "God"

    def test_clean_sword_markup_with_attributes(self, parser):
        """Test removing tags with attributes."""
        text = '<w lemma="strong:H7225" morph="HNcfsa">בְּרֵאשִׁית</w>'
        cleaned = parser._clean_sword_markup(text)
        assert cleaned == "בְּרֵאשִׁית"

    def test_clean_sword_markup_multiple_spaces(self, parser):
        """Test collapsing multiple spaces."""
        text = "word1   <w>word2</w>    word3"
        cleaned = parser._clean_sword_markup(text)
        assert cleaned == "word1 word2 word3"

    def test_clean_sword_markup_empty_input(self, parser):
        """Test cleaning empty or None input."""
        assert parser._clean_sword_markup(None) == ""
        assert parser._clean_sword_markup("") == ""
        assert parser._clean_sword_markup("   ") == ""

    def test_extract_strongs_numbers_single(self, parser):
        """Test extracting single Strong's number."""
        text = '<w lemma="strong:H430">God</w>'
        strongs = parser._extract_strongs_numbers(text)
        assert strongs == ["H430"]

    def test_extract_strongs_numbers_multiple(self, parser):
        """Test extracting multiple Strong's numbers."""
        text = (
            '<w lemma="strong:H7225">בְּרֵאשִׁית</w> '
            '<w lemma="strong:H1254">בָּרָא</w> '
            '<w lemma="strong:H430">אֱלֹהִים</w>'
        )
        strongs = parser._extract_strongs_numbers(text)
        assert strongs == ["H7225", "H1254", "H430"]

    def test_extract_strongs_numbers_greek(self, parser):
        """Test extracting Greek Strong's numbers."""
        text = (
            '<w lemma="strong:G1722">Ἐν</w> '
            '<w lemma="strong:G746">ἀρχῇ</w> '
            '<w lemma="strong:G1510">ἦν</w>'
        )
        strongs = parser._extract_strongs_numbers(text)
        assert strongs == ["G1722", "G746", "G1510"]

    def test_extract_strongs_numbers_duplicates(self, parser):
        """Test deduplication of Strong's numbers."""
        text = (
            '<w lemma="strong:H430">God</w> '
            '<w lemma="strong:H430">God</w> '
            '<w lemma="strong:H1254">created</w>'
        )
        strongs = parser._extract_strongs_numbers(text)
        assert strongs == ["H430", "H1254"]  # No duplicates, order preserved

    def test_extract_strongs_numbers_none_found(self, parser):
        """Test when no Strong's numbers present."""
        text = "<w>plain text without lemma</w>"
        strongs = parser._extract_strongs_numbers(text)
        assert strongs == []

    def test_extract_strongs_numbers_empty_input(self, parser):
        """Test extracting from empty input."""
        assert parser._extract_strongs_numbers(None) == []
        assert parser._extract_strongs_numbers("") == []

    def test_initialize_missing_directory(self):
        """Test initialization with missing modules directory."""
        # Don't use fixture - create parser with truly missing dir
        parser = SwordParser(modules_dir=Path("/nonexistent/path"))

        with pytest.raises(FileNotFoundError) as exc_info:
            parser.initialize()
        assert "not found" in str(exc_info.value).lower()

    def test_initialize_success(self, parser):
        """Test successful initialization with mocked modules."""
        # Create modules directory
        parser.modules_dir.mkdir(exist_ok=True)

        # Mock SwordModules
        with patch("sword_parser.SwordModules") as mock_modules_class:
            mock_modules = Mock()
            mock_modules.parse_modules.return_value = ["WLC", "SBLGNT"]
            mock_modules.get_bible_from_module = Mock(side_effect=lambda name: Mock())
            mock_modules_class.return_value = mock_modules

            parser.initialize()

            # Verify initialization
            assert parser.modules is not None
            assert parser.wlc is not None
            assert parser.sblgnt is not None

    def test_initialize_missing_wlc(self, parser, caplog):
        """Test initialization when WLC module missing."""
        parser.modules_dir.mkdir(exist_ok=True)

        with patch("sword_parser.SwordModules") as mock_modules_class:
            mock_modules = Mock()
            mock_modules.parse_modules.return_value = ["SBLGNT"]  # No WLC
            mock_modules.get_bible_from_module = Mock(return_value=Mock())
            mock_modules_class.return_value = mock_modules

            parser.initialize()

            assert parser.wlc is None
            assert parser.sblgnt is not None
            assert "WLC module not found" in caplog.text

    def test_get_verse_text_not_initialized(self, parser):
        """Test getting verse text without initialization."""
        with pytest.raises(RuntimeError) as exc_info:
            parser.get_verse_text("Genesis", 1, 1)
        assert "not initialized" in str(exc_info.value)

    def test_get_verse_text_success_hebrew(self, parser):
        """Test getting Hebrew verse text."""
        parser.modules_dir.mkdir(exist_ok=True)

        # Mock WLC module
        mock_wlc = Mock()
        mock_wlc.get.return_value = '<w lemma="strong:H7225">בְּרֵאשִׁית</w> <w lemma="strong:H1254">בָּרָא</w>'

        with patch("sword_parser.SwordModules") as mock_modules_class:
            mock_modules = Mock()
            mock_modules.parse_modules.return_value = ["WLC"]
            mock_modules.get_bible_from_module.return_value = mock_wlc
            mock_modules_class.return_value = mock_modules

            parser.initialize()
            result = parser.get_verse_text("Genesis", 1, 1, testament="OT")

            assert result is not None
            assert result["language"] == "hebrew"
            assert "בְּרֵאשִׁית" in result["original_text"]
            assert "strongs_numbers" in result
            assert "H7225" in result["strongs_numbers"]

    def test_get_verse_text_success_greek(self, parser):
        """Test getting Greek verse text."""
        parser.modules_dir.mkdir(exist_ok=True)

        # Mock SBLGNT module
        mock_sblgnt = Mock()
        mock_sblgnt.get.return_value = '<w lemma="strong:G1722">Ἐν</w> <w lemma="strong:G746">ἀρχῇ</w>'

        with patch("sword_parser.SwordModules") as mock_modules_class:
            mock_modules = Mock()
            mock_modules.parse_modules.return_value = ["SBLGNT"]
            mock_modules.get_bible_from_module.return_value = mock_sblgnt
            mock_modules_class.return_value = mock_modules

            parser.initialize()
            parser.wlc = None  # Force NT
            result = parser.get_verse_text("John", 1, 1, testament="NT")

            assert result is not None
            assert result["language"] == "greek"
            assert "Ἐν" in result["original_text"]
            assert "strongs_numbers" in result
            assert "G1722" in result["strongs_numbers"]

    def test_get_verse_text_auto_detect_testament(self, parser):
        """Test automatic testament detection."""
        parser.modules_dir.mkdir(exist_ok=True)

        mock_wlc = Mock()
        mock_wlc.get.return_value = "Hebrew text"

        with patch("sword_parser.SwordModules") as mock_modules_class:
            mock_modules = Mock()
            mock_modules.parse_modules.return_value = ["WLC"]
            mock_modules.get_bible_from_module.return_value = mock_wlc
            mock_modules_class.return_value = mock_modules

            parser.initialize()

            # Don't specify testament - should auto-detect
            result = parser.get_verse_text("Exodus", 3, 14)

            assert result is not None
            assert result["language"] == "hebrew"

    def test_get_verse_text_not_found(self, parser, caplog):
        """Test getting verse that doesn't exist."""
        parser.modules_dir.mkdir(exist_ok=True)

        mock_wlc = Mock()
        mock_wlc.get.return_value = None  # Verse not found

        with patch("sword_parser.SwordModules") as mock_modules_class:
            mock_modules = Mock()
            mock_modules.parse_modules.return_value = ["WLC"]
            mock_modules.get_bible_from_module.return_value = mock_wlc
            mock_modules_class.return_value = mock_modules

            parser.initialize()
            result = parser.get_verse_text("Genesis", 1, 999)

            assert result is None
            assert "No text found" in caplog.text

    def test_get_verse_text_module_not_loaded(self, parser, caplog):
        """Test getting verse when required module not loaded."""
        parser.modules_dir.mkdir(exist_ok=True)

        with patch("sword_parser.SwordModules") as mock_modules_class:
            mock_modules = Mock()
            mock_modules.parse_modules.return_value = []  # No modules
            mock_modules_class.return_value = mock_modules

            parser.initialize()
            result = parser.get_verse_text("Genesis", 1, 1)

            assert result is None
            assert "WLC module not loaded" in caplog.text

    def test_get_chapter_verses(self, parser):
        """Test batch fetching of chapter verses."""
        parser.modules_dir.mkdir(exist_ok=True)

        # Mock WLC to return different verses
        def mock_get(*args, **kwargs):
            verse = kwargs.get('verses', [1])[0]
            if verse <= 3:
                return f"<w>Verse {verse} text</w>"
            return None  # End of chapter

        mock_wlc = Mock()
        mock_wlc.get = mock_get

        with patch("sword_parser.SwordModules") as mock_modules_class:
            mock_modules = Mock()
            mock_modules.parse_modules.return_value = ["WLC"]
            mock_modules.get_bible_from_module.return_value = mock_wlc
            mock_modules_class.return_value = mock_modules

            parser.initialize()
            results = parser.get_chapter_verses("Genesis", 1, verse_start=1, verse_end=10)

            assert len(results) == 3  # Only 3 verses available
            assert 1 in results
            assert 2 in results
            assert 3 in results
            assert results[1]["language"] == "hebrew"
            assert "Verse 1" in results[1]["original_text"]


class TestVerifyBookNormalization:
    """Tests for book normalization verification function."""

    def test_verify_all_66_books(self):
        """Test normalization of all 66 Bible books."""
        normalization = verify_book_normalization()

        # Should have all 66 books
        assert len(normalization) == 66

        # Check specific normalizations
        assert normalization["I Samuel"] == "1 Samuel"
        assert normalization["II Kings"] == "2 Kings"
        assert normalization["Song of Solomon"] == "Song of Songs"
        assert normalization["Revelation of John"] == "Revelation"

        # Check unchanged books
        assert normalization["Genesis"] == "Genesis"
        assert normalization["Matthew"] == "Matthew"
        assert normalization["Psalms"] == "Psalms"  # Already plural in list

    def test_all_normalized_books_recognized(self):
        """Test that all normalized book names are recognized."""
        from sword_parser import SwordParser

        parser = SwordParser()
        normalization = verify_book_normalization()

        # All normalized names should be valid
        for original, normalized in normalization.items():
            # Should not raise ValueError
            try:
                testament = parser.get_testament(normalized)
                assert testament in ["OT", "NT"]
            except ValueError:
                pytest.fail(f"Normalized book {normalized} (from {original}) not recognized")
