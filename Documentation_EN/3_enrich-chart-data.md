# Script 3: YouTube Chart Enrichment System

![MIT License](https://img.shields.io/badge/license-MIT-9ecae1?style=flat-square&logo=open-source-initiative&logoColor=white) ![Web Scraping](https://img.shields.io/badge/Web-Scraping-orange?style=flat-square)
![Data Enrichment](https://img.shields.io/badge/Data-Enrichment-blue?style=flat-square)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=flat-square&logo=selenium&logoColor=white)
![yt-dlp](https://img.shields.io/badge/yt--dlp-FF6F61?style=flat-square&logo=youtube&logoColor=white)
![YouTube API](https://img.shields.io/badge/YouTube_API-FF0000?style=flat-square&logo=youtube&logoColor=white) 


## 📥 Quick Downloads
| Document                | Format                                                     |
| ------------------------- | ------------------------------------------------------------ |
| **🇬🇧 English Documentation** | [PDF](https://drive.google.com/file/d/1XGEx2fRBCpOhU5BfY_YjlKm6zmI41RpB/view?usp=drive_link) |
| **🇪🇸 Spanish Documentation** | [PDF](https://drive.google.com/file/d/1tSFjf_gQQeArdE4n5DLL2I2G_MJW6vE3/view?usp=drive_link) |

## 📋 General Description

This script is the **third component** of the YouTube Charts intelligence system. It takes the weekly chart database (from Script 1) and the artist metadata database (from Script 2), then **enriches each song with detailed YouTube video metadata** using an intelligent three-layer fallback system.

The script extracts video duration, likes, comments, upload date, audio language, regional restrictions, and classifies video type (official/lyric/live), channel type (VEVO/Topic/Artist), and collaboration patterns. It also resolves country and genre for multi-artist tracks using a weighted collaboration algorithm.

### Key Features

- **🔄 3-Layer Retrieval System**: YouTube API (priority) → Selenium → yt-dlp (last resort) for maximum reliability
- **⚡ Optimized Performance**: Processes 100 songs in ~2 minutes using YouTube API (vs. 8+ minutes with pure yt-dlp)
- **👥 Collaboration Weighting System**: Intelligent algorithm that determines country and genre when multiple artists are involved
- **🗺️ Country-Based Cultural Hierarchies**: Ordered genre lists that reflect local importance (e.g., K-Pop first in South Korea)
- **📝 Video Metadata Detection**: Identifies whether a video is official, lyric video, live performance, or remix/special version
- **📺 Channel Classification**: Detects VEVO, Topic, Label/Studio, Artist Channel, and more
- **🔄 Automatic Updates**: Selects the most recent charts database and generates its enriched version
- **🔧 CI/CD Optimized**: Specifically designed to run in GitHub Actions with zero manual intervention

------

## 📊 Process Flow Diagram

### **Legend**

| Color        | Type     | Description                                              |
| :----------- | :------- | :------------------------------------------------------- |
| 🔵 Blue       | Input    | Source data (chart database + artist database)           |
| 🟠 Orange     | Process  | Internal processing logic                                |
| 🟣 Purple     | API      | External service queries (YouTube API, Selenium, yt-dlp) |
| 🟢 Green      | Storage  | SQLite databases, temporary files                        |
| 🔴 Red        | Decision | Conditional branching points                             |
| 🟢 Dark Green | Output   | Enriched database                                        |

### **Diagram 1: Main Flow Overview**
<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/refs/heads/main/Documentation_EN/Diagrams/3_enrich_chart_data/1.png" alt="Diagram 1: Main Flow Overview" width="500">

This diagram shows the **high-level pipeline** of the entire system:

1. **Input**: Locates the most recent chart database (`youtube_charts_YYYY-WXX.db`) from Script 1
2. **Download Artist DB**: Fetches `artist_countries_genres.db` from GitHub (temporary file)
3. **Build Lookup**: Creates in-memory dictionary `{normalized_name: (country, genre)}` for O(1) lookups
4. **Load Songs**: Reads 100 songs from `chart_data` table
5. **Create Output Table**: Sets up `enriched_songs` table with 25 columns + indexes
6. **Per-Song Loop**: For each song (1 to 100):
   - **Extract Artists**: Splits names using delimiters (&, feat., ft., etc.)
   - **Lookup Artist Data**: Queries dictionary for each artist's country/genre
   - **Collaboration Resolution**: Applies weighted algorithm to determine final country/genre
   - **Fetch YouTube Metadata**: 3-layer fallback (API → Selenium → yt-dlp)
   - **Classify Video**: Detects type, channel type, collaboration, upload season
   - **Insert Row**: Saves enriched data to output database
7. **Cleanup**: Removes temporary artist database file
8. **Output**: Enriched database ready for Script 4 (notebook generation)

### **Diagram 2: 3-Layer Metadata Retrieval System**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/refs/heads/main/Documentation_EN/Diagrams/3_enrich_chart_data/2.png" alt="Diagram 2: 3-Layer Metadata Retrieval" width="500">

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

### **Diagram 3: Collaboration Weighting System**

<img src="https://raw.githubusercontent.com/adroguetth/Music-Charts-Intelligence/refs/heads/main/Documentation_EN/Diagrams/3_enrich_chart_data/3.png" alt="Diagram 3: Collaboration Weighting System" width="500">

This diagram shows the **intelligent decision engine** for multi-artist tracks:

1. **Input**: Receives list of artists with their countries and genres from the lookup dictionary

2. **Single Artist Check**: If only 1 artist → returns that artist's country and genre immediately ✅

3. **Filter Known Artists**: Remove artists with NULL/Unknown country

4. **Count Countries**: Calculate frequency of each country among known artists

5. **Apply Decision Rules**:

   | Rule                                                  | Condition                       | Result                                               |
   | :---------------------------------------------------- | :------------------------------ | :--------------------------------------------------- |
   | **Rule 1 – Absolute Majority**                        | >50% from same country          | Return majority country + infer genre from hierarchy |
   | **Rule 2 – Exact 50/50 Split**                        | =50% with exactly 2 countries   | Return majority country + infer genre                |
   | **Rule 3 – Exact 50/50 Split (3+ countries)**         | =50% with 3+ countries          | Return "Multi-country" + "Multi-genre"               |
   | **Rule 4 – Relative Majority (<50%)**                 | Same continent and ≤2 countries | Return majority country + infer genre                |
   | **Rule 5 – Relative Majority (different continents)** | <50% with different continents  | Return "Multi-country" + "Multi-genre"               |
   | **Rule 6 – Fallback**                                 | No known artists                | Return "Unknown" + "Pop"                             |

6. **Genre Inference** (`infer_genre_by_country`):

   - Retrieves country's genre hierarchy from `GENRE_HIERARCHY`
   - If a single genre has >50% among artists → use it
   - Otherwise, pick the highest-ranked genre present in known genres
   - Fallback to hierarchy's first genre

7. **Output**: Returns final `(country, genre)` tuple for the track

------

## 🔍 Detailed Analysis of `3_enrich_chart_data.py`

### Code Structure

#### **1. Configuration and Paths**

```python
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
INPUT_DB_DIR = PROJECT_ROOT / "charts_archive" / "1_download-chart" / "databases"
URL_ARTIST_DB = "https://github.com/adroguetth/Music-Charts-Intelligence/raw/refs/heads/main/charts_archive/2_countries-genres-artist/artist_countries_genres.db"
OUTPUT_DIR = PROJECT_ROOT / "charts_archive" / "3_enrich-chart-data"
```

The script integrates the two previous components:

| Path            | Purpose                                                      |
| :-------------- | :----------------------------------------------------------- |
| `INPUT_DB_DIR`  | Input: Weekly chart databases from Script 1                  |
| `URL_ARTIST_DB` | Reference: Artist database from Script 2 (downloaded temporarily) |
| `OUTPUT_DIR`    | Output: Enriched databases for Script 4                      |

#### **2. Core Reference Tables**

**Country-to-Continent Map (196 countries):**

```python
COUNTRY_TO_CONTINENT = {
    "South Korea": "Asia", "Japan": "Asia", "China": "Asia",
    "United States": "America", "Canada": "America",
    "United Kingdom": "Europe", "France": "Europe",
    "Nigeria": "Africa", "South Africa": "Africa",
    "Australia": "Oceania", "New Zealand": "Oceania",
    # ... 196 countries total
}
```

**Genre Hierarchies by Country (local cultural priority):**

```python
GENRE_HIERARCHY = {
    "South Korea": ["K-Pop/K-Rock", "Hip-Hop/Rap", "Rock", "Ballad", "Trot"],
    "Brazil": ["Sertanejo", "Funk Brasileiro", "Reggaeton/Latin Trap", "Pop", "Rock"],
    "Nigeria": ["Afrobeats", "Hip-Hop/Rap", "Gospel", "Jùjú", "Fuji"],
    # ... 100+ countries with custom hierarchies
}
```

#### **3. 3-Layer Metadata Retrieval System**

```python
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

#### **4. Collaboration Weighting System**

```python
def resolve_country_and_genre(artists_info: list) -> tuple:
    """
    Apply the collaboration weight algorithm to determine a single
    country and genre for a potentially multi-artist track.
    
    Decision tree:
        Rule 1 – Absolute majority (>50%): assign majority country + its genre
        Rule 2 – Exact 50/50 split (2 countries): assign the majority country
        Rule 3 – Exact 50/50 split (3+ countries): Multi-country / Multi-genre
        Rule 4 – Relative majority (<50%): assign if same continent and ≤2 countries
        Rule 5 – Otherwise: Multi-country / Multi-genre
    """
```

**Example scenarios:**

| Scenario | Artists                        | Countries   | Result                              |
| :------- | :----------------------------- | :---------- | :---------------------------------- |
| 1        | BTS (alone)                    | South Korea | South Korea, K-Pop/K-Rock           |
| 2        | ROSÉ (SK) + Bruno Mars (USA)   | 2 distinct  | Multi-country, Multi-genre          |
| 3        | Bad Bunny (PR) + J Balvin (CO) | 2 distinct  | Multi-country, Multi-genre          |
| 4        | 3 US + 1 UK artists            | 75% US      | United States, Pop (from hierarchy) |
| 5        | All unknown                    | None        | Unknown, Pop                        |

#### **5. Text Classifiers**

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

#### **6. Artist Name Processing**

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

#### **7. Output Database Schema**

```sqlite
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
);

-- Indexes for query optimization
CREATE INDEX idx_country ON enriched_songs(artist_country);
CREATE INDEX idx_genre ON enriched_songs(macro_genre);
CREATE INDEX idx_upload_date ON enriched_songs(upload_date);
CREATE INDEX idx_error ON enriched_songs(error);
```

---

## ⚙️ GitHub Actions Workflow Analysis (`3_enrich-chart-data.yml`)

### Workflow Structure

```yaml
name: 3- Enrich Chart Data

on:
  schedule:
    # Run every Monday at 14:00 UTC (2 hours after download)
    - cron: '0 14 * * 1'
  
  # Allow manual workflow execution
  workflow_dispatch:
  
  # Trigger on push to main branch if enrichment script changes
  push:
    branches:
      - main
    paths:
      - 'scripts/3_enrich_chart_data.py'
      - '.github/workflows/3_enrich-chart-data.yml'

env:
  # Number of weeks to retain enriched databases (1.5 years)
  RETENTION_WEEKS: 78
```

### Job Steps

| Step | Name                            | Purpose                                       |
| :--- | :------------------------------ | :-------------------------------------------- |
| 1    | 📚 Checkout repository           | Clone repository with full history            |
| 2    | 🐍 Setup Python                  | Install Python 3.12 with pip cache            |
| 3    | 📦 Install dependencies          | Install requirements (selenium, yt-dlp, etc.) |
| 4    | 📁 Create directory structure    | Create input and output folders               |
| 5    | 🚀 Run enrichment script         | Execute main enrichment script                |
| 6    | ✅ Verify results                | List generated files and sizes                |
| 7    | 📤 Commit and push changes       | Push changes to GitHub (with rebase)          |
| 8    | 📦 Upload artifacts (on failure) | Upload debug data for troubleshooting         |
| 9    | 🧹 Clean old databases           | Delete databases older than 78 weeks          |
| 10   | 📋 Final report                  | Generate execution summary                    |

### Detailed Steps

#### **1. 📚 Repository Checkout**

```yaml
- name: 📚 Checkout repository
  uses: actions/checkout@v4
  with:
    fetch-depth: 0
```

#### **2. 🐍 Setup Python**

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

#### **4. 📁 Create Directory Structure**

```yaml
- name: 📁 Create directory structure
  run: |
    mkdir -p charts_archive/1_download-chart/databases
    mkdir -p charts_archive/3_enrich-chart-data
```

#### **5. 🚀 Run Enrichment Script**

```yaml
- name: 🚀 Run enrichment script
  run: |
    python scripts/3_enrich_chart_data.py
  env:
    YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
    GITHUB_ACTIONS: true
```

#### **6. ✅ Verify Results**

```yaml
- name: ✅ Verify results
  run: |
    echo "📊 Verifying execution results..."
    echo "📂 Contents of charts_archive/3_enrich-chart-data/:"
    ls -lah charts_archive/3_enrich-chart-data/
```

#### **7. 📤 Commit and Push Changes**

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
      git commit -m "🤖 Enriched chart data ${DATE} (Week ${WEEK}) [Automated]"
      git pull --rebase origin main
      git push origin HEAD:main
    fi
```

#### **8. 📦 Upload Artifacts (on failure)**

```yaml
- name: 📦 Upload artifacts (on failure)
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: enrich-debug-${{ github.run_number }}
    path: |
      charts_archive/3_enrich-chart-data/
    retention-days: 7
```

#### **9. 🧹 Clean Old Databases**

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

#### **10. 📋 Final Report**

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
    fi
```

### Cron Schedule

```cron
'0 14 * * 1'  # Minute 0, Hour 14, Any day of month, Any month, Monday
```

- **Execution**: Every Monday at 14:00 UTC
- **Offset**: 2 hours after Script 1 (12:00 UTC) and 1 hour after Script 2 (13:00 UTC)
- **Purpose**: Allows previous workflows to complete before enrichment begins

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

#### **5. Run Initial Test**

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

---

## 📁 Generated File Structure

```text
charts_archive/
├── 1_download-chart/
│   ├── databases/
│   │   ├── youtube_charts_2025-W01.db
│   │   ├── youtube_charts_2025-W02.db
│   │   └── ...
│   └── backup/
├── 2_countries-genres-artist/
│   └── artist_countries_genres.db       # Artist database (downloaded temporarily)
└── 3_enrich-chart-data/                  # ← Output of this script
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

### Expanding Genre Hierarchies

```python
# In GENRE_HIERARCHY
"New Country": [
    "Primary Genre",     # Priority 1
    "Secondary Genre",   # Priority 2
    "Tertiary Genre"     # Priority 3
]
```

---

## 🐛 Troubleshooting

### Common Issues and Solutions

| Error                                 | Likely Cause          | Solution                                    |
| :------------------------------------ | :-------------------- | :------------------------------------------ |
| `No module named 'isodate'`           | Missing library       | `pip install isodate`                       |
| `Selenium: ChromeDriver not found`    | Chrome not installed  | `sudo apt-get install google-chrome-stable` |
| `No database found`                   | Script 1 hasn't run   | Run Script 1 first                          |
| `Sign in to confirm you're not a bot` | YouTube blocks yt-dlp | Set `YOUTUBE_API_KEY`                       |
| `API key not valid`                   | Invalid key           | Verify in Google Cloud Console              |
| `Quota exceeded`                      | Daily limit reached   | Script auto-falls back to Selenium          |

### Performance Metrics

| Scenario          | Time         | Notes                |
| :---------------- | :----------- | :------------------- |
| With API Key      | ~2 minutes   | 0.3-0.8s per video   |
| No API (Selenium) | 5-7 minutes  | Depends on page load |
| No API (yt-dlp)   | 8-10 minutes | May be blocked       |

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
  - Artist database from Script 2

------

## 🤝 Contribution

1. Report issues with complete logs
2. Propose improvements with use cases
3. Add new genre hierarchies for missing countries
4. Improve collaboration detection patterns
5. Maintain compatibility with existing database schema

------

**⭐ If you find this project useful, please consider starring it on GitHub!**
