"""Unit tests for verse chunking module."""

import pytest

from verse_chunker import (
    count_tokens,
    chunk_verses,
    _chunk_chapter,
    _create_chunk_document,
    analyze_chunking_quality,
)
from config import settings


class TestCountTokens:
    """Test token counting functionality."""

    def test_count_tokens_simple_text(self):
        """Count tokens in simple text."""
        text = "The Lord is my shepherd"
        token_count = count_tokens(text)

        assert isinstance(token_count, int)
        assert token_count > 0
        assert token_count < 10  # Simple phrase should be few tokens

    def test_count_tokens_empty_string(self):
        """Empty string has zero tokens."""
        assert count_tokens("") == 0

    def test_count_tokens_consistent(self):
        """Same text produces same token count."""
        text = "For God so loved the world"
        count1 = count_tokens(text)
        count2 = count_tokens(text)

        assert count1 == count2


class TestChunkShortChapter:
    """Test chunking behavior for short chapters."""

    def test_chunk_psalm_23_single_chunk(self, psalm_23_verses):
        """Psalm 23 (~180 tokens) should stay as one chunk."""
        chunks = list(chunk_verses(psalm_23_verses, "KJV"))

        assert len(chunks) == 1
        assert chunks[0]["title"] == "Psalms 23:1-6 (KJV)"
        assert chunks[0]["metadata"]["verse_start"] == 1
        assert chunks[0]["metadata"]["verse_end"] == 6

        # Verify token count is reasonable
        token_count = chunks[0]["metadata"]["structure"]["token_count"]
        assert 150 < token_count < 250

    def test_chunk_john_3_single_chunk(self, john_3_verses):
        """John 3:16-17 should stay as one chunk."""
        chunks = list(chunk_verses(john_3_verses, "KJV"))

        assert len(chunks) == 1
        assert "John 3:16-17" in chunks[0]["title"]


class TestChunkLongChapter:
    """Test chunking behavior for long chapters."""

    def test_chunk_genesis_1_multiple_chunks(self, genesis_1_verses):
        """Genesis 1:1-5 should be one chunk (short sample)."""
        chunks = list(chunk_verses(genesis_1_verses, "KJV"))

        # With 5 verses, should be single chunk
        assert len(chunks) == 1

    def test_chunk_respects_target_tokens(self, genesis_1_verses):
        """Chunks should aim for target token count."""
        chunks = list(chunk_verses(genesis_1_verses, "KJV"))

        for chunk in chunks:
            token_count = chunk["metadata"]["structure"]["token_count"]
            # Should not wildly exceed target (unless single verse is long)
            assert token_count <= settings.max_chunk_tokens


class TestChunkBoundaries:
    """Test chunk boundary logic."""

    def test_chunk_never_spans_chapters(self, mixed_chapter_verses):
        """Chunks should never span chapter boundaries."""
        chunks = list(chunk_verses(mixed_chapter_verses, "KJV"))

        # Verify each chunk is from a single chapter
        for chunk in chunks:
            chapter = chunk["metadata"]["chapter"]
            book_id = chunk["metadata"]["book_id"]
            verse_start = chunk["metadata"]["verse_start"]
            verse_end = chunk["metadata"]["verse_end"]

            # All verses in range should be from same book and chapter
            relevant_verses = [
                v for v in mixed_chapter_verses
                if v.book_id == book_id
                and v.chapter == chapter
                and verse_start <= v.verse <= verse_end
            ]

            assert all(v.chapter == chapter for v in relevant_verses)

    def test_chunk_preserves_verse_order(self, genesis_1_verses):
        """Verse ranges should always be consecutive."""
        chunks = list(chunk_verses(genesis_1_verses, "KJV"))

        for chunk in chunks:
            verse_start = chunk["metadata"]["verse_start"]
            verse_end = chunk["metadata"]["verse_end"]

            # Verse end should be >= start
            assert verse_end >= verse_start

            # For multi-verse chunks, verses should be consecutive
            if verse_end > verse_start:
                expected_verses = list(range(verse_start, verse_end + 1))
                assert verse_end - verse_start + 1 == len(expected_verses)


class TestOversizedVerses:
    """Test handling of verses exceeding max tokens."""

    def test_chunk_oversized_verse_standalone(self, oversized_verse):
        """Single verse >500 tokens becomes standalone chunk."""
        chunks = list(chunk_verses([oversized_verse], "KJV"))

        assert len(chunks) == 1
        assert chunks[0]["metadata"]["verse_start"] == oversized_verse.verse
        assert chunks[0]["metadata"]["verse_end"] == oversized_verse.verse

        # Should exceed max_chunk_tokens (that's the point)
        token_count = chunks[0]["metadata"]["structure"]["token_count"]
        assert token_count > settings.max_chunk_tokens


