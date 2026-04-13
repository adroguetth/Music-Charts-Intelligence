#!/usr/bin/env python3
"""
YouTube Charts Song Catalog Builder
===================================
Automated ETL pipeline for building and maintaining a canonical song catalog
from YouTube Charts weekly database snapshots.

Features:
- Automatic detection of most recent weekly database via lexicographic ordering
- Idempotent insertion with composite natural key deduplication
- Auto-incrementing surrogate primary key generation
- Schema validation and automatic table initialization
- Comprehensive error handling and logging
- GitHub Actions CI/CD compatible

Data Flow:
1. Scans charts_archive/1_download-chart/databases/ for youtube_charts_20XX-WXX.db files
2. Selects most recent snapshot based on ISO week identifier
3. Extracts distinct (Artist Names, Track Name) tuples
4. Performs existence check against artist_track catalog
5. Inserts new records with auto-generated sequential IDs

Database Schema:
    Table: artist_track
    Columns:
        - id           : INTEGER PRIMARY KEY AUTOINCREMENT (surrogate key)
        - artist_names : VARCHAR(200) NOT NULL (natural key component)
        - track_name   : VARCHAR(200) NOT NULL (natural key component)
    
    Natural Key: UNIQUE(artist_names, track_name) constraint implied by logic

Requirements:
- Python 3.7+
- sqlite3 (included in Python standard library)
- pathlib (included in Python standard library)
- re (included in Python standard library)

Author: Alfonso Droguett
License: MIT
"""

import sqlite3
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List

# -----------------------------------------------------------------------------
# Directory Structure Configuration
# -----------------------------------------------------------------------------
# Repository-relative paths ensure consistent behavior across local development
# and GitHub Actions CI/CD environments.

# Determine repository root (parent of scripts directory)
REPO_ROOT = Path(__file__).parent.parent

# Source: Where weekly chart databases are stored (Script 1 output)
SOURCE_DIR = REPO_ROOT / "charts_archive" / "1_download-chart" / "databases"

# Target: Where the canonical song catalog will be maintained
# Using 2_2.build-song-catalog naming pattern consistent with other scripts
TARGET_DIR = REPO_ROOT / "charts_archive" / "2_2.build-song-catalog"
TARGET_DB_NAME = "build_song.db"

# Create target directory structure if it doesn't exist
TARGET_DIR.mkdir(parents=True, exist_ok=True)

# Regex pattern for YouTube Charts weekly database filenames
# Format: youtube_charts_YYYY-Www.db (e.g., youtube_charts_2026-W15.db)
# Note: Pattern matches years 2000-2099 (20\d{2})
DB_FILENAME_PATTERN = re.compile(r'youtube_charts_20\d{2}-W\d{1,2}\.db$')


def get_week_identifier_from_filename(filename: str) -> Optional[str]:
    """
    Extract ISO week identifier from database filename.
    
    Args:
        filename: Database filename (e.g., 'youtube_charts_2026-W15.db')
        
    Returns:
        str: Week identifier in format 'YYYY-WXX', or None if pattern doesn't match
    """
    match = DB_FILENAME_PATTERN.match(filename)
    if match:
        # Extract week identifier by removing prefix and extension
        week_id = filename.replace("youtube_charts_", "").replace(".db", "")
        return week_id
    return None


