"""Import missing Greek lexicon entries to Prism."""

import asyncio
from pathlib import Path
from lexicon_importer import LexiconImporter
from prism_client import import_documents_in_batches

async def get_existing_greek_ids():
    """Get list of already-imported Greek Strong's IDs."""
    from prism_client import PrismClient

    existing_ids = set()
    async with PrismClient() as client:
        # Get all Greek documents
        response = await client.client.get(
            "/api/v1/documents",
            params={"domain": "lexicon/strongs", "limit": 10000}
        )
        data = response.json()

        for doc in data.get("documents", []):
            strong_id = doc.get("metadata", {}).get("strong_id")
            if strong_id and strong_id.startswith("G"):
                existing_ids.add(strong_id)

    return existing_ids

async def main():
    print("🔍 Checking for missing Greek lexicon entries...")

    # Get existing IDs from Prism
    existing_ids = await get_existing_greek_ids()
    print(f"   Found {len(existing_ids)} existing Greek entries in Prism")

    # Parse Greek lexicon from source
    importer = LexiconImporter(Path("data_sources/strongs"))
    greek_dict = importer.parse_js_dictionary(importer.greek_file)
    print(f"   Found {len(greek_dict)} Greek entries in source")

    # Find missing entries
    missing_ids = set(greek_dict.keys()) - existing_ids
    print(f"   Missing {len(missing_ids)} Greek entries")

    if not missing_ids:
        print("\n✅ No missing entries - all Greek lexicon entries already imported!")
        return

    # Create documents for missing entries
    missing_docs = []
    for strong_id in sorted(missing_ids, key=lambda x: int(x[1:])):
        entry = greek_dict[strong_id]
        doc = importer.greek_entry_to_document(strong_id, entry)
        missing_docs.append(doc)

    print(f"\n📤 Importing {len(missing_docs)} missing Greek entries...")

    # Progress callback
    def progress_callback(batch_num, total_batches, result):
        if "error" in result:
            print(f"   ❌ Batch {batch_num}/{total_batches}: {result['error']}")
        else:
            imported = result.get("imported", 0)
            failed = result.get("failed", 0)
            print(f"   ✓ Batch {batch_num}/{total_batches}: {imported} imported, {failed} failed")

    # Import missing entries
    results = await import_documents_in_batches(
        missing_docs,
        batch_size=100,
        embed=True,
        progress_callback=progress_callback,
    )

    print(f"\n✅ Import complete!")
    print(f"   Total attempted: {results['total_documents']:,}")
    print(f"   Successful: {results['success_count']:,}")
    print(f"   Errors: {results['error_count']:,}")

if __name__ == "__main__":
    asyncio.run(main())
