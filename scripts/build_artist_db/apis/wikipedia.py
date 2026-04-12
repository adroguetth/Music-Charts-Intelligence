"""
Wikipedia API client for country and genre extraction.

Uses the MediaWiki API to parse infoboxes and page summaries.
"""

import re
import requests
from typing import Optional, List, Tuple

from ..config import logger
from ..utils.cache import get_cache, get_http_sessions
from ..utils.text_utils import normalize_text
from ..country_detector import validate_and_normalize_country
from ..genre_detector import normalize_genre


# Stopwords to filter out false positives in genre extraction
GENRE_STOPWORDS_FOR_WIKIPEDIA = {
    'american', 'british', 'canadian', 'australian', 'indian', 'korean',
    'japanese', 'mexican', 'spanish', 'french', 'german', 'italian',
    'brazilian', 'argentine', 'colombian', 'chilean', 'peruvian',
    'venezuelan', 'cuban', 'dominican', 'african', 'nigerian',
    'south african', 'kenyan', 'egyptian', 'moroccan', 'israeli',
    'turkish', 'russian', 'ukrainian', 'polish', 'swedish', 'norwegian',
    'danish', 'finnish', 'dutch', 'belgian', 'swiss', 'austrian',
    'portuguese', 'greek', 'irish', 'scottish', 'welsh', 'english',
    'famous', 'popular', 'well-known', 'acclaimed', 'award-winning',
    'multi-platinum', 'grammy', 'grammy-winning', 'oscar', 'oscar-winning',
    'best-selling', 'successful', 'influential', 'legendary', 'iconic'
}


def search_wikipedia_infobox_country_cached(artist: str, lang: str = 'en') -> Optional[str]:
    """
    Extract country from Wikipedia infobox fields (origin, birth_place, location, etc.).

    Args:
        artist: Artist name.
        lang: Wikipedia language code.

    Returns:
        Canonical country name or None.
    """
    cache = get_cache()
    key = (artist, lang)
    if key in cache['wikipedia_country']:
        return cache['wikipedia_country'][key]

    sessions = get_http_sessions()
    session = sessions['wikipedia']

    try:
        url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            'action': 'query',
            'titles': artist,
            'redirects': 1,
            'format': 'json'
        }
        resp = session.get(url, params=params, timeout=8)
        data = resp.json()

        pages = data['query']['pages']
        page_id = next(iter(pages))
        title = pages[page_id].get('title', artist)

        params = {
            'action': 'parse',
            'page': title,
            'prop': 'wikitext',
            'format': 'json',
            'redirects': True
        }
        resp = session.get(url, params=params, timeout=10)
        data = resp.json()

        if 'parse' not in data:
            cache['wikipedia_country'][key] = None
            return None

        wikitext = data['parse']['wikitext']['*']
        infobox_pattern = r'\{\{\s*Infobox (?:musical artist|band)[\s\S]*?\}\}'
        infobox_match = re.search(infobox_pattern, wikitext, re.IGNORECASE)

        if not infobox_match:
            cache['wikipedia_country'][key] = None
            return None

        infobox = infobox_match.group()
        fields = ['origin', 'birth_place', 'location', 'from', 'country']

        for field in fields:
            field_pattern = r'\|?\s*' + field + r'\s*=\s*([^\n|]+)'
            field_match = re.search(field_pattern, infobox, re.IGNORECASE)
            if field_match:
                value = field_match.group(1).strip()
                value = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', value)
                value = re.sub(r'<[^>]+>', '', value)
                country_norm = validate_and_normalize_country(value)
                if country_norm:
                    cache['wikipedia_country'][key] = country_norm
                    return country_norm

        cache['wikipedia_country'][key] = None
        return None

    except Exception as e:
        logger.debug(f"Wikipedia infobox {lang} country error for {artist}: {e}")
        cache['wikipedia_country'][key] = None
        return None


