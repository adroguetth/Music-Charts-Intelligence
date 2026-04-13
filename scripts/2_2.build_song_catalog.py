#!/usr/bin/env python3
"""
YouTube Charts Song Catalog Builder with Country/Genre Resolution
==================================================================
Automated ETL pipeline for building and maintaining a canonical song catalog
from YouTube Charts weekly snapshots, now enriched with artist origin country
and macro-genre using a deterministic collaboration weight algorithm.

Features:
- Automatic detection of most recent weekly chart database
- Integration with pre-downloaded artist metadata DB (artist_countries_genres.db)
- Weighted country/genre resolution for multi-artist collaborations
- Idempotent insertion: calculates attributes only once per unique song
- Surrogate primary key (id) with auto-increment
- Comprehensive logging and error handling

Data Flow:
1. Scan charts_archive/1_download-chart/databases/ for latest youtube_charts_20XX-WXX.db
2. Load artist metadata from charts_archive/2_1.countries-genres-artist/artist_countries_genres.db
3. Extract distinct (Artist Names, Track Name) tuples from source
4. For each new song:
   a. Parse artist list and resolve each artist's country/genre via lookup
   b. Apply collaboration weight algorithm to determine final country/genre
   c. Insert record with auto-generated ID and resolved attributes
5. Skip existing songs (no recalculation)

Database Schema (artist_track table):
    id             INTEGER PRIMARY KEY AUTOINCREMENT
    artist_names   VARCHAR(200) NOT NULL
    track_name     VARCHAR(200) NOT NULL
    artist_country VARCHAR(100)          -- resolved via weight algorithm
    macro_genre    VARCHAR(50)           -- resolved via weight algorithm
    artists_found  VARCHAR(20)           -- e.g., "2/3" (matched/total)
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP

Requirements:
- Python 3.7+
- sqlite3 (stdlib)
- pathlib (stdlib)
- Artist metadata DB must exist locally before execution.

Author: Alfonso Droguett
License: MIT
"""

import sqlite3
import re
import sys
from datetime import datetime
from pathlib import Path
from collections import Counter
from typing import Optional, Tuple, List, Dict, Any

# -----------------------------------------------------------------------------
# PATH CONFIGURATION
# -----------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent

# Source: weekly chart databases (from script 1_download-chart)
SOURCE_DIR = REPO_ROOT / "charts_archive" / "1_download-chart" / "databases"

# Artist metadata database (pre-downloaded by script 2_1)
ARTIST_DB_PATH = REPO_ROOT / "charts_archive" / "2_1.countries-genres-artist" / "artist_countries_genres.db"

# Target: canonical song catalog
TARGET_DIR = REPO_ROOT / "charts_archive" / "2_2.build-song-catalog"
TARGET_DB_NAME = "build_song.db"
TARGET_DIR.mkdir(parents=True, exist_ok=True)

# Regex for weekly DB filenames
DB_FILENAME_PATTERN = re.compile(r'youtube_charts_20\d{2}-W\d{1,2}\.db$')

# -----------------------------------------------------------------------------
# LOOKUP TABLES FOR COLLABORATION WEIGHT ALGORITHM
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

DEFAULT_GENRE = "Pop"

# -----------------------------------------------------------------------------
# COLLABORATION WEIGHT ALGORITHM FUNCTIONS
# -----------------------------------------------------------------------------
def normalize_name(name: str) -> str:
    """Normalize artist name for fuzzy matching against the artist database."""
    if name is None:
        return ""
    name = re.sub(r'\s+', ' ', str(name)).strip().lower()
    name = re.sub(r'[^\w\s]', '', name)
    return name

def parse_artist_list(artist_names: str) -> List[str]:
    """Split raw 'Artist Names' field into individual artist name strings."""
    if artist_names is None:
        return []
    text = artist_names
    for sep in ['&', 'feat.', 'ft.', ',', ' y ', ' and ', ' with ', ' x ', ' vs ']:
        text = text.replace(sep, '|')
    return [part.strip() for part in text.split('|') if part.strip()]

def get_continent(country: str) -> str:
    """Map a country name to its continent identifier."""
    return COUNTRY_TO_CONTINENT.get(country, "Unknown")

