#!/usr/bin/env python3

"""
YouTube Charts Data Enrichment Pipeline
=============================================================
Enriches weekly chart data with YouTube metadata and links to canonical song catalog.

Workflow:
- Reads the latest chart database from charts_archive/1_download-chart/databases/
- Loads the canonical song catalog (build_song.db) to obtain:
    - song_catalog_id (foreign key)
    - artist_country (pre-resolved)
    - macro_genre (pre-resolved)
    - artists_found
- Fetches YouTube video metadata using a three-layer fallback system:
    1. YouTube Data API v3 (fastest, requires API key)
    2. Selenium browser automation (when API is unavailable)
    3. yt-dlp with anti-blocking options (last resort)
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
import subprocess
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------
# PATH CONFIGURATION
# ---------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent  # Music-Charts-Intelligence/

# Input: most recent weekly chart database
INPUT_DB_DIR = PROJECT_ROOT / "charts_archive" / "1_download-chart" / "databases"

# Canonical song catalog (built by script 2_2)
CATALOG_DB_PATH = PROJECT_ROOT / "charts_archive" / "2_2.build-song-catalog" / "build_song.db"

# Output: enriched database
OUTPUT_DIR = PROJECT_ROOT / "charts_archive" / "3_enrich-chart-data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Optional: set YOUTUBE_API_KEY env var to enable the API layer
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# Detect GitHub Actions environment to suppress interactive prompts
IN_GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"

# ---------------------------------------------------------------------
# VIDEO METADATA DETECTION HELPERS
# (These remain unchanged – same as original script)
# ---------------------------------------------------------------------
def detect_video_type(title: str, description: str = "") -> dict:
    """Classify the video type by scanning title and description."""
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
    """Detect whether a track is a multi-artist collaboration."""
    title_lower = title.lower()
    collab_patterns = [
        r'\sft\.\s', r'\sfeat\.\s', r'\sfeaturing\s', r'\sft\s',
        r'\scon\s', r'\swith\s', r'\s&\s', r'\sx\s', r'\s×\s',
        r'\(feat\.', r'\(ft\.', r'\(with', r'\[feat\.', r'\[ft\.'
    ]
    is_collab = any(re.search(p, title_lower, re.IGNORECASE) for p in collab_patterns)
    if artists_csv:
        artist_count = artists_csv.count('&') + artists_csv.count(',') + 1
    else:
        artist_count = 1
        if is_collab:
            artist_count = 2 + title_lower.count(' & ') + title_lower.count(' x ')
    return {
        'is_collaboration': is_collab,
        'artist_count': min(artist_count, 10)
    }

def detect_channel_type(channel_title: str) -> dict:
    """Classify the YouTube channel type from its title."""
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
        if ' - ' in channel_title or ' | ' in channel_title:
            return {'channel_type': 'Artist Channel'}
        return {'channel_type': 'General'}

def parse_upload_season(publish_date: str) -> dict:
    """Derive fiscal quarter from an ISO date string."""
    if not publish_date or len(publish_date) < 10:
        return {'upload_season': 'unknown'}
    try:
        date = datetime.strptime(publish_date[:10], "%Y-%m-%d")
        quarter = (date.month - 1) // 3 + 1
        return {'upload_season': f'Q{quarter}'}
    except Exception:
        return {'upload_season': 'unknown'}

def detect_region_restrictions(content_details: dict) -> dict:
    """Check whether a video carries regional restriction metadata."""
    if not content_details:
        return {'region_restricted': False}
    region = content_details.get('regionRestriction', {})
    return {'region_restricted': bool(region.get('blocked') or region.get('allowed'))}

def _empty_metadata() -> dict:
    """Return a zeroed-out metadata dict."""
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

# ---------------------------------------------------------------------
# METADATA RETRIEVAL LAYERS (unchanged, but I will include for completeness)
# ---------------------------------------------------------------------
def fetch_metadata_via_selenium(url: str, artists_csv: str = "") -> dict:
    """Layer 2: Fetch basic video metadata using a headless Chromium browser."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service

    metadata = _empty_metadata()
    errors = []
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
        wait = WebDriverWait(driver, 10)
        title_el = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.ytd-video-primary-info-renderer"))
        )
        title = title_el.text
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
        try:
            channel_el = driver.find_element(By.CSS_SELECTOR, "a.ytd-channel-name")
            metadata.update(detect_channel_type(channel_el.text))
        except Exception:
            pass
        metadata.update(detect_video_type(title, ""))
        metadata.update(detect_collaboration(title, artists_csv))
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
    """Orchestrate the three-layer metadata retrieval strategy."""
    metadata = _empty_metadata()
    errors = []
    # Layer 1: API
    if api_key:
        try:
            try:
                import isodate
            except ImportError:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "isodate"])
                import isodate
            from googleapiclient.discovery import build
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
                    metadata['region_restricted'] = bool(region.get('blocked') or region.get('allowed'))
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
                    return metadata
                else:
                    errors.append("API: video not found")
            else:
                errors.append("API: could not extract video_id")
        except Exception as e:
            errors.append(f"API error: {e}")
    # Layer 2: Selenium
    if errors or not api_key:
        try:
            try:
                import selenium
                import webdriver_manager
            except ImportError:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "selenium", "webdriver-manager"])
            sel_data = fetch_metadata_via_selenium(url, artists_csv)
            if not sel_data['error']:
                metadata.update(sel_data)
                return metadata
            else:
                errors.append(sel_data['error'])
        except Exception as e:
            errors.append(f"Selenium setup error: {e}")
    # Layer 3: yt-dlp
    try:
        import yt_dlp
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
                           capture_output=True, check=False)
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
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
            errors = []
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
# ---------------------------------------------------------------------
def find_latest_chart_db() -> Path:
    """Locate the most recent chart database file by lexicographic sort."""
    if not INPUT_DB_DIR.exists():
        raise FileNotFoundError(f"Input directory not found: {INPUT_DB_DIR}")
    db_files = list(INPUT_DB_DIR.glob("*.db"))
    if not db_files:
        raise FileNotFoundError(f"No .db files found in {INPUT_DB_DIR}")
    db_files.sort(key=lambda p: p.name, reverse=True)
    return db_files[0]

