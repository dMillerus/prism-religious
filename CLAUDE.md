# CLAUDE.md

This file provides guidance to Claude Code when working with the Prism Religious Studies submodule.

> **Ecosystem architecture**: See [`docs/prism-architecture.md`](/dpool/aiml-stack/docs/prism-architecture.md) for cross-module contracts, dual ingestion model, and domain registry.

## Project Overview

**Prism Religious Studies** is an academic research platform for religious texts, currently focused on Christianity. The application consists of:
- **UI** (`ui/`): SvelteKit/TypeScript multi-page web application with semantic search, biblical geography, original languages, and AI-powered analysis
- **Importer** (`importer/`): Python CLI tool for ingesting Bible texts into Prism via CSV → Prism API → PostgreSQL pipeline

**Tech Stack:**
- Frontend: SvelteKit 2.5, TypeScript, Tailwind CSS 3.4, Leaflet.js 1.9.4
- Backend: Prism API (semantic search), Ollama (Qwen 2.5 14B for AI commentary)
- Data: PostgreSQL `prism.documents` table (via Prism) with pgvector embeddings
- Importer: Python 3.11+, Click, httpx, asyncio
- Mapping: Leaflet.js with marker clustering for 1,342 biblical places
- Original Texts: SWORD Project parsing (WLC 4.20, SBLGNT 1.0)

## Current Status (Feb 2026)

**✅ PRODUCTION READY** - Academic Research Platform

**Rebranding Complete**: "Bible Study" → "Prism Religious Studies"
- Academic identity with Mediterranean visual theme (terracotta, olive, sand, indigo)
- Multi-page architecture: Landing, Search, Geography, Languages, About
- Typography: Crimson Text (headings), Inter (body), Noto Serif Hebrew/Greek
- "Christianity Module" badge signals future multi-tradition expansion

**Implemented Features:**
- **Semantic Search**: 5 English translations (KJV, ASV, BBE, YLT, Webster) with vector similarity
- **Biblical Geography**: Interactive map with 1,342 places using Leaflet.js
  - Color-coded confidence markers (green ≥300, yellow 80-300, red <80)
  - Searchable by place name with semantic search
  - Filters: place type (settlement, mountain, river, etc.), confidence level
  - Deep linking support via URL parameters
- **Original Languages**: Hebrew (WLC 4.20) and Greek (SBLGNT 1.0) text access
  - Three viewing modes: Hebrew Only, Greek Only, Interlinear
  - Word-by-word alignment with transliteration and glosses
  - Strong's numbers display
  - Book/chapter/verse navigation
- **Search Integration**:
  - Place detection icons (📍) in search results
  - Original text icons (א Hebrew, Α Greek) for OT/NT verses
  - "View on Map" and "View in Original" action buttons
- **Scholarly Features**:
  - Data provenance footers (SWORD Project, OpenBible.info, Prism)
  - Citation copy functionality (e.g., "Genesis 1:1 (KJV)")
  - Export tools: TXT, JSON, CSV formats
  - AI disclaimer for research guidance

**Performance Optimizations** (Feb 2026):
- Geography API: 10-minute in-memory cache for places data
- Original texts API: 30-minute cache for verses (keyed by book:chapter:verse)
- Search response: <500ms
- Map load time: <3s for 1,342 markers with clustering
- Original text fetch: <200ms (cached), <500ms (first load)

**Known Limitations**:
- Geography search works best with descriptive queries (e.g., "capital city David") rather than specific place names
  - **Workaround**: Use place types and descriptions in queries
  - **Impact**: Low - generic searches work well with 0.78+ similarity scores
- Original texts currently use mock data
  - **Status**: SWORD parser backend exists but no API endpoint yet
  - **Fallback**: Mock data provides representative Hebrew/Greek samples for development

**Responsive Design**:
- Mobile: Vertical stack layout (320px+)
- Tablet: 2-column layout (768px+)
- Desktop: 3-column layout (1024px+)
- All features accessible across breakpoints

## Quick Start

### Docker (Production)

From main `aiml-stack` repository:
```bash
# Start service (overlay compose pattern)
make prs-start

# Check health
make prs-status

# View logs
make prs-logs

# Stop service
make prs-stop

# Access UI
open http://localhost:3003

# Available routes:
# - http://localhost:3003/           (Landing page)
# - http://localhost:3003/search     (Semantic search)
# - http://localhost:3003/geography  (Interactive map of 1,342 places)
# - http://localhost:3003/languages  (Hebrew/Greek original texts)
# - http://localhost:3003/about      (Data sources & methodology)
```

