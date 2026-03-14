#!/usr/bin/env python3
"""
SCRIPT UNIFICADO COMPLETO CON SISTEMA DE PESOS
- Salida a SQLite en charts_archive/3_enrich-chart-data/
- Obtiene metadatos específicos con yt-dlp + YouTube API
- Consulta país y género desde base de datos remota
- Implementa algoritmo de decisión para colaboraciones
"""

import csv
import re
import time
import sys
from datetime import datetime
from pathlib import Path
import sqlite3
import requests
import tempfile
import os
from collections import Counter

# =====================================================================
# CONFIGURACIÓN
# =====================================================================

API_KEY = "AIzaSyA3WKtRcRwn__qPc8Gt9mqCEvUFaCk13HE"
SCRIPT_DIR = Path(__file__).parent.absolute()
INPUT_CSV = SCRIPT_DIR / "latest_chart.csv"

# NUEVA RUTA: Base de datos SQLite de salida
DB_OUTPUT_DIR = SCRIPT_DIR / "charts_archive" / "3_enrich-chart-data"
DB_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)  # Crea el directorio si no existe

# Nombre del archivo con timestamp para evitar sobrescribir
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
DB_OUTPUT_PATH = DB_OUTPUT_DIR / f"chart_enriquecido_{timestamp}.db"

# URL RAW de tu base de datos en GitHub
URL_DB = "https://github.com/adroguetth/Music-Charts-Intelligence/raw/refs/heads/main/charts_archive/2_countries-genres-artist/artist_countries_genres.db"

# =====================================================================
# DICCIONARIOS DE SOPORTE
# =====================================================================

# Mapeo de países a continentes
PAIS_A_CONTINENTE = {
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
    "Georgia": "Asia", "Armenia": "Asia", "Russia": "Asia",  # Rusia es euroasiática
    
    # América del Norte
    "United States": "America", "Canada": "America", "Mexico": "America",
    "Guatemala": "America", "Honduras": "America", "El Salvador": "America",
    "Nicaragua": "America", "Costa Rica": "America", "Panama": "America",
    "Belize": "America",
    
    # Caribe
    "Cuba": "America", "Jamaica": "America", "Haiti": "America", "Dominican Republic": "America",
    "Puerto Rico": "America", "Bahamas": "America", "Trinidad and Tobago": "America",
    "Barbados": "America", "Saint Lucia": "America", "Grenada": "America",
    "Saint Vincent and the Grenadines": "America", "Antigua and Barbuda": "America",
    "Dominica": "America", "Saint Kitts and Nevis": "America",
    
    # América del Sur
    "Colombia": "America", "Venezuela": "America", "Ecuador": "America", "Peru": "America",
    "Bolivia": "America", "Chile": "America", "Argentina": "America", "Paraguay": "America",
    "Uruguay": "America", "Brazil": "America", "Guyana": "America", "Suriname": "America",
    "French Guiana": "America",
    
    # Europa
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
    
    # África
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
    
    # Oceanía
    "Australia": "Oceania", "New Zealand": "Oceania", "Papua New Guinea": "Oceania",
    "Fiji": "Oceania", "Samoa": "Oceania", "Tonga": "Oceania", "Solomon Islands": "Oceania",
    "Vanuatu": "Oceania", "Micronesia": "Oceania", "Marshall Islands": "Oceania",
    "Palau": "Oceania", "Nauru": "Oceania", "Kiribati": "Oceania", "Tuvalu": "Oceania",
    "Hawaii": "Oceania"
}

