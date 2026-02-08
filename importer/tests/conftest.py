"""Shared test fixtures for bible-importer test suite."""

import sys
from pathlib import Path
from typing import AsyncGenerator, Dict, List
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from csv_parser import BibleVerse
from prism_client import PrismClient
from config import BibleImporterSettings


@pytest.fixture
def sample_verses_csv_path() -> Path:
    """Path to sample verses CSV fixture."""
    return Path(__file__).parent / "fixtures" / "sample_verses.csv"


@pytest.fixture
def malformed_verses_csv_path() -> Path:
    """Path to malformed verses CSV fixture."""
    return Path(__file__).parent / "fixtures" / "malformed_verses.csv"


@pytest.fixture
def genesis_1_verses() -> List[BibleVerse]:
    """Parsed Genesis 1:1-5 verses for testing."""
    return [
        BibleVerse(
            book_id=1,
            book_name="Genesis",
            chapter=1,
            verse=1,
            text="In the beginning God created the heaven and the earth.",
        ),
        BibleVerse(
            book_id=1,
            book_name="Genesis",
            chapter=1,
            verse=2,
            text="And the earth was without form, and void; and darkness was upon the face of the deep. And the Spirit of God moved upon the face of the waters.",
        ),
        BibleVerse(
            book_id=1,
            book_name="Genesis",
            chapter=1,
            verse=3,
            text="And God said, Let there be light: and there was light.",
        ),
        BibleVerse(
            book_id=1,
            book_name="Genesis",
            chapter=1,
            verse=4,
            text="And God saw the light, that it was good: and God divided the light from the darkness.",
        ),
        BibleVerse(
            book_id=1,
            book_name="Genesis",
            chapter=1,
            verse=5,
            text="And God called the light Day, and the darkness he called Night. And the evening and the morning were the first day.",
        ),
    ]


@pytest.fixture
def psalm_23_verses() -> List[BibleVerse]:
    """Parsed Psalm 23 verses for testing short chapter."""
    return [
        BibleVerse(
            book_id=19,
            book_name="Psalms",
            chapter=23,
            verse=1,
            text="The LORD is my shepherd; I shall not want.",
        ),
        BibleVerse(
            book_id=19,
            book_name="Psalms",
            chapter=23,
            verse=2,
            text="He maketh me to lie down in green pastures: he leadeth me beside the still waters.",
        ),
        BibleVerse(
            book_id=19,
            book_name="Psalms",
            chapter=23,
            verse=3,
            text="He restoreth my soul: he leadeth me in the paths of righteousness for his name's sake.",
        ),
        BibleVerse(
            book_id=19,
            book_name="Psalms",
            chapter=23,
            verse=4,
            text="Yea, though I walk through the valley of the shadow of death, I will fear no evil: for thou art with me; thy rod and thy staff they comfort me.",
        ),
        BibleVerse(
            book_id=19,
            book_name="Psalms",
            chapter=23,
            verse=5,
            text="Thou preparest a table before me in the presence of mine enemies: thou anointest my head with oil; my cup runneth over.",
        ),
        BibleVerse(
            book_id=19,
            book_name="Psalms",
            chapter=23,
            verse=6,
            text="Surely goodness and mercy shall follow me all the days of my life: and I will dwell in the house of the LORD for ever.",
        ),
    ]


@pytest.fixture
def john_3_verses() -> List[BibleVerse]:
    """Parsed John 3:16-17 verses for testing."""
    return [
        BibleVerse(
            book_id=43,
            book_name="John",
            chapter=3,
            verse=16,
            text="For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life.",
        ),
        BibleVerse(
            book_id=43,
            book_name="John",
            chapter=3,
            verse=17,
            text="For God sent not his Son into the world to condemn the world; but that the world through him might be saved.",
        ),
    ]


@pytest.fixture
def mixed_chapter_verses(genesis_1_verses: List[BibleVerse], psalm_23_verses: List[BibleVerse]) -> List[BibleVerse]:
    """Combined verses from multiple chapters for testing chapter boundaries."""
    # Create Genesis 2:1 to test chapter boundary
    genesis_2_verse = BibleVerse(
        book_id=1,
        book_name="Genesis",
        chapter=2,
        verse=1,
        text="Thus the heavens and the earth were finished, and all the host of them.",
    )
    return genesis_1_verses + [genesis_2_verse] + psalm_23_verses


@pytest.fixture
def famous_passages() -> Dict[str, Dict[str, str]]:
    """Famous Bible passages for search quality testing."""
    return {
        "psalm_23": {
            "query": "The Lord is my shepherd I shall not want",
            "expected_book": "Psalms",
            "expected_chapter": 23,
        },
        "john_3_16": {
            "query": "For God so loved the world",
            "expected_book": "John",
            "expected_chapter": 3,
        },
        "genesis_creation": {
            "query": "In the beginning God created the heaven and the earth",
            "expected_book": "Genesis",
            "expected_chapter": 1,
        },
    }


@pytest.fixture
def mock_httpx_client() -> AsyncMock:
    """Mock httpx.AsyncClient for unit tests."""
    mock = AsyncMock(spec=httpx.AsyncClient)

    # Create a mock request to avoid raise_for_status errors
    mock_request = httpx.Request("GET", "http://test")

    # Default health check response
    get_response = httpx.Response(
        200,
        json={"status": "healthy", "version": "1.0.0"},
        request=mock_request,
    )
    mock.get.return_value = get_response

    # Default import response
    post_response = httpx.Response(
        200,
        json={
            "success": 100,
            "errors": [],
            "skipped": 0,
            "total": 100,
        },
        request=mock_request,
    )
    mock.post.return_value = post_response

    return mock


@pytest.fixture
def mock_prism_client(mock_httpx_client: AsyncMock) -> PrismClient:
    """Mock PrismClient for unit tests (no real HTTP calls)."""
    client = PrismClient()
    client.client = mock_httpx_client
    return client


@pytest.fixture
def test_settings() -> BibleImporterSettings:
    """Test settings with safe defaults."""
    return BibleImporterSettings(
        prism_base_url="http://localhost:8100",
        target_chunk_tokens=350,
        min_chunk_tokens=50,
        max_chunk_tokens=500,
        batch_size=100,
    )


@pytest_asyncio.fixture
async def prism_test_client() -> AsyncGenerator[PrismClient, None]:
    """
    Real PrismClient for integration tests.

    Skips test if Prism is not accessible.
    """
    async with PrismClient() as client:
        # Check if Prism is running
        try:
            is_healthy = await client.check_health()
            if not is_healthy:
                pytest.skip("Prism API is not healthy")
        except Exception as e:
            pytest.skip(f"Prism API not accessible: {e}")

        yield client


@pytest.fixture
def oversized_verse() -> BibleVerse:
    """Create a verse with >500 tokens for testing standalone chunking."""
    # Create a very long verse text
    long_text = " ".join([
        "This is a very long verse that exceeds the maximum chunk token limit."
    ] * 50)

    return BibleVerse(
        book_id=1,
        book_name="Genesis",
        chapter=1,
        verse=1,
        text=long_text,
    )
