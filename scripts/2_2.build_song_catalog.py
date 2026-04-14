#!/usr/bin/env python3

"""
YouTube Charts Song Catalog Builder
===================================
Automated ETL pipeline for building and maintaining a canonical song catalog
from YouTube Charts weekly database snapshots.

Features:
- Automatic detection of most recent weekly database via lexicographic ordering
- Idempotent insertion with composite natural key deduplication
- Auto-incrementing surrogate primary key generation
- Integration with artist metadata database for country and macro-genre resolution
- Weighted collaboration algorithm for multi-artist tracks
- Conditional update for existing records with missing/invalid country/genre data
- Schema validation and automatic table initialization/migration
- Comprehensive error handling and logging
- GitHub Actions CI/CD compatible

Data Flow:
1. Scans charts_archive/1_download-chart/databases/ for youtube_charts_20XX-WXX.db files
2. Selects most recent snapshot based on ISO week identifier
3. Loads artist metadata from charts_archive/2_1.countries-genres-artist/artist_countries_genres.db
4. Extracts distinct (Artist Names, Track Name) tuples from chart database
5. For each new song, resolves country and macro-genre using collaboration weight algorithm
6. For each existing song with NULL/Unknown country or genre, updates the record with resolved values
7. Inserts new records with auto-generated sequential IDs and resolved attributes

Database Schema:
    Table: artist_track
    Columns:
        - id            : INTEGER PRIMARY KEY AUTOINCREMENT (surrogate key)
        - artist_names  : VARCHAR(200) NOT NULL (natural key component)
        - track_name    : VARCHAR(200) NOT NULL (natural key component)
        - artist_country: TEXT NOT NULL
        - macro_genre   : TEXT NOT NULL
        - artists_found : TEXT (format: 'matched/total')

Requirements:
- Python 3.7+
- sqlite3 (included in Python standard library)
- pathlib (included in Python standard library)
- re (included in Python standard library)

Author: Alfonso Droguett
License: MIT
"""

import sqlite3
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from collections import Counter

# -----------------------------------------------------------------------------
# Directory Structure Configuration
# -----------------------------------------------------------------------------
# Repository-relative paths ensure consistent behavior across local development
# and GitHub Actions CI/CD environments.

# Determine repository root (parent of scripts directory)
REPO_ROOT = Path(__file__).parent.parent

# Source: Where weekly chart databases are stored (Script 1 output)
SOURCE_DIR = REPO_ROOT / "charts_archive" / "1_download-chart" / "databases"

# Artist metadata database path (country + macro-genre per artist)
ARTIST_DB_PATH = REPO_ROOT / "charts_archive" / "2_1.countries-genres-artist" / "artist_countries_genres.db"

# Target: Where the canonical song catalog will be maintained
TARGET_DIR = REPO_ROOT / "charts_archive" / "2_2.build-song-catalog"
TARGET_DB_NAME = "build_song.db"

# Create target directory structure if it doesn't exist
TARGET_DIR.mkdir(parents=True, exist_ok=True)

# Regex pattern for YouTube Charts weekly database filenames
# Format: youtube_charts_YYYY-Www.db (e.g., youtube_charts_2026-W15.db)
# Note: Pattern matches years 2000-2099 (20\d{2})
DB_FILENAME_PATTERN = re.compile(r'youtube_charts_20\d{2}-W\d{1,2}\.db$')


# -----------------------------------------------------------------------------
# LOOKUP TABLES (from script 3)
# Country → Continent mapping used by the collaboration weight algorithm.
# Continent-level resolution is the fallback when per-country logic is
# inconclusive (e.g., 3+ countries with no clear majority).
# -----------------------------------------------------------------------------
COUNTRY_TO_CONTINENT = {
    # Asia
    "South Korea": "Asia", "Japan": "Asia", "China": "Asia", "Taiwan": "Asia",
    "Hong Kong": "Asia", "Thailand": "Asia", "Vietnam": "Asia", "Philippines": "Asia",
    "Indonesia": "Asia", "Malaysia": "Asia", "Singapore": "Asia", "India": "Asia",
    "Pakistan": "Asia", "Bangladesh": "Asia", "Sri Lanka": "Asia", "Nepal": "Asia",
    "Bhutan": "Asia", "Maldives": "Asia", "Kazakhstan": "Asia", "Uzbekistan": "Asia",
    "Turkmenistan": "Asia", "Kyrgyzstan": "Asia", "Tajikistan": "Asia", "Mongolia": "Asia",
    "Myanmar": "Asia", "Laos": "Asia", "Cambodia": "Asia", "Afghanistan": "Asia",
    "Iran": "Asia", "Iraq": "Asia", "Syria": "Asia", "Lebanon": "Asia", "Jordan": "Asia",
    "Israel": "Asia", "Palestine": "Asia", "Saudi Arabia": "Asia", "Yemen": "Asia",
    "Oman": "Asia", "United Arab Emirates": "Asia", "Qatar": "Asia", "Kuwait": "Asia",
    "Bahrain": "Asia", "Turkey": "Asia", "Cyprus": "Asia", "Azerbaijan": "Asia",
    "Georgia": "Asia", "Armenia": "Asia", "Russia": "Asia",
    # North America
    "United States": "America", "Canada": "America", "Mexico": "America",
    "Guatemala": "America", "Honduras": "America", "El Salvador": "America",
    "Nicaragua": "America", "Costa Rica": "America", "Panama": "America",
    "Belize": "America",
    # Caribbean
    "Cuba": "America", "Jamaica": "America", "Haiti": "America", "Dominican Republic": "America",
    "Puerto Rico": "America", "Bahamas": "America", "Trinidad and Tobago": "America",
    "Barbados": "America", "Saint Lucia": "America", "Grenada": "America",
    "Saint Vincent and the Grenadines": "America", "Antigua and Barbuda": "America",
    "Dominica": "America", "Saint Kitts and Nevis": "America",
    # South America
    "Colombia": "America", "Venezuela": "America", "Ecuador": "America", "Peru": "America",
    "Bolivia": "America", "Chile": "America", "Argentina": "America", "Paraguay": "America",
    "Uruguay": "America", "Brazil": "America", "Guyana": "America", "Suriname": "America",
    "French Guiana": "America",
    # Europe
    "United Kingdom": "Europe", "Ireland": "Europe", "France": "Europe", "Belgium": "Europe",
    "Netherlands": "Europe", "Germany": "Europe", "Austria": "Europe", "Switzerland": "Europe",
    "Italy": "Europe", "Spain": "Europe", "Portugal": "Europe", "Greece": "Europe",
    "Sweden": "Europe", "Norway": "Europe", "Denmark": "Europe", "Finland": "Europe",
    "Iceland": "Europe", "Luxembourg": "Europe", "Monaco": "Europe", "Liechtenstein": "Europe",
    "Andorra": "Europe", "San Marino": "Europe", "Malta": "Europe", "Poland": "Europe",
    "Czech Republic": "Europe", "Slovakia": "Europe", "Hungary": "Europe", "Romania": "Europe",
    "Bulgaria": "Europe", "Serbia": "Europe", "Croatia": "Europe", "Bosnia and Herzegovina": "Europe",
    "Montenegro": "Europe", "North Macedonia": "Europe", "Kosovo": "Europe", "Albania": "Europe",
    "Slovenia": "Europe", "Lithuania": "Europe", "Latvia": "Europe", "Estonia": "Europe",
    "Belarus": "Europe", "Moldova": "Europe", "Ukraine": "Europe",
    # Africa
    "Nigeria": "Africa", "Ghana": "Africa", "South Africa": "Africa", "Tanzania": "Africa",
    "Kenya": "Africa", "Uganda": "Africa", "Zimbabwe": "Africa", "Zambia": "Africa",
    "Mozambique": "Africa", "Angola": "Africa", "Ethiopia": "Africa", "Rwanda": "Africa",
    "Senegal": "Africa", "Mali": "Africa", "Ivory Coast": "Africa", "Cameroon": "Africa",
    "Benin": "Africa", "Togo": "Africa", "Burkina Faso": "Africa", "Niger": "Africa",
    "Chad": "Africa", "Central African Republic": "Africa", "Equatorial Guinea": "Africa",
    "Gabon": "Africa", "Republic of the Congo": "Africa", "Democratic Republic of the Congo": "Africa",
    "Burundi": "Africa", "Djibouti": "Africa", "Eritrea": "Africa", "Somalia": "Africa",
    "Sudan": "Africa", "South Sudan": "Africa", "Malawi": "Africa", "Botswana": "Africa",
    "Namibia": "Africa", "Lesotho": "Africa", "Eswatini": "Africa", "Madagascar": "Africa",
    "Comoros": "Africa", "Mauritius": "Africa", "Seychelles": "Africa", "Cabo Verde": "Africa",
    "São Tomé and Príncipe": "Africa",
    # Oceania
    "Australia": "Oceania", "New Zealand": "Oceania", "Papua New Guinea": "Oceania",
    "Fiji": "Oceania", "Samoa": "Oceania", "Tonga": "Oceania", "Solomon Islands": "Oceania",
    "Vanuatu": "Oceania", "Micronesia": "Oceania", "Marshall Islands": "Oceania",
    "Palau": "Oceania", "Nauru": "Oceania", "Kiribati": "Oceania", "Tuvalu": "Oceania",
    "Hawaii": "Oceania"
}

