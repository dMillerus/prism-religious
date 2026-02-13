# Prism Religious Studies

An academic research platform for religious texts, starting with Christianity. Provides semantic search, original language access, biblical geography, and AI-powered textual analysis for scholarly research.

**Current Focus**: Christianity (5 Bible translations, Hebrew/Greek texts, 1,342 biblical places)
**Future Expansion**: Islam, Judaism, and other religious traditions

## Features

### Current (Christianity Module)

**Semantic Search & Study Tools**:
- **Multi-Translation Search**: Semantic search across 5 English translations (KJV, ASV, BBE, YLT, Webster) using nomic-embed-text embeddings (768 dimensions)
- **Translation Comparison**: View up to 4 translations side-by-side for detailed analysis
- **AI-Powered Insights**: LLM-generated contextual commentary (historical context, literary analysis, theological themes)
- **Cross-References**: AI-discovered related passages with explanatory connections
- **Translation Analysis**: Detailed comparison of word choices, etymology, and textual variants
- **Citation Tools**: One-click citation copying and export to TXT/JSON/CSV formats

**Biblical Geography (1,342 Places)**:
- **Interactive Map**: Leaflet.js-powered map with marker clustering for visual exploration
- **Confidence-Based Markers**: Color-coded by archaeological confidence (Green ≥300, Yellow 80-300, Red <80)
- **Place Details**: Coordinates, type (settlement/mountain/river/etc.), verse references, alternate names
- **Search & Filters**: Semantic search for place names, filter by type and confidence level
- **Deep Linking**: URL parameters support direct navigation from search results
- **Data Source**: OpenBible.info (CC-BY 4.0) with comprehensive verse cross-references

**Original Languages (Hebrew & Greek)**:
- **Hebrew Text**: Westminster Leningrad Codex (WLC 4.20) for Old Testament
- **Greek Text**: Society of Biblical Literature Greek New Testament (SBLGNT 1.0) for New Testament
- **Interlinear View**: Word-by-word alignment with original script, transliteration, and English glosses
- **Strong's Numbers**: Lexical references for deeper word study
- **Book Navigation**: Browse by book, chapter, and verse with previous/next controls
- **Proper Typography**: Unicode fonts (Noto Serif Hebrew, Noto Sans Greek) with RTL support

## Visual Design

