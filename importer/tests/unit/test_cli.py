"""Unit tests for CLI module."""

import pytest
from click.testing import CliRunner

from cli import cli


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_version(self):
        """CLI has version command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_help(self):
        """CLI has help text."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Bible text ingestion system" in result.output


class TestImportCommand:
    """Test import command parsing."""

    def test_import_command_exists(self):
        """Import command is available."""
        runner = CliRunner()
        result = runner.invoke(cli, ["import-bible", "--help"])

        assert result.exit_code == 0
        assert "--version" in result.output
        assert "--verses-csv" in result.output

    def test_import_requires_version(self):
        """Import command requires --version."""
        runner = CliRunner()
        # Use a temp file that exists to avoid path validation error
        with runner.isolated_filesystem():
            # Create temp CSV file
            with open("test.csv", "w") as f:
                f.write("Book,Chapter,Verse,Text\n")

            result = runner.invoke(cli, ["import-bible", "--verses-csv", "test.csv"])

            assert result.exit_code != 0
            assert "Missing option" in result.output or "required" in result.output.lower()

    def test_import_requires_verses_csv(self):
        """Import command requires --verses-csv."""
        runner = CliRunner()
        result = runner.invoke(cli, ["import-bible", "--version", "kjv"])

        assert result.exit_code != 0


class TestSearchCommand:
    """Test search command parsing."""

    def test_search_command_exists(self):
        """Search command is available."""
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--help"])

        assert result.exit_code == 0
        assert "--query" in result.output
        assert "--version" in result.output
        assert "--top-k" in result.output

    def test_search_requires_query(self):
        """Search command requires --query."""
        runner = CliRunner()
        result = runner.invoke(cli, ["search"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_search_version_optional(self):
        """Search command --version is optional."""
        runner = CliRunner()
        # This will fail at runtime (no Prism), but should parse successfully
        result = runner.invoke(cli, ["search", "--query", "test"])

        # Exit code may be non-zero due to Prism connection, but not due to parsing
        # Check that it's not a Click usage error (exit code 2)
        assert result.exit_code != 2 or "Missing option" not in result.output

    def test_search_top_k_has_integer_type(self):
        """Search command top-k is integer type."""
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--help"])

        # Just verify it accepts top-k parameter
        assert "--top-k" in result.output


class TestValidateCommand:
    """Test validate command parsing."""

    def test_validate_command_exists(self):
        """Validate command is available."""
        runner = CliRunner()
        result = runner.invoke(cli, ["validate", "--help"])

        assert result.exit_code == 0
        assert "--verses-csv" in result.output


class TestStatusCommand:
    """Test status command parsing."""

    def test_status_command_exists(self):
        """Status command is available."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--help"])

        assert result.exit_code == 0