def search_wikipedia_summary_country_cached(artist: str, lang: str = 'en') -> Optional[str]:
    """
    Extract country from Wikipedia page summary using regex patterns.

    Args:
        artist: Artist name.
        lang: Wikipedia language code.

    Returns:
        Canonical country name or None.
    """
    cache = get_cache()
    key = (artist, lang)
    if key in cache['wikipedia_country']:
        return cache['wikipedia_country'][key]

    sessions = get_http_sessions()
    session = sessions['wikipedia']

    try:
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(artist)}"
        headers = {'User-Agent': 'ArtistDB/5.0'}
        resp = session.get(url, headers=headers, timeout=8)

        if resp.status_code != 200:
            cache['wikipedia_country'][key] = None
            return None

        data = resp.json()
        extract = data.get('extract', '').lower()

        if not extract:
            cache['wikipedia_country'][key] = None
            return None

        patterns = [
            r'is\s+(?:a|an)\s+([a-z\s]+?)\s+(?:singer|rapper|musician|artist|songwriter|producer|dj|band|group)',
            r'was\s+(?:a|an)\s+([a-z\s]+?)\s+(?:singer|rapper|musician|artist|songwriter|producer|dj|band|group)',
            r'are\s+(?:a|an)\s+([a-z\s]+?)\s+(?:band|group|duo)',
            r'from\s+([a-z\s]+?)(?:\.|,|\s+who|\s+is|\s+was)',
            r'born\s+in\s+([^,]+?)(?:\.|,)',
            r'formed\s+in\s+([^,]+?)(?:\.|,)',
        ]

        for pattern in patterns:
            match = re.search(pattern, extract)
            if match:
                candidate = match.group(1).strip()
                if 2 <= len(candidate) <= 35:
                    country = validate_and_normalize_country(candidate)
                    if country:
                        cache['wikipedia_country'][key] = country
                        return country

        cache['wikipedia_country'][key] = None
        return None

    except Exception as e:
        logger.debug(f"Wikipedia summary {lang} country error for {artist}: {e}")
        cache['wikipedia_country'][key] = None
        return None


