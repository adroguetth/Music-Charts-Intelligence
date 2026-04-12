"""
Dictionary data for artist country and genre detection.

This package contains canonical mappings for:
- Country names, cities, and demonyms (countries.py)
- Genre mappings to macro-genres (genres.py)
- List of valid macro-genres (macro_genres.py)
- Country-specific genre priorities and rules (country_rules.py)
- Stopwords for genre filtering (stopwords.py)
"""

from .macro_genres import MACRO_GENRES, GENERIC_MACROS
from .country_rules import (
    COUNTRY_GENRE_PRIORITY,
    COUNTRY_SPECIFIC_RULES,
    DEFAULT_GENRE_PRIORITY,
)
from .stopwords import GENRE_STOPWORDS

__all__ = [
    "MACRO_GENRES",
    "GENERIC_MACROS",
    "COUNTRY_GENRE_PRIORITY",
    "COUNTRY_SPECIFIC_RULES",
    "DEFAULT_GENRE_PRIORITY",
    "GENRE_STOPWORDS",
]
