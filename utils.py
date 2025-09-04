"""
Utility functions for the TSX Stock Analyzer
"""

import logging
import time
import functools
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

def retry_with_backoff(retries: int = 3, backoff_factor: float = 1.0):
    """Decorator to retry functions with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == retries - 1:  # Last attempt
                        raise e
                    
                    wait_time = backoff_factor * (2 ** attempt)
                    logging.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
            
        return wrapper
    return decorator

def log_execution_time(func: Callable) -> Callable:
    """Decorator to log function execution time"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        logging.info(f"{func.__name__} executed in {execution_time:.2f} seconds")
        return result
    
    return wrapper

def validate_symbol(symbol: str) -> bool:
    """Validate TSX symbol format"""
    if not symbol or not isinstance(symbol, str):
        return False
    
    # TSX symbols end with .TO
    if not symbol.endswith('.TO'):
        return False
    
    # Remove .TO and check the base symbol
    base_symbol = symbol[:-3]
    
    # Should be 1-5 characters, alphanumeric
    if not (1 <= len(base_symbol) <= 5) or not base_symbol.isalnum():
        return False
    
    return True

def format_currency(amount: float, currency: str = 'CAD') -> str:
    """Format currency values"""
    if currency == 'CAD':
        return f"${amount:,.2f} CAD"
    else:
        return f"${amount:,.2f}"

def format_percentage(value: float, decimal_places: int = 1) -> str:
    """Format percentage values"""
    return f"{value * 100:.{decimal_places}f}%"

def calculate_trading_days(start_date: datetime, end_date: datetime) -> int:
    """Calculate number of trading days between two dates (approximate)"""
    total_days = (end_date - start_date).days
    # Approximate: 5/7 of days are trading days, minus holidays (~10 per year)
    trading_days = int(total_days * 5/7 - (total_days / 365 * 10))
    return max(0, trading_days)

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero"""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ZeroDivisionError):
        return default

def normalize_score(value: float, min_val: float, max_val: float, 
                   target_min: float = 0, target_max: float = 100) -> float:
    """Normalize a value to a target range"""
    if max_val == min_val:
        return target_min
    
    normalized = (value - min_val) / (max_val - min_val)
    return target_min + normalized * (target_max - target_min)

def get_risk_level(risk_percentage: float) -> str:
    """Convert risk percentage to descriptive level"""
    if risk_percentage < 25:
        return "Low"
    elif risk_percentage < 50:
        return "Moderate"
    elif risk_percentage < 75:
        return "High"
    else:
        return "Very High"

def get_score_grade(score: int) -> str:
    """Convert numerical score to letter grade"""
    if score >= 90:
        return "A+"
    elif score >= 85:
        return "A"
    elif score >= 80:
        return "A-"
    elif score >= 75:
        return "B+"
    elif score >= 70:
        return "B"
    elif score >= 65:
        return "B-"
    elif score >= 60:
        return "C+"
    elif score >= 55:
        return "C"
    elif score >= 50:
        return "C-"
    elif score >= 45:
        return "D+"
    elif score >= 40:
        return "D"
    else:
        return "F"

def clean_financial_data(value) -> Optional[float]:
    """Clean and validate financial data from API"""
    if value is None:
        return None
    
    try:
        # Handle string values
        if isinstance(value, str):
            # Remove common formatting
            cleaned = value.replace(',', '').replace('$', '').replace('%', '')
            value = float(cleaned)
        
        # Handle infinite or very large values
        if abs(value) > 1e15:  # Arbitrary large number threshold
            return None
            
        return float(value)
    except (ValueError, TypeError):
        return None

def validate_date_range(start_date: str, end_date: str) -> bool:
    """Validate date range for data requests"""
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Check if dates are reasonable
        if start > end:
            return False
        
        if start < datetime(1990, 1, 1):  # Too far back
            return False
            
        if end > datetime.now() + timedelta(days=1):  # Future date
            return False
            
        return True
    except ValueError:
        return False