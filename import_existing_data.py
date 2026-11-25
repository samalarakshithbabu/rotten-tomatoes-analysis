#!/usr/bin/env python3
"""
Import Existing CSV Data into SQLite Database

This script imports data from the existing rotten_tomatoes_700.csv file
into the new SQLite database schema with proper validation and quality checks.
"""

import os
import sys
import logging
from pathlib import Path

import pandas as pd
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from database.schema import DatabaseManager
from database.models import ScrapingSession, DataQualityCheck

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clean_critics_score(value):
    """Convert critics score to numeric."""
    if pd.isna(value) or value == '':
        return None
    try:
        return float(str(value).replace('%', '').strip())
    except (ValueError, AttributeError):
        return None


def clean_year(value):
    """Extract year from string like '(2023)'."""
    if pd.isna(value) or value == '':
        return None
    try:
        val_str = str(value).strip()
        if val_str.startswith('(') and val_str.endswith(')'):
            return int(val_str[1:-1])
        return int(float(val_str))
    except (ValueError, AttributeError):
        return None


def import_csv_to_database(csv_path: str, db_path: str = "database/rotten_tomatoes.db"):
    """
    Import CSV data into SQLite database.
    
    Args:
        csv_path: Path to CSV file
        db_path: Path to output database
    """
    logger.info(f"Starting import from {csv_path}")
    
    # Validate file exists
    if not os.path.exists(csv_path):
        logger.error(f"File not found: {csv_path}")
        return False
    
    # Initialize database
    db = DatabaseManager(db_path)
    db.create_tables()
    
    # Create a session for this import
    session = ScrapingSession(
        target_records=1000,
        status="completed",
        total_records=0,
        config_snapshot='{"source": "csv_import", "file": "' + csv_path + '"}'
    )
    session_id = db.add_session(session)
    logger.info(f"Created scraping session: {session_id}")
    
    # Load CSV
    try:
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} records from CSV")
    except Exception as e:
        logger.error(f"Error loading CSV: {e}")
        return False
    
    # Display original columns
    logger.info(f"Original columns: {list(df.columns)}")
    
    # Transform data to match schema
    movies_data = []
    for idx, row in df.iterrows():
        movie = {
            'title': row.get('Title', ''),
            'year': clean_year(row.get('Year', None)),
            'critics_score': clean_critics_score(row.get('Critics_Score', None)),
            'cast': row.get('Cast', None) if pd.notna(row.get('Cast')) else None,
            'image_link': row.get('Image_Link', None),
            # Use cleaned columns if available
            'critics_score_2': clean_critics_score(row.get('Critics_Score_Clean', None)),
            'year_2': clean_year(row.get('Year_Clean', None))
        }
        
        # Prefer cleaned values if available
        if 'Critics_Score_Clean' in df.columns and pd.notna(row.get('Critics_Score_Clean')):
            movie['critics_score'] = movie['critics_score_2']
        if 'Year_Clean' in df.columns and pd.notna(row.get('Year_Clean')):
            movie['year'] = movie['year_2']
        
        # Clean up temporary fields
        movie.pop('critics_score_2', None)
        movie.pop('year_2', None)
        
        movies_data.append(movie)
    
    # Bulk insert
    count = db.add_movies_bulk(movies_data, session_id)
    logger.info(f"Inserted {count} movies into database")
    
    # Update session record
    db.update_session_status(session_id, "completed", total_records=count)
    
    # Run quality checks
    logger.info("Running data quality checks...")
    checks = db.run_quality_checks()
    
    for check in checks:
        details_str = str(check.get('details', 'N/A'))[:100] if check.get('details') else "N/A"
        logger.info(f"  {check['check_type']}: {check['status']} - {details_str}...")
    
    # Generate summary statistics
    stats = db.get_score_statistics()
    logger.info(f"\nScore Statistics:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    
    movie_count = db.get_movie_count()
    logger.info(f"\nTotal movies in database: {movie_count}")
    
    # Export to verify
    export_path = "data/movies_from_db.csv"
    db.export_to_csv(export_path)
    logger.info(f"Exported verification copy to {export_path}")
    
    db.close()
    
    return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Import CSV data to SQLite database")
    parser.add_argument("csv_file", nargs="?", default="rotten_tomatoes_700.csv",
                       help="Path to CSV file (default: rotten_tomatoes_700.csv)")
    parser.add_argument("--db", default="database/rotten_tomatoes.db",
                       help="Output database path")
    
    args = parser.parse_args()
    
    # Handle relative paths
    csv_path = args.csv_file
    if not os.path.isabs(csv_path):
        csv_path = os.path.join(os.getcwd(), csv_path)
    
    success = import_csv_to_database(csv_path, args.db)
    
    if success:
        print("\n✓ Import completed successfully!")
        print(f"  Database: {args.db}")
        print(f"  Run 'python analysis/run_full_analysis.py' to analyze the data")
    else:
        print("\n✗ Import failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()