# Country → ordered list of genres, from most to least culturally dominant.
# This hierarchy drives genre inference when artist-level genre data is absent
# or when no single genre holds a majority across collaborating artists.
GENRE_HIERARCHY = {
    # North America
    "United States": [
        "Pop", "Hip-Hop/Rap", "R&B/Soul", "Country", "Rock",
        "Alternative", "Electronic/Dance", "Reggaeton/Latin Trap",
        "Jazz/Blues", "Classical"
    ],
    "Canada": [
        "Pop", "Hip-Hop/Rap", "Rock", "Alternative",
        "Electronic/Dance", "R&B/Soul", "Reggaeton/Latin Trap",
        "Country", "Classical"
    ],
    "Mexico": [
        "Regional Mexican", "Reggaeton/Latin Trap", "Pop",
        "Bachata", "Cumbia", "Rock", "Tropical/Salsa/Merengue/Bolero",
        "Classical"
    ],
    # Central America
    "Guatemala": ["Reggaeton/Latin Trap", "Bachata", "Cumbia", "Dancehall/Reggae", "Tropical/Salsa/Merengue/Bolero"],
    "Honduras": ["Reggaeton/Latin Trap", "Bachata", "Cumbia", "Dancehall/Reggae", "Tropical/Salsa/Merengue/Bolero"],
    "El Salvador": ["Reggaeton/Latin Trap", "Bachata", "Cumbia", "Dancehall/Reggae"],
    "Nicaragua": ["Reggaeton/Latin Trap", "Bachata", "Cumbia", "Dancehall/Reggae"],
    "Costa Rica": ["Reggaeton/Latin Trap", "Pop", "Bachata", "Cumbia", "Dancehall/Reggae", "Tropical/Salsa/Merengue/Bolero"],
    "Panama": [
        "Reggaeton/Latin Trap", "Dancehall/Reggae",
        "Tropical/Salsa/Merengue/Bolero", "Cumbia", "Pop"
    ],
    "Belize": ["Dancehall/Reggae", "Reggaeton/Latin Trap", "Pop", "Cumbia"],
    # Caribbean
    "Jamaica": ["Dancehall/Reggae"],
    "Puerto Rico": ["Reggaeton/Latin Trap", "Pop"],
    "Dominican Republic": [
        "Reggaeton/Latin Trap", "Bachata", "Tropical/Salsa/Merengue/Bolero", "Dancehall/Reggae"
    ],
    "Cuba": [
        "Reggaeton/Latin Trap", "Tropical/Salsa/Merengue/Bolero",
        "Pop", "Jazz/Blues"
    ],
    "Haiti": ["Reggaeton/Latin Trap", "Tropical/Salsa/Merengue/Bolero", "Pop"],
    "Trinidad and Tobago": [
        "Tropical/Salsa/Merengue/Bolero", "Dancehall/Reggae",
        "Reggaeton/Latin Trap", "Pop"
    ],
    "Bahamas": ["Pop", "Dancehall/Reggae", "R&B/Soul"],
    "Barbados": ["Pop", "Dancehall/Reggae", "R&B/Soul", "Reggaeton/Latin Trap"],
    "Saint Lucia": ["Pop", "Dancehall/Reggae", "Reggaeton/Latin Trap"],
    "Grenada": ["Pop", "Dancehall/Reggae", "Reggaeton/Latin Trap"],
    "Saint Vincent and the Grenadines": ["Pop", "Dancehall/Reggae", "Reggaeton/Latin Trap"],
    "Antigua and Barbuda": ["Pop", "Dancehall/Reggae", "Reggaeton/Latin Trap"],
    "Dominica": ["Pop", "Dancehall/Reggae", "Reggaeton/Latin Trap"],
    "Saint Kitts and Nevis": ["Pop", "Dancehall/Reggae", "Reggaeton/Latin Trap"],
    # South America
    "Colombia": [
        "Reggaeton/Latin Trap", "Cumbia", "Vallenato",
        "Tropical/Salsa/Merengue/Bolero", "Pop", "Rock"
    ],
    "Venezuela": [
        "Reggaeton/Latin Trap", "Tropical/Salsa/Merengue/Bolero",
        "Pop", "Rock", "Classical"
    ],
    "Ecuador": ["Reggaeton/Latin Trap", "Cumbia", "Folk/Roots", "Pop"],
    "Peru": ["Reggaeton/Latin Trap", "Cumbia", "Folk/Roots", "Pop"],
    "Bolivia": ["Reggaeton/Latin Trap", "Cumbia", "Folk/Roots", "Pop"],
    "Chile": ["Reggaeton/Latin Trap", "Cumbia", "Pop", "Rock", "Folk/Roots", "Classical"],
    "Argentina": [
        "Reggaeton/Latin Trap", "Cumbia", "Rock", "Pop", "Folk/Roots",
        "Classical"
    ],
    "Paraguay": ["Reggaeton/Latin Trap", "Cumbia", "Folk/Roots", "Pop"],
    "Uruguay": ["Reggaeton/Latin Trap", "Cumbia", "Pop", "Rock", "Electronic/Dance", "Classical"],
    "Brazil": [
        "Sertanejo", "Brazilian Funk", "Reggaeton/Latin Trap",
        "Pop", "Rock", "Hip-Hop/Rap", "Forro", "Axe", "MPB",
        "Classical"
    ],
    "Guyana": ["Dancehall/Reggae", "Reggaeton/Latin Trap", "Pop"],
    "Suriname": ["Dancehall/Reggae", "Reggaeton/Latin Trap", "Pop"],
    "French Guiana": ["Dancehall/Reggae", "Reggaeton/Latin Trap", "Pop", "Kizomba/Zouk"],
    # Western Europe
    "Spain": [
        "Reggaeton/Latin Trap", "Pop", "Hip-Hop/Rap",
        "Flamenco/Copla", "Rock", "Electronic/Dance",
        "Classical"
    ],
    "Portugal": [
        "Pop", "Hip-Hop/Rap", "Folk/Roots",
        "Kizomba/Zouk", "Reggaeton/Latin Trap", "Rock", "Fado",
        "Classical"
    ],
    "United Kingdom": [
        "Pop", "Hip-Hop/Rap", "Rock", "Alternative",
        "Electronic/Dance", "Afrobeats", "Dancehall/Reggae",
        "R&B/Soul", "Classical"
    ],
    "Ireland": [
        "Pop", "Rock", "Alternative", "Hip-Hop/Rap",
        "Folk/Roots", "Electronic/Dance", "Classical"
    ],
    "France": [
        "Pop", "Hip-Hop/Rap", "Electronic/Dance", "Afrobeats",
        "Chanson", "R&B/Soul", "Rock", "Classical"
    ],
    "Belgium": ["Pop", "Hip-Hop/Rap", "Electronic/Dance", "Rock", "Chanson", "Classical"],
    "Netherlands": ["Pop", "Electronic/Dance", "Hip-Hop/Rap", "Rock", "Alternative", "Classical"],
    "Germany": [
        "Hip-Hop/Rap", "Pop", "Electronic/Dance", "Schlager",
        "Rock", "Alternative", "Classical"
    ],
    "Austria": [
        "Pop", "Hip-Hop/Rap", "Schlager", "Rock", "Alpine Folk",
        "Classical"
    ],
    "Switzerland": [
        "Pop", "Hip-Hop/Rap", "Alpine Folk", "Rock",
        "Electronic/Dance", "Schlager", "Classical"
    ],
    "Italy": [
        "Pop", "Hip-Hop/Rap", "Italian Song", "Rock", "Electronic/Dance",
        "Classical"
    ],
    "Greece": ["Pop", "Hip-Hop/Rap", "Laiko", "Rock", "Electronic/Dance", "Classical"],
    "Sweden": ["Pop", "Hip-Hop/Rap", "Electronic/Dance", "Rock", "Metal", "Dansband", "Classical"],
    "Norway": ["Pop", "Hip-Hop/Rap", "Metal", "Electronic/Dance", "Rock", "Dansband", "Classical"],
    "Denmark": ["Pop", "Hip-Hop/Rap", "Electronic/Dance", "Rock", "Dansband", "Classical"],
    "Finland": ["Pop", "Metal", "Hip-Hop/Rap", "Rock", "Iskelma", "Electronic/Dance", "Classical"],
    "Iceland": ["Pop", "Alternative", "Rock", "Hip-Hop/Rap", "Electronic/Dance", "Classical"],
    # Small European states
    "Luxembourg": ["Pop", "Hip-Hop/Rap", "Rock", "Electronic/Dance", "Chanson"],
    "Monaco": ["Pop", "Hip-Hop/Rap", "Chanson", "Electronic/Dance"],
    "Liechtenstein": ["Pop", "Rock", "Alpine Folk", "Schlager"],
    "Andorra": ["Pop", "Reggaeton/Latin Trap", "Rock", "Flamenco/Copla"],
    "San Marino": ["Pop", "Rock", "Italian Song"],
    "Malta": ["Pop", "Rock", "Hip-Hop/Rap", "Electronic/Dance"],
    "Cyprus": ["Pop", "Rock", "Hip-Hop/Rap", "Laiko", "Electronic/Dance"],
    # Eastern Europe and Balkans
    "Russia": [
        "Pop", "Hip-Hop/Rap", "Rock", "Electronic/Dance", "Classical",
        "Folk"
    ],
    "Ukraine": ["Pop", "Hip-Hop/Rap", "Rock", "Electronic/Dance", "Folk"],
    "Poland": ["Pop", "Hip-Hop/Rap", "Rock", "Electronic/Dance", "Classical"],
    "Czech Republic": ["Pop", "Hip-Hop/Rap", "Rock", "Electronic/Dance", "Classical"],
    "Slovakia": ["Pop", "Hip-Hop/Rap", "Rock"],
    "Hungary": ["Pop", "Hip-Hop/Rap", "Rock", "Electronic/Dance", "Classical"],
    "Romania": ["Manele", "Pop", "Hip-Hop/Rap", "Electronic/Dance", "Rock"],
    "Bulgaria": ["Chalga", "Pop", "Hip-Hop/Rap", "Rock", "Electronic/Dance"],
    "Serbia": ["Turbo-folk", "Pop", "Hip-Hop/Rap", "Electronic/Dance", "Rock"],
    "Croatia": ["Pop", "Turbo-folk", "Rock", "Hip-Hop/Rap", "Electronic/Dance"],
    "Bosnia and Herzegovina": ["Turbo-folk", "Pop", "Rock", "Hip-Hop/Rap"],
    "Montenegro": ["Turbo-folk", "Pop", "Rock"],
    "North Macedonia": ["Turbo-folk", "Pop", "Rock"],
    "Kosovo": ["Tallava", "Pop", "Hip-Hop/Rap", "Turbo-folk", "Rock"],
    "Albania": ["Tallava", "Pop", "Hip-Hop/Rap", "Rock"],
    "Slovenia": ["Pop", "Rock", "Hip-Hop/Rap", "Electronic/Dance"],
    "Lithuania": ["Pop", "Hip-Hop/Rap", "Rock", "Electronic/Dance"],
    "Latvia": ["Pop", "Hip-Hop/Rap", "Rock", "Electronic/Dance"],
    "Estonia": ["Pop", "Hip-Hop/Rap", "Rock", "Electronic/Dance", "Folk"],
    "Belarus": ["Pop", "Rock", "Hip-Hop/Rap"],
    "Moldova": ["Pop", "Rock", "Hip-Hop/Rap", "Manele"],
    # Middle East and North Africa
    "Turkey": ["Turkish Pop/Rock", "Pop", "Hip-Hop/Rap", "Rock", "Arabesk", "Classical"],
    "Israel": ["Israeli Pop/Rock", "Pop", "Hip-Hop/Rap", "Rock", "Mizrahi", "Classical"],
    "Lebanon": ["Arabic Pop/Rock", "Pop", "Hip-Hop/Rap"],
    "Syria": ["Arabic Pop/Rock"],
    "Jordan": ["Arabic Pop/Rock", "Pop", "Hip-Hop/Rap"],
    "Iraq": ["Arabic Pop/Rock", "Pop", "Hip-Hop/Rap"],
    "Iran": ["Pop", "Hip-Hop/Rap", "Rock", "Classical Persian"],
    "Egypt": ["Arabic Pop/Rock", "Shaabi", "Hip-Hop/Rap"],
    "Morocco": ["Arabic Pop/Rock", "Gnawa", "Hip-Hop/Rap", "Chaabi"],
    "Algeria": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Rai"],
    "Tunisia": ["Arabic Pop/Rock", "Hip-Hop/Rap"],
    "Libya": ["Arabic Pop/Rock"],
    "Saudi Arabia": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Khaliji"],
    "United Arab Emirates": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Khaliji"],
    "Kuwait": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Khaliji"],
    "Qatar": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Khaliji"],
    "Bahrain": ["Arabic Pop/Rock", "Khaliji"],
    "Oman": ["Arabic Pop/Rock", "Khaliji"],
    "Yemen": ["Arabic Pop/Rock"],
    # Sub-Saharan Africa
    "Nigeria": ["Afrobeats", "Hip-Hop/Rap", "Gospel", "Juju", "Fuji"],
    "Ghana": ["Afrobeats", "Highlife", "Hip-Hop/Rap", "Gospel"],
    "South Africa": [
        "Amapiano", "Kwaito", "Hip-Hop/Rap", "Afrobeats",
        "Electronic/Dance", "Maskandi", "Mbaqanga", "Gqom", "Afro-soul"
    ],
    "Tanzania": ["Bongo Flava", "Taarab", "Afrobeats", "Hip-Hop/Rap"],
    "Kenya": ["Afrobeats", "Gengetone", "Kapuka", "Benga", "Hip-Hop/Rap"],
    "Uganda": ["Afrobeats", "Hip-Hop/Rap"],
    "Zimbabwe": ["Zim Dancehall", "Afrobeats", "Amapiano", "Sungura"],
    "Zambia": ["Amapiano", "Afrobeats", "Hip-Hop/Rap"],
    "Mozambique": ["Marrabenta", "Amapiano", "Afrobeats", "Kizomba/Zouk"],
    "Angola": ["Kuduro", "Kizomba/Zouk", "Afrobeats", "Semba"],
    "Ethiopia": ["Ethio-jazz", "Pop", "Hip-Hop/Rap"],
    "Rwanda": ["Afrobeats", "Hip-Hop/Rap"],
    "Senegal": ["Mbalax", "Afrobeats", "Hip-Hop/Rap"],
    "Mali": ["Afrobeats", "Desert Blues"],
    "Ivory Coast": ["Coupe-Decale", "Afrobeats", "Zouglou", "Hip-Hop/Rap"],
    "Cameroon": ["Afrobeats", "Bikutsi", "Makossa", "Hip-Hop/Rap"],
    "Benin": ["Afrobeats", "Gospel"],
    "Togo": ["Afrobeats"],
    "Burkina Faso": ["Afrobeats"],
    "Niger": ["Afrobeats"],
    "Chad": ["Afrobeats"],
    "Central African Republic": ["Afrobeats"],
    "Equatorial Guinea": ["Afrobeats"],
    "Gabon": ["Afrobeats"],
    "Republic of the Congo": ["Soukous/Ndombolo", "Afrobeats"],
    "Democratic Republic of the Congo": ["Soukous/Ndombolo", "Afrobeats", "Rumba"],
    "Burundi": ["Afrobeats"],
    "Djibouti": ["Afrobeats"],
    "Eritrea": ["Afrobeats"],
    "Somalia": ["Afrobeats", "Qaraami"],
    "Sudan": ["Afrobeats", "Hip-Hop/Rap"],
    "South Sudan": ["Afrobeats"],
    "Malawi": ["Afrobeats"],
    "Botswana": ["Afrobeats", "Amapiano"],
    "Namibia": ["Afrobeats", "Amapiano"],
    "Lesotho": ["Afrobeats", "Amapiano"],
    "Eswatini": ["Afrobeats", "Amapiano"],
    "Madagascar": ["Salegy", "Afrobeats"],
    "Comoros": ["Afrobeats", "Taarab"],
    "Mauritius": ["Sega", "Afrobeats", "Kizomba/Zouk"],
    "Seychelles": ["Sega", "Afrobeats", "Kizomba/Zouk"],
    "Cabo Verde": ["Kizomba/Zouk", "Coladeira", "Funana", "Morna"],
    "São Tomé and Príncipe": ["Afrobeats", "Kizomba/Zouk"],
    # Asia
    "India": [
        "Indian Pop", "Hip-Hop/Rap", "Bollywood", "Indian Classical",
        "Rock", "Electronic/Dance"
    ],
    "Pakistan": ["Pakistani Pop", "Hip-Hop/Rap", "Qawwali", "Rock"],
    "Bangladesh": ["Bangladeshi Pop/Rock", "Hip-Hop/Rap", "Folk"],
    "Sri Lanka": ["Sri Lankan Pop/Rock", "Baila", "Hip-Hop/Rap"],
    "Nepal": ["Nepali Pop/Rock", "Hip-Hop/Rap", "Folk"],
    "Bhutan": ["Bhutanese Pop/Rock", "Rigsar"],
    "Maldives": ["Maldivian Pop/Rock", "Boduberu fusion"],
    "South Korea": [
        "K-Pop/K-Rock", "Hip-Hop/Rap", "Rock", "Ballad", "Trot",
        "Classical"
    ],
    "Japan": [
        "J-Pop/J-Rock", "Hip-Hop/Rap", "Rock", "Electronic/Dance", "Enka", "City Pop",
        "Classical"
    ],
    "China": [
        "C-Pop/C-Rock", "Hip-Hop/Rap", "Folk", "Rock",
        "Classical"
    ],
    "Taiwan": ["TW-Pop/TW-Rock", "Hip-Hop/Rap", "Rock", "Mandopop", "Classical"],
    "Hong Kong": ["HK-Pop/HK-Rock", "Cantopop", "Hip-Hop/Rap", "Classical"],
    "Macau": ["Macanese Pop/Rock", "Cantopop", "Pop"],
    "Mongolia": ["Mongolian Pop/Rock/Metal", "Folk Metal", "Hip-Hop/Rap"],
    "Indonesia": [
        "Indonesian Pop/Dangdut", "Rock", "Hip-Hop/Rap",
        "Electronic/Dance", "Keroncong"
    ],
    "Malaysia": [
        "Malaysian Pop", "Indonesian Pop/Dangdut", "K-Pop/K-Rock",
        "J-Pop/J-Rock", "Hip-Hop/Rap"
    ],
    "Singapore": [
        "Singaporean Pop", "K-Pop/K-Rock", "J-Pop/J-Rock",
        "C-Pop/C-Rock", "Hip-Hop/Rap"
    ],
    "Philippines": [
        "OPM", "K-Pop/K-Rock", "J-Pop/J-Rock", "Pop",
        "Rock", "Hip-Hop/Rap"
    ],
    "Thailand": [
        "T-Pop/T-Rock", "K-Pop/K-Rock", "J-Pop/J-Rock",
        "Luk Thung", "Mor Lam", "Hip-Hop/Rap"
    ],
    "Vietnam": [
        "V-Pop/V-Rock", "K-Pop/K-Rock", "Hip-Hop/Rap",
        "Vietnamese Bolero", "Folk"
    ],
    "Myanmar": ["Burmese Pop/Rock", "Hip-Hop/Rap"],
    "Cambodia": ["Cambodian Pop/Rock", "Hip-Hop/Rap", "Folk"],
    "Laos": ["Lao Pop/Rock", "Mor Lam", "Hip-Hop/Rap"],
    "Brunei": ["Bruneian Pop/Rock", "Malaysian Pop", "K-Pop/K-Rock"],
    "Timor-Leste": ["Timorese Pop/Rock", "Dancehall/Reggae", "Folk"],
    # Central Asia and Caucasus
    "Kazakhstan": ["Q-pop/Q-rock", "Pop", "Hip-Hop/Rap", "Folk"],
    "Uzbekistan": ["Pop", "Hip-Hop/Rap", "Folk", "Rock"],
    "Turkmenistan": ["Pop", "Folk"],
    "Kyrgyzstan": ["Pop", "Hip-Hop/Rap", "Folk"],
    "Tajikistan": ["Pop", "Folk"],
    "Azerbaijan": ["Pop", "Hip-Hop/Rap", "Mugham", "Rock"],
    "Georgia": ["Pop", "Hip-Hop/Rap", "Folk", "Rock"],
    "Armenia": ["Pop", "Hip-Hop/Rap", "Folk", "Rock", "Classical"],
    # Oceania
    "Australia": [
        "Pop", "Hip-Hop/Rap", "Rock", "Alternative",
        "Electronic/Dance", "Country", "Aboriginal Australian Pop/Rock",
        "Classical"
    ],
    "New Zealand": [
        "Pop", "Hip-Hop/Rap", "Rock", "Alternative",
        "Maori Pop/Rock", "Electronic/Dance", "Pacific Reggae",
        "Classical"
    ],
    "Papua New Guinea": ["PNG Pop/Rock", "Dancehall/Reggae", "Stringband", "Folk"],
    "Fiji": ["Pasifika Pop/Rock", "Dancehall/Reggae", "Folk", "Indian Pop"],
    "Samoa": ["Pasifika Pop/Rock", "Dancehall/Reggae", "Folk"],
    "Tonga": ["Pasifika Pop/Rock", "Dancehall/Reggae", "Folk"],
    "Solomon Islands": ["Pasifika Pop/Rock", "Folk"],
    "Vanuatu": ["Pasifika Pop/Rock", "Folk"],
    "Micronesia": ["Pasifika Pop/Rock", "Folk"],
    "Marshall Islands": ["Pasifika Pop/Rock", "Folk"],
    "Palau": ["Pasifika Pop/Rock", "Folk"],
    "Nauru": ["Pasifika Pop/Rock", "Folk"],
    "Kiribati": ["Pasifika Pop/Rock", "Folk"],
    "Tuvalu": ["Pasifika Pop/Rock", "Folk"],
    "Hawaii": ["Hawaiian Pop/Rock", "Pop", "Reggae", "Slack Key Guitar"],
}

