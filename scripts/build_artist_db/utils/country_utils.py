"""
Country validation and normalization utilities.

This module provides functions to validate and canonicalize country names
using the comprehensive country variants dictionary.
"""

import re
from typing import Optional

from ..dictionaries.countries import VARIANT_TO_COUNTRY, COUNTRIES_CANONICAL
from .text_utils import normalize_text


def validate_and_normalize_country(text: str) -> Optional[str]:
    """
    Validate and normalize a raw country string to a canonical country name.

    Args:
        text: Raw country name, city, or demonym.

    Returns:
        Canonical country name if found, None otherwise.
    """
    if not text:
        return None

    text_norm = normalize_text(text)

    # Direct lookup in variant dictionary
    if text_norm in VARIANT_TO_COUNTRY:
        return VARIANT_TO_COUNTRY[text_norm]

    # Check comma-separated parts (e.g., "New York, United States")
    parts = [p.strip() for p in text_norm.split(',')]
    for part in reversed(parts):
        if part in VARIANT_TO_COUNTRY:
            return VARIANT_TO_COUNTRY[part]

    # Substring match for longer variants (avoid false positives on short strings)
    for variant, country in VARIANT_TO_COUNTRY.items():
        if variant in text_norm and len(variant) > 3:
            return country

    # Check against canonical names directly
    for country_canonical in COUNTRIES_CANONICAL.keys():
        if text_norm == country_canonical.lower():
            return country_canonical
        if text_norm.replace(' ', '') == country_canonical.lower().replace(' ', ''):
            return country_canonical

    return None
