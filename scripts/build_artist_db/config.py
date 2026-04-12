"""
Configuration and shared resources for the artist database builder.

This module defines project paths, logging setup, in-memory cache,
and persistent HTTP sessions used across all API clients.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Any
import requests

# =============================================================================
# PROJECT PATHS
# =============================================================================
# Determine project root relative to this file's location
# build_artist_db/config.py -> build_artist_db -> scripts -> project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()

# Directory containing YouTube chart databases
CHARTS_DB_DIR = PROJECT_ROOT / "charts_archive" / "1_download-chart" / "databases"

# Output path for the artist database
ARTIST_DB_PATH = (
    PROJECT_ROOT
    / "charts_archive"
    / "2_1.countries-genres-artist"
    / "artist_countries_genres.db"
)

# Ensure the output directory exists
ARTIST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a logger for the module.

    Args:
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger(__name__)

# Default logger instance
logger = setup_logging()

# =============================================================================
# IN-MEMORY CACHE AND HTTP SESSIONS
# =============================================================================
# Global cache shared across all API clients to avoid redundant calls.
# Structure:
# {
#     'musicbrainz_country': {},
#     'wikidata_country': {},
#     'wikipedia_country': {},
#     'musicbrainz_genre': {},
#     'wikidata_genre': {},
#     'wikipedia_genre': {},
# }
_CACHE: Dict[str, Dict[str, Any]] = {
    'musicbrainz_country': {},
    'wikidata_country': {},
    'wikipedia_country': {},
    'musicbrainz_genre': {},
    'wikidata_genre': {},
    'wikipedia_genre': {},
}

# Reusable HTTP sessions with connection pooling
_SESSION_WIKIPEDIA = requests.Session()
_SESSION_WIKIDATA = requests.Session()
_SESSION_MUSICBRAINZ = requests.Session()


def get_cache() -> Dict[str, Dict[str, Any]]:
    """Return the global cache dictionary."""
    return _CACHE


def get_http_sessions() -> Dict[str, requests.Session]:
    """
    Return the reusable HTTP sessions.

    Returns:
        Dictionary with keys: 'wikipedia', 'wikidata', 'musicbrainz'
    """
    return {
        'wikipedia': _SESSION_WIKIPEDIA,
        'wikidata': _SESSION_WIKIDATA,
        'musicbrainz': _SESSION_MUSICBRAINZ,
    }