# Safe default when no country data is available
DEFAULT_GENRE = "Pop"
DEFAULT_COUNTRY = "Unknown"


# -----------------------------------------------------------------------------
# COLLABORATION WEIGHT SYSTEM (from script 3)
# Helper functions that resolve country and genre for multi-artist tracks.
# -----------------------------------------------------------------------------

def get_continent(country: str) -> str:
    """
    Map a country name to its continent identifier.

    Args:
        country: Full country name (e.g., 'Brazil')

    Returns:
        str: Continent label, or 'Unknown' if not found in lookup table
    """
    return COUNTRY_TO_CONTINENT.get(country, "Unknown")


def infer_genre_by_country(artists_info: List[Dict]) -> str:
    """
    Infer the most representative genre for a set of artists from the same country.

    Logic:
    1. If a single genre accounts for >50% of artists, use it directly.
    2. Otherwise, walk the country's GENRE_HIERARCHY list and return the
       first genre that appears in the known artist genres.
    3. Fall back to the top of the hierarchy if no match is found.

    Args:
        artists_info: List of dicts with keys 'country' and 'genre'

    Returns:
        str: Resolved genre label
    """
    if not artists_info:
        return DEFAULT_GENRE

    # Use the primary artist's country to anchor the hierarchy lookup
    country = artists_info[0]['country']
    hierarchy = GENRE_HIERARCHY.get(country, [DEFAULT_GENRE])

    known_genres = [a['genre'] for a in artists_info if a['genre']]
    if not known_genres:
        return hierarchy[0] if hierarchy else DEFAULT_GENRE

    counter = Counter(known_genres)
    most_common_genre = counter.most_common(1)[0][0]

    # Absolute majority check
    if counter[most_common_genre] > len(known_genres) / 2:
        return most_common_genre

    # Hierarchy-guided tiebreaker
    for priority_genre in hierarchy:
        if priority_genre in known_genres:
            return priority_genre

    return hierarchy[0] if hierarchy else DEFAULT_GENRE