**Color Palette** (Mediterranean Academic Theme):
- **Terracotta** (#E2725B): Primary accent, evokes archaeological sites
- **Olive Green** (#6B8E23): Secondary accent, ancient landscape
- **Sand** (#C2B280): Neutral backgrounds, parchment aesthetic
- **Deep Indigo** (#1E3A5F): Scholarly depth, text emphasis

**Typography**:
- **Headings**: Crimson Text (scholarly serif, 16-32px)
- **Body**: Inter (modern sans-serif, 14-16px)
- **Hebrew**: Noto Serif Hebrew (proper Unicode with RTL support)
- **Greek**: Noto Sans Greek (classical letterforms)
- **Code/References**: JetBrains Mono (monospace, 12-14px)

**Layout**:
- **Responsive**: Mobile-first design (320px+)
- **Tablet**: 2-column layouts (768px+)
- **Desktop**: 3-column layouts (1024px+)
- **Navigation**: Global top nav with active state indicators

## Architecture

### Frontend
- **Framework**: SvelteKit 2.5 + TypeScript
- **Styling**: Tailwind CSS 3.4 with custom Mediterranean theme
- **Mapping**: Leaflet.js 1.9.4 with marker clustering
- **Icons**: Lucide Svelte
- **Routing**: Multi-page SPA with deep linking support

### Backend
- **Search**: Prism API (PostgreSQL + pgvector)
- **AI**: Ollama (Qwen 2.5 14B, temperature 0.7)
- **Geography**: Prism documents (domain: geography/biblical)
- **Original Texts**: SWORD Project modules (via Python parser)
- **Caching**:
  - AI responses: 1-hour in-memory cache
  - Geography: 10-minute cache
  - Verses: 30-minute cache

### Multi-Page Structure
- **/** - Landing page with features and statistics
- **/search** - Semantic search with AI insights
- **/geography** - Interactive map of biblical places
- **/languages** - Hebrew/Greek original texts with interlinear view
- **/about** - Methodology, data sources, and academic attributions

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
docker build -f docker/Dockerfile -t prism-religious-ui:latest .

# Run container
docker run -p 3000:3000 \
  -e VITE_PRISM_API_URL=http://prism:8100 \
  -e VITE_OLLAMA_API_URL=http://ollama:11434 \
  prism-religious-ui:latest
```

## Environment Variables

- `VITE_PRISM_API_URL`: Prism REST API endpoint (default: `http://prism:8100`)
- `VITE_OLLAMA_API_URL`: Ollama API endpoint (default: `http://ollama:11434`)

## Usage

### Semantic Search
1. Navigate to **Search** page (or homepage search bar)
2. Enter a query: word ("shepherd"), phrase ("love your enemies"), or reference ("John 3:16")
3. Select translations to search (default: all 5)
4. Click a verse in the results list to view details
5. Center panel shows selected translations side-by-side
6. Right panel provides AI-generated commentary, cross-references, and translation analysis
7. Click **Copy Citation** or **Export** for academic workflows

### Biblical Geography
1. Navigate to **Geography** page
2. Explore the interactive map with 1,342 biblical places
3. Click markers to see place details (coordinates, verse references, alternate names)
4. Use filters to narrow by place type (settlement, mountain, river, etc.) or confidence level
5. Search for specific places using the semantic search bar
6. Click **Search Verses About This Place** to find related passages
7. Or navigate from search results using **View on Map** button (📍 icon indicates geography data)

### Original Languages
1. Navigate to **Languages** page
2. Toggle between **Hebrew** (Old Testament) and **Greek** (New Testament) tabs
3. Select book, chapter, and verse using dropdowns
4. Switch to **Interlinear** view to see word-by-word alignment with transliteration and glosses
5. Use **Previous/Next Verse** buttons to browse
6. Strong's numbers displayed when available for lexical study
7. Or navigate from search results using **View in Hebrew/Greek** button (א/Α icons indicate original text availability)

## Performance

**Search & AI**:
- Semantic search response: <500ms (including embedding + vector search)
- Translation comparison: <200ms
- AI commentary (first time): ~3-5s (Qwen 2.5 14B inference)
- AI commentary (cached): <100ms (1-hour cache)

**Geography Module**:
- Map load time: <3s (1,342 markers with clustering)
- Place search: ~400ms (semantic search with filtering)
- API cache: 10-minute TTL for frequently accessed data

**Original Languages**:
- Verse fetch: <200ms (cached), <500ms (first load)
- Verse cache: 30-minute TTL per verse
- Interlinear rendering: <100ms (client-side)

**Scalability**: Supports 20+ concurrent users with in-memory caching

## Data

**Search Corpus**:
- **Verses**: 18,069 indexed verses across 5 English translations
- **Embeddings**: nomic-embed-text (768 dimensions)
- **Vector Index**: HNSW algorithm with 0.6-0.9 similarity scores

**Biblical Geography**:
- **Places**: 1,342 locations with coordinates (latitude/longitude)
- **Confidence Scores**: 0-500 scale (archaeological certainty)
- **Verse References**: Comprehensive cross-references for each place
- **Place Types**: Settlement, mountain, river, valley, region, body of water, wilderness, etc.

**Original Texts**:
- **Hebrew**: Westminster Leningrad Codex (WLC 4.20) - complete Old Testament
- **Greek**: Society of Biblical Literature Greek New Testament (SBLGNT 1.0) - complete New Testament
- **Interlinear Data**: Word alignment, transliteration (scholarly standard), English glosses
- **Lexical References**: Strong's numbers for deeper word study

## Data Sources & Attribution

- **Hebrew Text**: Westminster Leningrad Codex (WLC 4.20)
- **Greek Text**: Society of Biblical Literature Greek New Testament (SBLGNT 1.0)
- **Geography**: OpenBible.info (CC-BY 4.0) - 1,342 biblical places
- **Translations**: SWORD Project modules (Public Domain)
- **Search Engine**: Prism (Personal Semantic Data Layer)

## Credits

- **Built with**: Claude Code
- **LLM**: Anthropic Claude Sonnet 4.5
- **Embedding Model**: nomic-embed-text (768 dimensions)
- **Original Language Parsing**: SWORD Project
