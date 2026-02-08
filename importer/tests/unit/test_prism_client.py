"""Unit tests for Prism client module (with mocked HTTP)."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch

from prism_client import PrismClient, import_documents_in_batches


class TestPrismClientInit:
    """Test PrismClient initialization."""

    def test_init_default_url(self):
        """Client uses default URL from settings."""
        client = PrismClient()
        assert client.base_url == "http://localhost:8100"

    def test_init_custom_url(self):
        """Client accepts custom base URL."""
        client = PrismClient(base_url="http://custom:9999")
        assert client.base_url == "http://custom:9999"

    def test_init_timeout_from_settings(self):
        """Client timeout comes from settings."""
        client = PrismClient()
        assert client.timeout.read == 300  # From config default


class TestPrismClientContextManager:
    """Test async context manager behavior."""

    @pytest.mark.asyncio
    async def test_context_manager_initializes_client(self):
        """Context manager creates httpx.AsyncClient."""
        async with PrismClient() as client:
            assert client.client is not None
            assert isinstance(client.client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self):
        """Context manager closes client on exit."""
        client_instance = PrismClient()

        async with client_instance as client:
            http_client = client.client

        # After context exit, should be closed
        assert http_client.is_closed


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_httpx_client):
        """Health check returns True on 200 response."""
        mock_httpx_client.get.return_value = httpx.Response(200, json={"status": "healthy"})

        client = PrismClient()
        client.client = mock_httpx_client

        is_healthy = await client.check_health()

        assert is_healthy is True
        mock_httpx_client.get.assert_called_once_with("/health")

    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_httpx_client):
        """Health check returns False on non-200 response."""
        mock_httpx_client.get.return_value = httpx.Response(503, json={"status": "unhealthy"})

        client = PrismClient()
        client.client = mock_httpx_client

        is_healthy = await client.check_health()

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_exception(self, mock_httpx_client):
        """Health check returns False on exception."""
        mock_httpx_client.get.side_effect = httpx.ConnectError("Connection failed")

        client = PrismClient()
        client.client = mock_httpx_client

        is_healthy = await client.check_health()

        assert is_healthy is False


class TestImportCorpusBatch:
    """Test corpus batch import."""

    @pytest.mark.asyncio
    async def test_import_batch_success(self, mock_httpx_client):
        """Successful batch import returns results."""
        mock_request = httpx.Request("POST", "http://test")
        mock_response = {
            "total": 5,
            "imported": 5,
            "failed": 0,
            "results": [
                {"title": "Doc 1", "document_id": "uuid-1", "success": True},
                {"title": "Doc 2", "document_id": "uuid-2", "success": True},
            ],
        }
        mock_httpx_client.post.return_value = httpx.Response(
            200, json=mock_response, request=mock_request
        )

        client = PrismClient()
        client.client = mock_httpx_client

        documents = [{"title": f"Doc {i}", "content": "text"} for i in range(5)]
        result = await client.import_corpus_batch(documents, embed=True)

        assert result["imported"] == 5
        assert result["failed"] == 0
        mock_httpx_client.post.assert_called_once()

        # Verify payload structure
        call_args = mock_httpx_client.post.call_args
        assert call_args[0][0] == "/api/v1/corpus/import"
        payload = call_args[1]["json"]
        assert payload["documents"] == documents
        assert payload["embed"] is True

    @pytest.mark.asyncio
    async def test_import_batch_validates_max_100(self, mock_httpx_client):
        """Batch size >100 raises ValueError."""
        client = PrismClient()
        client.client = mock_httpx_client

        documents = [{"title": f"Doc {i}"} for i in range(101)]

        with pytest.raises(ValueError) as exc_info:
            await client.import_corpus_batch(documents)

        assert "exceeds maximum of 100" in str(exc_info.value)
        mock_httpx_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_import_batch_embed_false(self, mock_httpx_client):
        """Can disable embedding during import."""
        mock_request = httpx.Request("POST", "http://test")
        mock_httpx_client.post.return_value = httpx.Response(
            200, json={"imported": 1}, request=mock_request
        )

        client = PrismClient()
        client.client = mock_httpx_client

        documents = [{"title": "Doc 1", "content": "text"}]
        await client.import_corpus_batch(documents, embed=False)

        # Verify embed=False in payload
        call_args = mock_httpx_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["embed"] is False


class TestSearchDocuments:
    """Test document search functionality."""

    @pytest.mark.asyncio
    async def test_search_documents_basic(self, mock_httpx_client):
        """Basic search returns results."""
        mock_request = httpx.Request("POST", "http://test")
        mock_response = {
            "results": [
                {
                    "document_title": "Genesis 1:1",
                    "content": "In the beginning...",
                    "similarity": 0.95,
                }
            ],
            "total": 1,
        }
        mock_httpx_client.post.return_value = httpx.Response(
            200, json=mock_response, request=mock_request
        )

        client = PrismClient()
        client.client = mock_httpx_client

        results = await client.search_documents(query="creation", top_k=5)

        assert "results" in results
        mock_httpx_client.post.assert_called_once()

        # Verify payload
        call_args = mock_httpx_client.post.call_args
        assert call_args[0][0] == "/api/v1/search"
        payload = call_args[1]["json"]
        assert payload["query"] == "creation"
        assert payload["top_k"] == 5
        assert "domain" not in payload  # No domain filter

    @pytest.mark.asyncio
    async def test_search_documents_with_domain(self, mock_httpx_client):
        """Search with domain filter."""
        mock_request = httpx.Request("POST", "http://test")
        mock_httpx_client.post.return_value = httpx.Response(
            200, json={"results": []}, request=mock_request
        )

        client = PrismClient()
        client.client = mock_httpx_client

        await client.search_documents(
            query="shepherd",
            domain="bible/kjv",
            top_k=10
        )

        # Verify domain in payload
        call_args = mock_httpx_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["domain"] == "bible/kjv"
        assert payload["top_k"] == 10

    @pytest.mark.asyncio
    async def test_search_documents_parses_results(self, mock_httpx_client):
        """Search results parsed correctly."""
        mock_request = httpx.Request("POST", "http://test")
        mock_response = {
            "results": [
                {
                    "document_title": "Psalms 23:1",
                    "content": "The LORD is my shepherd",
                    "similarity": 0.92,
                },
                {
                    "document_title": "Psalms 23:2",
                    "content": "He maketh me to lie down",
                    "similarity": 0.88,
                },
            ],
        }
        mock_httpx_client.post.return_value = httpx.Response(
            200, json=mock_response, request=mock_request
        )

        client = PrismClient()
        client.client = mock_httpx_client

        results = await client.search_documents(query="shepherd")

        assert len(results["results"]) == 2
        assert results["results"][0]["similarity"] == 0.92


class TestImportDocumentsInBatches:
    """Test batch import helper function."""

    @pytest.mark.asyncio
    async def test_import_in_batches_validates_batch_size(self):
        """Batch size >100 raises ValueError."""
        documents = [{"title": f"Doc {i}"} for i in range(10)]

        with pytest.raises(ValueError) as exc_info:
            await import_documents_in_batches(documents, batch_size=101)

        assert "cannot exceed 100" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_import_in_batches_checks_health(self, mock_httpx_client):
        """Function checks Prism health before importing."""
        mock_httpx_client.get.return_value = httpx.Response(503, json={"status": "unhealthy"})

        documents = [{"title": "Doc 1"}]

        with patch.object(PrismClient, "__aenter__", return_value=PrismClient()) as mock_enter:
            mock_client = mock_enter.return_value
            mock_client.client = mock_httpx_client

            with pytest.raises(RuntimeError) as exc_info:
                await import_documents_in_batches(documents)

            assert "not accessible" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_import_in_batches_aggregates_results(self, mock_httpx_client):
        """Aggregate success/error counts across batches."""
        mock_request = httpx.Request("POST", "http://test")

        # Mock health check
        mock_httpx_client.get.return_value = httpx.Response(
            200, json={"status": "healthy"}, request=mock_request
        )

        # Mock batch imports
        mock_httpx_client.post.return_value = httpx.Response(
            200,
            json={
                "total": 5,
                "imported": 4,
                "failed": 1,
                "results": [
                    {"title": "Doc 1", "success": True},
                    {"title": "Doc 2", "success": False, "error": "Invalid format"},
                ],
            },
            request=mock_request,
        )

        documents = [{"title": f"Doc {i}"} for i in range(10)]

        with patch.object(PrismClient, "__aenter__") as mock_enter, \
             patch.object(PrismClient, "__aexit__"):

            mock_client_instance = PrismClient()
            mock_client_instance.client = mock_httpx_client
            mock_enter.return_value = mock_client_instance

            result = await import_documents_in_batches(documents, batch_size=5)

            # 2 batches of 5 documents each
            assert result["total_documents"] == 10
            assert result["total_batches"] == 2
            # Each batch returns 4 success, 1 error
            assert result["success_count"] == 8
            assert result["error_count"] == 2

    @pytest.mark.asyncio
    async def test_import_in_batches_progress_callback(self, mock_httpx_client):
        """Progress callback called for each batch."""
        mock_request = httpx.Request("POST", "http://test")
        mock_httpx_client.get.return_value = httpx.Response(
            200, json={"status": "healthy"}, request=mock_request
        )
        mock_httpx_client.post.return_value = httpx.Response(
            200,
            json={"total": 2, "imported": 2, "failed": 0, "results": []},
            request=mock_request,
        )

        documents = [{"title": f"Doc {i}"} for i in range(4)]
        progress_calls = []

        def progress_callback(batch_num, total_batches, result):
            progress_calls.append((batch_num, total_batches))

        with patch.object(PrismClient, "__aenter__") as mock_enter, \
             patch.object(PrismClient, "__aexit__"):

            mock_client_instance = PrismClient()
            mock_client_instance.client = mock_httpx_client
            mock_enter.return_value = mock_client_instance

            await import_documents_in_batches(
                documents,
                batch_size=2,
                progress_callback=progress_callback
            )

            # Should be called twice (2 batches)
            assert len(progress_calls) == 2
            assert progress_calls[0] == (1, 2)
            assert progress_calls[1] == (2, 2)