def resolve_country_and_genre(artists_info: List[Dict]) -> Tuple[str, str]:
    """
    Apply the collaboration weight algorithm to determine a single
    country and genre for a potentially multi-artist track.

    Decision tree:
        Rule 1 – Absolute majority (>50%): assign majority country + its genre
        Rule 2 – Exact 50/50 split (2 countries): assign the majority country
        Rule 3 – Relative majority (<50%): assign if same continent and ≤2 distinct
                  countries, otherwise 'Multi-country' / 'Multi-genre'

    Args:
        artists_info: List of dicts with keys 'name', 'country', 'genre'

    Returns:
        tuple: (country_str, genre_str)
    """
    total_artists = len(artists_info)
    if total_artists == 0:
        return DEFAULT_COUNTRY, DEFAULT_GENRE

    # Single artist — straightforward
    if total_artists == 1:
        info = artists_info[0]
        return info['country'] or DEFAULT_COUNTRY, info['genre'] or DEFAULT_GENRE

    # Filter artists with known country
    known = [a for a in artists_info if a['country'] is not None]
    if not known:
        return DEFAULT_COUNTRY, DEFAULT_GENRE

    known_countries = [a['country'] for a in known]
    country_counter = Counter(known_countries)
    majority_country = country_counter.most_common(1)[0][0]
    majority_count = country_counter[majority_country]
    majority_pct = majority_count / total_artists

    continents = [get_continent(c) for c in known_countries if c]
    continent_counter = Counter(continents)
    distinct_continents = len(continent_counter)
    distinct_countries = len(country_counter)

    # Rule 1: Absolute majority (>50%)
    if majority_pct > 0.5:
        # Fill unknown-country slots with the majority country before genre inference
        filled = []
        for a in artists_info:
            if a['country'] is None:
                filled.append({'country': majority_country, 'genre': None})
            else:
                filled.append(a)
        majority_artists = [a for a in filled if a['country'] == majority_country]
        genre = infer_genre_by_country(majority_artists)
        return majority_country, genre

    # Rule 2: Exact 50/50 split between exactly 2 countries
    if majority_pct == 0.5:
        if distinct_countries == 2:
            majority_artists = [a for a in known if a['country'] == majority_country]
            genre = infer_genre_by_country(majority_artists)
            return majority_country, genre
        else:
            return "Multi-country", "Multi-genre"

    # Rule 3: Relative majority (<50%) — same-continent, ≤2 countries
    if majority_pct < 0.5:
        if distinct_continents == 1 and distinct_countries <= 2:
            majority_artists = [a for a in known if a['country'] == majority_country]
            genre = infer_genre_by_country(majority_artists)
            return majority_country, genre
        else:
            return "Multi-country", "Multi-genre"

    # Safety net — should never be reached with valid input
    return "Multi-country", "Multi-genre"


