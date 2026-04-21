# Script 3: YouTube Chart Enrichment System

![MIT License](https://img.shields.io/badge/license-MIT-9ecae1?style=flat-square&logo=open-source-initiative&logoColor=white) ![Web Scraping](https://img.shields.io/badge/Web-Scraping-orange?style=flat-square) ![ETL](https://img.shields.io/badge/ETL-9ecae1?style=flat-square) ![Data Enrichment](https://img.shields.io/badge/Data-Enrichment-blue?style=flat-square)

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white) ![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=flat-square&logo=selenium&logoColor=white) ![yt-dlp](https://img.shields.io/badge/yt--dlp-FF6F61?style=flat-square&logo=youtube&logoColor=white) ![YouTube API](https://img.shields.io/badge/YouTube_API-FF0000?style=flat-square&logo=youtube&logoColor=white)


## 📥 Quick Downloads

| Document                     | Format                                                       |
| :--------------------------- | :----------------------------------------------------------- |
| **🇬🇧 English Documentation** | [PDF](https://drive.google.com/file/d/1XGEx2fRBCpOhU5BfY_YjlKm6zmI41RpB/view?usp=drive_link) |
| **🇪🇸 Spanish Documentation** | [PDF](https://drive.google.com/file/d/1tSFjf_gQQeArdE4n5DLL2I2G_MJW6vE3/view?usp=drive_link) |

> **📚 Legacy Documentation:** For the previous version of this script (with collaboration weighting system included), please refer to the [Script 3 Legacy Documentation](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/Documentation_backup/3_enrich-chart-data.md)

## 📋 General Description

This script is the **third component** of the YouTube Charts intelligence system. It takes the weekly chart database (from Script 1) and the **song catalog database (from Script 2_2)**, then **enriches each song with detailed YouTube video metadata** using an intelligent three-layer fallback system.

The script extracts video duration, likes, comments, upload date, audio language, regional restrictions, and classifies video type (official/lyric/live), channel type (VEVO/Topic/Artist), and collaboration patterns. **Country and genre information are no longer resolved in this script** – they are read directly from the song catalog (`build_song.db`) where they were pre-resolved by Script 2_2's collaboration weighting algorithm.

### Key Features

- **3-Layer Retrieval System**: YouTube API (priority) → Selenium → yt-dlp (last resort) for maximum reliability
- **Optimized Performance**: Processes 100 songs in ~2 minutes using YouTube API (vs. 8+ minutes with pure yt-dlp)
- **Song Catalog Integration**: Reads `artist_country`, `macro_genre`, `artists_found`, and `id` from `build_song.db` (Script 2_2 output)
- **Foreign Key Relationship**: The `id` column now references `artist_track.id` from the catalog
- **Video Metadata Detection**: Identifies whether a video is official, lyric video, live performance, or remix/special version
- **Channel Classification**: Detects VEVO, Topic, Label/Studio, Artist Channel, and more
- **Automatic Updates**: Selects the most recent charts database and generates its enriched version
- **CI/CD Optimized**: Specifically designed to run in GitHub Actions with zero manual intervention

### Version Changes

| Feature                         | [Previous (Legacy)](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/Documentation_backup/3_enrich-chart-data.md) | Current Version                   |
| :------------------------------ | :----------------------------------------------------------- | :-------------------------------- |
| **Country/Genre Resolution**    | Script 3 (weekly, per song)                                  | Script 2_2 (once per unique song) |
| **Artist Database Source**      | Downloads from GitHub URL                                    | Reads local `build_song.db`       |
| **Collaboration Weighting**     | Included in Script 3                                         | Moved to Script 2_2               |
| **COUNTRY_TO_CONTINENT**        | Defined in Script 3                                          | Moved to Script 2_2               |
| **GENRE_HIERARCHY**             | Defined in Script 3                                          | Moved to Script 2_2               |
| **resolve_country_and_genre()** | In Script 3                                                  | Moved to Script 2_2               |
| **Output `id` Column**          | AUTOINCREMENT                                                | Foreign key to `artist_track.id`  |

------

## 📊 Process Flow Diagram

### **Legend**

| Color        | Type     | Description                                              |
| :----------- | :------- | :------------------------------------------------------- |
| 🔵 Blue       | Input    | Source data (chart database + song catalog)              |
| 🟠 Orange     | Process  | Internal processing logic                                |
| 🟣 Purple     | API      | External service queries (YouTube API, Selenium, yt-dlp) |
| 🟢 Green      | Storage  | SQLite databases, temporary files                        |
| 🔴 Red        | Decision | Conditional branching points                             |
| 🟢 Dark Green | Output   | Enriched database                                        |

### **Diagram 1: Main Flow Overview**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/refs/heads/main/Documentation_EN/Diagrams/3_enrich_chart_data/1.png" alt="Diagram 1: Main Flow Overview" width="500">

This diagram shows the **high-level pipeline** of the entire system:

1. **Input**: Locates the most recent chart database (`youtube_charts_YYYY-WXX.db`) from Script 1
2. **Load Song Catalog**: Reads `build_song.db` from Script 2.2 (no longer downloads artist DB from GitHub)
3. **Build Lookup**: Creates in-memory dictionary `{(artist_names, track_name): (id, country, genre, artists_found)}` for O(1) lookups
4. **Load Songs**: Reads 100 songs from `chart_data` table
5. **Create Output Table**: Sets up `enriched_songs` table with 25 columns + indexes (including foreign key to catalog)
6. **Per-Song Loop**: For each song (1 to 100):
   - **Lookup Catalog Data**: Queries dictionary for song's `id`, `artist_country`, `macro_genre`, `artists_found`
   - **Fetch YouTube Metadata**: 3-layer fallback (API → Selenium → yt-dlp)
   - **Classify Video**: Detects type, channel type, collaboration, upload season
   - **Insert Row**: Saves enriched data with catalog ID as foreign key
7. **Output**: Enriched database ready for Script 4 (notebook generation)

### **Diagram 2: 3-Layer Metadata Retrieval System**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/refs/heads/main/Documentation_EN/Diagrams/3_enrich_chart_data/2.png" alt="Diagram 2: 3-Layer Metadata Retrieval" width="600">

This diagram details the **cascading retrieval strategy** for YouTube video metadata:

1. **Start**: Receives YouTube video URL and artist CSV string
2. **Layer 1 – YouTube Data API v3** (0.3–0.8s/video):
   - Extracts video_id from URL (11-character pattern)
   - Queries API for `snippet`, `contentDetails`, `statistics`
   - Retrieves: duration, likes, comments, audio language, upload date, region restrictions
   - **If successful** → Returns full metadata ✅
   - **If fails** (no key, quota exceeded, error) → Proceeds to Layer 2
3. **Layer 2 – Selenium Headless Browser** (3–5s/video):
   - Launches headless Chrome browser
   - Navigates to video page, waits for title element
   - Extracts: title, duration (from player), channel name, upload date (from meta tag)
   - **Note**: Selenium does NOT return likes, comments, or audio language
   - **If successful** → Returns partial metadata ✅
   - **If fails** → Proceeds to Layer 3
4. **Layer 3 – yt-dlp with Client Rotation** (2–4s/video):
   - Tries multiple player client configurations sequentially:
     - `android` (most reliable)
     - `ios` (good fallback)
     - `android + web` (combination)
     - `web` (standard browser)
   - Each attempt includes retries and delays to avoid bot detection
   - **If any succeeds** → Returns full metadata ✅
   - **If all fail** → Returns empty metadata with error message
5. **Output**: Returns metadata dict with 15+ fields (some may be empty on failure)

### **Diagram 3: Song Catalog Integration (Updated)**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/refs/heads/main/Documentation_EN/Diagrams/3_enrich_chart_data/3.png" alt="Diagram 3: Song Catalog Integration" width="650">

This diagram shows the **catalog lookup flow** that replaces the former collaboration weighting system:

1. **Input**: Receives `artist_names` and `track_name` from chart row
2. **Lookup in Catalog**: Query `song_catalog_lookup` dictionary with `(artist_names, track_name)` key
3. **If Found**:
   - Retrieve `song_id`, `artist_country`, `macro_genre`, `artists_found`
   - Use these values directly in enriched output
   - **No country/genre resolution performed** (already done by Script 2.2)
4. **If Not Found**:
   - Set `song_id = NULL`
   - Set `artist_country = "Unknown"`
   - Set `macro_genre = "Pop"`
   - Set `artists_found = "0/0"`
5. **Output**: Enriched row with proper foreign key relationship

> **Note**: The collaboration weighting system (`COUNTRY_TO_CONTINENT`, `GENRE_HIERARCHY`, `resolve_country_and_genre()`) has been **moved to Script 2.2**. Script 3 now consumes the pre-resolved values.

------

## 🔍 Detailed Analysis of `3_enrich_chart_data.py`

### Code Structure

#### **1. Configuration and Paths**

```python
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent

# Input: Weekly chart databases from Script 1
INPUT_DB_DIR = PROJECT_ROOT / "charts_archive" / "1_download-chart" / "databases"

# Input: Song catalog database from Script 2.2 (REPLACES artist DB download)
SONG_CATALOG_DB_PATH = PROJECT_ROOT / "charts_archive" / "2_2.build-song-catalog" / "build_song.db"

# Output: Enriched databases for Script 4
OUTPUT_DIR = PROJECT_ROOT / "charts_archive" / "3_enrich-chart-data"
```

The script integrates the two components:

| Path                   | Purpose                                                      |
| :--------------------- | :----------------------------------------------------------- |
| `INPUT_DB_DIR`         | Input: Weekly chart databases from Script 1                  |
| `SONG_CATALOG_DB_PATH` | Input: Song catalog with pre-resolved country/genre from Script 2.2 |
| `OUTPUT_DIR`           | Output: Enriched databases for Script 4                      |

**Changes from previous version:**

- **REMOVED**: `URL_ARTIST_DB` (no longer downloads artist database from GitHub)
- **ADDED**: `SONG_CATALOG_DB_PATH` (reads local catalog instead)

#### **2. Core Reference Tables (REMOVED)**

The following tables have been **removed** from Script 3 as they were moved to Script 2.2:

- ~~`COUNTRY_TO_CONTINENT`~~ (196 countries mapping)
- ~~`GENRE_HIERARCHY`~~ (genre hierarchies by country)

These are now maintained exclusively in `2_2.build_song_catalog.py`.

#### **3. 3-Layer Metadata Retrieval System**

```
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
    """
```



**Layer 1 – YouTube Data API v3:**

```python
# Extract video ID from URL
vid_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
video_id = vid_match.group(1)

youtube = build('youtube', 'v3', developerKey=api_key)
response = youtube.videos().list(
    part='snippet,contentDetails,statistics',
    id=video_id
).execute()

# Retrieved fields:
# - duration: isodate.parse_duration() → seconds
# - likeCount, commentCount
# - defaultAudioLanguage
# - regionRestriction (blocked/allowed)
# - publishedAt → date and quarter
# - title, description, channelTitle
```



**Layer 2 – Selenium Headless Browser:**

```python
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(service=service, options=chrome_options)

driver.get(url)
title = driver.find_element(By.CSS_SELECTOR, "h1.ytd-video-primary-info-renderer").text
duration = driver.find_element(By.CSS_SELECTOR, "span.ytp-time-duration").text
channel = driver.find_element(By.CSS_SELECTOR, "a.ytd-channel-name").text
date = driver.find_element(By.CSS_SELECTOR, "meta[itemprop='datePublished']").get_attribute("content")
```



**Layer 3 – yt-dlp with Client Rotation:**

```python
client_options = [
    {'player_client': ['android']},     # Most reliable
    {'player_client': ['ios']},         # Good fallback
    {'player_client': ['android', 'web']},  # Combination
    {'player_client': ['web']},         # Standard browser
]

for opts in client_options:
    ydl_config = {
        'quiet': True,
        'skip_download': True,
        'extractor_retries': 5,
        'sleep_interval': 2,
        **opts
    }
    with yt_dlp.YoutubeDL(ydl_config) as ydl:
        info = ydl.extract_info(url, download=False)
        if info:
            break  # Success
```



#### **4. Collaboration Weighting System (REMOVED)**

The following functions have been **removed** from Script 3:

- ~~`resolve_country_and_genre(artists_info: list) -> tuple`~~
- ~~`infer_genre_by_country(artists_info: List[Dict]) -> str`~~
- ~~`get_continent(country: str) -> str`~~

These functions were moved to Script 2.2 where they execute **once per unique song** at catalog insertion time, rather than weekly per chart appearance.

**Before (Legacy):**

- Each week: 100 songs × country/genre resolution
- Total: ~5,200 resolutions per year

**After (Current):**

- Each unique song: 1 resolution at catalog insertion

- Total: ~500-1,000 resolutions per year (depending on new song rate)

  

#### **5. Text Classifiers **

**Video Type Detection:**

```python
def detect_video_type(title: str, description: str = "") -> dict:
    full_text = f"{title.lower()} {description.lower()}"
    
    is_official = any(kw in full_text for kw in ['official', 'official music video'])
    is_lyric = any(kw in title.lower() for kw in ['lyric', 'lyrics', 'letra'])
    is_live = any(kw in full_text for kw in ['live', 'concert', 'performance'])
    is_special = any(kw in title.lower() for kw in ['remix', 'sped up', 'slowed', 'acoustic'])
    
    return {
        'is_official_video': is_official,
        'is_lyric_video': is_lyric,
        'is_live_performance': is_live,
        'is_special_version': is_special
    }
```



**Collaboration Detection:**

```python
def detect_collaboration(title: str, artists_csv: str) -> dict:
    collab_patterns = [r'\sft\.\s', r'\sfeat\.\s', r'\s&\s', r'\sx\s', r'\swith\s']
    is_collab = any(re.search(p, title.lower()) for p in collab_patterns)
    
    if artists_csv:
        artist_count = artists_csv.count('&') + artists_csv.count(',') + 1
    else:
        artist_count = 2 if is_collab else 1
    
    return {'is_collaboration': is_collab, 'artist_count': min(artist_count, 10)}
```



**Channel Type Classification:**

```python
def detect_channel_type(channel_title: str) -> dict:
    ch = channel_title.lower()
    
    if 'vevo' in ch:
        return {'channel_type': 'VEVO'}
    elif 'topic' in ch:
        return {'channel_type': 'Topic'}
    elif any(w in ch for w in ['records', 'music', 'label', 'studios']):
        return {'channel_type': 'Label/Studio'}
    elif any(w in ch for w in ['official', 'artist', 'band', 'singer']):
        return {'channel_type': 'Artist Channel'}
    else:
        return {'channel_type': 'General'}
```



#### **6. Song Catalog Lookup (NEW)**

```python
def load_song_catalog_lookup() -> dict:
    """
    Load the song catalog (artist_track table) into an in-memory dict.
    
    The key is a tuple of (artist_names, track_name) exactly as stored.
    The value is a tuple of (id, artist_country, macro_genre, artists_found).
    
    Returns:
        dict: {(artist_names, track_name): (id, country, genre, artists_found)}
    """
    catalog_lookup = {}
    if not SONG_CATALOG_DB_PATH.exists():
        print(f"⚠️  Song catalog not found at {SONG_CATALOG_DB_PATH}.")
        print("   Please run 2_2.build_song_catalog.py first to create the catalog.")
        return catalog_lookup
    
    conn = sqlite3.connect(SONG_CATALOG_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT artist_names, track_name, id, artist_country, macro_genre, artists_found
        FROM artist_track
    """)
    rows = cursor.fetchall()
    conn.close()
    
    for artist_names, track_name, song_id, country, genre, found in rows:
        catalog_lookup[(artist_names, track_name)] = (song_id, country, genre, found)
    
    return catalog_lookup
```



#### **7. Artist Name Processing **

```python
def parse_artist_list(artist_names: str) -> list:
    """Split raw artist names using multiple delimiters."""
    text = artist_names
    for sep in ['&', 'feat.', 'ft.', ',', ' y ', ' and ', ' with ', ' x ', ' vs ']:
        text = text.replace(sep, '|')
    return [part.strip() for part in text.split('|') if part.strip()]

def normalize_name(name: str) -> str:
    """Normalize artist name for dictionary lookup."""
    name = re.sub(r'\s+', ' ', str(name)).strip().lower()
    name = re.sub(r'[^\w\s]', '', name)  # Remove punctuation
    return name
```



> **Note**: `parse_artist_list()` and `normalize_name()` are still used for collaboration detection in video titles, but **NOT** for country/genre resolution.

#### **8. Output Database Schema (UPDATED)**

sqlite

```sqlite
CREATE TABLE enriched_songs (
    id INTEGER UNIQUE,                     -- Foreign key to artist_track.id (was AUTOINCREMENT)
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
    artist_country TEXT,                   -- From catalog (was resolved here)
    macro_genre TEXT,                      -- From catalog (was resolved here)
    artists_found TEXT,                    -- From catalog (was generated here)
    error TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for query optimization
CREATE INDEX idx_country ON enriched_songs(artist_country);
CREATE INDEX idx_genre ON enriched_songs(macro_genre);
CREATE INDEX idx_upload_date ON enriched_songs(upload_date);
CREATE INDEX idx_error ON enriched_songs(error);
```

[]()

**Schema Changes:** 

| Column           | [Previous (Legacy)](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/Documentation_backup/3_enrich-chart-data.md) | Current                                  |
| :--------------- | :----------------------------------------------------------- | :--------------------------------------- |
| `id`             | `INTEGER PRIMARY KEY AUTOINCREMENT`                          | `INTEGER UNIQUE` (foreign key reference) |
| `artist_country` | Resolved by Script 3 each week                               | Read from catalog (pre-resolved)         |
| `macro_genre`    | Resolved by Script 3 each week                               | Read from catalog (pre-resolved)         |
| `artists_found`  | Generated by Script 3 each week                              | Read from catalog (pre-resolved)         |

------

## ⚙️ GitHub Actions Workflow Analysis (`3_enrich-chart-data.yml`)

### Workflow Structure

```yaml
name: 3 - Enrich Chart Data

on:
  schedule:
    # Run every Monday at 14:00 UTC (after Script 2.2 completes)
    - cron: '00 14 * * 1'
  
  workflow_dispatch:

env:
  RETENTION_WEEKS: 78
```



### Job Steps

| Step | Name                            | Purpose                                              |
| :--- | :------------------------------ | :--------------------------------------------------- |
| 1    | 📚 Checkout repository           | Clone repository with full history                   |
| 2    | 🐍 Setup Python                  | Install Python 3.12 with pip cache                   |
| 3    | 📦 Install dependencies          | Install requirements (selenium, yt-dlp, etc.)        |
| 4    | 📁 Create directory structure    | Create input and output folders                      |
| 5    | 🔍 Verify song catalog exists    | Check `build_song.db` exists before proceeding (NEW) |
| 6    | 🚀 Run enrichment script         | Execute main enrichment script                       |
| 7    | ✅ Verify results                | List generated files and sizes                       |
| 8    | 📤 Commit and push changes       | Push changes to GitHub (with rebase)                 |
| 9    | 📦 Upload artifacts (on failure) | Upload debug data for troubleshooting                |
| 10   | 🧹 Clean old databases           | Delete databases older than 78 weeks                 |
| 11   | 📋 Final report                  | Generate execution summary                           |

### Detailed Steps

#### **1. 📚 Repository Checkout**

```yaml
- name: 📚 Checkout repository
  uses: actions/checkout@v4
  with:
    fetch-depth: 0
```



#### **2. 🐍 Setup Python**

```yaml
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



#### **4. 📁 Create Directory Structure**

```yaml
- name: 📁 Create directory structure
  run: |
    mkdir -p charts_archive/1_download-chart/databases
    mkdir -p charts_archive/3_enrich-chart-data
```



#### **5. 🔍 Verify Song Catalog Exists**

```yaml
- name: 🔍 Verify song catalog database exists
  run: |
    if [ ! -f "charts_archive/2_2.build-song-catalog/build_song.db" ]; then
      echo "❌ Song catalog database not found at charts_archive/2_2.build-song-catalog/build_song.db"
      echo "   Please ensure script 2_2 has run successfully before this workflow."
      exit 1
    fi
    echo "✅ Song catalog database found"
    SIZE=$(stat -c%s "charts_archive/2_2.build-song-catalog/build_song.db")
    echo "   Size: $((SIZE / 1024)) KB"
```



#### **6. 🚀 Run Enrichment Script**

```yaml
- name: 🚀 Run enrichment script
  run: |
    python scripts/3_enrich_chart_data.py
  env:
    YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
    GITHUB_ACTIONS: true
```



#### **7. ✅ Verify Results**

```yaml
- name: ✅ Verify results
  run: |
    echo "📊 Verifying execution results..."
    echo "📂 Contents of charts_archive/3_enrich-chart-data/:"
    ls -lah charts_archive/3_enrich-chart-data/
    
    echo -e "\n🗃️ Enriched databases:"
    ls -lah charts_archive/3_enrich-chart-data/*_enriched.db 2>/dev/null || echo "No enriched databases found"
```



#### **8. 📤 Commit and Push Changes**

```yaml
- name: 📤 Commit and push changes
  run: |
    git config --global user.name "github-actions[bot]"
    git config --global user.email "github-actions[bot]@users.noreply.github.com"
    git add charts_archive/3_enrich-chart-data/
    
    if git diff --cached --quiet; then
      echo "🔭 No changes to commit"
    else
      DATE=$(date +'%Y-%m-%d')
      WEEK=$(date +'%Y-W%W')
      git commit -m "🤖 Enriched chart data (catalog-linked) ${DATE} (Week ${WEEK}) [Automated]"
      git pull --rebase origin main
      git push origin HEAD:main
    fi
```



#### **9. 📦 Upload Artifacts (on failure)**

```yaml
- name: 📦 Upload artifacts (on failure)
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: enrich-debug-${{ github.run_number }}
    path: |
      scripts/3_enrich_chart_data.py.log
      charts_archive/3_enrich-chart-data/
    retention-days: 7
```



#### **10. 🧹 Clean Old Databases**

```yaml
- name: 🧹 Clean old databases
  run: |
    echo "🧹 Cleaning enriched databases older than ${{ env.RETENTION_WEEKS }} weeks..."
    find charts_archive/3_enrich-chart-data/ \
      -name "*_enriched.db" \
      -type f \
      -mtime +$((RETENTION_WEEKS * 7)) \
      -delete
```



#### **11. 📋 Final Report (UPDATED)**

```yaml
- name: 📋 Final report
  if: always()
  run: |
    echo "========================================"
    echo "🎵 ENRICHMENT EXECUTION REPORT"
    echo "========================================"
    echo "📅 Date: $(date)"
    echo "📌 Trigger: ${{ github.event_name }}"
    
    LATEST_DB=$(ls -t charts_archive/3_enrich-chart-data/*_enriched.db 2>/dev/null | head -1)
    if [ -f "$LATEST_DB" ]; then
      echo "✅ Latest enriched database: $(basename $LATEST_DB)"
      SIZE=$(stat -c%s "$LATEST_DB")
      echo "📊 Size: $((SIZE / 1024)) KB"
      
      if command -v sqlite3 &> /dev/null; then
        echo ""
        echo "📊 Database statistics:"
        TOTAL=$(sqlite3 "$LATEST_DB" "SELECT COUNT(*) FROM enriched_songs;" 2>/dev/null)
        LINKED=$(sqlite3 "$LATEST_DB" "SELECT COUNT(*) FROM enriched_songs WHERE id IS NOT NULL;" 2>/dev/null)
        MULTI=$(sqlite3 "$LATEST_DB" "SELECT COUNT(*) FROM enriched_songs WHERE artist_country = 'Multi-country';" 2>/dev/null)
        ERROR=$(sqlite3 "$LATEST_DB" "SELECT COUNT(*) FROM enriched_songs WHERE error != '';" 2>/dev/null)
        
        echo "   • Total songs: $TOTAL"
        echo "   • Linked to catalog: $LINKED ($(( LINKED * 100 / TOTAL ))%)"
        echo "   • Multi-country: $MULTI"
        echo "   • With errors: $ERROR"
      fi
    fi
```



### Cron Schedule

```cron
'00 14 * * 1'  # Minute 0, Hour 14, Any day of month, Any month, Monday
```
- **Execution**: Every Monday at 14:00 UTC
- **Offset**: 2 hours after Script 1 (12:00 UTC) and 45 minutes after Script 2.2 (13:15 UTC)
- **Purpose**: Allows Script 2.2 to complete and generate `build_song.db` before enrichment begins

### Execution Triggers

This workflow runs **only** on:

- **Scheduled execution**: Every Monday at 14:00 UTC
- **Manual execution**: Via `workflow_dispatch` from GitHub Actions UI

> **Note**: Automatic execution on `git push` has been disabled. Changes to scripts or the song catalog do not trigger this workflow automatically. To test changes, use manual dispatch or wait for the next scheduled run.

### Execution Flow Timeline

```text
Monday 12:00 UTC ─→ Script 1: Download charts
    ↓
13:00 UTC ─→ Script 2.1: Artist enrichment
    ↓
13:15 UTC ─→ Script 2.2: Build song catalog
    ↓
14:00 UTC ─→ Script 3: Chart enrichment (THIS WORKFLOW)
    ↓
15:00 UTC ─→ Script 4: Notebook generation
    ↓
Tuesday 12:00 UTC ─→ Script 5: Export to PDF + Drive
```

### Required Secrets

| Secret            | Purpose                                                      |
| :---------------- | :----------------------------------------------------------- |
| `YOUTUBE_API_KEY` | YouTube Data API v3 key for retrieving video metadata (Layer 1). Optional; script falls back to Selenium/yt-dlp without it. |

------

## 🚀 Installation and Local Setup

### Prerequisites

- Python 3.7 or higher (3.12 recommended)
- Git installed
- Internet access
- Weekly chart databases from Script 1 (`charts_archive/1_download-chart/databases/`)
- **Song catalog database from Script 2.2** (`charts_archive/2_2.build-song-catalog/build_song.db`) - **NEW REQUIREMENT**
- (Optional) YouTube Data API v3 key for faster metadata retrieval

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



#### **4. Set YouTube API Key (optional but recommended)**

```bash
# Linux/Mac
export YOUTUBE_API_KEY="your-api-key-here"

# Windows (Command Prompt)
set YOUTUBE_API_KEY=your-api-key-here

# Windows (PowerShell)
$env:YOUTUBE_API_KEY="your-api-key-here"
```



#### **5. Ensure Song Catalog Exists **

```bash
# Verify catalog from Script 2.2 exists
ls -la charts_archive/2_2.build-song-catalog/build_song.db
```



#### **6. Run Initial Test**

```bash
python scripts/3_enrich_chart_data.py
```



### Development Configuration

```bash
# Simulate GitHub Actions environment
export GITHUB_ACTIONS=true

# Run without interactive confirmation
export YOUTUBE_API_KEY="your-api-key"
```



------

## 📁 Generated File Structure

```text
charts_archive/
├── 1_download-chart/
│   ├── databases/
│   │   ├── youtube_charts_2025-W01.db
│   │   ├── youtube_charts_2025-W02.db
│   │   └── ...
│   └── backup/
├── 2_2.build-song-catalog/
│   └── build_song.db                       # Song catalog (required input)
└── 3_enrich-chart-data/                    # ← Output of this script
    ├── youtube_charts_2025-W01_enriched.db
    ├── youtube_charts_2025-W02_enriched.db
    └── ...
```



### Database Growth

| Metric            | Value                |
| :---------------- | :------------------- |
| Weekly songs      | 100                  |
| Size per database | 200-300 KB           |
| Annual storage    | 15-20 MB             |
| Retention         | 78 weeks (1.5 years) |

------

## 🔧 Customization and Configuration

### Adjustable Parameters in Script

```python
# In 3_enrich_chart_data.py
SLEEP_BETWEEN_VIDEOS = 0.1      # Pause between videos (seconds)
YT_DLP_RETRIES = 5               # Retries for yt-dlp
SELENIUM_TIMEOUT = 10            # Selenium timeout (seconds)
```



### Workflow Configuration

```yaml
# In 3_enrich-chart-data.yml
env:
  RETENTION_WEEKS: 78       # Weeks to retain databases

timeout-minutes: 60          # Total job timeout
```



### Adding New Artist Delimiters

```python
# In parse_artist_list()
separators = [
    '&', 'feat.', 'ft.', ',', ' y ', ' and ',
    ' with ', ' x ', ' vs ',           # Existing
    ' présentation ', ' en duo avec ', # French
    ' und ', ' & ',                    # German
    ' e ', ' com '                     # Portuguese
]
```



> **Note**: These delimiters are now only used for collaboration detection in video titles, not for country/genre resolution.

------

## 🐛 Troubleshooting

### Common Issues and Solutions

| Error                                 | Likely Cause          | Solution                                    |
| :------------------------------------ | :-------------------- | :------------------------------------------ |
| `Song catalog not found`              | Script 2.2 hasn't run | Run `2_2.build_song_catalog.py` first       |
| `No module named 'isodate'`           | Missing library       | `pip install isodate`                       |
| `Selenium: ChromeDriver not found`    | Chrome not installed  | `sudo apt-get install google-chrome-stable` |
| `No database found`                   | Script 1 hasn't run   | Run Script 1 first                          |
| `Sign in to confirm you're not a bot` | YouTube blocks yt-dlp | Set `YOUTUBE_API_KEY`                       |
| `API key not valid`                   | Invalid key           | Verify in Google Cloud Console              |
| `Quota exceeded`                      | Daily limit reached   | Script auto-falls back to Selenium          |
| `NULL id in enriched output`          | Song not in catalog   | Run Script 2.2 to add missing songs         |

### Performance Metrics

| Scenario          | Time         | Notes                |
| :---------------- | :----------- | :------------------- |
| With API Key      | ~2 minutes   | 0.3-0.8s per video   |
| No API (Selenium) | 5-7 minutes  | Depends on page load |
| No API (yt-dlp)   | 8-10 minutes | May be blocked       |

### Migration from Legacy Version

If you were using the previous version of Script 3 (with built-in collaboration weighting), follow these steps to migrate:

1. **Run Script 2.2** to build the song catalog with resolved country/genre
2. **Update your workflow** to ensure Script 2.2 runs before Script 3
3. **Remove** any custom modifications to `COUNTRY_TO_CONTINENT` or `GENRE_HIERARCHY` from Script 3
4. **Add** those customizations to Script 2.2 instead
5. **Re-run** Script 3 – it will now read pre-resolved values from the catalog

------

## 📄 License and Attribution

- **License**: MIT
- **Author**: Alfonso Droguett
  - 🔗 **LinkedIn:** [Alfonso Droguett](https://www.linkedin.com/in/adroguetth/)
  - 🌐 **Web portfolio:** [adroguett-portfolio.cl](https://www.adroguett-portfolio.cl/)
  - 📧 **Email:** adroguett.consultor@gmail.com
- **Data Sources**:
  - YouTube Data API v3
  - YouTube website (via Selenium/yt-dlp)
  - Song catalog from Script 2.2

------

## 🤝 Contribution

1. Report issues with complete logs
2. Propose improvements with use cases
3. Add new video type detection patterns
4. Improve collaboration detection patterns
5. Maintain compatibility with existing database schema

------

**⭐ If you find this project useful, please consider starring it on GitHub!**
