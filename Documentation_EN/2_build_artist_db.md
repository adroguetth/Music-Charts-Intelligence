# 🎵 Artist Country + Genre Detection System: Enriquecimiento Inteligente

![MIT](https://img.shields.io/badge/License-MIT-green) ![Data Enrichment](https://img.shields.io/badge/Data-Enrichment-blue) [![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)](#) [![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=fff)](#) ![Requests](https://img.shields.io/badge/Requests-FF6F61?logo=python&logoColor=fff) [![SQLite](https://img.shields.io/badge/SQLite-%2307405e.svg?logo=sqlite&logoColor=white)](#) ![musicbrainz](https://img.shields.io/badge/MusicBrainz-BA478F?logo=musicbrainz&logoColor=white) ![Wikipedia](https://img.shields.io/badge/Wikipedia-000000?logo=wikipedia&logoColor=white)



## 📋 General Description

This project is the second component of the YouTube Charts intelligence system. It takes the raw artist names extracted by the downloader and **enriches them with geographic and genre metadata** by querying multiple open knowledge bases. The result is a structured database of artists with their country of origin and primary music genre.

### Key Features

- **Multi-Source Lookup**: Intelligent cascading queries to MusicBrainz, Wikipedia (summary & infobox), and Wikidata
- **Smart Name Variation**: Generates up to 15 variations per artist (accents removed, prefixes stripped, etc.)
- **Geographic Intelligence**: Country detection from cities, demonyms, and regional references using a curated dictionary of 30,000+ terms
- **Genre Classification**: 200+ macro-genres and 5,000+ subgenre mappings with weighted voting system
- **Country-Specific Rules**: Special handling for 50+ countries (e.g., K-Pop for South Korea, Sertanejo for Brazil)
- **Script Detection**: Automatic language detection for non-Latin scripts (Cyrillic, Devanagari, Arabic, etc.)
- **Intelligent Updates**: Only fills missing data, never overwrites existing correct information

## 📊 Process Flow Diagram

pendiente

## 🔍 Detailed Analysis of `2_build_artist_db.py`

### Code Structure

#### **1. Configuration and Paths**

```python
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
CHARTS_DB_DIR = PROJECT_ROOT / "charts_archive" / "1_download-chart" / "databases"
ARTIST_DB_PATH = PROJECT_ROOT / "charts_archive" / "2_artist_countries_genres" / "artist_countries_genres.db"
```

The script reads from the downloader's output and creates its own enriched database:

- Input: Weekly chart databases from step 1 (youtube_charts_YYYY-WXX.db)

- Output: Artist metadata database (artist_countries_genres.db)

- Structure: charts_archive/2_artist_countries_genres/

#### **2. Intelligent Name Variation System**

```python
def generate_all_variations(name: str) -> List[str]:
    """
    Generates up to 15 variations of an artist name:
    - Original
    - Without accents
    - Without dots
    - Without hyphens
    - Without prefixes (DJ, MC, Lil, The, etc.)
    - Combinations of the above
    """
```

**Example for "Lil Wayne":**

```python
Lil Wayne
Wayne
Lil Wayne
Lil Wayne
Wayne
... (up to 15 variations)
```

**Prefix dictionary includes:**

```python
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
```

#### **3. Geographic Intelligence System**

The heart of country detection is the `COUNTRIES_CANONICAL` dictionary, a curated knowledge base with **30,000+ terms** mapping to 200+ countries.

**Structure example for United States:**

```python
'United States': {
    # Country names
    'united states', 'usa', 'us', 'u.s.', 'u.s.a.', 'america',
    'estados unidos', 'ee.uu.', 'eeuu', 'estadosunidos',
    # Demonyms
    'american', 'americano', 'americanos', 'estadounidense', 'estadounidenses',
    # Cities — All 50 states covered
    'new york', 'nyc', 'brooklyn', 'los angeles', 'la', 'chicago',
    'houston', 'phoenix', 'philadelphia', 'san antonio', 'san diego',
    'dallas', 'austin', 'miami', 'atlanta', 'boston', ... (500+ cities)
}
```

**Detection process:**

1. **Direct match**: "canadian" → Canada
2. **City mention**: "from Toronto" → Canada
3. **Regional reference**: "born in Brooklyn" → United States
4. **Demonym**: "argentine singer" → Argentina

#### **4. Genre Classification Ontology**

The `GENRE_MAPPINGS` dictionary contains **5,000+ genre variants** mapped to 200+ macro-genres.

**Example mapping for Electronic music:**

```python
# House variants
'house': ('Electrónica/Dance', 'house'),
'deep house': ('Electrónica/Dance', 'deep house'),
'progressive house': ('Electrónica/Dance', 'progressive house'),
'tech house': ('Electrónica/Dance', 'tech house'),
'tropical house': ('Electrónica/Dance', 'tropical house'),

# Techno variants
'techno': ('Electrónica/Dance', 'techno'),
'detroit techno': ('Electrónica/Dance', 'detroit techno'),
'minimal techno': ('Electrónica/Dance', 'minimal techno'),

# Trance variants
'trance': ('Electrónica/Dance', 'trance'),
'psytrance': ('Electrónica/Dance', 'psytrance'),
'goa trance': ('Electrónica/Dance', 'goa trance'),
```

**Macro-genre categories (200+):**

- Global: `Pop`, `Rock`, `Hip-Hop/Rap`, `R&B/Soul`, `Electrónica/Dance`
- Regional: `K-Pop/K-Rock`, `J-Pop/J-Rock`, `C-Pop/C-Rock`, `Reggaetón/Trap Latino`
- Traditional: `Flamenco / Copla`, `Sertanejo`, `Funk Brasileiro`, `Afrobeats`
- Indigenous: `Māori Pop/Rock`, `Aboriginal Australian Pop/Rock`, `Siberian Indigenous Pop/Rock`

#### **5. Multi-Source API Queries**

The script queries three knowledge bases in cascade:

```python
def search_artist_genre(artist: str, country: Optional[str] = None):
    """
    Optimized search flow:
    1. MusicBrainz (structured, high reliability)
    2. Wikidata (semantic, medium reliability)
    3. Wikipedia in priority languages (rich text, lower reliability)
    """
```

**MusicBrainz query:**

```python
url = "https://musicbrainz.org/ws/2/artist/"
params = {'query': artist, 'fmt': 'json', 'limit': 1}
# Returns structured genre tags with confidence scores
```

**Wikipedia infobox extraction:**

```python
# Extracts from Infobox musical artist
# Fields searched: genre, géneros, genres
# Example: | genre = [[Pop music|Pop]], [[R&B]]
```

**Wikipedia summary extraction with NLP patterns:**

```python
patterns = [
    r'is\s+(?:a|an)\s+([a-z\s\-]+?)\s+(?:singer|rapper|musician)',
    r'are\s+(?:a|an)\s+([a-z\s\-]+?)\s+(?:band|group)',
    r'known\s+for\s+their\s+([a-z\s\-]+?)\s+music',
    r'genre\s+is\s+([a-z\s\-]+?)(?:\.|,|$)'
]
```

#### **6. Intelligent Caching System**

```python
_CACHE = {
    'musicbrainz_country': {},
    'wikidata_country': {},
    'wikipedia_country': {},
    'musicbrainz_genre': {},
    'wikidata_genre': {},
    'wikipedia_genre': {},
}

_SESSION_WIKIPEDIA = requests.Session()
_SESSION_WIKIDATA = requests.Session()
_SESSION_MUSICBRAINZ = requests.Session()
```

