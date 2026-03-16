#!/usr/bin/env python3

"""
YouTube Charts Data Enrichment Pipeline
=========================================
Enriches weekly chart data with YouTube metadata and artist origin information.

Workflow:
- Reads the latest chart database (SQLite) from charts_archive/1_download-chart/databases/
- Downloads artist_countries_genres.db temporarily from GitHub
- Fetches YouTube video metadata using a three-layer fallback system:
    1. YouTube Data API v3 (fastest, requires API key)
    2. Selenium browser automation (when API is unavailable)
    3. yt-dlp with anti-blocking options (last resort)
- Applies a weighted collaboration algorithm to resolve country/genre for multi-artist tracks
- Saves enriched results to charts_archive/3_enrich-chart-data/ as {name}_enriched.db

Requirements:
- Python 3.7+
- requests
- yt-dlp
- selenium + webdriver-manager (optional, used as fallback)
- google-api-python-client + isodate (optional, used when API key is present)
- sqlite3 (included in Python standard library)

Author: Alfonso Droguett
License: MIT
"""

import os
import sys
import re
import time
import sqlite3
import tempfile
import requests
import subprocess
from pathlib import Path
from datetime import datetime
from collections import Counter

# ---------------------------------------------------------------------
# PATH CONFIGURATION
# ---------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent  # Music-Charts-Intelligence/

# Input: most recent weekly chart database
INPUT_DB_DIR = PROJECT_ROOT / "charts_archive" / "1_download-chart" / "databases"

# Remote artist metadata database (country + macro-genre per artist)
URL_ARTISTS_DB = "https://github.com/adroguetth/Music-Charts-Intelligence/raw/refs/heads/main/charts_archive/2_countries-genres-artist/artist_countries_genres.db"

# Output: enriched database written here
OUTPUT_DIR = PROJECT_ROOT / "charts_archive" / "3_enrich-chart-data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Optional: set YOUTUBE_API_KEY env var to enable the API layer
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# Detect GitHub Actions environment to suppress interactive prompts
IN_GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"


# ---------------------------------------------------------------------
# LOOKUP TABLES
# Country → Continent mapping used by the collaboration weight algorithm.
# Continent-level resolution is the fallback when per-country logic is
# inconclusive (e.g., 3+ countries with no clear majority).
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# COLLABORATION WEIGHT SYSTEM
# Helper functions that resolve country and genre for multi-artist tracks.
# The decision rules below implement a tiered majority logic:
#   > 50% same country   → assign that country
#   = 50% (two countries) → assign the majority country
#   < 50% but same continent (≤2 countries) → assign relative majority country
#   otherwise            → "Multi-country" / "Multi-genre"
# ---------------------------------------------------------------------

def get_continent(country: str) -> str:
    """
    Map a country name to its continent identifier.

    Args:
        country: Full country name (e.g., 'Brazil')

    Returns:
        str: Continent label, or 'Unknown' if not found in lookup table
    """
    return COUNTRY_TO_CONTINENT.get(country, "Unknown")