def get_most_recent_database(directory: Path) -> Optional[Path]:
    """
    Identify the most recent YouTube Charts database file in the specified directory.
    
    Selection algorithm:
        1. Filter files matching pattern: youtube_charts_20YY-Www.db
        2. Extract ISO week identifiers for comparison
        3. Sort by year (descending), then by week number (descending)
        4. Return path to the most recent valid database
    
    This approach correctly handles year boundaries (e.g., 2025-W52 vs 2026-W01).
    Lexicographic sorting works because ISO format 'YYYY-WXX' is naturally ordered.
    
    Args:
        directory: Path object pointing to directory containing weekly databases
        
    Returns:
        Path: Absolute path to most recent database file, or None if none found
    """
    matching_files: List[Tuple[str, Path]] = []
    
    # Scan directory for files matching naming convention
    for file_path in directory.glob("youtube_charts_*.db"):
        filename = file_path.name
        week_id = get_week_identifier_from_filename(filename)
        if week_id:
            matching_files.append((week_id, file_path))
    
    if not matching_files:
        return None
    
    # Sort by week identifier (lexicographic order works due to ISO format)
    # Example: '2026-W15' > '2025-W52' in string comparison
    matching_files.sort(key=lambda x: x[0], reverse=True)
    
    most_recent_week, most_recent_path = matching_files[0]
    return most_recent_path


def initialize_target_schema(connection: sqlite3.Connection) -> None:
    """
    Ensure target catalog table exists with correct schema definition.
    
    Creates the artist_track table if it doesn't exist with the following structure:
        id           : INTEGER PRIMARY KEY AUTOINCREMENT
        artist_names : VARCHAR(200) NOT NULL
        track_name   : VARCHAR(200) NOT NULL
    
    The AUTOINCREMENT keyword ensures that SQLite generates monotonically
    increasing IDs and never reuses deleted IDs, which is important for
    referential integrity in downstream analytics.
    
    Args:
        connection: Active SQLite database connection
        
    Raises:
        sqlite3.Error: If schema creation fails
    """
    ddl_statement = """
        CREATE TABLE IF NOT EXISTS artist_track (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            artist_names VARCHAR(200) NOT NULL,
            track_name   VARCHAR(200) NOT NULL
        )
    """
    
    try:
        with connection:
            connection.execute(ddl_statement)
    except sqlite3.Error as e:
        print(f"   ❌ Schema initialization error: {e}")
        raise


def record_exists(cursor: sqlite3.Cursor, artist_names: str, track_name: str) -> bool:
    """
    Check for existence of an artist-track pair in the catalog.
    
    Performs an efficient existence check using SELECT 1 with LIMIT 1
    to minimize I/O overhead while maintaining accuracy. This is an
    O(1) operation assuming proper index coverage (implicit on PRIMARY KEY).
    
    Args:
        cursor: Active SQLite cursor
        artist_names: Artist name(s) string (may contain multiple artists)
        track_name: Track name string
        
    Returns:
        bool: True if the (artist_names, track_name) tuple exists, False otherwise
    """
    query = """
        SELECT 1
        FROM artist_track
        WHERE artist_names = ?
          AND track_name = ?
        LIMIT 1
    """
    
    try:
        cursor.execute(query, (artist_names, track_name))
        return cursor.fetchone() is not None
    except sqlite3.Error as e:
        print(f"   ⚠️  Error checking record existence: {e}")
        return False


def get_catalog_statistics(connection: sqlite3.Connection) -> Tuple[int, int]:
    """
    Retrieve current catalog statistics.
    
    Args:
        connection: Active SQLite database connection
        
    Returns:
        Tuple[int, int]: (total_records, latest_id)
            - total_records: Total number of unique songs in catalog
            - latest_id: Highest auto-generated ID (0 if empty)
    """
    cursor = connection.cursor()
    
    cursor.execute("SELECT COUNT(*), COALESCE(MAX(id), 0) FROM artist_track")
    total_records, latest_id = cursor.fetchone()
    
    return total_records, latest_id


