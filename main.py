#!/usr/bin/env python3
"""
Rotten Tomatoes Analysis - Main Entry Point

This is the main entry point for the complete Rotten Tomatoes data analysis
project, including web scraping, database storage, and statistical analysis.

Usage:
    python main.py --help
    python main.py scrape --records 1500
    python main.py import --csv rotten_tomatoes_700.csv
    python main.py analyze
    python main.py dashboard
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Rotten Tomatoes Web Scraper & Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Scrape and analyze data:
    python main.py scrape --records 1000
    python main.py analyze
    
  Import existing CSV:
    python main.py import --csv rotten_tomatoes_700.csv
    
  Run full pipeline:
    python main.py pipeline --csv rotten_tomatoes_700.csv
        
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape Rotten Tomatoes data')
    scrape_parser.add_argument('-n', '--records', type=int, default=1500,
                              help='Number of records to scrape (default: 1500)')
    scrape_parser.add_argument('-o', '--output', default='database/rotten_tomatoes.db',
                              help='Output database path')
    scrape_parser.add_argument('--headless', action='store_true', default=True,
                              help='Run browser in headless mode')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import CSV data to database')
    import_parser.add_argument('--csv', required=True, help='Path to CSV file')
    import_parser.add_argument('--db', default='database/rotten_tomatoes.db',
                              help='Output database path')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Run analysis on database')
    analyze_parser.add_argument('--db', default='database/rotten_tomatoes.db',
                              help='Path to database')
    analyze_parser.add_argument('--output', default='docs/analysis',
                              help='Output directory')
    
    # Pipeline command (full workflow)
    pipeline_parser = subparsers.add_parser('pipeline', help='Run complete pipeline')
    pipeline_parser.add_argument('--csv', help='Optional CSV to import first')
    pipeline_parser.add_argument('--scrape', action='store_true',
                                help='Scrape fresh data instead of importing')
    pipeline_parser.add_argument('--records', type=int, default=1500,
                                help='Records to scrape')
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Launch interactive dashboard')
    dashboard_parser.add_argument('--db', default='database/rotten_tomatoes.db',
                                 help='Path to database')
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    # Execute appropriate command
    if args.command == 'scrape':
        from scraper.scraper import RottenTomatoesScraper, ScraperConfig
        from database.schema import DatabaseManager
        
        print("\n" + "="*60)
        print("NOTE: Rotten Tomatoes may block automated scraping.")
        print("If scraping fails, use 'import' command instead:")
        print("  python main.py import --csv rotten_tomatoes_700.csv")
        print("="*60 + "\n")
        
        config = ScraperConfig(
            target_records=args.records,
            db_path=args.output,
            headless=args.headless
        )
        
        scraper = RottenTomatoesScraper(config)
        movies = scraper.run()
        
        if len(movies) == 0:
            print("\n⚠ Scraping returned 0 movies.")
            print("The website structure may have changed.")
            print("Try importing existing data instead:")
            print("  python main.py import --csv rotten_tomatoes_700.csv")
        else:
            print(f"\n✓ Scraping complete! Collected {len(movies)} movies.")
            print(f"  Database: {args.output}")
            print(f"\nRun 'python main.py analyze' to analyze the data.")
    
    elif args.command == 'import':
        sys.path.insert(0, str(Path(__file__).parent))
        from import_existing_data import import_csv_to_database
        
        success = import_csv_to_database(args.csv, args.db)
        
        if success:
            print(f"\n✓ Import complete!")
            print(f"  Database: {args.db}")
            print(f"\nRun 'python main.py analyze' to analyze the data.")
        else:
            sys.exit(1)
    
    elif args.command == 'analyze':
        sys.path.insert(0, str(Path(__file__).parent))
        from analysis.run_full_analysis import run_analysis_pipeline
        
        run_analysis_pipeline(args.db, args.output)
    
    elif args.command == 'pipeline':
        from database.schema import DatabaseManager
        
        if args.csv and not args.scrape:
            # Import CSV first
            print(f"Importing data from {args.csv}...")
            sys.path.insert(0, str(Path(__file__).parent))
            from import_existing_data import import_csv_to_database
            import_csv_to_database(args.csv)
        
        elif args.scrape:
            # Scrape fresh data
            from scraper.scraper import RottenTomatoesScraper, ScraperConfig
            
            print(f"Scraping {args.records} records...")
            config = ScraperConfig(target_records=args.records)
            scraper = RottenTomatoesScraper(config)
            scraper.run()
        
        # Then analyze
        print("\nRunning analysis...")
        run_analysis_pipeline()
    
    elif args.command == 'dashboard':
        print("Starting interactive dashboard...")
        print("(Note: Run 'jupyter lab' and open docs/dashboard.ipynb for interactive visualization)")
        
        # Create a simple HTML summary
        from database.schema import DatabaseManager
        db = DatabaseManager(args.db)
        df = db.export_to_dataframe()
        db.close()
        
        summary = f"""
        <html>
        <head><title>Rotten Tomatoes Dashboard</title></head>
        <body>
            <h1>Rotten Tomatoes Analysis Dashboard</h1>
            <p>Total Movies: {len(df)}</p>
            <p>Mean Score: {df['critics_score'].mean():.1f}%</p>
            <p>Year Range: {df['year'].min()}-{df['year'].max()}</p>
        </body>
        </html>
        """
        
        with open('docs/dashboard.html', 'w') as f:
            f.write(summary)
        
        print(f"Dashboard saved to docs/dashboard.html")


if __name__ == "__main__":
    main()