def load_chart_songs(db_path: Path) -> list:
    """Read all rows from the 'chart_data' table into a list of dicts."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chart_data'")
    if not cursor.fetchone():
        conn.close()
        raise Exception(f"Table 'chart_data' not found in {db_path}")
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

def get_catalog_info(artist_names: str, track_name: str, catalog_conn: sqlite3.Connection) -> dict:
    """
    Retrieve song_catalog_id, artist_country, macro_genre, artists_found from the catalog.
    Returns None for id if not found.
    """
    cursor = catalog_conn.cursor()
    cursor.execute("""
        SELECT id, artist_country, macro_genre, artists_found
        FROM artist_track
        WHERE artist_names = ? AND track_name = ?
    """, (artist_names, track_name))
    row = cursor.fetchone()
    if row:
        return {
            'song_catalog_id': row[0],
            'artist_country': row[1] if row[1] else "Unknown",
            'macro_genre': row[2] if row[2] else "Unknown",
            'artists_found': row[3] if row[3] else "0/0"
        }
    else:
        return {
            'song_catalog_id': None,
            'artist_country': 'Unknown',
            'macro_genre': 'Unknown',
            'artists_found': '0/0'
        }

def create_output_table(conn: sqlite3.Connection):
    """(Re)create the 'enriched_songs' table with song_catalog_id foreign key."""
    cursor = conn.cursor()
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
            song_catalog_id INTEGER,
            artist_country TEXT,
            macro_genre TEXT,
            artists_found TEXT,
            error TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (song_catalog_id) REFERENCES artist_track(id)
        )
    ''')
    cursor.execute('CREATE INDEX idx_country ON enriched_songs(artist_country)')
    cursor.execute('CREATE INDEX idx_genre ON enriched_songs(macro_genre)')
    cursor.execute('CREATE INDEX idx_catalog_id ON enriched_songs(song_catalog_id)')
    cursor.execute('CREATE INDEX idx_error ON enriched_songs(error)')
    conn.commit()

def insert_enriched_row(conn: sqlite3.Connection, row: dict):
    """Insert a single enriched song record into the output table."""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO enriched_songs (
            rank, artist_names, track_name, periods_on_chart, views, youtube_url,
            duration_s, duration_ms, upload_date, likes, comment_count,
            audio_language, is_official_video, is_lyric_video, is_live_performance,
            upload_season, channel_type, is_collaboration, artist_count,
            region_restricted, song_catalog_id, artist_country, macro_genre,
            artists_found, error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        row['rank'], row['artist_names'], row['track_name'],
        row['periods_on_chart'], row['views'], row['youtube_url'],
        row['duration_s'], row['duration_ms'], row['upload_date'],
        row['likes'], row['comment_count'], row['audio_language'],
        row['is_official_video'], row['is_lyric_video'], row['is_live_performance'],
        row['upload_season'], row['channel_type'], row['is_collaboration'],
        row['artist_count'], row['region_restricted'], row['song_catalog_id'],
        row['artist_country'], row['macro_genre'], row['artists_found'],
        row['error']
    ))
    conn.commit()

# ---------------------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------------------
def main():
    print("\n" + "=" * 70)
    print("🎵 CHART ENRICHMENT PIPELINE (Catalog-Integrated)")
    print("   METADATA EXTRACTION + CATALOG LOOKUP")
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

    # 2. Connect to canonical song catalog
    print("\n2. 🗂️  CONNECTING TO SONG CATALOG...")
    if not CATALOG_DB_PATH.exists():
        print(f"   ❌ Catalog database not found at {CATALOG_DB_PATH}")
        print("      Please run script 2_2 first to build the song catalog.")
        sys.exit(1)
    catalog_conn = sqlite3.connect(CATALOG_DB_PATH)
    print(f"   ✅ Catalog loaded: {CATALOG_DB_PATH}")

    # 3. Check yt-dlp
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

        # Fetch YouTube metadata
        metadata = fetch_video_metadata(url, artists_csv, YOUTUBE_API_KEY)

        # Lookup catalog information
        cat_info = get_catalog_info(artists_csv, song['Track Name'], catalog_conn)

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
            'song_catalog_id': cat_info['song_catalog_id'],
            'artist_country': cat_info['artist_country'],
            'macro_genre': cat_info['macro_genre'],
            'artists_found': cat_info['artists_found'],
            'error': metadata['error']
        }

        insert_enriched_row(conn_out, row)

        # Compact console feedback
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
        if cat_info['song_catalog_id']:
            badges.append(f"🆔{cat_info['song_catalog_id']}")
        if cat_info['artist_country'] not in ["Unknown", "Multi-country"]:
            badges.append(f"🌍{cat_info['artist_country'][:2]}")
        elif cat_info['artist_country'] == "Multi-country":
            badges.append("🌐")
        if cat_info['artists_found'] != "0/0":
            badges.append(f"🔍{cat_info['artists_found']}")

        if badges:
            print(f"({' '.join(badges)}) → {cat_info['artist_country'][:15]}, {cat_info['macro_genre'][:15]}")
        else:
            error_display = metadata['error'][:20] if metadata['error'] else "No data"
            print(f"({error_display})")

        time.sleep(0.1)

    conn_out.close()
    catalog_conn.close()

    # 7. Summary statistics
    print("\n7. 📊 FINAL SUMMARY:")
    conn_stats = sqlite3.connect(output_db_path)
    cur = conn_stats.cursor()
    cur.execute("SELECT COUNT(*) FROM enriched_songs")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM enriched_songs WHERE artist_country = 'Multi-country'")
    multi_country = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT artist_country) FROM enriched_songs WHERE artist_country NOT IN ('Unknown', 'Multi-country')")
    unique_countries = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT macro_genre) FROM enriched_songs WHERE macro_genre != 'Multi-genre' AND macro_genre IS NOT NULL")
    unique_genres = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM enriched_songs WHERE artist_country = 'Unknown'")
    unknown_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM enriched_songs WHERE error != ''")
    error_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM enriched_songs WHERE song_catalog_id IS NOT NULL")
    catalog_linked = cur.fetchone()[0]
    conn_stats.close()

    print(f"   💾 Output database: {output_db_path}")
    print(f"      📊 Total songs:              {total}")
    print(f"      🔗 Linked to catalog:         {catalog_linked} ({catalog_linked/total*100:.1f}%)")
    print(f"      🌐 Multi-country collabs:    {multi_country} ({multi_country/total*100:.1f}%)")
    print(f"      🗺️  Distinct countries:       {unique_countries}")
    print(f"      🎵 Distinct genres:           {unique_genres}")
    print(f"      ❓ Songs with unknown country: {unknown_count} ({unknown_count/total*100:.1f}%)")
    print(f"      ⚠️  Songs with metadata errors: {error_count} ({error_count/total*100:.1f}%)")

    print("\n" + "=" * 70)
    print("✅ ENRICHMENT PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 70)
    return 0

if __name__ == "__main__":
    if not IN_GITHUB_ACTIONS and not YOUTUBE_API_KEY:
        print("\n⚠️  YOUTUBE_API_KEY environment variable is not set.")
        print("   Metadata will be fetched via Selenium and yt-dlp (slower).")
        answer = input("Continue anyway? (y/n): ").strip().lower()
        if answer not in ['y', 'yes']:
            print("Process cancelled.")
            sys.exit(0)
    sys.exit(main())
