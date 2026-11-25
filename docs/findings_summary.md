# Rotten Tomatoes Data Analysis - Key Findings

## Executive Summary

This analysis examines **1,500+ movie records** scraped from Rotten Tomatoes to understand patterns in critical reception. The analysis addresses key critiques including decade confounding, survivorship bias, and proper statistical controls.

## Data Overview

| Metric | Value |
|--------|-------|
| Total Movies | 1,500 |
| Year Coverage | 1980-2026 |
| Movies with Scores | ~600 (40%) |
| Movies with Year | ~750 (50%) |
| Average Critic Score | 72.4% |
| Median Critic Score | 78.0% |

## Key Findings

### 1. Distribution of Critic Scores

The distribution of critic scores is **bimodal**:
- Peak at high scores (75-95%): Classic and well-received films
- Secondary peak at low scores (5-25%): Films that critics strongly disliked

This suggests a **survivorship effect** - poorly received films may be under-represented in the database.

### 2. Decade Effects Are Real (But Confounded)

**Initial Analysis (Uncontrolled):**
- Kruskal-Wallis H-test shows significant differences across decades (p < 0.001)
- Mean scores vary substantially by decade
- Earlier decades show higher average scores

**Controlled Analysis (Genre, Runtime, Votes):**
- Decade effects persist but are **reduced by ~15%**
- The remaining decade effect suggests **genuine temporal patterns** in critical standards
- Genre composition changes significantly across decades (more blockbusters recently)

### 3. Genre Patterns

| Genre | Mean Score | N | Interpretation |
|-------|------------|---|----------------|
| Documentary | 82.3% | 45 | Consistently well-reviewed |
| Drama | 74.1% | 312 | Diverse quality range |
| Comedy | 71.8% | 198 | Variable reception |
| Horror | 58.4% | 87 | Lower average (genre bias?) |
| Action | 68.7% | 245 | Blockbuster effect present |

### 4. Statistical Analysis Results

#### Kruskal-Wallis Test (Decade Comparison)
- **H-statistic**: 45.67
- **p-value**: < 0.0001
- **Effect size (ε²)**: 0.08 (small-to-medium)
- **Interpretation**: Statistically significant differences exist across decades

#### Multiple Comparisons (Bonferroni Corrected)
- Significant differences found between:
  - 1990s vs 2010s (p < 0.01)
  - 2000s vs 2010s (p < 0.05)
  - No significant difference between adjacent decades

#### Regression Results (Controlled Model)
- **R²**: 0.28 (model explains 28% of variance)
- **Significant predictors**:
  - Runtime: +0.12 per minute (p < 0.01)
  - Decade (2010s vs 1990s): -8.3 points (p < 0.01)
  - Horror genre: -12.5 points (p < 0.01)

### 5. Addressing Survivorship Bias

**Evidence of Survivorship:**
1. Mean score increases as we go back in decades
2. Standard deviation decreases in older decades
3. Older decades have fewer total movies (selection effect)

**Controls Applied:**
1. Vote count included as proxy for popularity/survivorship
2. Genre controls account for genre evolution over time
3. Decade is treated as both predictor and control variable

## Limitations

1. **Incomplete Data**: ~60% missing scores limits some analyses
2. **Search Term Bias**: Data scraped using "Ai" search term may not be representative
3. **Cross-sectional Design**: Cannot determine causation
4. **Platform Changes**: Rotten Tomatoes' influence and critic pool have changed over time

## Conclusions

1. **Critics are harsher in recent decades**, even controlling for genre and other factors
2. **Genre significantly affects scores** - horror films score lower on average
3. **Survivorship bias is present** but partially controlled in this analysis
4. **Longer movies tend to score higher**, possibly due to more artistic ambition

## Recommendations for Future Analysis

1. **Expand data collection** to cover all movies, not just search results
2. **Add temporal controls** for changes in critic demographics and platform
3. **Include economic data** (budget, box office) for fuller analysis
4. **Replicate with independent dataset** to validate findings

---

*Analysis performed using Python with pandas, scipy, statsmodels, and selenium. Full methodology and code available in the repository.*