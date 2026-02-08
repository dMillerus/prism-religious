# Bible Importer Test Suite

Comprehensive test suite for the Bible text ingestion system covering unit tests, integration tests, search quality validation, and regression prevention.

## Test Overview

**Total Tests: 117**
- **Unit Tests: 83** (no external dependencies)
- **Integration Tests: 34** (requires Prism API)

## Test Categories

### Unit Tests (`tests/unit/`)

Fast, isolated tests that run without external dependencies. Use mocked HTTP responses.

- **test_csv_parser.py** (23 tests): CSV parsing, verse validation, book grouping
- **test_verse_chunker.py** (25 tests): Token-aware chunking, boundary logic, metadata generation
- **test_prism_client.py** (18 tests): HTTP client with mocked responses, batch imports
- **test_config.py** (10 tests): Pydantic settings validation, environment overrides
- **test_cli.py** (7 tests): Click command parsing and validation

### Integration Tests (`tests/integration/`)

End-to-end tests requiring a running Prism instance. Test real search functionality.

- **test_search_e2e.py** (12 tests): Basic search, domain filtering, response structure, performance
- **test_search_quality.py** (11 tests): Famous passages (Psalm 23, John 3:16, Genesis), concept search, similarity thresholds
- **test_regression.py** (11 tests): Translation availability, domain isolation, data integrity, consistency

## Running Tests

### Quick Start

```bash
# Setup (one-time)
cd /dpool/aiml-stack/scripts/bible-importer
source .venv/bin/activate
pip install -e ".[dev]"

# Run all tests
pytest tests/

# Run only unit tests (fast, no Prism needed)
pytest tests/unit/ -v

# Run only integration tests (requires Prism)
docker compose up -d prism
pytest tests/integration/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing
```

### Test Markers

Tests are marked for selective execution:

```bash
# Run only unit tests (no external deps)
pytest -m unit

# Run only integration tests
pytest -m integration

# Run fast tests only
pytest -m "not slow"
```

### Continuous Integration

```bash
# Pre-commit: unit tests only (fast)
pytest tests/unit/ -q

# PR validation: all tests
pytest tests/ -v

# Nightly: full suite with coverage
pytest tests/ --cov=. --cov-report=html
```

## Test Requirements

### Unit Tests
- **Dependencies**: pytest, pytest-asyncio, httpx (mocked)
- **Runtime**: ~2 seconds
- **External Services**: None

