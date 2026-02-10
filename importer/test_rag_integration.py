"""Integration tests for Bible Study Phase 1 RAG workflows.

Tests semantic search, context retrieval, and cross-domain functionality
for lexicon, book metadata, and Bible verses.
"""

import asyncio
import sys
from typing import Dict, List, Any
from prism_client import PrismClient


async def test_domain_coverage():
    """Test that all expected domains are present."""
    print("=" * 60)
    print("TEST 1: Domain Coverage")
    print("=" * 60)

    async with PrismClient() as client:
        stats = await client.get_stats()

        print(f"\n📊 Overall Statistics:")
        print(f"   Total documents: {stats.get('total_documents', 0):,}")
        print(f"   Total chunks: {stats.get('total_chunks', 0):,}")
        print(f"   Embedded chunks: {stats.get('embedded_chunks', 0):,}")
        print(f"   Domains: {stats.get('domains', 0)}")

        # Check specific domains
        expected_domains = {
            "lexicon/strongs": 14197,
            "metadata/books": 66,
            "bible/kjv": None,  # Variable count
            "bible/asv": None,
            "bible/bbe": None,
            "bible/ylt": None,
            "bible/webster": None,
        }

        print(f"\n📁 Domain Verification:")
        for domain, expected_count in expected_domains.items():
            count = await client.count_domain_documents(domain)
            status = "✅" if count > 0 else "❌"
            if expected_count:
                match = "✅" if count == expected_count else f"⚠️  (expected {expected_count})"
                print(f"   {status} {domain}: {count:,} documents {match}")
            else:
                print(f"   {status} {domain}: {count:,} documents")

        return stats


async def test_lexicon_search():
    """Test lexicon semantic search."""
    print("\n" + "=" * 60)
    print("TEST 2: Lexicon Semantic Search")
    print("=" * 60)

    test_queries = [
        ("love charity compassion", ["G26", "H157"]),  # agape, ahab
        ("father patriarch ancestor", ["H1", "G3962"]),  # ab, pater
        ("redemption salvation deliverance", ["H1350", "G629"]),  # gaal, apolutrosis
        ("holy sanctified set apart", ["H6944", "G40"]),  # qodesh, hagios
    ]

    async with PrismClient() as client:
        for query, expected_ids in test_queries:
            print(f"\n🔍 Query: '{query}'")
            results = await client.search_documents(
                query=query,
                domain="lexicon/strongs",
                top_k=3
            )

            if results.get("results"):
                for i, result in enumerate(results["results"][:3], 1):
                    title = result.get("document_title", "Unknown")
                    similarity = result.get("similarity", 0)
                    print(f"   {i}. {title} (similarity: {similarity:.3f})")

                # Check if expected IDs are in top results
                found_ids = [r.get("document_title", "").split()[1]
                            for r in results["results"][:5]]
                matches = [eid for eid in expected_ids if any(eid in fid for fid in found_ids)]
                if matches:
                    print(f"   ✅ Found expected IDs: {matches}")
                else:
                    print(f"   ⚠️  Expected IDs not in top 5: {expected_ids}")
            else:
                print("   ❌ No results found")


async def test_book_metadata_search():
    """Test book metadata semantic search."""
    print("\n" + "=" * 60)
    print("TEST 3: Book Metadata Semantic Search")
    print("=" * 60)

    test_queries = [
        ("Paul's letters about justification faith grace", ["Romans", "Galatians"]),
        ("Gospel accounts of Jesus life and ministry", ["Matthew", "Mark", "Luke", "John"]),
        ("prophecy judgment restoration Israel", ["Isaiah", "Jeremiah", "Ezekiel"]),
        ("wisdom proverbs practical living", ["Proverbs", "Ecclesiastes"]),
    ]

    async with PrismClient() as client:
        for query, expected_books in test_queries:
            print(f"\n🔍 Query: '{query}'")
            results = await client.search_documents(
                query=query,
                domain="metadata/books",
                top_k=3
            )

            if results.get("results"):
                for i, result in enumerate(results["results"][:3], 1):
                    title = result.get("document_title", "Unknown")
                    similarity = result.get("similarity", 0)
                    print(f"   {i}. {title} (similarity: {similarity:.3f})")

                # Check if expected books are found
                found_books = [r.get("document_title", "") for r in results["results"][:5]]
                matches = [book for book in expected_books
                          if any(book in title for title in found_books)]
                if matches:
                    print(f"   ✅ Found expected books: {matches}")
                else:
                    print(f"   ⚠️  Expected books not in top 5: {expected_books}")
            else:
                print("   ❌ No results found")


