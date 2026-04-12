"""
Country validation and normalization utilities.

This module provides functions to validate and canonicalize country names
using the comprehensive country variants dictionary. It is separated from
country_detector.py to avoid circular imports with API modules.
"""

import re
from typing import Optional

from ..dictionaries.countries import VARIANT_TO_COUNTRY, COUNTRIES_CANONICAL
from .text_utils import normalize_text


def validate_and_normalize_country(text: str) -> Optional[str]:
    """
    Validate and normalize a raw country string to a canonical country name.

    This function handles:
    - Direct matches against country variants (names, cities, demonyms)
    - Comma-separated locations (e.g., "Brooklyn, United States")
    - Substring matches for longer variants (with length > 3 to avoid false positives)
    - Direct comparison with canonical country names

    Args:
        text: Raw country name, city, demonym, or location string.

    Returns:
        Canonical country name if found, None otherwise.

    Examples:
        >>> validate_and_normalize_country("USA")
        'United States'
        >>> validate_and_normalize_country("Brooklyn, New York")
        'United States'
        >>> validate_and_normalize_country("british")
        'United Kingdom'
        >>> validate_and_normalize_country("nowhere")
        None
    """
    if not text:
        return None

    # Normalize the input text (lowercase, strip punctuation, collapse whitespace)
    text_norm = normalize_text(text)

    # Direct lookup in the variant dictionary (O(1) average)
    if text_norm in VARIANT_TO_COUNTRY:
        return VARIANT_TO_COUNTRY[text_norm]

    # Handle comma-separated locations (e.g., "New York, United States")
    # Check parts from right to left (country usually last)
    parts = [p.strip() for p in text_norm.split(',')]
    for part in reversed(parts):
        if part in VARIANT_TO_COUNTRY:
            return VARIANT_TO_COUNTRY[part]

    # Substring match for longer variants (avoid false positives on short strings)
    # This catches cases like "American singer" -> "american" -> "United States"
    for variant, country in VARIANT_TO_COUNTRY.items():
        if variant in text_norm and len(variant) > 3:
            return country

    # Check against canonical names directly (handles edge cases like spacing differences)
    for country_canonical in COUNTRIES_CANONICAL.keys():
        if text_norm == country_canonical.lower():
            return country_canonical
        # Also check without spaces (e.g., "UnitedStates" vs "United States")
        if text_norm.replace(' ', '') == country_canonical.lower().replace(' ', ''):
            return country_canonical

    return None
