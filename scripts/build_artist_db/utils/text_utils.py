"""
Text normalization and name variation generation utilities.

This module provides functions for cleaning and transforming artist names
to improve match rates across different data sources.
"""

import re
import unicodedata
from typing import List, Optional


def normalize_text(text: str) -> str:
    """
    Normalize a text string for comparison and lookup.

    Converts to lowercase, collapses whitespace, and strips punctuation.

    Args:
        text: Raw input string.

    Returns:
        Cleaned and normalized string.
    """
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    text = text.strip('.,;:¿?¡!()[]"\'«»…–—')
    return text


def generate_name_variations(name: str) -> List[str]:
    """
    Generate basic variations of an artist name.

    Variations include:
    - Original
    - Without accents
    - Without dots
    - Without hyphens (replaced by spaces)

    Args:
        name: Original artist name.

    Returns:
        List of unique name variations.
    """
    variations = [name]

    # Remove accents
    no_accents = ''.join(
        c for c in unicodedata.normalize('NFD', name)
        if unicodedata.category(c) != 'Mn'
    )
    if no_accents != name:
        variations.append(no_accents)

    # Remove dots
    no_dots = name.replace('.', '')
    if no_dots != name:
        variations.append(no_dots)
        variations.append(no_dots.replace(' ', ''))

    # Replace hyphens with spaces
    no_hyphens = name.replace('-', ' ')
    if no_hyphens != name:
        variations.append(no_hyphens)

    return list(dict.fromkeys(variations))


# Common prefixes in artist names that may be removed for broader matching
ARTIST_PREFIXES = {
    'dj': ['DJ', 'Dj', 'dj'],
    'mc': ['MC', 'Mc', 'mc'],
    'lil': ['Lil', 'lil', 'LIL'],
    'young': ['Young', 'young'],
    'big': ['Big', 'big'],
    'the': ['The', 'the', 'THE'],
    'los': ['Los', 'los'],
    'las': ['Las', 'las'],
    'el': ['El', 'el'],
    'la': ['La', 'la'],
}


def remove_artist_prefixes(name: str) -> List[str]:
    """
    Remove common prefixes (DJ, MC, Lil, The, etc.) from a name.

    Args:
        name: Artist name.

    Returns:
        List of variations with prefixes removed.
    """
    variations = [name]
    for prefix_base, variants in ARTIST_PREFIXES.items():
        for variant in variants:
            pattern = r'^' + re.escape(variant) + r'\s+'
            if re.match(pattern, name):
                without_prefix = re.sub(pattern, '', name)
                if without_prefix:
                    variations.append(without_prefix)
    return list(dict.fromkeys(variations))


def generate_all_variations(name: str) -> List[str]:
    """
    Generate an extensive list of name variations by combining
    accent removal, dot removal, hyphen replacement, and prefix removal.

    Args:
        name: Original artist name.

    Returns:
        List of up to 15 unique variations, starting with the original.
    """
    all_vars = set()
    for var in generate_name_variations(name):
        all_vars.add(var)
        for no_prefix in remove_artist_prefixes(var):
            all_vars.add(no_prefix)
            for var2 in generate_name_variations(no_prefix):
                all_vars.add(var2)

    result = [name]
    for var in sorted(all_vars - {name}, key=len, reverse=True):
        if var and len(var) > 1:
            result.append(var)
    return result[:15]


def detect_script_from_name(name: str) -> Optional[str]:
    """
    Detect the writing system from an artist name and return an ISO 639-1 language code.

    Useful for prioritizing Wikipedia language editions during lookup.

    Args:
        name: Artist name string.

    Returns:
        Two-letter language code (e.g., 'ru', 'hi', 'ja') or None if no specific script.
    """
    # Devanagari (Hindi, Marathi, Nepali, etc.)
    if re.search(r'[\u0900-\u097F]', name):
        return 'hi'
    # Gujarati
    elif re.search(r'[\u0A80-\u0AFF]', name):
        return 'gu'
    # Oriya
    elif re.search(r'[\u0B00-\u0B7F]', name):
        return 'or'
    # Tamil
    elif re.search(r'[\u0B80-\u0BFF]', name):
        return 'ta'
    # Telugu
    elif re.search(r'[\u0C00-\u0C7F]', name):
        return 'te'
    # Kannada
    elif re.search(r'[\u0C80-\u0CFF]', name):
        return 'kn'
    # Malayalam
    elif re.search(r'[\u0D00-\u0D7F]', name):
        return 'ml'
    # Sinhala
    elif re.search(r'[\u0D80-\u0DFF]', name):
        return 'si'
    # Thai
    elif re.search(r'[\u0E00-\u0E7F]', name):
        return 'th'
    # Tibetan
    elif re.search(r'[\u0F00-\u0FFF]', name):
        return 'bo'
    # Burmese
    elif re.search(r'[\u1000-\u109F]', name):
        return 'my'
    # Khmer
    elif re.search(r'[\u1780-\u17FF]', name):
        return 'km'
    # Japanese (Hiragana/Katakana)
    elif re.search(r'[\u3040-\u309F\u30A0-\u30FF]', name):
        return 'ja'
    # Chinese (Han) - distinguish from Korean Hangul
    elif re.search(r'[\u4E00-\u9FFF]', name):
        if re.search(r'[\uAC00-\uD7AF]', name):
            return 'ko'  # Korean (Hangul + Hanja)
        return 'zh'
    # Hangul (Korean)
    elif re.search(r'[\uAC00-\uD7AF]', name):
        return 'ko'
    # Arabic / Urdu / Persian
    elif re.search(r'[\u0600-\u06FF]', name) or re.search(r'[\u0750-\u077F]', name):
        # Detect Urdu by specific characters: گ چ پ ژ
        if re.search(r'[گچپژ]', name):
            return 'ur'
        else:
            return 'ar'
    # Cyrillic
    elif re.search(r'[\u0400-\u04FF]', name):
        # Ukrainian: і, ї, є, ґ
        if re.search(r'[іїєґ]', name, re.IGNORECASE):
            return 'uk'
        # Bulgarian: ъ (common at word end)
        if re.search(r'ъ', name, re.IGNORECASE):
            return 'bg'
        # Serbian: ћ, ђ, џ, љ, њ
        if re.search(r'[ћђџљњ]', name, re.IGNORECASE):
            return 'sr'
        # Default to Russian
        return 'ru'
    # Greek
    elif re.search(r'[\u0370-\u03FF]', name):
        return 'el'
    # Latin with Spanish ñ
    elif re.search(r'ñ', name, re.IGNORECASE):
        return 'es'
    # Latin with Portuguese-specific accents (ç, ã, õ)
    elif re.search(r'[çãõ]', name, re.IGNORECASE):
        return 'pt'
    # Other Latin accents default to Spanish
    elif re.search(r'[áéíóúâêôàèìòùäëïöü]', name, re.IGNORECASE):
        return 'es'

    return None
