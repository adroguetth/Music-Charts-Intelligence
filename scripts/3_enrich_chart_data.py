#!/usr/bin/env python3

"""
YouTube Charts Data Enrichment Pipeline with Catalog Linking
=============================================================
Enriches weekly chart data with YouTube metadata and artist origin information,
and links each song to the canonical song catalog (build_song.db).

Workflow:
- Reads the latest chart database (SQLite) from charts_archive/1_download-chart/databases/
- Loads the local artist metadata database (artist_countries_genres.db) from
  charts_archive/2_1.countries-genres-artist/
- Fetches YouTube video metadata using a three-layer fallback system:
    1. YouTube Data API v3 (fastest, requires API key)
    2. Selenium browser automation (when API is unavailable)
    3. yt-dlp with anti-blocking options (last resort)
- Applies a weighted collaboration algorithm to resolve country/genre for multi-artist tracks
- Looks up the song in the catalog (build_song.db) to obtain its surrogate primary key
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
from collections import Counter
from typing import Optional

# ---------------------------------------------------------------------
# PATH CONFIGURATION
# ---------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent  # Music-Charts-Intelligence/

# Input: most recent weekly chart database
INPUT_DB_DIR = PROJECT_ROOT / "charts_archive" / "1_download-chart" / "databases"

# Local artist metadata database (pre‑downloaded by script 2_1)
ARTIST_DB_PATH = PROJECT_ROOT / "charts_archive" / "2_1.countries-genres-artist" / "artist_countries_genres.db"

# Canonical song catalog (built by script 2_2)
CATALOG_DB_PATH = PROJECT_ROOT / "charts_archive" / "2_2.build-song-catalog" / "build_song.db"

# Output: enriched database written here
OUTPUT_DIR = PROJECT_ROOT / "charts_archive" / "3_enrich-chart-data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Optional: set YOUTUBE_API_KEY env var to enable the API layer
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# Detect GitHub Actions environment to suppress interactive prompts
IN_GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"


# ---------------------------------------------------------------------
# LOOKUP TABLES (unchanged from original script)
# ---------------------------------------------------------------------
COUNTRY_TO_CONTINENT = {
    # (full dictionary omitted for brevity – keep as in original)
}

GENRE_HIERARCHY = {
    # (full dictionary omitted for brevity – keep as in original)
}

DEFAULT_GENRE = "Pop"


# ---------------------------------------------------------------------
# COLLABORATION WEIGHT SYSTEM (unchanged)
# ---------------------------------------------------------------------
def get_continent(country: str) -> str:
    return COUNTRY_TO_CONTINENT.get(country, "Unknown")


def infer_genre_by_country(artists_info: list) -> str:
    # (unchanged)
    pass


def resolve_country_and_genre(artists_info: list) -> tuple:
    # (unchanged)
    pass


def normalize_name(name: str) -> str:
    # (unchanged)
    pass


def parse_artist_list(artist_names: str) -> list:
    # (unchanged)
    pass


# ---------------------------------------------------------------------
# VIDEO METADATA DETECTION HELPERS (unchanged)
# ---------------------------------------------------------------------
def detect_video_type(title: str, description: str = "") -> dict:
    # (unchanged)
    pass


def detect_collaboration(title: str, artists_csv: str) -> dict:
    # (unchanged)
    pass


def detect_channel_type(channel_title: str) -> dict:
    # (unchanged)
    pass


def parse_upload_season(publish_date: str) -> dict:
    # (unchanged)
    pass


def detect_region_restrictions(content_details: dict) -> dict:
    # (unchanged)
    pass


# ---------------------------------------------------------------------
# METADATA RETRIEVAL LAYERS (unchanged)
# ---------------------------------------------------------------------
def _empty_metadata() -> dict:
    # (unchanged)
    pass


def fetch_metadata_via_selenium(url: str, artists_csv: str = "") -> dict:
    # (unchanged)
    pass


def fetch_video_metadata(url: str, artists_csv: str = "", api_key: str = None) -> dict:
    # (unchanged)
    pass


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


def build_artist_lookup(db_path: Path) -> dict:
    """
    Load artist records from the local SQLite file into an in‑memory dict.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Artist metadata DB not found: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, country, macro_genre FROM artist")
    rows = cursor.fetchall()
    conn.close()

    artist_lookup = {}
    for raw_name, country, genre in rows:
        key = normalize_name(raw_name)
        artist_lookup[key] = (country, genre)

    print(f"   ✅ Loaded {len(artist_lookup)} artists from local artist DB.")
    return artist_lookup


