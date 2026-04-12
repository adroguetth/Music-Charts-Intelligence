"""
Country-specific genre priorities and rule configurations.

COUNTRY_GENRE_PRIORITY: Ordered list of most likely macro-genres per country.
COUNTRY_SPECIFIC_RULES: Additional rules (keywords, bonuses, forced mappings).
DEFAULT_GENRE_PRIORITY: Fallback priority when country is unknown.
"""

from typing import Dict, List, Set, Any

# Ordered list of macro-genres by likelihood for each country
# Used as tie-breaker in genre voting and as fallback when no data is found.
COUNTRY_GENRE_PRIORITY: Dict[str, List[str]] = {
    # North America
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

    # Central America
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

    # Caribbean
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

    # South America
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
        "Pop", "Rock", "Hip-Hop/Rap", "Folklore/Raíces",
        "Classical"
    ],

    # Western Europe
    "Spain": [
        "Reggaetón/Trap Latino", "Pop", "Hip-Hop/Rap",
        "Flamenco / Copla", "Rock", "Electrónica/Dance",
        "Classical"
    ],
    "Portugal": [
        "Pop", "Hip-Hop/Rap", "Folklore/Raíces",
        "Kizomba/Zouk", "Reggaetón/Trap Latino", "Rock",
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

    # Eastern Europe and Balkans
    "Russia": [
        "Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Classical",
        "Folklore/Raíces"
    ],
    "Ukraine": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Folklore/Raíces"],
    "Poland": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Classical"],
    "Czech Republic": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Classical"],
    "Slovakia": ["Pop", "Hip-Hop/Rap", "Rock"],
    "Hungary": ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Classical"],
    "Romania": ["Manele", "Pop", "Hip-Hop/Rap", "Electrónica/Dance", "Rock"],
    "Bulgaria": ["Chalga", "Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance"],
    "Serbia": ["Turbo-folk", "Pop", "Hip-Hop/Rap", "Electrónica/Dance", "Rock"],
    "Croatia": ["Pop", "Turbo-folk", "Rock", "Hip-Hop/Rap", "Electrónica/Dance"],
    "Bosnia and Herzegovina": ["Turbo-folk", "Pop", "Rock", "Hip-Hop/Rap"],
    "North Macedonia": ["Turbo-folk", "Pop", "Rock"],
    "Kosovo": ["Tallava", "Pop", "Hip-Hop/Rap", "Turbo-folk", "Rock"],
    "Albania": ["Tallava", "Pop", "Hip-Hop/Rap", "Rock"],
    "Slovenia": ["Pop", "Rock", "Hip-Hop/Rap", "Electrónica/Dance"],

    # Middle East and North Africa
    "Turkey": ["Turkish Pop/Rock", "Pop", "Hip-Hop/Rap", "Rock", "Arabesk", "Classical"],
    "Israel": ["Israeli Pop/Rock", "Pop", "Hip-Hop/Rap", "Rock", "Mizrahi", "Classical"],
    "Lebanon": ["Arabic Pop/Rock", "Pop", "Hip-Hop/Rap"],
    "Egypt": ["Arabic Pop/Rock", "Shaabi", "Hip-Hop/Rap"],
    "Morocco": ["Arabic Pop/Rock", "Gnawa", "Hip-Hop/Rap"],
    "Algeria": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Raï"],
    "Tunisia": ["Arabic Pop/Rock", "Hip-Hop/Rap"],
    "Saudi Arabia": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Khaliji"],
    "United Arab Emirates": ["Arabic Pop/Rock", "Hip-Hop/Rap", "Khaliji"],

    # Sub-Saharan Africa
    "Nigeria": ["Afrobeats", "Hip-Hop/Rap", "Jùjú", "Fuji"],
    "Ghana": ["Afrobeats", "Highlife", "Hip-Hop/Rap"],
    "South Africa": [
        "Amapiano", "Kwaito", "Hip-Hop/Rap", "Afrobeats",
        "Electrónica/Dance", "Maskandi", "Mbaqanga", "Afro-soul"
    ],
    "Tanzania": ["Bongo Flava", "Taarab", "Afrobeats", "Hip-Hop/Rap"],
    "Kenya": ["Afrobeats", "Gengetone", "Kapuka", "Benga", "Hip-Hop/Rap"],
    "Zimbabwe": ["Zim Dancehall", "Afrobeats", "Amapiano"],
    "Angola": ["Kuduro", "Kizomba/Zouk", "Afrobeats"],
    "Ethiopia": ["Ethio-jazz", "Pop", "Hip-Hop/Rap"],
    "Senegal": ["Mbalax", "Afrobeats", "Hip-Hop/Rap"],
    "Ivory Coast": ["Coupé-Décalé", "Afrobeats", "Hip-Hop/Rap"],
    "Democratic Republic of Congo": ["Soukous/Ndombolo", "Afrobeats"],

    # Asia
    "India": [
        "Indian Pop", "Hip-Hop/Rap", "Folklore/Raíces",
        "Rock", "Electrónica/Dance"
    ],
    "Pakistan": ["Pakistani Pop", "Hip-Hop/Rap", "Rock"],
    "Bangladesh": ["Bangladeshi Pop/Rock", "Hip-Hop/Rap"],
    "Sri Lanka": ["Sri Lankan Pop/Rock", "Hip-Hop/Rap"],
    "Nepal": ["Nepali Pop/Rock", "Hip-Hop/Rap"],
    "Bhutan": ["Bhutanese Pop/Rock"],
    "Maldives": ["Maldivian Pop/Rock"],
    "South Korea": [
        "K-Pop/K-Rock", "Hip-Hop/Rap", "Rock", "Classical"
    ],
    "Japan": [
        "J-Pop/J-Rock", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Classical"
    ],
    "China": [
        "C-Pop/C-Rock", "Hip-Hop/Rap", "Rock", "Classical"
    ],
    "Taiwan": ["TW-Pop/TW-Rock", "Hip-Hop/Rap", "Rock", "Classical"],
    "Hong Kong": ["HK-Pop/HK-Rock", "Hip-Hop/Rap", "Classical"],
    "Mongolia": ["Mongolian Pop/Rock/Metal", "Hip-Hop/Rap"],
    "Indonesia": [
        "Indonesian Pop/Dangdut", "Rock", "Hip-Hop/Rap", "Electrónica/Dance"
    ],
    "Malaysia": [
        "Malaysian Pop", "Indonesian Pop/Dangdut", "K-Pop/K-Rock", "Hip-Hop/Rap"
    ],
    "Singapore": [
        "Singaporean Pop", "K-Pop/K-Rock", "C-Pop/C-Rock", "Hip-Hop/Rap"
    ],
    "Philippines": [
        "OPM", "K-Pop/K-Rock", "Pop", "Rock", "Hip-Hop/Rap"
    ],
    "Thailand": [
        "T-Pop/T-Rock", "K-Pop/K-Rock", "Hip-Hop/Rap"
    ],
    "Vietnam": [
        "V-Pop/V-Rock", "K-Pop/K-Rock", "Hip-Hop/Rap"
    ],
    "Myanmar": ["Burmese Pop/Rock", "Hip-Hop/Rap"],
    "Cambodia": ["Cambodian Pop/Rock", "Hip-Hop/Rap"],
    "Laos": ["Lao Pop/Rock", "Hip-Hop/Rap"],

    # Central Asia
    "Kazakhstan": ["Q-pop/Q-rock", "Pop", "Hip-Hop/Rap"],
    "Uzbekistan": ["Pop", "Hip-Hop/Rap"],

    # Oceania
    "Australia": [
        "Pop", "Hip-Hop/Rap", "Rock", "Alternative",
        "Electrónica/Dance", "Country", "Aboriginal Australian Pop/Rock",
        "Classical"
    ],
    "New Zealand": [
        "Pop", "Hip-Hop/Rap", "Rock", "Alternative",
        "Māori Pop/Rock", "Electrónica/Dance", "Classical"
    ],
    "Papua New Guinea": ["PNG Pop/Rock", "Dancehall/Reggae"],
    "Fiji": ["Pasifika Pop/Rock", "Dancehall/Reggae"],
    "Hawaii": ["Hawaiian Pop/Rock", "Pop", "Dancehall/Reggae"],
}