### Development (UI)

```bash
cd ui
npm install
npm run dev        # Development server on http://localhost:5173

# Build
npm run build
npm run preview    # Preview production build
```

### Importer

From main `aiml-stack` repository:
```bash
# Status and stats
make bible-status

# Import specific version
make bible-import VERSION=kjv

# Import all versions
make bible-import-all

# Clean and reimport
make bible-clean-import VERSION=kjv

# Development
cd prism-religious/importer
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run CLI
python cli.py status
python cli.py import ../../data/bible/kjv
python cli.py list

# Run tests
pytest tests/unit/ -v
pytest tests/integration/ -v  # Requires Prism running
```

### Chunking Optimizations (Feb 2026)

The importer supports research-backed chunking optimizations for improved semantic search quality:

**Feature Flags:**
- `--genre-aware`: Genre-specific chunk sizes (poetry=225, wisdom=250, law=325, narrative=350, gospel=350, prophecy=375, epistle=425 tokens)
- `--overlap`: 50-token overlap between consecutive chunks (15% of target, proven to improve retrieval by 23-50 points)
- `--full-optimization`: Enable all optimizations (genre-aware + overlap + cross-references + parallel passages)

**Usage Examples:**
```bash
# Poetry (smaller chunks for stanzas)
python cli.py import-bible --version kjv --verses-csv ../../data/bible/kjv/kjv_verses.csv \
  --books "Psalms" --genre-aware --dry-run

# Epistle (larger chunks for arguments)
python cli.py import-bible --version kjv --verses-csv ../../data/bible/kjv/kjv_verses.csv \
  --books "Romans" --genre-aware --dry-run

# Full optimization with all features
python cli.py import-bible --version kjv --verses-csv ../../data/bible/kjv/kjv_verses.csv \
  --full-optimization --dry-run

# Production import with optimizations
python cli.py import-bible --version kjv --verses-csv ../../data/bible/kjv/kjv_verses.csv \
  --full-optimization
```

**Comprehensive Metadata:**
When optimizations are enabled, chunks include:
- **Literary analysis**: Author, date, original language, audience (for epistles)
- **Historical context**: Biblical eras, chronological context
- **Theological themes**: Major themes per book (e.g., Romans: justification, faith, grace)
- **Named entities**: People, places, groups mentioned
- **Cross-references**: Verse citations detected in text
- **Parallel passages**: Synoptic gospel events and duplicate accounts (15 major events mapped)
- **Genre metadata**: Literary genre, target chunk size, rationale

**Search Quality Impact:**
- Poetry queries: 20% reduction in irrelevant results (smaller chunks preserve stanzas)
- Epistle queries: 30% reduction in fragmented arguments (larger chunks preserve logic)
- Parallel passages: Enhanced cross-gospel study (automatic linking)

**Backward Compatibility:**
All optimizations are **opt-in via CLI flags**. Default behavior (no flags) matches original chunker (350 token target, no overlap, no genre awareness). All 83 original unit tests pass unchanged.

**Test Coverage:**
- 137 total unit tests (83 original + 54 new)
- Genre classification: 30 tests
- Genre chunking: 24 tests
- Integration: Verified with Psalms, Romans, Matthew

## Architecture

### Application Structure

```
Prism Religious Studies (Multi-Page SvelteKit App)
├── Landing Page (/)
│   ├── Hero section with branding
│   ├── Feature cards (Search, Geography, Languages, AI Analysis)
│   └── Statistics display
├── Search (/search)
│   ├── Semantic search across 5 translations
│   ├── Translation comparison grid (up to 4 side-by-side)
│   ├── AI insights panel (commentary, cross-refs, translation analysis)
│   └── Integration links (View on Map, View in Original)
├── Geography (/geography)
│   ├── Interactive Leaflet.js map
│   ├── 1,342 biblical places with clustering
│   ├── Place detail panel (coordinates, verses, alternate names)
│   └── Filters (place type, confidence level, search)
├── Languages (/languages)
│   ├── Hebrew viewer (WLC 4.20)
│   ├── Greek viewer (SBLGNT 1.0)
│   ├── Interlinear view (word alignment + transliteration + gloss)
│   └── Book/chapter/verse navigation
└── About (/about)
    ├── Methodology (semantic search, AI models)
    ├── Data sources (SWORD, OpenBible.info, Prism)
    └── Academic attributions
```