def infer_genre_by_country(artists_info: List[Dict[str, Any]]) -> str:
    """
    Infer the most representative genre for a set of artists from the same country.
    Logic: absolute majority (>50%) -> that genre; else follow hierarchy.
    """
    if not artists_info:
        return DEFAULT_GENRE
    country = artists_info[0]['country']
    hierarchy = GENRE_HIERARCHY.get(country, [DEFAULT_GENRE])
    known_genres = [a['genre'] for a in artists_info if a['genre']]
    if not known_genres:
        return hierarchy[0] if hierarchy else DEFAULT_GENRE
    counter = Counter(known_genres)
    most_common = counter.most_common(1)[0][0]
    if counter[most_common] > len(known_genres) / 2:
        return most_common
    for priority_genre in hierarchy:
        if priority_genre in known_genres:
            return priority_genre
    return hierarchy[0] if hierarchy else DEFAULT_GENRE

def resolve_country_and_genre(artists_info: List[Dict[str, Any]]) -> Tuple[str, str, str]:
    """
    Apply collaboration weight algorithm to determine a single country and genre.
    Returns: (country, genre, artists_found_string)
    """
    total_artists = len(artists_info)
    if total_artists == 0:
        return ("Unknown", DEFAULT_GENRE, "0/0")
    if total_artists == 1:
        info = artists_info[0]
        return (info['country'] or "Unknown", info['genre'] or DEFAULT_GENRE, f"1/1" if info['country'] else "0/1")

    known = [a for a in artists_info if a['country'] is not None]
    matched_count = len(known)
    artists_found_str = f"{matched_count}/{total_artists}"
    if not known:
        return ("Unknown", DEFAULT_GENRE, artists_found_str)

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
        filled = []
        for a in artists_info:
            if a['country'] is None:
                filled.append({'country': majority_country, 'genre': None})
            else:
                filled.append(a)
        majority_artists = [a for a in filled if a['country'] == majority_country]
        genre = infer_genre_by_country(majority_artists)
        return (majority_country, genre, artists_found_str)

    # Rule 2: Exact 50/50 split between exactly 2 countries
    if majority_pct == 0.5:
        if distinct_countries == 2:
            majority_artists = [a for a in known if a['country'] == majority_country]
            genre = infer_genre_by_country(majority_artists)
            return (majority_country, genre, artists_found_str)
        else:
            return ("Multi-country", "Multi-genre", artists_found_str)

    # Rule 3: Relative majority (<50%) – same continent and ≤2 distinct countries
    if majority_pct < 0.5:
        if distinct_continents == 1 and distinct_countries <= 2:
            majority_artists = [a for a in known if a['country'] == majority_country]
            genre = infer_genre_by_country(majority_artists)
            return (majority_country, genre, artists_found_str)
        else:
            return ("Multi-country", "Multi-genre", artists_found_str)

    return ("Multi-country", "Multi-genre", artists_found_str)

# -----------------------------------------------------------------------------
# DATABASE HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def get_week_identifier_from_filename(filename: str) -> Optional[str]:
    match = DB_FILENAME_PATTERN.match(filename)
    if match:
        return filename.replace("youtube_charts_", "").replace(".db", "")
    return None

def get_most_recent_database(directory: Path) -> Optional[Path]:
    matching_files = []
    for file_path in directory.glob("youtube_charts_*.db"):
        week_id = get_week_identifier_from_filename(file_path.name)
        if week_id:
            matching_files.append((week_id, file_path))
    if not matching_files:
        return None
    matching_files.sort(key=lambda x: x[0], reverse=True)
    return matching_files[0][1]

def load_artist_metadata(db_path: Path) -> Dict[str, Tuple[str, str]]:
    """Load artist (country, macro_genre) into a dict keyed by normalized name."""
    if not db_path.exists():
        raise FileNotFoundError(f"Artist metadata DB not found: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, country, macro_genre FROM artist")
    rows = cursor.fetchall()
    conn.close()
    lookup = {}
    for raw_name, country, genre in rows:
        key = normalize_name(raw_name)
        lookup[key] = (country, genre)
    return lookup

def get_artist_info_list(artist_names: str, lookup: Dict) -> List[Dict[str, Any]]:
    """Resolve each artist in the track's artist list against the lookup dict."""
    names = parse_artist_list(artist_names)
    if not names:
        return []
    result = []
    for name in names:
        key = normalize_name(name)
        country, genre = lookup.get(key, (None, None))
        result.append({'name': name, 'country': country, 'genre': genre})
    return result

