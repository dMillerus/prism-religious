"""Unit tests for biblical geography importer."""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, mock_open

from geography_importer import GeographyImporter


class TestGeographyImporter:
    """Tests for GeographyImporter class."""

    @pytest.fixture
    def importer(self, tmp_path):
        """Create importer with temporary data directory."""
        data_dir = tmp_path / "geography"
        data_dir.mkdir()
        return GeographyImporter(data_dir=data_dir)

    @pytest.fixture
    def sample_place_entry(self):
        """Sample geography entry from ancient.jsonl (OpenBible format)."""
        return {
            "friendly_id": "Jerusalem",
            "url_slug": "jerusalem",
            "types": ["settlement"],
            "identifications": [
                {
                    "resolutions": [
                        {
                            "lonlat": "35.2345,31.7767",
                            "type": "settlement",
                            "land_or_water": "land"
                        }
                    ],
                    "score": {
                        "vote_total": 800,
                        "vote_count": 20
                    }
                }
            ],
            "verses": [
                {"osis": "Gen.14.18", "readable": "Gen 14:18"},
                {"osis": "Josh.10.1", "readable": "Josh 10:1"},
                {"osis": "2Sam.5.6", "readable": "2 Sam 5:6"},
                {"osis": "1Kgs.11.13", "readable": "1 Kgs 11:13"},
                {"osis": "Ps.122.3", "readable": "Ps 122:3"}
            ],
            "translation_name_counts": {
                "Jerusalem": 814,
                "Salem": 2,
                "Zion": 154
            }
        }

    def test_calculate_confidence_score(self, importer):
        """Test confidence score calculation from vote counts."""
        # High confidence entry
        entry = {
            "confidence_yes": 10,      # +300
            "confidence_likely": 5,    # +50
            "confidence_possible": 2,  # +10
            "confidence_unlikely": 1,  # -10
        }
        score = importer.calculate_confidence_score(entry)
        assert score == 350  # 300 + 50 + 10 - 10

        # Low confidence entry
        entry = {
            "confidence_yes": 0,
            "confidence_likely": 1,    # +10
            "confidence_possible": 3,  # +15
            "confidence_unlikely": 2,  # -20
            "confidence_no": 1,        # -20
        }
        score = importer.calculate_confidence_score(entry)
        assert score == -15  # 10 + 15 - 20 - 20

        # Empty entry (missing keys)
        entry = {}
        score = importer.calculate_confidence_score(entry)
        assert score == 0

    def test_classify_confidence(self, importer):
        """Test confidence score classification."""
        assert importer.classify_confidence(600) == "very high"
        assert importer.classify_confidence(500) == "high"
        assert importer.classify_confidence(300) == "high"
        assert importer.classify_confidence(200) == "moderate"
        assert importer.classify_confidence(100) == "moderate"
        assert importer.classify_confidence(50) == "low"
        assert importer.classify_confidence(0) == "low"
        assert importer.classify_confidence(-50) == "low"

    def test_parse_coordinates_valid(self, importer):
        """Test parsing valid lonlat strings."""
        # Standard format
        lat, lon = importer.parse_coordinates("35.2345,31.7767")
        assert lat == pytest.approx(31.7767)
        assert lon == pytest.approx(35.2345)

        # With spaces
        lat, lon = importer.parse_coordinates(" 35.2345 , 31.7767 ")
        assert lat == pytest.approx(31.7767)
        assert lon == pytest.approx(35.2345)

        # Negative coordinates
        lat, lon = importer.parse_coordinates("-122.4194,37.7749")
        assert lat == pytest.approx(37.7749)
        assert lon == pytest.approx(-122.4194)

        # Edge cases (valid range)
        lat, lon = importer.parse_coordinates("180.0,90.0")
        assert lat == 90.0
        assert lon == 180.0

        lat, lon = importer.parse_coordinates("-180.0,-90.0")
        assert lat == -90.0
        assert lon == -180.0

    def test_parse_coordinates_invalid(self, importer):
        """Test parsing invalid coordinates."""
        # None input
        assert importer.parse_coordinates(None) == (None, None)

        # Empty string
        assert importer.parse_coordinates("") == (None, None)

        # Invalid format (no comma)
        assert importer.parse_coordinates("35.2345 31.7767") == (None, None)

        # Too many parts
        assert importer.parse_coordinates("35.2345,31.7767,100") == (None, None)

        # Non-numeric
        assert importer.parse_coordinates("abc,def") == (None, None)

        # Out of range longitude
        assert importer.parse_coordinates("200.0,50.0") == (None, None)

        # Out of range latitude
        assert importer.parse_coordinates("50.0,100.0") == (None, None)

    def test_get_best_identification(self, importer):
        """Test extraction of best identification resolution."""
        # Entry with identifications
        entry = {
            "identifications": [
                {
                    "resolutions": [
                        {
                            "lonlat": "35.0,31.0",
                            "type": "settlement",
                            "land_or_water": "land"
                        }
                    ]
                }
            ]
        }
        resolution = importer.get_best_identification(entry)
        assert resolution is not None
        assert resolution["lonlat"] == "35.0,31.0"
        assert resolution["type"] == "settlement"

        # Entry with no identifications
        entry = {"identifications": []}
        resolution = importer.get_best_identification(entry)
        assert resolution is None

        # Entry with no resolutions
        entry = {"identifications": [{"resolutions": []}]}
        resolution = importer.get_best_identification(entry)
        assert resolution is None

        # Missing identifications key
        entry = {}
        resolution = importer.get_best_identification(entry)
        assert resolution is None

    def test_extract_verse_references(self, importer):
        """Test verse reference extraction from verses array (OpenBible format)."""
        # Multiple verses
        entry = {
            "verses": [
                {"osis": "Gen.1.1", "readable": "Gen 1:1"},
                {"osis": "Gen.2.3", "readable": "Gen 2:3"},
                {"osis": "Exod.3.14", "readable": "Exod 3:14"},
            ]
        }
        refs = importer.extract_verse_references(entry)
        assert len(refs) == 3
        assert "Gen 1:1" in refs
        assert "Gen 2:3" in refs
        assert "Exod 3:14" in refs

        # Deduplicate references
        entry = {
            "verses": [
                {"osis": "Gen.1.1", "readable": "Gen 1:1"},
                {"osis": "Gen.1.1", "readable": "Gen 1:1"},
                {"osis": "Gen.1.1", "readable": "Gen 1:1"},
            ]
        }
        refs = importer.extract_verse_references(entry)
        assert len(refs) == 1
        assert refs[0] == "Gen 1:1"

        # Empty verses
        entry = {"verses": []}
        refs = importer.extract_verse_references(entry)
        assert refs == []

        # Missing readable key
        entry = {"verses": [{"osis": "Gen.1.1"}]}
        refs = importer.extract_verse_references(entry)
        assert refs == []

        # Non-string readable (skip invalid)
        entry = {
            "verses": [
                {"osis": "Gen.1.1", "readable": "Gen 1:1"},
                {"osis": "Gen.2.3", "readable": 123},
                {"osis": "Gen.3.5", "readable": None},
                {"osis": "Gen.4.7", "readable": "Gen 4:7"},
            ]
        }
        refs = importer.extract_verse_references(entry)
        assert len(refs) == 2
        assert "Gen 1:1" in refs
        assert "Gen 4:7" in refs

    def test_extract_verse_references_max_limit(self, importer):
        """Test verse reference limiting to prevent metadata bloat."""
        # Create entry with 50 verse references
        verses = [
            {"osis": f"Book.{i}.{i}", "readable": f"Book {i}:{i}"}
            for i in range(50)
        ]
        entry = {"verses": verses}

        # Default limit of 20
        refs = importer.extract_verse_references(entry, max_refs=20)
        assert len(refs) == 20

        # Custom limit
        refs = importer.extract_verse_references(entry, max_refs=10)
        assert len(refs) == 10

        # Sorted output (deterministic)
        assert refs == sorted(refs)

    def test_place_to_document_complete(self, importer, sample_place_entry):
        """Test document conversion with complete place entry (OpenBible format)."""
        doc = importer.place_to_document(sample_place_entry)

        # Verify structure
        assert "title" in doc
        assert "content" in doc
        assert "domain" in doc
        assert "metadata" in doc

        # Verify values
        assert doc["domain"] == "geography/biblical"
        assert "Jerusalem" in doc["title"]
        assert doc["metadata"]["slug"] == "jerusalem"
        assert doc["metadata"]["place_name"] == "Jerusalem"
        assert doc["metadata"]["place_type"] == "settlement"
        assert doc["metadata"]["land_or_water"] == "land"

        # Verify coordinates
        assert doc["metadata"]["latitude"] == pytest.approx(31.7767)
        assert doc["metadata"]["longitude"] == pytest.approx(35.2345)

        # Verify confidence (from score.vote_total)
        assert doc["metadata"]["confidence_score"] == 800
        assert doc["metadata"]["confidence_level"] == "very high"

        # Verify verse references
        assert doc["metadata"]["verse_count"] == 5
        assert len(doc["metadata"]["verse_references"]) == 5
        assert "Gen 14:18" in doc["metadata"]["verse_references"]

        # Verify alternate names
        assert "alternate_names" in doc["metadata"]
        assert "Jerusalem" in doc["metadata"]["alternate_names"]
        assert "Salem" in doc["metadata"]["alternate_names"]
        assert "Zion" in doc["metadata"]["alternate_names"]

        # Verify content formatting
        assert "Jerusalem" in doc["content"]
        assert "settlement" in doc["content"]
        assert "31.7767°N" in doc["content"]
        assert "very high" in doc["content"]

    def test_place_to_document_minimal(self, importer):
        """Test document conversion with minimal place entry (OpenBible format)."""
        entry = {
            "friendly_id": "Unknown Site",
            "url_slug": "unknown-site",
        }
        doc = importer.place_to_document(entry)

        # Should still produce valid document
        assert doc["domain"] == "geography/biblical"
        assert "Unknown Site" in doc["title"]
        assert doc["metadata"]["slug"] == "unknown-site"
        assert doc["metadata"]["place_type"] == "unknown"

        # Coordinates should be None
        assert "latitude" not in doc["metadata"]
        assert "longitude" not in doc["metadata"]

        # Confidence should default to 0 (low)
        assert doc["metadata"]["confidence_score"] == 0
        assert doc["metadata"]["confidence_level"] == "low"

    def test_place_to_document_missing_coordinates(self, importer):
        """Test document with missing or invalid coordinates (OpenBible format)."""
        entry = {
            "friendly_id": "Site 1",
            "url_slug": "site1",
            "identifications": [
                {
                    "resolutions": [
                        {
                            "lonlat": None,
                            "land_or_water": "land"
                        }
                    ],
                    "score": {"vote_total": 100}
                }
            ]
        }
        doc = importer.place_to_document(entry)
        assert "latitude" not in doc["metadata"]
        assert "longitude" not in doc["metadata"]
        assert "Coordinates unknown" in doc["content"]

        # Test invalid coordinates
        entry["identifications"][0]["resolutions"][0]["lonlat"] = "invalid"
        doc = importer.place_to_document(entry)
        assert "latitude" not in doc["metadata"]

    def test_parse_jsonl_valid(self, importer, tmp_path):
        """Test parsing valid JSONL file."""
        # Create test JSONL file
        jsonl_file = tmp_path / "geography" / "test.jsonl"
        entries = [
            {"slug": "place1", "name": "Place 1"},
            {"slug": "place2", "name": "Place 2"},
            {"slug": "place3", "name": "Place 3"},
        ]

        with open(jsonl_file, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        places = importer.parse_jsonl(jsonl_file)
        assert len(places) == 3
        assert places[0]["slug"] == "place1"
        assert places[1]["slug"] == "place2"
        assert places[2]["slug"] == "place3"

    def test_parse_jsonl_with_empty_lines(self, importer, tmp_path):
        """Test parsing JSONL with empty lines (should skip)."""
        jsonl_file = tmp_path / "geography" / "test.jsonl"

        with open(jsonl_file, "w") as f:
            f.write('{"slug": "place1"}\n')
            f.write('\n')  # Empty line
            f.write('{"slug": "place2"}\n')
            f.write('   \n')  # Whitespace line
            f.write('{"slug": "place3"}\n')

        places = importer.parse_jsonl(jsonl_file)
        assert len(places) == 3

    def test_parse_jsonl_with_invalid_json(self, importer, tmp_path, caplog):
        """Test parsing JSONL with invalid JSON lines (should skip with warning)."""
        jsonl_file = tmp_path / "geography" / "test.jsonl"

        with open(jsonl_file, "w") as f:
            f.write('{"slug": "place1"}\n')
            f.write('invalid json line\n')  # Invalid
            f.write('{"slug": "place2"}\n')
            f.write('{"incomplete": \n')  # Invalid
            f.write('{"slug": "place3"}\n')

        places = importer.parse_jsonl(jsonl_file)
        assert len(places) == 3  # Should parse valid lines

        # Check warning was logged
        assert "Skipped 2 invalid lines" in caplog.text

    def test_parse_jsonl_missing_file(self, importer):
        """Test parsing non-existent file raises error."""
        with pytest.raises(FileNotFoundError) as exc_info:
            importer.parse_jsonl(Path("nonexistent.jsonl"))
        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_download_data_success(self, importer):
        """Test successful data download."""
        mock_response = Mock()
        mock_response.text = '{"slug": "test"}\n'
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context

            result = await importer.download_data()

            assert result == importer.jsonl_file
            assert importer.jsonl_file.exists()
            content = importer.jsonl_file.read_text()
            assert content == '{"slug": "test"}\n'

    @pytest.mark.asyncio
    async def test_download_data_cached(self, importer):
        """Test download skips if file already exists."""
        # Create existing file
        importer.jsonl_file.write_text('{"cached": true}\n')

        # Should not download
        result = await importer.download_data(force=False)
        assert result == importer.jsonl_file

        # Content should be unchanged
        assert "cached" in importer.jsonl_file.read_text()

    @pytest.mark.asyncio
    async def test_download_data_force_redownload(self, importer):
        """Test force download overwrites existing file."""
        # Create existing file
        importer.jsonl_file.write_text('{"old": true}\n')

        mock_response = Mock()
        mock_response.text = '{"new": true}\n'
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_context

            result = await importer.download_data(force=True)

            assert result == importer.jsonl_file
            assert "new" in importer.jsonl_file.read_text()
            assert "old" not in importer.jsonl_file.read_text()

    def test_import_all_dry_run(self, importer, sample_place_entry, tmp_path):
        """Test dry run mode (parse only, no import)."""
        # Create test JSONL file
        jsonl_file = tmp_path / "geography" / "ancient.jsonl"
        with open(jsonl_file, "w") as f:
            for i in range(5):
                entry = dict(sample_place_entry)
                entry["slug"] = f"place{i}"
                entry["name"] = f"Place {i}"
                f.write(json.dumps(entry) + "\n")

        results = importer.import_all(dry_run=True, download=False)

        # Verify structure
        assert "total_documents" in results
        assert "type_counts" in results
        assert "sample_documents" in results

        # Verify counts
        assert results["total_documents"] == 5
        assert results["type_counts"]["settlement"] == 5

        # Verify samples
        assert len(results["sample_documents"]) == 3  # First 3

    def test_import_all_no_data(self, importer, tmp_path):
        """Test import with no place entries."""
        # Create empty JSONL file
        jsonl_file = tmp_path / "geography" / "ancient.jsonl"
        jsonl_file.write_text("")

        results = importer.import_all(dry_run=True, download=False)

        assert results["total_documents"] == 0
        assert "error" in results

    def test_import_all_conversion_error_handling(self, importer, tmp_path, caplog):
        """Test import handles conversion errors gracefully."""
        # Create JSONL with entry that will fail conversion
        jsonl_file = tmp_path / "geography" / "ancient.jsonl"
        with open(jsonl_file, "w") as f:
            # Valid entry
            f.write('{"slug": "valid", "name": "Valid Place"}\n')
            # Entry that will fail conversion (mock by patching)
            f.write('{"slug": "problematic", "name": "Problem"}\n')

        # Mock place_to_document to fail on second call
        call_count = [0]
        original_method = importer.place_to_document

        def failing_converter(entry):
            call_count[0] += 1
            if call_count[0] == 2:
                raise ValueError("Conversion error")
            return original_method(entry)

        with patch.object(importer, 'place_to_document', side_effect=failing_converter):
            results = importer.import_all(dry_run=True, download=False)

            # Should convert successfully despite one failure
            assert results["total_documents"] == 1  # Only valid entry

        # Check warning was logged
        assert "Failed to convert" in caplog.text


class TestVerifyGeographyImport:
    """Tests for geography import verification function."""

    @pytest.mark.asyncio
    async def test_verify_geography_import_default_queries(self):
        """Test verification with default sample queries."""
        from geography_importer import verify_geography_import

        # Mock PrismClient (imported inside the function)
        with patch("prism_client.PrismClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            # Mock responses
            mock_client.get_stats.return_value = {
                "total_documents": 1000,
                "total_chunks": 5000,
            }
            mock_client.count_domain_documents.return_value = 500
            mock_client.search_documents.return_value = {
                "results": [
                    {
                        "document_title": "Biblical Place: Jerusalem",
                        "similarity": 0.95,
                        "content": "Jerusalem is a biblical settlement...",
                    }
                ]
            }

            results = await verify_geography_import()

            # Verify calls
            assert mock_client.get_stats.called
            assert mock_client.count_domain_documents.called
            assert mock_client.search_documents.call_count == 4  # 4 default queries

            # Verify results structure
            assert "prism_stats" in results
            assert "geography_document_count" in results
            assert "places" in results
            assert len(results["places"]) == 4

    @pytest.mark.asyncio
    async def test_verify_geography_import_custom_queries(self):
        """Test verification with custom queries."""
        from geography_importer import verify_geography_import

        custom_queries = ["Bethlehem", "Nazareth"]

        with patch("prism_client.PrismClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            mock_client.get_stats.return_value = {}
            mock_client.count_domain_documents.return_value = 300
            mock_client.search_documents.return_value = {"results": []}

            results = await verify_geography_import(sample_queries=custom_queries)

            # Should only search for custom queries
            assert mock_client.search_documents.call_count == 2
            assert len(results["places"]) == 2
            assert "Bethlehem" in results["places"]
            assert "Nazareth" in results["places"]