def normalize_name(name: str) -> str:
    """
    Normalize an artist name for fuzzy matching against the artist database.

    Transforms to lowercase, strips extra whitespace, and removes punctuation
    so that "Bad Bunny", "bad bunny", and "bad  bunny!" all resolve to the
    same dictionary key.

    Args:
        name: Raw artist name string

    Returns:
        str: Normalized name suitable for dict lookup
    """
    if name is None:
        return ""
    name = re.sub(r'\s+', ' ', str(name)).strip().lower()
    name = re.sub(r'[^\w\s]', '', name)
    return name


def parse_artist_list(artist_names: str) -> List[str]:
    """
    Split a raw 'Artist Names' CSV field into individual artist name strings.

    Handles the most common delimiters found in YouTube Charts exports:
    &, feat., ft., comma, 'y', 'and', 'with', 'x', 'vs'.

    Args:
        artist_names: Raw string from the 'Artist Names' chart column

    Returns:
        list[str]: Individual artist names, whitespace-stripped
    """
    if artist_names is None:
        return []
    text = artist_names
    for sep in ['&', 'feat.', 'ft.', ',', ' y ', ' and ', ' with ', ' x ', ' vs ']:
        text = text.replace(sep, '|')
    return [part.strip() for part in text.split('|') if part.strip()]