def search_wikipedia_infobox_genre_cached(artist: str, lang: str = 'en') -> List[Tuple[str, int, str]]:
    """
    Extract genre from Wikipedia infobox 'genre' or 'género' fields.

    Args:
        artist: Artist name.
        lang: Wikipedia language code.

    Returns:
        List of (genre_name, weight=2, source) tuples.
    """
    cache = get_cache()
    key = (artist, lang)
    if key in cache['wikipedia_genre']:
        return cache['wikipedia_genre'][key]

    sessions = get_http_sessions()
    session = sessions['wikipedia']
    candidates = []

    try:
        url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            'action': 'query',
            'titles': artist,
            'redirects': 1,
            'format': 'json'
        }
        resp = session.get(url, params=params, timeout=8)
        data = resp.json()

        pages = data['query']['pages']
        page_id = next(iter(pages))
        title = pages[page_id].get('title', artist)

        params = {
            'action': 'parse',
            'page': title,
            'prop': 'wikitext',
            'format': 'json',
            'redirects': True
        }
        resp = session.get(url, params=params, timeout=10)
        data = resp.json()

        if 'parse' not in data:
            cache['wikipedia_genre'][key] = candidates
            return candidates

        wikitext = data['parse']['wikitext']['*']
        infobox_pattern = r'\{\{\s*Infobox (?:musical artist|band)[\s\S]*?\}\}'
        infobox_match = re.search(infobox_pattern, wikitext, re.IGNORECASE)

        if not infobox_match:
            cache['wikipedia_genre'][key] = candidates
            return candidates

        infobox = infobox_match.group()
        genre_fields = ['genre', 'género', 'genres', 'géneros']

        for field in genre_fields:
            pattern = r'\|?\s*' + field + r'\s*=\s*([^\n|]+)'
            match = re.search(pattern, infobox, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                value = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', value)
                value = re.sub(r'<[^>]+>', '', value)
                value = re.sub(r'\{\{[^}]+\}\}', '', value)

                separators = r',|\sand\s|\sy\s|;'
                genres = re.split(separators, value)

                for g in genres:
                    g = g.strip().lower()
                    if g and len(g) > 2 and g not in GENRE_STOPWORDS_FOR_WIKIPEDIA:
                        candidates.append((g, 2, f'wikipedia_{lang}_infobox'))

    except Exception as e:
        logger.debug(f"Wikipedia infobox genre error for {artist} ({lang}): {e}")

    cache['wikipedia_genre'][key] = candidates
    return candidates


def search_wikipedia_summary_genre_cached(artist: str, lang: str = 'en') -> List[Tuple[str, int, str]]:
    """
    Extract genre hints from Wikipedia page summary using regex patterns.

    Args:
        artist: Artist name.
        lang: Wikipedia language code.

    Returns:
        List of (genre_name, weight, source) tuples.
    """
    cache = get_cache()
    key = (artist, lang)
    if key in cache['wikipedia_genre']:
        return cache['wikipedia_genre'][key]

    sessions = get_http_sessions()
    session = sessions['wikipedia']
    candidates = []

    try:
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(artist)}"
        headers = {'User-Agent': 'ArtistDB/5.0'}
        resp = session.get(url, headers=headers, timeout=8)

        if resp.status_code != 200:
            cache['wikipedia_genre'][key] = candidates
            return candidates

        data = resp.json()
        extract = data.get('extract', '').lower()

        if not extract:
            cache['wikipedia_genre'][key] = candidates
            return candidates

        # Pattern: "is a [genre] singer/rapper/musician..."
        pattern1 = r'is\s+(?:a|an)\s+([a-z\s\-]+?)\s+(?:singer|rapper|musician|artist|songwriter|producer|dj|band|group|duo|trio)'
        matches = re.findall(pattern1, extract)
        for match in matches:
            candidate = match.strip()
            subgenres = re.split(r'\s+(?:and|y)\s+|\s*,\s*', candidate)
            for sub in subgenres:
                sub = sub.strip()
                if sub and len(sub) > 2 and sub not in GENRE_STOPWORDS_FOR_WIKIPEDIA:
                    candidates.append((sub, 1, f'wikipedia_{lang}_summary'))

        # Pattern: "[nationality] [genre] singer..."
        pattern2 = r'(?:american|british|canadian|australian|indian|korean|japanese|mexican|spanish|french|german|italian|brazilian|argentine|colombian|chilean|peruvian|venezuelan|puerto rican|cuban|dominican|african|nigerian|south african|kenyan|egyptian|moroccan|israeli|turkish|russian|ukrainian|polish|swedish|norwegian|danish|finnish|dutch|belgian|swiss|austrian|portuguese|greek|irish|scottish|welsh|english)\s+([a-z\s\-]+?)\s+(?:singer|rapper|musician|artist|songwriter|producer|dj|band|group|duo)'
        matches = re.findall(pattern2, extract)
        for match in matches:
            candidate = match[0].strip() if isinstance(match, tuple) else match.strip()
            subgenres = re.split(r'\s+(?:and|y)\s+|\s*,\s*', candidate)
            for sub in subgenres:
                sub = sub.strip()
                if sub and len(sub) > 2 and sub not in GENRE_STOPWORDS_FOR_WIKIPEDIA:
                    candidates.append((sub, 1, f'wikipedia_{lang}_summary'))

        # Pattern: "are a [genre] band/group"
        pattern3 = r'are\s+(?:a|an)\s+([a-z\s\-]+?)\s+(?:band|group|duo)'
        matches = re.findall(pattern3, extract)
        for match in matches:
            candidate = match.strip()
            subgenres = re.split(r'\s+(?:and|y)\s+|\s*,\s*', candidate)
            for sub in subgenres:
                sub = sub.strip()
                if sub and len(sub) > 2 and sub not in GENRE_STOPWORDS_FOR_WIKIPEDIA:
                    candidates.append((sub, 1, f'wikipedia_{lang}_summary'))

        # Pattern: "playing [genre] music"
        pattern4 = r'playing\s+([a-z\s\-]+?)\s+music'
        matches = re.findall(pattern4, extract)
        for match in matches:
            candidate = match.strip()
            if candidate and len(candidate) > 2 and candidate not in GENRE_STOPWORDS_FOR_WIKIPEDIA:
                candidates.append((candidate, 1, f'wikipedia_{lang}_summary'))

        # Pattern: "known for their [genre] music"
        pattern5 = r'known\s+for\s+their\s+([a-z\s\-]+?)\s+music'
        matches = re.findall(pattern5, extract)
        for match in matches:
            candidate = match.strip()
            if candidate and len(candidate) > 2 and candidate not in GENRE_STOPWORDS_FOR_WIKIPEDIA:
                candidates.append((candidate, 1, f'wikipedia_{lang}_summary'))

        # Pattern: "genre is [genre]"
        pattern6 = r'genre\s+is\s+([a-z\s\-]+?)(?:\.|,|$)'
        matches = re.findall(pattern6, extract)
        for match in matches:
            candidate = match.strip()
            if candidate and len(candidate) > 2 and candidate not in GENRE_STOPWORDS_FOR_WIKIPEDIA:
                candidates.append((candidate, 1, f'wikipedia_{lang}_summary'))

        # Keyword matching (low weight)
        genre_keywords = [
            'pop', 'rock', 'hip hop', 'rap', 'trap', 'reggaeton', 'reggaetón',
            'cumbia', 'bachata', 'salsa', 'metal', 'punk', 'indie', 'alternative',
            'electrónica', 'dance', 'k-pop', 'j-pop', 'bollywood', 'country',
            'folk', 'reggae', 'dancehall', 'afrobeats', 'edm', 'house', 'techno',
            'pakistani pop', 'bangladeshi pop', 'urdu', 'punjabi', 'bhangra',
            'sertanejo', 'funk brasileiro', 'amapiano', 'afrobeat'
        ]
        for keyword in genre_keywords:
            if keyword in extract and keyword not in GENRE_STOPWORDS_FOR_WIKIPEDIA:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, extract):
                    candidates.append((keyword, 0.5, f'wikipedia_{lang}_keyword'))

    except Exception as e:
        logger.debug(f"Wikipedia summary genre error for {artist} ({lang}): {e}")

    cache['wikipedia_genre'][key] = candidates
    return candidates
