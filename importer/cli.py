"""Command-line interface for Bible importer."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

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
def import_bible(
    version: str,
    verses_csv: Path,
    books: Optional[str],
    batch_size: int,
    no_embed: bool,
    dry_run: bool,
):
    """Import Bible translation into Prism."""
    translation = version.upper()

    click.echo(f"🔍 Parsing {translation} from {verses_csv}...")

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
    documents = list(chunk_verses(verses, translation))
    click.echo(f"✅ Created {len(documents):,} chunks")

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


if __name__ == "__main__":
    cli()