def infer_genre_by_country(artists_info: list) -> str:
    """
    Infer the most representative genre for a set of artists from the same country.

    Logic:
    1. If a single genre accounts for >50% of artists, use it directly.
    2. Otherwise, walk the country's GENRE_HIERARCHY list and return the
       first genre that appears in the known artist genres.
    3. Fall back to the top of the hierarchy if no match is found.

    Args:
        artists_info: List of dicts with keys 'pais'/'country' and 'genre'

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


def resolve_country_and_genre(artists_info: list) -> tuple:
    """
    Apply the collaboration weight algorithm to determine a single
    country and genre for a potentially multi-artist track.

    Decision tree:
        Rule 1 – Absolute majority (>50%): assign majority country + its genre
        Rule 2 – Exact 50/50 split (2 countries): assign the majority country
        Rule 3 – Relative majority (<50%): assign if same continent and ≤2 distinct
                  countries, otherwise 'Multi-country' / 'Multi-genre'

    Args:
        artists_info: List of dicts with keys 'nombre'/'name', 'country', 'genre'

    Returns:
        tuple: (country_str, genre_str)
    """
    total_artists = len(artists_info)
    if total_artists == 0:
        return "Unknown", DEFAULT_GENRE

    # Single artist — straightforward
    if total_artists == 1:
        info = artists_info[0]
        return info['country'] or "Unknown", info['genre'] or DEFAULT_GENRE

    # Filter artists with known country
    known = [a for a in artists_info if a['country'] is not None]
    if not known:
        return "Unknown", DEFAULT_GENRE

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


def parse_artist_list(artist_names: str) -> list:
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


# ---------------------------------------------------------------------
# VIDEO METADATA DETECTION HELPERS
# These functions classify video attributes from title/description text
# without requiring API access — used by all three retrieval layers.
# ---------------------------------------------------------------------

def detect_video_type(title: str, description: str = "") -> dict:
    """
    Classify the video type (official, lyric, live, remix/special version)
    by scanning title and description for known keyword patterns.

    Args:
        title: YouTube video title
        description: Video description text (optional, improves accuracy)

    Returns:
        dict: Boolean flags — is_official_video, is_lyric_video,
              is_live_performance, is_special_version
    """
    full_text = f"{title.lower()} {description.lower()}"
    title_lower = title.lower()

    is_official = any(kw in full_text for kw in [
        'official', 'video oficial', 'official video',
        'official music video', 'vídeo oficial'
    ])
    is_lyric = any(kw in title_lower for kw in [
        'lyric', 'lyrics', 'letra', 'letras', 'karaoke',
        'lyric video', 'letra oficial'
    ]) or 'lyric' in full_text

    is_live = any(kw in full_text for kw in [
        'live', 'en vivo', 'concert', 'performance', 'show',
        'live performance', 'en concierto', 'directo'
    ])
    is_special = any(kw in title_lower for kw in [
        'remix', 'version', 'edit', 'mix', 'bootleg', 'rework',
        'sped up', 'slowed', 'reverb', 'acoustic', 'acústico',
        'piano version', 'instrumental'
    ])
    return {
        'is_official_video': is_official,
        'is_lyric_video': is_lyric,
        'is_live_performance': is_live,
        'is_special_version': is_special
    }


def detect_collaboration(title: str, artists_csv: str) -> dict:
    """
    Detect whether a track is a multi-artist collaboration.

    Uses regex patterns on the title and falls back to counting delimiters
    in the CSV artist field when title patterns are absent.

    Args:
        title: YouTube video title
        artists_csv: Raw 'Artist Names' string from the chart row

    Returns:
        dict: is_collaboration (bool) and artist_count (int, capped at 10)
    """
    title_lower = title.lower()
    collab_patterns = [
        r'\sft\.\s', r'\sfeat\.\s', r'\sfeaturing\s', r'\sft\s',
        r'\scon\s', r'\swith\s', r'\s&\s', r'\sx\s', r'\s×\s',
        r'\(feat\.', r'\(ft\.', r'\(with', r'\[feat\.', r'\[ft\.'
    ]
    is_collab = any(re.search(p, title_lower, re.IGNORECASE) for p in collab_patterns)

    if artists_csv:
        # Count delimiter-separated tokens as a proxy for artist count
        artist_count = artists_csv.count('&') + artists_csv.count(',') + 1
    else:
        artist_count = 1
        if is_collab:
            # Rough heuristic when CSV is missing
            artist_count = 2 + title_lower.count(' & ') + title_lower.count(' x ')

    return {
        'is_collaboration': is_collab,
        'artist_count': min(artist_count, 10)  # cap at 10 to prevent outliers
    }


def detect_channel_type(channel_title: str) -> dict:
    """
    Classify the YouTube channel type from its title string.

    Categories:
        VEVO         – major label premium channel
        Topic        – auto-generated YouTube Music channel
        Label/Studio – record label or production house
        Artist Channel – verified artist or band channel
        User Channel – generic user/fan upload channel
        General      – unclassified

    Args:
        channel_title: Channel display name

    Returns:
        dict: channel_type key with the resolved category string
    """
    if not channel_title:
        return {'channel_type': 'unknown'}

    ch = channel_title.lower()

    if 'vevo' in ch:
        return {'channel_type': 'VEVO'}
    elif 'topic' in ch:
        return {'channel_type': 'Topic'}
    elif any(w in ch for w in ['records', 'music', 'label', 'entertainment',
                                'studios', 'production', 'presents', 'network']):
        return {'channel_type': 'Label/Studio'}
    elif any(w in ch for w in ['official', 'oficial', 'artist', 'band', 'singer',
                                'musician', 'rapper', 'dj', 'producer']):
        return {'channel_type': 'Artist Channel'}
    elif any(w in ch for w in ['channel', 'tv', 'hd', 'video', 'videos']):
        return {'channel_type': 'User Channel'}
    else:
        # Structured names like "Beyoncé - Topic" often contain separators
        if ' - ' in channel_title or ' | ' in channel_title:
            return {'channel_type': 'Artist Channel'}
        return {'channel_type': 'General'}


def parse_upload_season(publish_date: str) -> dict:
    """
    Derive the fiscal quarter from an ISO date string.

    Maps calendar months to Q1–Q4 using standard quarter boundaries.

    Args:
        publish_date: Date string in 'YYYY-MM-DD' format (only first 10 chars used)

    Returns:
        dict: upload_season key with value 'Q1'–'Q4' or 'unknown'
    """
    if not publish_date or len(publish_date) < 10:
        return {'upload_season': 'unknown'}
    try:
        date = datetime.strptime(publish_date[:10], "%Y-%m-%d")
        quarter = (date.month - 1) // 3 + 1
        return {'upload_season': f'Q{quarter}'}
    except Exception:
        return {'upload_season': 'unknown'}


def detect_region_restrictions(content_details: dict) -> dict:
    """
    Check whether a video carries regional restriction metadata.

    A video is flagged as restricted if the contentDetails object contains
    either a 'blocked' or 'allowed' region list — both indicate geo-gating.

    Args:
        content_details: The 'contentDetails' sub-object from the YouTube API response

    Returns:
        dict: region_restricted (bool)
    """
    if not content_details:
        return {'region_restricted': False}
    region = content_details.get('regionRestriction', {})
    return {'region_restricted': bool(region.get('blocked') or region.get('allowed'))}


# ---------------------------------------------------------------------
# METADATA RETRIEVAL LAYERS
# Three-layer fallback: YouTube API → Selenium → yt-dlp
# Each layer returns the same dict schema so the caller is layer-agnostic.
# ---------------------------------------------------------------------

def _empty_metadata() -> dict:
    """
    Return a zeroed-out metadata dict used as the default before any
    successful retrieval. Keeps the caller code DRY.
    """
    return {
        'Duration (s)': 0,
        'duration (m:s)': "0:00",
        'upload_date': "",
        'likes': 0,
        'comment_count': 0,
        'audio_language': "",
        'is_official_video': False,
        'is_lyric_video': False,
        'is_live_performance': False,
        'upload_season': 'unknown',
        'channel_type': 'unknown',
        'is_collaboration': False,
        'artist_count': 1,
        'region_restricted': False,
        'error': ""
    }


def fetch_metadata_via_selenium(url: str, artists_csv: str = "") -> dict:
    """
    Layer 2: Fetch basic video metadata using a headless Chromium browser.

    Useful when the YouTube Data API is unavailable (no key, quota exhausted)
    and yt-dlp is being blocked. Extracts: title, duration, channel name,
    upload date, and video type flags.

    Note: Selenium does NOT return likes, comment count, or audio language —
    those fields remain at their zero defaults.

    Args:
        url: Full YouTube video URL
        artists_csv: Raw 'Artist Names' string used for collaboration detection

    Returns:
        dict: Metadata dict (same schema as _empty_metadata)
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service

    metadata = _empty_metadata()
    errors = []

    # Standard headless Chrome configuration with a realistic user-agent
    # to avoid bot-detection on YouTube pages
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)

        # Wait for the video title to confirm the page has rendered
        wait = WebDriverWait(driver, 10)
        title_el = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.ytd-video-primary-info-renderer"))
        )
        title = title_el.text

        # Duration — scraped from the player progress bar label
        try:
            dur_el = driver.find_element(By.CSS_SELECTOR, "span.ytp-time-duration")
            parts = dur_el.text.split(':')
            if len(parts) == 2:
                duration_s = int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                duration_s = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:
                duration_s = 0
            metadata['Duration (s)'] = duration_s
            metadata['duration (m:s)'] = f"{duration_s // 60}:{duration_s % 60:02d}"
        except Exception:
            pass

        # Channel name — used for channel type classification
        try:
            channel_el = driver.find_element(By.CSS_SELECTOR, "a.ytd-channel-name")
            metadata.update(detect_channel_type(channel_el.text))
        except Exception:
            pass

        metadata.update(detect_video_type(title, ""))
        metadata.update(detect_collaboration(title, artists_csv))

        # Upload date from structured data meta tag (more reliable than visible text)
        try:
            date_el = driver.find_element(By.CSS_SELECTOR, "meta[itemprop='datePublished']")
            date_str = date_el.get_attribute("content")[:10]
            if date_str:
                metadata['upload_date'] = date_str
                metadata.update(parse_upload_season(date_str))
        except Exception:
            pass

        driver.quit()

    except Exception as e:
        errors.append(f"Selenium error: {e}")
        try:
            driver.quit()
        except Exception:
            pass

    if errors:
        metadata['error'] = " | ".join(errors)
    return metadata


