"""
Regression Analysis Module

This module provides regression analysis to control for confounding variables
like genre, runtime, and vote count when analyzing movie scores.

Key Features:
- OLS regression with robust standard errors
- Control for genre, runtime, year, and vote count
- Model diagnostics and interpretation
- Effect size reporting
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.diagnostic import het_breuschpagan, linear_reset
from statsmodels.nonparametric.smoothers_lowess import lowess

logger = logging.getLogger(__name__)


@dataclass
class RegressionResult:
    """Container for regression analysis results."""
    model_name: str
    r_squared: float
    adjusted_r_squared: float
    f_statistic: float
    f_pvalue: float
    coefficients: pd.DataFrame
    vif_scores: pd.DataFrame
    model_summary: str
    significant_vars: List[str]
    interpretation: str
    diagnostics: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'model_name': self.model_name,
            'r_squared': self.r_squared,
            'adjusted_r_squared': self.adjusted_r_squared,
            'f_statistic': self.f_statistic,
            'f_pvalue': self.f_pvalue,
            'coefficients': self.coefficients.to_dict(),
            'vif_scores': self.vif_scores.to_dict(),
            'significant_vars': self.significant_vars,
            'interpretation': self.interpretation,
            'diagnostics': self.diagnostics
        }


class RegressionAnalyzer:
    """
    Regression analysis for movie rating data with confounding control.
    
    Provides methods for:
    - OLS regression with robust standard errors
    - Control for genre, runtime, year, vote count
    - Model diagnostics (VIF, heteroscedasticity, normality)
    - Interpretation of regression results
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
        self.results: Optional[RegressionResult] = None
        
        logger.info(f"RegressionAnalyzer initialized with {len(df)} records")
    
    def prepare_data(self,
                    target_col: str = 'critics_score',
                    control_cols: Optional[List[str]] = None,
                    genre_col: str = 'genres',
                    year_col: str = 'year',
                    runtime_col: str = 'runtime',
                    vote_col: str = 'num_reviews') -> pd.DataFrame:
        """
        Prepare data for regression analysis.
        
        This method:
        1. Drops rows with missing target values
        2. One-hot encodes genres
        3. Handles missing control variables
        
        Args:
            target_col: Name of the dependent variable
            control_cols: Additional control variables
            genre_col: Column containing genres
            year_col: Column containing release year
            runtime_col: Column containing runtime
            vote_col: Column containing vote/review counts
            
        Returns:
            Prepared DataFrame ready for regression
        """
        df = self.df.copy()
        
        # Drop rows with missing target
        df = df.dropna(subset=[target_col])
        logger.info(f"After dropping missing target: {len(df)} records")
        
        # Ensure numeric types for year and runtime
        if year_col in df.columns:
            df[year_col] = pd.to_numeric(df[year_col], errors='coerce')
        if runtime_col in df.columns:
            df[runtime_col] = pd.to_numeric(df[runtime_col], errors='coerce')
        if vote_col in df.columns:
            df[vote_col] = pd.to_numeric(df[vote_col], errors='coerce')
        
        # Create decade variable (from decade critique)
        if year_col in df.columns:
            df['decade'] = (df[year_col] // 10) * 10
            df['decade'] = df['decade'].fillna(df['decade'].median())
        
        # Create genre dummies (top genres)
        if genre_col in df.columns:
            # Get top 10 genres
            all_genres = []
            for genres in df[genre_col].dropna():
                if isinstance(genres, str):
                    all_genres.extend([g.strip() for g in genres.split(',')])
            
            top_genres = pd.Series(all_genres).value_counts().head(10).index.tolist()
            
            # Create dummy columns for top genres
            for genre in top_genres:
                col_name = f"genre_{genre.lower().replace(' ', '_')}"
                df[col_name] = df[genre_col].apply(
                    lambda x: 1 if isinstance(x, str) and genre in x else 0
                )
        
        # Fill remaining numeric controls with median
        numeric_cols = [year_col, runtime_col, vote_col, 'decade']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(df[col].median())
        
        logger.info(f"Prepared data: {len(df)} records, {len(df.columns)} columns")
        return df
    
    def run_ols_regression(self,
                          target_col: str = 'critics_score',
                          predictors: Optional[List[str]] = None,
                          robust_se: bool = True) -> RegressionResult:
        """
        Run OLS regression with specified predictors.
        
        Args:
            target_col: Name of the dependent variable
            predictors: List of predictor column names
            robust_se: Use heteroscedasticity-robust standard errors
            
        Returns:
            RegressionResult with full analysis
        """
        # Prepare data
        df = self.prepare_data(target_col)
        
        # Default predictors
        if predictors is None:
            predictors = [
                'decade', 'runtime',
                'genre_action', 'genre_comedy', 'genre_drama',
                'genre_horror', 'genre_thriller', 'genre_romance'
            ]
        
        # Filter to available columns
        available_predictors = [p for p in predictors if p in df.columns]
        
        # Add constant
        X = df[available_predictors].copy()
        X = sm.add_constant(X)
        y = df[target_col]
        
        # Fit model
        if robust_se:
            model = sm.OLS(y, X).fit(cov_type='HC3')  # Robust SE
        else:
            model = model = sm.OLS(y, X).fit()
        
        # Calculate VIF for multicollinearity
        vif_data = self._calculate_vif(X.drop('const', axis=1))
        
        # Run diagnostics
        diagnostics = self._run_diagnostics(model, X, y)
        
        # Identify significant variables
        sig_vars = [
            name for name, pval in model.pvalues.items()
            if pval < self.alpha and name != 'const'
        ]
        
        # Create coefficient summary
        coef_df = pd.DataFrame({
            'coef': model.params,
            'se': model.bse,
            't_stat': model.tvalues,
            'p_value': model.pvalues,
            'ci_low': model.conf_int()[0],
            'ci_high': model.conf_int()[1]
        }).round(4)
        
        # Interpretation
        interpretation = self._interpret_results(model, sig_vars)
        
        result = RegressionResult(
            model_name="OLS Regression with Robust Standard Errors",
            r_squared=model.rsquared,
            adjusted_r_squared=model.rsquared_adj,
            f_statistic=model.fvalue,
            f_pvalue=model.f_pvalue,
            coefficients=coef_df,
            vif_scores=vif_data,
            model_summary=model.summary().as_text(),
            significant_vars=sig_vars,
            interpretation=interpretation,
            diagnostics=diagnostics
        )
        
        self.results = result
        logger.info(f"OLS Regression: R²={model.rsquared:.4f}, F={model.fvalue:.2f}")
        
        return result
    
    def _calculate_vif(self, X: pd.DataFrame) -> pd.DataFrame:
        """Calculate Variance Inflation Factors for predictors."""
        vif_dict = {}
        for i, col in enumerate(X.columns):
            try:
                vif_dict[col] = variance_inflation_factor(X.values, i)
            except:
                vif_dict[col] = np.nan
        
        vif_df = pd.DataFrame({
            'Variable': list(vif_dict.keys()),
            'VIF': list(vif_dict.values())
        }).round(2)
        
        vif_df['Multicollinearity'] = vif_df['VIF'].apply(
            lambda x: 'High' if x > 10 else ('Moderate' if x > 5 else 'Low')
        )
        
        return vif_df
    
    def _run_diagnostics(self, model, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """Run regression diagnostics."""
        diagnostics = {}
        residuals = model.resid
        fitted = model.fittedvalues
        
        # Breusch-Pagan test for heteroscedasticity
        bp_stat, bp_p, _, _ = het_breuschpagan(residuals, X)
        diagnostics['heteroscedasticity'] = {
            'test': 'Breusch-Pagan',
            'statistic': float(bp_stat),
            'p_value': float(bp_p),
            'significant': bp_p < self.alpha,
            'interpretation': (
                'Heteroscedasticity detected (p < 0.05)' if bp_p < 0.05
                else 'No significant heteroscedasticity'
            )
        }
        
        # Normality of residuals (Shapiro-Wilk on subsample if large)
        if len(residuals) <= 5000:
            _, sw_p = stats.shapiro(residuals[:min(5000, len(residuals))])
            diagnostics['normality'] = {
                'test': 'Shapiro-Wilk',
                'p_value': float(sw_p),
                'significant': sw_p < self.alpha,
                'interpretation': (
                    'Non-normal residuals (p < 0.05)' if sw_p < 0.05
                    else 'Residuals appear normal'
                )
            }
        
        # Model specification (RESET test)
        try:
            reset_stat, reset_p, _, _ = linear_reset(model)
            diagnostics['specification'] = {
                'test': 'RAMSEY RESET',
                'statistic': float(reset_stat),
                'p_value': float(reset_p),
                'significant': reset_p < self.alpha,
                'interpretation': (
                    'Possible specification error (p < 0.05)' if reset_p < 0.05
                    else 'No specification error detected'
                )
            }
        except:
            diagnostics['specification'] = {'error': 'Could not run RESET test'}
        
        # Multicollinearity summary
        vif_max = diagnostics.get('vif_scores', pd.DataFrame()).get('VIF', [0]).max()
        diagnostics['multicollinearity'] = {
            'max_vif': float(vif_max) if not pd.isna(vif_max) else 0,
            'severity': 'High' if vif_max > 10 else ('Moderate' if vif_max > 5 else 'Low')
        }
        
        return diagnostics
    
    def _interpret_results(self, model, sig_vars: List[str]) -> str:
        """Generate interpretation of regression results."""
        lines = []
        lines.append("REGRESSION ANALYSIS INTERPRETATION")
        lines.append("=" * 50)
        
        # Model fit
        lines.append(f"\nModel Fit:")
        lines.append(f"  R² = {model.rsquared:.4f} (explains {model.rsquared*100:.1f}% of variance)")
        lines.append(f"  Adjusted R² = {model.rsquared_adj:.4f}")
        lines.append(f"  F-statistic = {model.fvalue:.2f}, p = {model.f_pvalue:.6f}")
        
        # Significant predictors
        lines.append(f"\nSignificant Predictors (α = {self.alpha}):")
        if sig_vars:
            for var in sig_vars:
                coef = model.params[var]
                pval = model.pvalues[var]
                direction = "increases" if coef > 0 else "decreases"
                lines.append(f"  - {var}: {direction} scores by {abs(coef):.2f} (p={pval:.4f})")
        else:
            lines.append("  No significant predictors found")
        
        # Control variables interpretation
        lines.append("\nControl Variables:")
        for var in model.params.index:
            if var != 'const':
                coef = model.params[var]
                pval = model.pvalues[var]
                sig = "significant" if pval < self.alpha else "not significant"
                lines.append(f"  - {var}: coef={coef:.2f} ({sig})")
        
        return "\n".join(lines)
    
    def compare_controlled_vs_uncontrolled(self,
                                           target_col: str = 'critics_score',
                                           grouping_col: str = 'decade') -> Dict[str, Any]:
        """
        Compare controlled vs uncontrolled analysis of group effects.
        
        This directly addresses the critique that decade effects might be
        confounded with genre, runtime, and vote count.
        
        Args:
            target_col: Score column to analyze
            grouping_col: Grouping variable (e.g., decade)
            
        Returns:
            Dictionary with both model comparisons
        """
        # Uncontrolled model: just the grouping variable
        df = self.prepare_data(target_col)
        
        # Uncontrolled
        X_unc = pd.get_dummies(df[grouping_col], prefix=grouping_col, drop_first=True)
        X_unc = sm.add_constant(X_unc)
        y = df[target_col]
        
        model_unc = sm.OLS(y, X_unc).fit(cov_type='HC3')
        
        # Controlled model
        model_ctrl = self.run_ols_regression(target_col)
        
        # Compare
        comparison = {
            'uncontrolled_model': {
                'r_squared': model_unc.rsquared,
                'f_statistic': model_unc.fvalue,
                'f_pvalue': model_unc.f_pvalue,
                'summary': model_unc.summary().as_text()
            },
            'controlled_model': {
                'r_squared': model_ctrl.r_squared,
                'f_statistic': model_ctrl.f_statistic,
                'f_pvalue': model_ctrl.f_pvalue,
                'summary': model_ctrl.model_summary
            },
            'interpretation': (
                f"Controlling for genre, runtime, and vote count, the effect of "
                f"{grouping_col} changes from R²={model_unc.rsquared:.4f} (uncontrolled) "
                f"to R²={model_ctrl.r_squared:.4f} (controlled). "
                f"The change of {(model_ctrl.r_squared - model_unc.rsquared)*100:.2f}% suggests "
                f"{'substantial' if abs(model_ctrl.r_squared - model_unc.rsquared) > 0.1 else 'modest'} "
                f"confounding by these variables."
            )
        }
        
        return comparison
    
    def get_effect_contribution(self) -> pd.DataFrame:
        """Calculate each variable's contribution to R² (dominance analysis)."""
        if self.results is None:
            logger.warning("No regression results available. Run regression first.")
            return pd.DataFrame()
        
        # Use results from prepare_data
        df = self.prepare_data()
        predictors = self.results.coefficients.index.tolist()
        predictors = [p for p in predictors if p != 'const']
        
        contributions = {}
        total_r2 = self.results.r_squared
        
        for pred in predictors:
            X = df[[pred]].copy()
            X = sm.add_constant(X)
            y = df['critics_score']
            
            try:
                model = sm.OLS(y, X).fit()
                contributions[pred] = {
                    'r_squared': model.rsquared,
                    'proportion': model.rsquared / total_r2 if total_r2 > 0 else 0
                }
            except:
                contributions[pred] = {'r_squared': 0, 'proportion': 0}
        
        contrib_df = pd.DataFrame(contributions).T
        contrib_df = contrib_df.sort_values('r_squared', ascending=False)
        
        return contrib_df


def main():
    """Example usage of regression analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run regression analysis")
    parser.add_argument("db_path", help="Path to SQLite database")
    parser.add_argument("--target", default="critics_score", help="Target variable")
    parser.add_argument("--output", help="Output file for results")
    
    args = parser.parse_args()
    
    # Load data
    from database.schema import DatabaseManager
    db = DatabaseManager(args.db_path)
    df = db.export_to_dataframe()
    
    # Run analysis
    analyzer = RegressionAnalyzer(df)
    result = analyzer.run_ols_regression(args.target)
    
    # Output
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
    else:
        print(result.model_summary)
        print("\n" + result.interpretation)


if __name__ == "__main__":
    main()