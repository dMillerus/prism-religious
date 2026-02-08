# Bible Importer for aiml-stack

Imports Bible translations into Prism (PSDL) with optimized chunking for LLM consumption via MCP.

## Overview

This tool:
- Parses Bible CSV files from [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases)
- Chunks verses adaptively for optimal LLM context (target: 350 tokens per chunk)
- Imports into Prism corpus API with automatic embedding generation
- Supports 140+ Bible translations with the same codebase

## Currently Imported Translations

Five English translations are currently available for semantic search:

| Translation | Identifier | Chunks | Characteristics | Year |
|-------------|-----------|--------|-----------------|------|
| **KJV** | `kjv` | 3,539 | Early Modern English, poetic | 1611 |
| **ASV** | `asv` | 3,528 | Literal, word-for-word | 1901 |
| **BBE** | `bbe` | 3,519 | Simple English (850-word vocabulary) | 1965 |
| **YLT** | `ylt` | 3,821 | Ultra-literal translation | 1862 |
| **Webster** | `webster` | 3,662 | Modernized KJV | 1833 |

**Total: 18,069 chunks** across 5 translations, all fully embedded and searchable.

### Cross-Version Search Examples

Search across all versions:
```bash
make bible-search QUERY='faith hope love'
# Returns results from all 5 translations
```

Search specific version:
```bash
python cli.py search --query "shepherd" --version asv --top-k 5
```

Compare translations side-by-side:
```bash
python cli.py search --query "love your neighbor" --top-k 10
# Results show different phrasings across versions
```

## Installation

```bash
cd /dpool/aiml-stack/scripts/bible-importer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

### 1. Download Bible CSV Data

```bash
# KJV (King James Version)
curl -L -o /dpool/aiml-stack/data/bible/kjv/kjv_verses.csv \
  "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/csv/KJV.csv"
```

### 2. Validate Data

```bash
python cli.py validate \
  --version kjv \
  --verses-csv /dpool/aiml-stack/data/bible/kjv/kjv_verses.csv
```

### 3. Import into Prism

```bash
# Full import (31,102 verses → ~3,500 chunks)
python cli.py import-bible \
  --version kjv \
  --verses-csv /dpool/aiml-stack/data/bible/kjv/kjv_verses.csv \
  --batch-size 100

# Import specific books (for testing)
python cli.py import-bible \
  --version kjv \
  --verses-csv /dpool/aiml-stack/data/bible/kjv/kjv_verses.csv \
  --books Genesis,Exodus \
  --batch-size 50

# Dry run (parse and chunk only, no API calls)
python cli.py import-bible \
  --version kjv \
  --verses-csv /dpool/aiml-stack/data/bible/kjv/kjv_verses.csv \
  --dry-run
```

### 4. Check Status

```bash
# General Prism statistics
python cli.py status

# Version-specific (requires documents endpoint query)
python cli.py status --version kjv
```

### 5. Test Search

```bash
# Semantic search with domain filter
python cli.py search \
  --query "In the beginning God created" \
  --version kjv \
  --top-k 5

# Search across all Bible versions
python cli.py search \
  --query "love thy neighbor" \
  --top-k 10
```

## CLI Reference

### Commands

#### `validate`
Validate Bible CSV data quality.

Options:
- `--version, -v` (required): Translation identifier (e.g., kjv, niv)
- `--verses-csv` (required): Path to verses CSV file

Example:
```bash
python cli.py validate --version kjv --verses-csv ./data/kjv_verses.csv
```

#### `import-bible`
Import Bible translation into Prism.

Options:
- `--version, -v` (required): Translation identifier
- `--verses-csv` (required): Path to verses CSV file
- `--books`: Comma-separated list of books (default: all 66 books)
- `--batch-size`: Documents per API batch, max 100 (default: 100)
- `--no-embed`: Skip embedding generation (faster, but not searchable)
- `--dry-run`: Parse and chunk only, don't call Prism API

Examples:
```bash
# Full import
python cli.py import-bible --version kjv --verses-csv ./data/kjv.csv

# Specific books
python cli.py import-bible --version kjv --verses-csv ./data/kjv.csv --books "Genesis,Psalms,Matthew"

