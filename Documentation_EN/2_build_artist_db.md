# 🎵 Script 2: Artist Country + Genre Detection System, Intelligent Enrichment

![MIT License](https://img.shields.io/badge/license-MIT-9ecae1?style=flat-square&logo=open-source-initiative&logoColor=white) ![Data Enrichment](https://img.shields.io/badge/Data-Enrichment-blue?style=flat-square) 

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white) ![Requests](https://img.shields.io/badge/Requests-FF6F61?style=flat-square&logo=python&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white) ![MusicBrainz](https://img.shields.io/badge/MusicBrainz-BA478F?style=flat-square&logo=musicbrainz&logoColor=white) ![Wikipedia API](https://img.shields.io/badge/Wikipedia-000000?style=flat-square&logo=wikipedia&logoColor=white) ![Wikidata](https://img.shields.io/badge/Wikidata-990000?style=flat-square&logo=wikidata&logoColor=white) ![DeepSeek](https://custom-icon-badges.demolab.com/badge/DeepSeek-4D6BFF?logo=deepseek&logoColor=white&style=flat-square)
s


## 📋 General Description

This script is the **second component** of the YouTube Charts intelligence system. It takes the raw artist names extracted by Script 1 and **enriches them with geographic and genre metadata** by querying multiple open knowledge bases. The result is a structured, cumulative database of artists with their country of origin and primary music genre.

The script implements a **cascading search strategy** across MusicBrainz, Wikipedia (summary & infobox), Wikidata, and a DeepSeek AI fallback. It uses a **sophisticated weighted voting system** with country-specific rules, script detection, and name variation generation to achieve high accuracy even for obscure artists.

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

| Color        | Type     | Description                                                  |
| :----------- | :------- | :----------------------------------------------------------- |
| 🔵 Blue       | Input    | Source data (charts database from Script 1)                  |
| 🟠 Orange     | Process  | Internal processing logic                                    |
| 🟣 Purple     | API      | External service queries (MusicBrainz, Wikipedia, Wikidata, DeepSeek) |
| 🟢 Green      | Cache    | In-memory temporary storage                                  |
| 🔴 Red        | Decision | Conditional branching points                                 |
| 🟢 Dark Green | Output   | Final artist database                                        |

### **Diagram 1: Main Flow Overview**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_EN/Diagrams/2_build_artist_db/1.png" alt="Diagram 1" width="45%">

This diagram shows the **high-level pipeline** of the entire system:

1. **Input**: Reads the weekly YouTube Charts database (`youtube_charts_YYYY-WXX.db`) from Script 1
2. **Extraction**: Reads artist names and splits them (handles "feat.", "&", commas, etc.)
3. **Deduplication**: Creates a list of unique artists to avoid redundant processing
4. **Per-Artist Loop**: For each artist, checks if they already exist in the enriched database
   - **If complete** (country + genre known): Skips to next artist ✅
   - **If missing info**: Searches only the missing fields (country or genre)
   - **If new**: Performs full country and genre search
5. **Country Search** → **Genre Search** → **Voting System** → **Database Update**
6. **After all artists**: Generates a final report and automatically commits changes to GitHub

### **Diagram 2: Country Search (Detailed)**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_EN/Diagrams/2_build_artist_db/2.png" alt="Diagram 2" width="45%">

This diagram details the **cascading search strategy** for detecting an artist's country:

1. **Start**: Receives an artist name (may be missing info or new artist)
2. **Name Variations**: Generates up to 15 variations (no accents, no prefixes, etc.)
3. **Cache Check**: First checks in-memory cache to avoid repeat API calls
4. **MusicBrainz**: Queries MusicBrainz API (structured data, high reliability)
   - **If found** → returns country ✅
5. **Wikipedia English**: If not found, queries Wikipedia English:
   - First checks summary (first paragraph) for patterns like "born in...", "from..."
   - Then checks infobox for fields like "origin", "birth_place", "location"
   - **If found** → returns country ✅
6. **Wikipedia Priority Languages**: If still not found, tries Wikipedia in languages based on:
   - The artist's country (if already known from previous step)
   - Detected script from the artist's name (Cyrillic → Russian Wikipedia, etc.)
   - **If found** → returns country ✅
7. **Wikidata**: Final free source, queries Wikidata using properties P27 (country of citizenship) and P19 (place of birth)
8. **DeepSeek AI Fallback**: Only if all free sources fail, queries DeepSeek API (cost-effective)
   - Uses structured prompt asking for country and genre
   - Results are normalized using the same validation functions
   - Rate-limited to 0.5s delay between calls
9. **Result**: Returns either a canonical country name or "Unknown"

### **Diagram 3: Genre Search (Detailed)**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_EN/Diagrams/2_build_artist_db/2.png" alt="Diagram 2" width="45%">


This diagram shows how the system **collects genre candidates** from multiple sources:

1. **Start**: Receives artist name (and country if already detected)
2. **Name Variations**: Same variation system for maximum match rate
3. **MusicBrainz**: First source, extracts genre tags and their counts
   - Adds candidates with base weight (1.5× for MusicBrainz)
4. **Wikidata**: Second source, queries property P136 (genre)
   - Adds candidates with base weight (1.3× for Wikidata)
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

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_EN/Diagrams/2_build_artist_db/4.png" alt="Diagram 4" width="45%">

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
5. **Term Bonuses**: Multiplies weight by 1.4× if specific keywords are found:
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

### **Diagram 5: Database Update Process**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/main/Documentation_EN/Diagrams/2_build_artist_db/5.png" alt="Diagram 5" width="45%">

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

------

## 🔍 Detailed Analysis of `2_build_artist_db.py`

### Code Structure

#### **1. Configuration and Paths**

```python
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
CHARTS_DB_DIR = PROJECT_ROOT / "charts_archive" / "1_download-chart" / "databases"
ARTIST_DB_PATH = PROJECT_ROOT / "charts_archive" / "2_countries-genres-artist" / "artist_countries_genres.db"
```

The script reads from the downloader's output and creates its own enriched database:

| Path             | Purpose                                     |
| :--------------- | :------------------------------------------ |
| `CHARTS_DB_DIR`  | Input: Weekly chart databases from Script 1 |
| `ARTIST_DB_PATH` | Output: Cumulative artist metadata database |

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
Variations generated:
1. Lil Wayne
2. Wayne
3. Lil Wayne (no accent)
4. Lil Wayne (no dots)
5. Wayne (no prefix)
```

**Prefix dictionary includes:**

- `dj`, `mc`, `lil`, `young`, `big`, `the`, `los`, `las`, `el`, `la`

#### **3. Geographic Intelligence System**

The heart of country detection is the `COUNTRIES_CANONICAL` dictionary, a curated knowledge base with **30,000+ terms** mapping to 200+ countries.

**Structure example for United States:**

```python
'United States': {
    # Country names
    'united states', 'usa', 'us', 'america',
    # Demonyms
    'american', 'estadounidense',
    # Cities — All 50 states covered
    'new york', 'los angeles', 'chicago', 'miami', ... (500+ cities)
}
```

**Detection process:**

| Step | Method             | Example                            |
| :--- | :----------------- | :--------------------------------- |
| 1    | Direct match       | "canadian" → Canada                |
| 2    | City mention       | "from Toronto" → Canada            |
| 3    | Regional reference | "born in Brooklyn" → United States |
| 4    | Demonym            | "argentine singer" → Argentina     |

#### **4. Genre Classification Ontology**

The `GENRE_MAPPINGS` dictionary contains **5,000+ genre variants** mapped to 200+ macro-genres.

**Example mapping for Electronic music:**

```python
'house': ('Electrónica/Dance', 'house'),
'deep house': ('Electrónica/Dance', 'deep house'),
'techno': ('Electrónica/Dance', 'techno'),
'trance': ('Electrónica/Dance', 'trance'),
'edm': ('Electrónica/Dance', 'edm'),
```

**Macro-genre categories (200+):**

| Category             | Examples                                               |
| :------------------- | :----------------------------------------------------- |
| **Global**           | Pop, Rock, Hip-Hop/Rap, R&B/Soul, Electrónica/Dance    |
| **Regional America** | Reggaetón/Trap Latino, Bachata, Cumbia, Sertanejo      |
| **Regional Asia**    | K-Pop/K-Rock, J-Pop/J-Rock, C-Pop/C-Rock, T-Pop/T-Rock |
| **Regional Africa**  | Afrobeats, Amapiano, Bongo Flava, Zim Dancehall        |
| **Regional Europe**  | Turbo-folk, Manele, Schlager, Chanson, Fado            |
| **Indigenous**       | Māori Pop/Rock, Aboriginal Australian Pop/Rock         |

#### **5. Multi-Source API Queries**

The script queries four knowledge bases in cascade (with DeepSeek as final fallback):

```python
def search_artist_genre(artist: str, country: Optional[str] = None):
    """
    Optimized search flow:
    1. MusicBrainz (structured, high reliability) → 1.5x weight
    2. Wikidata (semantic, medium reliability) → 1.3x weight
    3. Wikipedia in priority languages (rich text) → 1.0-1.2x weight
    4. DeepSeek API (fallback, only when all free sources fail)
    """
```

**Source weights:**

| Source             | Weight | Reason                                   |
| :----------------- | :----- | :--------------------------------------- |
| MusicBrainz        | 1.5×   | Structured, reliable genre tags          |
| Wikidata           | 1.3×   | Semantic data, medium reliability        |
| Wikipedia Infobox  | 1.2×   | Semi-structured, good for infobox fields |
| Wikipedia Summary  | 1.0×   | Free text, lower confidence              |
| Wikipedia Keywords | 0.5×   | Lowest confidence, pattern matching      |

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
- **Cost savings**: DeepSeek cache prevents duplicate paid calls

#### **7. Script/Language Detection**

```python
def detect_script_from_name(name: str) -> Optional[str]:
    """
    Detects writing system and returns ISO 639-1 language code.
    
    Ranges detected:
    - Devanagari (hi, ne) → India/Nepal
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
        "keywords": ["sertanejo", "funk brasileiro"],
        "bonus_extra": 1.5
    },
    "Puerto Rico": {
        "keywords": ["reggaeton", "trap latino", "urbano"],
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

| Scenario | Existing DB  | New Search      | Result                              |
| :------- | :----------- | :-------------- | :---------------------------------- |
| 1        | (USA, null)  | (null, Hip-Hop) | (USA, Hip-Hop) ✅ Only genre updated |
| 2        | (null, Rock) | (UK, Rock)      | (UK, Rock) ✅ Only country updated   |
| 3        | (USA, Pop)   | (Canada, Pop)   | (USA, Pop) ⚠️ No overwrite           |

### **`artist` Table Structure**

| Column        | Type      | Description            | Example        |
| :------------ | :-------- | :--------------------- | :------------- |
| `name`        | TEXT (PK) | Artist name            | "BTS"          |
| `country`     | TEXT      | Canonical country name | "South Korea"  |
| `macro_genre` | TEXT      | Primary macro-genre    | "K-Pop/K-Rock" |

------

## ⚙️ GitHub Actions Workflow Analysis (`2_update-artist-db.yml`)

### Workflow Structure

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
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true

jobs:
  build-artist-database:
    name: Build and Update Artist Database
    runs-on: ubuntu-latest
    timeout-minutes: 60
    
    permissions:
      contents: write
```

### Job Steps

| Step | Name                                  | Purpose                                     |
| :--- | :------------------------------------ | :------------------------------------------ |
| 1    | 📚 Checkout repository                 | Clone repository with full history          |
| 2    | 🐍 Setup Python                        | Install Python 3.12 with pip cache          |
| 3    | 📦 Install dependencies                | Install requirements (no Playwright needed) |
| 4    | 📁 Ensure directory structure          | Create databases and output folders         |
| 5    | 🚀 Build artist database               | Execute main enrichment script              |
| 6    | ✅ Verify database integrity           | Check database exists and is valid          |
| 7    | 📤 Commit and push changes             | Push changes to GitHub (with rebase)        |
| 8    | 📦 Upload debug artifacts (on failure) | Upload debug data for troubleshooting       |
| 9    | 📋 Generate final report               | Generate execution summary                  |

### Detailed Steps

#### **1. 📚 Repository Checkout**

```yaml
- name: 📚 Checkout repository
  uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Full history for git operations
```

#### **2. 🐍 Python 3.12 Setup**

```python
- name: 🐍 Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: "3.12"
    cache: 'pip'
```

#### **3. 📦 Install Dependencies**

```yaml
- name: 📦 Install dependencies
  run: |
    pip install -r requirements.txt
```

> **Note**: Playwright is not required for this script.

#### **4. 📁 Ensure Directory Structure**

```yaml
- name: 📁 Ensure directory structure
  run: |
    mkdir -p charts_archive/1_download-chart/databases
    mkdir -p charts_archive/2_countries-genres-artist
```

#### **5. 🚀 Build Artist Database**

```yaml
- name: 🚀 Build artist database
  run: |
    python scripts/2_build_artist_db.py
  env:
    GITHUB_ACTIONS: true
    DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
```

#### **6. ✅ Verify Database Integrity**

```yaml
- name: ✅ Verify database integrity
  run: |
    echo "📊 Verifying artist database..."
    DB_PATH="charts_archive/2_countries-genres-artist/artist_countries_genres.db"
    
    if [ -f "$DB_PATH" ]; then
      SIZE=$(stat -c%s "$DB_PATH")
      echo "✅ Database found: $((SIZE / 1024)) KB"
      
      if command -v sqlite3 &> /dev/null; then
        sqlite3 "$DB_PATH" "PRAGMA integrity_check;"
      fi
    else
      echo "❌ Database not found!"
      exit 1
    fi
```

#### **7. 📤 Commit and Push Changes**

```yaml
- name: 📤 Commit and push changes
  run: |
    git config --global user.name "github-actions[bot]"
    git config --global user.email "github-actions[bot]@users.noreply.github.com"
    git add charts_archive/2_countries-genres-artist/
    
    if git diff --cached --quiet; then
      echo "🔭 No changes to commit"
    else
      DATE=$(date +'%Y-%m-%d')
      git commit -m "🤖 Update artist database ${DATE} [Automated]"
      git pull --rebase origin main
      git push origin HEAD:main
    fi
```

#### **8. 📦 Upload Debug Artifacts (on failure)**

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

#### **9. 📋 Generate Final Report**

```yaml
- name: 📋 Generate final report
  if: always()
  run: |
    echo "========================================"
    echo "🎵 FINAL EXECUTION REPORT"
    echo "========================================"
    echo "📅 Date: $(date)"
    echo "📌 Trigger: ${{ github.event_name }}"
    
    DB_FILE="charts_archive/2_countries-genres-artist/artist_countries_genres.db"
    if [ -f "$DB_FILE" ]; then
      SIZE=$(stat -c%s "$DB_FILE")
      echo "✅ Artist database: $((SIZE / 1024)) KB"
      
      if command -v sqlite3 &> /dev/null; then
        ARTIST_COUNT=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM artist;")
        echo "👤 Artists processed: ${ARTIST_COUNT}"
      fi
    fi
```

### Cron Schedule

cron

```
'0 13 * * 1'  # Minute 0, Hour 13, Any day of month, Any month, Monday
```



- **Execution**: Every Monday at 13:00 UTC
- **Offset**: 1 hour after Script 1 (12:00 UTC)
- **Purpose**: Allows download workflow to complete before enrichment begins

### Required Secrets

| Secret             | Purpose                                                      |
| :----------------- | :----------------------------------------------------------- |
| `DEEPSEEK_API_KEY` | Used by DeepSeek AI fallback when all free sources fail. Optional; script continues without it. |

------

## 🚀 Installation and Local Setup

### Prerequisites

- Python 3.7 or higher (3.12 recommended)
- Git installed
- Internet access for API queries
- (Optional) DeepSeek API key for fallback

### Step-by-Step Installation

#### **1. Clone the Repository**

```bash
git clone https://github.com/adroguetth/Music-Charts-Intelligence.git
cd Music-Charts-Intelligence
```

#### **2. Create Virtual Environment (recommended)**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

#### **3. Install Dependencies**

```bash
pip install -r requirements.txt
```

#### **4. Set DeepSeek API Key (optional, for fallback)**

```bash
# Linux/Mac
export DEEPSEEK_API_KEY="your-api-key-here"

# Windows (Command Prompt)
set DEEPSEEK_API_KEY=your-api-key-here

# Windows (PowerShell)
$env:DEEPSEEK_API_KEY="your-api-key-here"
```

#### **5. Run Initial Test**

```bash
python scripts/2_build_artist_db.py
```

### Development Configuration

```bash
# Simulate GitHub Actions environment
export GITHUB_ACTIONS=true

# Enable detailed debugging (shows genre candidates)
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

### Database Growth

| Metric        | Value                 |
| :------------ | :-------------------- |
| Initial run   | 100-200 artists       |
| Weekly growth | 10-50 new artists     |
| Size estimate | ~10KB per 100 artists |

------

## 🔧 Customization and Configuration

### Adjustable Parameters in Script

```python
# In 2_build_artist_db.py
MIN_CANDIDATES = 3        # Minimum genre candidates before Wikipedia search
RETRY_DELAY = 0.5          # Delay between API calls (seconds)
DEFAULT_TIMEOUT = 10       # API timeout (seconds)
DEEPSEEK_RATE_LIMIT = 0.5  # Delay between DeepSeek calls (seconds)
```

### Workflow Configuration

```python
# In 2_update-artist-db.yml
env:
  RETENTION_DAYS: 30       # Days for artifacts

timeout-minutes: 60        # Total job timeout (allows for API rate limits)
```

### Adding New Countries

```python
# Extend COUNTRIES_CANONICAL
'New Country': {
    'country name', 'demonyms', 'capital', 'major cities'
}
```

### Adding New Genre Mappings

```python
# Extend GENRE_MAPPINGS
'new subgenre': ('Macro-Genre', 'subgenre')
```

### Adjusting Country Priorities

```python
# Modify COUNTRY_GENRE_PRIORITY
"Country Name": [
    "Priority Genre 1",   # Gets 2.0x bonus
    "Priority Genre 2",   # Gets 1.5x bonus
    "Priority Genre 3"    # Gets 1.2x bonus
]
```

## 🐛 Troubleshooting

### Common Issues and Solutions

| Error                          | Likely Cause        | Solution                           |
| :----------------------------- | :------------------ | :--------------------------------- |
| "No chart databases found"     | Script 1 hasn't run | Run Script 1 first                 |
| API timeouts                   | Slow network        | Increase `DEFAULT_TIMEOUT`         |
| Rate limiting from APIs        | Too many requests   | Increase `RETRY_DELAY`             |
| DeepSeek API key not set       | Missing secret      | Add to GitHub Secrets or env       |
| Artist not found in any source | Obscure artist      | Add fallback rules or use DeepSeek |

### Logs and Debugging

**Available log levels:**

| Level          | When                  | Details                                   |
| :------------- | :-------------------- | :---------------------------------------- |
| Basic          | Normal execution      | Progress and results                      |
| DEBUG          | `LOG_LEVEL=DEBUG`     | Shows genre candidates and voting details |
| GitHub Actions | `GITHUB_ACTIONS=true` | Enhanced logging for CI/CD                |

------

## 📈 Monitoring and Maintenance

### Health Indicators

| Metric            | Expected Range      | Notes                        |
| :---------------- | :------------------ | :--------------------------- |
| Database size     | +10-50 records/week | Grows slowly over time       |
| Success rate      | >90%                | For established artists      |
| API response time | <2 seconds          | Average across sources       |
| Cache hit rate    | 30-70%              | Increases with database size |
| DeepSeek usage    | <10%                | Only when free sources fail  |

### Performance Metrics

| Metric                 | Expected Range | Notes                         |
| :--------------------- | :------------- | :---------------------------- |
| Artists processed/hour | 500-1000       | Depends on API response times |
| Genre detection rate   | 85-95%         | Lower for niche artists       |
| Country detection rate | 80-90%         | Lower for obscure artists     |
| DeepSeek fallback rate | <10%           | Only when free sources fail   |
| Cost per 100 artists   | ~$0.002        | With DeepSeek fallback        |

------

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

------

## 🧪 Known Limitations

- **API Dependency**: System relies on external services that may change or rate-limit
- **New Artists**: Recently emerging artists may not appear in knowledge bases
- **Niche Genres**: Some micro-genres may not have mappings yet
- **Script Detection**: Heuristic-based, may occasionally misidentify
- **DeepSeek Cost**: While minimal, requires API key and has token costs

---

**⭐ If you find this project useful, please consider starring it on GitHub!**
