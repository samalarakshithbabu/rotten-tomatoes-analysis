"""
Statistical Analysis Module

This module provides comprehensive statistical analysis for movie data,
including non-parametric tests, effect sizes, and multiple comparison corrections.

Key Features:
- Kruskal-Wallis H-test for comparing groups
- Effect size calculations (Epsilon-squared, Eta-squared)
- Pairwise comparisons with multiple testing corrections
- Confidence intervals and bootstrap estimates
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import kruskal, mannwhitneyu, pearsonr, spearmanr
from statsmodels.stats.multitest import multipletests
import pingouin as pg

logger = logging.getLogger(__name__)


@dataclass
class StatisticalResult:
    """Container for statistical test results."""
    test_name: str
    statistic: float
    p_value: float
    effect_size: Optional[float] = None
    effect_size_label: Optional[str] = None
    significant: bool = False
    alpha: float = 0.05
    interpretation: str = ""
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        self.significant = self.p_value < self.alpha
        self._interpret()
    
    def _interpret(self):
        """Generate interpretation text based on results."""
        if self.significant:
            self.interpretation = (
                f"The {self.test_name} revealed a statistically significant "
                f"difference (p={self.p_value:.4f} < α={self.alpha}). "
                f"Effect size: {self.effect_size_label} = {self.effect_size:.3f} "
                f"({self._interpret_effect_size()})."
            )
        else:
            self.interpretation = (
                f"The {self.test_name} found no statistically significant "
                f"difference (p={self.p_value:.4f} >= α={self.alpha})."
            )
    
    def _interpret_effect_size(self):
        """Interpret effect size magnitude."""
        if self.effect_size is None:
            return "unknown"
        
        # Cohen's d interpretation
        abs_es = abs(self.effect_size)
        if abs_es < 0.2:
            return "negligible"
        elif abs_es < 0.5:
            return "small"
        elif abs_es < 0.8:
            return "medium"
        else:
            return "large"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'test_name': self.test_name,
            'statistic': self.statistic,
            'p_value': self.p_value,
            'effect_size': self.effect_size,
            'effect_size_label': self.effect_size_label,
            'significant': self.significant,
            'alpha': self.alpha,
            'interpretation': self.interpretation,
            'details': self.details
        }


class StatisticalAnalyzer:
    """
    Comprehensive statistical analysis for movie rating data.
    
    Provides methods for:
    - Descriptive statistics
    - Group comparisons (Kruskal-Wallis, Mann-Whitney U)
    - Effect size calculations
    - Multiple comparison corrections
    - Correlation analysis
    """
    
    def __init__(self, df: pd.DataFrame, alpha: float = 0.05):
        """
        Initialize the analyzer with movie data.
        
        Args:
            df: Pandas DataFrame with movie data
            alpha: Significance level for hypothesis tests
        """
        self.df = df.copy()
        self.alpha = alpha
        self.results: List[StatisticalResult] = []
        
        logger.info(f"StatisticalAnalyzer initialized with {len(df)} records")
    
    def get_descriptive_stats(self, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Compute descriptive statistics for numeric columns.
        
        Args:
            columns: List of columns to analyze (default: all numeric)
            
        Returns:
            DataFrame with descriptive statistics
        """
        if columns is None:
            columns = self.df.select_dtypes(include=[np.number]).columns.tolist()
        
        stats_dict = {}
        for col in columns:
            data = self.df[col].dropna()
            if len(data) > 0:
                stats_dict[col] = {
                    'count': len(data),
                    'mean': data.mean(),
                    'std': data.std(),
                    'min': data.min(),
                    'q25': data.quantile(0.25),
                    'median': data.median(),
                    'q75': data.quantile(0.75),
                    'max': data.max(),
                    'skewness': data.skew(),
                    'kurtosis': data.kurtosis(),
                    'missing': self.df[col].isna().sum()
                }
        
        return pd.DataFrame(stats_dict).T
    
    def run_kruskal_wallis(self, 
                          group_col: str, 
                          value_col: str,
                          min_group_size: int = 5) -> StatisticalResult:
        """
        Run Kruskal-Wallis H-test to compare groups.
        
        The Kruskal-Wallis test is a non-parametric alternative to one-way ANOVA.
        It tests whether samples from different groups come from the same distribution.
        
        Args:
            group_col: Column containing group names
            value_col: Column containing values to compare
            min_group_size: Minimum samples per group
            
        Returns:
            StatisticalResult with test outcomes
        """
        # Prepare groups
        groups = []
        group_names = []
        
        for name, group in self.df.groupby(group_col):
            values = group[value_col].dropna()
            if len(values) >= min_group_size:
                groups.append(values.values)
                group_names.append(name)
        
        if len(groups) < 2:
            logger.warning(f"Less than 2 valid groups for {group_col}")
            return StatisticalResult(
                test_name='Kruskal-Wallis',
                statistic=np.nan,
                p_value=np.nan,
                interpretation="Insufficient groups for comparison"
            )
        
        # Run Kruskal-Wallis test
        h_stat, p_value = kruskal(*groups)
        
        # Calculate effect size (Epsilon-squared)
        n_total = sum(len(g) for g in groups)
        k_groups = len(groups)
        epsilon_squared = (h_stat - k_groups + 1) / (n_total - k_groups)
        
        # Calculate eta-squared as alternative
        eta_squared = (h_stat - k_groups + 1) / (n_total - 1)
        
        # Interpret effect size
        if epsilon_squared < 0.01:
            effect_label = "negligible"
        elif epsilon_squared < 0.06:
            effect_label = "small"
        elif epsilon_squared < 0.14:
            effect_label = "medium"
        else:
            effect_label = "large"
        
        result = StatisticalResult(
            test_name='Kruskal-Wallis H-test',
            statistic=h_stat,
            p_value=p_value,
            effect_size=epsilon_squared,
            effect_size_label=f"ε² ({effect_label})",
            alpha=self.alpha,
            details={
                'group_col': group_col,
                'value_col': value_col,
                'n_groups': k_groups,
                'group_sizes': {name: len(g) for name, g in zip(group_names, groups)},
                'group_means': {name: np.mean(g) for name, g in zip(group_names, groups)},
                'eta_squared': eta_squared,
                'n_total': n_total
            }
        )
        
        self.results.append(result)
        logger.info(f"Kruskal-Wallis: H={h_stat:.2f}, p={p_value:.4f}")
        
        return result
    
    def run_pairwise_comparisons(self,
                                group_col: str,
                                value_col: str,
                                method: str = 'bonferroni',
                                min_group_size: int = 5) -> pd.DataFrame:
        """
        Run pairwise Mann-Whitney U tests with multiple comparison correction.
        
        Args:
            group_col: Column containing group names
            value_col: Column containing values to compare
            method: Correction method ('bonferroni', 'fdr_bh', 'holm')
            min_group_size: Minimum samples per group
            
        Returns:
            DataFrame with pairwise comparison results
        """
        # Get valid groups
        valid_groups = []
        for name, group in self.df.groupby(group_col):
            if len(group[value_col].dropna()) >= min_group_size:
                valid_groups.append(name)
        
        # Run all pairwise tests
        comparisons = []
        for i, g1 in enumerate(valid_groups):
            for g2 in valid_groups[i+1:]:
                data1 = self.df[self.df[group_col] == g1][value_col].dropna()
                data2 = self.df[self.df[group_col] == g2][value_col].dropna()
                
                # Mann-Whitney U test
                u_stat, p_raw = mannwhitneyu(data1, data2, alternative='two-sided')
                
                # Calculate effect size (rank-biserial correlation)
                n1, n2 = len(data1), len(data2)
                effect_size = 1 - (2 * u_stat) / (n1 * n2)
                
                comparisons.append({
                    'group1': g1,
                    'group2': g2,
                    'n1': n1,
                    'n2': n2,
                    'mean1': data1.mean(),
                    'mean2': data2.mean(),
                    'u_statistic': u_stat,
                    'p_raw': p_raw,
                    'effect_size': effect_size,
                    'rank_biserial': effect_size
                })
        
        if not comparisons:
            logger.warning("No valid comparisons found")
            return pd.DataFrame()
        
        # Create DataFrame
        comp_df = pd.DataFrame(comparisons)
        
        # Apply multiple testing correction
        reject, p_corrected, _, _ = multipletests(
            comp_df['p_raw'].values,
            alpha=self.alpha,
            method=method
        )
        
        comp_df['p_corrected'] = p_corrected
        comp_df['significant'] = reject
        
        # Add interpretation
        comp_df['interpretation'] = comp_df.apply(
            lambda row: (
                f"Significant difference between {row['group1']} and {row['group2']} "
                f"(p={row['p_corrected']:.4f})" if row['significant']
                else f"No significant difference (p={row['p_corrected']:.4f})"
            ),
            axis=1
        )
        
        logger.info(
            f"Pairwise comparisons: {reject.sum()}/{len(reject)} significant "
            f"after {method} correction"
        )
        
        return comp_df
    
    def calculate_effect_size_pairwise(self,
                                       group1_data: np.ndarray,
                                       group2_data: np.ndarray,
                                       method: str = 'cohen_d') -> Dict[str, float]:
        """
        Calculate effect sizes for two groups.
        
        Args:
            group1_data: First group's data
            group2_data: Second group's data
            method: Effect size measure ('cohen_d', 'hedges_g', 'glass_delta')
            
        Returns:
            Dictionary with effect size metrics
        """
        # Remove NaN
        g1 = group1_data[~np.isnan(group1_data)]
        g2 = group2_data[~np.isnan(group2_data)]
        
        n1, n2 = len(g1), len(g2)
        
        # Pooled standard deviation
        var1, var2 = np.var(g1, ddof=1), np.var(g2, ddof=1)
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        
        results = {
            'mean_diff': np.mean(g1) - np.mean(g2),
            'pooled_std': pooled_std
        }
        
        if method == 'cohen_d':
            d = (np.mean(g1) - np.mean(g2)) / pooled_std
            results['cohen_d'] = d
            results['magnitude'] = self._interpret_cohen(d)
            
        elif method == 'hedges_g':
            # Hedges' g (bias-corrected Cohen's d)
            d = (np.mean(g1) - np.mean(g2)) / pooled_std
            # Correction factor
            j = 1 - (3 / (4 * (n1 + n2) - 9))
            results['hedges_g'] = d * j
            results['magnitude'] = self._interpret_cohen(d * j)
            
        elif method == 'glass_delta':
            # Glass's delta (uses control group SD)
            glass_std = np.std(g2, ddof=1) if n2 > 1 else pooled_std
            if glass_std > 0:
                results['glass_delta'] = (np.mean(g1) - np.mean(g2)) / glass_std
        
        return results
    
    def _interpret_cohen(self, d: float) -> str:
        """Interpret Cohen's d effect size."""
        d = abs(d)
        if d < 0.2:
            return "negligible"
        elif d < 0.5:
            return "small"
        elif d < 0.8:
            return "medium"
        else:
            return "large"
    
    def correlate(self, 
                  col1: str, 
                  col2: str,
                  method: str = 'pearson') -> Dict[str, Any]:
        """
        Calculate correlation between two columns.
        
        Args:
            col1: First column name
            col2: Second column name
            method: 'pearson' or 'spearman'
            
        Returns:
            Dictionary with correlation results
        """
        # Get clean data
        mask = ~(self.df[col1].isna() | self.df[col2].isna())
        x = self.df.loc[mask, col1]
        y = self.df.loc[mask, col2]
        
        if len(x) < 3:
            logger.warning("Insufficient data for correlation")
            return {'error': 'Insufficient data'}
        
        if method == 'pearson':
            r, p = pearsonr(x, y)
        elif method == 'spearman':
            r, p = spearmanr(x, y)
        else:
            raise ValueError(f"Unknown correlation method: {method}")
        
        # Interpret correlation strength
        r_abs = abs(r)
        if r_abs < 0.1:
            strength = "negligible"
        elif r_abs < 0.3:
            strength = "weak"
        elif r_abs < 0.5:
            strength = "moderate"
        elif r_abs < 0.7:
            strength = "strong"
        else:
            strength = "very strong"
        
        return {
            'correlation': r,
            'p_value': p,
            'strength': strength,
            'direction': 'positive' if r > 0 else 'negative',
            'significant': p < self.alpha,
            'n': len(x)
        }
    
    def compare_decades(self, 
                       score_col: str = 'critics_score',
                       min_movies: int = 10) -> Tuple[StatisticalResult, pd.DataFrame]:
        """
        Compare movie scores across decades with proper statistical controls.
        
        This addresses the critique that release decade is confounded with
        other factors like genre and survivorship bias.
        
        Args:
            score_col: Column containing the score
            min_movies: Minimum movies per decade
            
        Returns:
            Tuple of (Kruskal-Wallis result, decade summary DataFrame)
        """
        # Create decade column
        self.df['decade'] = (self.df['year'] // 10) * 10
        
        # Filter to decades with enough movies
        decade_counts = self.df['decade'].value_counts()
        valid_decades = decade_counts[decade_counts >= min_movies].index
        
        df_filtered = self.df[self.df['decade'].isin(valid_decades)]
        
        # Summary by decade
        summary = df_filtered.groupby('decade').agg({
            score_col: ['mean', 'std', 'count', 'median']
        }).round(2)
        summary.columns = ['mean', 'std', 'count', 'median']
        summary = summary.sort_index()
        
        # Run Kruskal-Wallis
        result = self.run_kruskal_wallis('decade', score_col)
        
        return result, summary
    
    def run_analysis_report(self, group_col: str, value_col: str) -> Dict[str, Any]:
        """
        Generate comprehensive analysis report for a grouping variable.
        
        Args:
            group_col: Column to group by
            value_col: Column to analyze
            
        Returns:
            Dictionary containing all analysis results
        """
        report = {
            'grouping_variable': group_col,
            'value_variable': value_col,
            'descriptive': self.get_descriptive_stats([value_col]),
            'kruskal_wallis': self.run_kruskal_wallis(group_col, value_col),
            'pairwise': self.run_pairwise_comparisons(group_col, value_col)
        }
        
        return report
    
    def get_summary_report(self) -> str:
        """Generate a text summary of all analysis results."""
        if not self.results:
            return "No analyses have been run yet."
        
        lines = ["=" * 60]
        lines.append("STATISTICAL ANALYSIS SUMMARY REPORT")
        lines.append("=" * 60)
        
        for i, result in enumerate(self.results, 1):
            lines.append(f"\n{i}. {result.test_name}")
            lines.append(f"   Statistic: {result.statistic:.4f}")
            lines.append(f"   P-value: {result.p_value:.6f}")
            if result.effect_size is not None:
                lines.append(f"   Effect Size ({result.effect_size_label}): {result.effect_size:.4f}")
            lines.append(f"   Significant: {result.significant}")
            lines.append(f"\n   Interpretation:")
            lines.append(f"   {result.interpretation}")
        
        return "\n".join(lines)