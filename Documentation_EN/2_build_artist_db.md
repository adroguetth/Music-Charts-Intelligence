# 🎵 Script 2: Artist Country + Genre Detection System, Intelligent Enrichment

![MIT License](https://img.shields.io/badge/license-MIT-9ecae1?style=flat-square&logo=open-source-initiative&logoColor=white) ![Data Enrichment](https://img.shields.io/badge/Data-Enrichment-blue?style=flat-square) ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white) ![Requests](https://img.shields.io/badge/Requests-FF6F61?style=flat-square&logo=python&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white) ![MusicBrainz](https://img.shields.io/badge/MusicBrainz-BA478F?style=flat-square&logo=musicbrainz&logoColor=white) ![Wikipedia API](https://img.shields.io/badge/Wikipedia-000000?style=flat-square&logo=wikipedia&logoColor=white) ![Wikidata](https://img.shields.io/badge/Wikidata-990000?style=flat-square&logo=wikidata&logoColor=white) ![DeepSeek](https://custom-icon-badges.demolab.com/badge/DeepSeek-4D6BFF?logo=deepseek&logoColor=white&style=flat-square)

## 📥 Quick Downloads
| Document                | Format                                                     |                                                    
| ------------------------- | ------------------------------------------------------------ |
| **🇬🇧 English Documentation** | [PDF](https://drive.google.com/file/d/1ar9huV0mMVS0ABgedO5LQWwyA1aEyKvY/view?usp=drive_link) |
| **🇪🇸 Spanish Documentation**  | [PDF](https://drive.google.com/file/d/1WBHBreKeVToTBygSyCuYsHQUr_zSl3BT/view?usp=drive_link) |

## 📋 General Description

This project is the second component of the YouTube Charts intelligence system. It takes the raw artist names extracted by the downloader and **enriches them with geographic and genre metadata** by querying multiple open knowledge bases. The result is a structured database of artists with their country of origin and primary music genre.


### Key Features

- **Multi-Source Lookup**: Intelligent cascading queries to MusicBrainz, Wikipedia (summary & infobox), and Wikidata
- **DeepSeek AI Fallback**: Uses DeepSeek API as last resort when all free sources fail (cost-effective, ~$0.002 per 100 artists)
- **Smart Name Variation**: Generates up to 15 variations per artist (accents removed, prefixes stripped, etc.) for maximum match rate
- **Geographic Intelligence**: Country detection from cities, demonyms, and regional references using a curated dictionary of 30,000+ terms
- **Genre Classification**: 200+ macro-genres and 5,000+ subgenre mappings with weighted voting system
- **Country-Specific Rules**: Special handling for 50+ countries (e.g., K-Pop for South Korea, Sertanejo for Brazil)
- **Script Detection**: Automatic language detection for non-Latin scripts (Cyrillic, Devanagari, Arabic, Hangul, etc.)
- **Intelligent Updates**: Only fills missing data, never overwrites existing correct information
- **In-Memory Caching**: Avoids redundant API calls during execution
- **CI/CD Optimized**: Specifically configured for GitHub Actions with progressive fallbacks
- **Rate Limiting**: Built-in delays to respect API quotas and avoid throttling

## 📊 Process Flow Diagram

### **Legend**
| Color        | Type     | Description                   |
| :----------- | :------- | :---------------------------- |
| 🔵 Blue       | Input    | Source data (charts database) |
| 🟠 Orange     | Process  | Internal processing logic     |
| 🟣 Purple     | API      | External service queries      |
| 🟢 Green      | Cache    | In-memory temporary storage   |
| 🔴 Red        | Decision | Conditional branching points  |
| 🟢 Dark Green | Output   | Results and final database    |

### **Diagram 1: Main Flow Overview**

<img src="https://drive.google.com/uc?export=view&id=1Xa_kmFpuu-YjUbVn5PnGuS1BICWwLhaq" alt="Main Flow Overview" width="350">

This diagram shows the **high-level pipeline** of the entire system:

1. **Input**: Reads the weekly YouTube Charts database (`youtube_charts_YYYY-WXX.db`)
2. **Extraction**: Reads artist names and splits them (handles "feat.", "&", commas, etc.)
3. **Deduplication**: Creates a list of unique artists to avoid redundant processing
4. **Per-Artist Loop**: For each artist, checks if they already exist in the enriched database
   - **If complete** (country + genre known): Skips to next artist ✅
   - **If missing info**: Searches only the missing fields (country or genre)
   - **If new**: Performs full country and genre search
5. **Country Search** → **Genre Search** → **Voting System** → **Database Update**
6. **After all artists**: Generates a final report and automatically commits changes to GitHub

### **Diagram 2: Country Search (Detailed)**

<img src="https://drive.google.com/uc?export=view&id=1mQx2lJ4bltmssN9VBTnkiFxwQXSJiz7y" alt="Country Search" width="250">

This diagram details the **cascading search strategy** for detecting an artist's country:

1. **Start**: Receives an artist name (may be missing info or new artist)
2. **Name Variations**: Generates up to 15 variations (no accents, no prefixes, etc.)
3. **Cache Check**: First checks in-memory cache to avoid repeat API calls
4. **MusicBrainz**: Queries MusicBrainz API (structured data, high reliability)
   - If found → returns country ✅
5. **Wikipedia English**: If not found, queries Wikipedia English:
   - First checks summary (first paragraph) for patterns like "born in...", "from..."
   - Then checks infobox for fields like "origin", "birth_place", "location"
   - If found → returns country ✅
6. **Wikipedia Priority Languages**: If still not found, tries Wikipedia in languages based on:
   - The artist's country (if already known from previous step)
   - Detected script from the artist's name (Cyrillic → Russian Wikipedia, etc.)
   - If found → returns country ✅
7. **Wikidata**: Final free source, queries Wikidata using properties P27 (country of citizenship) and P19 (place of birth)
8. **DeepSeek AI Fallback**: Only if all free sources fail, queries DeepSeek API (cost-effective)
   - Uses structured prompt asking for country and genre
   - Results are normalized using the same validation functions
   - Rate-limited to 0.5s delay between calls
9. **Result**: Returns either a canonical country name or "Unknown"

### **Diagram 3: Genre Search (Detailed)**

<img src="https://drive.google.com/uc?export=view&id=173wJP4u30DDEN27HaFb52A3nhS1VCg0_" alt="Genre Search" width="350">

This diagram shows how the system **collects genre candidates** from multiple sources:

1. **Start**: Receives artist name (and country if already detected)
2. **Name Variations**: Same variation system for maximum match rate
3. **MusicBrainz**: First source, extracts genre tags and their counts
   - Adds candidates with base weight (1.5x for MusicBrainz)
4. **Wikidata**: Second source, queries property P136 (genre)
   - Adds candidates with base weight (1.3x for Wikidata)
5. **Candidate Check**: Checks if we already have at least 3 genre candidates
   - **If yes**: Proceeds directly to voting system
   - **If no**: Continues to Wikipedia search
6. **Wikipedia Priority Languages**: Queries Wikipedia in languages prioritized by:
   - Country (e.g., Korean artists → Korean Wikipedia)
   - Detected script (e.g., Arabic name → Arabic Wikipedia)
7. **Extraction**: Uses pattern matching to extract genres from:
   - **Infobox**: Looks for "genre", "genres", "género" fields
   - **Summary**: Uses NLP patterns like "is a [genre] singer", "known for [genre] music"
8. **Second Check**: If still under 3 candidates, tries Wikipedia in other common languages
9. **DeepSeek AI Fallback**: Only if all free sources return no candidates, queries DeepSeek API
   - Uses the country (if known) as context to improve accuracy
   - Returns a normalized genre or raw string
10. **Final**: All candidates (with their weights and sources) go to the Voting System

### **Diagram 4: Voting & Weight System**

<img src="https://drive.google.com/uc?export=view&id=1TjRbNOSIj7VdFqohXDTknysfzI7R5HgN" alt="Voting & Weight System" width="250">

This is the **intelligent decision engine** that selects the final genre:

1. **Input**: Receives all genre candidates with their raw weights and sources
2. **Normalization**: Maps each specific subgenre to a macro-genre using the `GENRE_MAPPINGS` dictionary
   - Example: "synth pop", "synth-pop", "synthpop" all → "Pop"
3. **Source Weights**: Applies multipliers based on source reliability:
   - MusicBrainz: ×1.5 (structured, reliable)
   - Wikidata: ×1.3 (semantic, medium reliability)
   - Wikipedia Infobox: ×1.2 (semi-structured)
   - Wikipedia Summary: ×1.0 (free text, lower confidence)
   - Wikipedia Keywords: ×0.5 (lowest confidence)
4. **Script Detection**: Analyzes the artist's name to detect writing system (Cyrillic, Hangul, Arabic, etc.)
5. **Term Bonuses**: Multiplies weight by 1.4x if specific keywords are found:
   - "reggaeton", "trap latino" → boosts Latin genres
   - "k-pop", "korean pop" → boosts K-Pop
   - "sertanejo", "funk brasileiro" → boosts Brazilian genres
6. **Country Priority** (if country known): Applies additional multipliers based on country's genre priority list:
   - 1st priority genre: ×2.0
   - 2nd priority genre: ×1.5
   - 3rd+ priority genres: ×1.2
7. **Country-Specific Rules**: Applies special rules for certain countries:
   - **force_macro**: Forces a specific macro-genre (e.g., Puerto Rico → Reggaetón/Trap Latino)
   - **map_generic_to**: Maps generic genres (Pop, Rock) to regional ones (e.g., Korea → K-Pop/K-Rock)
8. **Script Bonus**: If detected script matches the country's dominant language, applies ×1.2 bonus
9. **Vote Summation**: Adds all weighted votes for each macro-genre
10. **Winner Selection**: Chooses macro-genre with highest total votes
11. **Fallback**: If no winner and country is known, uses the first genre from country's priority list

### **Diagram 5: Database Update**
<img src="https://drive.google.com/uc?export=view&id=1k0Z2qZ-6Pxf7NGd6-m31sL9r77EX2S0r" alt="Country Search" width="350">

This diagram shows how the system **persists data intelligently**:

1. **Input**: Receives final country and genre data for an artist
2. **Connect**: Opens connection to `artist_countries_genres.db`
3. **Existence Check**: Queries if artist already exists in database
4. **If Artist Exists**:
   - **Check Missing Fields**: Compares existing data with new data
   - **Update Only Missing**: Updates country only if existing is NULL/Unknown and new is known
   - Updates genre only if existing is NULL/Unknown and new is known
   - **Never overwrites** existing correct data!
5. **If Artist is New**:
   - Inserts complete new record with country and genre
6. **Log Statistics**: Records success/failure for reporting
7. **Loop Check**: If more artists remain, returns to main loop
8. **All Artists Processed**:
   - Generates final report with statistics (success rate, new artists, etc.)
9. **GitHub Commit**: Automatically commits and pushes changes to repository

---
## 🔍 Detailed Analysis of `2_build_artist_db.py`

### Code Structure

#### **1. Configuration and Paths**
```python
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
CHARTS_DB_DIR = PROJECT_ROOT / "charts_archive" / "1_download-chart" / "databases"
ARTIST_DB_PATH = PROJECT_ROOT / "charts_archive" / "2_countries-genres-artist" / "artist_countries_genres.db"
```

The script reads from the downloader's output and creates its own enriched database:

- **Input**: Weekly chart databases from step 1 (`youtube_charts_YYYY-WXX.db`)
- **Output**: Artist metadata database (`artist_countries_genres.db`)
- **Structure**: `charts_archive/2_countries-genres-artist/`

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

- **Global**: `Pop`, `Rock`, `Hip-Hop/Rap`, `R&B/Soul`, `Electrónica/Dance`
- **Regional America**: `Reggaetón/Trap Latino`, `Bachata`, `Cumbia`, `Sertanejo`, `Funk Brasileiro`, `Regional Mexicano`, `Vallenato`
- **Regional Asia**: `K-Pop/K-Rock`, `J-Pop/J-Rock`, `C-Pop/C-Rock`, `T-Pop/T-Rock`, `V-Pop/V-Rock`, `OPM`, `Indonesian Pop/Dangdut`, `Pakistani Pop`
- **Regional Africa**: `Afrobeats`, `Amapiano`, `Bongo Flava`, `Zim Dancehall`, `Kuduro`, `Kizomba/Zouk`
- **Regional Europe**: `Turbo-folk`, `Manele`, `Schlager`, `Chanson`, `Flamenco / Copla`, `Canzone Italiana`
- **Indigenous**: `Māori Pop/Rock`, `Aboriginal Australian Pop/Rock`, `Siberian Indigenous Pop/Rock`, `Hawaiian Pop/Rock`

#### **5. Multi-Source API Queries**

The script queries four knowledge bases in cascade (with DeepSeek as final fallback):

```python
def search_artist_genre(artist: str, country: Optional[str] = None):
    """
    Optimized search flow:
    1. MusicBrainz (structured, high reliability) → 1.5x weight
    2. Wikidata (semantic, medium reliability) → 1.3x weight
    3. Wikipedia in priority languages (rich text) → 1.0-1.2x weight
    4. DeepSeek API (fallback, only when all free sources fail) → normalized result
    """
```

**MusicBrainz query:**

```python
url = "https://musicbrainz.org/ws/2/artist/"
params = {'query': artist, 'fmt': 'json', 'limit': 1}
# Returns structured genre tags with confidence scores
```

**Wikipedia infobox extraction:**

```text
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

**DeepSeek API fallback:**

```python
def search_deepseek_fallback(artist: str, context_country: Optional[str] = None):
    """
    Uses DeepSeek AI as last resort when all free sources fail.
    - Cost: ~146-1194 tokens per request (~$0.002 per 100 artists)
    - Rate-limited: 0.5s delay between calls
    - Cached to avoid redundant requests
    - Returns normalized country and genre
    """
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

_DEEPSEEK_CACHE = {}  # Cache for DeepSeek results
```

**Benefits:**

- **Performance**: Avoids redundant API calls for the same artist
- **Politeness**: Reduces load on external services
- **Speed**: In-memory cache for current execution
- **Session reuse**: Keep-alive connections for multiple queries
- **Cost savings**: DeepSeek cache prevents duplicate paid calls

#### **7. Script/Language Detection**

```python
def detect_script_from_name(name: str) -> Optional[str]:
    """
    Detects writing system and returns ISO 639-1 language code.
    
    Ranges detected:
    - Devanagari (hi, ne) → India/Nepal
    - Tamil (ta) → South India/Sri Lanka
    - Arabic/Urdu (ar/ur) → Middle East/Pakistan
    - Cyrillic (ru/uk/bg/sr) → Eastern Europe
    - Hangul (ko) → Korea
    - Hanzi/Kanji (zh/ja) → China/Japan
    """
```

**Used for:**

- Prioritizing Wikipedia queries in the right language
- Applying regional bonuses (e.g., Korean script → K-Pop)
- Improving name variation generation
- Providing context to DeepSeek fallback

#### **8. Weighted Voting System**

The `select_primary_genre` function implements a sophisticated voting algorithm:

```python
def select_primary_genre(artist: str, genre_candidates: List[Tuple[str, int, str]],
                         country: Optional[str] = None, detected_lang: Optional[str] = None):
    """
    Weighted voting system:
    - Base weight from source (MusicBrainz 1.5x, Infobox 1.2x, Wikidata 1.3x)
    - Term bonuses for specific genres (K-Pop, Reggaetón, etc.) 1.4x
    - Country priority bonus (top genre 2.0x, second 1.5x)
    - Country-specific rules (force_macro, map_generic_to)
    - Script detection bonus (1.2x for matching region)
    """
```

**Example for a South Korean artist:**

```python
Candidate genres detected:
- "k-pop" from MusicBrainz (weight 1.5) → K-Pop/K-Rock
- "pop" from Wikipedia (weight 1.0) → Pop
- "dance" from Wikipedia (weight 0.5) → Electrónica/Dance

Country = South Korea (priority: K-Pop/K-Rock #1 → 2.0x bonus)
Detected script = Korean (1.2x bonus for K-Pop/K-Rock)

Final votes:
- K-Pop/K-Rock: (1.5 × 2.0 × 1.2) = 3.6
- Pop: (1.0 × 1.2) = 1.2
- Electrónica/Dance: (0.5 × 1.2) = 0.6

Winner: K-Pop/K-Rock ✓
```

#### **9. Country-Specific Rules**

```python
COUNTRY_SPECIFIC_RULES = {
    "South Korea": {
        "keywords": ["k-pop", "kpop", "korean pop", "idol group"],
        "bonus_extra": 1.5,
        "force_macro": "K-Pop/K-Rock",
        "map_generic_to": "K-Pop/K-Rock"  # Maps "pop" → K-Pop
    },
    "Brazil": {
        "keywords": ["sertanejo", "funk brasileiro", "funk carioca", "brazilian funk"],
        "bonus_extra": 1.5
    },
    "Jamaica": {
        "keywords": ["dancehall", "reggae", "roots reggae", "dub"],
        "bonus_extra": 1.5
    },
    "Puerto Rico": {
        "keywords": ["reggaeton", "reggaetón", "trap latino", "urbano", "dembow"],
        "bonus_extra": 2.0,
        "force_macro": "Reggaetón/Trap Latino"
    },
    # ... 50+ countries with specific rules
}
```

#### **10. Smart Database Updates**

```python
def insert_artist(artist: str, country: str, genre: Optional[str] = None, source: str = ""):
    """
    Intelligent upsert:
    - If artist exists, only update missing fields
    - Never overwrite existing correct data
    - Track source of information for transparency
    """
```

**Example scenarios:**

```python
Artist already in DB: (Country: USA, Genre: null)
New search finds: (Country: null, Genre: Hip-Hop)
Result: (Country: USA, Genre: Hip-Hop)  ✓ Only genre updated

Artist already in DB: (Country: null, Genre: Rock)
New search finds: (Country: UK, Genre: Rock)
Result: (Country: UK, Genre: Rock)  ✓ Only country updated
```

### **`artist` Table Structure**

| Column      | Type   | Description               | Example        |
| :---------- | :----- | :------------------------ | :------------- |
| name        | `TEXT` | Artist name (primary key) | "BTS"          |
| country     | `TEXT` | Canonical country name    | "South Korea"  |
| macro_genre | `TEXT` | Primary macro-genre       | "K-Pop/K-Rock" |

---
## ⚙️ GitHub Actions Workflow Analysis (`2-update-artist-database.yml`)

### **Workflow Structure**

```yaml
name: 2- Update Artist Database

on:
  schedule:
    # Run every Monday at 13:00 UTC (1 hour after download)
    - cron: '0 13 * * 1'
  
  # Allow manual execution
  workflow_dispatch:

env:
  RETENTION_DAYS: 30
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true   # Advance to Node.js 24

jobs:
  build-artist-database:
    name: Build and Update Artist Database
    runs-on: ubuntu-latest
    timeout-minutes: 60
    
    permissions:
      contents: write
```

### **Jobs and Steps**

#### **Job: `build-artist-database`**

- **Operating system**: Ubuntu Latest
- **Timeout**: 60 minutes (allows for API rate limiting and DeepSeek calls)
- **Permissions**: Repository write access

#### **Detailed Steps:**

1. **📚 Repository Checkout**

```yaml
uses: actions/checkout@v4
with:
  fetch-depth: 0  # Full history for git operations
```

2. **🐍 Python 3.12 Setup**

```yaml
uses: actions/setup-python@v5
with:
  cache: 'pip'  # Dependency caching
```

3. **📦 Dependency Installation**

```yaml
run: |
  pip install -r requirements.txt
  # Playwright not needed for this script
```

4. **📁 Directory Structure Creation**

```yaml
run: |
  mkdir -p charts_archive/1_download-chart/databases
  mkdir -p charts_archive/2_countries-genres-artist
```

5. **🚀 Main Script Execution with DeepSeek API Key**

```yaml
- name: 🚀 Build artist database
  run: |
    python scripts/2_build_artist_db.py
  env:
    GITHUB_ACTIONS: true
    DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
```

6. **✅ Database Integrity Verification**

```python
- name: ✅ Verify database integrity
  run: |
    echo "📊 Verifying artist database..."
    DB_PATH="charts_archive/2_countries-genres-artist/artist_countries_genres.db"
    
    # Check directory contents
    echo "📂 Directory contents:"
    ls -la charts_archive/2_countries-genres-artist/
    
    # Verify database exists and has size
    if [ -f "$DB_PATH" ]; then
      SIZE=$(stat -c%s "$DB_PATH")
      echo "✅ Database found: $((SIZE / 1024)) KB"
      
      # Optional: Verify database integrity with sqlite3
      if command -v sqlite3 &> /dev/null; then
        echo "🔍 Checking database integrity..."
        sqlite3 "$DB_PATH" "PRAGMA integrity_check;"
      fi
    else
      echo "❌ Database not found!"
      exit 1
    fi
```

7. **📤 Automatic Commit and Push**

```yaml
- name: 📤 Commit and push changes
  run: |
    echo "📝 Preparing commit..."
    
    # Configure git user for automated commits
    git config --global user.name "github-actions[bot]"
    git config --global user.email "github-actions[bot]@users.noreply.github.com"
    
    # Stage only artist database files
    git add charts_archive/2_countries-genres-artist/
    
    # Check if there are changes to commit
    if git diff --cached --quiet; then
      echo "🔭 No changes to commit"
    else
      DATE=$(date +'%Y-%m-%d')
      git commit -m "🤖 Update artist database ${DATE} [Automated]"
      
      # Pull latest changes with rebase to avoid merge commits
      echo "⬇️ Pulling latest changes with rebase..."
      git pull --rebase origin main
      
      echo "⬆️ Pushing changes to repository..."
      git push origin HEAD:main
      echo "✅ Changes pushed successfully"
    fi
```

8. **📦 Artifact Upload (on failure)**


```yaml
- name: 📦 Upload debug artifacts
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: artist-db-debug-${{ github.run_number }}
    path: |
      charts_archive/
    retention-days: 7
```

9. **📋 Final Report**

```yaml
- name: 📋 Generate final report
  if: always()
  run: |
    echo "========================================"
    echo "🎵 FINAL EXECUTION REPORT"
    echo "========================================"
    echo "📅 Date: $(date)"
    echo "📌 Trigger: ${{ github.event_name }}"
    echo "🔗 Commit: ${{ github.sha }}"
    echo ""
    
    DB_FILE="charts_archive/2_countries-genres-artist/artist_countries_genres.db"
    if [ -f "$DB_FILE" ]; then
      SIZE=$(stat -c%s "$DB_FILE")
      echo "✅ Artist database: $((SIZE / 1024)) KB"
      
      # Count artists
      if command -v sqlite3 &> /dev/null; then
        ARTIST_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM artist;" 2>/dev/null || echo "N/A")
        echo "👤 Artists processed: ${ARTIST_COUNT}"
      fi
    else
      echo "⚠️ Artist database not found"
    fi
    
    echo ""
    echo "📊 Trigger details:"
    if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
      echo "   • Triggered by: Manual dispatch"
    elif [ "${{ github.event_name }}" = "schedule" ]; then
      echo "   • Triggered by: Scheduled cron (Monday 13:00 UTC)"
    fi
    
    echo ""
    echo "✅ Process completed"
    echo "========================================"
```

### **Cron Scheduling**

```cron
'0 13 * * 1'  # Minute 0, Hour 13, Any day of month, Any month, Monday
```

- **Execution**: Every Monday at 13:00 UTC
- **Offset**: 1 hour after the download workflow (12:00 UTC)
- **Purpose**: Allows download workflow to complete before enrichment begins

---

## 🔐 Required Secrets

| Secret             | Purpose                                                      |
| :----------------- | :----------------------------------------------------------- |
| `DEEPSEEK_API_KEY` | Used by the DeepSeek AI fallback system to retrieve country and genre information when all free sources (MusicBrainz, Wikidata, Wikipedia) fail to return results. Required only for the fallback functionality; the script continues without it if not provided. |

---

## 🚀 Installation and Local Setup

### **Prerequisites**

- Python 3.7 or higher
- Git installed
- Internet access for API queries
- (Optional) DeepSeek API key for fallback

### **Step-by-Step Installation**

1. **Clone the Repository**

```bash
git clone <repository-url>
cd <project-directory>
```

2. **Create Virtual Environment (recommended)**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install Dependencies**

```bash
pip install -r requirements.txt
# Playwright is not required for this script
```

4. **Set DeepSeek API Key (optional, for fallback)**

```bash
# Linux/Mac
export DEEPSEEK_API_KEY="your-api-key-here"

# Windows (Command Prompt)
set DEEPSEEK_API_KEY=your-api-key-here

# Windows (PowerShell)
$env:DEEPSEEK_API_KEY="your-api-key-here"
```

5. **Run Initial Test**

```bash
python scripts/2_build_artist_db.py
```

### **Development Configuration**

```bash
# To simulate GitHub Actions environment
export GITHUB_ACTIONS=true

# For detailed debugging (shows genre candidates)
export LOG_LEVEL=DEBUG
```

---

## 📁 Generated File Structure

```text
charts_archive/
├── 1_download-chart/
│   ├── latest_chart.csv
│   ├── databases/
│   │   ├── youtube_charts_2025-W01.db
│   │   ├── youtube_charts_2025-W02.db
│   │   └── ...
│   └── backup/
│       └── ...
└── 2_countries-genres-artist/          # ← This script's output
    └── artist_countries_genres.db       # Enriched artist database
```

### **Database Growth**

- Initial run: 100-200 artists
- Weekly growth: 10-50 new artists (only new ones from weekly charts)
- Size estimate: ~10KB per 100 artists

---

## 🔧 Customization and Configuration

### **Adjustable Parameters in Script**

```python
# In 2_build_artist_db.py
MIN_CANDIDATES = 3        # Minimum genre candidates before Wikipedia search
RETRY_DELAY = 0.5          # Delay between API calls (seconds)
DEFAULT_TIMEOUT = 10       # API timeout (seconds)
DEEPSEEK_RATE_LIMIT = 0.5  # Delay between DeepSeek calls (seconds)
```

### **Workflow Configuration**

```yaml
# In 2-update-artist-database.yml
env:
  RETENTION_DAYS: 30       # Days for artifacts

timeout-minutes: 60        # Total job timeout (allows for API rate limits)
```

### **Adding New Countries**

```python
# Extend COUNTRIES_CANONICAL
'New Country': {
    'country name', 'demonyms', 'capital', 'major cities'
}
```

### **Adding New Genre Mappings**

```python
# Extend GENRE_MAPPINGS
'new subgenre': ('Macro-Genre', 'subgenre')
```

### **Adjusting Country Priorities**

```python
# Modify COUNTRY_GENRE_PRIORITY
"Country Name": [
    "Priority Genre 1",   # Gets 2.0x bonus
    "Priority Genre 2",   # Gets 1.5x bonus
    "Priority Genre 3"    # Gets 1.2x bonus
]
---

## 🐛 Troubleshooting

### **Common Issues and Solutions**

1. **Error: "No chart databases found"**
   - Run the download workflow (script 1) first
   - Check if `charts_archive/1_download-chart/databases/` exists
   - Verify file permissions
2. **Error: API timeouts in GitHub Actions**

```bash
# Increase timeouts in script
DEFAULT_TIMEOUT = 20
RETRY_DELAY = 1.0
```

3. **Error: Rate limiting from APIs**

   - The script includes delays between calls
   - For large batches, consider adding longer delays
   - Monitor API response headers for rate limit info

4. **Error: DeepSeek API key not set**

   - Add `DEEPSEEK_API_KEY` to GitHub Secrets
   - For local testing, set environment variable
   - The script continues without DeepSeek if key is missing

5. **Error: Artist not found in any source**
   - Check if artist name has special characters
   - Try manual search in MusicBrainz
   - Add fallback rules for the country
   - DeepSeek may help with obscure artists
   

### **Logs and Debugging**

**Available log levels:**

1. **Basic information**: Shows progress and results
2. **DEBUG mode**: Shows genre candidates and voting details
3. **GitHub Actions mode**: Enhanced logging for CI/CD
4. **Verbose API logging**: Uncomment `print` statements in API functions
5. **DeepSeek fallback logging**: Shows when AI fallback is used

---

## 📈 Monitoring and Maintenance

### **Health Indicators**

1. **Database size**: Grows by ~10-50 records/week
2. **Success rate**: Should be >90% for established artists
3. **API response time**: <2 seconds average
4. **Cache hit rate**: Increases over time as artists accumulate
5. **DeepSeek usage**: Should be low (<10% of artists)

### **Performance Metrics**

| Metric                 | Expected Range | Notes                                         |
| :--------------------- | :------------- | :-------------------------------------------- |
| Artists processed/hour | 500-1000       | Depends on API response times                 |
| Cache hit rate         | 30-70%         | Increases with database size                  |
| Genre detection rate   | 85-95%         | Lower for very niche artists                  |
| Country detection rate | 80-90%         | Lower for artists with little online presence |
| DeepSeek fallback rate | <10%           | Only used when free sources fail              |
| Cost per 100 artists   | ~$0.002        | With DeepSeek fallback                        |

---

## 📄 License and Attribution

- **License**: MIT
- **Author**: Alfonso Droguett
  - 🔗 **LinkedIn:** [Alfonso Droguett](https://www.linkedin.com/in/adroguetth/)
  - 🌐 **Web portfolio:** [adroguett-portfolio.cl](https://www.adroguett-portfolio.cl/)
  - 📧 **Email:** adroguett.consultor@gmail.com
- **Data Sources**:
  - MusicBrainz (GPL License)
  - Wikipedia (CC BY-SA)
  - Wikidata (CC0)
  - DeepSeek (Commercial API, fallback only)

---

## 🤝 Contribution

1. Report issues with complete logs
2. Propose improvements with use cases
3. Add new genre mappings with examples
4. Contribute country variants (especially for underrepresented regions)
5. Maintain compatibility with existing database structure

---

## 🧪 Known Limitations and Future Improvements

### **Current Limitations**

- **API Dependency**: System relies on external services that may change or rate-limit
- **New Artists**: Recently emerging artists may not appear in knowledge bases
- **Niche Genres**: Some micro-genres may not have mappings yet
- **Brazilian MCs**: Currently receive `Sertanejo` as fallback (priority list order)
- **Script Detection**: Heuristic-based, may occasionally misidentify
- **DeepSeek Cost**: While minimal, requires API key and has token costs


------

**⭐ If you find this project useful, please consider starring it on GitHub!**
