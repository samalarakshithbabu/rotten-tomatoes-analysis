#!/usr/bin/env python3
"""
Full Analysis Pipeline

This script runs the complete analysis pipeline on the Rotten Tomatoes data:
1. Load data from database
2. Run descriptive statistics
3. Perform Kruskal-Wallis tests
4. Run regression analysis
5. Generate visualizations
6. Create summary report
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_analysis_pipeline(db_path: str = "database/rotten_tomatoes.db",
                         output_dir: str = "docs/analysis"):
    """
    Run the complete analysis pipeline.
    
    Args:
        db_path: Path to SQLite database
        output_dir: Directory for analysis outputs
    """
    logger.info("=" * 60)
    logger.info("ROTTEN TOMATOES ANALYSIS PIPELINE")
    logger.info(f"Started: {datetime.now().isoformat()}")
    logger.info("=" * 60)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(f"{output_dir}/charts", exist_ok=True)
    
    # Import analysis modules
    from database.schema import DatabaseManager
    from analysis.statistical_analysis import StatisticalAnalyzer
    from analysis.regression import RegressionAnalyzer
    from analysis.visualization import MovieVisualizer
    
    # ========== Step 1: Load Data ==========
    logger.info("\n[1/6] Loading data from database...")
    
    db = DatabaseManager(db_path)
    df = db.export_to_dataframe()
    
    logger.info(f"Loaded {len(df)} movies")
    logger.info(f"Columns: {list(df.columns)}")
    
    # Display data quality
    missing_pct = (df.isnull().sum() / len(df) * 100).round(1)
    logger.info(f"\nMissing Data Summary:")
    for col, pct in missing_pct.items():
        if pct > 0:
            logger.info(f"  {col}: {pct}%")
    
    # ========== Step 2: Descriptive Statistics ==========
    logger.info("\n[2/6] Computing descriptive statistics...")
    
    stats_analyzer = StatisticalAnalyzer(df)
    descriptive = stats_analyzer.get_descriptive_stats()
    
    # Save descriptive stats
    descriptive.to_csv(f"{output_dir}/descriptive_statistics.csv")
    logger.info(f"Saved descriptive statistics to {output_dir}/descriptive_statistics.csv")
    
    print("\nDescriptive Statistics Summary:")
    print(descriptive.round(2))
    
    # ========== Step 3: Statistical Tests ==========
    logger.info("\n[3/6] Running statistical tests...")
    
    results = {}
    
    # 3a. Kruskal-Wallis by Decade
    logger.info("Running Kruskal-Wallis test by decade...")
    
    # Create decade column for both df and stats_analyzer
    df['decade'] = (df['year'] // 10) * 10
    stats_analyzer.df = df  # Update analyzer's dataframe
    
    try:
        kw_result = stats_analyzer.run_kruskal_wallis('decade', 'critics_score')
        results['kruskal_wallis_decade'] = kw_result.to_dict()
        
        print(f"\nKruskal-Wallis Results:")
        print(f"  H-statistic: {kw_result.statistic:.2f}")
        print(f"  p-value: {kw_result.p_value:.6f}")
        if kw_result.effect_size is not None:
            print(f"  Effect size (ε²): {kw_result.effect_size:.4f} ({kw_result.effect_size_label})")
        else:
            print("  Effect size: N/A (insufficient data)")
    except Exception as e:
        logger.warning(f"Kruskal-Wallis test failed: {e}")
        kw_result = None
        results['kruskal_wallis_decade'] = {'error': str(e)}
    
    # 3b. Pairwise comparisons by decade
    logger.info("Running pairwise comparisons...")
    try:
        pairwise = stats_analyzer.run_pairwise_comparisons('decade', 'critics_score')
        if not pairwise.empty:
            results['pairwise_decade'] = pairwise.to_dict('records')
            pairwise.to_csv(f"{output_dir}/pairwise_comparisons.csv", index=False)
        else:
            results['pairwise_decade'] = []
            logger.warning("No valid pairwise comparisons (insufficient data per group)")
    except Exception as e:
        logger.warning(f"Pairwise comparisons failed: {e}")
        results['pairwise_decade'] = []

    # 3c. Compare decades (summary)
    try:
        _, decade_summary = stats_analyzer.compare_decades()
        if not decade_summary.empty:
            decade_summary.to_csv(f"{output_dir}/decade_summary.csv")
            print("\nDecade Summary:")
            print(decade_summary.round(2))
        else:
            logger.warning("No decade summary available")
    except Exception as e:
        logger.warning(f"Decade comparison failed: {e}")
        decade_summary = pd.DataFrame()
    
    # ========== Step 4: Regression Analysis ==========
    logger.info("\n[4/6] Running regression analysis...")
    
    reg_analyzer = RegressionAnalyzer(df)
    
    # Controlled regression
    try:
        reg_result = reg_analyzer.run_ols_regression('critics_score')
        results['regression_controlled'] = {
            'r_squared': reg_result.r_squared,
            'adjusted_r_squared': reg_result.adjusted_r_squared,
            'f_statistic': reg_result.f_statistic,
            'f_pvalue': reg_result.f_pvalue,
            'coefficients': reg_result.coefficients.to_dict(),
            'significant_vars': reg_result.significant_vars,
            'vif_scores': reg_result.vif_scores.to_dict(),
            'diagnostics': reg_result.diagnostics
        }
        
        print(f"\nRegression Results:")
        print(f"  R² = {reg_result.r_squared:.4f}")
        print(f"  Adjusted R² = {reg_result.adjusted_r_squared:.4f}")
        print(f"  F-statistic = {reg_result.f_statistic:.2f}")
        print(f"  Significant predictors: {reg_result.significant_vars}")
        
        # Compare controlled vs uncontrolled
        logger.info("Comparing controlled vs uncontrolled models...")
        comparison = reg_analyzer.compare_controlled_vs_uncontrolled()
        results['model_comparison'] = comparison
        
        print("\nModel Comparison:")
        print(f"  Uncontrolled R²: {comparison['uncontrolled_model']['r_squared']:.4f}")
        print(f"  Controlled R²: {comparison['controlled_model']['r_squared']:.4f}")
        
    except Exception as e:
        logger.warning(f"Regression analysis failed: {e}")
        results['regression_controlled'] = {'error': str(e)}
        reg_result = None
    
    # ========== Step 5: Visualization ==========
    logger.info("\n[5/6] Generating visualizations...")
    
    viz = MovieVisualizer(df)
    
    # Create all charts
    charts = viz.create_summary_dashboard(f"{output_dir}/charts")
    
    # Additional charts
    viz.plot_score_by_group('decade', save_path=f"{output_dir}/charts/score_by_decade.png")
    viz.plot_correlation_matrix(save_path=f"{output_dir}/charts/correlation_matrix.png")
    
    import matplotlib.pyplot as plt
    plt.close('all')  # Free memory
    
    logger.info(f"Saved {len(charts)} charts to {output_dir}/charts/")
    
    # ========== Step 6: Generate Report ==========
    logger.info("\n[6/6] Generating summary report...")
    
    report = {
        'analysis_date': datetime.now().isoformat(),
        'data_summary': {
            'total_movies': len(df),
            'year_range': f"{df['year'].min()}-{df['year'].max()}" if df['year'].notna().any() else "N/A",
            'movies_with_scores': df['critics_score'].notna().sum(),
            'score_mean': float(df['critics_score'].mean()),
            'score_median': float(df['critics_score'].median())
        },
        'statistical_tests': {
            'kruskal_wallis': results.get('kruskal_wallis_decade', {}),
            'pairwise_comparisons': results.get('pairwise_decade', [])
        },
        'regression': results.get('regression_controlled', {}),
        'interpretation': reg_result.interpretation if reg_result else "Insufficient data for regression analysis"
    }
    
    # Save JSON report
    with open(f"{output_dir}/analysis_report.json", 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    # Save text summary
    def safe_format(val, fmt=".2f", default="N/A"):
        """Safely format a value that might be None."""
        return fmt.format(val) if val is not None and not (isinstance(val, float) and (val != val or float('inf') if isinstance(val, float) else False)) else default
    
    summary_text = f"""
