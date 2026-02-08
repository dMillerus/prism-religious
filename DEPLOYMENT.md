# Bible Study UI - Deployment Guide

## Quick Start

The Bible Study UI is now deployed and accessible at **http://localhost:3003**

## What Was Deployed

### Phase 1: Core Search UI ✅ COMPLETE

A fully functional SvelteKit-based Bible study application with:

1. **Search Interface**
   - Semantic search across 5 English translations (KJV, ASV, BBE, YLT, Webster)
   - Real-time debounced search (500ms delay)
   - Translation filtering (select which versions to search)
   - Results sorted by similarity score (0-1.0)

2. **3-Panel Desktop Layout**
   - **Left Panel**: Results list with similarity scores
   - **Center Panel**: 4-column translation comparison (side-by-side)
   - **Right Panel**: AI insights (commentary, cross-refs, translation analysis)

3. **AI Features** (On-Demand)
   - **Commentary**: Historical, literary, theological, and practical context
   - **Cross-References**: AI-discovered related verses with explanations
   - **Translation Insights**: Analysis of differences between versions

4. **Caching System**
   - 1-hour TTL for LLM responses
   - Prevents redundant AI generation
   - Auto-cleanup of expired cache entries

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Browser (localhost:3003)                               │
│  ↓                                                      │
│  SvelteKit UI (Node.js 20)                             │
│  ├─ Search → Prism API (localhost:8100)                │
│  └─ AI Insights → Ollama (localhost:11434)             │
└─────────────────────────────────────────────────────────┘
```

## Service Configuration

### Docker Compose Entry
```yaml
bible-study:
  build: ./apps/bible-study
  ports: 127.0.0.1:3003:3000
  environment:
    - VITE_PRISM_API_URL=http://prism:8100
    - VITE_OLLAMA_API_URL=http://ollama:11434
  depends_on:
    - prism (healthy)
    - ollama (started)
  resources:
    limits: 1 CPU, 512MB RAM
```

### Health Check
```bash
# Check service status
docker compose ps bible-study

# View logs
docker compose logs -f bible-study

# Restart service
docker compose restart bible-study

# Rebuild after changes
docker compose build bible-study
docker compose up -d bible-study
```

## Homepage Dashboard

Added to control surface at **http://localhost:3000** under "Semantic Data" section:
- Icon: Book icon
- Link: http://localhost:3003
- Description: "Bible search with AI insights"
- Container: bible-study

## Usage

1. **Search**: Enter a query (e.g., "love", "shepherd", "John 3:16")
2. **Filter**: Select which translations to search (default: all 5)
3. **Select**: Click a verse in the results list
4. **Compare**: Center panel shows translations side-by-side
5. **AI Insights**: Right panel - click sections to generate:
   - Commentary (3-5s first time, <100ms cached)
   - Cross-References (find related verses)
   - Translation Differences (if multiple versions selected)

## Performance Metrics

- Search response: <500ms
- Translation comparison: <200ms
- AI commentary generation: 3-5s (first time)
- AI commentary retrieval: <100ms (cached)
- Page load: <2s cold, <500ms warm

## Data

- **Corpus**: 18,069 indexed verses
- **Translations**: 5 (KJV, ASV, BBE, YLT, Webster)
- **Embeddings**: nomic-embed-text (768 dimensions)
- **Similarity**: 0.6-0.9 typical range

## Development Workflow

### Local Development
```bash
cd apps/bible-study
npm install
npm run dev  # http://localhost:3000
```

### Build & Deploy
```bash
# From /dpool/aiml-stack
docker compose build bible-study
docker compose up -d bible-study
```

### Environment Variables
```bash
# .env file (already configured)
VITE_PRISM_API_URL=http://prism:8100
VITE_OLLAMA_API_URL=http://ollama:11434
```

## File Structure

```
apps/bible-study/
├── src/
│   ├── lib/
│   │   ├── api/
│   │   │   ├── prism.ts          # Prism API client
│   │   │   └── ollama.ts         # Ollama LLM client
│   │   ├── components/
│   │   │   ├── SearchBar.svelte
│   │   │   ├── ResultsList.svelte
│   │   │   ├── TranslationGrid.svelte
│   │   │   ├── AIPanel.svelte
│   │   │   ├── CommentarySection.svelte
│   │   │   ├── CrossRefSection.svelte
│   │   │   └── TranslationInsightsSection.svelte
│   │   ├── stores/
│   │   │   ├── search.ts         # Search state
│   │   │   ├── selection.ts      # Selected verse state
│   │   │   └── cache.ts          # LLM response cache
│   │   └── types/
│   │       └── bible.ts          # TypeScript interfaces
│   ├── routes/
│   │   ├── +page.svelte          # Main UI
│   │   └── +layout.svelte
│   ├── app.html
│   └── app.css
├── docker/
│   └── Dockerfile
├── package.json
├── svelte.config.js
├── vite.config.ts
├── tailwind.config.js
└── README.md
```

## Next Steps (Phase 2 & 3)

### Phase 2: Enhanced AI Features (Week 3-4)
- [ ] Thematic summary of all search results
- [ ] Streaming AI responses (SSE)
- [ ] Word study (etymology, Greek/Hebrew)
- [ ] Timeline/geography integration

### Phase 3: Study Tools (Week 5-6)
- [ ] Bookmarks (save favorite verses)
- [ ] Personal notes (markdown editor)
- [ ] Highlighting (color-code verses)
- [ ] Export (PDF, markdown, JSON)
- [ ] Reading plans

### Phase 4: Polish (Week 7)
- [ ] Keyboard shortcuts (Vim-style navigation)
- [ ] Dark mode toggle
- [ ] Accessibility improvements
- [ ] Performance optimization
- [ ] Mobile-responsive design

## Troubleshooting

### Service won't start
```bash
# Check dependencies
docker compose ps prism ollama

# Check logs
docker compose logs bible-study

# Restart dependencies
docker compose restart prism ollama
docker compose restart bible-study
```

### Search not working
```bash
# Verify Prism is healthy
curl http://localhost:8100/health

# Check Bible data is indexed
curl -X POST http://localhost:8100/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "love", "domain": "bible/kjv", "top_k": 1}'
```

### AI insights failing
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Verify model is available
docker exec ollama ollama list | grep qwen2.5

# Pull model if missing
docker exec ollama ollama pull qwen2.5:14b
```

### Port conflict
```bash
# Check if port 3003 is in use
lsof -i :3003

# Change port in compose.yaml if needed
ports:
  - "127.0.0.1:3004:3000"  # Changed from 3003
```

## Credits

- **Built with**: Claude Code (Anthropic)
- **LLM**: Claude Sonnet 4.5
- **Search**: Prism (Personal Semantic Data Layer)
- **AI Commentary**: Qwen 2.5 14B via Ollama
- **Frontend**: SvelteKit + Tailwind CSS
- **Data**: Public domain Bible translations

---

**Status**: ✅ Phase 1 Complete & Deployed
**Access**: http://localhost:3003
**Dashboard**: http://localhost:3000 (control surface)