def get_artist_info(artist_names: str, artist_lookup: dict) -> list:
    """Resolve each artist in a track's 'Artist Names' field against the lookup dict."""
    names = parse_artist_list(artist_names)
    if not names:
        return []

    result = []
    for name in names:
        key = normalize_name(name)
        country, genre = artist_lookup.get(key, (None, None))
        result.append({'name': name, 'country': country, 'genre': genre})
    return result


def get_catalog_id(artist_names: str, track_name: str, catalog_conn: sqlite3.Connection) -> Optional[int]:
    """
    Retrieve the surrogate primary key (id) from the canonical song catalog.
    Returns None if the song is not yet present in the catalog.
    """
    cursor = catalog_conn.cursor()
    cursor.execute(
        "SELECT id FROM artist_track WHERE artist_names = ? AND track_name = ?",
        (artist_names, track_name)
    )
    row = cursor.fetchone()
    return row[0] if row else None


def create_output_table(conn: sqlite3.Connection):
    """
    (Re)create the 'enriched_songs' table, now including a song_catalog_id column.
    """
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
            artist_country TEXT,
            macro_genre TEXT,
            artists_found TEXT,
            song_catalog_id INTEGER,
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
            region_restricted, artist_country, macro_genre,
            artists_found, song_catalog_id, error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        row['rank'], row['artist_names'], row['track_name'],
        row['periods_on_chart'], row['views'], row['youtube_url'],
        row['duration_s'], row['duration_ms'], row['upload_date'],
        row['likes'], row['comment_count'], row['audio_language'],
        row['is_official_video'], row['is_lyric_video'], row['is_live_performance'],
        row['upload_season'], row['channel_type'], row['is_collaboration'],
        row['artist_count'], row['region_restricted'], row['artist_country'],
        row['macro_genre'], row['artists_found'], row['song_catalog_id'],
        row['error']
    ))
    conn.commit()