def initialize_target_schema(connection: sqlite3.Connection) -> None:
    """Create artist_track table if not exists, with new country/genre columns."""
    ddl = """
        CREATE TABLE IF NOT EXISTS artist_track (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist_names VARCHAR(200) NOT NULL,
            track_name VARCHAR(200) NOT NULL,
            artist_country VARCHAR(100),
            macro_genre VARCHAR(50),
            artists_found VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    with connection:
        connection.execute(ddl)
    # Add columns if table existed from older version (migration)
    cursor = connection.cursor()
    cursor.execute("PRAGMA table_info(artist_track)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    for col, col_type in [('artist_country', 'VARCHAR(100)'),
                          ('macro_genre', 'VARCHAR(50)'),
                          ('artists_found', 'VARCHAR(20)'),
                          ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')]:
        if col not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE artist_track ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass  # Column may already exist
    connection.commit()

def record_exists(cursor: sqlite3.Cursor, artist_names: str, track_name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM artist_track WHERE artist_names = ? AND track_name = ? LIMIT 1",
        (artist_names, track_name)
    )
    return cursor.fetchone() is not None

def get_catalog_statistics(connection: sqlite3.Connection) -> Tuple[int, int]:
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*), COALESCE(MAX(id), 0) FROM artist_track")
    return cursor.fetchone()

# -----------------------------------------------------------------------------
# MAIN ETL PIPELINE
# -----------------------------------------------------------------------------
def migrate_data() -> int:
    print("\n" + "=" * 70)
    print("🎵 YOUTUBE CHARTS - SONG CATALOG BUILDER (with Country/Genre Resolution)")
    print("   IDEMPOTENT ETL PIPELINE FOR ARTIST-TRACK CATALOG")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 1. Locate source chart database
    print("\n1. 🔍 LOCATING MOST RECENT SOURCE DATABASE...")
    if not SOURCE_DIR.exists():
        print(f"   ❌ Source directory does not exist: {SOURCE_DIR}")
        return 1
    source_path = get_most_recent_database(SOURCE_DIR)
    if not source_path:
        print(f"   ❌ No weekly chart DB found in {SOURCE_DIR}")
        return 1
    source_week_id = get_week_identifier_from_filename(source_path.name)
    print(f"   ✅ Source: {source_path.name} (Week {source_week_id})")

    # 2. Load artist metadata (must exist)
    print("\n2. 🎤 LOADING ARTIST METADATA DATABASE...")
    if not ARTIST_DB_PATH.exists():
        print(f"   ❌ Artist DB not found at {ARTIST_DB_PATH}")
        print("      Please run script 2_1 first to download artist_countries_genres.db")
        return 1
    try:
        artist_lookup = load_artist_metadata(ARTIST_DB_PATH)
        print(f"   ✅ Loaded {len(artist_lookup)} artists from {ARTIST_DB_PATH.name}")
    except Exception as e:
        print(f"   ❌ Error loading artist DB: {e}")
        return 1

    # 3. Connect to source and target databases
    print("\n3. 🔗 ESTABLISHING DATABASE CONNECTIONS...")
    target_path = TARGET_DIR / TARGET_DB_NAME
    source_uri = f"file:{source_path}?mode=ro"
    try:
        source_conn = sqlite3.connect(source_uri, uri=True)
        source_conn.row_factory = sqlite3.Row
        source_cursor = source_conn.cursor()
        # Verify chart_data table exists
        source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chart_data'")
        if not source_cursor.fetchone():
            print("   ❌ Source DB missing 'chart_data' table")
            source_conn.close()
            return 1
        target_conn = sqlite3.connect(target_path)
        print(f"   ✅ Connections established")
    except sqlite3.Error as e:
        print(f"   ❌ Connection error: {e}")
        return 1

    # 4. Initialize target schema
    print("\n4. 📋 INITIALIZING TARGET SCHEMA...")
    initialize_target_schema(target_conn)
    initial_count, initial_max_id = get_catalog_statistics(target_conn)
    print(f"   ✅ Schema ready. Current catalog size: {initial_count:,} records")

    # 5. Extract distinct artist-track pairs
    print("\n5. 📤 EXTRACTING ARTIST-TRACK PAIRS FROM SOURCE...")
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
    source_cursor.execute(extract_query)
    all_rows = source_cursor.fetchall()
    total_extracted = len(all_rows)
    print(f"   ✅ Extracted {total_extracted:,} distinct pairs")
    if total_extracted == 0:
        source_conn.close()
        target_conn.close()
        return 0

    # 6. Idempotent insertion with country/genre resolution
    print("\n6. 💾 PERFORMING IDEMPOTENT INSERTION (calculating country/genre for new songs)...")
    target_cursor = target_conn.cursor()
    insert_stmt = """
        INSERT INTO artist_track (artist_names, track_name, artist_country, macro_genre, artists_found)
        VALUES (?, ?, ?, ?, ?)
    """
    inserted_count = 0
    skipped_count = 0
    progress_interval = max(1, total_extracted // 4)

    for idx, row in enumerate(all_rows, 1):
        artist_names = row['artist_names']
        track_name = row['track_name']

        if not record_exists(target_cursor, artist_names, track_name):
            # Resolve country/genre for this new song
            artists_info = get_artist_info_list(artist_names, artist_lookup)
            country, genre, artists_found = resolve_country_and_genre(artists_info)
            target_cursor.execute(insert_stmt, (artist_names, track_name, country, genre, artists_found))
            inserted_count += 1
        else:
            skipped_count += 1

        if idx % progress_interval == 0 or idx == total_extracted:
            progress_pct = (idx / total_extracted) * 100
            print(f"   📈 Progress: {idx:,}/{total_extracted:,} ({progress_pct:.1f}%) - "
                  f"Inserted: {inserted_count:,}, Skipped: {skipped_count:,}")

    target_conn.commit()
    print(f"\n   ✅ Insertion completed:")
    print(f"      🆕 New records inserted: {inserted_count:,}")
    print(f"      ⏭️  Already existed: {skipped_count:,}")

    # 7. Verification and statistics
    print("\n7. 📊 VERIFICATION AND STATISTICS...")
    final_count, final_max_id = get_catalog_statistics(target_conn)
    if final_count == initial_count + inserted_count:
        print(f"   ✅ Integrity check passed: {final_count:,} total records")
    else:
        print(f"   ⚠️  Count mismatch (expected {initial_count + inserted_count}, got {final_count})")
    if initial_count > 0:
        growth_pct = ((final_count - initial_count) / initial_count) * 100
        print(f"   📈 Catalog growth: +{growth_pct:.2f}%")
    print(f"   🔑 Latest ID: {final_max_id}")
    print(f"   💾 Database: {target_path} ({target_path.stat().st_size / 1024:.1f} KB)")

    # Show sample of recent entries with new attributes (handling possible NULLs safely)
    target_cursor.execute("""
        SELECT id, artist_names, track_name,
               COALESCE(artist_country, '') AS artist_country,
               COALESCE(macro_genre, '') AS macro_genre,
               COALESCE(artists_found, '') AS artists_found
        FROM artist_track ORDER BY id DESC LIMIT 5
    """)
    print("\n   📋 Sample of recent catalog entries:")
    for row in target_cursor.fetchall():
        country_display = row[3] if row[3] else 'N/A'
        genre_display = row[4] if row[4] else 'N/A'
        found_display = row[5] if row[5] else 'N/A'
        print(f"      [{row[0]:4d}] {row[1][:30]:30} — {row[2][:30]:30} | {country_display:15} | {genre_display:20} | {found_display}")

    source_conn.close()
    target_conn.close()

    print("\n" + "=" * 70)
    if inserted_count > 0:
        print(f"✅ CATALOG UPDATED: Added {inserted_count:,} new songs with resolved country/genre")
    else:
        print("✅ CATALOG UNCHANGED: No new songs to add")
    print("=" * 70)
    return 0

def list_catalog_summary() -> None:
    """Display summary statistics of the song catalog."""
    target_path = TARGET_DIR / TARGET_DB_NAME
    if not target_path.exists():
        print("   ℹ️  Song catalog does not exist yet")
        return
    try:
        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='artist_track'")
        if not cursor.fetchone():
            print("   ℹ️  artist_track table not found")
            conn.close()
            return
        total_records, latest_id = get_catalog_statistics(conn)
        cursor.execute("""
            SELECT id, artist_names, track_name,
                   COALESCE(artist_country, '') AS artist_country,
                   COALESCE(macro_genre, '') AS macro_genre
            FROM artist_track ORDER BY id DESC LIMIT 5
        """)
        recent = cursor.fetchall()
        conn.close()
        print(f"\n📀 SONG CATALOG SUMMARY:")
        print(f"   📊 Total unique songs: {total_records:,}")
        print(f"   🔑 Highest ID: {latest_id}")
        if recent:
            print(f"\n   🆕 Most recent additions:")
            for row in recent:
                country_display = row[3] if row[3] else 'N/A'
                genre_display = row[4] if row[4] else 'N/A'
                print(f"      [{row[0]:4d}] {row[1][:30]:30} — {row[2][:30]:30} | {country_display:15} | {genre_display:20}")
    except sqlite3.Error as e:
        print(f"   ⚠️  Error reading catalog: {e}")

def main() -> int:
    exit_code = migrate_data()
    if exit_code == 0:
        list_catalog_summary()
    else:
        print("\n❌ Migration failed.")
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