### Integration Tests
- **Dependencies**: pytest, pytest-asyncio, httpx, running Prism
- **Runtime**: ~3-4 seconds
- **External Services**: Prism API (http://localhost:8100)
- **Data**: Bible translations imported (KJV, ASV, BBE, YLT, Webster)

## Test Fixtures

### Shared Fixtures (`conftest.py`)

- `sample_verses_csv_path`: Path to Genesis 1, Psalm 23, John 3 sample data
- `genesis_1_verses`: Parsed Genesis 1:1-5 verses
- `psalm_23_verses`: Parsed Psalm 23 (short chapter)
- `john_3_verses`: Parsed John 3:16-17
- `mixed_chapter_verses`: Multi-chapter test data
- `famous_passages`: Dict of well-known passages for quality tests
- `mock_httpx_client`: AsyncMock for unit tests
- `mock_prism_client`: Mocked PrismClient (no HTTP calls)
- `prism_test_client`: Real PrismClient for integration tests
- `test_settings`: Safe test configuration
- `oversized_verse`: Verse exceeding max tokens

## Success Criteria

### Unit Tests
- ✅ All modules tested in isolation
- ✅ 83 tests covering core functionality
- ✅ Fast execution (<10 seconds)
- ✅ No external dependencies

### Integration Tests
- ✅ Search works end-to-end with real Prism
- ✅ All 5 translations searchable independently
- ✅ Cross-version search returns multiple translations
- ✅ Domain filtering isolates specific versions
- ✅ Famous passages found with good similarity (>0.70)
- ✅ Concept searches return relevant results
- ✅ Search results deterministic and consistent

### Regression Prevention
- ✅ All translations searchable (kjv, asv, bbe, ylt, webster)
- ✅ Domain isolation verified
- ✅ Data integrity maintained (verse numbers, no duplicates)
- ✅ Special characters handled gracefully

## Key Test Files

### Most Critical Tests
1. **test_verse_chunker.py**: Chunking algorithm (most complex core logic)
2. **test_search_quality.py**: Search quality validation (user-facing)
3. **test_csv_parser.py**: Data integrity (foundation)
4. **test_regression.py**: Prevents known issues

### Sample Test Commands

```bash
# Test chunking algorithm
pytest tests/unit/test_verse_chunker.py -v

# Test search quality
pytest tests/integration/test_search_quality.py -v

# Test specific famous passage
pytest tests/integration/test_search_quality.py::TestSearchQuality::test_search_psalm_23 -v

# Test domain isolation
pytest tests/integration/test_regression.py::TestRegressionPrevention::test_domain_isolation -v
```

## Troubleshooting

### Integration Tests Skipped

If integration tests are skipped with "Prism API not accessible":

```bash
# Check Prism is running
docker compose ps prism

# Start Prism if needed
docker compose up -d prism

# Wait for healthy status
docker compose ps prism  # Should show "healthy"

# Test health check
curl http://localhost:8100/health
```

### Low Similarity Scores

Search quality tests may occasionally fail if:
- Different Bible translations have varying text
- Embedding model differences
- Query phrasing variations

Adjust thresholds in `test_search_quality.py` if needed:
- Exact matches: >0.80 similarity
- Famous passages: >0.70 similarity
- Concept searches: >0.60 similarity

### Test Failures

```bash
# Run with verbose output
pytest tests/integration/test_search_quality.py -vv

# Run with full traceback
pytest tests/ --tb=long

# Run single test with debugging
pytest tests/unit/test_verse_chunker.py::TestChunkBoundaries::test_chunk_never_spans_chapters -vv --pdb
```

## Maintenance

### Adding New Tests

When adding features, follow this pattern:

1. **Unit test first**: Test new function in isolation
2. **Integration test**: Test with real Prism if search-related
3. **Regression test**: Add to `test_regression.py` if fixing a bug

### Updating Tests

- **New translation added**: Add to `test_regression.py` domain list
- **Chunking logic changed**: Update `test_verse_chunker.py` expectations
- **Prism API changed**: Update `test_prism_client.py` mocks
- **Search quality degraded**: Add failing case to `test_search_quality.py`

### Test Performance

Monitor test execution time:

```bash
# Show slowest tests
pytest tests/ --durations=10

# Run in parallel (if needed)
pytest tests/unit/ -n auto
```

## Coverage Goals

- **Overall**: >80% code coverage
- **Critical modules**: >90% coverage
  - `verse_chunker.py`
  - `csv_parser.py`
  - `prism_client.py`

```bash
# Generate coverage report
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run unit tests
  run: |
    cd scripts/bible-importer
    pytest tests/unit/ -v

- name: Start Prism
  run: docker compose up -d prism

- name: Run integration tests
  run: |
    cd scripts/bible-importer
    pytest tests/integration/ -v
```

### Pre-commit Hook

```bash
#!/bin/bash
# Run fast unit tests before commit
cd scripts/bible-importer
source .venv/bin/activate
pytest tests/unit/ -q || exit 1
```

## Test Data

### Sample Fixtures
- **Genesis 1:1-5**: Creation narrative (long verses)
- **Psalm 23**: Complete short chapter (~180 tokens)
- **John 3:16-17**: Famous NT passage

### Famous Passages
- Psalm 23:1 - "The Lord is my shepherd"
- John 3:16 - "For God so loved the world"
- Genesis 1:1 - "In the beginning God created"

## Related Documentation

- [Bible Importer README](../README.md) - Project overview
- [CLAUDE.md](../../CLAUDE.md) - Development guidelines
- [Prism Documentation](../../prism/README.md) - Search API details