def migrate_data() -> int:
    """
    Execute the ETL pipeline to update the song catalog.
    
    Process flow:
        1. Validate source directory and locate most recent database
        2. Establish read-only connection to source database
        3. Establish read-write connection to target catalog
        4. Initialize target schema if necessary
        5. Extract distinct artist-track pairs from source
        6. Insert new records with idempotent logic
        7. Commit transaction and report statistics
        8. Handle errors gracefully with appropriate exit codes
    
    Returns:
        int: Exit code (0 = success, 1 = failure)
    """
    print("\n" + "=" * 70)
    print("🎵 YOUTUBE CHARTS - SONG CATALOG BUILDER")
    print("   IDEMPOTENT ETL PIPELINE FOR ARTIST-TRACK CATALOG")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # -------------------------------------------------------------------------
    # Phase 1: Source Database Selection
    # -------------------------------------------------------------------------
    print("\n1. 🔍 LOCATING MOST RECENT SOURCE DATABASE...")
    
    if not SOURCE_DIR.exists():
        print(f"   ❌ Source directory does not exist: {SOURCE_DIR}")
        print(f"   ℹ️  Please run 1_download.py first to populate chart databases")
        return 1
    
    source_path = get_most_recent_database(SOURCE_DIR)
    
    if not source_path:
        print(f"   ❌ No database files found matching pattern: youtube_charts_20XX-WXX.db")
        print(f"   📁 Directory: {SOURCE_DIR}")
        return 1
    
    source_week_id = get_week_identifier_from_filename(source_path.name)
    source_size_kb = source_path.stat().st_size / 1024
    
    print(f"   ✅ Source identified: {source_path.name}")
    print(f"   📆 Week identifier: {source_week_id}")
    print(f"   📊 File size: {source_size_kb:.1f} KB")
    
    # -------------------------------------------------------------------------
    # Phase 2: Database Connections
    # -------------------------------------------------------------------------
    print("\n2. 🔗 ESTABLISHING DATABASE CONNECTIONS...")
    
    target_path = TARGET_DIR / TARGET_DB_NAME
    target_exists = target_path.exists()
    
    # Source connection: read-only mode prevents accidental modification
    # URI connection format allows parameter specification
    source_uri = f"file:{source_path}?mode=ro"
    
    try:
        source_conn = sqlite3.connect(source_uri, uri=True)
        source_conn.row_factory = sqlite3.Row  # Enable column access by name
        source_cursor = source_conn.cursor()
        
        # Verify source database has expected table structure
        source_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chart_data'"
        )
        if not source_cursor.fetchone():
            print(f"   ❌ Source database missing 'chart_data' table")
            source_conn.close()
            return 1
        
        print(f"   ✅ Source connection established (read-only mode)")
        
        target_conn = sqlite3.connect(target_path)
        target_cursor = target_conn.cursor()
        
        if target_exists:
            target_size_kb = target_path.stat().st_size / 1024
            print(f"   ✅ Target connection established (existing: {target_size_kb:.1f} KB)")
        else:
            print(f"   ✅ Target connection established (new database)")
            
    except sqlite3.Error as e:
        print(f"   ❌ Database connection error: {e}")
        return 1
    
    # -------------------------------------------------------------------------
    # Phase 3: Schema Initialization
    # -------------------------------------------------------------------------
    print("\n3. 📋 INITIALIZING TARGET SCHEMA...")
    
    try:
        initialize_target_schema(target_conn)
        
        # Get pre-migration statistics for growth calculation
        initial_count, initial_max_id = get_catalog_statistics(target_conn)
        print(f"   ✅ Schema ready: artist_track table")
        print(f"   📊 Current catalog size: {initial_count:,} records")
        
    except sqlite3.Error as e:
        print(f"   ❌ Schema initialization failed: {e}")
        source_conn.close()
        target_conn.close()
        return 1
    
    # -------------------------------------------------------------------------
    # Phase 4: Data Extraction and Transformation
    # -------------------------------------------------------------------------
    print("\n4. 📤 EXTRACTING ARTIST-TRACK PAIRS FROM SOURCE...")
    
    # Extract distinct artist-track pairs from source
    # Using DISTINCT to reduce processing overhead for duplicates within source
    # Filters out NULL and empty strings to maintain data quality
    extract_query = """
        SELECT DISTINCT
            "Artist Names" AS artist_names,
            "Track Name" AS track_name
        FROM chart_data
        WHERE "Artist Names" IS NOT NULL
          AND "Track Name" IS NOT NULL
          AND TRIM("Artist Names") != ''
          AND TRIM("Track Name") != ''
        ORDER BY "Artist Names", "Track Name"
    """
    
    try:
        source_cursor.execute(extract_query)
        all_rows = source_cursor.fetchall()
        total_extracted = len(all_rows)
        
        print(f"   ✅ Extracted {total_extracted:,} distinct artist-track pairs")
        
        if total_extracted == 0:
            print(f"   ⚠️  No valid records found in source database")
            source_conn.close()
            target_conn.close()
            return 0
            
    except sqlite3.Error as e:
        print(f"   ❌ Data extraction error: {e}")
        source_conn.close()
        target_conn.close()
        return 1
    
    # -------------------------------------------------------------------------
    # Phase 5: Idempotent Insertion
    # -------------------------------------------------------------------------
    print("\n5. 💾 PERFORMING IDEMPOTENT INSERTION...")
    
    insert_statement = """
        INSERT INTO artist_track (artist_names, track_name)
        VALUES (?, ?)
    """
    
    inserted_count = 0
    skipped_count = 0
    error_count = 0
    
    # Calculate progress intervals for user feedback (25%, 50%, 75%, 100%)
    progress_interval = max(1, total_extracted // 4)
    
    for idx, row in enumerate(all_rows, 1):
        artist_names = row['artist_names']
        track_name = row['track_name']
        
        try:
            # Check existence before insertion to maintain idempotency
            if not record_exists(target_cursor, artist_names, track_name):
                target_cursor.execute(insert_statement, (artist_names, track_name))
                inserted_count += 1
            else:
                skipped_count += 1
        except sqlite3.Error as e:
            error_count += 1
            # Limit error noise to first 5 occurrences
            if error_count <= 5:
                print(f"   ⚠️  Error processing: {artist_names[:30]}... - {track_name[:30]}...")
        
        # Progress reporting at calculated intervals
        if idx % progress_interval == 0 or idx == total_extracted:
            progress_pct = (idx / total_extracted) * 100
            print(f"   📈 Progress: {idx:,}/{total_extracted:,} ({progress_pct:.1f}%) - "
                  f"Inserted: {inserted_count:,}, Skipped: {skipped_count:,}")
    
    # Commit all pending transactions atomically
    target_conn.commit()
    
    print(f"\n   ✅ Insertion completed:")
    print(f"      🆕 New records inserted: {inserted_count:,}")
    print(f"      ⏭️  Duplicates skipped: {skipped_count:,}")
    if error_count > 0:
        print(f"      ⚠️  Errors encountered: {error_count}")
    
    # -------------------------------------------------------------------------
    # Phase 6: Verification and Statistics
    # -------------------------------------------------------------------------
    print("\n6. 📊 VERIFICATION AND STATISTICS...")
    
    final_count, final_max_id = get_catalog_statistics(target_conn)
    
    # Verify count matches expectation (initial + inserted = final)
    expected_final = initial_count + inserted_count
    if final_count == expected_final:
        print(f"   ✅ Integrity check passed: {final_count:,} total records")
    else:
        print(f"   ⚠️  Count mismatch: Expected {expected_final:,}, Found {final_count:,}")
    
    # Calculate growth percentage (0% if initial_count is 0)
    if initial_count > 0:
        growth_pct = ((final_count - initial_count) / initial_count) * 100
        print(f"   📈 Catalog growth: +{growth_pct:.2f}%")
    
    print(f"   🔑 Latest ID: {final_max_id}")
    print(f"   💾 Database location: {target_path}")
    print(f"   📀 Database size: {target_path.stat().st_size / 1024:.1f} KB")
    
    # Sample recent entries for human verification (last 5 inserted)
    print(f"\n   📋 Sample of recent catalog entries:")
    target_cursor.execute("""
        SELECT id, artist_names, track_name
        FROM artist_track
        ORDER BY id DESC
        LIMIT 5
    """)
    
    recent_entries = target_cursor.fetchall()
    for entry_id, artist, track in recent_entries:
        # Truncate long strings for display readability
        artist_display = artist[:40] + "..." if len(artist) > 40 else artist
        track_display = track[:40] + "..." if len(track) > 40 else track
        print(f"      [{entry_id:4d}] {artist_display} — {track_display}")
    
    # -------------------------------------------------------------------------
    # Phase 7: Cleanup
    # -------------------------------------------------------------------------
    source_conn.close()
    target_conn.close()
    
    print("\n" + "=" * 70)
    if inserted_count > 0:
        print(f"✅ CATALOG UPDATED: Added {inserted_count:,} new songs")
    else:
        print(f"✅ CATALOG UNCHANGED: No new songs to add")
    print("=" * 70)
    
    return 0


def list_catalog_summary() -> None:
    """
    Display summary statistics of the song catalog.
    
    Shows:
    - Total unique songs
    - Most recent additions (last 5)
    - Top artists by unique song count
    - Database file information
    
    This function is idempotent and safe to call even if catalog doesn't exist.
    """
    target_path = TARGET_DIR / TARGET_DB_NAME
    
    if not target_path.exists():
        print("   ℹ️  Song catalog does not exist yet")
        print("   💡 Run with migration first to create catalog")
        return
    
    try:
        conn = sqlite3.connect(target_path)
        cursor = conn.cursor()
        
        # Check if table exists (handles empty/partial databases)
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='artist_track'"
        )
        if not cursor.fetchone():
            print("   ℹ️  artist_track table not found in catalog")
            conn.close()
            return
        
        # Get global statistics
        total_records, latest_id = get_catalog_statistics(conn)
        
        # Get most recent additions (for verification)
        cursor.execute("""
            SELECT id, artist_names, track_name
            FROM artist_track
            ORDER BY id DESC
            LIMIT 10
        """)
        recent = cursor.fetchall()
        
        # Get top artists by song count (for analytics insights)
        cursor.execute("""
            SELECT artist_names, COUNT(*) as song_count
            FROM artist_track
            GROUP BY artist_names
            ORDER BY song_count DESC
            LIMIT 5
        """)
        top_artists = cursor.fetchall()
        
        conn.close()
        
        print(f"\n📀 SONG CATALOG SUMMARY:")
        print(f"   📊 Total unique songs: {total_records:,}")
        print(f"   🔑 Highest ID: {latest_id}")
        print(f"   💾 File size: {target_path.stat().st_size / 1024:.1f} KB")
        
        if top_artists:
            print(f"\n   🏆 Top artists by unique songs:")
            for artist, count in top_artists:
                artist_display = artist[:50] + "..." if len(artist) > 50 else artist
                print(f"      • {artist_display}: {count} songs")
        
        if recent:
            print(f"\n   🆕 Most recent additions:")
            for entry_id, artist, track in recent[:5]:
                artist_display = artist[:40] + "..." if len(artist) > 40 else artist
                track_display = track[:40] + "..." if len(track) > 40 else track
                print(f"      [{entry_id:4d}] {artist_display} — {track_display}")
                
    except sqlite3.Error as e:
        print(f"   ⚠️  Error reading catalog: {e}")


def main() -> int:
    """
    Main execution function.
    
    Workflow:
        1. Execute ETL pipeline to update song catalog
        2. Display catalog summary statistics
        3. Return appropriate exit code
        
    Returns:
        int: Exit code (0 = success, 1 = error)
    """
    # Execute migration (ETL pipeline)
    exit_code = migrate_data()
    
    # Display catalog summary if migration succeeded
    if exit_code == 0:
        list_catalog_summary()
    else:
        print("\n❌ Migration failed. See errors above.")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
