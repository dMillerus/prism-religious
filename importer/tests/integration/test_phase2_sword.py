"""
Integration tests for Phase 2 SWORD parser.

Tests Hebrew/Greek text extraction for all Bible books.
"""

import pytest
from sword_parser import SwordParser, verify_book_normalization


def test_sword_parser_initialization():
    """Test SWORD modules initialize correctly."""
    parser = SwordParser()
    parser.initialize()

    assert parser.wlc is not None, "WLC module not loaded"
    assert parser.sblgnt is not None, "SBLGNT module not loaded"


def test_book_normalization_complete():
    """Test all 66 books can be normalized."""
    normalization = verify_book_normalization()

    # Should have all 66 books
    assert len(normalization) == 66, f"Expected 66 books, got {len(normalization)}"

    # Test specific normalizations
    assert normalization["I Samuel"] == "1 Samuel"
    assert normalization["II Kings"] == "2 Kings"
    assert normalization["Song of Solomon"] == "Song of Songs"

    # All values should be non-empty
    for original, normalized in normalization.items():
        assert normalized, f"Empty normalization for {original}"
        assert isinstance(normalized, str), f"Non-string normalization: {normalized}"


def test_sword_parser_all_ot_books():
    """Test Hebrew extraction for sample OT books across all sections."""
    parser = SwordParser()
    parser.initialize()

    # Sample books from different OT sections
    ot_books = [
        ("Genesis", 1, 1),  # Torah
        ("Exodus", 20, 1),  # Torah
        ("Joshua", 1, 1),  # Historical
        ("Judges", 1, 1),  # Historical
        ("Psalms", 23, 1),  # Wisdom
        ("Proverbs", 1, 1),  # Wisdom
        ("Isaiah", 53, 5),  # Major Prophets
        ("Jeremiah", 1, 1),  # Major Prophets
        ("Hosea", 1, 1),  # Minor Prophets
        ("Malachi", 3, 1),  # Minor Prophets (last OT book)
    ]

    for book, chapter, verse in ot_books:
        result = parser.get_verse_text(book, chapter, verse)
        assert result is not None, f"Failed to get {book} {chapter}:{verse}"
        assert result["language"] == "hebrew", f"{book} should be Hebrew"
        assert len(result["original_text"]) > 0, f"{book} has no text"
        # Verify Hebrew characters
        assert any('\u0590' <= c <= '\u05FF' for c in result["original_text"]), \
            f"No Hebrew characters in {book}"


def test_sword_parser_all_nt_books():
    """Test Greek extraction for sample NT books across all sections."""
    parser = SwordParser()
    parser.initialize()

    # Sample books from different NT sections
    nt_books = [
        ("Matthew", 5, 1),  # Gospels
        ("Mark", 1, 1),  # Gospels
        ("Luke", 2, 1),  # Gospels
        ("John", 3, 16),  # Gospels
        ("Acts", 1, 1),  # History
        ("Romans", 8, 28),  # Paul's Epistles
        ("Ephesians", 2, 8),  # Paul's Epistles
        ("Hebrews", 11, 1),  # General Epistles
        ("James", 1, 1),  # General Epistles
    ]

    for book, chapter, verse in nt_books:
        result = parser.get_verse_text(book, chapter, verse)
        assert result is not None, f"Failed to get {book} {chapter}:{verse}"
        assert result["language"] == "greek", f"{book} should be Greek"
        assert len(result["original_text"]) > 0, f"{book} has no text"
        # Verify Greek characters
        assert any('\u0370' <= c <= '\u03FF' for c in result["original_text"]), \
            f"No Greek characters in {book}"


def test_sword_parser_markup_cleaning():
    """Test OSIS markup is properly removed."""
    parser = SwordParser()

    test_cases = [
        # SWORD/OSIS markup
        ('<w lemma="strong:H430">אֱלֹהִים</w>', 'אֱלֹהִים'),
        ('<w lemma="strong:G2316">θεός</w>', 'θεός'),
        # Notes and other tags
        ('<note>footnote</note>text', 'text'),
        ('<div>content</div>', 'content'),
        # Plain text (should pass through)
        ('plain text', 'plain text'),
        # Mixed content
        ('before<tag>inside</tag>after', 'beforeinsideafter'),
    ]

    for dirty, expected in test_cases:
        clean = parser._clean_sword_markup(dirty)
        # Tags should be removed
        assert '<' not in clean, f"Tags remain: {clean}"
        assert '>' not in clean, f"Tags remain: {clean}"
        # Expected content should be present
        assert expected in clean or clean == expected, \
            f"Expected '{expected}' in '{clean}'"


def test_sword_parser_verse_not_found():
    """Test handling of invalid verse references."""
    parser = SwordParser()
    parser.initialize()

    # Non-existent verse
    result = parser.get_verse_text("Genesis", 999, 999)
    assert result is None, "Should return None for invalid verse"

    # Invalid book
    result = parser.get_verse_text("InvalidBook", 1, 1)
    assert result is None, "Should return None for invalid book"


def test_sword_parser_edge_cases():
    """Test edge cases like first/last verses."""
    parser = SwordParser()
    parser.initialize()

    # First verse of Bible (Hebrew)
    result = parser.get_verse_text("Genesis", 1, 1)
    assert result is not None
    assert result["language"] == "hebrew"

    # Sample OT verse (Hebrew)
    result = parser.get_verse_text("Malachi", 3, 1)
    assert result is not None
    assert result["language"] == "hebrew"

    # First verse of NT (Greek)
    result = parser.get_verse_text("Matthew", 1, 1)
    assert result is not None
    assert result["language"] == "greek"

    # Sample NT verse (Greek)
    result = parser.get_verse_text("John", 1, 1)
    assert result is not None
    assert result["language"] == "greek"