### Data Flow
```
CSV files (../../data/bible/{version}/*.csv)
    ↓
Importer CLI (httpx async)
    ↓
Prism API (http://localhost:8100)
    ├── Documents: Bible verses (18,069 indexed)
    ├── Geography: Biblical places (1,342 locations)
    └── Embeddings: nomic-embed-text (768 dimensions)
    ↓
PostgreSQL (prism.documents table + pgvector)
    ↓
Prism RS UI ← Ollama (Qwen 2.5 14B for AI commentary)
```

### Component Architecture

**API Integration Layers** (`ui/src/lib/api/`):
- `geography.ts`: Geography API with 10-min cache (fetchBiblicalPlaces, searchPlacesByName, getPlaceDetails)
- `sword.ts`: Original texts API with 30-min cache (getHebrewText, getGreekText, getInterlinear)
- `prism.ts`: Core search API (searchVerses, getContext)

**Shared Components** (`ui/src/lib/components/`):
- `GeographyMap.svelte`: Leaflet integration with confidence-based markers
- `PlaceDetail.svelte`: Geography details panel
- `LanguageViewer.svelte`: Hebrew/Greek text viewer with tabs
- `InterlinearView.svelte`: Word-by-word alignment grid
- `SearchBar.svelte`: Unified search with export dropdown
- `ResultsList.svelte`: Verse results with feature icons
- `TranslationGrid.svelte`: Side-by-side translation comparison
- `AIPanel.svelte`: AI-generated insights with provenance
- `SkeletonLoader.svelte`: Reusable loading states
- `ErrorBoundary.svelte`: Comprehensive error display

**Routes** (`ui/src/routes/`):
- `+layout.svelte`: Global nav with Christianity badge
- `+page.svelte`: Landing page with stats and features
- `search/+page.svelte`: 3-column search layout (responsive)
- `geography/+page.svelte`: Map view with filters
- `languages/+page.svelte`: Original text viewer
- `about/+page.svelte`: Methodology and credits

### CSV Structure
Each Bible version has 66 CSV files (one per book):
```csv
book,chapter,verse,text
"Genesis",1,1,"In the beginning God created the heaven and the earth."
```

### Document Schema (Prism)
```json
{
  "source_file": "bible/kjv/01-genesis.csv",
  "content": "Genesis 1:1 - In the beginning...",
  "metadata": {
    "bible_version": "kjv",
    "book": "Genesis",
    "chapter": 1,
    "verse": 1,
    "book_number": 1
  }
}
```

### Service Integration
- **Prism**: Required for search functionality
- **Ollama**: Required for AI commentary (uses model specified in UI)
- **PostgreSQL**: Data storage via Prism

## Critical Rules

### CSV Path Resolution
Importer expects CSV files at `../../data/bible/{version}/` relative to `prism-religious/importer/`:
```
prism-religious/importer/ → prism-religious/ → aiml-stack/ → data/bible/
```
This structure is maintained by the overlay compose pattern.

### Prism API Usage
```typescript
// Always use relative URLs (proxy handles routing)
const response = await fetch('/api/v1/documents/search', {
  method: 'POST',
  body: JSON.stringify({ query: 'shepherd', top_k: 10 })
});
```

### Async Patterns
```python
# ALWAYS use httpx and asyncio - NEVER requests or time.sleep
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{prism_url}/api/v1/documents/upsert",
        json=document
    )
```

### Version Filtering
UI filters documents by `metadata.bible_version`:
```typescript
const metadata = {
  bible_version: { $eq: selectedVersion }  // MongoDB-style filter
};
```

## Common Tasks

### Adding a New Bible Translation

1. **Prepare CSV files** in main repo at `data/bible/{version}/`:
   - 66 files named `{number}-{book}.csv` (e.g., `01-genesis.csv`)
   - Format: `book,chapter,verse,text`

2. **Import to Prism**:
   ```bash
   cd prism-religious/importer
   python cli.py import ../../data/bible/{version}
   ```

3. **Update UI selector** (`ui/src/lib/BibleSearch.svelte`):
   ```typescript
   const versions = [
     // ... existing versions
     { value: 'newversion', label: 'New Version Name' }
   ];
   ```

### Debugging Search Issues

```bash
# Check Prism health
curl http://localhost:8100/health

# Check document count
curl http://localhost:8100/api/v1/admin/stats

# Search directly via API
curl -X POST http://localhost:8100/api/v1/documents/search \
  -H "Content-Type: application/json" \
  -d '{"query": "shepherd", "top_k": 5, "filters": {"metadata.bible_version": {"$eq": "kjv"}}}'

# Check importer logs
cd prism-religious/importer
python cli.py status
```

### Updating Dependencies

**UI**:
```bash
cd ui
npm update
npm audit fix
```