# Fast import without embeddings (can generate later)
python cli.py import-bible --version kjv --verses-csv ./data/kjv.csv --no-embed
```

#### `status`
Check import status in Prism.

Options:
- `--version, -v` (optional): Filter by translation

Examples:
```bash
python cli.py status              # General stats
python cli.py status --version kjv  # KJV-specific
```

#### `search`
Test semantic search for Bible verses.

Options:
- `--query, -q` (required): Search query text
- `--version, -v` (optional): Filter by translation
- `--top-k`: Number of results (default: 5)

Examples:
```bash
python cli.py search --query "faith hope love" --version kjv --top-k 3
python cli.py search --query "shepherd" --top-k 10
```

## Chunking Strategy

### Problem
Bible verses are too small individually (~25 tokens avg) but chapters are too large (500-2000 tokens). Need semantic coherence for LLM consumption.

### Solution
Adaptive multi-verse chunking:
1. Group consecutive verses until reaching 300-400 token target
2. Respect chapter boundaries (never span chapters)
3. Handle edge cases (single long verses, poetry, genealogies)
4. Preserve verse range metadata for precise citations

### Example Chunks
- Genesis 1:1-13 (creation narrative, ~340 tokens)
- Psalm 23 (complete psalm, ~180 tokens - kept together)
- Genesis 5:1-11 (genealogy, ~290 tokens)

### Configuration
Edit `config.py` to adjust chunking parameters:
```python
target_chunk_tokens: int = 350  # Target tokens per chunk
min_chunk_tokens: int = 50      # Minimum (single verse floor)
max_chunk_tokens: int = 500     # Maximum (hard limit)
```

## Data Structure

### Prism Document Format

Each verse group becomes a Prism corpus document:

```python
{
  "title": "Genesis 1:1-5 (KJV)",
  "content": "1 In the beginning God created...",
  "domain": "bible/kjv",
  "metadata": {
    "book": "Genesis",
    "book_id": 1,
    "chapter": 1,
    "verse_start": 1,
    "verse_end": 5,
    "testament": "OT",
    "translation": "KJV",
    "language": "en",
    "structure": {
      "path": "KJV > Genesis > Chapter 1 > Verses 1-5",
      "book_number": 1,
      "total_verses": 5,
      "token_count": 340
    },
    "source": {
      "type": "corpus",
      "origin": "scrollmapper/bible_databases",
      "url": "https://github.com/scrollmapper/bible_databases",
      "format": "csv"
    }
  }
}
```

### Domain Namespacing
- `bible/kjv` - King James Version (1611)
- `bible/asv` - American Standard Version (1901)
- `bible/bbe` - Bible in Basic English (1965)
- `bible/ylt` - Young's Literal Translation (1862)
- `bible/webster` - Webster Bible (1833)
- `bible` - All versions (when searching without version filter)

## Performance

### KJV Import
- Verses: 31,102
- Chunks: ~3,500
- Parsing: <1 minute
- API upload: ~5 minutes (35 batches × 100 docs)
- Embedding: 2-3 hours (Ollama nomic-embed-text, background)
- Total time: ~3 hours end-to-end

### Storage
- Verbatim text: ~4MB (KJV raw text)
- Prism documents: ~15MB (with metadata)
- Embeddings: ~10MB (3,500 chunks × 768 dims × 4 bytes)
- Total: ~30MB per Bible version

## Adding New Translations

### Public Domain Translations

The [scrollmapper repository](https://github.com/scrollmapper/bible_databases/tree/master/formats/csv) provides 140+ public domain translations. **Note:** Modern copyrighted translations (NIV, ESV, NASB, NLT) are **not available** for free download and require licensing agreements.

**Available public domain English translations include:**
- KJV, AKJV, KJVPCE (King James variants)
- ASV, RWebster, Darby, YLT (literal translations)
- BBE, Twenty (simplified/modern English)
- Many historical translations (Tyndale, Geneva, Wycliffe, etc.)

### Import Process

1. Download CSV from scrollmapper:
```bash
# Example: Darby Translation
curl -L -o /dpool/aiml-stack/data/bible/darby/darby_verses.csv \
  "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/csv/Darby.csv"