def load_artist_lookup() -> Dict[str, Tuple[str, str]]:
    """
    Load artist records from the local SQLite file into an in-memory dict for O(1) lookups.

    The file is expected at charts_archive/2_1.countries-genres-artist/artist_countries_genres.db

    Returns:
        dict: {normalized_name: (country, macro_genre)} mapping

    Raises:
        SystemExit: If the artist database file does not exist.
    """
    if not ARTIST_DB_PATH.exists():
        print(f"❌ Artist database not found at: {ARTIST_DB_PATH}")
        print("   Please ensure script 2_1 has run successfully.")
        sys.exit(1)

    print("🌍 Loading artist metadata database from local path...")
    conn = sqlite3.connect(ARTIST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, country, macro_genre FROM artist")
    rows = cursor.fetchall()
    conn.close()

    artist_lookup = {}
    for raw_name, country, genre in rows:
        key = normalize_name(raw_name)
        artist_lookup[key] = (country, genre)

    print(f"   ✅ Loaded {len(artist_lookup)} artists from local DB.")
    return artist_lookup


def get_artist_info(artist_names: str, artist_lookup: Dict) -> List[Dict]:
    """
    Resolve each artist in a track's 'Artist Names' field against the lookup dict.

    Args:
        artist_names: Raw 'Artist Names' string from the chart row
        artist_lookup: Dict returned by load_artist_lookup()

    Returns:
        list[dict]: One entry per artist with keys 'name', 'country', 'genre'
    """
    names = parse_artist_list(artist_names)
    if not names:
        return []

    result = []
    for name in names:
        key = normalize_name(name)
        country, genre = artist_lookup.get(key, (None, None))
        result.append({'name': name, 'country': country, 'genre': genre})
    return result


# -----------------------------------------------------------------------------
# Helper: Check if country/genre data is missing or invalid
# -----------------------------------------------------------------------------
def needs_country_genre_update(row: Optional[Tuple]) -> bool:
    """
    Determine if a record requires country/genre resolution based on current values.

    Args:
        row: Tuple (artist_country, macro_genre) from database, or None if record not found.

    Returns:
        bool: True if record does not exist or has NULL/Unknown/empty country or genre.
    """
    if row is None:
        return True  # Record doesn't exist, will be inserted
    country, genre = row
    invalid_country = country is None or country.strip() == "" or country == "Unknown"
    invalid_genre = genre is None or genre.strip() == "" or genre == "Unknown"
    return invalid_country or invalid_genre


# -----------------------------------------------------------------------------
# Original functions (modified to support extended schema)
# -----------------------------------------------------------------------------

def get_week_identifier_from_filename(filename: str) -> Optional[str]:
    """
    Extract ISO week identifier from database filename.
    
    Args:
        filename: Database filename (e.g., 'youtube_charts_2026-W15.db')
        
    Returns:
        str: Week identifier in format 'YYYY-WXX', or None if pattern doesn't match
    """
    match = DB_FILENAME_PATTERN.match(filename)
    if match:
        # Extract week identifier by removing prefix and extension
        week_id = filename.replace("youtube_charts_", "").replace(".db", "")
        return week_id
    return None


def get_most_recent_database(directory: Path) -> Optional[Path]:
    """
    Identify the most recent YouTube Charts database file in the specified directory.
    
    Selection algorithm:
        1. Filter files matching pattern: youtube_charts_20YY-Www.db
        2. Extract ISO week identifiers for comparison
        3. Sort by year (descending), then by week number (descending)
        4. Return path to the most recent valid database
    
    This approach correctly handles year boundaries (e.g., 2025-W52 vs 2026-W01).
    Lexicographic sorting works because ISO format 'YYYY-WXX' is naturally ordered.
    
    Args:
        directory: Path object pointing to directory containing weekly databases
        
    Returns:
        Path: Absolute path to most recent database file, or None if none found
    """
    matching_files: List[Tuple[str, Path]] = []
    
    # Scan directory for files matching naming convention
    for file_path in directory.glob("youtube_charts_*.db"):
        filename = file_path.name
        week_id = get_week_identifier_from_filename(filename)
        if week_id:
            matching_files.append((week_id, file_path))
    
    if not matching_files:
        return None
    
    # Sort by week identifier (lexicographic order works due to ISO format)
    # Example: '2026-W15' > '2025-W52' in string comparison
    matching_files.sort(key=lambda x: x[0], reverse=True)
    
    most_recent_week, most_recent_path = matching_files[0]
    return most_recent_path


def initialize_target_schema(connection: sqlite3.Connection) -> None:
    """
    Ensure target catalog table exists with correct schema definition.
    
    Creates the artist_track table if it doesn't exist with the following structure:
        id            : INTEGER PRIMARY KEY AUTOINCREMENT
        artist_names  : VARCHAR(200) NOT NULL
        track_name    : VARCHAR(200) NOT NULL
        artist_country: TEXT NOT NULL
        macro_genre   : TEXT NOT NULL
        artists_found : TEXT
    
    If the table already exists but lacks the new columns, they are added via ALTER TABLE.
    
    Args:
        connection: Active SQLite database connection
        
    Raises:
        sqlite3.Error: If schema creation fails
    """
    cursor = connection.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='artist_track'")
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        # Create table with full schema
        ddl_statement = """
            CREATE TABLE artist_track (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_names  VARCHAR(200) NOT NULL,
                track_name    VARCHAR(200) NOT NULL,
                artist_country TEXT NOT NULL,
                macro_genre    TEXT NOT NULL,
                artists_found  TEXT
            )
        """
        try:
            with connection:
                connection.execute(ddl_statement)
            print("   ✅ Created artist_track table with extended schema.")
        except sqlite3.Error as e:
            print(f"   ❌ Schema initialization error: {e}")
            raise
    else:
        # Table exists: check for missing columns and add them
        cursor.execute("PRAGMA table_info(artist_track)")
        columns = {row[1] for row in cursor.fetchall()}
        
        new_columns = []
        if 'artist_country' not in columns:
            new_columns.append(('artist_country', 'TEXT NOT NULL DEFAULT "Unknown"'))
        if 'macro_genre' not in columns:
            new_columns.append(('macro_genre', 'TEXT NOT NULL DEFAULT "Pop"'))
        if 'artists_found' not in columns:
            new_columns.append(('artists_found', 'TEXT'))
        
        for col_name, col_def in new_columns:
            try:
                with connection:
                    connection.execute(f"ALTER TABLE artist_track ADD COLUMN {col_name} {col_def}")
                print(f"   ✅ Added column {col_name} to existing artist_track table.")
            except sqlite3.Error as e:
                print(f"   ⚠️  Could not add column {col_name}: {e}")
        
        if new_columns:
            print("   ✅ Schema migration completed.")
        else:
            print("   ✅ Schema already up to date.")


def get_catalog_statistics(connection: sqlite3.Connection) -> Tuple[int, int]:
    """
    Retrieve current catalog statistics.
    
    Args:
        connection: Active SQLite database connection
        
    Returns:
        Tuple[int, int]: (total_records, latest_id)
            - total_records: Total number of unique songs in catalog
            - latest_id: Highest auto-generated ID (0 if empty)
    """
    cursor = connection.cursor()
    
    cursor.execute("SELECT COUNT(*), COALESCE(MAX(id), 0) FROM artist_track")
    total_records, latest_id = cursor.fetchone()
    
    return total_records, latest_id


def migrate_data() -> int:
    """
    Execute the ETL pipeline to update the song catalog.
    
    Process flow:
        1. Validate source directory and locate most recent database
        2. Load artist metadata for country/genre resolution
        3. Establish read-only connection to source database
        4. Establish read-write connection to target catalog
        5. Initialize/migrate target schema
        6. Extract distinct artist-track pairs from source
        7. For each pair:
            a. If record does not exist, resolve country/genre and INSERT
            b. If record exists but has NULL/Unknown country or genre, resolve and UPDATE
            c. Otherwise, skip (already has valid data)
        8. Commit transaction and report statistics
        9. Handle errors gracefully with appropriate exit codes
    
    Returns:
        int: Exit code (0 = success, 1 = failure)
    """
    print("\n" + "=" * 70)
    print("🎵 YOUTUBE CHARTS - SONG CATALOG BUILDER")
    print("   IDEMPOTENT ETL PIPELINE FOR ARTIST-TRACK CATALOG")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # -------------------------------------------------------------------------
    # Phase 1: Source Database Selection
    # -------------------------------------------------------------------------
    print("\n1. 🔍 LOCATING MOST RECENT SOURCE DATABASE...")
    
    if not SOURCE_DIR.exists():
        print(f"   ❌ Source directory does not exist: {SOURCE_DIR}")
        print(f"   ℹ️  Please run 1_download.py first to populate chart databases")
        return 1
    
    source_path = get_most_recent_database(SOURCE_DIR)
    
    if not source_path:
        print(f"   ❌ No database files found matching pattern: youtube_charts_20XX-WXX.db")
        print(f"   📁 Directory: {SOURCE_DIR}")
        return 1
    
    source_week_id = get_week_identifier_from_filename(source_path.name)
    source_size_kb = source_path.stat().st_size / 1024
    
    print(f"   ✅ Source identified: {source_path.name}")
    print(f"   📆 Week identifier: {source_week_id}")
    print(f"   📊 File size: {source_size_kb:.1f} KB")
    
    # -------------------------------------------------------------------------
    # Phase 2: Load Artist Metadata
    # -------------------------------------------------------------------------
    print("\n2. 🌍 LOADING ARTIST METADATA DATABASE...")
    artist_lookup = load_artist_lookup()
    
    # -------------------------------------------------------------------------
    # Phase 3: Database Connections
    # -------------------------------------------------------------------------
    print("\n3. 🔗 ESTABLISHING DATABASE CONNECTIONS...")
    
    target_path = TARGET_DIR / TARGET_DB_NAME
    target_exists = target_path.exists()
    
    # Source connection: read-only mode prevents accidental modification
    # URI connection format allows parameter specification
    source_uri = f"file:{source_path}?mode=ro"
    
    try:
        source_conn = sqlite3.connect(source_uri, uri=True)
        source_conn.row_factory = sqlite3.Row  # Enable column access by name
        source_cursor = source_conn.cursor()
        
        # Verify source database has expected table structure
        source_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chart_data'"
        )
        if not source_cursor.fetchone():
            print(f"   ❌ Source database missing 'chart_data' table")
            source_conn.close()
            return 1
        
        print(f"   ✅ Source connection established (read-only mode)")
        
        target_conn = sqlite3.connect(target_path)
        target_cursor = target_conn.cursor()
        
        if target_exists:
            target_size_kb = target_path.stat().st_size / 1024
            print(f"   ✅ Target connection established (existing: {target_size_kb:.1f} KB)")
        else:
            print(f"   ✅ Target connection established (new database)")
            
    except sqlite3.Error as e:
        print(f"   ❌ Database connection error: {e}")
        return 1
    
    # -------------------------------------------------------------------------
    # Phase 4: Schema Initialization / Migration
    # -------------------------------------------------------------------------
    print("\n4. 📋 INITIALIZING TARGET SCHEMA...")
    
    try:
        initialize_target_schema(target_conn)
        
        # Get pre-migration statistics for growth calculation
        initial_count, initial_max_id = get_catalog_statistics(target_conn)
        print(f"   📊 Current catalog size: {initial_count:,} records")
        
    except sqlite3.Error as e:
        print(f"   ❌ Schema initialization failed: {e}")
        source_conn.close()
        target_conn.close()
        return 1
    
    # -------------------------------------------------------------------------
    # Phase 5: Data Extraction and Transformation
    # -------------------------------------------------------------------------
    print("\n5. 📤 EXTRACTING ARTIST-TRACK PAIRS FROM SOURCE...")
    
    # Extract distinct artist-track pairs from source
    # Using DISTINCT to reduce processing overhead for duplicates within source
    # Filters out NULL and empty strings to maintain data quality
    extract_query = """
        SELECT DISTINCT
            "Artist Names" AS artist_names,
            "Track Name" AS track_name
        FROM chart_data
        WHERE "Artist Names" IS NOT NULL
          AND "Track Name" IS NOT NULL
          AND TRIM("Artist Names") != ''
          AND TRIM("Track Name") != ''
        ORDER BY "Artist Names", "Track Name"
    """
    
    try:
        source_cursor.execute(extract_query)
        all_rows = source_cursor.fetchall()
        total_extracted = len(all_rows)
        
        print(f"   ✅ Extracted {total_extracted:,} distinct artist-track pairs")
        
        if total_extracted == 0:
            print(f"   ⚠️  No valid records found in source database")
            source_conn.close()
            target_conn.close()
            return 0
            
    except sqlite3.Error as e:
        print(f"   ❌ Data extraction error: {e}")
        source_conn.close()
        target_conn.close()
        return 1
    
    # -------------------------------------------------------------------------
    # Phase 6: Idempotent Insertion / Conditional Update with Country/Genre Resolution
    # -------------------------------------------------------------------------
    print("\n6. 💾 PERFORMING IDEMPOTENT OPERATIONS...")
    print("   🔬 Resolving country and macro-genre for new/incomplete records...")
    
    insert_statement = """
        INSERT INTO artist_track (artist_names, track_name, artist_country, macro_genre, artists_found)
        VALUES (?, ?, ?, ?, ?)
    """
    
    update_statement = """
        UPDATE artist_track
        SET artist_country = ?, macro_genre = ?, artists_found = ?
        WHERE artist_names = ? AND track_name = ?
    """
    
    # Query to fetch existing country/genre for a given artist-track pair
    check_query = """
        SELECT artist_country, macro_genre
        FROM artist_track
        WHERE artist_names = ? AND track_name = ?
    """
    
    inserted_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    # Calculate progress intervals for user feedback (25%, 50%, 75%, 100%)
    progress_interval = max(1, total_extracted // 4)
    
    for idx, row in enumerate(all_rows, 1):
        artist_names = row['artist_names']
        track_name = row['track_name']
        
        try:
            # Check current state in catalog
            target_cursor.execute(check_query, (artist_names, track_name))
            existing = target_cursor.fetchone()
            
            if needs_country_genre_update(existing):
                # Resolve country and genre using collaboration weight algorithm
                artists_info = get_artist_info(artist_names, artist_lookup)
                final_country, final_genre = resolve_country_and_genre(artists_info)
                
                # Count matched artists for transparency
                matched = sum(1 for a in artists_info if a['country'] is not None)
                total_arts = len(artists_info) if artists_info else 1
                artists_found_str = f"{matched}/{total_arts}"
                
                if existing is None:
                    # Insert new record
                    target_cursor.execute(insert_statement, (
                        artist_names, track_name, final_country, final_genre, artists_found_str
                    ))
                    inserted_count += 1
                else:
                    # Update existing record with missing/invalid data
                    target_cursor.execute(update_statement, (
                        final_country, final_genre, artists_found_str, artist_names, track_name
                    ))
                    updated_count += 1
            else:
                skipped_count += 1
                
        except sqlite3.Error as e:
            error_count += 1
            # Limit error noise to first 5 occurrences
            if error_count <= 5:
                print(f"   ⚠️  Error processing: {artist_names[:30]}... - {track_name[:30]}... : {e}")
        
        # Progress reporting at calculated intervals
        if idx % progress_interval == 0 or idx == total_extracted:
            progress_pct = (idx / total_extracted) * 100
            print(f"   📈 Progress: {idx:,}/{total_extracted:,} ({progress_pct:.1f}%) - "
                  f"Inserted: {inserted_count:,}, Updated: {updated_count:,}, Skipped: {skipped_count:,}")
    
    # Commit all pending transactions atomically
    target_conn.commit()
    
    print(f"\n   ✅ Operations completed:")
    print(f"      🆕 New records inserted: {inserted_count:,}")
    print(f"      🔄 Existing records updated: {updated_count:,}")
    print(f"      ⏭️  Valid records skipped: {skipped_count:,}")
    if error_count > 0:
        print(f"      ⚠️  Errors encountered: {error_count}")
    
    # -------------------------------------------------------------------------
    # Phase 7: Verification and Statistics
    # -------------------------------------------------------------------------
    print("\n7. 📊 VERIFICATION AND STATISTICS...")
    
    final_count, final_max_id = get_catalog_statistics(target_conn)
    
    # Verify count matches expectation (initial + inserted = final)
    expected_final = initial_count + inserted_count
    if final_count == expected_final:
        print(f"   ✅ Integrity check passed: {final_count:,} total records")
    else:
        print(f"   ⚠️  Count mismatch: Expected {expected_final:,}, Found {final_count:,}")
    
    # Calculate growth percentage (0% if initial_count is 0)
    if initial_count > 0:
        growth_pct = ((final_count - initial_count) / initial_count) * 100
        print(f"   📈 Catalog growth: +{growth_pct:.2f}%")
    
    print(f"   🔑 Latest ID: {final_max_id}")
    print(f"   💾 Database location: {target_path}")
    print(f"   📀 Database size: {target_path.stat().st_size / 1024:.1f} KB")
    
    # Sample recent entries for human verification (last 5 inserted)
    print(f"\n   📋 Sample of recent catalog entries:")
    target_cursor.execute("""
        SELECT id, artist_names, track_name, artist_country, macro_genre, artists_found
        FROM artist_track
        ORDER BY id DESC
        LIMIT 5
    """)
    
    recent_entries = target_cursor.fetchall()
    for entry_id, artist, track, country, genre, found in recent_entries:
        # Truncate long strings for display readability
        artist_display = artist[:30] + "..." if len(artist) > 30 else artist
        track_display = track[:30] + "..." if len(track) > 30 else track
        print(f"      [{entry_id:4d}] {artist_display} — {track_display}")
        print(f"            🌍 {country} | 🎵 {genre} | 👥 {found}")
    
    # -------------------------------------------------------------------------
    # Phase 8: Cleanup
    # -------------------------------------------------------------------------
    source_conn.close()
    target_conn.close()
    
    print("\n" + "=" * 70)
    if inserted_count > 0 or updated_count > 0:
        print(f"✅ CATALOG UPDATED: Added {inserted_count:,} songs, Updated {updated_count:,} songs")
    else:
        print(f"✅ CATALOG UNCHANGED: No new songs or updates required")
    print("=" * 70)
    
    return 0


def list_catalog_summary() -> None:
    """
    Display summary statistics of the song catalog.
    
    Shows:
    - Total unique songs
    - Most recent additions (last 5)
    - Top artists by unique song count
    - Database file information
    
    This function is idempotent and safe to call even if catalog doesn't exist.
    """
    target_path = TARGET_DIR / TARGET_DB_NAME
    
    if not target_path.exists():
        print("   ℹ️  Song catalog does not exist yet")
        print("   💡 Run with migration first to create catalog")
        return
    
    try:
        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()
        
        # Check if table exists (handles empty/partial databases)
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='artist_track'"
        )
        if not cursor.fetchone():
            print("   ℹ️  artist_track table not found in catalog")
            conn.close()
            return
        
        # Get global statistics
        total_records, latest_id = get_catalog_statistics(conn)
        
        # Get most recent additions (for verification)
        cursor.execute("""
            SELECT id, artist_names, track_name, artist_country, macro_genre
            FROM artist_track
            ORDER BY id DESC
            LIMIT 10
        """)
        recent = cursor.fetchall()
        
        # Get top artists by song count (for analytics insights)
        cursor.execute("""
            SELECT artist_names, COUNT(*) as song_count
            FROM artist_track
            GROUP BY artist_names
            ORDER BY song_count DESC
            LIMIT 5
        """)
        top_artists = cursor.fetchall()
        
        conn.close()
        
        print(f"\n📀 SONG CATALOG SUMMARY:")
        print(f"   📊 Total unique songs: {total_records:,}")
        print(f"   🔑 Highest ID: {latest_id}")
        print(f"   💾 File size: {target_path.stat().st_size / 1024:.1f} KB")
        
        if top_artists:
            print(f"\n   🏆 Top artists by unique songs:")
            for artist, count in top_artists:
                artist_display = artist[:50] + "..." if len(artist) > 50 else artist
                print(f"      • {artist_display}: {count} songs")
        
        if recent:
            print(f"\n   🆕 Most recent additions:")
            for entry_id, artist, track, country, genre in recent[:5]:
                artist_display = artist[:40] + "..." if len(artist) > 40 else artist
                track_display = track[:40] + "..." if len(track) > 40 else track
                print(f"      [{entry_id:4d}] {artist_display} — {track_display}")
                print(f"            🌍 {country} | 🎵 {genre}")
                
    except sqlite3.Error as e:
        print(f"   ⚠️  Error reading catalog: {e}")


def main() -> int:
    """
    Main execution function.
    
    Workflow:
        1. Execute ETL pipeline to update song catalog
        2. Display catalog summary statistics
        3. Return appropriate exit code
        
    Returns:
        int: Exit code (0 = success, 1 = error)
    """
    # Execute migration (ETL pipeline)
    exit_code = migrate_data()
    
    # Display catalog summary if migration succeeded
    if exit_code == 0:
        list_catalog_summary()
    else:
        print("\n❌ Migration failed. See errors above.")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
