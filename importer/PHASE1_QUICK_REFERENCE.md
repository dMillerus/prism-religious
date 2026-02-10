# Bible Study Phase 1 - Quick Reference

**Status**: ✅ OPERATIONAL (Feb 10, 2026)

## What Was Built

✅ **14,197 Strong's Lexicon entries** (Hebrew + Greek definitions)
✅ **66 Bible book metadata documents** (authors, themes, dates, genres)
✅ **100% embedding coverage** across all documents
✅ **Cross-domain RAG queries** working

## Quick Start

### Import Lexicon

```bash
cd /dpool/aiml-stack/bible-study/importer
source .venv/bin/activate
python cli.py import-lexicon
```

### Import Book Metadata

```bash
python cli.py export-book-metadata
```

### Test Search

```bash
# Search lexicon
python cli.py search --query "love charity compassion" --top-k 5

# Verify lexicon entries
python cli.py verify-lexicon --strong-ids H1,H157,G26,G2316
```

## RAG Query Examples

### Via Prism API

```bash
# Mixed-domain query (lexicon + verses + book metadata)
curl -X POST http://localhost:8100/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What does the Bible teach about love?", "top_k": 10}'

# Lexicon-specific
curl -X POST http://localhost:8100/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "redemption salvation deliverance", "domain": "lexicon/strongs", "top_k": 5}'

# Book metadata
curl -X POST http://localhost:8100/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Pauls letters about grace", "domain": "metadata/books", "top_k": 3}'
```

### Via MCP (Claude Code)

```
# In Claude Code conversation:
User: "Search my knowledge base for the Greek word for love"
Claude: [uses search-prism MCP tool]
→ Returns Strong's G26 (agape) with definition

User: "What are the major themes in the book of Romans?"
Claude: [uses search-prism with domain=metadata/books]
→ Returns Romans metadata with themes: justification, faith, grace, law, salvation
```

## Database Locations

| Domain | Count | Purpose |
|--------|-------|---------|
| `lexicon/strongs` | 14,197 | Hebrew/Greek word definitions |
| `metadata/books` | 66 | Book-level scholarly context |
| `bible/kjv` | 3,635 | King James verses |
| `bible/asv` | 3,637 | American Standard verses |
| `bible/bbe` | 3,641 | Basic English verses |
| `bible/ylt` | 3,947 | Young's Literal verses |
| `bible/webster` | 3,785 | Webster's verses |

## Common Tasks

### Check Status

```bash
curl http://localhost:8100/api/v1/admin/stats | jq '{docs: .total_documents, chunks: .total_chunks, embedded: .embedded_chunks}'
```

### Verify Specific Entry

```sql
-- Check H157 (love) exists
SELECT title, left(content, 100)
FROM prism.documents
WHERE domain = 'lexicon/strongs'
  AND metadata->>'strong_id' = 'H157';
```

### Run Integration Tests

```bash
python test_rag_integration.py
```

## Known Limitations

⚠️ **Single-word lexicon queries** may be filtered by similarity threshold
- Workaround: Use multi-word queries ("love charity" vs "love")

⚠️ **Original Hebrew/Greek text** not yet linked to verses
- Status: SWORD modules downloaded, parsing deferred to Phase 2

## File Locations

- **Lexicon Importer**: `lexicon_importer.py`
- **Book Metadata**: `book_metadata_exporter.py`
- **Integration Tests**: `test_rag_integration.py`
- **CLI**: `cli.py` (commands: import-lexicon, export-book-metadata, verify-lexicon)
- **Data**: `data_sources/strongs/` (lexicon), `data_sources/sword_modules/` (original texts)

## Next Steps (Phase 2)

1. Add biblical geography (300-700 locations with coordinates)
2. Parse SWORD modules for original Hebrew/Greek text
3. Link Strong's numbers to verses
4. Tune similarity thresholds based on production queries

## Support

- **Full Report**: `PHASE1_COMPLETION_REPORT.md`
- **Test Suite**: `test_rag_integration.py`
- **CLAUDE.md**: Main project documentation in parent directory