```

2. Validate:
```bash
python cli.py validate --version darby --verses-csv ./data/bible/darby/darby_verses.csv
```

3. Import:
```bash
python cli.py import-bible --version darby --verses-csv ./data/bible/darby/darby_verses.csv
```

4. Search across all versions:
```bash
# All imported translations will be searchable
python cli.py search --query "grace" --top-k 10
```

### Bulk Import

Use Makefile targets for convenience:
```bash
# Download and import all modern translations (ASV, BBE, YLT, Webster)
make bible-download-all
make bible-import-all-modern
```

## Troubleshooting

### Prism Not Accessible
```
❌ Prism service not accessible at http://localhost:8100
```

**Solution:**
```bash
cd /dpool/aiml-stack
docker compose up -d prism
docker compose ps prism  # Check status
docker compose logs -f prism  # View logs
```

### Import Fails with Duplicates
```
Duplicate content (existing document: xxx)
```

**Solution:** Documents already imported. This is expected behavior - Prism prevents duplicate corpus content. To re-import:
1. Delete existing documents via Prism API (if needed)
2. Or skip re-import - corpus documents are immutable by design

### Embeddings Not Generated
If `--no-embed` was used or embeddings failed:

**Solution:** Embeddings are generated asynchronously. Check:
```bash
docker compose logs -f prism
# Watch for: "Embedded chunk xxx"
```

To verify completion:
```bash
python cli.py status
# Check: embedded_chunks should equal total_chunks
```

### Chunking Quality Issues
Too many chunks below/above thresholds?

**Solution:** Adjust chunking parameters in `config.py`:
```python
target_chunk_tokens = 400  # Increase for larger chunks
min_chunk_tokens = 100     # Raise floor
max_chunk_tokens = 600     # Raise ceiling
```

Then re-validate:
```bash
python cli.py validate --version kjv --verses-csv ./data/kjv.csv
```

## Architecture

### Components
- `csv_parser.py` - Parse scrollmapper CSV format, validate integrity
- `verse_chunker.py` - Adaptive token-aware verse grouping
- `prism_client.py` - Async HTTP client for Prism corpus API
- `cli.py` - Click-based command-line interface
- `config.py` - Pydantic settings with environment overrides

### Dependencies
- `httpx` - Async HTTP for Prism API calls
- `tiktoken` - Token counting (cl100k_base encoding)
- `pydantic` - Data validation and settings
- `click` - CLI framework

### Integration with Prism
- Uses Prism's corpus API (`/api/v1/corpus/import`)
- Documents automatically marked as immutable
- Duplicate detection via content hash
- Batch import (up to 100 docs per call)
- Async embedding generation

## Future Work

### MCP Server Integration
Build MCP server on top of this data layer:

```python
@mcp.tool()
async def search_bible_verses(query: str, version: str = "kjv", limit: int = 5):
    """Semantic search for Bible verses via Prism."""

@mcp.tool()
async def get_passage(book: str, chapter: int, verse_start: int, verse_end: int):
    """Retrieve specific passage by reference."""

@mcp.resource()
async def list_bible_books(version: str = "kjv"):
    """List all books with chapter counts."""
```

### Cross-Version Search
Enable comparative study:
```bash
python cli.py compare \
  --query "love thy neighbor" \
  --versions kjv,niv,esv \
  --show-differences
```

### Enhanced Metadata
- Strong's concordance numbers
- Cross-references
- Translation notes
- Original language lemmas

## Testing

Comprehensive test suite with 117 tests covering unit tests, integration tests, search quality, and regression prevention.

### Quick Test Commands

```bash
# All tests (requires Prism running)
pytest tests/ -v

# Unit tests only (no dependencies, fast)
pytest tests/unit/ -v

# Integration tests (requires Prism + data)
docker compose up -d prism
pytest tests/integration/ -v

# Test specific module
pytest tests/unit/test_verse_chunker.py -v

# Test search quality
pytest tests/integration/test_search_quality.py -v
```

### Test Coverage

- **Unit Tests (83)**: CSV parsing, verse chunking, Prism client, config, CLI
- **Integration Tests (34)**: End-to-end search, domain filtering, famous passages, regression
- **Execution Time**: ~3.5 seconds total

See [tests/README.md](tests/README.md) for detailed test documentation.

## License

Bible text from [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases) (MIT License).

Importer code: Part of aiml-stack project.

## Credits

- Bible CSV data: [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases)
- Chunking algorithm: Custom implementation using tiktoken
- Storage layer: [Prism (PSDL)](https://github.com/yourusername/prism)
