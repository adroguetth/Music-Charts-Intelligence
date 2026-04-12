#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Artist Country + Genre Detection System - Main Orchestrator
===========================================================
Intelligent enricher that adds geographic and genre metadata to artists from YouTube Charts.

This script orchestrates the modular components in build_artist_db/ to:
1. Read artist names from the latest YouTube chart database
2. Determine country of origin and primary genre for each artist
3. Store results in a persistent SQLite database
4. Only update missing or incomplete data

Features:
- Multi-source lookup (MusicBrainz, Wikipedia, Wikidata) with intelligent cascading
- Smart name variation generation (accents, prefixes, suffixes) for maximum match rate
- Country detection from cities, demonyms, and geographic references
- Genre classification with 200+ macro-genres and 5000+ subgenre mappings
- Weighted voting system with country-specific rules (e.g., K-Pop for South Korea)
- Persistent SQLite storage with partial update logic (only fills missing data)
- In-memory caching to avoid redundant API calls
- Automatic script detection for non-Latin artist names

Requirements:
- Python 3.7+
- requests
- openai
- pandas (optional, for future extensions)

Author: Alfonso Droguett
License: MIT
"""

import sys
import time
from pathlib import Path
from typing import Set

# ============================================================================
# PATH CONFIGURATION (for running as standalone script)
# ============================================================================
# Add the parent directory to sys.path so we can import build_artist_db
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================================
# IMPORTS FROM MODULAR PACKAGE
# ============================================================================
from build_artist_db.config import (
    CHARTS_DB_DIR,
    ARTIST_DB_PATH,
    setup_logging,
)
from build_artist_db.utils.db_utils import (
    create_database,
    artist_in_database,
    insert_artist,
    count_artists_in_database,
    get_latest_chart_database,
    get_artists_from_chart_db,
)
from build_artist_db.utils.artist_parser import split_artists
from build_artist_db.country_detector import search_country
from build_artist_db.genre_detector import search_artist_genre

# ============================================================================
# LOGGING SETUP
# ============================================================================
logger = setup_logging()


# ============================================================================
# MAIN FUNCTION
# ============================================================================
def main() -> None:
    """Main execution function for the artist database builder."""
    logger.info("=" * 80)
    logger.info("🎵 Artist Country + Genre Detection System - MODULAR MODE")
    logger.info(f"📁 Chart DB directory: {CHARTS_DB_DIR}")
    logger.info(f"💾 Artist DB path: {ARTIST_DB_PATH}")
    logger.info("=" * 80)

    # Ensure the database and table exist
    create_database()

    # Find the latest chart database
    chart_db = get_latest_chart_database()
    if not chart_db:
        logger.error("❌ Could not obtain chart database. Aborting.")
        sys.exit(1)

    # Extract all unique artist names from the chart database
    chart_artists = get_artists_from_chart_db(chart_db)
    if not chart_artists:
        logger.error("❌ No artists found in the chart database.")
        sys.exit(1)

    total_artists = len(chart_artists)
    logger.info(f"🎯 {total_artists} unique artists to process\n")

    # Statistics counters
    in_db_complete = 0      # Already in DB with both country and genre
    new_country_found = 0   # New country discovered
    new_genre_found = 0     # New genre discovered
    no_info_found = 0       # Neither country nor genre found

    # Process each artist in alphabetical order for consistent logging
    for i, artist in enumerate(sorted(chart_artists), 1):
        exists, db_country, db_genre = artist_in_database(artist)

        # If artist is already fully populated, skip processing
        if exists and db_country and db_country != 'Unknown' and db_genre and db_genre != 'Unknown':
            logger.info(f"  ✅ {artist} → {db_country} | {db_genre}")
            in_db_complete += 1
        else:
            # Artist needs processing (either new or missing data)
            if exists:
                logger.info(
                    f"  🔍 {artist} (in DB - Country: {db_country or '?'} | "
                    f"Genre: {db_genre or '?'}, searching missing info...)"
                )
            else:
                logger.info(f"  🔍 {artist} (new, searching...)")

            # Search for country
            country, country_source = search_country(artist)

            # Search for genre (if not already in DB)
            genre = None
            genre_source = ""
            if not db_genre or db_genre == 'Unknown':
                genre, genre_source = search_artist_genre(artist, country)

            # Determine final values (prefer newly found over existing)
            final_country = country if country else (db_country if db_country else "Unknown")
            final_genre = genre if genre else (db_genre if db_genre else None)

            # Build combined source description for logging
            source_parts = []
            if country_source and country_source != "Not found":
                source_parts.append(country_source)
            if genre_source and genre_source != "Genre not found":
                source_parts.append(genre_source)
            final_source = " | ".join(source_parts) if source_parts else ""

            # Insert or update the database
            insert_artist(artist, final_country, final_genre, final_source)

            # Update statistics
            if country and country != 'Unknown':
                new_country_found += 1
            if genre:
                new_genre_found += 1
            if not country and not genre:
                no_info_found += 1

        # Progress report every 10 artists
        if i % 10 == 0:
            logger.info(
                f"\n  📊 {i}/{total_artists} | "
                f"✅ Complete: {in_db_complete} | "
                f"🔍 New country: {new_country_found} | "
                f"🎵 New genre: {new_genre_found} | "
                f"❌ No info: {no_info_found}\n"
            )

    # ==========================================================================
    # FINAL SUMMARY
    # ==========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("📈 EXECUTION SUMMARY")
    logger.info(f"   Total artists processed: {total_artists}")

    if total_artists > 0:
        pct_complete = (in_db_complete / total_artists) * 100
        pct_country = (new_country_found / total_artists) * 100
        pct_genre = (new_genre_found / total_artists) * 100
        pct_none = (no_info_found / total_artists) * 100

        logger.info(f"   ✅ Already complete (country+genre): {in_db_complete} ({pct_complete:.1f}%)")
        logger.info(f"   🔍 New country found: {new_country_found} ({pct_country:.1f}%)")
        logger.info(f"   🎵 New genre found: {new_genre_found} ({pct_genre:.1f}%)")
        logger.info(f"   ❌ No information found: {no_info_found} ({pct_none:.1f}%)")

    total_in_db = count_artists_in_database()
    logger.info(f"   🗃️  Total artists in database: {total_in_db}")
    logger.info("=" * 80)


# ==============================================================================
# SCRIPT ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    main()
