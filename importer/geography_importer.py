"""Biblical Geography importer for Prism.

Imports biblical place data with coordinates, confidence scores, and verse references
into Prism as searchable documents for spatial RAG context.

Data source: Open Bible Info Bible Geocoding Data (CC-BY-SA 4.0)
https://github.com/openbibleinfo/Bible-Geocoding-Data
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

import httpx

from config import settings
from prism_client import import_documents_in_batches

# Set up logging
logger = logging.getLogger(__name__)

# Data source URL
GEOGRAPHY_DATA_URL = (
    "https://raw.githubusercontent.com/openbibleinfo/Bible-Geocoding-Data/"
    "main/data/ancient.jsonl"
)


class GeographyImporter:
    """Importer for biblical geography data with coordinates and verse references."""

    def __init__(self, data_dir: Path = Path("data_sources/geography")):
        """
        Initialize geography importer.

        Args:
            data_dir: Path to geography data directory
        """
        self.data_dir = data_dir
        self.jsonl_file = data_dir / "ancient.jsonl"

    async def download_data(self, force: bool = False) -> Path:
        """
        Download ancient.jsonl from GitHub if not already cached.

        Args:
            force: If True, download even if file exists

        Returns:
            Path to downloaded file

        Raises:
            httpx.HTTPError: If download fails
        """
        if self.jsonl_file.exists() and not force:
            logger.info(f"Using cached geography data at {self.jsonl_file}")
            return self.jsonl_file

        # Ensure directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading geography data from {GEOGRAPHY_DATA_URL}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(GEOGRAPHY_DATA_URL)
            response.raise_for_status()

            # Save to file
            self.jsonl_file.write_text(response.text, encoding="utf-8")
            logger.info(f"Downloaded {len(response.text)} bytes to {self.jsonl_file}")

        return self.jsonl_file

    def parse_jsonl(self, jsonl_file: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Parse JSON Lines file to extract place entries.

        Each line is a separate JSON object representing one biblical place.

        Args:
            jsonl_file: Path to JSONL file (defaults to self.jsonl_file)

        Returns:
            List of place entry dictionaries

        Raises:
            FileNotFoundError: If JSONL file doesn't exist
            ValueError: If file cannot be parsed
        """
        file_path = jsonl_file or self.jsonl_file

        if not file_path.exists():
            raise FileNotFoundError(
                f"Geography data file not found: {file_path}. "
                "Run with --download or check data directory."
            )

        places = []
        skipped = 0

        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                    places.append(entry)
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Skipping invalid JSON on line {line_num}: {e}"
                    )
                    skipped += 1
                    continue

        if skipped > 0:
            logger.warning(f"Skipped {skipped} invalid lines")

        logger.info(f"Parsed {len(places)} place entries from {file_path}")
        return places

    def calculate_confidence_score(self, entry: Dict[str, Any]) -> int:
        """
        Calculate aggregate confidence score from vote counts.

        Scoring system:
        - confidence_yes: +30 per vote
        - confidence_likely: +10 per vote
        - confidence_possible: +5 per vote
        - confidence_unlikely: -10 per vote
        - confidence_no: -20 per vote

        Args:
            entry: Place entry dictionary

        Returns:
            Total confidence score (can be negative)
        """
        score = 0
        score += entry.get("confidence_yes", 0) * 30
        score += entry.get("confidence_likely", 0) * 10
        score += entry.get("confidence_possible", 0) * 5
        score += entry.get("confidence_unlikely", 0) * -10
        score += entry.get("confidence_no", 0) * -20
        return score

    def classify_confidence(self, score: int) -> str:
        """
        Classify confidence score into categorical level.

        Args:
            score: Numeric confidence score

        Returns:
            Confidence level: "very high", "high", "moderate", or "low"
        """
        if score > 500:
            return "very high"
        elif score > 200:
            return "high"
        elif score > 50:
            return "moderate"
        else:
            return "low"

    def parse_coordinates(self, lonlat: Optional[str]) -> tuple[Optional[float], Optional[float]]:
        """
        Parse lonlat string to extract latitude and longitude.

        Format: "lon,lat" (e.g., "35.2345,31.7767")

        Args:
            lonlat: Comma-separated lon,lat string

        Returns:
            Tuple of (latitude, longitude) or (None, None) if invalid
        """
        if not lonlat:
            return None, None

        try:
            parts = lonlat.split(",")
            if len(parts) != 2:
                return None, None

            lon = float(parts[0].strip())
            lat = float(parts[1].strip())

            # Validate ranges
            if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
                logger.warning(f"Invalid coordinates: lon={lon}, lat={lat}")
                return None, None

            return lat, lon
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse coordinates from: {lonlat}")
            return None, None

    def extract_verse_references(
        self, entry: Dict[str, Any], max_refs: int = 20
    ) -> List[str]:
        """
        Extract verse references from verses array.

        OpenBible format has a "verses" array with "readable" field containing
        human-readable references like "2 Kgs 5:12".

        Args:
            entry: Place entry dictionary
            max_refs: Maximum references to include (to avoid metadata bloat)

        Returns:
            List of verse reference strings (limited to max_refs)
        """
        refs = []

        # Extract from verses array (OpenBible format)
        for verse in entry.get("verses", []):
            readable = verse.get("readable")
            if readable and isinstance(readable, str):
                refs.append(readable)

        # Sort for deterministic output
        refs = sorted(set(refs))  # Deduplicate and sort

        if len(refs) > max_refs:
            logger.debug(
                f"{entry.get('friendly_id', 'Unknown')}: {len(refs)} refs, "
                f"limiting to {max_refs}"
            )
            return refs[:max_refs]

        return refs

    def get_best_identification(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract the best identification resolution from OpenBible data.

        OpenBible places have an "identifications" array with nested "resolutions".
        We take the first identification's first resolution as the primary data source.

        Args:
            entry: Place entry dictionary

        Returns:
            Best resolution dict or None if not found
        """
        identifications = entry.get("identifications", [])
        if not identifications:
            return None

        # Take first identification
        first_id = identifications[0]

        # Get first resolution
        resolutions = first_id.get("resolutions", [])
        if not resolutions:
            return None

        return resolutions[0]

    def place_to_document(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert geography entry to Prism document format.

        Handles OpenBible data structure:
        - friendly_id / url_slug for name
        - types array for place type
        - identifications[0].resolutions[0] for coordinates and details
        - verses array for biblical references
        - identifications[0].score for confidence

        Args:
            entry: Place entry dictionary from JSONL

        Returns:
            Prism document dict with title, content, domain, metadata
        """
        # Extract core fields (OpenBible format)
        slug = entry.get("url_slug", entry.get("friendly_id", "unknown"))
        place_name = entry.get("friendly_id", slug)

        # Get place type from types array (first type)
        types = entry.get("types", [])
        place_type = types[0] if types else "unknown"

        # Get best identification resolution
        resolution = self.get_best_identification(entry)

        # Extract details from resolution
        if resolution:
            land_or_water = resolution.get("land_or_water", "unknown")
            lonlat_str = resolution.get("lonlat")
            resolution_type = resolution.get("type", place_type)
            # Use resolution type if more specific
            if resolution_type != place_type and resolution_type:
                place_type = resolution_type
        else:
            land_or_water = "unknown"
            lonlat_str = None

        # Parse coordinates
        latitude, longitude = self.parse_coordinates(lonlat_str)

        # Calculate confidence from score (OpenBible format)
        confidence_score = 0
        if entry.get("identifications"):
            first_id = entry["identifications"][0]
            score_data = first_id.get("score", {})
            # Use vote_total as confidence score
            confidence_score = score_data.get("vote_total", 0)

        confidence_level = self.classify_confidence(confidence_score)

        # Extract verse references
        verse_refs = self.extract_verse_references(entry)
        verse_count = len(verse_refs)

        # Extract alternate names from translation_name_counts
        alternate_names = []
        name_counts = entry.get("translation_name_counts", {})
        if isinstance(name_counts, dict):
            alternate_names = list(name_counts.keys())

        # Build rich content for embedding
        parts = []

        # Title line
        parts.append(f"**{place_name}** is a biblical {place_type}.")

        # Location description
        if latitude is not None and longitude is not None:
            parts.append(
                f"Located at {latitude:.4f}°N, {longitude:.4f}°E ({land_or_water})."
            )
        else:
            parts.append(f"Location type: {land_or_water}. Coordinates unknown.")

        # Confidence
        parts.append(
            f"Identification confidence: {confidence_level} (score: {confidence_score})."
        )

        # Verse references (sample)
        if verse_refs:
            sample_refs = ", ".join(verse_refs[:5])
            if len(verse_refs) > 5:
                sample_refs += f", ... ({verse_count} total references)"
            parts.append(f"Biblical references: {sample_refs}")

        # Alternate names
        if alternate_names and alternate_names != [place_name]:
            alt_names_display = [n for n in alternate_names if n != place_name][:5]
            if alt_names_display:
                parts.append(f"Also known as: {', '.join(alt_names_display)}")

        content = " ".join(parts)

        # Create document title
        title = f"Biblical Place: {place_name}"

        # Build metadata
        metadata = {
            "slug": slug,
            "place_name": place_name,
            "place_type": place_type,
            "land_or_water": land_or_water,
            "confidence_score": confidence_score,
            "confidence_level": confidence_level,
            "verse_count": verse_count,
        }

        # Add optional fields
        if latitude is not None:
            metadata["latitude"] = latitude
        if longitude is not None:
            metadata["longitude"] = longitude
        if verse_refs:
            metadata["verse_references"] = verse_refs  # Full list in metadata
        if alternate_names:
            metadata["alternate_names"] = alternate_names

        return {
            "title": title,
            "content": content,
            "domain": "geography/biblical",
            "metadata": metadata,
        }

    def import_all(
        self,
        batch_size: int = 100,
        embed: bool = True,
        dry_run: bool = False,
        download: bool = True,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Import biblical geography data to Prism.

        Args:
            batch_size: Documents per batch (max 100)
            embed: Whether to generate embeddings
            dry_run: If True, parse only without importing
            download: If True, download data if not cached
            progress_callback: Optional callback(batch_num, total_batches, result)

        Returns:
            Import results summary

        Raises:
            FileNotFoundError: If data file missing and download=False
        """
        # Download data if requested
        if download:
            asyncio.run(self.download_data())

        # Parse data
        entries = self.parse_jsonl()

        if not entries:
            return {
                "error": "No place entries found in data file",
                "total_documents": 0,
            }

        # Convert to documents
        documents = []
        for entry in entries:
            try:
                doc = self.place_to_document(entry)
                documents.append(doc)
            except Exception as e:
                logger.warning(
                    f"Failed to convert place {entry.get('name', 'Unknown')}: {e}"
                )
                continue

        logger.info(f"Converted {len(documents)} place entries to documents")

        # Count places by type
        type_counts = {}
        for doc in documents:
            place_type = doc["metadata"].get("place_type", "unknown")
            type_counts[place_type] = type_counts.get(place_type, 0) + 1

        if dry_run:
            return {
                "total_documents": len(documents),
                "type_counts": type_counts,
                "sample_documents": documents[:3],  # Show first 3 as samples
            }

        # Import to Prism
        results = asyncio.run(
            import_documents_in_batches(
                documents,
                batch_size=batch_size,
                embed=embed,
                progress_callback=progress_callback,
            )
        )

        # Add geography-specific stats
        results["type_counts"] = type_counts

        return results


async def verify_geography_import(sample_queries: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Verify geography entries were imported correctly by searching for known places.

    Args:
        sample_queries: Optional list of place names to search for
                       If None, uses common examples

    Returns:
        Verification results with search results for each query
    """
    from prism_client import PrismClient

    if sample_queries is None:
        # Common biblical places
        sample_queries = [
            "Jerusalem",
            "Bethlehem",
            "Mount Sinai",
            "Sea of Galilee",
        ]

    results = {}

    async with PrismClient() as client:
        # Check overall stats
        stats = await client.get_stats()
        results["prism_stats"] = stats

        # Count geography documents
        geography_count = await client.count_domain_documents("geography/biblical")
        results["geography_document_count"] = geography_count

        # Search for specific places
        results["places"] = {}
        for query in sample_queries:
            search_results = await client.search_documents(
                query=query, domain="geography/biblical", top_k=3
            )
            results["places"][query] = search_results.get("results", [])

    return results
