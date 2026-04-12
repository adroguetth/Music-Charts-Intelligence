"""
Genre detection and voting system for artists.

This module determines an artist's primary musical genre using a weighted
voting system across multiple sources (MusicBrainz, Wikidata, Wikipedia).
It applies country-specific rules and normalizes raw genre strings to a
standardized macro-genre taxonomy.
"""

import time
import re
from collections import defaultdict
from typing import Optional, Tuple, List

from .config import logger, get_cache, get_http_sessions
from .utils.text_utils import normalize_text, generate_all_variations, detect_script_from_name
from .apis.musicbrainz import search_musicbrainz_genre_cached
from .apis.wikidata import search_wikidata_genre_cached
from .apis.wikipedia import (
    search_wikipedia_infobox_genre_cached,
    search_wikipedia_summary_genre_cached,
)
from .apis.deepseek import search_deepseek_fallback

# Dictionary imports (assumed to exist in dictionaries/)
from .dictionaries.genres import GENRE_MAPPINGS
from .dictionaries.macro_genres import MACRO_GENRES, GENERIC_MACROS
from .dictionaries.country_rules import COUNTRY_GENRE_PRIORITY, COUNTRY_SPECIFIC_RULES, DEFAULT_GENRE_PRIORITY
from .dictionaries.stopwords import GENRE_STOPWORDS


