"""
Visualization Module

This module provides comprehensive visualization functions for movie data
analysis, including distribution plots, statistical comparisons, and regression diagnostics.
"""

import logging
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


class MovieVisualizer:
    """
    Visualization class for Rotten Tomatoes movie data.
    
    Provides methods for:
    - Distribution plots (histograms, boxplots)
    - Statistical comparison plots
    - Time series and trend analysis
    - Regression diagnostics
    - Interactive Plotly charts
    """
    
    def __init__(self, df: pd.DataFrame, style: str = "seaborn-v0_8"):
        """
        Initialize the visualizer.
        
        Args:
            df: Pandas DataFrame with movie data
            style: matplotlib/seaborn style to use
        """
        self.df = df.copy()
        plt.style.use(style)
        logger.info(f"MovieVisualizer initialized with {len(df)} records")
    
    def set_palette(self, n_colors: int = 8) -> None:
        """Set color palette for plots."""
        self.palette = sns.color_palette("husl", n_colors)
    
    # ========== Distribution Plots ==========
    
    def plot_score_distribution(self,
                               score_col: str = 'critics_score',
                               save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot distribution of movie scores with statistics.
        
        Args:
            score_col: Column containing scores
            save_path: Optional path to save figure
            
        Returns:
            Matplotlib figure
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Histogram
        ax1 = axes[0]
        self.df[score_col].dropna().hist(bins=30, ax=ax1, edgecolor='black', alpha=0.7)
        ax1.axvline(self.df[score_col].mean(), color='red', linestyle='--', 
                   label=f'Mean: {self.df[score_col].mean():.1f}')
        ax1.axvline(self.df[score_col].median(), color='green', linestyle='--',
                   label=f'Median: {self.df[score_col].median():.1f}')
        ax1.set_xlabel(f'{score_col}')
        ax1.set_ylabel('Frequency')
        ax1.set_title(f'Distribution of {score_col}')
        ax1.legend()
        
        # Boxplot
        ax2 = axes[1]
        bp = ax2.boxplot(self.df[score_col].dropna(), vert=True, patch_artist=True)
        bp['boxes'][0].set_facecolor(self.palette[0] if hasattr(self, 'palette') else 'lightblue')
        ax2.set_ylabel(f'{score_col}')
        ax2.set_title(f'Boxplot of {score_col}')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved distribution plot to {save_path}")
        
        return fig
    
    def plot_genre_distribution(self,
                               genre_col: str = 'genres',
                               top_n: int = 10,
                               save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot distribution of movie genres.
        
        Args:
            genre_col: Column containing genres
            top_n: Number of top genres to show
            save_path: Optional path to save figure
            
        Returns:
            Matplotlib figure
        """
        # Count genres
        genre_counts = {}
        for genres in self.df[genre_col].dropna():
            if isinstance(genres, str):
                for genre in genres.split(','):
                    genre = genre.strip().lower()
                    if genre:
                        genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        # Get top genres
        top_genres = dict(sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:top_n])
        
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.barh(list(top_genres.keys()), list(top_genres.values()), 
                      color=self.palette[:len(top_genres)] if hasattr(self, 'palette') else 'steelblue')
        
        ax.set_xlabel('Number of Movies')
        ax.set_ylabel('Genre')
        ax.set_title(f'Top {top_n} Movie Genres')
        ax.invert_yaxis()  # Highest at top
        
        # Add value labels
        for bar, val in zip(bars, top_genres.values()):
            ax.text(val + 5, bar.get_y() + bar.get_height()/2, 
                   str(val), va='center', fontsize=10)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved genre distribution to {save_path}")
        
        return fig
    
    # ========== Group Comparison Plots ==========
    
    def plot_score_by_group(self,
                           group_col: str,
                           score_col: str = 'critics_score',
                           save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot score distribution by groups (e.g., decade, genre).
        
        Args:
            group_col: Column to group by
            score_col: Column containing scores
            save_path: Optional path to save figure
            
        Returns:
            Matplotlib figure
        """
        # Filter to groups with enough data
        group_counts = self.df[group_col].value_counts()
        valid_groups = group_counts[group_counts >= 5].index
        df_filtered = self.df[self.df[group_col].isin(valid_groups)]
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Boxplot
        ax1 = axes[0]
        order = df_filtered.groupby(group_col)[score_col].median().sort_values().index
        sns.boxplot(data=df_filtered, x=group_col, y=score_col, ax=ax1, order=order,
                   palette=self.palette if hasattr(self, 'palette') else 'husl')
        ax1.set_xlabel(group_col)
        ax1.set_ylabel(score_col)
        ax1.set_title(f'{score_col} by {group_col}')
        ax1.tick_params(axis='x', rotation=45)
        
        # Violin plot
        ax2 = axes[1]
        sns.violinplot(data=df_filtered, x=group_col, y=score_col, ax=ax2, order=order,
                      palette=self.palette if hasattr(self, 'palette') else 'husl')
        ax2.set_xlabel(group_col)
        ax2.set_ylabel(score_col)
        ax2.set_title(f'{score_col} Distribution by {group_col} (Violin)')
        ax2.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved group comparison plot to {save_path}")
        
        return fig
    
    def plot_decade_comparison(self,
                               score_col: str = 'critics_score',
                               save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot score comparison across decades with statistics.
        
        This addresses the survivorship bias critique.
        
        Args:
            score_col: Column containing scores
            save_path: Optional path to save figure
            
        Returns:
            Matplotlib figure
        """
        # Create decade
        df = self.df.copy()
        df['decade'] = (df['year'] // 10) * 10
        df = df.dropna(subset=['decade', score_col])
        
        # Calculate stats by decade
        decade_stats = df.groupby('decade')[score_col].agg(['mean', 'std', 'count']).reset_index()
        decade_stats['se'] = decade_stats['std'] / np.sqrt(decade_stats['count'])
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Bar chart with error bars
        ax1 = axes[0]
        colors = plt.cm.viridis(np.linspace(0, 1, len(decade_stats)))
        bars = ax1.bar(decade_stats['decade'].astype(str), 
                      decade_stats['mean'],
                      yerr=1.96*decade_stats['se'],  # 95% CI
                      capsize=5,
                      color=colors,
                      edgecolor='black')
        
        ax1.set_xlabel('Decade')
        ax1.set_ylabel(f'Mean {score_col}')
        ax1.set_title(f'Mean {score_col} by Decade (with 95% CI)')
        
        # Add movie counts
        for bar, count in zip(bars, decade_stats['count']):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                    f'n={count}', ha='center', va='bottom', fontsize=9)
        
        # Count by decade (shows survivorship)
        ax2 = axes[1]
        ax2.bar(decade_stats['decade'].astype(str), decade_stats['count'],
               color='lightcoral', edgecolor='black')
        ax2.set_xlabel('Decade')
        ax2.set_ylabel('Number of Movies')
        ax2.set_title('Movie Count by Decade (Survivorship Indicator)')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved decade comparison plot to {save_path}")
        
        return fig
    
    # ========== Correlation Plots ==========
    
    def plot_correlation_matrix(self,
                               numeric_cols: Optional[List[str]] = None,
                               save_path: Optional[str] = None) -> plt.Figure:
        """
        Plot correlation matrix for numeric variables.
        
        Args:
            numeric_cols: List of columns to include
            save_path: Optional path to save figure
            
        Returns:
            Matplotlib figure
        """
        if numeric_cols is None:
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        
        corr_matrix = self.df[numeric_cols].corr()
        
        fig, ax = plt.subplots(figsize=(10, 8))
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
        
        sns.heatmap(corr_matrix, mask=mask, annot=True, fmt='.2f',
                   cmap='RdBu_r', center=0, ax=ax,
                   square=True, linewidths=0.5)
        
        ax.set_title('Correlation Matrix')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved correlation matrix to {save_path}")
        
        return fig
    
    # ========== Interactive Plots ==========
    
    def create_interactive_scatter(self,
                                  x_col: str,
                                  y_col: str,
                                  color_col: Optional[str] = None,
                                  title: Optional[str] = None) -> go.Figure:
        """
        Create an interactive scatter plot using Plotly.
        
        Args:
            x_col: X-axis column
            y_col: Y-axis column
            color_col: Optional color grouping column
            title: Plot title
            
        Returns:
            Plotly figure object
        """
        fig = px.scatter(
            self.df, x=x_col, y=y_col, color=color_col,
            title=title or f'{y_col} vs {x_col}',
            hover_data=['title', 'year'],
            trendline='ols' if color_col is None else None
        )
        
        return fig
    
    def create_interactive_decade_chart(self,
                                       score_col: str = 'critics_score') -> go.Figure:
        """
        Create interactive decade comparison chart.
        
        Args:
            score_col: Score column to analyze
            
        Returns:
            Plotly figure object
        """
        df = self.df.copy()
        df['decade'] = (df['year'] // 10) * 10
        df = df.dropna(subset=['decade', score_col])
        
        fig = go.Figure()
        
        # Box plots for each decade
        for i, decade in enumerate(sorted(df['decade'].unique())):
            decade_data = df[df['decade'] == decade][score_col]
            
            fig.add_trace(go.Box(
                y=decade_data,
                name=str(int(decade)),
                boxpoints='outliers',
                marker_color=px.colors.qualitative.Plotly[i % 10]
            ))
        
        fig.update_layout(
            title=f'{score_col} Distribution by Decade',
            xaxis_title='Decade',
            yaxis_title=score_col
        )
        
        return fig
    
    # ========== Regression Diagnostics ==========
    
    def plot_regression_diagnostics(self,
                                    model,
                                    save_path: Optional[str] = None) -> plt.Figure:
        """
        Create regression diagnostic plots.
        
        Args:
            model: Fitted statsmodels OLS model
            save_path: Optional path to save figure
            
        Returns:
            Matplotlib figure
        """
        residuals = model.resid
        fitted = model.fittedvalues
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Residuals vs Fitted
        ax1 = axes[0, 0]
        ax1.scatter(fitted, residuals, alpha=0.5)
        ax1.axhline(0, color='red', linestyle='--')
        ax1.set_xlabel('Fitted Values')
        ax1.set_ylabel('Residuals')
        ax1.set_title('Residuals vs Fitted')
        
        # Histogram of residuals
        ax2 = axes[0, 1]
        ax2.hist(residuals, bins=30, edgecolor='black', alpha=0.7)
        ax2.set_xlabel('Residuals')
        ax2.set_ylabel('Frequency')
        ax2.set_title('Distribution of Residuals')
        
        # Q-Q plot
        ax3 = axes[1, 0]
        stats.probplot(residuals, dist="norm", plot=ax3)
        ax3.set_title('Normal Q-Q Plot')
        
        # Scale-Location plot
        ax4 = axes[1, 1]
        standardized_residuals = residuals / residuals.std()
        ax4.scatter(fitted, np.sqrt(np.abs(standardized_residuals)), alpha=0.5)
        ax4.set_xlabel('Fitted Values')
        ax4.set_ylabel('√|Standardized Residuals|')
        ax4.set_title('Scale-Location Plot')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved regression diagnostics to {save_path}")
        
        return fig
    
    # ========== Summary Charts ==========
    
    def create_summary_dashboard(self,
                                output_dir: str,
                                score_col: str = 'critics_score') -> Dict[str, str]:
        """
        Create a complete summary dashboard with key visualizations.
        
        Args:
            output_dir: Directory to save charts
            score_col: Score column to analyze
            
        Returns:
            Dictionary mapping chart names to file paths
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        charts = {}
        
        # Score distribution
        charts['score_distribution'] = os.path.join(output_dir, 'score_distribution.png')
        self.plot_score_distribution(score_col, charts['score_distribution'])
        
        # Genre distribution
        charts['genre_distribution'] = os.path.join(output_dir, 'genre_distribution.png')
        self.plot_genre_distribution(save_path=charts['genre_distribution'])
        
        # Decade comparison
        charts['decade_comparison'] = os.path.join(output_dir, 'decade_comparison.png')
        self.plot_decade_comparison(score_col, charts['decade_comparison'])
        
        # Correlation matrix
        charts['correlation_matrix'] = os.path.join(output_dir, 'correlation_matrix.png')
        self.plot_correlation_matrix(save_path=charts['correlation_matrix'])
        
        plt.close('all')  # Close figures to free memory
        
        logger.info(f"Created {len(charts)} summary charts in {output_dir}")
        
        return charts
    
    def save_all_figures(self, output_dir: str) -> None:
        """Save all default visualizations to a directory."""
        os.makedirs(output_dir, exist_ok=True)
        
        self.plot_score_distribution(save_path=os.path.join(output_dir, 'score_distribution.png'))
        self.plot_genre_distribution(save_path=os.path.join(output_dir, 'genre_distribution.png'))
        
        plt.close('all')


if __name__ == "__main__":
    from database.schema import DatabaseManager
    
    # Example usage
    db = DatabaseManager("database/rotten_tomatoes.db")
    df = db.export_to_dataframe()
    
    viz = MovieVisualizer(df)
    
    # Create dashboard
    charts = viz.create_summary_dashboard("docs/charts")
    print(f"Created charts: {list(charts.keys())}")