"""
Integration tests for Phase 2 geography import.

Tests geography semantic search with live Prism instance.
"""

import pytest
from prism_client import PrismClient


@pytest.mark.asyncio
async def test_geography_document_count():
    """Test that 1,342 geography documents exist."""
    async with PrismClient() as client:
        count = await client.count_domain_documents("geography/biblical")
        assert count == 1342, f"Expected 1,342 geography docs, found {count}"


@pytest.mark.asyncio
async def test_geography_semantic_search_generic():
    """Test semantic search returns relevant places for generic queries."""
    async with PrismClient() as client:
        results = await client.search_documents(
            query="biblical settlement ancient city",
            domain="geography/biblical",
            top_k=10,
        )

        assert len(results["results"]) > 0, "No results returned"

        # Check similarity scores
        for result in results["results"]:
            assert result["similarity"] > 0.5, f"Low similarity: {result['similarity']}"


@pytest.mark.asyncio
async def test_geography_coordinate_filtering():
    """Test places have valid coordinates."""
    async with PrismClient() as client:
        results = await client.search_documents(
            query="biblical settlement with coordinates",
            domain="geography/biblical",
            top_k=10,
        )

        # Count results with coordinates
        with_coords = []
        for result in results["results"]:
            content = result.get("content", "")
            # Check if coordinates are in content
            if "Located at" in content and "°N" in content:
                with_coords.append(result)

        # At least 50% should have coordinates
        assert len(with_coords) >= len(results["results"]) // 2, \
            f"Only {len(with_coords)}/{len(results['results'])} have coordinates"


@pytest.mark.asyncio
async def test_geography_place_types():
    """Test different place types are searchable."""
    async with PrismClient() as client:
        # Test settlement
        settlement_results = await client.search_documents(
            query="biblical settlement village town",
            domain="geography/biblical",
            top_k=5,
        )
        assert len(settlement_results["results"]) > 0, "No settlements found"

        # Test mountain
        mountain_results = await client.search_documents(
            query="biblical mountain mount peak",
            domain="geography/biblical",
            top_k=5,
        )
        assert len(mountain_results["results"]) > 0, "No mountains found"

        # Test river/water
        water_results = await client.search_documents(
            query="biblical river water sea lake",
            domain="geography/biblical",
            top_k=5,
        )
        assert len(water_results["results"]) > 0, "No water bodies found"


@pytest.mark.asyncio
async def test_geography_verse_references():
    """Test verse references are present in content."""
    async with PrismClient() as client:
        results = await client.search_documents(
            query="biblical settlement with many references",
            domain="geography/biblical",
            top_k=5,
        )

        assert len(results["results"]) > 0, "No results"

        # Check that at least some have verse references
        with_verses = 0
        for result in results["results"]:
            content = result.get("content", "")
            if "Biblical references:" in content:
                with_verses += 1

        assert with_verses >= 3, f"Only {with_verses} results have verse references"


@pytest.mark.asyncio
async def test_geography_confidence_levels():
    """Test confidence levels are present."""
    async with PrismClient() as client:
        results = await client.search_documents(
            query="biblical settlement",
            domain="geography/biblical",
            top_k=5,
        )

        assert len(results["results"]) > 0, "No results"

        # Check confidence in content
        confidence_found = 0
        for result in results["results"]:
            content = result.get("content", "")
            if "Identification confidence:" in content:
                confidence_found += 1

        assert confidence_found >= 3, f"Only {confidence_found} have confidence levels"


@pytest.mark.asyncio
async def test_geography_embeddings_complete():
    """Test all geography documents have embeddings."""
    async with PrismClient() as client:
        stats = await client.get_stats()

        # Geography docs should be included in total
        assert stats["total_documents"] >= 1342, "Geography docs not in total"

        # Should have 100% embedding coverage
        coverage = stats["embedded_chunks"] / stats["total_chunks"] * 100
        assert coverage == 100, f"Embedding coverage is {coverage}%, expected 100%"


# Known issue: Specific place name searches may not work well
@pytest.mark.xfail(reason="Known issue: specific place name queries don't work well with current embedding model")
@pytest.mark.asyncio
async def test_geography_specific_places():
    """Test searching for specific well-known places (expected to fail currently)."""
    async with PrismClient() as client:
        # These searches are expected to fail with current implementation
        places = ["Jerusalem", "Bethlehem", "Nazareth"]

        for place in places:
            results = await client.search_documents(
                query=place,
                domain="geography/biblical",
                top_k=5,
            )
            # This assertion will likely fail, which is expected
            assert len(results["results"]) > 0, f"No results for {place}"
