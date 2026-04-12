"""
MusicBrainz API client for country and genre lookup.

Uses the MusicBrainz REST API with caching and name variations.
"""

import time
from difflib import SequenceMatcher
from typing import Optional, Tuple, List

from ..config import logger
from ..utils.cache import get_cache, get_http_sessions
from ..utils.text_utils import generate_all_variations
from ..country_detector import validate_and_normalize_country


def extract_genre_from_musicbrainz(mb_data: dict) -> List[Tuple[str, int, str]]:
    """
    Extract genre tags from a MusicBrainz artist record.

    Args:
        mb_data: MusicBrainz artist JSON data.

    Returns:
        List of (genre_name, count, source) tuples.
    """
    candidates = []
    if 'genres' in mb_data:
        for genre in mb_data['genres'][:5]:
            name = genre.get('name', '')
            count = genre.get('count', 1)
            if name:
                candidates.append((name.lower(), count, 'musicbrainz_genres'))
    if 'tags' in mb_data and not candidates:
        for tag in mb_data['tags'][:5]:
            name = tag.get('name', '')
            count = tag.get('count', 1)
            if name:
                candidates.append((name.lower(), count, 'musicbrainz_tags'))
    return candidates


def search_musicbrainz_country_cached(artist: str) -> Tuple[Optional[str], str]:
    """
    Search MusicBrainz for an artist's country of origin.

    Uses name variations and scoring to find the best match.

    Args:
        artist: Artist name to search.

    Returns:
        Tuple of (country or None, source description).
    """
    cache = get_cache()
    if artist in cache['musicbrainz_country']:
        return cache['musicbrainz_country'][artist]

    sessions = get_http_sessions()
    session = sessions['musicbrainz']

    try:
        url = "https://musicbrainz.org/ws/2/artist/"
        headers = {'User-Agent': 'ArtistDB/5.0 (contact@example.com)'}
        params = {'query': artist, 'fmt': 'json', 'limit': 5}
        resp = session.get(url, headers=headers, params=params, timeout=10)

        if resp.status_code != 200:
            cache['musicbrainz_country'][artist] = (None, "Not found")
            return None, "Not found"

        data = resp.json()
        if not data.get('artists'):
            cache['musicbrainz_country'][artist] = (None, "Not found")
            return None, "Not found"

        artist_lower = artist.lower()
        best_score = 0.0
        best_artist = None

        for mb_artist in data['artists'][:5]:
            mb_name = mb_artist.get('name', '').lower()
            bonus = 0.3 if (artist_lower in mb_name or mb_name in artist_lower) else 0.0
            score = SequenceMatcher(None, artist_lower, mb_name).ratio() + bonus
            if score > best_score:
                best_score = score
                best_artist = mb_artist

        if best_score < 0.55:
            cache['musicbrainz_country'][artist] = (None, "Not found")
            return None, "Not found"

        for field in ['area', 'begin-area']:
            if field in best_artist:
                country_raw = best_artist[field].get('name', '')
                if country_raw:
                    country_norm = validate_and_normalize_country(country_raw)
                    if country_norm:
                        result = (country_norm, f"MusicBrainz ({artist})")
                        cache['musicbrainz_country'][artist] = result
                        return result

        cache['musicbrainz_country'][artist] = (None, "Not found")
        return None, "Not found"

    except Exception as e:
        logger.debug(f"MusicBrainz country error for {artist}: {e}")
        cache['musicbrainz_country'][artist] = (None, "Not found")
        return None, "Not found"


def search_musicbrainz_genre_cached(artist: str) -> List[Tuple[str, int, str]]:
    """
    Search MusicBrainz for genre tags associated with an artist.

    Args:
        artist: Artist name.

    Returns:
        List of (genre_name, count, source) tuples.
    """
    cache = get_cache()
    if artist in cache['musicbrainz_genre']:
        return cache['musicbrainz_genre'][artist]

    sessions = get_http_sessions()
    session = sessions['musicbrainz']
    candidates = []

    try:
        url = "https://musicbrainz.org/ws/2/artist/"
        headers = {'User-Agent': 'ArtistDB/5.0 (contact@example.com)'}
        params = {'query': artist, 'fmt': 'json', 'limit': 1}
        resp = session.get(url, headers=headers, params=params, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            if data.get('artists'):
                mb_data = data['artists'][0]
                candidates = extract_genre_from_musicbrainz(mb_data)

    except Exception as e:
        logger.debug(f"MusicBrainz genre error for {artist}: {e}")

    cache['musicbrainz_genre'][artist] = candidates
    return candidates
