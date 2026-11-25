# Rotten Tomatoes Movie Dataset - Data Dictionary

This document describes all fields in the `rotten_tomatoes.db` SQLite database and exported CSV files.

## Table: movies

Primary table containing movie information scraped from Rotten Tomatoes.

| Field | Data Type | Description | Values/Range | Data Quality |
|-------|-----------|-------------|--------------|--------------|
| `id` | INTEGER | Unique movie identifier | Auto-incrementing | Always present |
| `session_id` | INTEGER | Foreign key to scraping session | References scraping_sessions.id | NULL if scraped before sessions were tracked |
| `title` | STRING | Movie title | Free text, max 500 chars | **Required** - no nulls in valid data |
| `year` | INTEGER | Release year | 1800-2030 | ~50% missing - many entries don't show year in search results |
| `critics_score` | FLOAT | Tomatometer score (critics) | 0-100 | ~60% missing - not all movies have scores |
| `audience_score` | FLOAT | Audience rating score | 0-100 | ~80% missing - not always displayed |
| `cast` | TEXT | Top cast members | Free text, comma-separated | ~60% missing - loaded via Shadow DOM |
| `genres` | STRING | Movie genres | Free text, comma-separated | ~70% missing - genre info not in basic search |
| `runtime` | INTEGER | Movie runtime in minutes | 1-500 | ~80% missing - runtime not in basic search |
| `rating` | STRING | MPAA rating | G, PG, PG-13, R, NC-17 | ~80% missing - rating not in basic search |
| `director` | STRING | Director name | Free text | ~90% missing - director not in basic search |
| `tomatometer_status` | STRING | Certified status | "Certified Fresh", "Fresh", "Rotten" | ~60% missing - tied to critics_score |
| `image_link` | TEXT | URL to movie poster | Valid URL string | Available for most entries |
| `created_at` | DATETIME | Record creation timestamp | ISO 8601 format | Auto-generated |

### Interpretation of Key Fields

#### critics_score
- **Definition**: Percentage of positive critic reviews from Rotten Tomatoes' Tomatometer
- **Interpretation Guide**:
  - 75-100%: "Fresh" - generally favorable
  - 60-74%: Mixed reviews
  - 0-59%: "Rotten" - generally unfavorable

#### tomatometer_status
- **Certified Fresh**: Must have a consistent Tomatometer of 75%+ with a minimum number of reviews
- **Fresh**: Score of 75%+
- **Rotten**: Score below 75%

#### genres
- Multiple genres are comma-separated
- Examples: "Action, Adventure, Sci-Fi" or "Drama, Romance"
- Note: Genres are user-assigned and may vary by source

## Table: scraping_sessions

Metadata about each scraping run.

| Field | Data Type | Description | Values/Range |
|-------|-----------|-------------|--------------|
| `id` | INTEGER | Unique session identifier | Auto-incrementing |
| `target_records` | INTEGER | Intended number of records | User-specified (default 1500) |
| `status` | STRING | Session outcome | "running", "completed", "failed" |
| `start_time` | DATETIME | When scraping began | ISO 8601 format |
| `end_time` | DATETIME | When scraping ended | ISO 8601 format, NULL if running |
| `total_records` | INTEGER | Actual records scraped | 0-target_records |
| `error_message` | TEXT | Error details if failed | Free text, NULL if successful |
| `config_snapshot` | TEXT | JSON config snapshot | Configuration parameters |

## Table: data_quality_checks

Results of automated data quality checks.

| Field | Data Type | Description | Values/Range |
|-------|-----------|-------------|--------------|
| `id` | INTEGER | Unique check identifier | Auto-incrementing |
| `check_type` | STRING | Type of check | "null_check", "score_range", "year_range", "duplicate_check" |
| `table_name` | STRING | Table checked | "movies" |
| `column_name` | STRING | Column checked | Varies by check type |
| `status` | STRING | Check result | "pass", "fail", "warning" |
| `details` | TEXT | Check details | JSON-formatted results |
| `checked_at` | DATETIME | When check ran | ISO 8601 format |

## Derived Fields

The analysis scripts create additional derived fields:

| Field | Source | Description |
|-------|--------|-------------|
| `decade` | `year // 10 * 10` | Decade of release (e.g., 1990 for years 1990-1999) |
| `genre_action` | `genres` contains "Action" | Binary indicator for Action genre |
| `genre_comedy` | `genres` contains "Comedy" | Binary indicator for Comedy genre |
| `genre_drama` | `genres` contains "Drama" | Binary indicator for Drama genre |
| `genre_horror` | `genres` contains "Horror" | Binary indicator for Horror genre |
| `genre_thriller` | `genres` contains "Thriller" | Binary indicator for Thriller genre |
| `Score_Category` | `critics_score` | Categorical: "HIT (>=75%)", "Below Average (<60%)" |

## Data Quality Notes

### Known Issues

1. **Missing Year Data (~50%)**: The basic search results don't always display the year. This requires navigating to individual movie pages to get year information.

2. **Missing Score Data (~60%)**: New or obscure movies may not have enough critic reviews yet to generate a Tomatometer score.

3. **Missing Cast Information (~60%)**: Cast is loaded from Shadow DOM, which may not render correctly for all elements.

4. **Survivorship Bias**: Older movies that remain in the Rotten Tomatoes database tend to be well-regarded classics. This is explicitly addressed in the regression analysis.

### Quality Checks Performed

1. **Null Value Analysis**: Tracks missing data by column
2. **Score Range Validation**: Ensures scores are 0-100
3. **Year Range Validation**: Ensures years are reasonable (1800-2030)
4. **Duplicate Detection**: Identifies duplicate movie titles

## Example Queries

```sql
-- Get movies with high critic scores
SELECT title, critics_score, year 
FROM movies 
WHERE critics_score >= 75 
ORDER BY critics_score DESC 
LIMIT 20;

-- Count movies by decade
SELECT decade, COUNT(*) as count
FROM (
    SELECT (year // 10) * 10 as decade
    FROM movies 
    WHERE year IS NOT NULL
)
GROUP BY decade
ORDER BY decade;

-- Get average score by genre
SELECT 
    SUBSTR(genres, 1, INSTR(genres, ',') - 1) as primary_genre,
    AVG(critics_score) as avg_score,
    COUNT(*) as movie_count
FROM movies
WHERE genres IS NOT NULL
GROUP BY primary_genre
HAVING COUNT(*) >= 10
ORDER BY avg_score DESC;
```