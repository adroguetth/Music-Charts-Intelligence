"""
Wikidata API client for country and genre lookup.

Queries Wikidata entities using the wbsearchentities and wbgetentities actions.
"""

from typing import Optional, List, Tuple

from ..config import logger
from ..utils.cache import get_cache, get_http_sessions
from ..country_detector import validate_and_normalize_country


def search_wikidata_country_cached(artist: str) -> Optional[str]:
    """
    Search Wikidata for an artist's country (P27) or place of birth (P19).

    Args:
        artist: Artist name.

    Returns:
        Canonical country name or None.
    """
    cache = get_cache()
    if artist in cache['wikidata_country']:
        return cache['wikidata_country'][artist]

    sessions = get_http_sessions()
    session = sessions['wikidata']

    try:
        url = "https://www.wikidata.org/w/api.php"
        params = {
            'action': 'wbsearchentities',
            'search': artist,
            'language': 'en',
            'format': 'json',
            'limit': 3
        }
        resp = session.get(url, params=params, timeout=10)
        data = resp.json()

        if not data.get('search'):
            cache['wikidata_country'][artist] = None
            return None

        for result in data['search']:
            qid = result['id']
            params = {
                'action': 'wbgetentities',
                'ids': qid,
                'props': 'claims',
                'format': 'json'
            }
            resp = session.get(url, params=params, timeout=10)
            data2 = resp.json()

            if 'entities' not in data2 or qid not in data2['entities']:
                continue

            entity = data2['entities'][qid]
            claims = entity.get('claims', {})

            for prop in ['P27', 'P19']:  # P27: country of citizenship, P19: place of birth
                if prop in claims:
                    for claim in claims[prop]:
                        if 'mainsnak' in claim and 'datavalue' in claim['mainsnak']:
                            dv = claim['mainsnak']['datavalue']
                            if 'value' in dv and 'id' in dv['value']:
                                q_country = dv['value']['id']

                                params_label = {
                                    'action': 'wbgetentities',
                                    'ids': q_country,
                                    'props': 'labels',
                                    'languages': 'en|es',
                                    'format': 'json'
                                }
                                resp3 = session.get(url, params=params_label, timeout=8)
                                data3 = resp3.json()

                                if 'entities' not in data3 or q_country not in data3['entities']:
                                    continue

                                country_entity = data3['entities'][q_country]
                                labels = country_entity.get('labels', {})
                                country_name = None
                                if 'en' in labels:
                                    country_name = labels['en']['value']
                                elif 'es' in labels:
                                    country_name = labels['es']['value']

                                if country_name:
                                    country_canonical = validate_and_normalize_country(country_name)
                                    if country_canonical:
                                        cache['wikidata_country'][artist] = country_canonical
                                        return country_canonical

        cache['wikidata_country'][artist] = None
        return None

    except Exception as e:
        logger.debug(f"Wikidata country error for {artist}: {e}")
        cache['wikidata_country'][artist] = None
        return None


def search_wikidata_genre_cached(artist: str) -> List[Tuple[str, int, str]]:
    """
    Search Wikidata for genre claims (P136) associated with an artist.

    Args:
        artist: Artist name.

    Returns:
        List of (genre_name, weight=3, 'wikidata') tuples.
    """
    cache = get_cache()
    if artist in cache['wikidata_genre']:
        return cache['wikidata_genre'][artist]

    sessions = get_http_sessions()
    session = sessions['wikidata']
    candidates = []

    try:
        url = "https://www.wikidata.org/w/api.php"
        params_search = {
            'action': 'wbsearchentities',
            'search': artist,
            'language': 'en',
            'format': 'json',
            'limit': 3
        }
        resp = session.get(url, params=params_search, timeout=10)
        data = resp.json()

        if not data.get('search'):
            cache['wikidata_genre'][artist] = candidates
            return candidates

        for result in data['search']:
            qid = result['id']
            params_claims = {
                'action': 'wbgetentities',
                'ids': qid,
                'props': 'claims',
                'format': 'json'
            }
            resp2 = session.get(url, params=params_claims, timeout=10)
            data2 = resp2.json()

            if 'entities' not in data2 or qid not in data2['entities']:
                continue

            entity = data2['entities'][qid]
            claims = entity.get('claims', {})

            if 'P136' in claims:  # P136: genre
                for claim in claims['P136'][:3]:
                    try:
                        if 'mainsnak' in claim and 'datavalue' in claim['mainsnak']:
                            dv = claim['mainsnak']['datavalue']
                            if 'value' in dv and 'id' in dv['value']:
                                genre_qid = dv['value']['id']

                                params_label = {
                                    'action': 'wbgetentities',
                                    'ids': genre_qid,
                                    'props': 'labels',
                                    'languages': 'en|es',
                                    'format': 'json'
                                }
                                resp3 = session.get(url, params=params_label, timeout=8)
                                data3 = resp3.json()

                                if 'entities' in data3 and genre_qid in data3['entities']:
                                    labels = data3['entities'][genre_qid].get('labels', {})
                                    genre_name = None
                                    if 'en' in labels:
                                        genre_name = labels['en']['value']
                                    elif 'es' in labels:
                                        genre_name = labels['es']['value']

                                    if genre_name:
                                        candidates.append((genre_name.lower(), 3, 'wikidata'))
                    except Exception as e:
                        logger.debug(f"Error processing Wikidata genre claim: {e}")

    except Exception as e:
        logger.debug(f"Wikidata genre error for {artist}: {e}")

    cache['wikidata_genre'][artist] = candidates
    return candidates