# Jerarquía de géneros por país (ordenados de más a menos representativo)
JERARQUIA_GENEROS = {
    # América del Norte
    "United States": [
        "Pop", "Hip-Hop/Rap", "R&B/Soul", "Country", "Rock",
        "Alternative", "Electrónica/Dance", "Reggaetón/Trap Latino",
        "Jazz/Blues", "Classical"
    ],
    "Canada": [
        "Pop", "Hip-Hop/Rap", "Rock", "Alternative",
        "Electrónica/Dance", "R&B/Soul", "Reggaetón/Trap Latino",
        "Country", "Classical"
    ],
    "Mexico": [
        "Regional Mexicano", "Reggaetón/Trap Latino", "Pop",
        "Bachata", "Cumbia", "Rock", "Tropical/Salsa/Merengue/Bolero",
        "Classical"
    ],

    # Centroamérica
    "Guatemala": ["Reggaetón/Trap Latino", "Bachata", "Cumbia", "Dancehall/Reggae", "Tropical/Salsa/Merengue/Bolero"],
    "Honduras": ["Reggaetón/Trap Latino", "Bachata", "Cumbia", "Dancehall/Reggae", "Tropical/Salsa/Merengue/Bolero"],
    "El Salvador": ["Reggaetón/Trap Latino", "Bachata", "Cumbia", "Dancehall/Reggae"],
    "Nicaragua": ["Reggaetón/Trap Latino", "Bachata", "Cumbia", "Dancehall/Reggae"],
    "Costa Rica": ["Reggaetón/Trap Latino", "Pop", "Bachata", "Cumbia", "Dancehall/Reggae", "Tropical/Salsa/Merengue/Bolero"],
    "Panama": [
        "Reggaetón/Trap Latino", "Dancehall/Reggae",
        "Tropical/Salsa/Merengue/Bolero", "Cumbia", "Pop"
    ],
    "Belize": ["Dancehall/Reggae", "Reggaetón/Trap Latino", "Pop", "Cumbia"],

    # Caribe
    "Jamaica": ["Dancehall/Reggae"],
    "Puerto Rico": ["Reggaetón/Trap Latino", "Pop"],
    "Dominican Republic": [
        "Reggaetón/Trap Latino", "Bachata", "Tropical/Salsa/Merengue/Bolero", "Dancehall/Reggae"
    ],
    "Cuba": [
        "Reggaetón/Trap Latino", "Tropical/Salsa/Merengue/Bolero",
        "Pop", "Jazz/Blues"
    ],
    "Haiti": ["Reggaetón/Trap Latino", "Tropical/Salsa/Merengue/Bolero", "Pop"],
    "Trinidad and Tobago": [
        "Tropical/Salsa/Merengue/Bolero", "Dancehall/Reggae",
        "Reggaetón/Trap Latino", "Pop"
    ],
    "Bahamas": ["Pop", "Dancehall/Reggae", "R&B/Soul"],
    "Barbados": ["Pop", "Dancehall/Reggae", "R&B/Soul", "Reggaetón/Trap Latino"],
    "Saint Lucia": ["Pop", "Dancehall/Reggae", "Reggaetón/Trap Latino"],
    "Grenada": ["Pop", "Dancehall/Reggae", "Reggaetón/Trap Latino"],
    "Saint Vincent and the Grenadines": ["Pop", "Dancehall/Reggae", "Reggaetón/Trap Latino"],
    "Antigua and Barbuda": ["Pop", "Dancehall/Reggae", "Reggaetón/Trap Latino"],
    "Dominica": ["Pop", "Dancehall/Reggae", "Reggaetón/Trap Latino"],
    "Saint Kitts and Nevis": ["Pop", "Dancehall/Reggae", "Reggaetón/Trap Latino"],

    # Sudamérica
    "Colombia": [
        "Reggaetón/Trap Latino", "Cumbia", "Vallenato",
        "Tropical/Salsa/Merengue/Bolero", "Pop", "Rock"
    ],
    "Venezuela": [
        "Reggaetón/Trap Latino", "Tropical/Salsa/Merengue/Bolero",
        "Pop", "Rock", "Classical"
    ],
    "Ecuador": ["Reggaetón/Trap Latino", "Cumbia", "Folklore/Raíces", "Pop"],
    "Peru": ["Reggaetón/Trap Latino", "Cumbia", "Folklore/Raíces", "Pop"],
    "Bolivia": ["Reggaetón/Trap Latino", "Cumbia", "Folklore/Raíces", "Pop"],
    "Chile": ["Reggaetón/Trap Latino", "Cumbia", "Pop", "Rock", "Folklore/Raíces", "Classical"],
    "Argentina": [
        "Reggaetón/Trap Latino", "Cumbia", "Rock", "Pop", "Folklore/Raíces",
        "Classical"
    ],
    "Paraguay": ["Reggaetón/Trap Latino", "Cumbia", "Folklore/Raíces", "Pop"],
    "Uruguay": ["Reggaetón/Trap Latino", "Cumbia", "Pop", "Rock", "Electrónica/Dance", "Classical"],
    "Brazil": [
        "Sertanejo", "Funk Brasileiro", "Reggaetón/Trap Latino",
        "Pop", "Rock", "Hip-Hop/Rap", "Forró", "Axé", "MPB",
        "Classical"
    ],
    "Guyana": ["Dancehall/Reggae", "Reggaetón/Trap Latino", "Pop"],
    "Suriname": ["Dancehall/Reggae", "Reggaetón/Trap Latino", "Pop"],
    "French Guiana": ["Dancehall/Reggae", "Reggaetón/Trap Latino", "Pop", "Kizomba/Zouk"],

    # Europa Occidental
    "Spain": [
        "Reggaetón/Trap Latino", "Pop", "Hip-Hop/Rap",
        "Flamenco / Copla", "Rock", "Electrónica/Dance",
        "Classical"
    ],
    "Portugal": [
        "Pop", "Hip-Hop/Rap", "Folklore/Raíces",
        "Kizomba/Zouk", "Reggaetón/Trap Latino", "Rock", "Fado",
        "Classical"
    ],
    "United Kingdom": [
        "Pop", "Hip-Hop/Rap", "Rock", "Alternative",
        "Electrónica/Dance", "Afrobeats", "Dancehall/Reggae",
        "R&B/Soul", "Classical"
    ],
    "Ireland": [
        "Pop", "Rock", "Alternative", "Hip-Hop/Rap",
        "Folklore/Raíces", "Electrónica/Dance", "Classical"
    ],
    "France": [
        "Pop", "Hip-Hop/Rap", "Electrónica/Dance", "Afrobeats",
        "Chanson", "R&B/Soul", "Rock", "Classical"
    ],
    "Belgium": ["Pop", "Hip-Hop/Rap", "Electrónica/Dance", "Rock", "Chanson", "Classical"],
    "Netherlands": ["Pop", "Electrónica/Dance", "Hip-Hop/Rap", "Rock", "Alternative", "Classical"],
    "Germany": [
        "Hip-Hop/Rap", "Pop", "Electrónica/Dance", "Schlager",
        "Rock", "Alternative", "Classical"
    ],
    "Austria": [
        "Pop", "Hip-Hop/Rap", "Schlager", "Rock", "Alpine Folk",
        "Classical"
    ],
    "Switzerland": [
        "Pop", "Hip-Hop/Rap", "Alpine Folk", "Rock",
        "Electrónica/Dance", "Schlager", "Classical"
    ],
    "Italy": [
        "Pop", "Hip-Hop/Rap", "Canzone Italiana", "Rock", "Electrónica/Dance",
        "Classical"
    ],
    "Greece": ["Pop", "Hip-Hop/Rap", "Laïko", "Rock", "Electrónica/Dance", "Classical"],
    "Sweden": ["Pop", "Hip-Hop/Rap", "Electrónica/Dance", "Rock", "Metal", "Dansband", "Classical"],
    "Norway": ["Pop", "Hip-Hop/Rap", "Metal", "Electrónica/Dance", "Rock", "Dansband", "Classical"],
    "Denmark": ["Pop", "Hip-Hop/Rap", "Electrónica/Dance", "Rock", "Dansband", "Classical"],
    "Finland": ["Pop", "Metal", "Hip-Hop/Rap", "Rock", "Iskelmä", "Electrónica/Dance", "Classical"],
    "Iceland": ["Pop", "Alternative", "Rock", "Hip-Hop/Rap", "Electrónica/Dance", "Classical"],

    # Pequeños estados europeos
    "Luxembourg": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Chanson"],
    "Monaco": ["Pop", "Hip-Hop/Rap", "Chanson", "Electrónica/Dance"],
    "Liechtenstein": ["Pop", "Rock", "Alpine Folk", "Schlager"],
    "Andorra": ["Pop", "Reggaetón/Trap Latino", "Rock", "Flamenco / Copla"],
    "San Marino": ["Pop", "Rock", "Canzone Italiana"],
    "Malta": ["Pop", "Rock", "Hip-Hop/Rap", "Electrónica/Dance"],
    "Cyprus": ["Pop", "Rock", "Hip-Hop/Rap", "Laïko", "Electrónica/Dance"],

    # Europa Oriental y Balcanes
    "Russia": [
        "Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Classical",
        "Folk"
    ],
    "Ukraine": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Folk"],
    "Poland": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Classical"],
    "Czech Republic": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Classical"],
    "Slovakia": ["Pop", "Hip-Hop/Rap", "Rock"],
    "Hungary": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Classical"],
    "Romania": ["Manele", "Pop", "Hip-Hop/Rap", "Electrónica/Dance", "Rock"],
    "Bulgaria": ["Chalga", "Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance"],
    "Serbia": ["Turbo-folk", "Pop", "Hip-Hop/Rap", "Electrónica/Dance", "Rock"],
    "Croatia": ["Pop", "Turbo-folk", "Rock", "Hip-Hop/Rap", "Electrónica/Dance"],
    "Bosnia and Herzegovina": ["Turbo-folk", "Pop", "Rock", "Hip-Hop/Rap"],
    "Montenegro": ["Turbo-folk", "Pop", "Rock"],
    "North Macedonia": ["Turbo-folk", "Pop", "Rock"],
    "Kosovo": ["Tallava", "Pop", "Hip-Hop/Rap", "Turbo-folk", "Rock"],
    "Albania": ["Tallava", "Pop", "Hip-Hop/Rap", "Rock"],
    "Slovenia": ["Pop", "Rock", "Hip-Hop/Rap", "Electrónica/Dance"],
    "Lithuania": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance"],
    "Latvia": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance"],
    "Estonia": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Folk"],
    "Belarus": ["Pop", "Rock", "Hip-Hop/Rap"],
    "Moldova": ["Pop", "Rock", "Hip-Hop/Rap", "Manele"],

    # Oriente Medio y Norte de África
    "Turkey": ["Turkish Pop/Rock", "Pop", "Hip-Hop/Rap", "Rock", "Arabesk", "Classical"],
    "Israel": ["Israeli Pop/Rock", "Pop", "Hip-Hop/Rap", "Rock", "Mizrahi", "Classical"],
    "Lebanon": ["Arabic Pop/Rock", "Pop", "Hip-Hop/Rap"],
    "Syria": ["Arabic Pop/Rock"],
    "Jordan": ["Arabic Pop/Rock", "Pop", "Hip-Hop/Rap"],
    "Iraq": ["Arabic Pop/Rock", "Pop", "Hip-Hop/Rap"],
    "Iran": ["Pop", "Hip-Hop/Rap", "Rock", "Classical Persian"],
    "Egypt": ["Arabic Pop/Rock", "Shaabi", "Hip-Hop/Rap"],
    "Morocco": ["Arabic Pop/Rock", "Gnawa", "Hip-Hop/Rap", "Chaabi"],
    "Algeria": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Raï"],
    "Tunisia": ["Arabic Pop/Rock", "Hip-Hop/Rap"],
    "Libya": ["Arabic Pop/Rock"],
    "Saudi Arabia": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Khaliji"],
    "United Arab Emirates": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Khaliji"],
    "Kuwait": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Khaliji"],
    "Qatar": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Khaliji"],
    "Bahrain": ["Arabic Pop/Rock", "Khaliji"],
    "Oman": ["Arabic Pop/Rock", "Khaliji"],
    "Yemen": ["Arabic Pop/Rock"],

    # África Subsahariana
    "Nigeria": ["Afrobeats", "Hip-Hop/Rap", "Gospel", "Jùjú", "Fuji"],
    "Ghana": ["Afrobeats", "Highlife", "Hip-Hop/Rap", "Gospel"],
    "South Africa": [
        "Amapiano", "Kwaito", "Hip-Hop/Rap", "Afrobeats",
        "Electrónica/Dance", "Maskandi", "Mbaqanga", "Gqom", "Afro-soul"
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
    "Ivory Coast": ["Coupé-Décalé", "Afrobeats", "Zouglou", "Hip-Hop/Rap"],
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
    "Cabo Verde": ["Kizomba/Zouk", "Coladeira", "Funaná", "Morna"],
    "São Tomé and Príncipe": ["Afrobeats", "Kizomba/Zouk"],

    # Asia
    "India": [
        "Indian Pop", "Hip-Hop/Rap", "Bollywood", "Indian Classical",
        "Rock", "Electrónica/Dance"
    ],  # 'Indian Classical' ya cubre la tradición clásica india, no se añade 'Classical'
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
        "J-Pop/J-Rock", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Enka", "City Pop",
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
        "Electrónica/Dance", "Keroncong"
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
        "Bolero Vietnamita", "Folk"
    ],
    "Myanmar": ["Burmese Pop/Rock", "Hip-Hop/Rap"],
    "Cambodia": ["Cambodian Pop/Rock", "Hip-Hop/Rap", "Folk"],
    "Laos": ["Lao Pop/Rock", "Mor Lam", "Hip-Hop/Rap"],
    "Brunei": ["Bruneian Pop/Rock", "Malaysian Pop", "K-Pop/K-Rock"],
    "Timor-Leste": ["Timorese Pop/Rock", "Dancehall/Reggae", "Folk"],

    # Asia Central y Cáucaso
    "Kazakhstan": ["Q-pop/Q-rock", "Pop", "Hip-Hop/Rap", "Folk"],
    "Uzbekistan": ["Pop", "Hip-Hop/Rap", "Folk", "Rock"],
    "Turkmenistan": ["Pop", "Folk"],
    "Kyrgyzstan": ["Pop", "Hip-Hop/Rap", "Folk"],
    "Tajikistan": ["Pop", "Folk"],
    "Azerbaijan": ["Pop", "Hip-Hop/Rap", "Mugham", "Rock"],
    "Georgia": ["Pop", "Hip-Hop/Rap", "Folk", "Rock"],
    "Armenia": ["Pop", "Hip-Hop/Rap", "Folk", "Rock", "Classical"],

    # Oceanía
    "Australia": [
        "Pop", "Hip-Hop/Rap", "Rock", "Alternative",
        "Electrónica/Dance", "Country", "Aboriginal Australian Pop/Rock",
        "Classical"
    ],
    "New Zealand": [
        "Pop", "Hip-Hop/Rap", "Rock", "Alternative",
        "Māori Pop/Rock", "Electrónica/Dance", "Pacific Reggae",
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

# Género por defecto para países sin jerarquía definida
GENERO_POR_DEFECTO = "Pop"

def obtener_continente(pais):
    """Retorna el continente de un país o 'Desconocido' si no está mapeado"""
    return PAIS_A_CONTINENTE.get(pais, "Desconocido")

def generar_genero_por_pais(artistas_info):
    """
    Determina el género basado en jerarquía local cuando hay múltiples géneros
    pero todos los artistas son del mismo país
    """
    if not artistas_info:
        return GENERO_POR_DEFECTO
    
    # Obtener el país (todos deberían ser iguales en este punto)
    pais = artistas_info[0]['pais']
    
    # Obtener la jerarquía para este país
    jerarquia = JERARQUIA_GENEROS.get(pais, [GENERO_POR_DEFECTO])
    
    # Contar frecuencias de géneros conocidos
    generos_conocidos = [a['genero'] for a in artistas_info if a['genero']]
    if not generos_conocidos:
        return jerarquia[0] if jerarquia else GENERO_POR_DEFECTO
    
    # Si hay un género claramente dominante, usarlo
    counter = Counter(generos_conocidos)
    genero_mas_comun = counter.most_common(1)[0][0]
    if counter[genero_mas_comun] > len(generos_conocidos) / 2:
        return genero_mas_comun
    
    # Si no hay dominancia, usar el de mayor jerarquía entre los presentes
    for genero_prioritario in jerarquia:
        if genero_prioritario in generos_conocidos:
            return genero_prioritario
    
    # Si nada coincide, usar el primero de la jerarquía
    return jerarquia[0] if jerarquia else GENERO_POR_DEFECTO

def determinar_pais_y_genero_colaboracion(artistas_info):
    """
    Algoritmo principal de decisión para colaboraciones
    artistas_info: lista de diccionarios [{'pais': x, 'genero': y}, ...]
    Retorna: (pais_resultado, genero_resultado)
    """
    total_artistas = len(artistas_info)
    
    # Caso especial: artista único o todos desconocidos
    if total_artistas == 0:
        return "Desconocido", GENERO_POR_DEFECTO
    
    if total_artistas == 1:
        info = artistas_info[0]
        return info['pais'] or "Desconocido", info['genero'] or GENERO_POR_DEFECTO
    
    # Separar conocidos y desconocidos
    conocidos = [a for a in artistas_info if a['pais'] is not None]
    desconocidos = [a for a in artistas_info if a['pais'] is None]
    
    # Si todos son desconocidos
    if not conocidos:
        return "Desconocido", GENERO_POR_DEFECTO
    
    # Contar países en conocidos
    paises_conocidos = [a['pais'] for a in conocidos]
    contador_paises = Counter(paises_conocidos)
    pais_mayoritario = contador_paises.most_common(1)[0][0]
    cantidad_mayoritaria = contador_paises[pais_mayoritario]
    porcentaje_mayoritario = cantidad_mayoritaria / total_artistas
    
    # Contar continentes
    continentes = [obtener_continente(p) for p in paises_conocidos if p]
    contador_continentes = Counter(continentes)
    cantidad_continentes_distintos = len(contador_continentes)
    
    # Determinar cuántos países distintos hay
    paises_distintos = len(contador_paises)
    
    # --- REGLAS DE DECISIÓN ---
    
    # REGLA 1: Mayoría absoluta (>50%)
    if porcentaje_mayoritario > 0.5:
        # Inferir géneros de desconocidos si comparten país
        artistas_completos = []
        for a in artistas_info:
            if a['pais'] is None:
                # Inferir país del mayoritario
                artistas_completos.append({'pais': pais_mayoritario, 'genero': None})
            else:
                artistas_completos.append(a)
        
        # Determinar género basado en los conocidos de ese país
        artistas_del_pais = [a for a in artistas_completos if a['pais'] == pais_mayoritario]
        genero_final = generar_genero_por_pais(artistas_del_pais)
        
        return pais_mayoritario, genero_final
    
    # REGLA 2: Mayoría exacta (50%)
    if porcentaje_mayoritario == 0.5:
        if paises_distintos == 2:
            # 50% entre 2 países: gana el mayoritario
            artistas_del_pais = [a for a in conocidos if a['pais'] == pais_mayoritario]
            genero_final = generar_genero_por_pais(artistas_del_pais)
            return pais_mayoritario, genero_final
        else:
            # 50% con 3+ países distintos: MULTI
            return "Multipais", "Multigénero"
    
    # REGLA 3: Mayoría relativa (<50%)
    if porcentaje_mayoritario < 0.5:
        # Verificar si todos los conocidos son del mismo continente
        if cantidad_continentes_distintos == 1 and paises_distintos <= 2:
            # Mismo continente y máximo 2 países distintos
            artistas_del_pais = [a for a in conocidos if a['pais'] == pais_mayoritario]
            genero_final = generar_genero_por_pais(artistas_del_pais)
            return pais_mayoritario, genero_final
        else:
            # Diferentes continentes o muchos países
            return "Multipais", "Multigénero"
    
    # Caso por defecto
    return "Multipais", "Multigénero"

# =====================================================================
# FUNCIONES DE DETECCIÓN DE METADATOS
# =====================================================================

def detectar_tipo_video(titulo, descripcion=""):
    """Detecta tipo específico de video musical"""
    texto_completo = f"{titulo.lower()} {descripcion.lower()}"
    titulo_lower = titulo.lower()
    
    es_oficial = any(palabra in texto_completo for palabra in [
        'official', 'oficial', 'video oficial', 'official video',
        'official music video', 'vídeo oficial'
    ])
    
    es_lyric = any(palabra in titulo_lower for palabra in [
        'lyric', 'lyrics', 'letra', 'letras', 'karaoke',
        'lyric video', 'letra oficial'
    ]) or 'lyric' in texto_completo
    
    es_live = any(palabra in texto_completo for palabra in [
        'live', 'en vivo', 'concert', 'performance', 'show',
        'live performance', 'en concierto', 'directo'
    ])
    
    es_remix = any(palabra in titulo_lower for palabra in [
        'remix', 'version', 'edit', 'mix', 'bootleg', 'rework',
        'sped up', 'slowed', 'reverb', 'acoustic', 'acústico',
        'piano version', 'instrumental'
    ])
    
    return {
        'is_official_video': es_oficial,
        'is_lyric_video': es_lyric,
        'is_live_performance': es_live,
        'is_special_version': es_remix
    }

def detectar_colaboracion_artistas(titulo, artistas_csv):
    """Detecta colaboración y cuenta artistas"""
    titulo_lower = titulo.lower()
    
    patrones_colaboracion = [
        r'\sft\.\s', r'\sfeat\.\s', r'\sfeaturing\s', r'\sft\s',
        r'\scon\s', r'\swith\s', r'\s&\s', r'\sx\s', r'\s×\s',
        r'\(feat\.', r'\(ft\.', r'\(with', r'\[feat\.', r'\[ft\.'
    ]
    
    es_colaboracion = False
    for patron in patrones_colaboracion:
        if re.search(patron, titulo_lower, re.IGNORECASE):
            es_colaboracion = True
            break
    
    if artistas_csv:
        artist_count = artistas_csv.count('&') + artistas_csv.count(',') + 1
    else:
        artist_count = 1
        if es_colaboracion:
            artist_count = 2
            artist_count += titulo_lower.count(' & ') + titulo_lower.count(' x ')
    
    return {
        'is_collaboration': es_colaboracion,
        'artist_count': min(artist_count, 10)
    }

def detectar_tipo_canal(channel_title):
    """Detecta tipo de canal"""
    if not channel_title:
        return {'channel_type': 'unknown'}
    
    channel_lower = channel_title.lower()
    
    if 'vevo' in channel_lower:
        return {'channel_type': 'VEVO'}
    elif 'topic' in channel_lower:
        return {'channel_type': 'Topic'}
    elif any(word in channel_lower for word in [
        'records', 'music', 'label', 'entertainment', 'studios',
        'production', 'presents', 'network'
    ]):
        return {'channel_type': 'Label/Studio'}
    elif any(word in channel_lower for word in [
        'official', 'oficial', 'artist', 'band', 'singer',
        'musician', 'rapper', 'dj', 'producer'
    ]):
        return {'channel_type': 'Artist Channel'}
    elif any(word in channel_lower for word in [
        'channel', 'tv', 'hd', 'video', 'videos'
    ]):
        return {'channel_type': 'User Channel'}
    else:
        if ' - ' in channel_title or ' | ' in channel_title:
            return {'channel_type': 'Artist Channel'}
        else:
            return {'channel_type': 'General'}

def obtener_trimestre(mes):
    return f'Q{mes}' if 1 <= mes <= 4 else 'unknown'

def analizar_fecha_trimestre(publish_date):
    if not publish_date or len(publish_date) < 10:
        return {'upload_season': 'unknown'}
    try:
        fecha = datetime.strptime(publish_date[:10], "%Y-%m-%d")
        return {'upload_season': obtener_trimestre((fecha.month-1)//3 + 1)}
    except:
        return {'upload_season': 'unknown'}

def detectar_restricciones_regionales(content_details):
    if not content_details:
        return {'region_restricted': False}
    region_restriction = content_details.get('regionRestriction', {})
    is_restricted = bool(region_restriction.get('blocked') or region_restriction.get('allowed'))
    return {'region_restricted': is_restricted}

# =====================================================================
# FUNCIONES PARA BASE DE DATOS REMOTA
# =====================================================================

def descargar_db(url):
    """Descarga la base de datos desde GitHub a un archivo temporal."""
    print("🌍 Descargando base de datos desde GitHub...")
    try:
        respuesta = requests.get(url, timeout=30)
        respuesta.raise_for_status()
    except Exception as e:
        print(f"❌ Error al descargar DB: {e}")
        sys.exit(1)
    
    archivo_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    archivo_temp.write(respuesta.content)
    archivo_temp.close()
    print(f"✓ Base de datos descargada temporalmente en: {archivo_temp.name}")
    return Path(archivo_temp.name)

def normalizar_nombre(nombre):
    """Limpia y normaliza un nombre para búsqueda (None → cadena vacía)."""
    if nombre is None:
        return ""
    nombre = re.sub(r'\s+', ' ', str(nombre)).strip().lower()
    nombre = re.sub(r'[^\w\s]', '', nombre)
    return nombre

def extraer_lista_artistas(artist_names):
    """Convierte 'A & B feat. C' en lista de nombres limpios (None → lista vacía)."""
    if artist_names is None:
        return []
    texto = artist_names
    for sep in ['&', 'feat.', 'ft.', ',', ' y ', ' and ', ' with ', ' x ', ' vs ']:
        texto = texto.replace(sep, '|')
    return [parte.strip() for parte in texto.split('|') if parte.strip()]

def cargar_db_en_diccionario(ruta_db):
    """Lee la DB y retorna dict: {nombre_normalizado: (país, género)}"""
    conn = sqlite3.connect(ruta_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name, country, macro_genre FROM artist")
    filas = cursor.fetchall()
    conn.close()

    artistas_dict = {}
    for nombre_original, pais, genero in filas:
        key = normalizar_nombre(nombre_original)
        artistas_dict[key] = (pais, genero)
    print(f"✓ Cargados {len(artistas_dict)} artistas desde la DB remota.")
    return artistas_dict

def obtener_info_artistas(artist_names, artistas_dict):
    """
    Versión mejorada: retorna lista de diccionarios con info de cada artista
    """
    lista = extraer_lista_artistas(artist_names)
    if not lista:
        return []
    
    artistas_info = []
    for nombre in lista:
        key = normalizar_nombre(nombre)
        pais, genero = artistas_dict.get(key, (None, None))
        artistas_info.append({
            'nombre': nombre,
            'pais': pais,
            'genero': genero
        })
    
    return artistas_info

# =====================================================================
# FUNCIÓN PRINCIPAL DE OBTENCIÓN DE METADATOS
# =====================================================================

def obtener_metadatos_especificos(url, artistas_csv="", api_key=None):
    """Obtiene los metadatos específicos"""
    metadatos = {
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
    
    error_msgs = []
    
    # yt-dlp
    try:
        import yt_dlp
        ydl_opts = {'quiet': True, 'skip_download': True, 'ignoreerrors': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                duracion = info.get('duration', 0)
                fecha_raw = info.get('upload_date', '')
                if fecha_raw and len(fecha_raw) == 8:
                    fecha = f"{fecha_raw[:4]}-{fecha_raw[4:6]}-{fecha_raw[6:8]}"
                    trimestre_info = analizar_fecha_trimestre(fecha)
                    metadatos.update(trimestre_info)
                    metadatos['upload_date'] = fecha
                likes = info.get('like_count', 0)
                titulo = info.get('title', '')
                descripcion = info.get('description', '')
                channel_title = info.get('channel', '')
                
                metadatos.update({
                    'Duration (s)': duracion,
                    'duration (m:s)': f"{duracion//60}:{duracion%60:02d}",
                    'likes': likes,
                })
                metadatos.update(detectar_tipo_video(titulo, descripcion))
                metadatos.update(detectar_tipo_canal(channel_title))
                metadatos.update(detectar_colaboracion_artistas(titulo, artistas_csv))
                yt_dlp_success = True
            else:
                yt_dlp_success = False
                error_msgs.append("No se pudo obtener info (yt-dlp)")
    except Exception as e:
        yt_dlp_success = False
        error_msgs.append(f"Error yt-dlp: {str(e)[:30]}")
    
    # YouTube API (si hay key)
    if api_key and api_key != "insertar_api":
        try:
            from googleapiclient.discovery import build
            video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
            if video_id_match:
                video_id = video_id_match.group(1)
                youtube = build('youtube', 'v3', developerKey=api_key)
                request = youtube.videos().list(
                    part='snippet,contentDetails,statistics',
                    id=video_id
                )
                response = request.execute()
                if response.get('items'):
                    video = response['items'][0]
                    snippet = video.get('snippet', {})
                    statistics = video.get('statistics', {})
                    content_details = video.get('contentDetails', {})
                    
                    metadatos['comment_count'] = int(statistics.get('commentCount', 0))
                    idioma = snippet.get('defaultAudioLanguage', '')
                    metadatos['audio_language'] = idioma[:2].upper() if idioma else ""
                    metadatos.update(detectar_restricciones_regionales(content_details))
                    
                    if not yt_dlp_success:
                        titulo_api = snippet.get('title', '')
                        descripcion_api = snippet.get('description', '')
                        channel_api = snippet.get('channelTitle', '')
                        metadatos.update(detectar_tipo_video(titulo_api, descripcion_api))
                        metadatos.update(detectar_tipo_canal(channel_api))
                        metadatos.update(detectar_colaboracion_artistas(titulo_api, artistas_csv))
                        fecha_api = snippet.get('publishedAt', '')[:10]
                        if fecha_api:
                            metadatos['upload_date'] = fecha_api
                            metadatos.update(analizar_fecha_trimestre(fecha_api))
        except Exception as e:
            error_msgs.append(f"Error API: {str(e)[:30]}")
    
    if error_msgs:
        metadatos['error'] = " | ".join(error_msgs)
    
    return metadatos

# =====================================================================
# FUNCIONES PARA BASE DE DATOS SQLITE DE SALIDA
# =====================================================================

def crear_tabla_resultados(conn):
    """Crea la tabla de resultados en la base de datos SQLite"""
    cursor = conn.cursor()
    
    # Crear tabla
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS canciones_enriquecidas (
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
            error TEXT,
            artist_country TEXT,
            macro_genre TEXT,
            artistas_encontrados TEXT,
            label TEXT,
            fecha_procesamiento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Crear índices para búsquedas rápidas
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pais ON canciones_enriquecidas(artist_country)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_genero ON canciones_enriquecidas(macro_genre)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_fecha ON canciones_enriquecidas(upload_date)')
    
    conn.commit()

def guardar_en_sqlite(conn, fila):
    """Guarda una fila en la base de datos SQLite"""
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO canciones_enriquecidas (
            rank, artist_names, track_name, periods_on_chart, views, youtube_url,
            duration_s, duration_ms, upload_date, likes, comment_count,
            audio_language, is_official_video, is_lyric_video, is_live_performance,
            upload_season, channel_type, is_collaboration, artist_count,
            region_restricted, error, artist_country, macro_genre,
            artistas_encontrados, label
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        fila['Rank'], fila['Artist Names'], fila['Track Name'], 
        fila['Periods on Chart'], fila['Views'], fila['YouTube URL'],
        fila['Duration (s)'], fila['duration (m:s)'], fila['upload_date'],
        fila['likes'], fila['comment_count'], fila['audio_language'],
        fila['is_official_video'], fila['is_lyric_video'], fila['is_live_performance'],
        fila['upload_season'], fila['channel_type'], fila['is_collaboration'],
        fila['artist_count'], fila['region_restricted'], fila['error'],
        fila['Artist_Country'], fila['macro_genre'], fila['artistas_encontrados'],
        fila['Label']
    ))
    
    conn.commit()

# =====================================================================
# FUNCIÓN PRINCIPAL
# =====================================================================

def main():
    print("="*80)
    print("🎵 ENRIQUECIMIENTO CON SISTEMA DE PESOS (salida a SQLite)")
    print("="*80)
    print(f"📁 Directorio de salida: {DB_OUTPUT_DIR}")
    print(f"💾 Base de datos: {DB_OUTPUT_PATH.name}\n")
    
    # 1. Descargar y cargar base de datos remota
    ruta_db_temp = descargar_db(URL_DB)
    artistas_dict = cargar_db_en_diccionario(ruta_db_temp)
    
    # 2. Verificar archivo CSV
    if not INPUT_CSV.exists():
        print(f"\n❌ No se encuentra: {INPUT_CSV.name}")
        return
    
    # 3. Instalar/verificar dependencias
    try:
        import yt_dlp
        print("✅ yt-dlp disponible")
    except ImportError:
        print("Instalando yt-dlp...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
        import yt_dlp
        print("✅ yt-dlp instalado")
    
    # 4. Leer CSV
    print(f"\n📖 Leyendo canciones de: {INPUT_CSV.name}")
    try:
        with open(INPUT_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            canciones = list(reader)
        print(f"✅ {len(canciones)} canciones cargadas\n")
    except Exception as e:
        print(f"❌ Error leyendo CSV: {e}")
        return
    
    # 5. Conectar a base de datos SQLite de salida
    conn = sqlite3.connect(DB_OUTPUT_PATH)
    crear_tabla_resultados(conn)
    
    # 6. Procesar cada canción
    print("🎬 Procesando y extrayendo metadatos...")
    resultados = []
    
    for i, cancion in enumerate(canciones, 1):
        url = cancion['YouTube URL']
        track = cancion['Track Name'][:30]
        artistas_csv = cancion.get('Artist Names', '')
        
        print(f"[{i:2d}/{len(canciones)}] {track:30}... ", end='', flush=True)
        
        # Obtener metadatos específicos
        metadatos = obtener_metadatos_especificos(url, artistas_csv, API_KEY)
        
        # Obtener información de artistas desde la DB
        artistas_info = obtener_info_artistas(artistas_csv, artistas_dict)
        
        # Aplicar algoritmo de decisión
        pais_final, genero_final = determinar_pais_y_genero_colaboracion(artistas_info)
        
        # Mostrar info de artistas encontrados
        encontrados = sum(1 for a in artistas_info if a['pais'] is not None)
        total_arts = len(artistas_info) if artistas_info else 1
        
        # Combinar todo en una fila
        fila = {
            'Rank': cancion['Rank'],
            'Artist Names': artistas_csv,
            'Track Name': cancion['Track Name'],
            'Periods on Chart': cancion['Periods on Chart'],
            'Views': cancion['Views'],
            'YouTube URL': url,
            'Duration (s)': metadatos['Duration (s)'],
            'duration (m:s)': metadatos['duration (m:s)'],
            'upload_date': metadatos['upload_date'],
            'likes': metadatos['likes'],
            'comment_count': metadatos['comment_count'],
            'audio_language': metadatos['audio_language'],
            'is_official_video': metadatos['is_official_video'],
            'is_lyric_video': metadatos['is_lyric_video'],
            'is_live_performance': metadatos['is_live_performance'],
            'upload_season': metadatos['upload_season'],
            'channel_type': metadatos['channel_type'],
            'is_collaboration': metadatos['is_collaboration'],
            'artist_count': metadatos['artist_count'],
            'region_restricted': metadatos['region_restricted'],
            'error': metadatos['error'],
            'Artist_Country': pais_final,
            'macro_genre': genero_final,
            'artistas_encontrados': f"{encontrados}/{total_arts}",
            'Label': None
        }
        
        # Guardar en SQLite
        guardar_en_sqlite(conn, fila)
        
        # Mostrar resumen
        iconos = []
        if metadatos['Duration (s)'] > 0:
            iconos.append(f"⏱️{metadatos['duration (m:s)']}")
        if metadatos['is_official_video']:
            iconos.append("📀")
        if metadatos['is_lyric_video']:
            iconos.append("📝")
        if metadatos['is_live_performance']:
            iconos.append("🎤")
        if metadatos['is_collaboration']:
            iconos.append(f"👥{metadatos['artist_count']}")
        if pais_final not in ["Desconocido", "Multipais"]:
            iconos.append(f"🌍{pais_final[:2]}")
        elif pais_final == "Multipais":
            iconos.append("🌐")
        
        if encontrados < total_arts:
            iconos.append(f"⚠️{encontrados}/{total_arts}")
        
        if iconos:
            print(f"({' '.join(iconos)}) → {pais_final[:15]}, {genero_final[:15]}")
        else:
            error_display = metadatos['error'][:20] if metadatos['error'] else "Sin datos"
            print(f"({error_display})")
        
        time.sleep(0.1)
    
    # 7. Cerrar conexión a base de datos
    conn.close()
    
    # 8. Mostrar estadísticas finales
    print(f"\n💾 Base de datos guardada en: {DB_OUTPUT_PATH}")
    
    # Conectar para leer estadísticas
    conn = sqlite3.connect(DB_OUTPUT_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM canciones_enriquecidas")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM canciones_enriquecidas WHERE artist_country = 'Multipais'")
    multi_pais = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT artist_country) FROM canciones_enriquecidas WHERE artist_country NOT IN ('Desconocido', 'Multipais')")
    paises_unicos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT macro_genre) FROM canciones_enriquecidas WHERE macro_genre != 'Multigénero' AND macro_genre IS NOT NULL")
    generos_unicos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM canciones_enriquecidas WHERE artist_country = 'Desconocido'")
    desconocidos = cursor.fetchone()[0]
    
    conn.close()
    
    print("\n📊 ESTADÍSTICAS FINALES")
    print(f"   • Total canciones: {total}")
    print(f"   • Colaboraciones multi-país: {multi_pais} ({multi_pais/total*100:.1f}%)")
    print(f"   • Países distintos detectados: {paises_unicos}")
    print(f"   • Géneros distintos: {generos_unicos}")
    print(f"   • Canciones sin país: {desconocidos} ({desconocidos/total*100:.1f}%)")
    
    # 9. Limpiar archivo temporal
    os.unlink(ruta_db_temp)
    print("\n🧹 Archivo temporal eliminado.")
    
    print("\n✅ PROCESO COMPLETADO")

if __name__ == "__main__":
    # Verificar API Key
    if API_KEY == "insertar_api":
        print("\n⚠️  NOTA SOBRE API KEY:")
        print("="*70)
        print("Para obtener comentarios, idioma y restricciones regionales,")
        print("necesitas una API Key de YouTube.")
        print("\nEl script funcionará sin API, pero obtendrá:")
        print("✓ Duración, fecha, likes (con yt-dlp)")
        print("✓ Metadatos específicos (con yt-dlp)")
        print("✓ País y género desde DB remota (CON SISTEMA DE PESOS)")
        print("✗ NO obtendrá: comentarios, idioma, restricciones")
        print("="*70)
    
    respuesta = input("\n¿Continuar con el procesamiento? (s/n): ").lower()
    if respuesta in ['s', 'si', 'y', 'yes']:
        main()
    else:
        print("Proceso cancelado.")
