# 🎵 Music Charts Intelligence System
**🇪🇸 ¿Buscas la versión en español?** → [README.es.md](README.es.md)

![WIP](https://img.shields.io/badge/status-WIP-fdd0a2?style=flat-square) 

![MIT License](https://img.shields.io/badge/license-MIT-9ecae1?style=flat-square&logo=open-source-initiative&logoColor=white) ![Automation](https://img.shields.io/badge/Automation-GitHub_Actions-blue?style=flat-square) ![Web Scraping](https://img.shields.io/badge/Web-Scraping-orange?style=flat-square) ![Data Enrichment](https://img.shields.io/badge/Data-Enrichment-blue?style=flat-square)

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white) ![Playwright](https://custom-icon-badges.demolab.com/badge/Playwright-2EAD33?logo=playwright&logoColor=white&style=flat-square) ![Selenium](https://img.shields.io/badge/Selenium-43b02a?style=flat-square&logo=selenium&logoColor=white) ![yt-dlp](https://img.shields.io/badge/yt--dlp-FF0000?style=flat-square&logo=youtube&logoColor=white) ![YouTube API](https://img.shields.io/badge/YouTube_API-ff0000?style=flat-square&logo=youtube&logoColor=white) ![MusicBrainz](https://img.shields.io/badge/MusicBrainz-BA478F?style=flat-square&logo=musicbrainz&logoColor=white) ![Wikipedia API](https://img.shields.io/badge/Wikipedia-000000?style=flat-square&logo=wikipedia&logoColor=white) ![Wikidata](https://img.shields.io/badge/Wikidata-990000?style=flat-square&logo=wikidata&logoColor=white) [![DeepSeek](https://custom-icon-badges.demolab.com/badge/DeepSeek-4D6BFF?logo=deepseek&logoColor=white&style=flat-square)](https://deepseek.com) ![Jupyter](https://img.shields.io/badge/Jupyter-f37626?style=flat-square&logo=jupyter&logoColor=white) ![Streamlit](https://img.shields.io/badge/Streamlit-ff4b4b?style=flat-square&logo=streamlit&logoColor=white)

A fully automated, end-to-end pipeline that downloads YouTube's weekly music charts, enriches every artist with geographic and genre metadata, and then augments each chart entry with deep YouTube video metadata — all running on GitHub Actions, zero manual intervention required.


## 📥 Documentation

| Script                     | Purpose                                                      | English Docs                                                 | Spanish Docs                                                 |
| -------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **1_download.py**          | Downloads weekly YouTube Charts (100 songs) into SQLite      | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/1_download.md) · [PDF](https://drive.google.com/file/d/11ANLX6PbK_eIzvHLPqL1rm9NY9rOshhD/view?usp=sharing) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/1_download.md) · [PDF](https://drive.google.com/file/d/1SdLvJnxcKxmQYmLlwoYttHr2Izud4iE5/view?usp=sharing) |
| **2_build_artist_db.py**   | Enriches artists with country + genre via MusicBrainz, Wikipedia, Wikidata | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/2_build_artist_db.md) · [PDF](https://drive.google.com/file/d/1viUAxZ7k-qeYYbyvZf2OaP20AfLOgKh2/view?usp=drive_link) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/2_build_artist_db.md) · [PDF](https://drive.google.com/file/d/1WBHBreKeVToTBygSyCuYsHQUr_zSl3BT/view?usp=drive_link) |
| **3_enrich_chart_data.py** | Adds YouTube video metadata to every chart entry (3-layer system) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/3_enrich-chart-data.md) · [PDF](https://drive.google.com/file/d/1XGEx2fRBCpOhU5BfY_YjlKm6zmI41RpB/view?usp=drive_link)                                             | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/3_enrich-chart-data.md) · [PDF](https://drive.google.com/file/d/1tSFjf_gQQeArdE4n5DLL2I2G_MJW6vE3/view?usp=sharing)                                                              |

> Each script's README contains detailed code analysis, configuration options, and troubleshooting guides. This document covers the system as a whole.

## 🗂️ System Architecture
 
The pipeline processes data in three distinct stages, each building on the previous one's output:
 
```
YouTube Charts (web)
        │
        ▼
┌───────────────────┐
│   Script 1        │  → Raw chart data (100 songs/week)
│   1_download.py   │    Rank, Track, Artist, Views, URL
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Script 2        │  → Artist reference database
│ 2_build_artist_db │    Artist → Country + Genre
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Script 3        │  → Fully enriched chart entries
│ 3_enrich_chart_   │    25 fields per song
│      data.py      │
└───────────────────┘
        │
        ▼
   SQLite Database
   (ready for analysis)
```
 
### Data Flow Between Scripts
 
| Stage | Input | Output | Records |
| :---- | :---- | :----- | :------ |
| Script 1 | YouTube Charts webpage | `youtube_charts_YYYY-WXX.db` | 100 songs/week |
| Script 2 | Script 1's database (artist names) | `artist_countries_genres.db` | Grows ~10–50 artists/week |
| Script 3 | Script 1's DB + Script 2's DB | `youtube_charts_YYYY-WXX_enriched.db` | 100 enriched rows/week |
 
# ⚙️ Automation Schedule
 
All three scripts are orchestrated by GitHub Actions and run automatically every Monday:
 
| Workflow | Schedule (UTC) | Trigger Logic | Timeout |
| :------- | :------------- | :------------ | :------ |
| `1_download-chart.yml` | Monday 12:00 | Cron + manual + push | 30 min |
| `2_update-artist-db.yml` | Monday 13:00 | Cron + after Script 1 | 60 min |
| `3_enrich-chart-data.yml` | Monday 14:00 | Cron + after Script 2 | 60 min |
 
The 1-hour gaps between each workflow ensure the previous step has finished before the next one begins. Each workflow commits its output directly back to the repository — no external storage needed.


### Required Secrets
 
| Secret | Used By | Purpose |
| :----- | :------ | :------ |
| `YOUTUBE_API_KEY` | Script 3 | YouTube Data API v3 for video metadata (Layer 1) |
 
Scripts 1 and 2 require no API keys. Script 3 works without a key but falls back to slower methods (Selenium, yt-dlp).
 
 
## 🔬 How Each Script Works
 
### Script 1 — Download YouTube Charts
 
Runs every Monday and scrapes the top 100 songs from YouTube Charts using Playwright with a headless Chromium browser. It implements multiple CSS selector strategies to find the download button, hides automation fingerprints with custom headers and JavaScript injection, and falls back to sample data if YouTube's interface changes.
 
Each weekly run produces a new, versioned SQLite database. Before writing, it creates a temporary backup of the existing file to prevent data loss. Old databases are cleaned up automatically based on a configurable retention period (default: 52 weeks).
 
**Key technical details:**
- Anti-detection: custom user agent, hidden `navigator.webdriver`, realistic viewport
- 3 fallback selectors for the download button (`#download-button`, `aria-label`, text)
- Backup naming: `backup_YYYY-WXX_YYYYMMDD_HHMMSS.db`
- Fallback data: 100 synthetic records with identical structure to real data
 
 
### Script 2 — Build Artist Database
 
Takes every unique artist name from Script 1's database and enriches it with country of origin and primary music genre. For each artist, it generates up to 15 name variations (removing accents, stripping prefixes, etc.) and queries them across three external knowledge bases in a cascading order.
 
**Country detection** uses a curated dictionary of 30,000+ geographic terms (cities, demonyms, regional references) to extract location signals from API responses. It checks MusicBrainz first (structured, reliable), then Wikipedia English (summary and infobox), then Wikipedia in priority languages (chosen based on detected script or known country), and finally Wikidata (properties P27 and P19).
 
**Genre detection** collects candidates from MusicBrainz tags and Wikidata's P136 property, then applies a weighted voting system across 200+ macro-genres and 5,000+ subgenre mappings. Country-specific priority bonuses are applied (e.g., K-Pop gets a 2.0× multiplier for South Korean artists).
 
The script never overwrites existing data — it only fills in missing fields. This makes re-runs safe and incremental.
 
**Key technical details:**
- 15 name variations per artist (e.g., "The Beatles" → "Beatles", "beatles", etc.)
- In-memory cache prevents duplicate API calls within a session
- Script detection (Cyrillic, Hangul, Devanagari, Arabic, etc.) guides Wikipedia language selection
- Weighted voting: MusicBrainz weight > Wikipedia weight > Wikidata weight
- Country-specific genre bonuses for 50+ countries
 
 
### Script 3 — Enrich Chart Data
 
Takes Script 1's latest chart database and Script 2's artist database and produces a fully enriched output with 25 fields per song. The most technically complex script in the system, it retrieves YouTube video metadata using a 3-layer strategy that always tries the fastest method first.
 
**Layer 1 — YouTube Data API v3** (0.3–0.8s/video): Retrieves exact duration, like count, comment count, audio language, regional restrictions, and upload date. Used when a valid API key is available and quota remains.
 
**Layer 2 — Selenium** (3–5s/video): Launches a headless Chrome browser and extracts metadata directly from the YouTube player. Used as fallback when the API is unavailable or quota is exhausted.
 
**Layer 3 — yt-dlp** (2–4s/video): Tries multiple client configurations (Android, iOS, Web) with retry delays to avoid bot detection. Used as a last resort.
 
Beyond video metadata, the script also classifies each entry using text analysis: it detects whether a video is official, a lyric video, a live performance, or a remix; classifies the channel type (VEVO, Topic, Label/Studio, Artist Channel); and resolves country/genre for collaborations using a weighted majority algorithm.
 
**Key technical details:**
- 196-country continent map for resolving multi-country collaborations
- Collaboration resolution: absolute majority (>50%) → relative majority → Multicountry
- 100+ country-specific genre hierarchies for tiebreaking
- Detects collaborations via regex patterns (feat., ft., &, x, with, con)
- Channel type detection via keyword matching
- Upload season (Q1–Q4) derived from upload date
 
 
## 📁 Repository Structure
```text
Music-Charts-Intelligence/
├── .github/workflows/
│   ├── 1_download-chart.yml
│   ├── 2_update-artist-db.yml
│   └── 3_enrich-chart-data.yml
│
├── scripts/
│   ├── 1_download.py
│   ├── 2_build_artist_db.py
│   └── 3_enrich_chart_data.py
│
├── charts_archive/
│   ├── 1_download-chart/
│   │   ├── latest_chart.csv              # Most recent chart (always updated)
│   │   ├── databases/
│   │   │   ├── youtube_charts_2025-W01.db
│   │   │   ├── youtube_charts_2025-W02.db
│   │   │   └── ...                       # One file per week
│   │   └── backup/
│   │       └── ...                       # Temporary pre-update backups
│   │
│   ├── 2_countries-genres-artist/
│   │   └── artist_countries_genres.db    # Cumulative artist enrichment DB
│   │
│   └── 3_enrich-chart-data/
│       ├── youtube_charts_2025-W01_enriched.db
│       ├── youtube_charts_2025-W02_enriched.db
│       └── ...                           # One enriched DB per week
│
├── Documentation_EN/
│   ├── 1_download.md
│   ├── 2_build_artist_db.md
│   └── 3_enrich_chart_data.md
│
├── Documentation_ES/
│   ├── 1_download.md
│   ├── 2_build_artist_db.md
│   └── 3_enrich_chart_data.md
│
├── requirements.txt
├── .gitignore
│
├── README.es.md
└── README.md
```
### Data Retention Policy
 
| Data | Retention | Configurable |
| :--- | :-------- | :----------- |
| Weekly chart databases (Script 1) | 52 weeks | `RETENTION_WEEKS` in script |
| Backup files (Script 1) | 7 days | `RETENTION_DAYS` in script |
| Enriched databases (Script 3) | 78 weeks | `RETENTION_WEEKS` in workflow |
| Artist database (Script 2) | Permanent (cumulative) | — |
 
## 🗄️ Database Schemas
 
### Script 1 Output — `chart_data` table
 
| Column | Type | Description |
| :----- | :--- | :---------- |
| `Rank` | INTEGER | Chart position (1–100) |
| `Previous Rank` | INTEGER | Position in previous week |
| `Track Name` | TEXT | Song title |
| `Artist Names` | TEXT | Artist(s), may include collaborations |
| `Periods on Chart` | INTEGER | Number of weeks on chart |
| `Views` | INTEGER | Total view count |
| `Growth` | TEXT | Week-over-week growth percentage |
| `YouTube URL` | TEXT | Direct video link |
| `download_date` | TEXT | Date of download |
| `download_timestamp` | TEXT | Full timestamp |
| `week_id` | TEXT | ISO week identifier (e.g., `2025-W11`) |

### Script 2 Output — `artist` table
 
| Column | Type | Description | Example |
| :----- | :--- | :---------- | :------ |
| `name` | TEXT (PK) | Canonical artist name | `"BTS"` |
| `country` | TEXT | Country of origin | `"South Korea"` |
| `macro_genre` | TEXT | Primary genre | `"K-Pop/K-Rock"` |

### Script 3 Output — `enriched_songs` table (25 fields)
 
| Category | Fields |
| :------- | :----- |
| **Identifiers** | `rank`, `artist_names`, `track_name` |
| **Chart Metrics** | `periods_on_chart`, `views`, `youtube_url` |
| **Video Metadata** | `duration_s`, `duration_ms`, `upload_date`, `likes`, `comment_count`, `audio_language` |
| **Video Flags** | `is_official_video`, `is_lyric_video`, `is_live_performance`, `is_special_version` |
| **Context** | `upload_season`, `channel_type`, `is_collaboration`, `artist_count`, `region_restricted` |
| **Enrichment** | `artist_country`, `macro_genre`, `artists_found` |
| **Control** | `error`, `processing_date` |
 
## 🚀 Quick Start
 
### Prerequisites
 
- Python 3.7 or higher (3.12 recommended)
- Git
- Internet access
- YouTube Data API v3 key (optional — only needed for Script 3 Layer 1)
 
### Installation
 
```bash
# Clone the repository
git clone https://github.com/adroguetth/Music-Charts-Intelligence
cd Music-Charts-Intelligence
 
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate       # Linux/Mac
# venv\Scripts\activate        # Windows
 
# Install all dependencies
pip install -r requirements.txt
 
# Install Playwright browser (Script 1 only)
python -m playwright install chromium
python -m playwright install-deps  # Linux only
```
 
### Running the Scripts
 
```bash
# Step 1: Download this week's YouTube Charts
python scripts/1_download.py
 
# Step 2: Enrich the artist database
python scripts/2_build_artist_db.py
 
# Step 3: Enrich chart entries with YouTube metadata
export YOUTUBE_API_KEY="your-api-key"   # Optional but recommended
python scripts/3_enrich_chart_data.py
```
 
Each script can be run independently. Scripts 2 and 3 depend on Script 1's output existing, and Script 3 also uses Script 2's artist database if available.
 
### Environment Variables
 
```bash
# Simulate GitHub Actions environment (disables interactive prompts)
export GITHUB_ACTIONS=true
 
# YouTube Data API v3 key (Script 3, Layer 1)
export YOUTUBE_API_KEY="your-key-here"
 
# Playwright visual debugging (Script 1)
export PWDEBUG=1
```
 
## 📊 Output Sample
 
After a full pipeline run, a typical weekly output looks like this:
 
```
✅ Script 1: YouTube Chart Update 2025-W11 — 100 songs downloaded
✅ Script 2: Artist database updated — 23 new artists enriched (2,346 total)
✅ Script 3: Chart enriched — 100 songs processed in 2m 04s
 
📊 Weekly Stats (2025-W11):
   • Distinct countries detected:    28
   • Distinct genres detected:       15
   • Multi-country collaborations:   24 (24.0%)
   • Official music videos:          61 (61.0%)
   • API success rate (Script 3):    98%
```
 
## 📈 Performance Reference
 
| Script | Typical Runtime | Bottleneck |
| :----- | :-------------- | :--------- |
| Script 1 | 2–5 minutes | Page load / Playwright startup |
| Script 2 | 10–30 minutes | API rate limits (MusicBrainz, Wikipedia) |
| Script 3 (with API key) | ~2 minutes | YouTube API quota |
| Script 3 (Selenium only) | ~5–7 minutes | Headless browser per video |
| Script 3 (yt-dlp only) | ~8–10 minutes | Anti-bot delays |
 
## 🔧 Configuration Reference
 
### Script 1 — `1_download.py`
 
```python
RETENTION_DAYS = 7        # Days to keep backup files
RETENTION_WEEKS = 52      # Weeks to keep weekly databases
TIMEOUT = 120000          # Playwright browser timeout (ms)
```
 
### Script 2 — `2_build_artist_db.py`
 
```python
MIN_CANDIDATES = 3        # Min genre candidates before querying Wikipedia
RETRY_DELAY = 0.5         # Delay between API calls (seconds)
DEFAULT_TIMEOUT = 10      # API request timeout (seconds)
```
 
### Script 3 — `3_enrich_chart_data.py`
 
```python
SLEEP_BETWEEN_VIDEOS = 0.1    # Pause between videos (seconds)
YT_DLP_RETRIES = 5             # yt-dlp retry attempts
SELENIUM_TIMEOUT = 10          # Selenium page load timeout (seconds)
```
 
### Workflow-level (`*.yml` files)
 
```yaml
# Script 1
timeout-minutes: 30
 
# Script 2
timeout-minutes: 60
env:
  RETENTION_DAYS: 30
 
# Script 3
timeout-minutes: 60
env:
  RETENTION_WEEKS: 78
```
 
## 🧩 Extending the System
 
### Adding a New Artist Delimiter (Script 2 & 3)
 
```python
separators = [
    '&', 'feat.', 'ft.', ',', ' y ', ' and ', ' with ', ' x ', ' vs ',
    ' présente ',      # French
    ' und ',           # German
    ' e ', ' com '     # Portuguese
]
```
 
### Adding a New Genre Mapping (Script 2)
 
```python
# In GENRE_MAPPINGS
'new subgenre name': ('Macro-Genre', 'subgenre')
```
 
### Adding a New Country Genre Hierarchy (Script 3)
 
```python
# In GENRE_HIERARCHY
"Country Name": [
    "Priority Genre 1",   # Selected first in tiebreaks
    "Priority Genre 2",
    "Priority Genre 3"
]
```
 
### Adjusting Country Genre Bonuses (Script 2)
 
```python
# In COUNTRY_GENRE_PRIORITY
"Country Name": [
    "Priority Genre 1",   # 2.0× multiplier
    "Priority Genre 2",   # 1.5× multiplier
    "Priority Genre 3"    # 1.2× multiplier
]
```
 
## 🐛 Common Issues
 
| Error | Likely Cause | Solution |
| :---- | :----------- | :------- |
| `Playwright browsers not installed` | Missing Chromium binary | `python -m playwright install chromium` |
| `No chart databases found` | Script 1 hasn't run yet | Run Script 1 first |
| `Sign in to confirm you're not a bot` | yt-dlp blocked by YouTube | Set `YOUTUBE_API_KEY`; script auto-falls back to Selenium |
| `Quota exceeded` | YouTube API daily limit hit | Script auto-falls back to Selenium/yt-dlp |
| `API key not valid` | Invalid or restricted key | Verify key in Google Cloud Console |
| `No module named 'isodate'` | Missing dependency | `pip install isodate` |
| Very slow Script 3 (>10 min) | API key missing or failing | Check `YOUTUBE_API_KEY` is set and valid |
 
For detailed troubleshooting, see the individual script documentation linked in the table at the top of this README.
 
## 🧪 Known Limitations
 
- **YouTube Interface Changes**: Script 1's CSS selectors may break if YouTube redesigns its Charts page. Screenshots are saved as artifacts on failure.
- **API Quotas**: YouTube Data API v3 has a 10,000-unit daily quota. Script 3 processes 100 videos per run (~100–200 units), so a single run uses about 1–2% of the daily quota.
- **Emerging Artists**: Script 2 relies on MusicBrainz, Wikipedia, and Wikidata. Artists who debuted recently may not yet have sufficient entries in these knowledge bases.
- **Complex Collaborations**: Collaborations with 5+ artists from different continents are resolved as "Multicountry / Multigenre" — individual contribution weighting is not yet implemented.
- **K-Pop Groups with Foreign Members**: Currently assigned to South Korea regardless of individual member nationalities.
 
 
## 📄 License and Attribution
 
**License**: MIT
 
**Author**: Alfonso Droguett
- 🔗 [LinkedIn](https://www.linkedin.com/in/adroguetth/)
- 🌐 [Portfolio](https://www.adroguett-portfolio.cl/)
- 📧 adroguett.consultor@gmail.com
 
**External Data Sources**:
- [MusicBrainz](https://musicbrainz.org/) — GPL License
- [Wikipedia](https://www.wikipedia.org/) — CC BY-SA
- [Wikidata](https://www.wikidata.org/) — CC0
- [YouTube Data API v3](https://developers.google.com/youtube/v3) — Google APIs Terms of Service
 
**Key Dependencies**:
- Playwright (Apache 2.0) — Script 1 browser automation
- Selenium (Apache 2.0) — Script 3 fallback browser
- yt-dlp (Unlicense) — Script 3 last-resort metadata
- Pandas (BSD 3-Clause) — Data processing
- Requests (Apache 2.0) — API calls
 
## 🤝 Contributing
 
1. **Report issues** with full logs (include the `error` column from the output database when relevant)
2. **Propose improvements** with concrete use cases
3. **Add genre mappings** — especially for underrepresented regions
4. **Improve CSS selectors** for Script 1 when YouTube updates its interface
5. **Maintain backward compatibility** with the existing database schema
 
```bash
# Standard contribution flow
git checkout -b feature/your-feature-name
# make changes, test locally
git commit -m "Add: brief description of change"
git push origin feature/your-feature-name
# open a Pull Request
```
**⭐ If you find this project useful, consider giving it a star on GitHub!**