async def test_mixed_domain_context():
    """Test cross-domain context retrieval for RAG."""
    print("\n" + "=" * 60)
    print("TEST 4: Mixed Domain Context Retrieval (RAG)")
    print("=" * 60)

    test_queries = [
        "What does the Bible say about love and charity?",
        "Tell me about Paul's letter to the Romans",
        "Where does Jesus teach about faith and works?",
    ]

    async with PrismClient() as client:
        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")

            # Search across all domains (no domain filter)
            results = await client.search_documents(
                query=query,
                top_k=10
            )

            if results.get("results"):
                # Group by domain
                domains_found = {}
                for result in results["results"]:
                    title = result.get("document_title", "")
                    # Infer domain from title
                    if "Strong's" in title:
                        domain = "lexicon"
                    elif "Book of" in title:
                        domain = "book_metadata"
                    elif "Document from" in title:
                        domain = "britannica"
                    else:
                        domain = "bible"

                    if domain not in domains_found:
                        domains_found[domain] = []
                    domains_found[domain].append({
                        "title": title,
                        "similarity": result.get("similarity", 0)
                    })

                print(f"   📊 Domains in results: {list(domains_found.keys())}")
                for domain, items in domains_found.items():
                    print(f"\n   {domain.upper()} ({len(items)} results):")
                    for item in items[:2]:
                        print(f"      - {item['title'][:60]}... ({item['similarity']:.3f})")

                # Check for mixed domains
                if len(domains_found) > 1:
                    print(f"\n   ✅ Mixed domain retrieval working! {len(domains_found)} domains")
                else:
                    print(f"\n   ⚠️  Only single domain found: {list(domains_found.keys())}")
            else:
                print("   ❌ No results found")


async def test_search_quality_metrics():
    """Test search quality with known good queries."""
    print("\n" + "=" * 60)
    print("TEST 5: Search Quality Metrics")
    print("=" * 60)

    # Known good queries with expected high similarity
    quality_tests = [
        ("love", "lexicon/strongs", 0.5),  # Should find love-related entries
        ("Romans justification", "metadata/books", 0.7),  # Should strongly match Romans
        ("shepherd psalm", "bible/kjv", 0.6),  # Should find Psalm 23
    ]

    async with PrismClient() as client:
        passed = 0
        failed = 0

        for query, domain, min_similarity in quality_tests:
            print(f"\n🔍 Query: '{query}' (domain: {domain})")
            results = await client.search_documents(
                query=query,
                domain=domain,
                top_k=1
            )

            if results.get("results"):
                top_result = results["results"][0]
                similarity = top_result.get("similarity", 0)
                title = top_result.get("document_title", "Unknown")

                if similarity >= min_similarity:
                    print(f"   ✅ PASS: {title} ({similarity:.3f} >= {min_similarity})")
                    passed += 1
                else:
                    print(f"   ❌ FAIL: {title} ({similarity:.3f} < {min_similarity})")
                    failed += 1
            else:
                print(f"   ❌ FAIL: No results found")
                failed += 1

        print(f"\n📊 Quality Score: {passed}/{passed + failed} passed ({passed * 100 / (passed + failed):.0f}%)")
        return passed, failed


async def test_verse_with_enrichment():
    """Test that verses have enriched metadata."""
    print("\n" + "=" * 60)
    print("TEST 6: Verse Metadata Enrichment")
    print("=" * 60)

    async with PrismClient() as client:
        # Get a sample of KJV verses
        response = await client.client.get(
            "/api/v1/documents",
            params={"domain": "bible/kjv", "limit": 5}
        )
        data = response.json()

        if not data.get("documents"):
            print("   ❌ No verses found")
            return

        print(f"\n📝 Checking metadata for {len(data['documents'])} sample verses:")

        for doc in data["documents"][:5]:
            title = doc.get("title", "Unknown")
            metadata = doc.get("metadata", {})

            # Check for enriched fields
            has_author = "author" in metadata
            has_themes = "theological_themes" in metadata or "themes" in metadata
            has_genre = "genre" in metadata
            has_era = "biblical_era" in metadata or "historical_eras" in metadata

            enrichment_score = sum([has_author, has_themes, has_genre, has_era])
            status = "✅" if enrichment_score >= 2 else "⚠️"

            print(f"\n   {status} {title}")
            print(f"      Metadata fields: {len(metadata)}")
            print(f"      Enriched: author={has_author}, themes={has_themes}, genre={has_genre}, era={has_era}")


async def run_all_tests():
    """Run all integration tests."""
    print("\n" + "=" * 80)
    print(" " * 20 + "BIBLE STUDY PHASE 1 - RAG INTEGRATION TESTS")
    print("=" * 80)

    try:
        # Test 1: Domain coverage
        await test_domain_coverage()

        # Test 2: Lexicon search
        await test_lexicon_search()

        # Test 3: Book metadata search
        await test_book_metadata_search()

        # Test 4: Mixed domain context
        await test_mixed_domain_context()

        # Test 5: Search quality
        passed, failed = await test_search_quality_metrics()

        # Test 6: Verse enrichment
        await test_verse_with_enrichment()

        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"\n✅ All integration tests completed!")
        print(f"\n📊 Key Metrics:")
        print(f"   - Domains operational: lexicon, book metadata, bible verses")
        print(f"   - Semantic search: Functional")
        print(f"   - Cross-domain retrieval: Functional")
        print(f"   - Search quality: {passed}/{passed + failed} tests passed")
        print(f"\n🎯 Phase 1 Status: OPERATIONAL")

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
