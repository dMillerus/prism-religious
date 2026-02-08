"""Async client for Prism corpus API."""

import asyncio
import httpx
from typing import Any, Optional, Callable

from config import settings


class PrismClient:
    """Async HTTP client for Prism API operations."""

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize Prism client.

        Args:
            base_url: Override default Prism URL (default: from settings)
        """
        self.base_url = base_url or settings.prism_base_url
        self.client: httpx.AsyncClient | None = None
        self.timeout = httpx.Timeout(settings.prism_timeout)

    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()

    async def check_health(self) -> bool:
        """
        Check if Prism service is accessible.

        Returns:
            True if Prism is healthy, False otherwise
        """
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception:
            return False

    async def get_stats(self) -> dict:
        """
        Get Prism database statistics.

        Returns:
            Dict with document counts, namespace info, etc.

        Raises:
            httpx.HTTPStatusError: If API returns error status
        """
        response = await self.client.get("/api/v1/admin/stats")
        response.raise_for_status()
        return response.json()

    async def import_corpus_batch(
        self,
        documents: list,
        embed: bool = True,
    ) -> dict:
        """
        Import a batch of documents via corpus endpoint.

        Prism corpus API handles:
        - Automatic immutability (corpus documents are read-only)
        - Duplicate detection (by title + domain)
        - Chunking and embedding
        - Error handling per document

        Args:
            documents: List of document dicts (max 100 per call)
            embed: Whether to generate embeddings (default: True)

        Returns:
            Response dict with Prism's structure:
            {
                "total": int,
                "imported": int,
                "failed": int,
                "results": [{"title": str, "document_id": UUID, "success": bool, "error": str}, ...]
            }

        Raises:
            ValueError: If batch exceeds 100 documents
            httpx.HTTPStatusError: If API returns error status
        """
        if len(documents) > 100:
            raise ValueError(
                f"Batch size {len(documents)} exceeds maximum of 100. "
                "Split into smaller batches."
            )

        payload = {
            "documents": documents,
            "embed": embed,
        }

        response = await self.client.post(
            "/api/v1/corpus/import",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def search_documents(
        self,
        query: str,
        domain: Optional[str] = None,
        top_k: int = 5,
    ) -> dict:
        """
        Search documents by semantic similarity.

        Args:
            query: Search query text
            domain: Optional domain filter (e.g., "bible/kjv")
            top_k: Number of results to return

        Returns:
            Search results with documents and similarity scores

        Raises:
            httpx.HTTPStatusError: If API returns error status
        """
        payload = {
            "query": query,
            "top_k": top_k,
        }
        if domain:
            payload["domain"] = domain

        response = await self.client.post(
            "/api/v1/search",
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def count_domain_documents(self, domain: str) -> int:
        """
        Count documents in a specific domain by searching.

        Args:
            domain: Domain to count (e.g., "bible/kjv")

        Returns:
            Number of documents in domain

        Raises:
            httpx.HTTPStatusError: If API returns error status
        """
        # Search with a very generic query to get documents in domain
        # This is a workaround since stats doesn't break down by domain
        try:
            response = await self.client.get(
                "/api/v1/documents",
                params={"domain": domain, "limit": 1},
            )
            response.raise_for_status()
            data = response.json()
            # If Prism returns a total count, use that
            # Otherwise we'll need to implement actual counting
            return data.get("total", len(data.get("documents", [])))
        except Exception:
            return 0


async def import_documents_in_batches(
    documents: list,
    batch_size: int = 100,
    embed: bool = True,
    progress_callback: Optional[Callable] = None,
) -> dict:
    """
    Import documents in batches with progress tracking.

    Args:
        documents: All documents to import
        batch_size: Documents per batch (max 100)
        embed: Whether to generate embeddings
        progress_callback: Optional function(batch_num, total_batches, result)

    Returns:
        Aggregated results:
        {
            "total_documents": int,
            "total_batches": int,
            "success_count": int,
            "error_count": int,
            "errors": [{"document": str, "error": str}, ...]
        }
    """
    if batch_size > 100:
        raise ValueError("Batch size cannot exceed 100")

    total_docs = len(documents)
    total_batches = (total_docs + batch_size - 1) // batch_size

    aggregated_results = {
        "total_documents": total_docs,
        "total_batches": total_batches,
        "success_count": 0,
        "error_count": 0,
        "errors": [],
    }

    async with PrismClient() as client:
        # Check health first
        if not await client.check_health():
            raise RuntimeError(
                f"Prism service not accessible at {client.base_url}. "
                "Ensure Prism is running: docker compose up -d prism"
            )

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_docs)
            batch = documents[start_idx:end_idx]

            try:
                result = await client.import_corpus_batch(batch, embed=embed)

                # Prism returns: {"total": int, "imported": int, "failed": int, "results": [...]}
                aggregated_results["success_count"] += result.get("imported", 0)
                aggregated_results["error_count"] += result.get("failed", 0)

                # Extract errors from results
                for doc_result in result.get("results", []):
                    if not doc_result.get("success", True) and doc_result.get("error"):
                        aggregated_results["errors"].append({
                            "document": doc_result.get("title", "Unknown"),
                            "error": doc_result.get("error"),
                        })

                if progress_callback:
                    progress_callback(batch_num + 1, total_batches, result)

            except Exception as e:
                # Handle batch-level errors
                error_msg = f"Batch {batch_num + 1} failed: {str(e)}"
                aggregated_results["error_count"] += len(batch)
                aggregated_results["errors"].append(
                    {"batch": batch_num + 1, "error": error_msg}
                )

                if progress_callback:
                    progress_callback(batch_num + 1, total_batches, {"error": error_msg})

            # Small delay between batches to avoid overwhelming Prism
            await asyncio.sleep(0.5)

    return aggregated_results
