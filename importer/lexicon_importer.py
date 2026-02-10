"""Strong's Lexicon importer for Prism.

Imports Strong's Hebrew and Greek dictionary entries into Prism as searchable documents
optimized for RAG (Retrieval-Augmented Generation) workflows.

Data source: Open Scriptures Strong's Dictionaries (CC-BY-SA)
https://github.com/openscriptures/strongs
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from config import settings
from prism_client import import_documents_in_batches

# Set up logging
logger = logging.getLogger(__name__)


class LexiconImporter:
    """Importer for Strong's Hebrew and Greek lexicon data."""

    def __init__(self, data_dir: Path = Path("data_sources/strongs")):
        """
        Initialize lexicon importer.

        Args:
            data_dir: Path to Strong's dictionary data directory
        """
        self.data_dir = data_dir
        self.hebrew_file = data_dir / "hebrew" / "strongs-hebrew-dictionary.js"
        self.greek_file = data_dir / "greek" / "strongs-greek-dictionary.js"

    def parse_js_dictionary(self, js_file: Path) -> Dict[str, Dict[str, Any]]:
        """
        Parse JavaScript dictionary file to extract JSON data.

        The files contain: var strongsGreekDictionary = {...}
        or: var strongsHebrewDictionary = {...}

        Args:
            js_file: Path to JavaScript file

        Returns:
            Dictionary of Strong's entries keyed by number

        Raises:
            FileNotFoundError: If JS file doesn't exist
            ValueError: If file cannot be parsed
        """
        if not js_file.exists():
            raise FileNotFoundError(f"Dictionary file not found: {js_file}")

        # Read file content
        content = js_file.read_text(encoding="utf-8")

        # Extract JSON from JavaScript variable assignment
        # Pattern: var strongsXXXDictionary = {...};
        match = re.search(r"var\s+strongs\w+Dictionary\s*=\s*(\{.+\});", content, re.DOTALL)
        if not match:
            raise ValueError(f"Could not extract dictionary from {js_file}")

        json_str = match.group(1)

        # Parse JSON
        try:
            dictionary = json.loads(json_str)
            return dictionary
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from {js_file}: {e}")

    def hebrew_entry_to_document(self, strong_id: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Hebrew lexicon entry to Prism document format.

        Args:
            strong_id: Strong's number (e.g., "H1")
            entry: Dictionary with entry data

        Returns:
            Prism document dict
        """
        # Extract fields (all are optional in the data)
        lemma = entry.get("lemma", "")
        xlit = entry.get("xlit", "")
        pron = entry.get("pron", "")
        strongs_def = entry.get("strongs_def", "")
        kjv_def = entry.get("kjv_def", "")
        derivation = entry.get("derivation", "")

        # Build rich content for embedding
        # Format: transliteration (lemma) - definition. Etymology. KJV usage.
        parts = []

        # Title line
        if xlit and lemma:
            title_part = f"{xlit} ({lemma})"
        elif xlit:
            title_part = xlit
        elif lemma:
            title_part = lemma
        else:
            title_part = strong_id

        # Definition
        if strongs_def:
            parts.append(f"Definition: {strongs_def}")

        # Etymology/Derivation
        if derivation:
            parts.append(f"Etymology: {derivation}")

        # KJV usage examples
        if kjv_def:
            parts.append(f"KJV translations: {kjv_def}")

        # Pronunciation
        if pron:
            parts.append(f"Pronunciation: {pron}")

        content = "\n\n".join(parts) if parts else strongs_def or "No definition available."

        # Create document title
        title = f"Strong's {strong_id} - {title_part}"

        # Parse KJV usage counts if available (format: "word1 (count1), word2 (count2)")
        kjv_usage = self._parse_kjv_usage(kjv_def)

        # Metadata
        metadata = {
            "strong_id": strong_id,
            "language": "hebrew",
            "lemma": lemma,
            "transliteration": xlit,
            "pronunciation": pron,
            "definition": strongs_def,
            "derivation": derivation,
            "kjv_def": kjv_def,
            "kjv_usage": kjv_usage,
        }

        # Remove empty fields from metadata
        metadata = {k: v for k, v in metadata.items() if v}

        return {
            "title": title,
            "content": content,
            "domain": "lexicon/strongs",
            "metadata": metadata,
        }

    def greek_entry_to_document(self, strong_id: str, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Greek lexicon entry to Prism document format.

        Args:
            strong_id: Strong's number (e.g., "G1")
            entry: Dictionary with entry data

        Returns:
            Prism document dict
        """
        # Extract fields (all are optional in the data)
        lemma = entry.get("lemma", "")
        translit = entry.get("translit", "")
        strongs_def = entry.get("strongs_def", "")
        kjv_def = entry.get("kjv_def", "")
        derivation = entry.get("derivation", "")

        # Build rich content for embedding
        parts = []

        # Title line
        if translit and lemma:
            title_part = f"{translit} ({lemma})"
        elif translit:
            title_part = translit
        elif lemma:
            title_part = lemma
        else:
            title_part = strong_id

        # Definition
        if strongs_def:
            parts.append(f"Definition: {strongs_def}")

        # Etymology/Derivation
        if derivation:
            parts.append(f"Etymology: {derivation}")

        # KJV usage examples
        if kjv_def:
            parts.append(f"KJV translations: {kjv_def}")

        content = "\n\n".join(parts) if parts else strongs_def or "No definition available."

        # Create document title
        title = f"Strong's {strong_id} - {title_part}"

        # Parse KJV usage counts
        kjv_usage = self._parse_kjv_usage(kjv_def)

        # Metadata
        metadata = {
            "strong_id": strong_id,
            "language": "greek",
            "lemma": lemma,
            "transliteration": translit,
            "definition": strongs_def,
            "derivation": derivation,
            "kjv_def": kjv_def,
            "kjv_usage": kjv_usage,
        }

        # Remove empty fields from metadata
        metadata = {k: v for k, v in metadata.items() if v}

        return {
            "title": title,
            "content": content,
            "domain": "lexicon/strongs",
            "metadata": metadata,
        }

    def _parse_kjv_usage(self, kjv_def: str) -> Optional[Dict[str, int]]:
        """
        Parse KJV usage string to extract word counts.

        Example: "father (1205), chief (2), patrimony (1)" → {"father": 1205, "chief": 2, "patrimony": 1}

        Args:
            kjv_def: KJV definition string

        Returns:
            Dictionary mapping translations to counts, or None if cannot parse
        """
        if not kjv_def:
            return None

        usage = {}
        # Pattern: word (count) or word(-hyphenated) (count)
        pattern = r"([\w\-\s]+)\s*\((\d+)\)"
        matches = re.findall(pattern, kjv_def)

        for word, count in matches:
            word = word.strip()
            usage[word] = int(count)

        return usage if usage else None

    def import_hebrew_lexicon(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Import Hebrew lexicon entries.

        Args:
            dry_run: If True, parse and return documents without importing

        Returns:
            List of Prism document dicts
        """
        logger.info(f"Parsing Hebrew lexicon from {self.hebrew_file}")
        hebrew_dict = self.parse_js_dictionary(self.hebrew_file)

        documents = []
        for strong_id, entry in hebrew_dict.items():
            doc = self.hebrew_entry_to_document(strong_id, entry)
            documents.append(doc)

        logger.info(f"Parsed {len(documents)} Hebrew lexicon entries")
        return documents

    def import_greek_lexicon(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Import Greek lexicon entries.

        Args:
            dry_run: If True, parse and return documents without importing

        Returns:
            List of Prism document dicts
        """
        logger.info(f"Parsing Greek lexicon from {self.greek_file}")
        greek_dict = self.parse_js_dictionary(self.greek_file)

        documents = []
        for strong_id, entry in greek_dict.items():
            doc = self.greek_entry_to_document(strong_id, entry)
            documents.append(doc)

        logger.info(f"Parsed {len(documents)} Greek lexicon entries")
        return documents

    def import_all(
        self,
        batch_size: int = 100,
        embed: bool = True,
        dry_run: bool = False,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Import both Hebrew and Greek lexicons to Prism.

        Args:
            batch_size: Documents per batch (max 100)
            embed: Whether to generate embeddings
            dry_run: If True, parse only without importing
            progress_callback: Optional callback(batch_num, total_batches, result)

        Returns:
            Import results summary
        """
        # Parse both lexicons
        hebrew_docs = self.import_hebrew_lexicon(dry_run=True)
        greek_docs = self.import_greek_lexicon(dry_run=True)

        all_documents = hebrew_docs + greek_docs

        logger.info(
            f"Total lexicon entries: {len(all_documents)} "
            f"({len(hebrew_docs)} Hebrew + {len(greek_docs)} Greek)"
        )

        if dry_run:
            return {
                "total_documents": len(all_documents),
                "hebrew_count": len(hebrew_docs),
                "greek_count": len(greek_docs),
                "sample_documents": all_documents[:3],  # Show first 3 as samples
            }

        # Import to Prism
        results = asyncio.run(
            import_documents_in_batches(
                all_documents,
                batch_size=batch_size,
                embed=embed,
                progress_callback=progress_callback,
            )
        )

        # Add lexicon-specific stats
        results["hebrew_count"] = len(hebrew_docs)
        results["greek_count"] = len(greek_docs)

        return results


async def verify_lexicon_import(strong_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Verify lexicon entries were imported correctly by searching for specific entries.

    Args:
        strong_ids: Optional list of Strong's IDs to verify (e.g., ["H1", "G26"])
                   If None, uses common examples

    Returns:
        Verification results with search results for each ID
    """
    from prism_client import PrismClient

    if strong_ids is None:
        # Common examples: H1 (father), H157 (love), G26 (agape), G2316 (God)
        strong_ids = ["H1", "H157", "G26", "G2316"]

    results = {}

    async with PrismClient() as client:
        # Check overall stats
        stats = await client.get_stats()
        results["prism_stats"] = stats

        # Count lexicon documents
        lexicon_count = await client.count_domain_documents("lexicon/strongs")
        results["lexicon_document_count"] = lexicon_count

        # Search for specific entries
        results["entries"] = {}
        for strong_id in strong_ids:
            search_results = await client.search_documents(
                query=strong_id, domain="lexicon/strongs", top_k=1
            )
            results["entries"][strong_id] = search_results.get("results", [])

    return results
