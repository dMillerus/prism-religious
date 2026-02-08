# CLAUDE.md

This file provides guidance to Claude Code when working with the bible-study submodule.

## Project Overview

**bible-study** is a semantic Bible search and AI-powered study application consisting of:
- **UI** (`ui/`): SvelteKit/TypeScript web interface with verse search, AI commentary, and cross-references
- **Importer** (`importer/`): Python CLI tool for ingesting Bible texts into Prism via CSV → Prism API → PostgreSQL pipeline

**Tech Stack:**
- Frontend: SvelteKit 2.x, TypeScript, Vite
- Backend: Prism API (semantic search), Ollama (AI commentary)
- Data: PostgreSQL `prism.documents` table (via Prism)
- Importer: Python 3.11+, Click, httpx, asyncio

## Quick Start

### Docker (Production)

From main `aiml-stack` repository:
```bash
# Start service (overlay compose pattern)
make bible-study-start

# Check health
make bible-study-status

# View logs
make bible-study-logs

# Stop service
make bible-study-stop

# Access UI
open http://localhost:3003
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
cd bible-study/importer
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

## Architecture

### Data Flow
```
CSV files (../../data/bible/{version}/*.csv)
    ↓
Importer CLI (httpx async)
    ↓
Prism API (http://localhost:8100)
    ↓
PostgreSQL (prism.documents table)
    ↓
Bible Study UI ← Ollama (AI commentary)
```

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
Importer expects CSV files at `../../data/bible/{version}/` relative to `bible-study/importer/`:
```
bible-study/importer/ → bible-study/ → aiml-stack/ → data/bible/
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
   cd bible-study/importer
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
cd bible-study/importer
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

- Service uses overlay compose pattern (like govarch)
- Build context is `bible-study/ui/` from main repo root
- Container name `bible-study` matches homepage dashboard config
- Memory limit: 512MB (sufficient for SvelteKit SSR)
- Health check polls internal port 3000 (mapped to 3003)
- Requires `aiml-net` network from main stack

## Key Files

| Path | Purpose |
|------|---------|
| `config/docker-compose.bible.yaml` | Overlay compose file |
| `ui/src/lib/BibleSearch.svelte` | Main search component |
| `ui/src/routes/+page.svelte` | Home page with search UI |
| `ui/docker/Dockerfile` | Multi-stage production build |
| `importer/cli.py` | CLI entry point |
| `importer/src/bible_importer/core.py` | Import logic |
| `importer/tests/` | Test suite (117 tests) |
| `docs/bible-importer-guide.md` | User documentation |

## Troubleshooting

**Service won't start:**
- Check Prism is running: `docker compose ps prism`
- Check network exists: `docker network ls | grep aiml-net`
- View build logs: `make bible-study-logs`

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
