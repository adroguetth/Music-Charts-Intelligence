"""
Artist Country & Genre Detection Module.

This module provides functionality to enrich artist data with geographic
and genre metadata from multiple sources (MusicBrainz, Wikidata, Wikipedia).
It is designed to be used by the main orchestration script.
"""

from .config import (
    PROJECT_ROOT,
    CHARTS_DB_DIR,
    ARTIST_DB_PATH,
    setup_logging,
    get_cache,
    get_http_sessions,
)

from .country_detector import search_country, validate_and_normalize_country
from .genre_detector import search_artist_genre, normalize_genre

__all__ = [
    "PROJECT_ROOT",
    "CHARTS_DB_DIR",
    "ARTIST_DB_PATH",
    "setup_logging",
    "get_cache",
    "get_http_sessions",
    "search_country",
    "validate_and_normalize_country",
    "search_artist_genre",
    "normalize_genre",
]