def fetch_video_metadata(url: str, artists_csv: str = "", api_key: str = None) -> dict:
    """
    Orchestrate the three-layer metadata retrieval strategy.

    Layer 1 — YouTube Data API v3 (requires YOUTUBE_API_KEY):
        Full metadata: duration, likes, comments, language, date, restrictions.
        Exits immediately on success.

    Layer 2 — Selenium headless browser:
        Partial metadata: duration, channel type, date, video type flags.
        Used when API is absent or returns an error.

    Layer 3 — yt-dlp with anti-blocking client rotation:
        Tries android → ios → android+web → web player clients in order.
        Last resort; may be slower and still fail against aggressive bot detection.

    Args:
        url: Full YouTube video URL
        artists_csv: Raw 'Artist Names' string for collaboration detection
        api_key: YouTube Data API v3 key (optional)

    Returns:
        dict: Populated metadata dict; 'error' key is non-empty if all layers fail
    """
    metadata = _empty_metadata()
    errors = []

    # ------------------------------------------------------------------
    # LAYER 1: YouTube Data API v3
    # ------------------------------------------------------------------
    if api_key:
        try:
            try:
                import isodate
            except ImportError:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "isodate"])
                import isodate

            from googleapiclient.discovery import build

            # Extract the 11-character video ID from any YouTube URL format
            vid_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
            if vid_match:
                video_id = vid_match.group(1)
                youtube = build('youtube', 'v3', developerKey=api_key)
                response = youtube.videos().list(
                    part='snippet,contentDetails,statistics',
                    id=video_id
                ).execute()

                if response.get('items'):
                    video = response['items'][0]
                    snippet = video.get('snippet', {})
                    stats = video.get('statistics', {})
                    content = video.get('contentDetails', {})

                    # Parse ISO 8601 duration (e.g., PT3M47S → 227 seconds)
                    iso_dur = content.get('duration', '')
                    if iso_dur:
                        dur_s = int(isodate.parse_duration(iso_dur).total_seconds())
                        metadata['Duration (s)'] = dur_s
                        metadata['duration (m:s)'] = f"{dur_s // 60}:{dur_s % 60:02d}"

                    metadata['likes'] = int(stats.get('likeCount', 0))
                    metadata['comment_count'] = int(stats.get('commentCount', 0))

                    lang = snippet.get('defaultAudioLanguage', '')
                    metadata['audio_language'] = lang[:2].upper() if lang else ""

                    region = content.get('regionRestriction', {})
                    metadata['region_restricted'] = bool(
                        region.get('blocked') or region.get('allowed')
                    )

                    pub_date = snippet.get('publishedAt', '')[:10]
                    if pub_date:
                        metadata['upload_date'] = pub_date
                        metadata.update(parse_upload_season(pub_date))

                    title_api = snippet.get('title', '')
                    desc_api = snippet.get('description', '')
                    channel_api = snippet.get('channelTitle', '')
                    metadata.update(detect_video_type(title_api, desc_api))
                    metadata.update(detect_channel_type(channel_api))
                    metadata.update(detect_collaboration(title_api, artists_csv))

                    return metadata  # Layer 1 succeeded — skip layers 2 and 3
                else:
                    errors.append("API: video not found")
            else:
                errors.append("API: could not extract video_id from URL")

        except Exception as e:
            errors.append(f"API error: {e}")

    # ------------------------------------------------------------------
    # LAYER 2: Selenium headless browser
    # ------------------------------------------------------------------
    if errors or not api_key:
        try:
            try:
                import selenium
                import webdriver_manager
            except ImportError:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", "selenium", "webdriver-manager"
                ])

            sel_data = fetch_metadata_via_selenium(url, artists_csv)
            if not sel_data['error']:
                metadata.update(sel_data)
                return metadata
            else:
                errors.append(sel_data['error'])
        except Exception as e:
            errors.append(f"Selenium setup error: {e}")

    # ------------------------------------------------------------------
    # LAYER 3: yt-dlp with rotating player client options
    # Cycling through android/ios/web clients helps bypass 403 blocks
    # that YouTube imposes on default yt-dlp requests.
    # ------------------------------------------------------------------
    try:
        import yt_dlp

        # Keep yt-dlp up-to-date — extractor fixes ship frequently
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                capture_output=True, check=False
            )
        except Exception:
            pass

        client_options = [
            {'player_client': ['android']},
            {'player_client': ['ios']},
            {'player_client': ['android', 'web']},
            {'player_client': ['web']},
        ]

        info = None
        last_error = ""

        for opts in client_options:
            ydl_config = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'ignoreerrors': False,
                'extract_flat': False,
                'user_agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ),
                'extractor_retries': 5,
                'fragment_retries': 5,
                'retry_sleep_functions': {'extractor': 2},
                'sleep_interval': 2,
                'sleep_interval_requests': 2,
                **opts
            }
            try:
                with yt_dlp.YoutubeDL(ydl_config) as ydl:
                    info = ydl.extract_info(url, download=False)
                if info:
                    break
            except Exception as e:
                last_error = str(e)
                continue

        if info:
            duration = info.get('duration', 0)
            raw_date = info.get('upload_date', '')

            # yt-dlp returns date as YYYYMMDD — convert to ISO format
            if raw_date and len(raw_date) == 8:
                iso_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                metadata['upload_date'] = iso_date
                metadata.update(parse_upload_season(iso_date))

            title_ydlp = info.get('title', '')
            desc_ydlp = info.get('description', '')
            channel_ydlp = info.get('channel', '')

            metadata.update({
                'Duration (s)': duration,
                'duration (m:s)': f"{duration // 60}:{duration % 60:02d}",
                'likes': info.get('like_count', 0),
            })
            metadata.update(detect_video_type(title_ydlp, desc_ydlp))
            metadata.update(detect_channel_type(channel_ydlp))
            metadata.update(detect_collaboration(title_ydlp, artists_csv))
            errors = []  # Clear previous errors — layer 3 succeeded

        else:
            errors.append(f"yt-dlp could not extract info: {last_error}")

    except Exception as e:
        errors.append(f"yt-dlp general error: {e}")

    if errors:
        metadata['error'] = " | ".join(errors)
        if IN_GITHUB_ACTIONS:
            print(f"⚠️  Metadata error for {url}: {metadata['error']}")

    return metadata