# Country-specific rules for genre detection adjustments
COUNTRY_SPECIFIC_RULES: Dict[str, Dict[str, Any]] = {
    "Puerto Rico": {
        "keywords": ["reggaeton", "reggaetón", "trap latino", "urbano", "dembow", "perreo", "neoperreo", "rap", "hip hop"],
        "bonus_extra": 2.0,
        "force_macro": "Reggaetón/Trap Latino"
    },
    "South Korea": {
        "keywords": ["k-pop", "kpop", "korean pop", "k-rap", "k-r&b", "korean hip hop", "korean rock", "idol group"],
        "bonus_extra": 1.5,
        "force_macro": "K-Pop/K-Rock",
        "map_generic_to": "K-Pop/K-Rock"
    },
    "Colombia": {
        "keywords": ["reggaeton", "reggaetón", "vallenato", "cumbia"],
        "bonus_extra": 1.3
    },
    "Brazil": {
        "keywords": ["sertanejo", "funk brasileiro", "funk carioca", "brazilian funk", "funk", "axe", "forro", "mpb"],
        "bonus_extra": 1.5
    },
    "Jamaica": {
        "keywords": ["dancehall", "reggae", "roots reggae", "dub"],
        "bonus_extra": 1.5
    },
    "India": {
        "keywords": ["indian", "bollywood", "punjabi", "bhangra", "filmi", "hindustani", "carnatic", "ghazal", "qawwali", "sufi"],
        "bonus_extra": 1.5
    },
    "Pakistan": {
        "keywords": ["pakistani pop", "urdu", "lollywood", "indian", "bollywood"],
        "bonus_extra": 1.5,
        "prefer_genre": "Pakistani Pop"
    },
    "Bangladesh": {
        "keywords": ["bangladeshi pop", "bengali", "indian"],
        "bonus_extra": 1.5,
        "prefer_genre": "Bangladeshi Pop/Rock"
    },
    "Mexico": {
        "keywords": ["regional mexicano", "banda", "norteño", "corridos", "mariachi", "ranchera"],
        "bonus_extra": 1.3
    },
    "Spain": {
        "keywords": ["reggaeton", "reggaetón", "trap latino", "flamenco", "rumba"],
        "bonus_extra": 1.3
    },
    "United Kingdom": {
        "keywords": ["uk drill", "grime", "britpop", "uk garage"],
        "bonus_extra": 1.3
    },
    "France": {
        "keywords": ["rap français", "french rap", "variété française"],
        "bonus_extra": 1.3
    },
    "Nigeria": {
        "keywords": ["afrobeats", "naija", "afro pop"],
        "bonus_extra": 1.5
    },
    "South Africa": {
        "keywords": ["amapiano", "south african house"],
        "bonus_extra": 1.5
    },
    "Japan": {
        "keywords": ["j-pop", "jpop", "japanese pop", "j-rock", "japanese rock", "anime", "city pop"],
        "bonus_extra": 1.5,
        "force_macro": "J-Pop/J-Rock",
        "map_generic_to": "J-Pop/J-Rock"
    },
    "China": {
        "keywords": ["c-pop", "cpop", "chinese pop", "mandopop", "chinese rock", "c-rock"],
        "bonus_extra": 1.5,
        "force_macro": "C-Pop/C-Rock",
        "map_generic_to": "C-Pop/C-Rock"
    },
    "Taiwan": {
        "keywords": ["taiwanese pop", "t-pop", "taiwanese rock"],
        "bonus_extra": 1.5,
        "force_macro": "TW-Pop/TW-Rock",
        "map_generic_to": "TW-Pop/TW-Rock"
    },
    "Hong Kong": {
        "keywords": ["cantopop", "hong kong pop", "hk-pop", "canto-pop"],
        "bonus_extra": 1.5,
        "force_macro": "HK-Pop/HK-Rock",
        "map_generic_to": "HK-Pop/HK-Rock"
    },
    "Thailand": {
        "keywords": ["t-pop", "thai pop", "thai rock", "luk thung", "mor lam"],
        "bonus_extra": 1.5,
        "force_macro": "T-Pop/T-Rock",
        "map_generic_to": "T-Pop/T-Rock"
    },
    "Vietnam": {
        "keywords": ["v-pop", "vpop", "vietnamese pop", "vietnamese rock"],
        "bonus_extra": 1.5,
        "force_macro": "V-Pop/V-Rock",
        "map_generic_to": "V-Pop/V-Rock"
    },
    "Philippines": {
        "keywords": ["opm", "pinoy pop", "filipino pop", "pinoy rock"],
        "bonus_extra": 1.5,
        "force_macro": "OPM",
        "map_generic_to": "OPM"
    },
    "Indonesia": {
        "keywords": ["indonesian pop", "dangdut", "indo-pop"],
        "bonus_extra": 1.5,
        "force_macro": "Indonesian Pop/Dangdut",
        "map_generic_to": "Indonesian Pop/Dangdut"
    },
    "Malaysia": {
        "keywords": ["malaysian pop", "m-pop", "malay pop"],
        "bonus_extra": 1.5,
        "force_macro": "Malaysian Pop",
        "map_generic_to": "Malaysian Pop"
    },
    "Singapore": {
        "keywords": ["singaporean pop", "sg pop", "xinyao"],
        "bonus_extra": 1.5,
        "force_macro": "Singaporean Pop",
        "map_generic_to": "Singaporean Pop"
    },
    "Turkey": {
        "keywords": ["turkish pop", "turkish rock", "türkçe pop", "arabesk"],
        "bonus_extra": 1.5,
        "force_macro": "Turkish Pop/Rock",
        "map_generic_to": "Turkish Pop/Rock"
    },
    "Egypt": {
        "keywords": ["egyptian pop", "arabic pop", "shaabi"],
        "bonus_extra": 1.5,
        "force_macro": "Arabic Pop/Rock",
        "map_generic_to": "Arabic Pop/Rock"
    },
    "Israel": {
        "keywords": ["israeli pop", "mizrahi"],
        "bonus_extra": 1.5,
        "force_macro": "Israeli Pop/Rock",
        "map_generic_to": "Israeli Pop/Rock"
    },
    "Kazakhstan": {
        "keywords": ["q-pop", "kazakh pop"],
        "bonus_extra": 1.5,
        "force_macro": "Q-pop/Q-rock",
        "map_generic_to": "Q-pop/Q-rock"
    },
    "Nepal": {
        "keywords": ["nepali pop", "nepop"],
        "bonus_extra": 1.5,
        "force_macro": "Nepali Pop/Rock",
        "map_generic_to": "Nepali Pop/Rock"
    },
    "Mongolia": {
        "keywords": ["mongolian pop", "mongolian rock", "mongolian metal"],
        "bonus_extra": 1.5,
        "force_macro": "Mongolian Pop/Rock/Metal",
        "map_generic_to": "Mongolian Pop/Rock/Metal"
    },
    "Afghanistan": {
        "keywords": ["afghan pop", "afghani pop"],
        "bonus_extra": 1.5,
        "force_macro": "Afghan Pop/Rock",
        "map_generic_to": "Afghan Pop/Rock"
    },
    "Sri Lanka": {
        "keywords": ["sri lankan pop", "baila"],
        "bonus_extra": 1.5,
        "force_macro": "Sri Lankan Pop/Rock",
        "map_generic_to": "Sri Lankan Pop/Rock"
    },
    "Myanmar": {
        "keywords": ["burmese pop", "myanmar pop"],
        "bonus_extra": 1.5,
        "force_macro": "Burmese Pop/Rock",
        "map_generic_to": "Burmese Pop/Rock"
    },
    "Laos": {
        "keywords": ["lao pop", "mor lam"],
        "bonus_extra": 1.5,
        "force_macro": "Lao Pop/Rock",
        "map_generic_to": "Lao Pop/Rock"
    },
    "Cambodia": {
        "keywords": ["cambodian pop", "khmer pop", "khmer rock"],
        "bonus_extra": 1.5,
        "force_macro": "Cambodian Pop/Rock",
        "map_generic_to": "Cambodian Pop/Rock"
    },
    "Bhutan": {
        "keywords": ["bhutanese pop", "rigsar"],
        "bonus_extra": 1.5,
        "force_macro": "Bhutanese Pop/Rock",
        "map_generic_to": "Bhutanese Pop/Rock"
    },
    "Maldives": {
        "keywords": ["maldivian pop", "dhivehi pop"],
        "bonus_extra": 1.5,
        "force_macro": "Maldivian Pop/Rock",
        "map_generic_to": "Maldivian Pop/Rock"
    },
    "Papua New Guinea": {
        "keywords": ["png pop", "papua new guinea pop"],
        "bonus_extra": 1.5,
        "force_macro": "PNG Pop/Rock",
        "map_generic_to": "PNG Pop/Rock"
    },
    "Fiji": {
        "keywords": ["fiji pop", "fijian pop"],
        "bonus_extra": 1.5,
        "force_macro": "Pasifika Pop/Rock",
        "map_generic_to": "Pasifika Pop/Rock"
    },
    "Samoa": {
        "keywords": ["samoan pop"],
        "bonus_extra": 1.5,
        "force_macro": "Pasifika Pop/Rock",
        "map_generic_to": "Pasifika Pop/Rock"
    },
    "Tonga": {
        "keywords": ["tongan pop"],
        "bonus_extra": 1.5,
        "force_macro": "Pasifika Pop/Rock",
        "map_generic_to": "Pasifika Pop/Rock"
    },
    "New Zealand": {
        "keywords": ["maori pop", "māori pop", "aotearoa pop", "waiata"],
        "bonus_extra": 1.5,
        "force_macro": "Māori Pop/Rock",
        "map_generic_to": "Māori Pop/Rock"
    },
    "Hawaii": {
        "keywords": ["hawaiian pop", "jawaiian", "hawaiian reggae"],
        "bonus_extra": 1.5,
        "force_macro": "Hawaiian Pop/Rock",
        "map_generic_to": "Hawaiian Pop/Rock"
    },
    "Australia": {
        "keywords": ["indigenous australian pop", "aboriginal pop"],
        "bonus_extra": 1.5,
        "force_macro": "Aboriginal Australian Pop/Rock",
        "map_generic_to": "Aboriginal Australian Pop/Rock"
    },
}

# Default priority when country is unknown
DEFAULT_GENRE_PRIORITY: List[str] = ["Pop", "Hip-Hop/Rap", "Rock", "Electrónica/Dance", "Alternative"]
