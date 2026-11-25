"""
Configuration for the Rotten Tomatoes Scraper
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScraperConfig:
    """Configuration for the web scraper."""
    
    # Browser settings
    headless: bool = True
    window_width: int = 1920
    window_height: int = 1080
    
    # Scraping settings
    target_records: int = 1500
    page_delay: float = 1.5
    scroll_delay: float = 0.3
    max_retries: int = 3
    retry_delay: float = 5.0
    
    # Timeout settings
    implicit_wait: float = 10.0
    explicit_wait: float = 15.0
    
    # Output settings
    output_dir: str = "data"
    db_path: str = "database/rotten_tomatoes.db"
    
    # Rate limiting
    request_delay: float = 2.0
    
    @classmethod
    def from_env(cls) -> 'ScraperConfig':
        """Create config from environment variables."""
        import os
        return cls(
            headless=os.getenv('HEADLESS', 'True').lower() == 'true',
            target_records=int(os.getenv('TARGET_RECORDS', '1500')),
            page_delay=float(os.getenv('PAGE_DELAY', '1.5')),
            db_path=os.getenv('DB_PATH', 'database/rotten_tomatoes.db')
        )