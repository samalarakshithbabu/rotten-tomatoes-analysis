"""
Rotten Tomatoes Web Scraper Module

This module provides a reusable, configurable web scraper for Rotten Tomatoes
movie data. It handles dynamic page elements, Shadow DOM extraction, and
stores results in SQLite database.

Usage:
    from scraper import RottenTomatoesScraper, ScraperConfig
    
    config = ScraperConfig(target_records=500)
    scraper = RottenTomatoesScraper(config)
    scraper.run()
    movies = scraper.get_movies()
"""

import time
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

import numpy as np
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException,
    WebDriverException
)

from database.models import Movie, ScrapingSession
from database.schema import DatabaseManager
from .config import ScraperConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ScrapedMovie:
    """Data class for scraped movie information."""
    title: str
    year: Optional[int] = None
    critics_score: Optional[float] = None
    audience_score: Optional[float] = None
    cast: Optional[str] = None
    genres: Optional[str] = None
    runtime: Optional[int] = None
    rating: Optional[str] = None
    director: Optional[str] = None
    tomatometer_status: Optional[str] = None
    image_link: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
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
            'image_link': self.image_link
        }


class RottenTomatoesScraper:
    """
    A configurable web scraper for Rotten Tomatoes movie data.
    
    This scraper handles:
    - Dynamic page loading with Selenium
    - Shadow DOM element extraction
    - Cookie consent handling
    - Pagination and data collection
    - SQLite database storage
    
    Attributes:
        config: ScraperConfig instance with scraping parameters
        driver: Selenium WebDriver instance
        db_manager: DatabaseManager for data persistence
        movies: List of scraped movies
    """
    
    BASE_URL = "https://www.rottentomatoes.com/"
    
    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize the scraper with configuration.
        
        Args:
            config: ScraperConfig instance. If None, uses defaults.
        """
        self.config = config or ScraperConfig()
        self.driver: Optional[webdriver.Chrome] = None
        self.db_manager = DatabaseManager(self.config.db_path)
        self.movies: List[ScrapedMovie] = []
        self.session_id: Optional[int] = None
        
    def _setup_driver(self) -> webdriver.Chrome:
        """
        Configure and initialize the Chrome WebDriver.
        
        Returns:
            Configured Chrome WebDriver instance
        """
        options = Options()
        
        if self.config.headless:
            options.add_argument("--headless")
        
        # Window settings
        options.add_argument(f"--window-size={self.config.window_width},{self.config.window_height}")
        options.add_argument("--start-maximized")
        
        # Performance and stability options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-browser-side-navigation")
        options.add_argument("--disable-logging")
        options.add_argument("--mute-audio")
        
        # User agent
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Ignore certificate errors
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--allow-running-insecure-content")
        
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(self.config.implicit_wait)
        
        logger.info("WebDriver initialized successfully")
        return driver
    
    def _accept_cookies(self) -> bool:
        """
        Handle cookie consent popup.
        
        Returns:
            True if cookies accepted successfully, False otherwise
        """
        try:
            accept_btn = WebDriverWait(self.driver, self.config.explicit_wait).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            accept_btn.click()
            time.sleep(0.5)
            logger.info("Cookie consent accepted")
            return True
        except TimeoutException:
            logger.warning("Cookie consent button not found - continuing anyway")
            return True
        except Exception as e:
            logger.error(f"Error accepting cookies: {e}")
            return False
    
    def _extract_movies_from_page(self) -> List[ScrapedMovie]:
        """
        Extract movie data from the current page.
        
        Returns:
            List of ScrapedMovie objects from current page
        """
        movies = []
        try:
            # Find all movie row elements
            rows = self.driver.find_elements(By.TAG_NAME, "search-page-media-row")
            logger.info(f"Found {len(rows)} movie rows on current page")
            
            for row in rows:
                try:
                    movie = self._extract_movie_from_row(row)
                    if movie and movie.title:
                        movies.append(movie)
                except Exception as e:
                    logger.warning(f"Error extracting movie from row: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting movies from page: {e}")
        
        return movies
    
    def _extract_movie_from_row(self, row) -> Optional[ScrapedMovie]:
        """
        Extract data from a single movie row element.
        
        Args:
            row: Selenium WebElement for the movie row
            
        Returns:
            ScrapedMovie object or None if extraction fails
        """
        movie = ScrapedMovie(title="")
        
        try:
            # Extract title (light DOM)
            try:
                title_elem = row.find_element(By.CSS_SELECTOR, '[slot="title"]')
                movie.title = title_elem.text.strip()
            except NoSuchElementException:
                return None
            
            # Get shadow root for nested elements
            try:
                shadow = self.driver.execute_script(
                    "return arguments[0].shadowRoot", row
                )
            except:
                shadow = None
            
            if shadow:
                # Extract year
                try:
                    year_elem = shadow.find_element(By.CSS_SELECTOR, '[data-qa="info-year"]')
                    year_text = year_elem.text.strip()
                    if year_text:
                        # Extract year from format like "(2023)"
                        movie.year = int(year_text.strip("()"))
                except NoSuchElementException:
                    pass
                
                # Extract critics score
                try:
                    score_elem = shadow.find_element(By.CLASS_NAME, "critics-score")
                    score_text = score_elem.text.strip()
                    if score_text and "%" in score_text:
                        movie.critics_score = float(score_text.strip("%"))
                except NoSuchElementException:
                    pass
                
                # Extract tomatometer status
                try:
                    status_elem = shadow.find_element(By.CLASS_NAME, "tomatometer-status")
                    movie.tomatometer_status = status_elem.text.strip()
                except NoSuchElementException:
                    pass
                
                # Extract cast
                try:
                    cast_elem = shadow.find_element(By.CSS_SELECTOR, '[data-qa="info-cast"]')
                    movie.cast = cast_elem.text.strip() or None
                except NoSuchElementException:
                    pass
            
            # Extract image link (light DOM)
            try:
                img = row.find_element(By.CSS_SELECTOR, '[slot="thumbnail"] img')
                movie.image_link = img.get_attribute("src")
            except NoSuchElementException:
                pass
                
        except Exception as e:
            logger.warning(f"Error processing movie row: {e}")
        
        return movie
    
    def _navigate_to_next_page(self) -> bool:
        """
        Navigate to the next page of results.
        
        Returns:
            True if navigation successful, False if no more pages
        """
        try:
            # Scroll to bottom to load pagination
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(self.config.scroll_delay)
            
            # Find and click next button
            next_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-qa="paging-btn-next"]'))
            )
            
            # Scroll to button and click via JavaScript
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_btn)
            time.sleep(self.config.scroll_delay)
            self.driver.execute_script("arguments[0].click();", next_btn)
            
            # Wait for new content to load
            time.sleep(self.config.page_delay)
            
            return True
            
        except TimeoutException:
            logger.info("No more pages to navigate")
            return False
        except Exception as e:
            logger.warning(f"Error navigating to next page: {e}")
            return False
    
    def _handle_rate_limiting(self, page_num: int) -> None:
        """
        Implement rate limiting to avoid being blocked.
        
        Args:
            page_num: Current page number
        """
        # Add delay between pages
        time.sleep(self.config.request_delay)
        
        # Optional: Add random variation
        if page_num % 10 == 0:
            logger.info(f"Rate limiting pause at page {page_num}")
            time.sleep(2.0)
    
    def initialize(self) -> bool:
        """
        Initialize the scraper (setup database, start browser).
        
        Returns:
            True if initialization successful
        """
        try:
            # Initialize database
            self.db_manager.create_tables()
            
            # Create scraping session record
            session = ScrapingSession(
                target_records=self.config.target_records,
                status="running"
            )
            self.session_id = self.db_manager.add_session(session)
            logger.info(f"Scraping session {self.session_id} started")
            
            # Setup WebDriver
            self.driver = self._setup_driver()
            
            # Navigate to base URL
            self.driver.get(self.BASE_URL)
            
            # Handle cookies
            self._accept_cookies()
            
            logger.info("Scraper initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    def run(self, search_term: str = "") -> List[ScrapedMovie]:
        """
        Run the complete scraping process.
        
        Args:
            search_term: Optional search term to filter results
            
        Returns:
            List of scraped movies
        """
        if not self.initialize():
            logger.error("Failed to initialize scraper")
            return []
        
        page_num = 0
        total_scraped = 0
        
        try:
            # Navigate to search if term provided
            if search_term:
                self._navigate_to_search(search_term)
            
            while total_scraped < self.config.target_records:
                page_num += 1
                logger.info(f"Scraping page {page_num}...")
                
                # Extract movies from current page
                page_movies = self._extract_movies_from_page()
                
                if not page_movies:
                    logger.warning(f"No movies found on page {page_num}")
                    # Try a few more pages before giving up
                    if page_num > 3:
                        logger.info("No movies for several pages - ending scrape")
                        break
                    continue
                
                # Add to collection
                self.movies.extend(page_movies)
                total_scraped = len(self.movies)
                
                logger.info(f"Page {page_num}: {len(page_movies)} movies, "
                          f"Total: {total_scraped}/{self.config.target_records}")
                
                # Save to database
                for movie in page_movies:
                    self.db_manager.add_movie(movie.to_dict(), self.session_id)
                
                # Check if we have enough
                if total_scraped >= self.config.target_records:
                    break
                
                # Navigate to next page
                if not self._navigate_to_next_page():
                    logger.info("Reached end of pagination")
                    break
                
                # Rate limiting
                self._handle_rate_limiting(page_num)
            
            # Update session status
            if self.session_id:
                self.db_manager.update_session_status(
                    self.session_id, 
                    "completed",
                    total_records=total_scraped
                )
            
            logger.info(f"Scraping completed. Total movies: {total_scraped}")
            return self.movies
            
        except WebDriverException as e:
            logger.error(f"WebDriver error during scraping: {e}")
            if self.session_id:
                self.db_manager.update_session_status(
                    self.session_id, 
                    "failed",
                    error_message=str(e)
                )
            return self.movies
        except Exception as e:
            logger.error(f"Unexpected error during scraping: {e}")
            return self.movies
        finally:
            self.cleanup()
    
    def _navigate_to_search(self, search_term: str) -> None:
        """
        Navigate to search results for a term.
        
        Args:
            search_term: Movie title or keyword to search
        """
        try:
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="header-main"]/search-results-nav/search-results-controls/input')
                )
            )
            search_box.clear()
            search_box.send_keys(search_term)
            search_box.submit()
            
            # Wait for results
            time.sleep(self.config.page_delay)
            logger.info(f"Navigated to search: {search_term}")
            
        except Exception as e:
            logger.warning(f"Could not navigate to search: {e}")
    
    def get_movies(self) -> List[ScrapedMovie]:
        """
        Get the list of scraped movies.
        
        Returns:
            List of ScrapedMovie objects
        """
        return self.movies
    
    def get_movies_from_db(self, session_id: Optional[int] = None) -> List[Dict]:
        """
        Retrieve movies from database.
        
        Args:
            session_id: Optional session ID to filter by
            
        Returns:
            List of movie dictionaries
        """
        return self.db_manager.get_movies(session_id)
    
    def cleanup(self) -> None:
        """Clean up resources (close browser, etc.)."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None


def main():
    """Main entry point for running the scraper."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Scrape Rotten Tomatoes movie data"
    )
    parser.add_argument(
        "-n", "--records",
        type=int,
        default=1500,
        help="Number of records to scrape (default: 1500)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="database/rotten_tomatoes.db",
        help="Output database path"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run in headless mode (no browser window)"
    )
    
    args = parser.parse_args()
    
    config = ScraperConfig(
        target_records=args.records,
        db_path=args.output,
        headless=args.headless
    )
    
    scraper = RottenTomatoesScraper(config)
    movies = scraper.run()
    
    print(f"\nScraping completed! Total movies collected: {len(movies)}")
    
    # Export to CSV for convenience
    if movies:
        import pandas as pd
        df = pd.DataFrame([m.to_dict() for m in movies])
        df.to_csv("data/movies.csv", index=False)
        print(f"Exported to data/movies.csv")


if __name__ == "__main__":
    main()