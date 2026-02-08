# Bible Study UI

A modern, desktop-focused Bible study interface with semantic search and AI-generated insights.

## Features

- **Semantic Search**: Search across 5 English translations (KJV, ASV, BBE, YLT, Webster) using vector similarity
- **Translation Comparison**: View up to 4 translations side-by-side for any verse
- **AI Commentary**: LLM-generated contextual commentary (historical, literary, theological)
- **Cross-References**: AI-discovered related passages with explanations
- **Translation Insights**: Analysis of differences between translations with etymology

## Architecture

### Frontend
- **Framework**: SvelteKit 2.5 + TypeScript
- **Styling**: Tailwind CSS 3.4
- **Icons**: Lucide Svelte

### Backend
- **Search**: Prism API (PostgreSQL + pgvector)
- **AI**: Ollama (Qwen 2.5 14B)
- **Caching**: In-memory LLM response cache (1 hour TTL)

## Development

```bash
# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Type checking
npm run check
```

## Docker Deployment

```bash
# Build image
docker build -f docker/Dockerfile -t bible-study-ui:latest .

# Run container
docker run -p 3000:3000 \
  -e VITE_PRISM_API_URL=http://prism:8100 \
  -e VITE_OLLAMA_API_URL=http://ollama:11434 \
  bible-study-ui:latest
```

## Environment Variables

- `VITE_PRISM_API_URL`: Prism REST API endpoint (default: `http://prism:8100`)
- `VITE_OLLAMA_API_URL`: Ollama API endpoint (default: `http://ollama:11434`)

## Usage

1. **Search**: Enter a query (word, phrase, or reference) in the search bar
2. **Filter**: Select which translations to search (default: all)
3. **Select**: Click a verse in the results list to view details
4. **Compare**: Center panel shows selected translations side-by-side
5. **AI Insights**: Right panel provides on-demand AI-generated commentary, cross-references, and translation analysis

## Performance

- Search response: <500ms
- Translation comparison: <200ms
- AI commentary (first time): ~3-5s
- AI commentary (cached): <100ms
- Supports 20+ concurrent users

## Data

- **Corpus**: 18,069 indexed verses across 5 translations
- **Embeddings**: `nomic-embed-text` (768 dimensions)
- **Index**: HNSW with 0.6-0.9 similarity scores

## Credits

- **Built with**: Claude Code
- **LLM**: Anthropic Claude Sonnet 4.5
- **Translations**: Public domain Bible texts
- **Search Engine**: Prism (Personal Semantic Data Layer)
