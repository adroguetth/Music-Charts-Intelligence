"""
Country detection logic for artists.

This module orchestrates multi-source lookup (MusicBrainz, Wikipedia, Wikidata)
to determine an artist's country of origin. It includes name variation generation,
text normalization, and fallback to Meta AI (Muse Spark) when other sources fail.
"""

import re
import time
import unicodedata
from difflib import SequenceMatcher
from typing import Optional, Tuple, List

from .config import logger, get_cache, get_http_sessions
from .utils.text_utils import normalize_text, generate_all_variations, detect_script_from_name
from .utils.country_utils import validate_and_normalize_country  # <-- Importante

from .apis.wikipedia import (
    search_wikipedia_summary_country_cached,
    search_wikipedia_infobox_country_cached,
)
from .apis.wikidata import search_wikidata_country_cached
from .apis.musicbrainz import search_musicbrainz_country_cached
from .apis.ia_search_engine import search_ia_fallback


def search_country(artist: str) -> Tuple[Optional[str], str]:
    """
    Determine the country of origin for an artist using multiple sources.
    
    Search order:
    1. MusicBrainz (with name variations)
    2. Wikipedia EN (summary, then infobox)
    3. Wikipedia in priority languages based on script detection
    4. Wikidata
    5. Meta AI / Muse Spark (fallback)
    
    Args:
        artist: Artist name to search for.
    
    Returns:
        Tuple of (country name or None, source description string).
    """
    variations = generate_all_variations(artist)

    # 1. MusicBrainz
    for var in variations[:3]:
        country, source = search_musicbrainz_country_cached(var)
        if country:
            info = f" (var: {var})" if var != artist else ""
            return country, f"MusicBrainz{info}"
    time.sleep(0.8)

    # 2. Wikipedia English
    for var in variations[:3]:
        country = search_wikipedia_summary_country_cached(var, 'en')
        if country:
            info = f" (var: {var})" if var != artist else ""
            return country, f"Wikipedia EN summary{info}"

        country = search_wikipedia_infobox_country_cached(var, 'en')
        if country:
            info = f" (var: {var})" if var != artist else ""
            return country, f"Wikipedia EN infobox{info}"
    time.sleep(0.3)

    # 3. Wikipedia in priority languages based on script detection
    detected_lang = detect_script_from_name(artist)
    priority_langs = []
    if detected_lang:
        priority_langs.append(detected_lang)
    priority_langs.extend(['es', 'pt', 'fr', 'de', 'it', 'hi', 'ko', 'ja', 'zh', 'ar', 'tr', 'ru'])
    seen = set()
    priority_langs = [lang for lang in priority_langs if not (lang in seen or seen.add(lang))]

    for lang in priority_langs:
        for var in variations[:2]:
            country = search_wikipedia_summary_country_cached(var, lang)
            if country:
                info = f" (var: {var})" if var != artist else ""
                return country, f"Wikipedia {lang.upper()}{info}"
            time.sleep(0.2)

    # 4. Wikidata
    for var in variations[:3]:
        country = search_wikidata_country_cached(var)
        if country:
            info = f" (var: {var})" if var != artist else ""
            return country, f"Wikidata{info}"

    # 5. Meta AI fallback
    logger.debug(f"  🔍 Using Meta AI fallback for country: {artist}")
    ia_country, _, _ = search_ia_fallback(artist)
    if ia_country:
        return ia_country, "Meta AI (Muse Spark)"

    return None, "Not found"
