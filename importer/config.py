"""Configuration for Bible importer."""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


class BibleImporterSettings(BaseSettings):
    """Settings for Bible importer."""

    # Prism API configuration
    prism_base_url: str = Field(
        default="http://localhost:8100",
        description="Base URL for Prism API",
    )
    prism_timeout: int = Field(
        default=300,
        description="Timeout for Prism API calls in seconds",
    )

    # Chunking configuration
    target_chunk_tokens: int = Field(
        default=350,
        description="Target number of tokens per chunk",
    )
    min_chunk_tokens: int = Field(
        default=50,
        description="Minimum number of tokens per chunk (single verse floor)",
    )
    max_chunk_tokens: int = Field(
        default=500,
        description="Maximum number of tokens per chunk (hard limit)",
    )

    # Import configuration
    batch_size: int = Field(
        default=100,
        description="Number of documents to import per API call",
    )
    embed: bool = Field(
        default=True,
        description="Whether to generate embeddings during import",
    )

    # Data paths
    data_dir: Path = Field(
        default=Path("/dpool/aiml-stack/data/bible"),
        description="Base directory for Bible CSV data",
    )

    class Config:
        env_prefix = "BIBLE_IMPORTER_"
        case_sensitive = False


# Global settings instance
settings = BibleImporterSettings()
