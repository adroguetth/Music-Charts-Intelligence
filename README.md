# 🎵 Music Charts Intelligence System
**🇪🇸 ¿Buscas la versión en español?** → [README.es.md](README.es.md)

![WIP](https://img.shields.io/badge/status-WIP-fdd0a2?style=flat-square) 

![MIT License](https://img.shields.io/badge/license-MIT-9ecae1?style=flat-square&logo=open-source-initiative&logoColor=white) ![Automation](https://img.shields.io/badge/Automation-GitHub_Actions-blue?style=flat-square) ![Web Scraping](https://img.shields.io/badge/Web-Scraping-orange?style=flat-square) ![ETL](https://img.shields.io/badge/ETL-9ecae1?style=flat-square&logo=dataengine&logoColor=white) ![Data Enrichment](https://img.shields.io/badge/Data-Enrichment-blue?style=flat-square) ![Notebook Generation](https://img.shields.io/badge/Notebook-Generation-blue?style=flat-square) ![AI Insights](https://img.shields.io/badge/AI-Insights-purple?style=flat-square) ![Interactive Dashboards](https://img.shields.io/badge/Interactive_Dashboards-9ecae1?style=flat-square&logo=databricks&logoColor=white)

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![SQLite](https://img.shields.io/badge/SQLite-07405e?style=flat-square&logo=sqlite&logoColor=white) ![Playwright](https://custom-icon-badges.demolab.com/badge/Playwright-2EAD33?logo=playwright&logoColor=white&style=flat-square) ![Selenium](https://img.shields.io/badge/Selenium-43b02a?style=flat-square&logo=selenium&logoColor=white) ![yt-dlp](https://img.shields.io/badge/yt--dlp-FF0000?style=flat-square&logo=youtube&logoColor=white) ![YouTube API](https://img.shields.io/badge/YouTube_API-ff0000?style=flat-square&logo=youtube&logoColor=white) ![MusicBrainz](https://img.shields.io/badge/MusicBrainz-BA478F?style=flat-square&logo=musicbrainz&logoColor=white) ![Wikipedia API](https://img.shields.io/badge/Wikipedia-000000?style=flat-square&logo=wikipedia&logoColor=white) ![Wikidata](https://img.shields.io/badge/Wikidata-990000?style=flat-square&logo=wikidata&logoColor=white) [![DeepSeek](https://custom-icon-badges.demolab.com/badge/DeepSeek-4D6BFF?logo=deepseek&logoColor=white&style=flat-square)](https://deepseek.com) ![Jupyter](https://img.shields.io/badge/Jupyter-f37626?style=flat-square&logo=jupyter&logoColor=white) ![Streamlit](https://img.shields.io/badge/Streamlit-ff4b4b?style=flat-square&logo=streamlit&logoColor=white) ![Google Drive](https://img.shields.io/badge/Google%20Drive-4285F4?style=flat-square&logo=googledrive&logoColor=white) ![OAuth 2.0](https://img.shields.io/badge/OAuth-2.0-3C873A?style=flat-square&logo=oauth&logoColor=white)

A fully automated, end-to-end pipeline that downloads YouTube's weekly music charts, enriches every artist with geographic and genre metadata, augments each chart entry with deep YouTube video metadata, generates AI-powered Jupyter notebooks, and archives everything to Google Drive — all running on GitHub Actions, zero manual intervention required.

## 📁 Online Archive

All exported notebooks and PDFs are publicly available at:

🔗 **[Music Charts Intelligence - Google Drive Archive](https://drive.google.com/drive/folders/1RpfyGHsIY5MThE1bfe0Rc3gk03WoYzpR)**

| Language   | Path                   | Contents          |
| :--------- | :--------------------- | :---------------- |
| 🇬🇧 English | `/Notebook_EN/weekly/` | `.ipynb` + `.pdf` |
| 🇪🇸 Spanish | `/Notebook_ES/weekly/` | `.ipynb` + `.pdf` |

> The archive is updated weekly every Tuesday at 12:00 UTC.

## 📥 Documentation

| Script                                      | Purpose                                                      | English Docs                                                 | Spanish Docs                                                 |
| :------------------------------------------ | :----------------------------------------------------------- | :----------------------------------------------------------- | :----------------------------------------------------------- |
| **1_download.py**                           | Downloads weekly YouTube Charts (100 songs) into SQLite      | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/1_download.md) · [PDF](https://drive.google.com/file/d/11ANLX6PbK_eIzvHLPqL1rm9NY9rOshhD/view?usp=sharing) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/1_download.md) · [PDF](https://drive.google.com/file/d/1SdLvJnxcKxmQYmLlwoYttHr2Izud4iE5/view?usp=sharing) |
| **2_1.build_artist_db.py**                  | Enriches artists with country + genre via MusicBrainz, Wikipedia, Wikidata | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/2_1.build_artist_db.md) · [PDF](https://drive.google.com/file/d/1viUAxZ7k-qeYYbyvZf2OaP20AfLOgKh2/view?usp=drive_link) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/2_1.build_artist_db.md) · [PDF](https://drive.google.com/file/d/1WBHBreKeVToTBygSyCuYsHQUr_zSl3BT/view?usp=drive_link) |
| **2_2.build_song_catalog.py**               | Builds canonical song catalog with resolved country/genre    | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/2_2.build_song_catalog.md) · [PDF](https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXX/view?usp=drive_link) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/2_2.build_song_catalog.md) · [PDF](https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXX/view?usp=sharing) |
| **3_enrich_chart_data.py**                  | Adds YouTube video metadata to every chart entry (3-layer system) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/3_enrich-chart-data.md) · [PDF](https://drive.google.com/file/d/1XGEx2fRBCpOhU5BfY_YjlKm6zmI41RpB/view?usp=drive_link) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/3_enrich-chart-data.md) · [PDF](https://drive.google.com/file/d/1tSFjf_gQQeArdE4n5DLL2I2G_MJW6vE3/view?usp=sharing) |
| **4_1.weekly_charts_notebook_generator.py** | Generates bilingual Jupyter notebooks with AI insights       | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/4_1.weekly_charts_notebook_generator.md) · [PDF](https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXX/view?usp=drive_link) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/4_1.weekly_charts_notebook_generator.md) · [PDF](https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXX/view?usp=sharing) |
| **5_export_notebook_to_pdf.py**             | Exports notebooks to PDF and uploads to Google Drive         | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_EN/5_export_notebook_to_pdf.md) · [PDF](https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXX/view?usp=drive_link) | [README](https://github.com/adroguetth/Music-Charts-Intelligence/blob/main/Documentation_ES/5_export_notebook_to_pdf.md) · [PDF](https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXX/view?usp=sharing) |

> Each script's README contains detailed code analysis, configuration options, and troubleshooting guides. This document covers the system as a whole.

------

## 🗂️ System Architecture

The pipeline processes data in five distinct stages, each building on the previous one's output:

```text
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
│   Script 2.1      │  → Artist reference database
│ build_artist_db   │    Artist → Country + Genre
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Script 2.2      │  → Song catalog (unique songs)
│build_song_catalog │    artist_names, track_name, country, genre
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Script 3        │  → Fully enriched chart entries
│ 3_enrich_chart_   │    25 fields per song (including catalog FK)
│      data.py      │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Script 4        │  → Bilingual Jupyter notebooks
│ 4_1.weekly_charts │    25+ visualizations + AI insights
│   _notebook_      │    (English & Spanish)
│   generator.py    │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   Script 5        │  → PDF export + Google Drive archive
│ 5_export_notebook │    Notebook_EN/ + Notebook_ES/ → Drive
│   _to_pdf.py      │    Structured folders: weekly/YYYY-WXX/EN/ES/
└───────────────────┘
        │
        ▼
   Archived & Ready
```

### Data Flow Between Scripts

| Stage      | Input                                | Output                                       | Records                   |
| :--------- | :----------------------------------- | :------------------------------------------- | :------------------------ |
| Script 1   | YouTube Charts webpage               | `youtube_charts_YYYY-WXX.db`                 | 100 songs/week            |
| Script 2.1 | Script 1's database (artist names)   | `artist_countries_genres.db`                 | Grows ~10–50 artists/week |
| Script 2.2 | Script 1's DB + Script 2.1's DB      | `build_song.db` (canonical catalog)          | Grows ~10–50 songs/week   |
| Script 3   | Script 1's DB + Script 2.2's catalog | `youtube_charts_YYYY-WXX_enriched.db`        | 100 enriched rows/week    |
| Script 4   | Script 3's enriched DB               | `Notebook_EN/` + `Notebook_ES/` notebooks    | 2 notebooks/week          |
| Script 5   | Script 4's notebooks                 | Google Drive (`weekly/YYYY-WXX/EN/` + `ES/`) | PDFs + original notebooks |

------

## ⚙️ Automation Schedule

All five scripts are orchestrated by GitHub Actions and run automatically each week:

| Workflow                            | Schedule (UTC) | Trigger Logic                    | Timeout |
| :---------------------------------- | :------------- | :------------------------------- | :------ |
| `1_download-chart.yml`              | Monday 12:00   | Cron + manual (push disabled)    | 30 min  |
| `2_1.update-artist-db.yml`          | Monday 13:00   | Cron + manual (push disabled)    | 60 min  |
| `2_2.build-song-catalog.yml`        | Monday 13:15   | Cron + manual (push disabled)    | 15 min  |
| `3_enrich-chart-data.yml`           | Monday 14:00   | Cron + manual (push disabled)    | 60 min  |
| `4_1.generate-weekly-notebooks.yml` | Monday 15:00   | Cron + manual (push disabled)    | 20 min  |
| `5_export-notebook-pdf.yml`         | Tuesday 12:00  | Cron + manual (no push triggers) | 20 min  |

> **Note**: Automatic execution on `git push` has been disabled for all workflows. Changes to scripts do not trigger workflows automatically. To test changes, use manual dispatch or wait for the next scheduled run.

The gaps between each workflow ensure the previous step has finished before the next one begins. Each workflow commits its output directly back to the repository. Script 5 runs on Tuesday to allow time for manual review of notebooks before archival.

### Execution Flow Timeline

```text
Monday 12:00 UTC ─→ Script 1: Download charts
        ↓
Monday 13:00 UTC ─→ Script 2.1: Artist enrichment
        ↓
Monday 13:15 UTC ─→ Script 2.2: Song catalog
        ↓
Monday 14:00 UTC ─→ Script 3: Chart enrichment
        ↓
Monday 15:00 UTC ─→ Script 4: Notebook generation
        ↓
Tuesday 12:00 UTC ─→ Script 5: Export to PDF + Google Drive
```



### Required Secrets

| Secret                  | Used By  | Purpose                                            |
| :---------------------- | :------- | :------------------------------------------------- |
| `YOUTUBE_API_KEY`       | Script 3 | YouTube Data API v3 for video metadata (Layer 1)   |
| `DEEPSEEK_API_KEY`      | Script 4 | DeepSeek AI for generating insights in notebooks   |
| `GDRIVE_CLIENT_ID`      | Script 5 | OAuth 2.0 client ID for Google Drive API           |
| `GDRIVE_CLIENT_SECRET`  | Script 5 | OAuth 2.0 client secret for Google Drive API       |
| `GDRIVE_REFRESH_TOKEN`  | Script 5 | Refresh token for persistent Drive access          |
| `GDRIVE_ROOT_FOLDER_ID` | Script 5 | ID of the root folder in Google Drive for archival |

Scripts 1, 2.1, and 2.2 require no API keys. Script 3 works without a key but falls back to slower methods (Selenium, yt-dlp). Script 4 works without DeepSeek but shows placeholder text instead of AI insights. Script 5 requires OAuth 2.0 credentials (desktop application type) with Drive API enabled.

------

## 🔬 How Each Script Works

### Script 1 — Download YouTube Charts

Runs every Monday and scrapes the top 100 songs from YouTube Charts using Playwright with a headless Chromium browser. It implements multiple CSS selector strategies to find the download button, hides automation fingerprints with custom headers and JavaScript injection, and falls back to sample data if YouTube's interface changes.

Each weekly run produces a new, versioned SQLite database. Before writing, it creates a temporary backup of the existing file to prevent data loss. Old databases are cleaned up automatically based on a configurable retention period (default: 52 weeks).

**Key technical details:**

- Anti-detection: custom user agent, hidden `navigator.webdriver`, realistic viewport
- 3 fallback selectors for the download button (`#download-button`, `aria-label`, text)
- Backup naming: `backup_YYYY-WXX_YYYYMMDD_HHMMSS.db`
- Fallback data: 100 synthetic records with identical structure to real data

------

### Script 2.1 — Build Artist Database

Takes every unique artist name from Script 1's database and enriches it with country of origin and primary music genre. For each artist, it generates up to 15 name variations (removing accents, stripping prefixes, etc.) and queries them across three external knowledge bases in a cascading order.

**Country detection** uses a curated dictionary of 30,000+ geographic terms (cities, demonyms, regional references) to extract location signals from API responses. It checks MusicBrainz first (structured, reliable), then Wikipedia English (summary and infobox), then Wikipedia in priority languages (chosen based on detected script or known country), and finally Wikidata (properties P27 and P19).

**Genre detection** collects candidates from MusicBrainz tags and Wikidata's P136 property, then applies a weighted voting system across 200+ macro-genres and 5,000+ subgenre mappings. Country-specific priority bonuses are applied (e.g., K-Pop gets a 2.0× multiplier for South Korean artists).

The script never overwrites existing data — it only fills in missing fields. This makes re-runs safe and incremental.

**Key technical details:**

- 15 name variations per artist (e.g., "The Beatles" → "Beatles", "beatles", etc.)
- In-memory cache prevents duplicate API calls within a session
- Script detection (Cyrillic, Hangul, Devanagari, Arabic, etc.) guides Wikipedia language selection
- Weighted voting: MusicBrainz weight > Wikipedia weight > Wikidata weight
- Country-specific genre bonuses for 100+ countries

------

### Script 2.2 — Build Song Catalog

Builds a canonical song catalog by extracting distinct `(artist_names, track_name)` pairs from the weekly chart database and resolving country and genre **once per unique song** using the collaboration weighting system (moved from Script 3). This eliminates redundant processing across multiple chart appearances.

The script loads artist metadata from Script 2.1's database, applies the collaboration algorithm to multi-artist tracks (absolute majority → relative majority → Multi-country), and maintains an idempotent SQLite database with auto-incrementing surrogate keys.

**Key technical details:**

- Natural key deduplication: `(artist_names, track_name)`
- Collaboration weighting: 196-country continent map, 100+ genre hierarchies
- Phase 5: repairs historical incomplete records (backfills missing country/genre)
- Schema migration: auto-adds `artist_country`, `macro_genre`, `artists_found` columns

------

### Script 3 — Enrich Chart Data

Takes Script 1's latest chart database and Script 2.2's song catalog and produces a fully enriched output with 25 fields per song. The most technically complex script in the system, it retrieves YouTube video metadata using a 3-layer strategy that always tries the fastest method first.

**Layer 1 — YouTube Data API v3** (0.3–0.8s/video): Retrieves exact duration, like count, comment count, audio language, regional restrictions, and upload date. Used when a valid API key is available and quota remains.

**Layer 2 — Selenium** (3–5s/video): Launches a headless Chrome browser and extracts metadata directly from the YouTube player. Used as fallback when the API is unavailable or quota is exhausted.

**Layer 3 — yt-dlp** (2–4s/video): Tries multiple client configurations (Android, iOS, Web) with retry delays to avoid bot detection. Used as a last resort.

Beyond video metadata, the script also classifies each entry using text analysis: it detects whether a video is official, a lyric video, a live performance, or a remix; classifies the channel type (VEVO, Topic, Label/Studio, Artist Channel); and links each song to its catalog ID as a foreign key.

**Key technical details:**

- Country/genre now read from song catalog (pre-resolved by Script 2.2)
- Foreign key relationship: `enriched_songs.id` references `artist_track.id`
- Detects collaborations via regex patterns (feat., ft., &, x, with, con)
- Channel type detection via keyword matching
- Upload season (Q1–Q4) derived from upload date

------

### Script 4 — Generate AI-Powered Notebooks

Takes Script 3's enriched database and automatically generates professional Jupyter notebooks with comprehensive visual analysis and AI-generated insights in both English and Spanish. The system produces two fully-executed notebooks per week containing **25+ visualizations**, **12 analysis sections**, and **AI-powered commentary** generated by DeepSeek API, all cached to avoid redundant API calls.

**Notebook sections include:**

- Introduction (AI-generated weekly overview)
- General statistics (songs, countries, genres, views, likes)
- Country analysis (geographic distribution, pie chart, bar charts)
- Genre analysis (treemap, engagement rates, heatmap)
- Song metrics (top songs by views, likes, engagement)
- Video metrics (performance by official/lyric/live video type)
- Temporal analysis (trends by release quarter)
- Collaborations analysis (solo vs collaboration performance)
- Executive summary (30-line AI-generated strategic summary)

**Key technical details:**

- 25+ static visualizations using matplotlib, seaborn, and squarify (no JavaScript)
- Per-week, per-language cache system for AI insights (MD5 hash-based)
- Sliding window retention: keeps only last 6 notebooks per language
- YouTube-inspired styling (#FF0000, #F9F9F9, etc.)
- Zero JavaScript — all charts compatible with GitHub preview

------

### Script 5 — Export to PDF + Google Drive

Exports the weekly notebooks (EN and ES) to PDF using `nbconvert --to webpdf` with Playwright Chromium (no LaTeX required) and uploads both the original notebooks and PDFs to Google Drive for long-term archival. The script scans both notebook directories, determines the most recent week using ISO week comparison (correctly handling year boundaries), and organizes files in a structured folder hierarchy.

**Key technical details:**

- Bilingual support: processes both `Notebook_EN/weekly/` and `Notebook_ES/weekly/`
- ISO week sorting: correctly identifies most recent week (`2026-W01` > `2025-W52`)
- Structured Drive organization: `weekly/ → youtube_charts_YYYY-WXX/ → EN/ and ES/`
- OAuth 2.0 authentication with refresh token (no manual re-authentication)
- Idempotent uploads: creates folders only if they don't exist

------

## 📁 Repository Structure

```text
Music-Charts-Intelligence/
├── .github/workflows/
│   ├── 1_download-chart.yml
│   ├── 2_1.update-artist-db.yml
│   ├── 2_2.build-song-catalog.yml
│   ├── 3_enrich-chart-data.yml
│   ├── 4_1.generate-weekly-notebooks.yml
│   └── 5_export-notebook-pdf.yml
│
├── scripts/
│   ├── 1_download.py
│   ├── 2_1.build_artist_db.py                    # Main orchestrator (~120 lines)
│   ├── 2_2.build_song_catalog.py
│   ├── 3_enrich_chart_data.py
│   ├── 4_1.weekly_charts_notebook_generator.py
│   └── 5_export_notebook_to_pdf.py
│
├── build_artist_db/                              # Modular package (Script 2.1)
│   ├── __init__.py                               # Public API exports
│   ├── config.py                                 # Paths, logging, cache, HTTP sessions
│   ├── country_detector.py                       # Country search orchestration
│   ├── genre_detector.py                         # Genre search + weighted voting
│   │
│   ├── dictionaries/                             # Static data (can be updated independently)
│   │   ├── __init__.py
│   │   ├── countries.py                          # 30,000+ country variants → canonical names
│   │   ├── genres.py                             # 5,000+ genre variants → macro-genres
│   │   ├── macro_genres.py                       # List of all 200+ valid macro-genres
│   │   ├── country_rules.py                      # Country genre priorities + specific rules
│   │   └── stopwords.py                          # Words to filter from genre extraction
│   │
│   ├── utils/                                    # Reusable utilities
│   │   ├── __init__.py
│   │   ├── text_utils.py                         # Normalization, variations, script detection
│   │   ├── cache.py                              # Access to global cache (re-export)
│   │   ├── db_utils.py                           # SQLite create, read, insert, update
│   │   └── artist_parser.py                      # Split multi-artist strings
│   │
│   └── apis/                                     # External API clients (pluggable)
│       ├── __init__.py
│       ├── musicbrainz.py                        # MusicBrainz API client
│       ├── wikidata.py                           # Wikidata API client
│       ├── wikipedia.py                          # Wikipedia API client (infobox + summary)
│       └── deepseek.py                           # DeepSeek AI fallback client
│
├── charts_archive/
│   ├── 1_download-chart/
│   │   ├── latest_chart.csv
│   │   ├── databases/
│   │   │   ├── youtube_charts_2025-W01.db
│   │   │   ├── youtube_charts_2025-W02.db
│   │   │   └── ...
│   │   └── backup/
│   │
│   ├── 2_1.countries-genres-artist/
│   │   └── artist_countries_genres.db
│   │
│   ├── 2_2.build-song-catalog/
│   │   └── build_song.db
│   │
│   └── 3_enrich-chart-data/
│       ├── youtube_charts_2025-W01_enriched.db
│       ├── youtube_charts_2025-W02_enriched.db
│       └── ...
│
├── Notebook_EN/                                   # English notebooks (Script 4 output)
│   └── weekly/
│       ├── youtube_charts_2025-W14.ipynb
│       ├── cache/
│       │   └── youtube_charts_2025-W14_en.json
│       └── ...
│
├── Notebook_ES/                                   # Spanish notebooks (Script 4 output)
│   └── weekly/
│       ├── youtube_charts_2025-W14.ipynb
│       ├── cache/
│       │   └── youtube_charts_2025-W14_es.json
│       └── ...
│
├── Documentation_EN/                              # English documentation
├── Documentation_ES/                              # Spanish documentation
│
├── requirements.txt
├── .gitignore
│
├── README.es.md
└── README.md
```



### Data Retention Policy

| Data                              | Retention               | Configurable                  |
| :-------------------------------- | :---------------------- | :---------------------------- |
| Weekly chart databases (Script 1) | 52 weeks                | `RETENTION_WEEKS` in script   |
| Backup files (Script 1)           | 7 days                  | `RETENTION_DAYS` in script    |
| Artist database (Script 2.1)      | Permanent (cumulative)  | —                             |
| Song catalog (Script 2.2)         | Permanent (cumulative)  | —                             |
| Enriched databases (Script 3)     | 78 weeks                | `RETENTION_WEEKS` in workflow |
| Notebooks (Script 4)              | 6 most recent           | `MAX_KEEP` in workflow        |
| Notebook cache (Script 4)         | 6 most recent           | `MAX_KEEP` in workflow        |
| Google Drive archive (Script 5)   | Permanent (15 GB quota) | —                             |

------

## 🗄️ Database Schemas

### Script 1 Output — `chart_data` table

| Column               | Type    | Description                            |
| :------------------- | :------ | :------------------------------------- |
| `Rank`               | INTEGER | Chart position (1–100)                 |
| `Previous Rank`      | INTEGER | Position in previous week              |
| `Track Name`         | TEXT    | Song title                             |
| `Artist Names`       | TEXT    | Artist(s), may include collaborations  |
| `Periods on Chart`   | INTEGER | Number of weeks on chart               |
| `Views`              | INTEGER | Total view count                       |
| `Growth`             | TEXT    | Week-over-week growth percentage       |
| `YouTube URL`        | TEXT    | Direct video link                      |
| `download_date`      | TEXT    | Date of download                       |
| `download_timestamp` | TEXT    | Full timestamp                         |
| `week_id`            | TEXT    | ISO week identifier (e.g., `2025-W11`) |

### Script 2.1 Output — `artist` table

| Column        | Type      | Description           | Example          |
| :------------ | :-------- | :-------------------- | :--------------- |
| `name`        | TEXT (PK) | Canonical artist name | `"BTS"`          |
| `country`     | TEXT      | Country of origin     | `"South Korea"`  |
| `macro_genre` | TEXT      | Primary genre         | `"K-Pop/K-Rock"` |

### Script 2.2 Output — `artist_track` table

| Column           | Type                              | Description                                     | Example                   |
| :--------------- | :-------------------------------- | :---------------------------------------------- | :------------------------ |
| `id`             | INTEGER PRIMARY KEY AUTOINCREMENT | Surrogate key (sequential)                      | `1`, `2`, `3`...          |
| `artist_names`   | VARCHAR(200) NOT NULL             | Artist name(s) from chart                       | `"Bad Bunny"`             |
| `track_name`     | VARCHAR(200) NOT NULL             | Song title                                      | `"DtMF"`                  |
| `artist_country` | TEXT NOT NULL                     | Resolved country (or "Multi-country"/"Unknown") | `"Puerto Rico"`           |
| `macro_genre`    | TEXT NOT NULL                     | Resolved genre (or "Multi-genre"/"Pop")         | `"Reggaetón/Trap Latino"` |
| `artists_found`  | TEXT                              | Ratio of matched artists (matched/total)        | `"1/1"` or `"2/3"`        |

### Script 3 Output — `enriched_songs` table (25 fields)

| Category           | Fields                                                       |
| :----------------- | :----------------------------------------------------------- |
| **Identifiers**    | `rank`, `id` (FK to `artist_track.id`), `artist_names`, `track_name` |
| **Chart Metrics**  | `periods_on_chart`, `views`, `youtube_url`                   |
| **Video Metadata** | `duration_s`, `duration_ms`, `upload_date`, `likes`, `comment_count`, `audio_language` |
| **Video Flags**    | `is_official_video`, `is_lyric_video`, `is_live_performance` |
| **Context**        | `upload_season`, `channel_type`, `is_collaboration`, `artist_count`, `region_restricted` |
| **Enrichment**     | `artist_country`, `macro_genre`, `artists_found` (from catalog) |
| **Control**        | `error`, `processed_at`                                      |

------

## 🚀 Quick Start

### Prerequisites

- Python 3.7 or higher (3.12 recommended)
- Git
- Internet access
- YouTube Data API v3 key (optional — only needed for Script 3 Layer 1)
- DeepSeek API key (optional — only needed for Script 4 AI insights)
- Google Cloud project with Drive API enabled + OAuth 2.0 credentials (optional — only needed for Script 5)

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

# Step 2.1: Enrich the artist database
python scripts/2_1.build_artist_db.py

# Step 2.2: Build the song catalog
python scripts/2_2.build_song_catalog.py

# Step 3: Enrich chart entries with YouTube metadata
export YOUTUBE_API_KEY="your-api-key"   # Optional but recommended
python scripts/3_enrich_chart_data.py

# Step 4: Generate AI-powered notebooks
export DEEPSEEK_API_KEY="your-api-key"  # Optional for AI insights
python scripts/4_1.weekly_charts_notebook_generator.py

# Step 5: Export to PDF and upload to Google Drive
export GDRIVE_CLIENT_ID="your-client-id"
export GDRIVE_CLIENT_SECRET="your-client-secret"
export GDRIVE_REFRESH_TOKEN="your-refresh-token"
export GDRIVE_ROOT_FOLDER_ID="your-folder-id"
python scripts/5_export_notebook_to_pdf.py
```

Each script can be run independently. Scripts 2.1, 2.2, 3, 4, and 5 depend on previous scripts' outputs existing.

### Environment Variables

```bash
# Simulate GitHub Actions environment (disables interactive prompts)
export GITHUB_ACTIONS=true

# YouTube Data API v3 key (Script 3, Layer 1)
export YOUTUBE_API_KEY="your-key-here"

# DeepSeek API key (Script 4, AI insights)
export DEEPSEEK_API_KEY="your-key-here"

# Google Drive OAuth 2.0 (Script 5)
export GDRIVE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GDRIVE_CLIENT_SECRET="GOCSPX-xxxx"
export GDRIVE_REFRESH_TOKEN="1//0gxxxx"
export GDRIVE_ROOT_FOLDER_ID="1ABCxyz123..."

# Playwright visual debugging (Script 1)
export PWDEBUG=1
```



------

## 📊 Output Sample

After a full pipeline run, a typical weekly output looks like this:

```text
✅ Script 1: YouTube Chart Update 2025-W11 — 100 songs downloaded
✅ Script 2.1: Artist database updated — 23 new artists enriched (2,346 total)
✅ Script 2.2: Song catalog updated — 15 new songs added (1,234 total)
✅ Script 3: Chart enriched — 100 songs processed in 2m 04s
✅ Script 4: Notebooks generated — EN + ES notebooks with AI insights
✅ Script 5: Exported to Drive — PDFs uploaded to weekly/2025-W11/

📊 Weekly Stats (2025-W11):
   • Distinct countries detected:    28
   • Distinct genres detected:       15
   • Multi-country collaborations:   24 (24.0%)
   • Official music videos:          61 (61.0%)
   • API success rate (Script 3):    98%
   • Catalog link rate (Script 3):   97%
```



------

## 📈 Performance Reference

| Script                   | Typical Runtime | Bottleneck                               |
| :----------------------- | :-------------- | :--------------------------------------- |
| Script 1                 | 2–5 minutes     | Page load / Playwright startup           |
| Script 2.1               | 10–30 minutes   | API rate limits (MusicBrainz, Wikipedia) |
| Script 2.2               | 3–8 seconds     | SQLite operations                        |
| Script 3 (with API key)  | ~2 minutes      | YouTube API quota                        |
| Script 3 (Selenium only) | ~5–7 minutes    | Headless browser per video               |
| Script 3 (yt-dlp only)   | ~8–10 minutes   | Anti-bot delays                          |
| Script 4 (with cache)    | ~1–2 minutes    | Notebook execution                       |
| Script 4 (new week)      | ~3–5 minutes    | DeepSeek API calls                       |
| Script 5                 | ~2–4 minutes    | PDF conversion + Drive upload            |

------

## 🔧 Configuration Reference

### Script 1 — `1_download.py`

```python
RETENTION_DAYS = 7        # Days to keep backup files
RETENTION_WEEKS = 52      # Weeks to keep weekly databases
TIMEOUT = 120000          # Playwright browser timeout (ms)
```



### Script 2.1 — `2_1.build_artist_db.py`

```python
MIN_CANDIDATES = 3        # Min genre candidates before querying Wikipedia
RETRY_DELAY = 0.5         # Delay between API calls (seconds)
DEFAULT_TIMEOUT = 10      # API request timeout (seconds)
```



### Script 2.2 — `2_2.build_song_catalog.py`

```python
progress_interval = max(1, total_extracted // 4)  # Progress reporting intervals
```



### Script 3 — `3_enrich_chart_data.py`

```python
SLEEP_BETWEEN_VIDEOS = 0.1    # Pause between videos (seconds)
YT_DLP_RETRIES = 5             # yt-dlp retry attempts
SELENIUM_TIMEOUT = 10          # Selenium page load timeout (seconds)
```



### Script 4 — `4_1.weekly_charts_notebook_generator.py`

```python
# Max tokens for AI insights
if section in ["introduction", "executive_summary"]:
    max_tokens = 2000  # For 30-line summary
else:
    max_tokens = 600

# Temperature for AI creativity
"temperature": 0.7  # Range: 0.0 (deterministic) to 1.0 (creative)
```



### Script 5 — `5_export_notebook_to_pdf.py`

```python
NOTEBOOKS_EN_DIR = Path("Notebook_EN/weekly")
NOTEBOOKS_ES_DIR = Path("Notebook_ES/weekly")
TEMP_PDF_DIR = Path("temp_pdf")  # Temporary storage for PDFs
```



### Workflow-level (`*.yml` files)

```yaml
# Script 1
timeout-minutes: 30

# Script 2.1
timeout-minutes: 60
env:
  RETENTION_DAYS: 30

# Script 2.2
timeout-minutes: 15

# Script 3
timeout-minutes: 60
env:
  RETENTION_WEEKS: 78

# Script 4
timeout-minutes: 20
env:
  MAX_KEEP: 6  # Notebooks to retain per language

# Script 5
timeout-minutes: 20
env:
  RETENTION_DAYS: 30
```



------

## 🧩 Extending the System

### Adding a New Artist Delimiter (Script 2.1, 2.2, 3)

```python
separators = [
    '&', 'feat.', 'ft.', ',', ' y ', ' and ', ' with ', ' x ', ' vs ',
    ' présente ',      # French
    ' und ',           # German
    ' e ', ' com '     # Portuguese
]
```



### Adding a New Genre Mapping (Script 2.1)

```python
# In GENRE_MAPPINGS
'new subgenre name': ('Macro-Genre', 'subgenre')
```



### Adding a New Country Genre Hierarchy (Script 2.2)

```python
# In GENRE_HIERARCHY
"Country Name": [
    "Priority Genre 1",   # Selected first in tiebreaks
    "Priority Genre 2",
    "Priority Genre 3"
]
```



### Adjusting Country Genre Bonuses (Script 2.1)

```python
# In COUNTRY_GENRE_PRIORITY
"Country Name": [
    "Priority Genre 1",   # 2.0× multiplier
    "Priority Genre 2",   # 1.5× multiplier
    "Priority Genre 3"    # 1.2× multiplier
]
```



### Adding a New Analysis Section (Script 4)

1. Add section title in `get_section_titles()`
2. Add prompt in `get_ai_insight()` (English and Spanish)
3. Add data summary in `get_data_summaries()`
4. Add code cell in `generate_notebook()`
5. Add to `sections` list in main execution

------

## 🐛 Common Issues

| Error                                             | Likely Cause                 | Solution                                                  |
| :------------------------------------------------ | :--------------------------- | :-------------------------------------------------------- |
| `Playwright browsers not installed`               | Missing Chromium binary      | `python -m playwright install chromium`                   |
| `No chart databases found`                        | Script 1 hasn't run yet      | Run Script 1 first                                        |
| `Sign in to confirm you're not a bot`             | yt-dlp blocked by YouTube    | Set `YOUTUBE_API_KEY`; script auto-falls back to Selenium |
| `Quota exceeded`                                  | YouTube API daily limit hit  | Script auto-falls back to Selenium/yt-dlp                 |
| `API key not valid`                               | Invalid or restricted key    | Verify key in Google Cloud Console                        |
| `No module named 'isodate'`                       | Missing dependency           | `pip install isodate`                                     |
| `ModuleNotFoundError: No module named 'squarify'` | Missing treemap library      | `pip install squarify`                                    |
| `DeepSeek API key not configured`                 | Missing secret for Script 4  | Add `DEEPSEEK_API_KEY` to GitHub Secrets or env           |
| `HttpError 403: storageQuotaExceeded`             | Service account has no quota | Use OAuth 2.0 with personal Google account (Script 5)     |
| `Invalid refresh token`                           | Token expired or revoked     | Re-run `generate_refresh_token.py` for Script 5           |
| Very slow Script 3 (>10 min)                      | API key missing or failing   | Check `YOUTUBE_API_KEY` is set and valid                  |
| Very slow Script 4 (>5 min)                       | No cache, first run of week  | Normal; subsequent runs use cache                         |

For detailed troubleshooting, see the individual script documentation linked in the table at the top of this README.

------

## 🧪 Known Limitations

- **YouTube Interface Changes**: Script 1's CSS selectors may break if YouTube redesigns its Charts page. Screenshots are saved as artifacts on failure.
- **API Quotas**: YouTube Data API v3 has a 10,000-unit daily quota. Script 3 processes 100 videos per run (~100–200 units), so a single run uses about 1–2% of the daily quota.
- **Emerging Artists**: Script 2.1 relies on MusicBrainz, Wikipedia, and Wikidata. Artists who debuted recently may not yet have sufficient entries in these knowledge bases.
- **Complex Collaborations**: Collaborations with 5+ artists from different continents are resolved as "Multi-country / Multi-genre" — individual contribution weighting is not yet implemented.
- **K-Pop Groups with Foreign Members**: Currently assigned to South Korea regardless of individual member nationalities.
- **Language Support**: Script 4 only supports English and Spanish notebooks (other languages would require new prompts).
- **Google Drive Quota**: Script 5 uses OAuth 2.0 with a personal Google account (15 GB free). Service accounts do not have storage quota and cannot upload to personal drives.

------

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
- [DeepSeek API](https://deepseek.com/) — Commercial API (fallback only)

**Key Dependencies**:

- Playwright (Apache 2.0) — Script 1 browser automation
- Selenium (Apache 2.0) — Script 3 fallback browser
- yt-dlp (Unlicense) — Script 3 last-resort metadata
- Pandas (BSD 3-Clause) — Data processing
- Requests (Apache 2.0) — API calls
- Jupyter (BSD 3-Clause) — Notebook generation
- Matplotlib, Seaborn, Squarify — Visualizations
- Google API Client (Apache 2.0) — Script 5 Drive upload

------

## 🤝 Contributing

1. **Report issues** with full logs (include the `error` column from the output database when relevant)
2. **Propose improvements** with concrete use cases
3. **Add genre mappings** — especially for underrepresented regions
4. **Improve CSS selectors** for Script 1 when YouTube updates its interface
5. **Maintain backward compatibility** with the existing database schema

bash

```bash
# Standard contribution flow
git checkout -b feature/your-feature-name
# make changes, test locally
git commit -m "Add: brief description of change"
git push origin feature/your-feature-name
# open a Pull Request
```



------

**⭐ If you find this project useful, consider giving it a star on GitHub!**