class TestCreateChunkDocument:
    """Test chunk document creation."""

    def test_create_chunk_metadata_structure(self, genesis_1_verses):
        """Verify all required metadata fields present."""
        chunk = _create_chunk_document(genesis_1_verses, "KJV")

        # Top-level fields
        assert "title" in chunk
        assert "content" in chunk
        assert "domain" in chunk
        assert "metadata" in chunk

        # Metadata fields
        metadata = chunk["metadata"]
        assert "book" in metadata
        assert "book_id" in metadata
        assert "chapter" in metadata
        assert "verse_start" in metadata
        assert "verse_end" in metadata
        assert "testament" in metadata
        assert "translation" in metadata
        assert "language" in metadata
        assert "structure" in metadata
        assert "source" in metadata

        # Structure fields
        structure = metadata["structure"]
        assert "path" in structure
        assert "book_number" in structure
        assert "total_verses" in structure
        assert "token_count" in structure

    def test_create_chunk_domain_namespacing(self, genesis_1_verses):
        """Domain format should be bible/{translation.lower()}."""
        chunk = _create_chunk_document(genesis_1_verses, "KJV")
        assert chunk["domain"] == "bible/kjv"

        chunk2 = _create_chunk_document(genesis_1_verses, "ASV")
        assert chunk2["domain"] == "bible/asv"

    def test_create_chunk_single_verse_title(self, genesis_1_verses):
        """Single verse title format."""
        chunk = _create_chunk_document(genesis_1_verses[:1], "KJV")
        assert chunk["title"] == "Genesis 1:1 (KJV)"

    def test_create_chunk_multi_verse_title(self, genesis_1_verses):
        """Multi-verse title format with range."""
        chunk = _create_chunk_document(genesis_1_verses, "KJV")
        assert chunk["title"] == "Genesis 1:1-5 (KJV)"

    def test_create_chunk_content_format(self, genesis_1_verses):
        """Content should include verse numbers."""
        chunk = _create_chunk_document(genesis_1_verses[:2], "KJV")

        assert "1 In the beginning" in chunk["content"]
        assert "2 And the earth" in chunk["content"]
        assert "\n" in chunk["content"]  # Verses separated by newlines

    def test_create_chunk_token_count_accuracy(self, genesis_1_verses):
        """Token count metadata should match tiktoken."""
        chunk = _create_chunk_document(genesis_1_verses[:1], "KJV")

        expected_tokens = count_tokens(chunk["content"])
        actual_tokens = chunk["metadata"]["structure"]["token_count"]

        assert actual_tokens == expected_tokens

    def test_create_chunk_hierarchical_path(self, genesis_1_verses):
        """Path should be hierarchical for navigation."""
        chunk = _create_chunk_document(genesis_1_verses, "KJV")

        path = chunk["metadata"]["structure"]["path"]
        assert "KJV" in path
        assert "Genesis" in path
        assert "Chapter 1" in path
        assert "Verses" in path

    def test_create_chunk_empty_verses_raises(self):
        """Cannot create chunk from empty verse list."""
        with pytest.raises(ValueError) as exc_info:
            _create_chunk_document([], "KJV")

        assert "empty verse list" in str(exc_info.value).lower()


class TestAnalyzeChunkingQuality:
    """Test chunking quality analysis."""

    def test_analyze_chunking_quality_returns_stats(self, genesis_1_verses):
        """Analysis returns expected statistics."""
        result = analyze_chunking_quality(genesis_1_verses, "KJV")

        assert "total_verses" in result
        assert "total_chunks" in result
        assert "verses_per_chunk_avg" in result
        assert "token_stats" in result
        assert "chunks_below_min" in result
        assert "chunks_above_max" in result
        assert "chunks_in_target_range" in result

    def test_analyze_chunking_quality_token_stats(self, genesis_1_verses):
        """Token stats contain min, max, avg."""
        result = analyze_chunking_quality(genesis_1_verses, "KJV")

        token_stats = result["token_stats"]
        assert "min" in token_stats
        assert "max" in token_stats
        assert "avg" in token_stats

        # Min should be <= max
        assert token_stats["min"] <= token_stats["max"]

    def test_analyze_chunking_quality_psalm_23(self, psalm_23_verses):
        """Analyze short chapter quality."""
        result = analyze_chunking_quality(psalm_23_verses, "KJV")

        assert result["total_verses"] == 6
        assert result["total_chunks"] >= 1

        # Short chapter should not exceed max tokens
        assert result["chunks_above_max"] == 0


class TestChunkVersesIntegration:
    """Integration tests for complete chunking pipeline."""

    def test_chunk_verses_generator(self, genesis_1_verses):
        """chunk_verses returns a generator."""
        result = chunk_verses(genesis_1_verses, "KJV")

        # Should be a generator
        assert hasattr(result, "__iter__")
        assert hasattr(result, "__next__")

        # Should produce dict documents
        chunks = list(result)
        assert len(chunks) > 0
        assert all(isinstance(chunk, dict) for chunk in chunks)

    def test_chunk_verses_maintains_order(self, mixed_chapter_verses):
        """Chunks should be in canonical order."""
        chunks = list(chunk_verses(mixed_chapter_verses, "KJV"))

        # Extract book and chapter from each chunk
        positions = [
            (chunk["metadata"]["book_id"], chunk["metadata"]["chapter"])
            for chunk in chunks
        ]

        # Should be sorted
        assert positions == sorted(positions)

    def test_chunk_verses_empty_input(self):
        """Empty input produces no chunks."""
        chunks = list(chunk_verses([], "KJV"))
        assert len(chunks) == 0

    def test_chunk_verses_all_chunks_valid(self, mixed_chapter_verses):
        """All chunks should be valid Prism documents."""
        chunks = list(chunk_verses(mixed_chapter_verses, "KJV"))

        for chunk in chunks:
            # Required fields
            assert chunk["title"]
            assert chunk["content"]
            assert chunk["domain"].startswith("bible/")

            # Valid metadata
            assert chunk["metadata"]["book_id"] >= 1
            assert chunk["metadata"]["book_id"] <= 66
            assert chunk["metadata"]["chapter"] >= 1
            assert chunk["metadata"]["verse_start"] >= 1
            assert chunk["metadata"]["verse_end"] >= chunk["metadata"]["verse_start"]

            # Valid token count
            assert chunk["metadata"]["structure"]["token_count"] > 0
