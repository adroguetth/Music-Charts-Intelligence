"""
AI client for fallback country and genre detection.

Uses Meta's OpenAI-compatible API (Muse Spark) to query the chat model.
Requires META_API_KEY environment variable.
"""

import os
import json
import re
import time
from typing import Optional, Tuple
from openai import OpenAI

from ..config import logger
from ..utils.country_utils import validate_and_normalize_country

# Meta API settings
META_BASE_URL = "https://api.meta.ai/v1"
META_MODEL = "muse-spark-1.3-contributor"
META_REASONING_EFFORT = "medium"

# Global client and cache
_IA_CLIENT = None
_IA_CACHE = {}  # Cache: {artist: (country, genre, source)}


def _get_ia_client() -> Optional[OpenAI]:
    """
    Lazy initialization of the Meta AI client.

    Returns:
        OpenAI client configured for Meta API, or None if API key missing.
    """
    global _IA_CLIENT
    if _IA_CLIENT is None:
        api_key = os.getenv("META_API_KEY")
        if not api_key:
            logger.debug("Meta API key not set")
            return None
        try:
            _IA_CLIENT = OpenAI(
                api_key=api_key,
                base_url=META_BASE_URL
            )
        except Exception as e:
            logger.debug(f"Failed to initialize Meta AI client: {e}")
            return None
    return _IA_CLIENT


def search_ia_fallback(
    artist: str,
    context_country: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], str]:
    """
    Use Meta AI (Muse Spark) as fallback to get country and/or genre.

    Only called when other sources return nothing.

    Args:
        artist: Artist name to search for.
        context_country: Optional known country to assist the model.

    Returns:
        Tuple of (country, genre, source_info).
    """
    if artist in _IA_CACHE:
        return _IA_CACHE[artist]

    client = _get_ia_client()
    if not client:
        return None, None, "Meta AI not available"

    # Rate limiting
    time.sleep(0.5)

    # Build prompt
    if context_country:
        prompt = f"""
You are a music knowledge expert. Provide accurate information about the musical artist "{artist}".

The artist is known to be from {context_country} (but please verify if correct). Return ONLY a valid JSON object with these fields (use null if unknown):
{{
    "country": "country of origin (full name, e.g., United States, South Korea, United Kingdom) - if the provided country is incorrect, provide the correct one, otherwise leave as provided",
    "genre": "primary musical genre (e.g., Pop, K-Pop, Reggaeton, Afrobeats, Rock, Hip-Hop/Rap)"
}}

Be precise and factual. If you're unsure about any field, set it to null.
Do not include any additional text outside the JSON object.
"""
    else:
        prompt = f"""
You are a music knowledge expert. Provide accurate information about the musical artist "{artist}".

Return ONLY a valid JSON object with these fields (use null if unknown):
{{
    "country": "country of origin (full name, e.g., United States, South Korea, United Kingdom)",
    "genre": "primary musical genre (e.g., Pop, K-Pop, Reggaeton, Afrobeats, Rock, Hip-Hop/Rap)"
}}

Be precise and factual. If you're unsure about any field, set it to null.
Do not include any additional text outside the JSON object.
"""

    try:
        response = client.chat.completions.create(
            model=META_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            # Was 200 with DeepSeek. With reasoning_effort="high" the model
            # "thinks" first, so a low limit can cut the answer off.
            max_tokens=2000,
            reasoning_effort=META_REASONING_EFFORT,
        )
        content = (response.choices[0].message.content or "").strip()

        # Extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
            country_raw = data.get('country')
            genre_raw = data.get('genre')

            country = None
            if country_raw:
                country = validate_and_normalize_country(country_raw)

            genre = None
            if genre_raw:
                # Local import to avoid circular dependency with genre_detector
                from ..genre_detector import normalize_genre
                macro, _ = normalize_genre(genre_raw)
                genre = macro if macro else genre_raw

            result = (country, genre, "Meta AI (Muse Spark)")
            _IA_CACHE[artist] = result
            return result

    except json.JSONDecodeError as e:
        logger.debug(f"Meta AI JSON parse error for {artist}: {e}")
    except Exception as e:
        logger.debug(f"Meta AI API error for {artist}: {e}")

    result = (None, None, "Meta AI failed")
    _IA_CACHE[artist] = result
    return result
