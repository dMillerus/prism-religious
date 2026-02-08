# Bible Importer Testing - Quick Start

## TL;DR

```bash
# Setup (one-time)
cd /dpool/aiml-stack/scripts/bible-importer
source .venv/bin/activate
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Expected: ✅ 117 passed in ~3.5s
```

## Test Categories

### Unit Tests (83) - Fast, No Dependencies
Test core functionality in isolation with mocked HTTP responses.

```bash
# All unit tests (~2 seconds)
pytest tests/unit/ -v

# By module
pytest tests/unit/test_csv_parser.py -v       # CSV parsing (23 tests)
pytest tests/unit/test_verse_chunker.py -v    # Chunking logic (25 tests)
pytest tests/unit/test_prism_client.py -v     # HTTP client (18 tests)
pytest tests/unit/test_config.py -v           # Settings (10 tests)
pytest tests/unit/test_cli.py -v              # Commands (7 tests)
```

### Integration Tests (34) - Requires Prism
Test end-to-end search with real Prism API.

```bash
# Start Prism first
cd /dpool/aiml-stack
docker compose up -d prism

# Wait for healthy status
docker compose ps prism  # Should show "healthy"

# All integration tests (~1.5 seconds)
cd scripts/bible-importer
pytest tests/integration/ -v

# By category
pytest tests/integration/test_search_e2e.py -v      # Basic search (12 tests)
pytest tests/integration/test_search_quality.py -v  # Famous passages (11 tests)
pytest tests/integration/test_regression.py -v      # Regression (11 tests)
```

## Most Useful Tests

### Test Chunking Algorithm
```bash
pytest tests/unit/test_verse_chunker.py::TestChunkShortChapter::test_chunk_psalm_23_single_chunk -v
pytest tests/unit/test_verse_chunker.py::TestChunkBoundaries::test_chunk_never_spans_chapters -v
```

### Test Search Quality
```bash
# Psalm 23
pytest tests/integration/test_search_quality.py::TestSearchQuality::test_search_psalm_23 -v

# John 3:16
pytest tests/integration/test_search_quality.py::TestSearchQuality::test_search_john_3_16 -v

# Genesis creation
pytest tests/integration/test_search_quality.py::TestSearchQuality::test_search_genesis_creation -v
```

### Test Domain Isolation
```bash
pytest tests/integration/test_regression.py::TestRegressionPrevention::test_domain_isolation -v
pytest tests/integration/test_regression.py::TestRegressionPrevention::test_all_five_translations_searchable -v
```

## Common Issues

### "Prism API not accessible"
Integration tests are skipping. Start Prism:
```bash
cd /dpool/aiml-stack
docker compose up -d prism
docker compose ps prism  # Verify "healthy"
curl http://localhost:8100/health  # Should return 200
```

### "No results found - Bible data may not be imported"
Search quality tests skipping. Import Bible data:
```bash
cd /dpool/aiml-stack
make bible-import-kjv  # Or your preferred translation
```

### Tests Running Slow
Only run unit tests (fast):
```bash
pytest tests/unit/ -v  # ~2 seconds
```

## Test Markers

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

## Quick Debugging

```bash
# Run single test with full output
pytest tests/unit/test_verse_chunker.py::test_chunk_short_chapter -vv

# Show print statements
pytest tests/unit/ -v -s

# Drop into debugger on failure
pytest tests/unit/ --pdb

# Show slowest 10 tests
pytest tests/ --durations=10
```

## Coverage Report

```bash
# Generate HTML coverage report
pytest tests/ --cov=. --cov-report=html

# Open report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Pre-Commit Testing

Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
cd scripts/bible-importer
source .venv/bin/activate
pytest tests/unit/ -q || exit 1
echo "✅ Unit tests passed"
```

## CI/CD Integration

```yaml
# GitHub Actions example
- name: Run Bible Importer Tests
  run: |
    cd scripts/bible-importer
    source .venv/bin/activate
    pytest tests/unit/ -v  # Fast unit tests

- name: Start Prism
  run: docker compose up -d prism

- name: Run Integration Tests
  run: |
    cd scripts/bible-importer
    pytest tests/integration/ -v
```

## Expected Results

### All Tests Passing
```
tests/integration/test_regression.py ...........       [ 9%]
tests/integration/test_search_e2e.py ............      [19%]
tests/integration/test_search_quality.py ...........   [29%]
tests/unit/test_cli.py ...........                     [38%]
tests/unit/test_config.py .........                    [46%]
tests/unit/test_csv_parser.py ....................     [63%]
tests/unit/test_prism_client.py ..................     [78%]
tests/unit/test_verse_chunker.py .........................  [100%]

======================== 117 passed in 3.40s ========================
```

### Unit Tests Only
```
tests/unit/test_cli.py ...........
tests/unit/test_config.py .........
tests/unit/test_csv_parser.py ....................
tests/unit/test_prism_client.py ..................
tests/unit/test_verse_chunker.py .........................

======================== 83 passed in 2.21s =========================
```

### Integration Tests Only
```
tests/integration/test_regression.py ...........
tests/integration/test_search_e2e.py ............
tests/integration/test_search_quality.py ...........

======================== 34 passed in 1.44s =========================
```

## Need More Help?

- **Full Documentation**: [tests/README.md](tests/README.md)
- **Implementation Summary**: [TEST_SUMMARY.md](TEST_SUMMARY.md)
- **Main README**: [README.md](README.md)

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 117 |
| Unit Tests | 83 (fast) |
| Integration Tests | 34 (requires Prism) |
| Execution Time | ~3.5 seconds |
| Coverage | All core modules |
| Status | ✅ All passing |
