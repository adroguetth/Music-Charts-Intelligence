"""
Artist name parsing utilities.

This module handles splitting strings that contain multiple artist names
(featuring, collaborations, etc.) into individual artist entries.
"""

import re
from typing import List


def split_artists(artist_str: str) -> List[str]:
    """
    Split a string containing multiple artists into a list of individual names.

    Handles common separators:
    - "feat.", "ft.", "featuring"
    - "&", "and", "y"
    - Commas
    - Parentheses

    Args:
        artist_str: Raw artist string from chart data.

    Returns:
        List of cleaned individual artist names.
    """
    if not artist_str or not isinstance(artist_str, str):
        return []

    # Normalize featuring patterns
    artist_str = re.sub(r'\s+feat\.?\s+', ', ', artist_str, flags=re.IGNORECASE)
    artist_str = re.sub(r'\s+ft\.?\s+', ', ', artist_str, flags=re.IGNORECASE)
    artist_str = re.sub(r'\s+featuring\s+', ', ', artist_str, flags=re.IGNORECASE)

    # Replace conjunctions
    artist_str = re.sub(r'\s+&\s+', ', ', artist_str)
    artist_str = re.sub(r'\s+y\s+', ', ', artist_str)
    artist_str = re.sub(r'\s+and\s+', ', ', artist_str, flags=re.IGNORECASE)

    # Remove parentheses (often contain feat. info)
    artist_str = re.sub(r'[\(\)]', '', artist_str)

    # Split by comma and clean
    artists = [a.strip() for a in artist_str.split(',')]

    # Filter empty and invalid entries
    artists = [a for a in artists if a and len(a) > 1]

    # Skip common placeholder strings
    skip_words = {'various', 'various artists', 'unknown', 'varios', 'varios artistas'}
    artists = [a for a in artists if a.lower() not in skip_words]

    return artists