def normalize_genre(genre_text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalize a raw genre string to (macro_genre, subgenre).

    Args:
        genre_text: Raw genre string from a source.

    Returns:
        Tuple of (macro_genre, subgenre) or (None, None) if no mapping.
    """
    if not genre_text:
        return None, None

    text_norm = normalize_text(genre_text)

    # Skip stopwords
    if text_norm in GENRE_STOPWORDS:
        return None, None

    # Direct lookup
    if text_norm in GENRE_MAPPINGS:
        return GENRE_MAPPINGS[text_norm]

    # Substring match for longer variants
    sorted_mappings = sorted(GENRE_MAPPINGS.keys(), key=len, reverse=True)
    for genre_variant in sorted_mappings:
        if genre_variant in text_norm and len(genre_variant) > 3:
            return GENRE_MAPPINGS[genre_variant]

    # Handle hyphen/space variations
    text_no_hyphen = text_norm.replace('-', ' ')
    if text_no_hyphen != text_norm and text_no_hyphen in GENRE_MAPPINGS:
        return GENRE_MAPPINGS[text_no_hyphen]

    text_with_hyphen = text_norm.replace(' ', '-')
    if text_with_hyphen != text_norm and text_with_hyphen in GENRE_MAPPINGS:
        return GENRE_MAPPINGS[text_with_hyphen]

    return None, None


def select_primary_genre(
    artist: str,
    genre_candidates: List[Tuple[str, int, str]],
    country: Optional[str] = None,
    detected_lang: Optional[str] = None,
) -> Optional[str]:
    """
    Select the primary macro-genre using a weighted voting system.

    Args:
        artist: Artist name (unused, for future logging).
        genre_candidates: List of (subgenre, weight, source) tuples.
        country: Optional country for regional bonuses.
        detected_lang: Optional language code from script detection.

    Returns:
        Selected macro-genre string or None.
    """
    if not genre_candidates:
        return None

    macro_votes = defaultdict(float)
    detailed_info = []

    for subgenre, weight, source in genre_candidates:
        macro, _ = normalize_genre(subgenre)
        if macro:
            final_weight = weight

            # Source-based bonuses
            if 'musicbrainz' in source:
                final_weight *= 1.5
            if 'infobox' in source:
                final_weight *= 1.2
            if 'wikidata' in source:
                final_weight *= 1.3

            # Specific term bonuses
            sub_lower = subgenre.lower()
            # Reggaeton / Latin
            if any(term in sub_lower for term in ['reggaeton', 'reggaetón', 'regueton', 'reguetón', 'trap latino', 'urbano', 'dembow', 'perreo']):
                final_weight *= 1.4
                macro = 'Reggaetón/Trap Latino'
            # K-Pop
            if any(term in sub_lower for term in ['k-pop', 'kpop', 'korean pop', 'k-rap', 'k-r&b']):
                final_weight *= 1.4
                macro = 'K-Pop/K-Rock'
            # J-Pop
            if any(term in sub_lower for term in ['j-pop', 'jpop', 'japanese pop']):
                final_weight *= 1.4
                macro = 'J-Pop/J-Rock'
            # Indian / South Asian
            if any(term in sub_lower for term in ['indian', 'bollywood', 'punjabi', 'bhangra']):
                final_weight *= 1.3
            if any(term in sub_lower for term in ['pakistani pop', 'urdu', 'lollywood']):
                final_weight *= 1.3
            if any(term in sub_lower for term in ['bangladeshi pop', 'bengali']):
                final_weight *= 1.3
            # Brazilian
            if any(term in sub_lower for term in ['sertanejo', 'funk brasileiro', 'funk carioca', 'funk']):
                final_weight *= 1.4
            # African
            if any(term in sub_lower for term in ['afrobeats', 'naija', 'amapiano']):
                final_weight *= 1.4

            macro_votes[macro] += final_weight
            detailed_info.append(f"{subgenre}→{macro} ({source}:{final_weight:.1f})")
        else:
            # Check if it's already a known macro genre
            for known_macro in MACRO_GENRES:
                if subgenre.lower() == known_macro.lower():
                    macro_votes[known_macro] += weight
                    detailed_info.append(f"{subgenre}→{known_macro} ({source})")
                    break

    # Map generic genres to regional ones if country rule exists
    if country and country in COUNTRY_SPECIFIC_RULES:
        rule = COUNTRY_SPECIFIC_RULES[country]
        map_to = rule.get("map_generic_to")
        if map_to:
            for subgenre, weight, source in genre_candidates:
                macro, _ = normalize_genre(subgenre)
                if macro and macro in GENERIC_MACROS:
                    macro_votes[map_to] += weight
                    detailed_info.append(f"map_generic: {subgenre}→{map_to} (weight {weight:.1f})")

    # Apply country priority bonuses
    if country and macro_votes:
        priority = COUNTRY_GENRE_PRIORITY.get(country, DEFAULT_GENRE_PRIORITY)
        for macro in list(macro_votes.keys()):
            if macro in priority:
                idx = priority.index(macro)
                if idx == 0:
                    macro_votes[macro] *= 2.0
                elif idx == 1:
                    macro_votes[macro] *= 1.5
                else:
                    macro_votes[macro] *= 1.2

    # Apply country-specific keyword/force rules
    if country and macro_votes and country in COUNTRY_SPECIFIC_RULES:
        rule = COUNTRY_SPECIFIC_RULES[country]
        for macro in list(macro_votes.keys()):
            for subgenre, _, _ in genre_candidates:
                sub_lower = subgenre.lower()
                if any(kw in sub_lower for kw in rule["keywords"]):
                    if "force_macro" in rule and macro != rule["force_macro"]:
                        peso = macro_votes.pop(macro)
                        macro_votes[rule["force_macro"]] += peso * rule["bonus_extra"]
                    elif "prefer_genre" in rule and macro == rule["prefer_genre"]:
                        macro_votes[macro] *= rule["bonus_extra"]
                    else:
                        macro_votes[macro] *= rule["bonus_extra"]
                    break

    # Bonus based on detected script and country
    if detected_lang and country:
        # South Asia
        if detected_lang in ['hi', 'ta', 'te', 'ml', 'kn', 'gu', 'or', 'bn'] and country in ['India', 'Pakistan', 'Bangladesh']:
            for m in ['Indian Pop', 'Pakistani Pop', 'Bangladeshi Pop/Rock']:
                if m in macro_votes:
                    macro_votes[m] *= 1.2
        # Korea
        if detected_lang == 'ko' and country == 'South Korea':
            if 'K-Pop/K-Rock' in macro_votes:
                macro_votes['K-Pop/K-Rock'] *= 1.2
        # Japan
        if detected_lang == 'ja' and country == 'Japan':
            if 'J-Pop/J-Rock' in macro_votes:
                macro_votes['J-Pop/J-Rock'] *= 1.2
        # China
        if detected_lang == 'zh' and country == 'China':
            if 'C-Pop/C-Rock' in macro_votes:
                macro_votes['C-Pop/C-Rock'] *= 1.2
        # Mongolia
        if detected_lang == 'mn' and country == 'Mongolia':
            if 'Mongolian Pop/Rock/Metal' in macro_votes:
                macro_votes['Mongolian Pop/Rock/Metal'] *= 1.2
        # Arab world
        if detected_lang == 'ar' and country in ['Egypt', 'Saudi Arabia', 'UAE', 'Morocco', 'Algeria', 'Tunisia']:
            if 'Arabic Pop/Rock' in macro_votes:
                macro_votes['Arabic Pop/Rock'] *= 1.2
        # Turkey
        if detected_lang == 'tr' and country == 'Turkey':
            if 'Turkish Pop/Rock' in macro_votes:
                macro_votes['Turkish Pop/Rock'] *= 1.2
        # Kazakhstan
        if detected_lang == 'kk' and country == 'Kazakhstan':
            if 'Q-pop/Q-rock' in macro_votes:
                macro_votes['Q-pop/Q-rock'] *= 1.2

    if macro_votes:
        primary_macro = max(macro_votes.items(), key=lambda x: x[1])[0]
        return primary_macro

    return None


def search_artist_genre(artist: str, country: Optional[str] = None) -> Tuple[Optional[str], str]:
    """
    Determine the primary genre for an artist using multiple sources.

    Search order:
    1. MusicBrainz
    2. Wikidata
    3. Wikipedia (priority languages based on country and script)
    4. DeepSeek API (fallback)
    5. Country priority fallback

    Args:
        artist: Artist name to search for.
        country: Optional known country to improve accuracy.

    Returns:
        Tuple of (macro_genre or None, source description string).
    """
    all_candidates = []
    variations = generate_all_variations(artist)
    detected_lang = detect_script_from_name(artist)

    # 1. MusicBrainz
    for var in variations[:2]:
        candidates = search_musicbrainz_genre_cached(var)
        all_candidates.extend(candidates)
        if candidates:
            break
        time.sleep(0.5)

    # 2. Wikidata
    if not all_candidates:
        for var in variations[:2]:
            candidates = search_wikidata_genre_cached(var)
            all_candidates.extend(candidates)
            if candidates:
                break
            time.sleep(0.5)

    MIN_CANDIDATES = 3

    # 3. Wikipedia in priority languages
    priority_langs = []
    if country:
        country_lang_map = {
            'India': ['hi', 'ta', 'te', 'ml', 'kn', 'gu', 'or', 'bn', 'en'],
            'Pakistan': ['ur', 'en'],
            'Bangladesh': ['bn', 'en'],
            'South Korea': ['ko', 'en'],
            'Japan': ['ja', 'en'],
            'China': ['zh', 'en'],
            'Mongolia': ['mn', 'en'],
            'Kazakhstan': ['kk', 'ru', 'en'],
            'Nepal': ['ne', 'en'],
            'Russia': ['ru', 'en'],
            'Ukraine': ['uk', 'ru', 'en'],
            'Brazil': ['pt', 'en'],
            'Mexico': ['es', 'en'],
            'Spain': ['es', 'en'],
            'France': ['fr', 'en'],
            'Germany': ['de', 'en'],
            'Italy': ['it', 'en'],
            'Turkey': ['tr', 'en'],
            'Egypt': ['ar', 'en'],
            'Israel': ['he', 'en'],
        }
        priority_langs.extend(country_lang_map.get(country, ['en', 'es']))
    else:
        if detected_lang:
            priority_langs.append(detected_lang)
        priority_langs.append('en')

    seen = set()
    priority_langs = [lang for lang in priority_langs if not (lang in seen or seen.add(lang))]

    if len(all_candidates) < MIN_CANDIDATES:
        for var in variations[:1]:
            for lang in priority_langs:
                candidates = search_wikipedia_infobox_genre_cached(var, lang)
                all_candidates.extend(candidates)
                if len(all_candidates) >= MIN_CANDIDATES:
                    break
                if not candidates:
                    candidates = search_wikipedia_summary_genre_cached(var, lang)
                    all_candidates.extend(candidates)
                if len(all_candidates) >= MIN_CANDIDATES:
                    break
                time.sleep(0.3)
            if len(all_candidates) >= MIN_CANDIDATES:
                break

    if len(all_candidates) < MIN_CANDIDATES:
        other_langs = ['es', 'pt', 'fr', 'de', 'it', 'ru', 'ar', 'zh', 'ja', 'ko']
        for lang in other_langs:
            if lang in priority_langs:
                continue
            for var in variations[:1]:
                candidates = search_wikipedia_infobox_genre_cached(var, lang)
                all_candidates.extend(candidates)
                if len(all_candidates) >= MIN_CANDIDATES:
                    break
                if not candidates:
                    candidates = search_wikipedia_summary_genre_cached(var, lang)
                    all_candidates.extend(candidates)
                if len(all_candidates) >= MIN_CANDIDATES:
                    break
                time.sleep(0.3)
            if len(all_candidates) >= MIN_CANDIDATES:
                break

    # 4. DeepSeek fallback
    if not all_candidates:
        logger.debug(f"  🔍 Using DeepSeek fallback for genre: {artist} (country: {country})")
        _, deepseek_genre, _ = search_deepseek_fallback(artist, context_country=country)
        if deepseek_genre:
            macro, _ = normalize_genre(deepseek_genre)
            if macro:
                logger.info(f"  🤖 DeepSeek genre for {artist}: {macro} (from: {deepseek_genre})")
                return macro, f"DeepSeek API (genre: {deepseek_genre})"
            else:
                logger.info(f"  🤖 DeepSeek raw genre for {artist}: {deepseek_genre}")
                return deepseek_genre, f"DeepSeek API (raw: {deepseek_genre})"

    # 5. Country fallback
    if not all_candidates and country:
        priority = COUNTRY_GENRE_PRIORITY.get(country, DEFAULT_GENRE_PRIORITY)
        if priority:
            return priority[0], f"Genre: country fallback ({country})"

    if all_candidates:
        primary_genre = select_primary_genre(artist, all_candidates, country, detected_lang)
        sources = set(s for _, _, s in all_candidates)
        return primary_genre, f"Genre: {', '.join(sources)}"

    return None, "Genre not found"
