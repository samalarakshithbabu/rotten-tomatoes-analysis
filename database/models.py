"""
Database Models for Rotten Tomatoes Data

This module defines the SQLAlchemy ORM models for storing movie data
and scraping session metadata.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, 
    Boolean, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class ScrapingSession(Base):
    """
    Represents a scraping session with metadata.
    
    Attributes:
        id: Unique session identifier
        target_records: Number of records intended to scrape
        status: Session status (running, completed, failed)
        start_time: When the session started
        end_time: When the session ended
        total_records: Actual number of records scraped
        error_message: Error details if failed
    """
    
    __tablename__ = 'scraping_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    target_records = Column(Integer, nullable=False, default=1500)
    status = Column(String(20), nullable=False, default='running')
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    total_records = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    config_snapshot = Column(Text, nullable=True)  # JSON config
    
    # Relationship to movies
    movies = relationship("Movie", back_populates="session", lazy="dynamic")
    
    def __repr__(self):
        return (
            f"<ScrapingSession(id={self.id}, status='{self.status}', "
            f"records={self.total_records})>"
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'target_records': self.target_records,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_records': self.total_records,
            'error_message': self.error_message
        }


class Movie(Base):
    """
    Represents a movie record from Rotten Tomatoes.
    
    Attributes:
        id: Unique movie identifier
        session_id: Reference to the scraping session
        title: Movie title
        year: Release year
        critics_score: Tomatometer score (0-100)
        audience_score: Audience rating score (0-100)
        cast: Comma-separated cast list
        genres: Comma-separated genre list
        runtime: Runtime in minutes
        rating: MPAA rating (PG, PG-13, R, etc.)
        director: Director name
        tomatometer_status: Certified Fresh, Fresh, or Rotten
        image_link: URL to movie poster
        created_at: When the record was created
    """
    
    __tablename__ = 'movies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('scraping_sessions.id'), nullable=True)
    
    # Core fields
    title = Column(String(500), nullable=False, index=True)
    year = Column(Integer, nullable=True, index=True)
    critics_score = Column(Float, nullable=True)
    audience_score = Column(Float, nullable=True)
    
    # Extended metadata
    cast = Column(Text, nullable=True)
    genres = Column(String(500), nullable=True, index=True)
    runtime = Column(Integer, nullable=True)
    rating = Column(String(10), nullable=True, index=True)
    director = Column(String(200), nullable=True)
    tomatometer_status = Column(String(20), nullable=True)
    image_link = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    session = relationship("ScrapingSession", back_populates="movies")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_movie_title_year', 'title', 'year'),
        Index('idx_movie_scores', 'critics_score', 'audience_score'),
        Index('idx_movie_genre_rating', 'genres', 'rating'),
    )
    
    def __repr__(self):
        return f"<Movie(id={self.id}, title='{self.title[:30]}...', year={self.year})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'title': self.title,
            'year': self.year,
            'critics_score': self.critics_score,
            'audience_score': self.audience_score,
            'cast': self.cast,
            'genres': self.genres,
            'runtime': self.runtime,
            'rating': self.rating,
            'director': self.director,
            'tomatometer_status': self.tomatometer_status,
            'image_link': self.image_link,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate the movie record.
        
        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []
        
        # Required fields
        if not self.title or not self.title.strip():
            errors.append("Title is required")
        
        # Score validation
        if self.critics_score is not None:
            if self.critics_score < 0 or self.critics_score > 100:
                errors.append(f"Critics score {self.critics_score} out of valid range [0, 100]")
        
        if self.audience_score is not None:
            if self.audience_score < 0 or self.audience_score > 100:
                errors.append(f"Audience score {self.audience_score} out of valid range [0, 100]")
        
        # Year validation
        if self.year is not None:
            if self.year < 1800 or self.year > 2030:
                errors.append(f"Year {self.year} is outside valid range")
        
        # Runtime validation
        if self.runtime is not None:
            if self.runtime < 0 or self.runtime > 1000:
                errors.append(f"Runtime {self.runtime} minutes is unrealistic")
        
        return len(errors) == 0, errors


class DataQualityCheck(Base):
    """
    Tracks data quality checks and their results.
    
    Attributes:
        id: Unique check identifier
        check_type: Type of quality check
        table_name: Table being checked
        column_name: Column being checked (if applicable)
        status: pass, fail, or warning
        details: Detailed results of the check
        checked_at: When the check was run
    """
    
    __tablename__ = 'data_quality_checks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    check_type = Column(String(50), nullable=False)
    table_name = Column(String(100), nullable=False)
    column_name = Column(String(100), nullable=True)
    status = Column(String(10), nullable=False)  # pass, fail, warning
    details = Column(Text, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return (
            f"<DataQualityCheck(type='{self.check_type}', "
            f"status='{self.status}')>"
        )