# ---------------------------------------------------------------------
# DATABASE UTILITIES
# Input/output SQLite operations for chart data and the artist lookup DB.
# ---------------------------------------------------------------------

def find_latest_chart_db() -> Path:
    """
    Locate the most recent chart database file by lexicographic sort.

    Filenames follow the pattern 'youtube_charts_YYYY-WXX.db', so
    lexicographic order is equivalent to chronological order.

    Returns:
        Path: Path to the latest .db file

    Raises:
        FileNotFoundError: If the input directory or any .db files are absent
    """
    if not INPUT_DB_DIR.exists():
        raise FileNotFoundError(f"Input directory not found: {INPUT_DB_DIR}")
    db_files = list(INPUT_DB_DIR.glob("*.db"))
    if not db_files:
        raise FileNotFoundError(f"No .db files found in {INPUT_DB_DIR}")
    db_files.sort(key=lambda p: p.name, reverse=True)
    return db_files[0]


def load_chart_songs(db_path: Path) -> list:
    """
    Read all rows from the 'chart_data' table into a list of dicts.

    Validates that the required columns (Rank, Artist Names, Track Name,
    YouTube URL) are present before returning data.

    Args:
        db_path: Path to the SQLite chart database

    Returns:
        list[dict]: One dict per chart row

    Raises:
        Exception: If the table is missing or required columns are absent
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chart_data'")
    if not cursor.fetchone():
        conn.close()
        raise Exception(f"Table 'chart_data' not found in {db_path}")

    # Use DISTINCT on Rank to guard against duplicate weekly runs that may have
    # written the same chart twice into the source database (see script 1 behavior).
    # ROW_NUMBER() picks the first occurrence per Rank and discards the rest.
    cursor.execute("""
        SELECT * FROM chart_data
        WHERE rowid IN (
            SELECT MIN(rowid) FROM chart_data GROUP BY Rank
        )
        ORDER BY Rank
    """)
    rows = cursor.fetchall()
    conn.close()

    songs = [dict(row) for row in rows]

    required_columns = {"Rank", "Artist Names", "Track Name", "YouTube URL"}
    if songs:
        actual_columns = set(songs[0].keys())
        missing = required_columns - actual_columns
        if missing:
            raise Exception(f"Missing columns in chart_data: {missing}")

    return songs


def download_artist_db(url: str) -> Path:
    """
    Download the remote artist metadata database to a temporary file.

    The file is intentionally kept in the system temp directory and
    should be deleted by the caller after use (see main()).

    Args:
        url: Direct download URL for the artist_countries_genres.db file

    Returns:
        Path: Path to the downloaded temporary file

    Raises:
        SystemExit: On HTTP error or connection failure
    """
    print("🌍 Downloading artist database from GitHub...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to download artist DB: {e}")
        sys.exit(1)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.write(response.content)
    tmp.close()
    print(f"   ✅ Artist DB downloaded to: {tmp.name}")
    return Path(tmp.name)


def build_artist_lookup(db_path: Path) -> dict:
    """
    Load artist records from the SQLite file into an in-memory dict for O(1) lookups.

    The normalized name is used as the key to handle minor spelling differences
    between the chart data and the artist database.

    Args:
        db_path: Path to the artist_countries_genres.db file

    Returns:
        dict: {normalized_name: (country, macro_genre)} mapping
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, country, macro_genre FROM artist")
    rows = cursor.fetchall()
    conn.close()

    artist_lookup = {}
    for raw_name, country, genre in rows:
        key = normalize_name(raw_name)
        artist_lookup[key] = (country, genre)

    print(f"   ✅ Loaded {len(artist_lookup)} artists from remote DB.")
    return artist_lookup