ROTTEN TOMATOES ANALYSIS REPORT
{'=' * 50}
Generated: {datetime.now().isoformat()}

DATA SUMMARY
------------
Total Movies: {len(df)}
Movies with Scores: {df['critics_score'].notna().sum()}
Year Range: {df['year'].min() if df['year'].notna().any() else 'N/A'} - {df['year'].max() if df['year'].notna().any() else 'N/A'}
Mean Score: {df['critics_score'].mean():.1f}%
Median Score: {df['critics_score'].median():.1f}%

STATISTICAL ANALYSIS
--------------------
Kruskal-Wallis H-test (by decade):
  H-statistic: {safe_format(kw_result.statistic if kw_result else None)}
  p-value: {safe_format(kw_result.p_value if kw_result else None, ".6f")}
  Effect size (epsilon-squared): {safe_format(kw_result.effect_size if kw_result else None) if kw_result else 'N/A'}
  Significant: {'Yes' if kw_result and kw_result.significant else 'No'}

REGRESSION ANALYSIS
-------------------
Model: OLS with robust standard errors
R²: {safe_format(reg_result.r_squared if reg_result else None)}
Adjusted R²: {safe_format(reg_result.adjusted_r_squared if reg_result else None)}
F-statistic: {safe_format(reg_result.f_statistic if reg_result else None)}

Significant Predictors:
{chr(10).join(['  - ' + v for v in reg_result.significant_vars]) if reg_result and reg_result.significant else '  None'}

SIGNIFICANT VARIABLES: {', '.join(reg_result.significant_vars) if reg_result and reg_result.significant else 'None'}

KEY FINDINGS
------------
1. Decade effects analyzed with Kruskal-Wallis H-test
2. Genre, runtime, and vote count controlled in regression
3. Effect sizes reported (ε² for Kruskal-Wallis)
4. Multiple comparison corrections applied (Bonferroni)

FILES GENERATED
---------------
- descriptive_statistics.csv
- pairwise_comparisons.csv
- decade_summary.csv
- analysis_report.json
- charts/ (visualizations)
"""
    
    with open(f"{output_dir}/analysis_summary.txt", 'w', encoding='utf-8') as f:
        f.write(summary_text)
    
    print(summary_text)
    
    db.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("ANALYSIS COMPLETE")
    logger.info(f"Output directory: {output_dir}")
    logger.info("=" * 60)
    
    return report


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run full analysis pipeline")
    parser.add_argument("--db", default="database/rotten_tomatoes.db",
                       help="Path to SQLite database")
    parser.add_argument("--output", default="docs/analysis",
                       help="Output directory for analysis results")
    
    args = parser.parse_args()
    
    run_analysis_pipeline(args.db, args.output)
    
    print(f"\n✓ Analysis complete! Check {args.output}/ for results.")


if __name__ == "__main__":
    main()
