# Bible Text Ingestion System - User Guide

## Overview

The Bible Importer provides optimized ingestion of Bible translations into Prism (PSDL) for LLM consumption via Model Context Protocol (MCP). The system focuses on intelligent chunking and semantic search rather than building a UI.

## Key Features

✅ **Adaptive Verse Chunking** - Groups verses to target 350 tokens (optimal for LLM context)
✅ **Semantic Search** - pgvector embeddings enable concept-based search, not just keywords
✅ **Multi-Version Support** - 140+ translations available with same codebase
✅ **Corpus Architecture** - Immutable documents prevent accidental modifications
✅ **Rich Metadata** - Hierarchical paths, testament tags, canonical ordering
✅ **MCP-Ready** - Data structure designed for future MCP server integration

## Quick Start

### Prerequisites

- Prism service running: `docker compose up -d prism`
- Python 3.10+ with venv
- ~500MB disk space per Bible version
- Ollama with nomic-embed-text model (for embeddings)

### Installation

```bash
cd /dpool/aiml-stack/scripts/bible-importer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Import KJV (5 minutes)

```bash
# 1. Validate data
python cli.py validate \
  --version kjv \
  --verses-csv /dpool/aiml-stack/data/bible/kjv/kjv_verses.csv

# 2. Import (~2 minutes for API upload, 2-3 hours for embeddings)
python cli.py import-bible \
  --version kjv \
  --verses-csv /dpool/aiml-stack/data/bible/kjv/kjv_verses.csv \
  --batch-size 100

# 3. Verify
python cli.py status
```

### Test Search

```bash
# Famous verses
python cli.py search --query "The Lord is my shepherd" --version kjv
python cli.py search --query "faith hope love" --version kjv

# Concepts
python cli.py search --query "God's faithfulness in trials" --version kjv
python cli.py search --query "sacrifice and atonement" --version kjv
```

## Understanding the Chunking Strategy

### The Problem

Bible verses vary wildly in length:
- Average verse: ~25 tokens (too small for LLM context)
- Short verse: "Jesus wept." (2 tokens)
- Long verse: Some genealogies reach 100+ tokens
- Full chapter: 500-2000 tokens (too large, loses focus)

**Challenge**: Find the "semantic unit" size that preserves meaning while optimizing for LLM retrieval.

### The Solution

**Adaptive Multi-Verse Chunking**:

1. **Target**: 300-400 tokens per chunk (sweet spot for context)
2. **Grouping**: Accumulate consecutive verses until target reached
3. **Boundaries**: Never span chapters (natural semantic breaks)
4. **Flexibility**: Allow 280-420 token range (±20%) for coherence

### Examples

#### Short Chapter (Psalm 23)
```
Chunk: Psalm 23:1-6 (KJV)
Verses: 6
Tokens: ~180
Strategy: Keep entire psalm together (semantic unit)
```

#### Creation Narrative (Genesis 1)
```
Chunk 1: Genesis 1:1-13 (KJV)
Verses: 13 (days 1-3)
Tokens: 340

Chunk 2: Genesis 1:14-25 (KJV)
Verses: 12 (days 4-6)
Tokens: 335

Chunk 3: Genesis 1:26-31 (KJV)
Verses: 6 (human creation, day 6)
Tokens: 285
```

#### Long Genealogy (Genesis 5)
```
Chunk: Genesis 5:1-11 (KJV)
Verses: 11 (Adam through Enosh lineage)
Tokens: 290
Strategy: Group genealogical entries to maintain family line context
```

### Configuration

Edit `config.py` if you need different chunking behavior:

```python
# Conservative (larger, more context per chunk)
target_chunk_tokens = 400
min_chunk_tokens = 100
max_chunk_tokens = 600