def get_artist_info(artist_names: str, artist_lookup: dict) -> list:
    """
    Resolve each artist in a track's 'Artist Names' field against the lookup dict.

    Args:
        artist_names: Raw 'Artist Names' string from the chart row
        artist_lookup: Dict returned by build_artist_lookup()

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


def create_output_table(conn: sqlite3.Connection):
    """
    (Re)create the 'enriched_songs' table from scratch on every pipeline run.

    DROP + CREATE is intentional: this is a fully derived table. Re-running
    the pipeline should always produce exactly 100 clean rows, never append
    on top of a previous run.

    Args:
        conn: Open SQLite connection to the output database
    """
    cursor = conn.cursor()
    # Wipe any previous run — idempotent by design
    cursor.execute('DROP TABLE IF EXISTS enriched_songs')
    cursor.execute('''
        CREATE TABLE enriched_songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rank INTEGER,
            artist_names TEXT,
            track_name TEXT,
            periods_on_chart INTEGER,
            views INTEGER,
            youtube_url TEXT,
            duration_s INTEGER,
            duration_ms TEXT,
            upload_date TEXT,
            likes INTEGER,
            comment_count INTEGER,
            audio_language TEXT,
            is_official_video BOOLEAN,
            is_lyric_video BOOLEAN,
            is_live_performance BOOLEAN,
            upload_season TEXT,
            channel_type TEXT,
            is_collaboration BOOLEAN,
            artist_count INTEGER,
            region_restricted BOOLEAN,
            artist_country TEXT,
            macro_genre TEXT,
            artists_found TEXT,
            error TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('CREATE INDEX idx_country ON enriched_songs(artist_country)')
    cursor.execute('CREATE INDEX idx_genre ON enriched_songs(macro_genre)')
    cursor.execute('CREATE INDEX idx_upload_date ON enriched_songs(upload_date)')
    cursor.execute('CREATE INDEX idx_error ON enriched_songs(error)')
    conn.commit()


def insert_enriched_row(conn: sqlite3.Connection, row: dict):
    """
    Insert a single enriched song record into the output table.

    Args:
        conn: Open SQLite connection
        row: Dict with keys matching the enriched_songs schema
    """
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO enriched_songs (
            rank, artist_names, track_name, periods_on_chart, views, youtube_url,
            duration_s, duration_ms, upload_date, likes, comment_count,
            audio_language, is_official_video, is_lyric_video, is_live_performance,
            upload_season, channel_type, is_collaboration, artist_count,
            region_restricted, artist_country, macro_genre,
            artists_found, error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        row['rank'], row['artist_names'], row['track_name'],
        row['periods_on_chart'], row['views'], row['youtube_url'],
        row['duration_s'], row['duration_ms'], row['upload_date'],
        row['likes'], row['comment_count'], row['audio_language'],
        row['is_official_video'], row['is_lyric_video'], row['is_live_performance'],
        row['upload_season'], row['channel_type'], row['is_collaboration'],
        row['artist_count'], row['region_restricted'], row['artist_country'],
        row['macro_genre'], row['artists_found'], row['error']
    ))
    conn.commit()


# ---------------------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------------------

def main():
    """
    Main execution function.

    Workflow:
    1.  Locate the latest weekly chart database
    2.  Download and index the remote artist metadata database
    3.  Verify yt-dlp is installed (install if missing)
    4.  Load chart songs from SQLite
    5.  Create the output enriched database
    6.  For each song: fetch YouTube metadata, resolve country/genre, write row
    7.  Print summary statistics
    8.  Clean up temporary files

    Returns:
        int: Exit code — 0 on success, 1 on critical error
    """
    print("\n" + "=" * 70)
    print("🎵 CHART ENRICHMENT PIPELINE (API → Selenium → yt-dlp)")
    print("   METADATA EXTRACTION + ARTIST COUNTRY/GENRE RESOLUTION")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 1. Locate latest chart database
    print("\n1. 📂 LOCATING LATEST CHART DATABASE...")
    try:
        chart_db_path = find_latest_chart_db()
        print(f"   ✅ Found: {chart_db_path.name}")
    except Exception as e:
        print(f"   ❌ {e}")
        sys.exit(1)

    # 2. Download and index remote artist database
    print("\n2. 🌍 LOADING ARTIST METADATA DATABASE...")
    artist_db_tmp = download_artist_db(URL_ARTISTS_DB)
    artist_lookup = build_artist_lookup(artist_db_tmp)

    # 3. Ensure yt-dlp is available (install silently if not)
    print("\n3. 🔧 CHECKING DEPENDENCIES...")
    try:
        import yt_dlp
        print("   ✅ yt-dlp available")
    except ImportError:
        print("   📦 Installing yt-dlp...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
        import yt_dlp
        print("   ✅ yt-dlp installed")

    # 4. Load chart songs
    print(f"\n4. 📖 READING CHART DATA FROM {chart_db_path.name}...")
    try:
        songs = load_chart_songs(chart_db_path)
        print(f"   ✅ {len(songs)} songs loaded")
    except Exception as e:
        print(f"   ❌ Error reading chart database: {e}")
        sys.exit(1)

    # 5. Prepare output database
    print("\n5. 🗃️  PREPARING OUTPUT DATABASE...")
    output_db_path = OUTPUT_DIR / f"{chart_db_path.stem}_enriched.db"
    conn_out = sqlite3.connect(output_db_path)
    create_output_table(conn_out)
    print(f"   ✅ Output path: {output_db_path}")

    # 6. Process each song
    print(f"\n6. 🎬 ENRICHING {len(songs)} SONGS...")
    print("   ⏱️  This may take several minutes depending on retrieval layer used...")

    for i, song in enumerate(songs, 1):
        url = song['YouTube URL']
        track = song['Track Name'][:30]
        artists_csv = song.get('Artist Names', '')

        print(f"   [{i:2d}/{len(songs)}] {track:30}... ", end='', flush=True)

        # Fetch YouTube metadata (three-layer fallback)
        metadata = fetch_video_metadata(url, artists_csv, YOUTUBE_API_KEY)

        # Resolve artist country and genre via the collaboration weight algorithm
        artists_info = get_artist_info(artists_csv, artist_lookup)
        final_country, final_genre = resolve_country_and_genre(artists_info)

        # Count how many artists were successfully matched against the lookup DB
        matched = sum(1 for a in artists_info if a['country'] is not None)
        total_arts = len(artists_info) if artists_info else 1

        # Build output row
        row = {
            'rank': song.get('Rank'),
            'artist_names': artists_csv,
            'track_name': song.get('Track Name'),
            'periods_on_chart': song.get('Periods on Chart'),
            'views': song.get('Views'),
            'youtube_url': url,
            'duration_s': metadata['Duration (s)'],
            'duration_ms': metadata['duration (m:s)'],
            'upload_date': metadata['upload_date'],
            'likes': metadata['likes'],
            'comment_count': metadata['comment_count'],
            'audio_language': metadata['audio_language'],
            'is_official_video': metadata['is_official_video'],
            'is_lyric_video': metadata['is_lyric_video'],
            'is_live_performance': metadata['is_live_performance'],
            'upload_season': metadata['upload_season'],
            'channel_type': metadata['channel_type'],
            'is_collaboration': metadata['is_collaboration'],
            'artist_count': metadata['artist_count'],
            'region_restricted': metadata['region_restricted'],
            'artist_country': final_country,
            'macro_genre': final_genre,
            'artists_found': f"{matched}/{total_arts}",
            'error': metadata['error']
        }

        insert_enriched_row(conn_out, row)

        # Build a compact inline status summary for the console
        badges = []
        if metadata['Duration (s)'] > 0:
            badges.append(f"⏱️{metadata['duration (m:s)']}")
        if metadata['is_official_video']:
            badges.append("📀")
        if metadata['is_lyric_video']:
            badges.append("📝")
        if metadata['is_live_performance']:
            badges.append("🎤")
        if metadata['is_collaboration']:
            badges.append(f"👥{metadata['artist_count']}")
        if final_country not in ["Unknown", "Multi-country"]:
            badges.append(f"🌍{final_country[:2]}")
        elif final_country == "Multi-country":
            badges.append("🌐")
        if matched < total_arts:
            badges.append(f"⚠️{matched}/{total_arts}")

        if badges:
            print(f"({' '.join(badges)}) → {final_country[:15]}, {final_genre[:15]}")
        else:
            error_display = metadata['error'][:20] if metadata['error'] else "No data"
            print(f"({error_display})")

        # Brief pause to avoid hammering endpoints when API is not used
        time.sleep(0.1)

    conn_out.close()

    # 7. Summary statistics
    print("\n7. 📊 FINAL SUMMARY:")
    conn_stats = sqlite3.connect(output_db_path)
    cur = conn_stats.cursor()

    cur.execute("SELECT COUNT(*) FROM enriched_songs")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM enriched_songs WHERE artist_country = 'Multi-country'")
    multi_country = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(DISTINCT artist_country) FROM enriched_songs "
        "WHERE artist_country NOT IN ('Unknown', 'Multi-country')"
    )
    unique_countries = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(DISTINCT macro_genre) FROM enriched_songs "
        "WHERE macro_genre != 'Multi-genre' AND macro_genre IS NOT NULL"
    )
    unique_genres = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM enriched_songs WHERE artist_country = 'Unknown'")
    unknown_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM enriched_songs WHERE error != ''")
    error_count = cur.fetchone()[0]

    conn_stats.close()

    print(f"   💾 Output database: {output_db_path}")
    print(f"      📊 Total songs:              {total}")
    print(f"      🌐 Multi-country collabs:    {multi_country} ({multi_country / total * 100:.1f}%)")
    print(f"      🗺️  Distinct countries:       {unique_countries}")
    print(f"      🎵 Distinct genres:           {unique_genres}")
    print(f"      ❓ Songs with unknown country: {unknown_count} ({unknown_count / total * 100:.1f}%)")
    print(f"      ⚠️  Songs with metadata errors: {error_count} ({error_count / total * 100:.1f}%)")

    # 8. Clean up temporary artist DB file
    print("\n8. 🧹 CLEANING UP...")
    os.unlink(artist_db_tmp)
    print("   ✅ Temporary artist database removed.")

    print("\n" + "=" * 70)
    print("✅ ENRICHMENT PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    # Warn and prompt the user when running locally without an API key.
    # In CI/CD (GitHub Actions) this block is skipped entirely.
    if not IN_GITHUB_ACTIONS and not YOUTUBE_API_KEY:
        print("\n⚠️  YOUTUBE_API_KEY environment variable is not set.")
        print("   Metadata will be fetched via Selenium and yt-dlp (slower).")
        answer = input("Continue anyway? (y/n): ").strip().lower()
        if answer not in ['y', 'yes']:
            print("Process cancelled.")
            sys.exit(0)
    sys.exit(main())
