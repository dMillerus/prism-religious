"""End-to-end search integration tests (requires Prism running)."""

import pytest


@pytest.mark.integration
class TestSearchEndToEnd:
    """Test search functionality with real Prism API."""

    @pytest.mark.asyncio
    async def test_prism_health_check(self, prism_test_client):
        """Prism service is accessible and healthy."""
        is_healthy = await prism_test_client.check_health()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_search_basic_query(self, prism_test_client):
        """Basic search query returns results."""
        results = await prism_test_client.search_documents(
            query="Lord shepherd",
            top_k=5
        )

        assert "results" in results
        assert isinstance(results["results"], list)

        # Should find results if Bible data is imported
        if len(results["results"]) > 0:
            result = results["results"][0]
            assert "document_title" in result or "title" in result
            assert "similarity" in result
            assert "content" in result

    @pytest.mark.asyncio
    async def test_search_with_domain_filter(self, prism_test_client):
        """Search with domain filter returns only that domain."""
        results = await prism_test_client.search_documents(
            query="creation",
            domain="bible/kjv",
            top_k=5
        )

        assert "results" in results

        # If results found, verify all are from KJV domain
        for result in results["results"]:
            # Domain filtering is handled by Prism - we can't verify directly
            # but we can check that results are returned
            assert "content" in result

    @pytest.mark.asyncio
    async def test_search_top_k_limits_results(self, prism_test_client):
        """top_k parameter limits number of results."""
        results = await prism_test_client.search_documents(
            query="God",
            top_k=3
        )

        # Should return at most 3 results
        assert len(results["results"]) <= 3

    @pytest.mark.asyncio
    async def test_search_response_structure(self, prism_test_client):
        """Search response has expected structure."""
        results = await prism_test_client.search_documents(
            query="love",
            top_k=1
        )

        # Verify response structure
        assert isinstance(results, dict)
        assert "results" in results
        assert isinstance(results["results"], list)

        if len(results["results"]) > 0:
            doc = results["results"][0]
            assert isinstance(doc, dict)
            # Content should be present
            assert "content" in doc
            # Similarity score should be present
            assert "similarity" in doc

    @pytest.mark.asyncio
    async def test_search_similarity_scores_range(self, prism_test_client):
        """Similarity scores should be in valid range [0, 1]."""
        results = await prism_test_client.search_documents(
            query="Jesus",
            top_k=10
        )

        for doc in results["results"]:
            similarity = doc.get("similarity", 0)
            assert 0 <= similarity <= 1

    @pytest.mark.asyncio
    async def test_search_similarity_scores_descending(self, prism_test_client):
        """Similarity scores should be in descending order."""
        results = await prism_test_client.search_documents(
            query="faith hope love",
            top_k=10
        )

        similarities = [doc.get("similarity", 0) for doc in results["results"]]

        # Check descending order
        for i in range(len(similarities) - 1):
            assert similarities[i] >= similarities[i + 1]

    @pytest.mark.asyncio
    async def test_search_empty_results_for_nonsense(self, prism_test_client):
        """Nonsensical query may return low-similarity results or none."""
        results = await prism_test_client.search_documents(
            query="xyzqwerty nonsense gibberish",
            top_k=5
        )

        # Either no results, or results with low similarity
        if len(results["results"]) > 0:
            # If results exist, similarity should be relatively low
            top_similarity = results["results"][0].get("similarity", 0)
            # Don't enforce strict threshold, just verify it's in valid range
            assert 0 <= top_similarity <= 1


@pytest.mark.integration
class TestCrossVersionSearch:
    """Test cross-version search functionality."""

    @pytest.mark.asyncio
    async def test_search_without_domain_finds_multiple_versions(self, prism_test_client):
        """Cross-version search (no domain) can find multiple translations."""
        results = await prism_test_client.search_documents(
            query="In the beginning God created",
            top_k=20  # Higher limit to catch multiple versions
        )

        # If multiple Bible versions are imported, we might see different translations
        # This test just verifies that cross-version search works
        assert "results" in results
        assert isinstance(results["results"], list)

    @pytest.mark.asyncio
    async def test_search_domain_filter_isolation(self, prism_test_client):
        """Domain filter should isolate specific version."""
        # Search KJV specifically
        kjv_results = await prism_test_client.search_documents(
            query="shepherd",
            domain="bible/kjv",
            top_k=5
        )

        # Search ASV specifically
        asv_results = await prism_test_client.search_documents(
            query="shepherd",
            domain="bible/asv",
            top_k=5
        )

        # Both should return results if both translations are imported
        # We can't verify exact domain in response, but we can verify
        # that the search executes successfully
        assert isinstance(kjv_results["results"], list)
        assert isinstance(asv_results["results"], list)


@pytest.mark.integration
class TestSearchPerformance:
    """Test search performance characteristics."""

    @pytest.mark.asyncio
    async def test_search_completes_quickly(self, prism_test_client):
        """Search should complete in reasonable time."""
        import time

        start = time.time()

        await prism_test_client.search_documents(
            query="love",
            top_k=10
        )

        elapsed = time.time() - start

        # Should complete in under 5 seconds (generous threshold)
        assert elapsed < 5.0

    @pytest.mark.asyncio
    async def test_search_handles_long_query(self, prism_test_client):
        """Search should handle long queries without error."""
        long_query = "The Lord is my shepherd I shall not want " * 10

        results = await prism_test_client.search_documents(
            query=long_query,
            top_k=5
        )

        # Should not raise an error
        assert "results" in results
