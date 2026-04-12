"""
Database operations for the artist database.

This module handles creation of the SQLite database, insertion/update of
artist records, and reading from the YouTube chart database.
"""

import sqlite3
import re
from pathlib import Path
from typing import Optional, Tuple, Set

from ..config import ARTIST_DB_PATH, CHARTS_DB_DIR, logger
from .artist_parser import split_artists


def create_database() -> None:
    """
    Create the artist database with columns: name (PK), country, macro_genre.
    If the table already exists, ensure the macro_genre column is present.
    """
    try:
        conn = sqlite3.connect(str(ARTIST_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='artist'")
        exists = cursor.fetchone()
        if not exists:
            cursor.execute('''
                CREATE TABLE artist (
                    name TEXT PRIMARY KEY,
                    country TEXT,
                    macro_genre TEXT
                )
            ''')
            conn.commit()
            logger.info("✅ Table 'artist' created (name, country, macro_genre)")
        else:
            cursor.execute("PRAGMA table_info(artist)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'macro_genre' not in columns:
                cursor.execute("ALTER TABLE artist ADD COLUMN macro_genre TEXT")
                conn.commit()
                logger.info("✅ Added 'macro_genre' column to existing table")
            else:
                logger.info("✅ Table 'artist' exists with all columns")
        conn.close()
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        raise


def artist_in_database(artist: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Check if an artist exists in the database and return their stored data.

    Args:
        artist: Artist name.

    Returns:
        Tuple of (exists: bool, country: Optional[str], macro_genre: Optional[str]).
    """
    try:
        conn = sqlite3.connect(str(ARTIST_DB_PATH))
        cursor = conn.cursor()
        cursor.execute('SELECT country, macro_genre FROM artist WHERE name = ?', (artist,))
        res = cursor.fetchone()
        conn.close()
        if res:
            return True, res[0], res[1]
        else:
            return False, None, None
    except Exception as e:
        logger.debug(f"Database query error: {e}")
        return False, None, None


def insert_artist(
    artist: str,
    country: str,
    genre: Optional[str] = None,
    source: str = ""
) -> None:
    """
    Insert a new artist or update missing fields for an existing artist.

    Args:
        artist: Artist name.
        country: Country name (or "Unknown").
        genre: Macro-genre (optional).
        source: Description of data source for logging.
    """
    try:
        conn = sqlite3.connect(str(ARTIST_DB_PATH))
        cursor = conn.cursor()
        cursor.execute('SELECT country, macro_genre FROM artist WHERE name = ?', (artist,))
        existing = cursor.fetchone()

        if existing:
            existing_country, existing_genre = existing
            update_country = (
                country != 'Unknown' and
                (not existing_country or existing_country == 'Unknown')
            )
            update_genre = (
                genre and genre != 'Unknown' and
                (not existing_genre or existing_genre == 'Unknown' or existing_genre is None)
            )

            if update_country or update_genre:
                set_clauses = []
                params = []
                if update_country:
                    set_clauses.append("country = ?")
                    params.append(country)
                if update_genre:
                    set_clauses.append("macro_genre = ?")
                    params.append(genre)
                params.append(artist)
                cursor.execute(f'''
                    UPDATE artist
                    SET {', '.join(set_clauses)}
                    WHERE name = ?
                ''', params)
                conn.commit()
                if source:
                    logger.info(
                        f"  🔄 {artist} → Country: {country if update_country else existing_country} | "
                        f"Genre: {genre if update_genre else existing_genre} ({source})"
                    )
        else:
            cursor.execute('''
                INSERT INTO artist (name, country, macro_genre)
                VALUES (?, ?, ?)
            ''', (artist, country, genre))
            conn.commit()
            if source:
                logger.info(f"  ➕ {artist} → Country: {country} | Genre: {genre or 'N/A'} ({source})")
            else:
                logger.info(f"  ✅ {artist} → Country: {country} | Genre: {genre or 'N/A'}")
        conn.close()
    except Exception as e:
        logger.error(f"Error inserting {artist}: {e}")


def count_artists_in_database() -> int:
    """Return the total number of artists stored in the database."""
    try:
        conn = sqlite3.connect(str(ARTIST_DB_PATH))
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM artist')
        total = cursor.fetchone()[0]
        conn.close()
        return total
    except Exception:
        return 0


def get_latest_chart_database() -> Optional[Path]:
    """
    Find the most recent YouTube chart database in the charts directory.

    Files are expected to follow the naming pattern: youtube_charts_YYYY-WW.db

    Returns:
        Path to the latest database or None if none found.
    """
    if not CHARTS_DB_DIR.exists():
        logger.error(f"❌ Directory not found: {CHARTS_DB_DIR}")
        return None

    db_files = list(CHARTS_DB_DIR.glob("youtube_charts_*.db"))
    if not db_files:
        logger.error("❌ No chart databases found")
        return None

    def week_key(file_path: Path) -> tuple:
        """Extract (year, week) from filename for sorting."""
        match = re.search(r'youtube_charts_(\d{4})-W(\d{1,2})\.db', file_path.name)
        if match:
            year = int(match.group(1))
            week = int(match.group(2))
            return (year, week)
        else:
            # Fallback to modification time
            return (0, file_path.stat().st_mtime)

    latest = max(db_files, key=week_key)
    logger.info(f"📁 Using database: {latest.name}")
    return latest


def get_artists_from_chart_db(db_path: Path) -> Set[str]:
    """
    Extract all unique artist names from a YouTube chart database.

    Args:
        db_path: Path to the chart SQLite database.

    Returns:
        Set of unique artist name strings.
    """
    if not db_path.exists():
        logger.error(f"❌ File not found: {db_path}")
        return set()

    artists = set()
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(chart_data)")
        columns = [col[1] for col in cursor.fetchall()]

        # Find the artist column (may have different names)
        artist_column = None
        for col in ['Artist Names', 'Artist', 'Artists', 'artist', 'Artista']:
            if col in columns:
                artist_column = col
                break

        if not artist_column:
            logger.error("❌ No artist column found in chart_data")
            conn.close()
            return set()

        safe_column = f'"{artist_column}"' if ' ' in artist_column else artist_column
        cursor.execute(f"SELECT {safe_column} FROM chart_data WHERE {safe_column} IS NOT NULL")
        rows = cursor.fetchall()

        for row in rows:
            if row[0]:
                artists.update(split_artists(str(row[0])))

        conn.close()
        logger.info(f"📊 {len(artists)} unique artists in the chart database")
        return artists

    except Exception as e:
        logger.error(f"❌ Error reading database: {e}")
        if 'conn' in locals():
            conn.close()
        return set()
