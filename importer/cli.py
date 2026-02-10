"""Command-line interface for Bible importer."""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List, Dict

import click

from config import settings
from csv_parser import parse_bible_csv, validate_verse_integrity
from verse_chunker import chunk_verses, analyze_chunking_quality
from prism_client import import_documents_in_batches, PrismClient


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Bible text ingestion system for aiml-stack.

    Imports Bible translations into Prism (PSDL) with optimized chunking
    for LLM consumption via MCP.
    """
    pass


@cli.command()
@click.option(
    "--version",
    "-v",
    required=True,
    help="Bible translation (e.g., kjv, niv)",
)
@click.option(
    "--verses-csv",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to verses CSV file",
)
@click.option(
    "--books",
    help="Comma-separated list of books to import (default: all)",
)
@click.option(
    "--batch-size",
    type=int,
    default=100,
    help="Documents per API batch (max 100)",
)
@click.option(
    "--no-embed",
    is_flag=True,
    help="Skip embedding generation (faster, but not searchable)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Parse and chunk only, don't call Prism API",
)
@click.option(
    "--genre-aware",
    is_flag=True,
    help="Use genre-specific chunk sizes (poetry=225, epistle=425, etc.)",
)
@click.option(
    "--overlap",
    is_flag=True,
    help="Add 50-token overlap between consecutive chunks for better context",
)
@click.option(
    "--full-optimization",
    is_flag=True,
    help="Enable all optimizations (genre-aware + overlap + cross-refs + parallels)",
)
def import_bible(
    version: str,
    verses_csv: Path,
    books: Optional[str],
    batch_size: int,
    no_embed: bool,
    dry_run: bool,
    genre_aware: bool,
    overlap: bool,
    full_optimization: bool,
):
    """Import Bible translation into Prism."""
    translation = version.upper()

    # Full optimization enables all features
    if full_optimization:
        genre_aware = True
        overlap = True

    # Display active features
    features = []
    if genre_aware:
        features.append("genre-aware chunking")
    if overlap:
        features.append("50-token overlap")
    if full_optimization:
        features.append("cross-references + parallel passages")

    click.echo(f"🔍 Parsing {translation} from {verses_csv}...")
    if features:
        click.echo(f"✨ Optimizations: {', '.join(features)}")

    # Parse book filter if provided
    filter_books = None
    if books:
        filter_books = [b.strip() for b in books.split(",")]
        click.echo(f"   Filtering to books: {', '.join(filter_books)}")

    # Parse CSV
    try:
        verses = parse_bible_csv(verses_csv, translation, filter_books)
    except Exception as e:
        click.echo(f"❌ Error parsing CSV: {e}", err=True)
        sys.exit(1)

    click.echo(f"✅ Parsed {len(verses):,} verses")

    # Validate verse integrity
    validation = validate_verse_integrity(verses)
    click.echo(f"   Books: {validation['books_found']}")
    click.echo(f"   Chapters: {validation['chapters_found']}")

    if validation["issues"]:
        click.echo(f"⚠️  Found {len(validation['issues'])} issues:")
        for issue in validation["issues"][:5]:  # Show first 5
            click.echo(f"   - {issue}")

    # Chunk verses
    click.echo(f"\n🧩 Chunking verses for LLM consumption...")
    documents = list(chunk_verses(
        verses,
        translation,
        enable_genre_aware=genre_aware,
        enable_overlap=overlap,
        overlap_tokens=settings.overlap_tokens,
    ))
    click.echo(f"✅ Created {len(documents):,} chunks")

    # Show genre distribution if genre-aware
    if genre_aware:
        _show_genre_distribution(documents)

    # Analyze chunking quality
    quality = analyze_chunking_quality(verses, translation)
    click.echo(f"\n📊 Chunking Quality:")
    click.echo(f"   Verses per chunk (avg): {quality['verses_per_chunk_avg']:.1f}")
    click.echo(f"   Token distribution:")
    click.echo(f"      Min: {quality['token_stats']['min']}")
    click.echo(f"      Avg: {quality['token_stats']['avg']:.0f}")
    click.echo(f"      Max: {quality['token_stats']['max']}")
    click.echo(
        f"   Chunks in target range "
        f"({settings.target_chunk_tokens * 0.8:.0f}-"
        f"{settings.target_chunk_tokens * 1.2:.0f} tokens): "
        f"{quality['chunks_in_target_range']} "
        f"({quality['chunks_in_target_range'] / len(documents) * 100:.1f}%)"
    )

    if quality["chunks_below_min"] > 0:
        click.echo(
            f"   ⚠️  {quality['chunks_below_min']} chunks below minimum "
            f"({settings.min_chunk_tokens} tokens)"
        )
    if quality["chunks_above_max"] > 0:
        click.echo(
            f"   ⚠️  {quality['chunks_above_max']} chunks above maximum "
            f"({settings.max_chunk_tokens} tokens)"
        )

    # Dry run - stop here
    if dry_run:
        click.echo("\n✅ Dry run complete (no data imported)")
        return

    # Import to Prism
    click.echo(f"\n📤 Importing to Prism ({settings.prism_base_url})...")
    click.echo(f"   Domain: bible/{translation.lower()}")
    click.echo(f"   Batch size: {batch_size}")
    click.echo(f"   Embedding: {'disabled' if no_embed else 'enabled'}")

    def progress_callback(batch_num, total_batches, result):
        if "error" in result:
            click.echo(f"   ❌ Batch {batch_num}/{total_batches}: {result['error']}")
        else:
            # Prism returns: {"total": int, "imported": int, "failed": int, "results": [...]}
            imported = result.get("imported", 0)
            failed = result.get("failed", 0)
            click.echo(
                f"   ✓ Batch {batch_num}/{total_batches}: "
                f"{imported} imported, {failed} failed"
            )

    try:
        results = asyncio.run(
            import_documents_in_batches(
                documents,
                batch_size=batch_size,
                embed=not no_embed,
                progress_callback=progress_callback,
            )
        )
    except Exception as e:
        click.echo(f"\n❌ Import failed: {e}", err=True)
        sys.exit(1)

    # Show final results
    click.echo(f"\n✅ Import complete!")
    click.echo(f"   Total documents: {results['total_documents']:,}")
    click.echo(f"   Successful: {results['success_count']:,}")
    click.echo(f"   Errors: {results['error_count']:,}")

    if results["errors"]:
        click.echo(f"\n⚠️  Errors encountered:")
        for error in results["errors"][:10]:  # Show first 10
            if "batch" in error:
                click.echo(f"   - Batch {error['batch']}: {error['error']}")
            else:
                click.echo(f"   - {error.get('document', 'Unknown')}: {error['error']}")

    if results["error_count"] > 0:
        sys.exit(1)


@cli.command()
@click.option(
    "--version",
    "-v",
    required=True,
    help="Bible translation (e.g., kjv)",
)
@click.option(
    "--verses-csv",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to verses CSV file",
)
def validate(version: str, verses_csv: Path):
    """Validate Bible CSV data quality."""
    translation = version.upper()

    click.echo(f"🔍 Validating {translation} from {verses_csv}...")

    try:
        verses = parse_bible_csv(verses_csv, translation)
    except Exception as e:
        click.echo(f"❌ Error parsing CSV: {e}", err=True)
        sys.exit(1)

    # Validate integrity
    validation = validate_verse_integrity(verses)

    click.echo(f"\n📊 Validation Results:")
    click.echo(f"   ✓ Total verses: {validation['total_verses']:,}")
    click.echo(f"   ✓ Books: {validation['books_found']}")
    click.echo(f"   ✓ Chapters: {validation['chapters_found']}")

    if validation["issues"]:
        click.echo(f"\n⚠️  Issues found ({len(validation['issues'])}):")
        for issue in validation["issues"]:
            click.echo(f"   - {issue}")
        sys.exit(1)
    else:
        click.echo(f"\n✅ No issues found!")

    # Analyze chunking
    quality = analyze_chunking_quality(verses, translation)
    click.echo(f"\n📊 Chunking Analysis:")
    click.echo(f"   Estimated chunks: {quality['total_chunks']:,}")
    click.echo(f"   Verses per chunk (avg): {quality['verses_per_chunk_avg']:.1f}")
    click.echo(f"   Token range: {quality['token_stats']['min']}-{quality['token_stats']['max']}")
    click.echo(f"   Token average: {quality['token_stats']['avg']:.0f}")


@cli.command()
@click.option(
    "--version",
    "-v",
    help="Bible translation (e.g., kjv) - optional",
)
def status(version: Optional[str]):
    """Check import status in Prism."""
    domain = None
    if version:
        translation = version.upper()
        domain = f"bible/{translation.lower()}"
        click.echo(f"🔍 Checking status for {translation}...")
    else:
        click.echo(f"🔍 Checking Prism status...")

    async def check():
        async with PrismClient() as client:
            # Check health
            if not await client.check_health():
                click.echo(f"❌ Prism not accessible at {client.base_url}", err=True)
                sys.exit(1)

            click.echo(f"✅ Prism is healthy")

            # Get stats
            stats = await client.get_stats()
            click.echo(f"\n📊 Prism Statistics:")
            click.echo(f"   Total documents: {stats.get('total_documents', 0):,}")
            click.echo(f"   Corpus documents: {stats.get('corpus_documents', 0):,}")
            click.echo(f"   KB documents: {stats.get('kb_documents', 0):,}")
            click.echo(f"   Total chunks: {stats.get('total_chunks', 0):,}")
            click.echo(f"   Embedded chunks: {stats.get('embedded_chunks', 0):,}")
            click.echo(f"   Unique domains: {stats.get('domains', 0):,}")

            if domain:
                # Count documents in specific domain
                count = await client.count_domain_documents(domain)
                click.echo(f"\n   Documents in {domain}: {count:,}")

    try:
        asyncio.run(check())
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--query",
    "-q",
    required=True,
    help="Search query text",
)
@click.option(
    "--version",
    "-v",
    help="Filter by translation (e.g., kjv)",
)
@click.option(
    "--top-k",
    type=int,
    default=5,
    help="Number of results to return",
)
def search(query: str, version: Optional[str], top_k: int):
    """Test semantic search for Bible verses."""
    domain = None
    if version:
        domain = f"bible/{version.lower()}"

    click.echo(f"🔍 Searching for: '{query}'")
    if domain:
        click.echo(f"   Domain: {domain}")

    async def do_search():
        async with PrismClient() as client:
            results = await client.search_documents(query, domain=domain, top_k=top_k)

            documents = results.get("results", [])
            if not documents:
                click.echo("\n❌ No results found")
                return

            click.echo(f"\n✅ Found {len(documents)} results:\n")
            for i, doc in enumerate(documents, 1):
                title = doc.get("document_title", doc.get("title", "Unknown"))
                similarity = doc.get("similarity", 0)
                content = doc.get("content", "")

                click.echo(f"{i}. {title} (similarity: {similarity:.3f})")
                # Show first 200 chars of content
                preview = content[:200] + "..." if len(content) > 200 else content
                click.echo(f"   {preview}\n")

    try:
        asyncio.run(do_search())
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--data-dir",
    type=click.Path(exists=True, path_type=Path),
    default=Path("data_sources/strongs"),
    help="Path to Strong's dictionary data directory",
)
@click.option(
    "--batch-size",
    type=int,
    default=100,
    help="Documents per API batch (max 100)",
)
@click.option(
    "--no-embed",
    is_flag=True,
    help="Skip embedding generation (faster, but not searchable)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Parse only, don't import to Prism",
)
def import_lexicon(
    data_dir: Path,
    batch_size: int,
    no_embed: bool,
    dry_run: bool,
):
    """Import Strong's Hebrew and Greek lexicon to Prism.

    Downloads Strong's concordance from Open Scriptures (CC-BY-SA).
    Creates ~14,000 searchable documents optimized for RAG workflows.

    Example:
        python cli.py import-lexicon --dry-run
        python cli.py import-lexicon
    """
    from lexicon_importer import LexiconImporter

    click.echo("📖 Strong's Lexicon Importer")
    click.echo(f"   Data directory: {data_dir}")
    click.echo(f"   Domain: lexicon/strongs")

    # Initialize importer
    try:
        importer = LexiconImporter(data_dir=data_dir)
    except Exception as e:
        click.echo(f"❌ Error initializing importer: {e}", err=True)
        sys.exit(1)

    # Progress callback
    def progress_callback(batch_num, total_batches, result):
        if "error" in result:
            click.echo(f"   ❌ Batch {batch_num}/{total_batches}: {result['error']}")
        else:
            imported = result.get("imported", 0)
            failed = result.get("failed", 0)
            click.echo(
                f"   ✓ Batch {batch_num}/{total_batches}: "
                f"{imported} imported, {failed} failed"
            )

    # Run import
    try:
        click.echo("\n🔍 Parsing lexicon data...")
        results = importer.import_all(
            batch_size=batch_size,
            embed=not no_embed,
            dry_run=dry_run,
            progress_callback=progress_callback if not dry_run else None,
        )

        if dry_run:
            click.echo(f"\n✅ Dry run complete!")
            click.echo(f"   Total entries: {results['total_documents']:,}")
            click.echo(f"   Hebrew: {results['hebrew_count']:,}")
            click.echo(f"   Greek: {results['greek_count']:,}")
            click.echo(f"\n📝 Sample entries:")
            for i, doc in enumerate(results['sample_documents'], 1):
                click.echo(f"\n   {i}. {doc['title']}")
                click.echo(f"      Content: {doc['content'][:150]}...")
                click.echo(f"      Metadata: {list(doc['metadata'].keys())}")
        else:
            click.echo(f"\n✅ Import complete!")
            click.echo(f"   Total documents: {results['total_documents']:,}")
            click.echo(f"   Hebrew entries: {results['hebrew_count']:,}")
            click.echo(f"   Greek entries: {results['greek_count']:,}")
            click.echo(f"   Successful: {results['success_count']:,}")
            click.echo(f"   Errors: {results['error_count']:,}")

            if results["errors"]:
                click.echo(f"\n⚠️  Errors encountered:")
                for error in results["errors"][:10]:
                    if "batch" in error:
                        click.echo(f"   - Batch {error['batch']}: {error['error']}")
                    else:
                        click.echo(f"   - {error.get('document', 'Unknown')}: {error['error']}")

            if results["error_count"] > 0:
                sys.exit(1)

    except Exception as e:
        click.echo(f"\n❌ Import failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--strong-ids",
    help="Comma-separated Strong's IDs to verify (e.g., H1,G26)",
)
def verify_lexicon(strong_ids: Optional[str]):
    """Verify lexicon entries were imported correctly.

    Searches Prism for specific Strong's entries and displays results.

    Example:
        python cli.py verify-lexicon
        python cli.py verify-lexicon --strong-ids H1,H157,G26,G2316
    """
    from lexicon_importer import verify_lexicon_import

    click.echo("🔍 Verifying lexicon import...")

    ids = None
    if strong_ids:
        ids = [s.strip() for s in strong_ids.split(",")]
        click.echo(f"   Checking IDs: {', '.join(ids)}")

    try:
        results = asyncio.run(verify_lexicon_import(strong_ids=ids))

        click.echo(f"\n📊 Prism Statistics:")
        stats = results.get("prism_stats", {})
        click.echo(f"   Total documents: {stats.get('total_documents', 0):,}")
        click.echo(f"   Total chunks: {stats.get('total_chunks', 0):,}")
        click.echo(f"   Embedded chunks: {stats.get('embedded_chunks', 0):,}")

        lexicon_count = results.get("lexicon_document_count", 0)
        click.echo(f"\n📖 Lexicon Documents: {lexicon_count:,}")

        if lexicon_count == 0:
            click.echo("\n❌ No lexicon documents found. Run 'import-lexicon' first.")
            sys.exit(1)

        click.echo(f"\n✅ Sample entries:")
        for strong_id, search_results in results.get("entries", {}).items():
            if search_results:
                entry = search_results[0]
                click.echo(f"\n   {strong_id}: {entry.get('document_title', 'Unknown')}")
                click.echo(f"      Similarity: {entry.get('similarity', 0):.3f}")
                content = entry.get('content', '')
                preview = content[:200] + "..." if len(content) > 200 else content
                click.echo(f"      {preview}")
            else:
                click.echo(f"\n   {strong_id}: ❌ Not found")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--batch-size",
    type=int,
    default=100,
    help="Documents per API batch (max 100)",
)
@click.option(
    "--no-embed",
    is_flag=True,
    help="Skip embedding generation (faster, but not searchable)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Generate documents only, don't import to Prism",
)
def export_book_metadata(
    batch_size: int,
    no_embed: bool,
    dry_run: bool,
):
    """Export book-level metadata to Prism as searchable documents.

    Creates 66 documents (one per Bible book) with comprehensive metadata
    including author, date, themes, genre, and historical context.

    Example:
        python cli.py export-book-metadata --dry-run
        python cli.py export-book-metadata
    """
    from book_metadata_exporter import import_book_metadata

    click.echo("📚 Book Metadata Exporter")
    click.echo("   Domain: metadata/books")
    click.echo("   Books: 66 (39 OT + 27 NT)")

    # Progress callback
    def progress_callback(batch_num, total_batches, result):
        if "error" in result:
            click.echo(f"   ❌ Batch {batch_num}/{total_batches}: {result['error']}")
        else:
            imported = result.get("imported", 0)
            failed = result.get("failed", 0)
            click.echo(
                f"   ✓ Batch {batch_num}/{total_batches}: "
                f"{imported} imported, {failed} failed"
            )

    try:
        click.echo("\n🔍 Generating book metadata...")
        results = asyncio.run(
            import_book_metadata(
                batch_size=batch_size,
                embed=not no_embed,
                dry_run=dry_run,
                progress_callback=progress_callback if not dry_run else None,
            )
        )

        if dry_run:
            click.echo(f"\n✅ Dry run complete!")
            click.echo(f"   Total books: {results['total_documents']}")
            click.echo(f"\n📝 Sample documents:")
            for i, doc in enumerate(results['sample_documents'], 1):
                click.echo(f"\n   {i}. {doc['title']}")
                click.echo(f"      {doc['content'][:150]}...")
                click.echo(f"      Metadata keys: {list(doc['metadata'].keys())}")
        else:
            click.echo(f"\n✅ Import complete!")
            click.echo(f"   Total documents: {results['total_documents']}")
            click.echo(f"   Successful: {results['success_count']}")
            click.echo(f"   Errors: {results['error_count']}")

            if results["errors"]:
                click.echo(f"\n⚠️  Errors encountered:")
                for error in results["errors"][:10]:
                    if "batch" in error:
                        click.echo(f"   - Batch {error['batch']}: {error['error']}")
                    else:
                        click.echo(f"   - {error.get('document', 'Unknown')}: {error['error']}")

            if results["error_count"] > 0:
                sys.exit(1)

    except Exception as e:
        click.echo(f"\n❌ Export failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default=Path("data_sources/geography"),
    help="Path to geography data directory",
)
@click.option(
    "--batch-size",
    type=int,
    default=100,
    help="Documents per API batch (max 100)",
)
@click.option(
    "--no-embed",
    is_flag=True,
    help="Skip embedding generation (faster, but not searchable)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Parse only, don't import to Prism",
)
@click.option(
    "--no-download",
    is_flag=True,
    help="Fail if data missing instead of auto-downloading",
)
def import_geography(
    data_dir: Path,
    batch_size: int,
    no_embed: bool,
    dry_run: bool,
    no_download: bool,
):
    """Import biblical geography data to Prism.

    Downloads place data from Open Bible Info (CC-BY-SA 4.0) with coordinates,
    confidence scores, and verse references. Creates 300-700 searchable documents
    for spatial RAG context.

    Example:
        python cli.py import-geography --dry-run
        python cli.py import-geography
        python cli.py import-geography --no-download
    """
    from geography_importer import GeographyImporter

    click.echo("🗺️  Biblical Geography Importer")
    click.echo(f"   Data directory: {data_dir}")
    click.echo(f"   Domain: geography/biblical")
    click.echo(f"   Download: {'disabled' if no_download else 'auto'}")

    # Initialize importer
    try:
        importer = GeographyImporter(data_dir=data_dir)
    except Exception as e:
        click.echo(f"❌ Error initializing importer: {e}", err=True)
        sys.exit(1)

    # Progress callback
    def progress_callback(batch_num, total_batches, result):
        if "error" in result:
            click.echo(f"   ❌ Batch {batch_num}/{total_batches}: {result['error']}")
        else:
            imported = result.get("imported", 0)
            failed = result.get("failed", 0)
            click.echo(
                f"   ✓ Batch {batch_num}/{total_batches}: "
                f"{imported} imported, {failed} failed"
            )

    # Run import
    try:
        if not dry_run:
            click.echo("\n🔍 Parsing geography data...")
        results = importer.import_all(
            batch_size=batch_size,
            embed=not no_embed,
            dry_run=dry_run,
            download=not no_download,
            progress_callback=progress_callback if not dry_run else None,
        )

        if "error" in results:
            click.echo(f"\n❌ {results['error']}", err=True)
            sys.exit(1)

        if dry_run:
            click.echo(f"\n✅ Dry run complete!")
            click.echo(f"   Total places: {results['total_documents']:,}")
            click.echo(f"\n📊 Place types:")
            for place_type, count in sorted(results['type_counts'].items()):
                click.echo(f"      {place_type:12}: {count:3}")
            click.echo(f"\n📝 Sample places:")
            for i, doc in enumerate(results['sample_documents'], 1):
                meta = doc['metadata']
                coords = ""
                if meta.get('latitude') and meta.get('longitude'):
                    coords = f" ({meta['latitude']:.2f}°N, {meta['longitude']:.2f}°E)"
                click.echo(f"\n   {i}. {doc['title']}{coords}")
                click.echo(f"      Type: {meta.get('place_type', 'unknown')}")
                click.echo(f"      Confidence: {meta.get('confidence_level', 'unknown')} (score: {meta.get('confidence_score', 0)})")
                if meta.get('verse_references'):
                    refs = meta['verse_references'][:3]
                    click.echo(f"      Verses: {', '.join(refs)} ({len(meta.get('verse_references', []))} total)")
        else:
            click.echo(f"\n✅ Import complete!")
            click.echo(f"   Total places: {results['total_documents']:,}")
            click.echo(f"   Successful: {results['success_count']:,}")
            click.echo(f"   Errors: {results['error_count']:,}")
            click.echo(f"\n📊 Place types:")
            for place_type, count in sorted(results['type_counts'].items()):
                click.echo(f"      {place_type:12}: {count:3}")

            if results["errors"]:
                click.echo(f"\n⚠️  Errors encountered:")
                for error in results["errors"][:10]:
                    if "batch" in error:
                        click.echo(f"   - Batch {error['batch']}: {error['error']}")
                    else:
                        click.echo(f"   - {error.get('document', 'Unknown')}: {error['error']}")

            if results["error_count"] > 0:
                sys.exit(1)

    except Exception as e:
        click.echo(f"\n❌ Import failed: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option(
    "--version",
    "-v",
    required=True,
    help="Bible translation (e.g., kjv)",
)
@click.option(
    "--modules-dir",
    type=click.Path(path_type=Path),
    default=Path("data_sources/sword_modules"),
    help="Path to SWORD modules directory",
)
@click.option(
    "--sample-verses",
    type=int,
    default=5,
    help="Number of sample verses to display",
)
def import_original(
    version: str,
    modules_dir: Path,
    sample_verses: int,
):
    """Display original Hebrew/Greek text for sample verses (Phase 2: dry run only).

    Shows interlinear display with original text and Strong's numbers.
    Full reimport with metadata enhancement is deferred to Phase 3.

    Example:
        python cli.py import-original --version kjv
        python cli.py import-original --version kjv --sample-verses 10
    """
    from sword_parser import SwordParser, verify_book_normalization

    translation = version.upper()

    click.echo(f"📖 Original Texts Display - {translation}")
    click.echo(f"   Modules directory: {modules_dir}")
    click.echo(f"   Mode: Dry run (Phase 2 - display only)")
    click.echo(f"\n⚠️  Note: Full reimport with metadata enhancement is deferred to Phase 3")

    # Initialize parser
    try:
        parser = SwordParser(modules_dir=modules_dir)
        parser.initialize()
    except Exception as e:
        click.echo(f"\n❌ Error initializing SWORD parser: {e}", err=True)
        sys.exit(1)

    # Test verses (mix of OT and NT)
    sample_references = [
        ("Genesis", 1, 1),      # OT - Hebrew
        ("Exodus", 3, 14),      # OT - Hebrew (I AM WHO I AM)
        ("Psalm", 23, 1),       # OT - Hebrew (The LORD is my shepherd)
        ("Isaiah", 53, 5),      # OT - Hebrew (prophecy)
        ("John", 1, 1),         # NT - Greek (In the beginning was the Word)
        ("John", 3, 16),        # NT - Greek (For God so loved the world)
        ("Romans", 8, 28),      # NT - Greek (All things work together for good)
        ("1 Corinthians", 13, 13),  # NT - Greek (faith, hope, love)
    ]

    # Limit to requested sample count
    sample_references = sample_references[:sample_verses]

    click.echo(f"\n📝 Sample Original Texts:\n")

    for book, chapter, verse in sample_references:
        try:
            result = parser.get_verse_text(book, chapter, verse)

            if result:
                # Get English text for comparison (if available from Prism)
                ref = f"{book} {chapter}:{verse}"

                click.echo(f"{'=' * 70}")
                click.echo(f"{ref}")
                click.echo(f"{'=' * 70}")

                # Original text
                lang_display = "Hebrew" if result["language"] == "hebrew" else "Greek"
                click.echo(f"{lang_display}: {result['original_text']}")

                # Strong's numbers if present
                if "strongs_numbers" in result and result["strongs_numbers"]:
                    strongs_list = result["strongs_numbers"][:10]  # Show first 10
                    strongs_str = ", ".join(strongs_list)
                    if len(result["strongs_numbers"]) > 10:
                        strongs_str += f", ... ({len(result['strongs_numbers'])} total)"
                    click.echo(f"Strong's: {strongs_str}")

                click.echo()
            else:
                click.echo(f"❌ {book} {chapter}:{verse}: Not found\n")

        except Exception as e:
            click.echo(f"❌ {book} {chapter}:{verse}: Error - {e}\n")

    # Verify book normalization
    click.echo(f"{'=' * 70}")
    click.echo("📚 Book Name Normalization Verification")
    click.echo(f"{'=' * 70}\n")

    normalization = verify_book_normalization()

    # Group by changes
    no_change = []
    with_change = []

    for original, normalized in sorted(normalization.items()):
        if original != normalized:
            with_change.append((original, normalized))
        else:
            no_change.append(original)

    if with_change:
        click.echo("Books requiring normalization:")
        for original, normalized in with_change:
            click.echo(f"   {original:25} → {normalized}")

    click.echo(f"\nTotal: {len(normalization)} books verified")
    click.echo(f"   {len(no_change)} books unchanged")
    click.echo(f"   {len(with_change)} books normalized")

    click.echo(f"\n✅ Original texts accessible via SWORD modules")
    click.echo(f"   Hebrew OT: {'✓' if parser.wlc else '✗'} WLC module")
    click.echo(f"   Greek NT:  {'✓' if parser.sblgnt else '✗'} SBLGNT module")

    click.echo(f"\n💡 Next Steps (Phase 3):")
    click.echo(f"   1. Modify verse_chunker.py to accept original_texts parameter")
    click.echo(f"   2. Add original text to verse metadata during chunking")
    click.echo(f"   3. Implement full reimport command with --add-original-texts flag")
    click.echo(f"   4. UI: Display Hebrew/Greek alongside English text")


@cli.command()
@click.option(
    "--query",
    help="Optional place name to search for (e.g., Jerusalem)",
)
def verify_geography(query: Optional[str]):
    """Verify geography import was successful.

    Searches Prism for biblical places and displays results.

    Example:
        python cli.py verify-geography
        python cli.py verify-geography --query "Jerusalem"
    """
    from geography_importer import verify_geography_import

    click.echo("🔍 Verifying geography import...")

    sample_queries = None
    if query:
        sample_queries = [query]
        click.echo(f"   Searching for: {query}")

    try:
        results = asyncio.run(verify_geography_import(sample_queries=sample_queries))

        click.echo(f"\n📊 Prism Statistics:")
        stats = results.get("prism_stats", {})
        click.echo(f"   Total documents: {stats.get('total_documents', 0):,}")
        click.echo(f"   Total chunks: {stats.get('total_chunks', 0):,}")

        geography_count = results.get("geography_document_count", 0)
        click.echo(f"\n🗺️  Geography Documents: {geography_count:,}")

        if geography_count == 0:
            click.echo("\n❌ No geography documents found. Run 'import-geography' first.")
            sys.exit(1)

        click.echo(f"\n✅ Sample places:")
        for place_name, search_results in results.get("places", {}).items():
            if search_results:
                place = search_results[0]
                meta = place.get('metadata', {})
                click.echo(f"\n   {place_name}:")
                click.echo(f"      Title: {place.get('document_title', 'Unknown')}")
                click.echo(f"      Similarity: {place.get('similarity', 0):.3f}")
                if meta.get('latitude') and meta.get('longitude'):
                    click.echo(f"      Coordinates: {meta['latitude']:.4f}°N, {meta['longitude']:.4f}°E")
                if meta.get('confidence_level'):
                    click.echo(f"      Confidence: {meta['confidence_level']} (score: {meta.get('confidence_score', 0)})")
                content = place.get('content', '')
                preview = content[:200] + "..." if len(content) > 200 else content
                click.echo(f"      {preview}")
            else:
                click.echo(f"\n   {place_name}: ❌ Not found")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


def _show_genre_distribution(documents: List[Dict]) -> None:
    """Display chunk distribution by genre."""
    from collections import defaultdict
    import statistics

    genre_stats = defaultdict(list)

    for doc in documents:
        genre = doc["metadata"].get("genre", {}).get("type", "unknown")
        token_count = doc["metadata"]["structure"]["token_count"]
        genre_stats[genre].append(token_count)

    click.echo("\n📊 Genre distribution:")
    for genre in sorted(genre_stats.keys()):
        tokens = genre_stats[genre]
        click.echo(
            f"   {genre:12} | "
            f"chunks: {len(tokens):4} | "
            f"avg: {statistics.mean(tokens):5.1f} tokens | "
            f"range: {min(tokens):3}-{max(tokens):3}"
        )


if __name__ == "__main__":
    cli()