# ---------------------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------------------
def main():
    print("\n" + "=" * 70)
    print("🎵 CHART ENRICHMENT PIPELINE (API → Selenium → yt‑dlp)")
    print("   METADATA EXTRACTION + ARTIST COUNTRY/GENRE RESOLUTION")
    print("   WITH CATALOG LINKING")
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

    # 2. Load local artist metadata database
    print("\n2. 🌍 LOADING ARTIST METADATA DATABASE...")
    if not ARTIST_DB_PATH.exists():
        print(f"   ❌ Artist DB not found at {ARTIST_DB_PATH}")
        print("      Please run script 2_1 first to download artist_countries_genres.db")
        sys.exit(1)
    try:
        artist_lookup = build_artist_lookup(ARTIST_DB_PATH)
    except Exception as e:
        print(f"   ❌ Error loading artist DB: {e}")
        sys.exit(1)

    # 3. Connect to song catalog (if exists)
    print("\n3. 🗂️  CONNECTING TO SONG CATALOG...")
    catalog_conn = None
    if CATALOG_DB_PATH.exists():
        catalog_conn = sqlite3.connect(CATALOG_DB_PATH)
        print(f"   ✅ Catalog found: {CATALOG_DB_PATH}")
    else:
        print("   ⚠️  Catalog not found – song_catalog_id will be NULL.")

    # 4. Ensure yt-dlp is available
    print("\n4. 🔧 CHECKING DEPENDENCIES...")
    try:
        import yt_dlp
        print("   ✅ yt-dlp available")
    except ImportError:
        print("   📦 Installing yt-dlp...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
        import yt_dlp
        print("   ✅ yt-dlp installed")

    # 5. Load chart songs
    print(f"\n5. 📖 READING CHART DATA FROM {chart_db_path.name}...")
    try:
        songs = load_chart_songs(chart_db_path)
        print(f"   ✅ {len(songs)} songs loaded")
    except Exception as e:
        print(f"   ❌ Error reading chart database: {e}")
        sys.exit(1)

    # 6. Prepare output database
    print("\n6. 🗃️  PREPARING OUTPUT DATABASE...")
    output_db_path = OUTPUT_DIR / f"{chart_db_path.stem}_enriched.db"
    conn_out = sqlite3.connect(output_db_path)
    create_output_table(conn_out)
    print(f"   ✅ Output path: {output_db_path}")

    # 7. Process each song
    print(f"\n7. 🎬 ENRICHING {len(songs)} SONGS...")
    print("   ⏱️  This may take several minutes depending on retrieval layer used...")

    for i, song in enumerate(songs, 1):
        url = song['YouTube URL']
        track = song['Track Name'][:30]
        artists_csv = song.get('Artist Names', '')

        print(f"   [{i:2d}/{len(songs)}] {track:30}... ", end='', flush=True)

        # Fetch YouTube metadata (three-layer fallback)
        metadata = fetch_video_metadata(url, artists_csv, YOUTUBE_API_KEY)

        # Resolve artist country and genre via the collaboration weight algorithm
        artists_info = get_artist_info(artists_csv, artist_lookup)
        final_country, final_genre = resolve_country_and_genre(artists_info)

        # Count how many artists were successfully matched against the lookup DB
        matched = sum(1 for a in artists_info if a['country'] is not None)
        total_arts = len(artists_info) if artists_info else 1

        # Lookup catalog ID if catalog is available
        catalog_id = None
        if catalog_conn:
            catalog_id = get_catalog_id(artists_csv, song['Track Name'], catalog_conn)

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
            'artist_country': final_country,
            'macro_genre': final_genre,
            'artists_found': f"{matched}/{total_arts}",
            'song_catalog_id': catalog_id,
            'error': metadata['error']
        }

        insert_enriched_row(conn_out, row)

        # Build a compact inline status summary for the console
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
        if catalog_id:
            badges.append(f"🆔{catalog_id}")
        if final_country not in ["Unknown", "Multi-country"]:
            badges.append(f"🌍{final_country[:2]}")
        elif final_country == "Multi-country":
            badges.append("🌐")
        if matched < total_arts:
            badges.append(f"⚠️{matched}/{total_arts}")

        if badges:
            print(f"({' '.join(badges)}) → {final_country[:15]}, {final_genre[:15]}")
        else:
            error_display = metadata['error'][:20] if metadata['error'] else "No data"
            print(f"({error_display})")

        # Brief pause to avoid hammering endpoints when API is not used
        time.sleep(0.1)

    conn_out.close()
    if catalog_conn:
        catalog_conn.close()

    # 8. Summary statistics
    print("\n8. 📊 FINAL SUMMARY:")
    conn_stats = sqlite3.connect(output_db_path)
    cur = conn_stats.cursor()

    cur.execute("SELECT COUNT(*) FROM enriched_songs")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM enriched_songs WHERE song_catalog_id IS NOT NULL")
    linked = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM enriched_songs WHERE artist_country = 'Multi-country'")
    multi_country = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(DISTINCT artist_country) FROM enriched_songs "
        "WHERE artist_country NOT IN ('Unknown', 'Multi-country')"
    )
    unique_countries = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(DISTINCT macro_genre) FROM enriched_songs "
        "WHERE macro_genre != 'Multi-genre' AND macro_genre IS NOT NULL"
    )
    unique_genres = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM enriched_songs WHERE artist_country = 'Unknown'")
    unknown_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM enriched_songs WHERE error != ''")
    error_count = cur.fetchone()[0]

    conn_stats.close()

    print(f"   💾 Output database: {output_db_path}")
    print(f"      📊 Total songs:              {total}")
    print(f"      🔗 Linked to catalog:         {linked} ({linked / total * 100:.1f}%)")
    print(f"      🌐 Multi-country collabs:    {multi_country} ({multi_country / total * 100:.1f}%)")
    print(f"      🗺️  Distinct countries:       {unique_countries}")
    print(f"      🎵 Distinct genres:           {unique_genres}")
    print(f"      ❓ Songs with unknown country: {unknown_count} ({unknown_count / total * 100:.1f}%)")
    print(f"      ⚠️  Songs with metadata errors: {error_count} ({error_count / total * 100:.1f}%)")

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