# Aggressive (smaller, more precise matching)
target_chunk_tokens = 250
min_chunk_tokens = 50
max_chunk_tokens = 400
```

**Recommendation**: Default settings (350/50/500) work well for most use cases.

## Data Structure

### Prism Document Schema

Each chunk is stored as an immutable corpus document:

```json
{
  "title": "Genesis 1:1-13 (KJV)",
  "content": "1 In the beginning...",
  "domain": "bible/kjv",
  "metadata": {
    "book": "Genesis",
    "book_id": 1,
    "chapter": 1,
    "verse_start": 1,
    "verse_end": 13,
    "testament": "OT",
    "translation": "KJV",
    "language": "en",
    "structure": {
      "path": "KJV > Genesis > Chapter 1 > Verses 1-13",
      "book_number": 1,
      "total_verses": 13,
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

### Why This Structure?

**For LLMs:**
- `content`: Verse text with verse numbers for precise citation
- `title`: Human-readable reference for context
- `structure.token_count`: Pre-calculated for context window planning

**For MCP:**
- `domain`: Filters by translation (`bible/kjv`, `bible/niv`, etc.)
- `book_id`: Canonical ordering (Genesis=1, Revelation=66)
- `verse_start/end`: Enables range queries and context reconstruction
- `structure.path`: Hierarchical navigation

**For Retrieval:**
- pgvector embeddings on `content` field
- JSONB metadata enables complex queries
- Immutability ensures data integrity

## Common Use Cases

### 1. Semantic Verse Discovery

**Query**: "God's love for humanity"

**What Happens:**
1. Query embedded by nomic-embed-text
2. pgvector cosine similarity search
3. Returns chunks semantically related to concept

**Top Results:**
- John 3:16 ("For God so loved the world...")
- 1 John 4:8-10 ("God is love...")
- Romans 5:8 ("God demonstrates his love...")

**Why It Works:** Embeddings capture meaning, not just keywords.

### 2. Topic Exploration

**Query**: "wisdom in decision making"

**Returns:**
- Proverbs passages on discernment
- James on asking God for wisdom
- Solomon's request for wisdom

**Use Case:** LLM needs biblical perspective on a modern question.

### 3. Cross-Reference Finding

**Query**: Content from Romans 8:28

**Returns:**
- Related verses about God's sovereignty
- Similar promises in other epistles
- Old Testament parallels (Joseph narrative)

**Use Case:** Building a study on a theme.

### 4. Context Retrieval

**MCP Tool** (future): `get_passage("Ephesians", 2, 1, 10)`

**Returns:** Chunks containing Ephesians 2:1-10, possibly multiple due to verse grouping

**Use Case:** LLM needs exact passage for citation or commentary.

## Performance Characteristics

### KJV Import (31,102 verses)

| Phase | Duration | Details |
|-------|----------|---------|
| CSV Parsing | <1 min | Load and validate 31K verses |
| Chunking | <1 min | Create 3,539 optimized chunks |
| API Upload | ~2 min | 36 batches × 100 docs |
| Embedding | 2-3 hours | Ollama nomic-embed-text (background) |
| **Total** | **~3 hours** | Mostly embedding generation |

### Storage per Version

- Raw CSV: ~4MB (compressed text)
- Prism documents: ~15MB (with metadata)
- pgvector embeddings: ~10MB (3,500 × 768 dims)
- **Total: ~30MB per translation**

### Search Performance

- Simple query: <100ms (pgvector index)
- Cross-version query: <200ms (union of domain filters)
- Reranking (future): +50-100ms (if implemented)

## Adding More Translations

### Available Translations

The scrollmapper repository provides 140+ versions:

**English:**
- KJV, NKJV (King James family)
- NIV, NIV84 (New International)
- ESV (English Standard)
- NASB (New American Standard)
- NLT (New Living)

**Other Languages:**
- Spanish: RVR1960, NVI
- French: LSG
- German: LUT
- Portuguese: ARC

Browse all: https://github.com/scrollmapper/bible_databases/tree/master/formats/csv

### Import Process

```bash
# 1. Download
mkdir -p /dpool/aiml-stack/data/bible/niv
curl -L -o /dpool/aiml-stack/data/bible/niv/niv_verses.csv \
  "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/csv/NIV.csv"

# 2. Validate
python cli.py validate --version niv --verses-csv ./data/bible/niv/niv_verses.csv

# 3. Import
python cli.py import-bible --version niv --verses-csv ./data/bible/niv/niv_verses.csv

# 4. Test
python cli.py search --query "grace and peace" --version niv --top-k 5
```

### Multi-Version Search

Once you have multiple translations:

```bash
# Search all versions
python cli.py search --query "love your enemies" --top-k 10

# Results will include:
# - Matthew 5:44 (KJV): "...Love your enemies..."
# - Matthew 5:44 (NIV): "...love your enemies..."
# - Luke 6:27 (both versions)
```

**Use Case:** Compare how different translations render the same concept.

## Integration with MCP

### Planned MCP Server

The data structure supports these MCP tools (future work):

```python
# 1. Semantic search
@mcp.tool()
async def search_bible(
    query: str,
    version: str = "kjv",
    testament: str | None = None,
    limit: int = 5
) -> list[dict]:
    """
    Search Bible by concept or topic.

    Args:
        query: Natural language search (e.g., "God's faithfulness")
        version: Translation (kjv, niv, esv, etc.)
        testament: Filter by OT or NT
        limit: Number of results

    Returns:
        List of verse chunks with metadata
    """

# 2. Passage retrieval
@mcp.tool()
async def get_passage(
    book: str,
    chapter: int,
    verse_start: int,
    verse_end: int | None = None,
    version: str = "kjv"
) -> dict:
    """
    Get exact Bible passage by reference.

    Returns:
        {
            "reference": "John 3:16-17 (KJV)",
            "text": "16 For God so loved...",
            "metadata": {...}
        }
    """

# 3. Context navigation
@mcp.tool()
async def get_surrounding_context(
    verse_reference: str,
    verses_before: int = 3,
    verses_after: int = 3,
    version: str = "kjv"
) -> dict:
    """
    Get context around a verse.

    Useful when LLM needs more context than initial chunk provided.
    """

# 4. Cross-references
@mcp.tool()
async def find_related_passages(
    reference: str,
    version: str = "kjv",
    limit: int = 5
) -> list[dict]:
    """
    Find semantically related passages.

    Uses embedding similarity, not manual cross-reference tables.
    """
```

### Example MCP Workflow

**User**: "What does the Bible say about patience in suffering?"

**LLM Process:**
1. Calls `search_bible("patience in suffering", limit=5)`
2. Receives James 1:2-4, Romans 5:3-5, 1 Peter 1:6-7, etc.
3. Synthesizes response with exact citations
4. If more context needed, calls `get_surrounding_context()`

**Result:** LLM provides biblically-grounded response with precise references.

## Troubleshooting

### Issue: Import fails with "Prism not accessible"

**Cause:** Prism service not running

**Solution:**
```bash
docker compose up -d prism
docker compose ps prism  # Should show "healthy"
docker compose logs -f prism  # Check for errors
```

### Issue: Embeddings not generating

**Cause:** Ollama not running or model not downloaded

**Solution:**
```bash
docker compose ps ollama
docker compose logs ollama

# Check model
curl http://localhost:11434/api/tags

# Download if missing
docker compose exec ollama ollama pull nomic-embed-text
```

### Issue: Search returns poor results

**Cause:** Embeddings may still be generating (background process)

**Solution:**
```bash
python cli.py status
# Check: embedded_chunks should equal total_chunks

# Watch embedding progress
docker compose logs -f prism | grep "Embedded"
```

### Issue: Duplicate content errors

**Cause:** Documents already imported

**Solution:** This is expected behavior. Corpus documents are immutable and deduplicated by content hash. If you need to re-import:

1. Delete existing documents (requires direct Prism API or DB access)
2. Or skip re-import - corpus is designed to be write-once

### Issue: Chunk token counts seem off

**Cause:** Token counting uses cl100k_base (GPT-4 encoding)

**Solution:** This is intentional. Token counts are for:
- Planning LLM context windows
- Ensuring retrieval chunks fit typical limits
- Not for exact billing (use your model's tokenizer for that)

## Best Practices

### 1. Validate Before Importing

Always run `validate` first to check data quality:

```bash
python cli.py validate --version kjv --verses-csv ./data/kjv.csv
```

Catches:
- Missing verses
- Empty text
- Unknown books
- Malformed CSV

### 2. Start with Dry Run

Test chunking without API calls:

```bash
python cli.py import-bible --version kjv --verses-csv ./data/kjv.csv --dry-run
```

Reviews:
- Total chunks created
- Token distribution
- Chunks outside target range

### 3. Use Batch Imports for Testing

Import a few books first:

```bash
python cli.py import-bible \
  --version kjv \
  --verses-csv ./data/kjv.csv \
  --books Genesis,Psalms,Matthew
```

Benefits:
- Faster iteration
- Test search quality
- Validate metadata structure

### 4. Monitor Embedding Progress

Embeddings happen asynchronously. Monitor:

```bash
# Check status periodically
watch -n 30 'python cli.py status'

# Or watch logs
docker compose logs -f prism | grep "Embedded"
```

### 5. Test Search Before Building MCP Server

Verify semantic search works as expected:

```bash
# Test various query types
python cli.py search --query "shepherd" --version kjv
python cli.py search --query "God's promises" --version kjv
python cli.py search --query "wisdom in leadership" --version kjv
```

Ensures embeddings capture meaning correctly.

## Advanced Usage

### Custom Chunking Parameters

For specialized use cases, edit `config.py`:

```python
# Poetry-focused (shorter, preserve verse integrity)
target_chunk_tokens = 200
min_chunk_tokens = 50
max_chunk_tokens = 300

# Narrative-focused (longer, more context)
target_chunk_tokens = 500
min_chunk_tokens = 150
max_chunk_tokens = 800
```

Then re-validate to see impact:

```bash
python cli.py validate --version kjv --verses-csv ./data/kjv.csv
```

### Programmatic Access

Use Prism API directly for advanced queries:

```bash
# JSONB metadata query (all Psalms)
curl -X POST http://localhost:8100/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "praise the Lord",
    "filter": {"metadata.book": "Psalms"},
    "domain": "bible/kjv",
    "top_k": 10
  }'

# Testament filter
curl -X POST http://localhost:8100/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "law and commandments",
    "filter": {"metadata.testament": "OT"},
    "domain": "bible/kjv",
    "top_k": 10
  }'
```

### Bulk Export

Export all Bible documents:

```bash
curl "http://localhost:8100/api/v1/corpus/export?limit=5000" > kjv_export.json
```

Use case: Backup or migration to another system.

## Roadmap

### Phase 1: Foundation (Complete)
- ✅ CSV parser
- ✅ Adaptive verse chunking
- ✅ Prism integration
- ✅ KJV full import
- ✅ Semantic search

### Phase 2: Multi-Version (Next)
- Import NIV, ESV, NASB
- Test cross-version search
- Add language metadata
- Compare translation differences

### Phase 3: MCP Server (Future)
- Implement MCP tools (search, get_passage, etc.)
- Add context reconstruction
- Build cross-reference discovery
- Package as standalone server

### Phase 4: Enhanced Metadata (Future)
- Strong's concordance integration
- Cross-reference tables
- Topic tagging
- Original language lemmas

## Resources

- **Prism Documentation**: `/dpool/aiml-stack/prism/README.md`
- **Importer Code**: `/dpool/aiml-stack/scripts/bible-importer/`
- **Data Source**: https://github.com/scrollmapper/bible_databases
- **tiktoken**: https://github.com/openai/tiktoken
- **MCP Protocol**: https://github.com/anthropics/mcp

## Support

For issues or questions:
1. Check Prism logs: `docker compose logs -f prism`
2. Verify Ollama status: `docker compose ps ollama`
3. Test API health: `curl http://localhost:8100/health`
4. Review validation output: `python cli.py validate --version kjv --verses-csv ...`

---

**Last Updated**: 2026-02-07
**Version**: 0.1.0
**Status**: Production-ready for KJV, extensible to 140+ translations
