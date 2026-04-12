"""
DeepSeek API client for fallback country and genre detection.

Uses the OpenAI-compatible interface to query DeepSeek's chat model.
Requires DEEPSEEK_API_KEY environment variable.
"""

import os
import json
import re
import time
from typing import Optional, Tuple
from openai import OpenAI

from ..config import logger
from ..utils.country_utils import validate_and_normalize_country

# Global client and cache
_DEEPSEEK_CLIENT = None
_DEEPSEEK_CACHE = {}  # Cache: {artist: (country, genre, source)}


def _get_deepseek_client() -> Optional[OpenAI]:
    """
    Lazy initialization of DeepSeek client.

    Returns:
        OpenAI client configured for DeepSeek, or None if API key missing.
    """
    global _DEEPSEEK_CLIENT
    if _DEEPSEEK_CLIENT is None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            logger.debug("DeepSeek API key not set")
            return None
        try:
            _DEEPSEEK_CLIENT = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
        except Exception as e:
            logger.debug(f"Failed to initialize DeepSeek client: {e}")
            return None
    return _DEEPSEEK_CLIENT


def search_deepseek_fallback(
    artist: str,
    context_country: Optional[str] = None
) -> Tuple[Optional[str], Optional[str], str]:
    """
    Use DeepSeek API as fallback to get country and/or genre.

    Only called when other sources return nothing.

    Args:
        artist: Artist name to search for.
        context_country: Optional known country to assist the model.

    Returns:
        Tuple of (country, genre, source_info).
    """
    if artist in _DEEPSEEK_CACHE:
        return _DEEPSEEK_CACHE[artist]

    client = _get_deepseek_client()
    if not client:
        return None, None, "DeepSeek not available"

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
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200
        )
        content = response.choices[0].message.content.strip()

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

            result = (country, genre, "DeepSeek API")
            _DEEPSEEK_CACHE[artist] = result
            return result

    except json.JSONDecodeError as e:
        logger.debug(f"DeepSeek JSON parse error for {artist}: {e}")
    except Exception as e:
        logger.debug(f"DeepSeek API error for {artist}: {e}")

    result = (None, None, "DeepSeek failed")
    _DEEPSEEK_CACHE[artist] = result
    return result
