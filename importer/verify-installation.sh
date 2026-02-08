#!/bin/bash
# Verify Bible Importer installation and KJV import

set -e

echo "Bible Importer Installation Verification"
echo "========================================"
echo ""

# Check Python venv
echo "1. Checking Python virtual environment..."
if [ -d ".venv" ]; then
    echo "   ✅ Virtual environment exists"
else
    echo "   ❌ Virtual environment missing"
    echo "   Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Check dependencies
echo ""
echo "2. Checking Python dependencies..."
if .venv/bin/python -c "import httpx, tiktoken, pydantic, click" 2>/dev/null; then
    echo "   ✅ All dependencies installed"
else
    echo "   ❌ Dependencies missing"
    echo "   Run: .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Check KJV CSV
echo ""
echo "3. Checking KJV CSV data..."
if [ -f "../../data/bible/kjv/kjv_verses.csv" ]; then
    VERSE_COUNT=$(wc -l < ../../data/bible/kjv/kjv_verses.csv)
    echo "   ✅ KJV CSV exists ($VERSE_COUNT lines)"
else
    echo "   ❌ KJV CSV missing"
    echo "   Run: curl -L -o ../../data/bible/kjv/kjv_verses.csv 'https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/csv/KJV.csv'"
    exit 1
fi

# Check Prism
echo ""
echo "4. Checking Prism service..."
if curl -s http://localhost:8100/health > /dev/null 2>&1; then
    echo "   ✅ Prism is accessible"
else
    echo "   ⚠️  Prism not accessible at http://localhost:8100"
    echo "   Run: docker compose up -d prism"
    exit 1
fi

# Check KJV import status
echo ""
echo "5. Checking KJV import status..."
STATS=$(.venv/bin/python cli.py status 2>/dev/null | grep "Corpus documents" | awk '{print $3}' | tr -d ',')
if [ -n "$STATS" ] && [ "$STATS" -gt 3000 ]; then
    echo "   ✅ KJV appears to be imported ($STATS documents)"
else
    echo "   ⚠️  KJV not imported or incomplete"
    echo "   Run: make bible-import-kjv"
fi

echo ""
echo "========================================"
echo "✅ Installation verification complete!"
echo ""
echo "Try a search:"
echo "  make bible-search QUERY='The Lord is my shepherd'"
echo ""
