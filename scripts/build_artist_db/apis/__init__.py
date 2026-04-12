"""
API client modules for external data sources.

This package provides cached access to:
- MusicBrainz (country and genre)
- Wikidata (country and genre)
- Wikipedia (country and genre via infobox and summary)
- DeepSeek (fallback AI for country and genre)
"""

from .musicbrainz import (
    search_musicbrainz_country_cached,
    search_musicbrainz_genre_cached,
    extract_genre_from_musicbrainz,
)
from .wikidata import (
    search_wikidata_country_cached,
    search_wikidata_genre_cached,
)
from .wikipedia import (
    search_wikipedia_infobox_country_cached,
    search_wikipedia_summary_country_cached,
    search_wikipedia_infobox_genre_cached,
    search_wikipedia_summary_genre_cached,
)
from .deepseek import search_deepseek_fallback, _get_deepseek_client

__all__ = [
    # MusicBrainz
    "search_musicbrainz_country_cached",
    "search_musicbrainz_genre_cached",
    "extract_genre_from_musicbrainz",
    # Wikidata
    "search_wikidata_country_cached",
    "search_wikidata_genre_cached",
    # Wikipedia
    "search_wikipedia_infobox_country_cached",
    "search_wikipedia_summary_country_cached",
    "search_wikipedia_infobox_genre_cached",
    "search_wikipedia_summary_genre_cached",
    # DeepSeek
    "search_deepseek_fallback",
    "_get_deepseek_client",
]
