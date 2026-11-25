"""
Database Schema Manager for SQLite Database Operations

This module provides the DatabaseManager class for handling all database
operations including table creation, data insertion, and queries.
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text, func, and_, or_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .models import Base, Movie, ScrapingSession, DataQualityCheck

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages SQLite database operations for Rotten Tomatoes data.
    
    This class provides methods for:
    - Database initialization and table creation
    - CRUD operations for movies and sessions
    - Data quality checks
    - Export functionality
    
    Attributes:
        db_path: Path to the SQLite database file
        engine: SQLAlchemy engine instance
        SessionLocal: Session factory for creating database sessions
    """
    
    def __init__(self, db_path: str = "database/rotten_tomatoes.db"):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Create engine and session factory
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            connect_args={'check_same_thread': False}
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )
        
        logger.info(f"Database manager initialized for: {db_path}")
    
    def create_tables(self) -> None:
        """
        Create all database tables if they don't exist.
        
        This uses SQLAlchemy's create_all to ensure all models
        are properly mapped to database tables.
        """
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    @contextmanager
    def session(self) -> Session:
        """
        Context manager for database sessions.
        
        Usage:
            with db.session() as session:
                session.query(Movie).all()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    # ========== Movie Operations ==========
    
    def add_movie(self, movie_data: Dict[str, Any], session_id: Optional[int] = None) -> Movie:
        """
        Add a single movie to the database.
        
        Args:
            movie_data: Dictionary containing movie attributes
            session_id: Optional scraping session ID
            
        Returns:
            The created Movie object
        """
        with self.session() as db_session:
            movie = Movie(**movie_data)
            if session_id:
                movie.session_id = session_id
            
            db_session.add(movie)
            db_session.flush()  # Get the ID without committing
            
            logger.debug(f"Added movie: {movie.title[:30]}...")
            return movie
    
    def add_movies_bulk(self, movies_data: List[Dict[str, Any]], 
                       session_id: Optional[int] = None) -> int:
        """
        Add multiple movies efficiently using bulk insert.
        
        Args:
            movies_data: List of movie dictionaries
            session_id: Optional scraping session ID
            
        Returns:
            Number of movies added
        """
        with self.session() as db_session:
            movies = []
            for data in movies_data:
                movie = Movie(**data)
                if session_id:
                    movie.session_id = session_id
                movies.append(movie)
            
            db_session.bulk_save_objects(movies)
            db_session.flush()
            
            count = len(movies)
            logger.info(f"Bulk inserted {count} movies")
            return count
    
    def get_movies(self, session_id: Optional[int] = None,
                  limit: Optional[int] = None,
                  offset: int = 0) -> List[Movie]:
        """
        Retrieve movies from the database.
        
        Args:
            session_id: Optional session ID to filter by
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of Movie objects
        """
        with self.session() as db_session:
            query = db_session.query(Movie)
            
            if session_id:
                query = query.filter(Movie.session_id == session_id)
            
            if offset:
                query = query.offset(offset)
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
    
    def get_movie_by_id(self, movie_id: int) -> Optional[Movie]:
        """
        Get a specific movie by ID.
        
        Args:
            movie_id: The movie's database ID
            
        Returns:
            Movie object or None if not found
        """
        with self.session() as db_session:
            return db_session.query(Movie).filter(Movie.id == movie_id).first()
    
    def get_movies_by_genre(self, genre: str, limit: int = 100) -> List[Movie]:
        """
        Get movies matching a specific genre.
        
        Args:
            genre: Genre to search for (partial match)
            limit: Maximum results
            
        Returns:
            List of matching Movie objects
        """
        with self.session() as db_session:
            return (
                db_session.query(Movie)
                .filter(Movie.genres.ilike(f"%{genre}%"))
                .limit(limit)
                .all()
            )
    
    def get_movies_by_year_range(self, start_year: int, end_year: int) -> List[Movie]:
        """
        Get movies within a year range.
        
        Args:
            start_year: Start year (inclusive)
            end_year: End year (inclusive)
            
        Returns:
            List of Movie objects in range
        """
        with self.session() as db_session:
            return (
                db_session.query(Movie)
                .filter(
                    and_(
                        Movie.year >= start_year,
                        Movie.year <= end_year
                    )
                )
                .all()
            )
    
    def update_movie(self, movie_id: int, **kwargs) -> bool:
        """
        Update movie attributes.
        
        Args:
            movie_id: ID of movie to update
            **kwargs: Field-value pairs to update
            
        Returns:
            True if update successful
        """
        with self.session() as db_session:
            result = (
                db_session.query(Movie)
                .filter(Movie.id == movie_id)
                .update(kwargs)
            )
            return result > 0
    
    def delete_movie(self, movie_id: int) -> bool:
        """
        Delete a movie by ID.
        
        Args:
            movie_id: ID of movie to delete
            
        Returns:
            True if deletion successful
        """
        with self.session() as db_session:
            result = (
                db_session.query(Movie)
                .filter(Movie.id == movie_id)
                .delete()
            )
            return result > 0
    
    # ========== Session Operations ==========
    
    def add_session(self, session_data: ScrapingSession) -> int:
        """
        Create a new scraping session.
        
        Args:
            session_data: ScrapingSession object
            
        Returns:
            ID of the created session
        """
        with self.session() as db_session:
            db_session.add(session_data)
            db_session.flush()
            logger.info(f"Created scraping session: {session_data.id}")
            return session_data.id
    
    def get_session(self, session_id: int) -> Optional[ScrapingSession]:
        """
        Get a session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            ScrapingSession or None
        """
        with self.session() as db_session:
            return (
                db_session.query(ScrapingSession)
                .filter(ScrapingSession.id == session_id)
                .first()
            )
    
    def get_all_sessions(self) -> List[ScrapingSession]:
        """
        Get all scraping sessions.
        
        Returns:
            List of all sessions
        """
        with self.session() as db_session:
            return db_session.query(ScrapingSession).all()
    
    def update_session_status(self, session_id: int, status: str,
                             total_records: Optional[int] = None,
                             error_message: Optional[str] = None) -> bool:
        """
        Update session status.
        
        Args:
            session_id: Session to update
            status: New status
            total_records: Optional record count
            error_message: Optional error details
            
        Returns:
            True if update successful
        """
        with self.session() as db_session:
            updates = {'status': status}
            
            if total_records is not None:
                updates['total_records'] = total_records
            
            if error_message:
                updates['error_message'] = error_message
            
            if status in ('completed', 'failed'):
                updates['end_time'] = datetime.utcnow()
            
            result = (
                db_session.query(ScrapingSession)
                .filter(ScrapingSession.id == session_id)
                .update(updates)
            )
            
            return result > 0
    
    # ========== Statistics and Aggregation ==========
    
    def get_movie_count(self, session_id: Optional[int] = None) -> int:
        """
        Get total movie count.
        
        Args:
            session_id: Optional session filter
            
        Returns:
            Total number of movies
        """
        with self.session() as db_session:
            query = db_session.query(func.count(Movie.id))
            if session_id:
                query = query.filter(Movie.session_id == session_id)
            return query.scalar()
    
    def get_score_statistics(self) -> Dict[str, float]:
        """
        Get aggregate statistics for critic and audience scores.
        
        Returns:
            Dictionary with score statistics
        """
        with self.session() as db_session:
            movies = db_session.query(Movie).all()
            
            critics_scores = [m.critics_score for m in movies if m.critics_score is not None]
            audience_scores = [m.audience_score for m in movies if m.audience_score is not None]
            
            stats = {}
            
            if critics_scores:
                stats['critics_mean'] = np.mean(critics_scores)
                stats['critics_std'] = np.std(critics_scores, ddof=1)  # Sample std
                stats['critics_min'] = np.min(critics_scores)
                stats['critics_max'] = np.max(critics_scores)
                stats['critics_count'] = len(critics_scores)
            
            if audience_scores:
                stats['audience_mean'] = np.mean(audience_scores)
                stats['audience_std'] = np.std(audience_scores, ddof=1)
                stats['audience_min'] = np.min(audience_scores)
                stats['audience_max'] = np.max(audience_scores)
                stats['audience_count'] = len(audience_scores)
            
            return stats
    
    def get_movies_per_year(self) -> Dict[int, int]:
        """
        Get count of movies per release year.
        
        Returns:
            Dictionary mapping year to movie count
        """
        with self.session() as db_session:
            results = (
                db_session.query(
                    Movie.year,
                    func.count(Movie.id)
                )
                .filter(Movie.year.isnot(None))
                .group_by(Movie.year)
                .order_by(Movie.year)
                .all()
            )
            return {int(row.year): row[1] for row in results}
    
    def get_genre_distribution(self) -> Dict[str, int]:
        """
        Get distribution of genres.
        
        Note: Movies may have multiple genres, separated by commas.
        
        Returns:
            Dictionary mapping genre to count
        """
        with self.session() as db_session:
            results = db_session.query(Movie.genres).all()
            
            genre_counts = {}
            for (genres,) in results:
                if genres:
                    for genre in genres.split(','):
                        genre = genre.strip().lower()
                        if genre:
                            genre_counts[genre] = genre_counts.get(genre, 0) + 1
            
            return dict(
                sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
            )
    
    # ========== Data Quality ==========
    
    def run_quality_checks(self) -> List[Dict[str, Any]]:
        """
        Run automated data quality checks.
        
        Checks performed:
        - Null value percentages
        - Score range validation
        - Year range validation
        - Duplicate detection
        - Data completeness
        
        Returns:
            List of dictionaries with check results (serialized for safety)
        """
        checks = []
        
        with self.session() as db_session:
            # Check for null values
            null_check = self._check_null_values(db_session)
            checks.append(self._serialize_check(null_check))
            
            # Check score ranges
            score_check = self._check_score_ranges(db_session)
            checks.append(self._serialize_check(score_check))
            
            # Check year ranges
            year_check = self._check_year_ranges(db_session)
            checks.append(self._serialize_check(year_check))
            
            # Check duplicates
            duplicate_check = self._check_duplicates(db_session)
            checks.append(self._serialize_check(duplicate_check))
            
            # Save to database
            for check in checks:
                db_check = DataQualityCheck(**check)
                db_session.add(db_check)
            
            logger.info(f"Ran {len(checks)} quality checks")
            for check in checks:
                logger.info(f"  {check['check_type']}: {check['status']}")
        
        return checks
    
    def _serialize_check(self, check: DataQualityCheck) -> Dict[str, Any]:
        """Serialize a DataQualityCheck object to dictionary."""
        return {
            'check_type': check.check_type,
            'table_name': check.table_name,
            'column_name': check.column_name,
            'status': check.status,
            'details': check.details,
            'checked_at': check.checked_at
        }
    
    def _check_null_values(self, db_session: Session) -> DataQualityCheck:
        """Check for null values in critical columns."""
        critical_cols = ['title', 'critics_score', 'year']
        null_counts = {}
        
        for col in critical_cols:
            count = db_session.query(
                func.count(getattr(Movie, col))
            ).filter(
                getattr(Movie, col).is_(None)
            ).scalar()
            null_counts[col] = count
        
        total = self.get_movie_count()
        has_issues = any(c > 0 for c in null_counts.values())
        
        return DataQualityCheck(
            check_type='null_check',
            table_name='movies',
            status='warning' if has_issues else 'pass',
            details=json.dumps({
                'total_records': total,
                'null_counts': null_counts,
                'null_percentages': {
                    k: f"{(v/total)*100:.2f}%" if total > 0 else "N/A"
                    for k, v in null_counts.items()
                }
            })
        )
    
    def _check_score_ranges(self, db_session: Session) -> DataQualityCheck:
        """Check that scores are in valid range [0, 100]."""
        # Find invalid scores
        invalid = db_session.query(Movie.id).filter(
            or_(
                Movie.critics_score < 0,
                Movie.critics_score > 100,
                Movie.audience_score < 0,
                Movie.audience_score > 100
            )
        ).count()
        
        return DataQualityCheck(
            check_type='score_range',
            table_name='movies',
            column_name='critics_score, audience_score',
            status='fail' if invalid > 0 else 'pass',
            details=f"Found {invalid} records with scores outside [0, 100] range"
        )
    
    def _check_year_ranges(self, db_session: Session) -> DataQualityCheck:
        """Check that years are in realistic range."""
        invalid = db_session.query(Movie.id).filter(
            or_(
                Movie.year < 1800,
                Movie.year > 2030
            )
        ).count()
        
        return DataQualityCheck(
            check_type='year_range',
            table_name='movies',
            column_name='year',
            status='fail' if invalid > 0 else 'pass',
            details=f"Found {invalid} records with years outside [1800, 2030] range"
        )
    
    def _check_duplicates(self, db_session: Session) -> DataQualityCheck:
        """Check for duplicate titles."""
        from sqlalchemy import func as sql_func
        
        # Find titles that appear more than once
        duplicates = (
            db_session.query(Movie.title, sql_func.count(Movie.id))
            .group_by(Movie.title)
            .having(sql_func.count(Movie.id) > 1)
            .count()
        )
        
        return DataQualityCheck(
            check_type='duplicate_check',
            table_name='movies',
            column_name='title',
            status='warning' if duplicates > 0 else 'pass',
            details=f"Found {duplicates} duplicate movie titles"
        )
    
    # ========== Export ==========
    
    def export_to_dataframe(self, session_id: Optional[int] = None):
        """
        Export movie data to a Pandas DataFrame.
        
        Args:
            session_id: Optional session filter
            
        Returns:
            Pandas DataFrame with movie data
        """
        import pandas as pd
        
        with self.session() as db_session:
            query = db_session.query(Movie)
            
            if session_id:
                query = query.filter(Movie.session_id == session_id)
            
            # Use column-based approach to avoid ORM detachment issues
            movies = query.all()
            
            # Build DataFrame directly from columns
            data = []
            for m in movies:
                data.append({
                    'id': m.id,
                    'session_id': m.session_id,
                    'title': m.title,
                    'year': m.year,
                    'critics_score': m.critics_score,
                    'audience_score': m.audience_score,
                    'cast': m.cast,
                    'genres': m.genres,
                    'runtime': m.runtime,
                    'rating': m.rating,
                    'director': m.director,
                    'tomatometer_status': m.tomatometer_status,
                    'image_link': m.image_link,
                    'created_at': m.created_at.isoformat() if m.created_at else None
                })
            
            return pd.DataFrame(data)
    
    def export_to_csv(self, filepath: str, session_id: Optional[int] = None) -> None:
        """
        Export movie data to a CSV file.
        
        Args:
            filepath: Output file path
            session_id: Optional session filter
        """
        df = self.export_to_dataframe(session_id)
        df.to_csv(filepath, index=False)
        logger.info(f"Exported {len(df)} records to {filepath}")
    
    # ========== Database Management ==========
    
    def vacuum(self) -> None:
        """Run VACUUM to reclaim space after deletions."""
        with self.session() as db_session:
            db_session.execute(text("VACUUM"))
            logger.info("Database vacuumed")
    
    def close(self) -> None:
        """Close the database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")
    
    def drop_all_tables(self) -> None:
        """
        Drop all tables (use with caution!).
        
        This is irreversible and deletes all data.
        """
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("All database tables dropped")
    
    def backup(self, backup_path: str) -> None:
        """
        Create a backup of the database.
        
        Args:
            backup_path: Path for the backup file
        """
        import shutil
        
        # Ensure any pending changes are written
        self.engine.connect().close()
        
        # Copy the database file
        shutil.copy2(self.db_path, backup_path)
        logger.info(f"Database backed up to {backup_path}")