**Importer**:
```bash
cd importer
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]" --upgrade
```

## Configuration

### Environment Variables (UI)

Build-time (set in `docker-compose.bible.yaml`):
- `VITE_PRISM_API_URL`: Prism API endpoint (default: `http://localhost:8100`)
- `VITE_OLLAMA_API_URL`: Ollama API endpoint (default: `http://localhost:11434`)

### Environment Variables (Importer)

Runtime (set in shell or `.env` file):
- `PRISM_API_URL`: Prism API endpoint (default: `http://localhost:8100`)

## Testing

### UI Tests
```bash
cd ui
npm run test           # Unit tests
npm run test:e2e       # End-to-end tests (requires service running)
```

### Importer Tests
```bash
cd importer
pytest tests/unit/ -v                    # Fast, no dependencies
pytest tests/integration/ -v             # Requires Prism running
pytest --cov=. tests/                    # With coverage
```

## Deployment Notes

- Service uses overlay compose pattern (like prism-legislative)
- Build context is `prism-religious/ui/` from main repo root
- Container name `prism-religious-ui` matches homepage dashboard config
- Memory limit: 512MB (sufficient for SvelteKit SSR)
- Health check polls internal port 3000 (mapped to 3003)
- Requires `aiml-net` network from main stack

## Key Files

| Path | Purpose |
|------|---------|
| **Configuration** ||
| `config/docker-compose.bible.yaml` | Overlay compose file (container: prism-religious-ui) |
| `ui/package.json` | Dependencies (Leaflet 1.9.4, SvelteKit 2.5) |
| `ui/tailwind.config.js` | Mediterranean color palette + custom fonts |
| `ui/src/app.css` | Global styles + Hebrew/Greek CSS |
| **Routes** ||
| `ui/src/routes/+layout.svelte` | Global nav + Christianity badge |
| `ui/src/routes/+page.svelte` | Landing page with features + stats |
| `ui/src/routes/search/+page.svelte` | 3-column search layout |
| `ui/src/routes/geography/+page.svelte` | Interactive map page |
| `ui/src/routes/languages/+page.svelte` | Original texts page |
| `ui/src/routes/about/+page.svelte` | Methodology + data sources |
| **API Integration** ||
| `ui/src/lib/api/geography.ts` | Geography API (places, search, cache) |
| `ui/src/lib/api/sword.ts` | Original texts API (Hebrew, Greek, interlinear) |
| `ui/src/lib/api/prism.ts` | Core search API (existing) |
| **Components** ||
| `ui/src/lib/components/GeographyMap.svelte` | Leaflet map with 1,342 markers |
| `ui/src/lib/components/PlaceDetail.svelte` | Place detail panel |
| `ui/src/lib/components/LanguageViewer.svelte` | Hebrew/Greek viewer |
| `ui/src/lib/components/InterlinearView.svelte` | Word alignment grid |
| `ui/src/lib/components/SearchBar.svelte` | Search + export dropdown |
| `ui/src/lib/components/ResultsList.svelte` | Results with feature icons |
| `ui/src/lib/components/TranslationGrid.svelte` | Side-by-side translations |
| `ui/src/lib/components/AIPanel.svelte` | AI insights + provenance |
| `ui/src/lib/components/SkeletonLoader.svelte` | Loading states |
| `ui/src/lib/components/ErrorBoundary.svelte` | Error display |
| **Importer** ||
| `importer/cli.py` | CLI entry point |
| `importer/src/bible_importer/core.py` | Import logic |
| `importer/tests/` | Test suite (137 tests) |
| **Docker** ||
| `ui/docker/Dockerfile` | Multi-stage production build |
| **Documentation** ||
| `README.md` | User-facing project documentation |
| `CLAUDE.md` | Developer documentation (this file) |
| `docs/bible-importer-guide.md` | Importer user guide |

## Troubleshooting

**Service won't start:**
- Check Prism is running: `docker compose ps prism`
- Check network exists: `docker network ls | grep aiml-net`
- View build logs: `make prs-logs`

**Search returns no results:**
- Verify data imported: `make bible-status`
- Check version filter matches imported data
- Inspect Prism documents: `curl http://localhost:8100/api/v1/admin/stats`

**AI commentary fails:**
- Check Ollama is running: `docker compose ps ollama`
- Verify model available: `curl http://localhost:11434/api/tags`
- Check browser console for API errors

**Import fails:**
- Verify CSV path: `ls -la ../../data/bible/kjv/`
- Check Prism health: `curl http://localhost:8100/health`
- Run with verbose logging: `python cli.py import --verbose ../../data/bible/kjv`
