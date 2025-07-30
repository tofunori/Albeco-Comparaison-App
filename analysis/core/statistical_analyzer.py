import numpy as np
import pandas as pd
import logging
from typing import Dict, Any, List, Tuple, Optional
from scipy import stats
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import warnings

logger = logging.getLogger(__name__)


class StatisticalAnalyzer:
    """Statistical analysis and comparison of albedo datasets."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.confidence_level = config.get('analysis', {}).get('statistics', {}).get('confidence_level', 0.95)
        
    def calculate_basic_metrics(self, observed: pd.Series, predicted: pd.Series) -> Dict[str, float]:
        """Calculate basic statistical metrics between observed and predicted values."""
        # Remove NaN values
        mask = ~(observed.isna() | predicted.isna())
        obs_clean = observed[mask]
        pred_clean = predicted[mask]
        
        if len(obs_clean) == 0:
            logger.warning("No valid data pairs for statistical calculation")
            return self._empty_metrics()
        
        metrics = {
            'n_samples': len(obs_clean),
            'rmse': np.sqrt(mean_squared_error(obs_clean, pred_clean)),
            'mae': mean_absolute_error(obs_clean, pred_clean),
            'bias': np.mean(pred_clean - obs_clean),
            'relative_bias': np.mean((pred_clean - obs_clean) / obs_clean) * 100,
            'r2': r2_score(obs_clean, pred_clean),
            'correlation': np.corrcoef(obs_clean, pred_clean)[0, 1],
            'std_obs': np.std(obs_clean),
            'std_pred': np.std(pred_clean),
            'mean_obs': np.mean(obs_clean),
            'mean_pred': np.mean(pred_clean)
        }
        
        # Additional metrics
        metrics.update(self._calculate_additional_metrics(obs_clean, pred_clean))
        
        return metrics
    
    def _calculate_additional_metrics(self, observed: np.ndarray, predicted: np.ndarray) -> Dict[str, float]:
        """Calculate additional statistical metrics."""
        # Nash-Sutcliffe Efficiency
        nse = 1 - (np.sum((observed - predicted) ** 2) / 
                  np.sum((observed - np.mean(observed)) ** 2))
        
        # Index of Agreement (Willmott, 1981)
        ioa = 1 - (np.sum((observed - predicted) ** 2) /
                  np.sum((np.abs(predicted - np.mean(observed)) + 
                         np.abs(observed - np.mean(observed))) ** 2))
        
        # Percent Bias
        pbias = 100 * np.sum(predicted - observed) / np.sum(observed)
        
        # Kling-Gupta Efficiency
        kge = self._calculate_kge(observed, predicted)
        
        return {
            'nse': nse,
            'ioa': ioa,
            'pbias': pbias,
            'kge': kge
        }
    
    def _calculate_kge(self, observed: np.ndarray, predicted: np.ndarray) -> float:
        """Calculate Kling-Gupta Efficiency."""
        r = np.corrcoef(observed, predicted)[0, 1]
        alpha = np.std(predicted) / np.std(observed)
        beta = np.mean(predicted) / np.mean(observed)
        
        kge = 1 - np.sqrt((r - 1)**2 + (alpha - 1)**2 + (beta - 1)**2)
        return kge
    
    def _empty_metrics(self) -> Dict[str, float]:
        """Return dictionary with NaN values for empty datasets."""
        return {
            'n_samples': 0,
            'rmse': np.nan,
            'mae': np.nan,
            'bias': np.nan,
            'relative_bias': np.nan,
            'r2': np.nan,
            'correlation': np.nan,
            'std_obs': np.nan,
            'std_pred': np.nan,
            'mean_obs': np.nan,
            'mean_pred': np.nan,
            'nse': np.nan,
            'ioa': np.nan,
            'pbias': np.nan,
            'kge': np.nan
        }
    
    def calculate_confidence_intervals(self, observed: pd.Series, predicted: pd.Series) -> Dict[str, Dict[str, float]]:
        """Calculate confidence intervals for key metrics."""
        mask = ~(observed.isna() | predicted.isna())
        obs_clean = observed[mask].values
        pred_clean = predicted[mask].values
        
        if len(obs_clean) < 10:
            logger.warning("Insufficient data for confidence interval calculation")
            return {}
        
        # Bootstrap confidence intervals
        n_bootstrap = 1000
        bootstrap_metrics = []
        
        for _ in range(n_bootstrap):
            # Bootstrap sample
            indices = np.random.choice(len(obs_clean), size=len(obs_clean), replace=True)
            obs_boot = obs_clean[indices]
            pred_boot = pred_clean[indices]
            
            # Calculate metrics for bootstrap sample
            try:
                metrics = {
                    'rmse': np.sqrt(mean_squared_error(obs_boot, pred_boot)),
                    'bias': np.mean(pred_boot - obs_boot),
                    'correlation': np.corrcoef(obs_boot, pred_boot)[0, 1]
                }
                bootstrap_metrics.append(metrics)
            except:
                continue
        
        if not bootstrap_metrics:
            return {}
        
        # Calculate confidence intervals
        bootstrap_df = pd.DataFrame(bootstrap_metrics)
        alpha = 1 - self.confidence_level
        
        confidence_intervals = {}
        for metric in bootstrap_df.columns:
            lower = bootstrap_df[metric].quantile(alpha/2)
            upper = bootstrap_df[metric].quantile(1 - alpha/2)
            confidence_intervals[metric] = {
                'lower': lower,
                'upper': upper,
                'width': upper - lower
            }
        
        return confidence_intervals
    
    def perform_significance_tests(self, datasets: Dict[str, pd.Series]) -> Dict[str, Any]:
        """Perform statistical significance tests between datasets."""
        results = {}
        
        dataset_names = list(datasets.keys())
        
        # Pairwise comparisons
        for i, name1 in enumerate(dataset_names):
            for name2 in dataset_names[i+1:]:
                pair_name = f"{name1}_vs_{name2}"
                
                data1 = datasets[name1].dropna()
                data2 = datasets[name2].dropna()
                
                if len(data1) < 5 or len(data2) < 5:
                    logger.warning(f"Insufficient data for significance test: {pair_name}")
                    continue
                
                # T-test for means
                t_stat, t_pvalue = stats.ttest_ind(data1, data2)
                
                # Mann-Whitney U test (non-parametric)
                u_stat, u_pvalue = stats.mannwhitneyu(data1, data2, alternative='two-sided')
                
                # Kolmogorov-Smirnov test for distributions
                ks_stat, ks_pvalue = stats.ks_2samp(data1, data2)
                
                results[pair_name] = {
                    'n1': len(data1),
                    'n2': len(data2),
                    'mean1': data1.mean(),
                    'mean2': data2.mean(),
                    'std1': data1.std(),
                    'std2': data2.std(),
                    't_test': {'statistic': t_stat, 'p_value': t_pvalue},
                    'mann_whitney': {'statistic': u_stat, 'p_value': u_pvalue},
                    'ks_test': {'statistic': ks_stat, 'p_value': ks_pvalue}
                }
        
        return results
    
    def calculate_seasonal_statistics(self, data: pd.DataFrame, 
                                    date_column: str = 'date',
                                    value_column: str = 'albedo') -> Dict[str, Any]:
        """Calculate seasonal statistics for albedo data."""
        if date_column not in data.columns or value_column not in data.columns:
            logger.error(f"Required columns not found: {date_column}, {value_column}")
            return {}
        
        # Ensure datetime index
        data_copy = data.copy()
        if not pd.api.types.is_datetime64_any_dtype(data_copy[date_column]):
            data_copy[date_column] = pd.to_datetime(data_copy[date_column])
        
        # Define seasons
        def get_season(month):
            if month in [12, 1, 2]:
                return 'Winter'
            elif month in [3, 4, 5]:
                return 'Spring'
            elif month in [6, 7, 8]:
                return 'Summer'
            else:
                return 'Autumn'
        
        data_copy['season'] = data_copy[date_column].dt.month.apply(get_season)
        data_copy['month'] = data_copy[date_column].dt.month
        
        # Seasonal statistics
        seasonal_stats = {}
        
        for season in ['Winter', 'Spring', 'Summer', 'Autumn']:
            season_data = data_copy[data_copy['season'] == season][value_column].dropna()
            
            if len(season_data) > 0:
                seasonal_stats[season] = {
                    'count': len(season_data),
                    'mean': season_data.mean(),
                    'std': season_data.std(),
                    'min': season_data.min(),
                    'max': season_data.max(),
                    'median': season_data.median(),
                    'q25': season_data.quantile(0.25),
                    'q75': season_data.quantile(0.75)
                }
        
        # Monthly statistics
        monthly_stats = {}
        for month in range(1, 13):
            month_data = data_copy[data_copy['month'] == month][value_column].dropna()
            
            if len(month_data) > 0:
                monthly_stats[month] = {
                    'count': len(month_data),
                    'mean': month_data.mean(),
                    'std': month_data.std()
                }
        
        return {
            'seasonal': seasonal_stats,
            'monthly': monthly_stats
        }
    
    def trend_analysis(self, data: pd.DataFrame, 
                      date_column: str = 'date',
                      value_column: str = 'albedo') -> Dict[str, Any]:
        """Perform trend analysis on time series data."""
        if date_column not in data.columns or value_column not in data.columns:
            logger.error(f"Required columns not found: {date_column}, {value_column}")
            return {}
        
        # Prepare data
        data_clean = data.dropna(subset=[date_column, value_column]).copy()
        if len(data_clean) < 10:
            logger.warning("Insufficient data for trend analysis")
            return {}
        
        data_clean = data_clean.sort_values(date_column)
        
        # Convert dates to ordinal for regression
        dates_ordinal = pd.to_datetime(data_clean[date_column]).map(pd.Timestamp.toordinal)
        values = data_clean[value_column].values
        
        # Linear trend
        slope, intercept, r_value, p_value, std_err = stats.linregress(dates_ordinal, values)
        
        # Mann-Kendall trend test
        mk_result = self._mann_kendall_test(values)
        
        # Calculate trend per year
        days_per_year = 365.25
        trend_per_year = slope * days_per_year
        
        return {
            'linear_trend': {
                'slope': slope,
                'slope_per_year': trend_per_year,
                'intercept': intercept,
                'r_squared': r_value**2,
                'p_value': p_value,
                'std_error': std_err
            },
            'mann_kendall': mk_result,
            'data_period': {
                'start': data_clean[date_column].min().strftime('%Y-%m-%d'),
                'end': data_clean[date_column].max().strftime('%Y-%m-%d'),
                'duration_years': (data_clean[date_column].max() - data_clean[date_column].min()).days / 365.25
            }
        }
    
    def _mann_kendall_test(self, data: np.ndarray) -> Dict[str, float]:
        """Perform Mann-Kendall trend test."""
        n = len(data)
        
        # Calculate S statistic
        S = 0
        for i in range(n-1):
            for j in range(i+1, n):
                if data[j] > data[i]:
                    S += 1
                elif data[j] < data[i]:
                    S -= 1
        
        # Calculate variance
        var_S = n * (n - 1) * (2*n + 5) / 18
        
        # Calculate Z statistic
        if S > 0:
            Z = (S - 1) / np.sqrt(var_S)
        elif S < 0:
            Z = (S + 1) / np.sqrt(var_S)
        else:
            Z = 0
        
        # Calculate p-value (two-tailed)
        p_value = 2 * (1 - stats.norm.cdf(abs(Z)))
        
        return {
            'S': S,
            'Z': Z,
            'p_value': p_value,
            'trend': 'increasing' if Z > 0 else 'decreasing' if Z < 0 else 'no trend'
        }
    
    def compare_multiple_methods(self, reference_data: pd.Series, 
                               method_data: Dict[str, pd.Series]) -> pd.DataFrame:
        """Compare multiple methods against reference data."""
        comparison_results = []
        
        for method_name, method_values in method_data.items():
            metrics = self.calculate_basic_metrics(reference_data, method_values)
            metrics['method'] = method_name
            comparison_results.append(metrics)
        
        results_df = pd.DataFrame(comparison_results)
        
        # Rank methods by different criteria
        ranking_metrics = ['rmse', 'mae', 'bias', 'r2', 'correlation']
        
        for metric in ranking_metrics:
            if metric in ['r2', 'correlation']:
                # Higher is better
                results_df[f'{metric}_rank'] = results_df[metric].rank(ascending=False)
            else:
                # Lower is better (for RMSE, MAE, bias)
                results_df[f'{metric}_rank'] = results_df[metric].abs().rank(ascending=True)
        
        # Overall ranking (average of individual ranks)
        rank_columns = [col for col in results_df.columns if col.endswith('_rank')]
        results_df['overall_rank'] = results_df[rank_columns].mean(axis=1)
        
        return results_df.sort_values('overall_rank')
    
    def generate_comparison_summary(self, comparison_results: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary of method comparison results."""
        if comparison_results.empty:
            return {}
        
        best_method = comparison_results.iloc[0]['method']
        
        summary = {
            'best_overall_method': best_method,
            'total_methods_compared': len(comparison_results),
            'metrics_summary': {},
            'method_rankings': comparison_results[['method', 'overall_rank']].to_dict('records')
        }
        
        # Summarize performance metrics
        numeric_cols = comparison_results.select_dtypes(include=[np.number]).columns
        metric_cols = [col for col in numeric_cols if not col.endswith('_rank') and col != 'n_samples']
        
        for metric in metric_cols:
            summary['metrics_summary'][metric] = {
                'best_value': comparison_results[metric].iloc[0],
                'worst_value': comparison_results[metric].iloc[-1],
                'range': comparison_results[metric].max() - comparison_results[metric].min(),
                'mean': comparison_results[metric].mean(),
                'std': comparison_results[metric].std()
            }
        
        return summary