"""
Utility functions for the artist database builder.

This package provides text processing, caching, database operations,
and artist name parsing utilities.
"""

from .text_utils import (
    normalize_text,
    generate_name_variations,
    remove_artist_prefixes,
    generate_all_variations,
    detect_script_from_name,
)
from .cache import get_cache, get_http_sessions
from .db_utils import (
    create_database,
    artist_in_database,
    insert_artist,
    count_artists_in_database,
    get_latest_chart_database,
    get_artists_from_chart_db,
)
from .artist_parser import split_artists
from .country_utils import validate_and_normalize_country

__all__ = [
    # text_utils
    "normalize_text",
    "generate_name_variations",
    "remove_artist_prefixes",
    "generate_all_variations",
    "detect_script_from_name",
    # cache
    "get_cache",
    "get_http_sessions",
    # db_utils
    "create_database",
    "artist_in_database",
    "insert_artist",
    "count_artists_in_database",
    "get_latest_chart_database",
    "get_artists_from_chart_db",
    # artist_parser
    "split_artists",
    # country_utils
    "validate_and_normalize_country",
]
