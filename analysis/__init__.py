"""
Rotten Tomatoes Analysis Package
"""
from .statistical_analysis import StatisticalAnalyzer
from .regression import RegressionAnalyzer
from .visualization import MovieVisualizer

__all__ = ['StatisticalAnalyzer', 'RegressionAnalyzer', 'MovieVisualizer']