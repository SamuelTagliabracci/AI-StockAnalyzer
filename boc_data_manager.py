"""
Bank of Canada Data Manager
Handles fetching and storing economic data from Bank of Canada APIs
"""

import requests
import pandas as pd
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager
import json
import time

logger = logging.getLogger(__name__)

class BankOfCanadaDataManager:
    """Manages Bank of Canada economic data ingestion and storage"""
    
    # Bank of Canada key economic indicators
    BOC_SERIES = {
        # Interest Rates
        'overnight_rate': 'V39079',           # Bank Rate
        'prime_rate': 'V122530',              # Prime lending rate
        'mortgage_1yr': 'V122521',            # 1-year mortgage rate
        'mortgage_5yr': 'V122515',            # 5-year mortgage rate
        'gov_bond_2yr': 'V122484',            # 2-year government bond
        'gov_bond_5yr': 'V122487',            # 5-year government bond
        'gov_bond_10yr': 'V122490',           # 10-year government bond
        'gov_bond_30yr': 'V122493',           # 30-year government bond
        
        # Exchange Rates
        'cad_usd': 'FXUSDCAD',                # CAD/USD exchange rate
        'cad_eur': 'FXEURCAD',                # CAD/EUR exchange rate
        'cad_gbp': 'FXGBPCAD',                # CAD/GBP exchange rate
        'cad_jpy': 'FXJPYCAD',                # CAD/JPY exchange rate
        
        # Economic Indicators
        'cpi_total': 'V41690973',             # Consumer Price Index
        'cpi_core': 'V41690914',              # Core CPI
        'gdp_monthly': 'V65201210',           # Monthly GDP
        'employment_rate': 'V2062815',        # Employment rate
        'unemployment_rate': 'V2062812',      # Unemployment rate
        'wage_growth': 'V103501909',          # Average hourly earnings growth
        
        # Money Supply
        'money_supply_m1': 'V37426',          # M1 money supply
        'money_supply_m2': 'V37427',          # M2 money supply
        'money_supply_m3': 'V37428',          # M3 money supply
        
        # Financial Markets
        'tsx_composite': 'V122620',           # TSX Composite Index
        'bank_credit': 'V122649',             # Total bank credit
        'business_credit': 'V122657',         # Business credit
        'consumer_credit': 'V122654',         # Consumer credit
        
        # Commodity Prices (Bank of Canada commodity price index)
        'commodity_index': 'V122530',         # Bank of Canada commodity price index
        'energy_index': 'V122531',            # Energy sub-index
        'metals_index': 'V122532',            # Metals and minerals sub-index
        'agriculture_index': 'V122533',       # Agriculture sub-index
        
        # Housing
        'housing_starts': 'V735394',          # Housing starts
        'house_price_index': 'V735426',       # New housing price index
        
        # Business Indicators
        'business_confidence': 'V122680',     # Business outlook survey
        'capacity_utilization': 'V122681',    # Capacity utilization
    }
    
    def __init__(self, db_path: str = "tsx_analyzer.db"):
        self.db_path = db_path
        self.base_url = "https://www.bankofcanada.ca/valet"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TSX-Stock-Analyzer/1.0',
            'Accept': 'application/json'
        })
        self.setup_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def setup_database(self):
        """Initialize database tables for Bank of Canada data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Economic data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS boc_economic_data (
                    series_code TEXT,
                    series_name TEXT,
                    date DATE,
                    value REAL,
                    frequency TEXT,
                    unit TEXT,
                    category TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (series_code, date)
                )
            ''')
            
            # Series metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS boc_series_metadata (
                    series_code TEXT PRIMARY KEY,
                    series_name TEXT,
                    description TEXT,
                    frequency TEXT,
                    unit TEXT,
                    category TEXT,
                    source TEXT,
                    first_observation DATE,
                    last_observation DATE,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Economic events/announcements table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS boc_announcements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE,
                    title TEXT,
                    summary TEXT,
                    type TEXT,
                    impact_level TEXT,
                    url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_boc_data_date ON boc_economic_data(date DESC)',
                'CREATE INDEX IF NOT EXISTS idx_boc_data_series ON boc_economic_data(series_code)',
                'CREATE INDEX IF NOT EXISTS idx_boc_announcements_date ON boc_announcements(date DESC)',
            ]
            
            for index in indexes:
                cursor.execute(index)
            
            conn.commit()
            logger.info("Bank of Canada database tables initialized")
    
    def fetch_series_data(self, series_code: str, start_date: str = None, 
                         end_date: str = None) -> Optional[pd.DataFrame]:
        """Fetch data for a specific series from Bank of Canada API"""
        try:
            # Construct API URL
            url = f"{self.base_url}/observations/{series_code}/json"
            
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            
            logger.info(f"Fetching BOC data for series {series_code}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract observations
            if 'observations' not in data:
                logger.warning(f"No observations found for series {series_code}")
                return None
            
            observations = data['observations']
            if not observations:
                logger.warning(f"Empty observations for series {series_code}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(observations)
            
            # Clean and process data
            df['date'] = pd.to_datetime(df['d'])
            df['value'] = pd.to_numeric(df['v'], errors='coerce')
            df = df[['date', 'value']].dropna()
            
            # Add metadata
            df['series_code'] = series_code
            df['series_name'] = self.get_series_name(series_code)
            
            logger.info(f"Retrieved {len(df)} observations for {series_code}")
            return df
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API error fetching {series_code}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing {series_code}: {e}")
            return None
    
    def fetch_series_metadata(self, series_code: str) -> Optional[Dict]:
        """Fetch metadata for a specific series"""
        try:
            url = f"{self.base_url}/series/{series_code}/json"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'series' not in data or not data['series']:
                return None
            
            series_info = data['series'][0]
            
            metadata = {
                'series_code': series_code,
                'series_name': series_info.get('label', ''),
                'description': series_info.get('description', ''),
                'frequency': series_info.get('frequency', ''),
                'unit': series_info.get('unit', ''),
                'source': 'Bank of Canada',
                'first_observation': series_info.get('firstObservation', ''),
                'last_observation': series_info.get('lastObservation', '')
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error fetching metadata for {series_code}: {e}")
            return None
    
    def get_series_name(self, series_code: str) -> str:
        """Get human-readable name for series code"""
        # Reverse lookup in BOC_SERIES
        for name, code in self.BOC_SERIES.items():
            if code == series_code:
                return name.replace('_', ' ').title()
        return series_code
    
    def get_series_category(self, series_name: str) -> str:
        """Categorize series by type"""
        name_lower = series_name.lower()
        
        if any(term in name_lower for term in ['rate', 'bond', 'yield', 'mortgage']):
            return 'Interest Rates'
        elif any(term in name_lower for term in ['cad', 'usd', 'eur', 'exchange']):
            return 'Exchange Rates'
        elif any(term in name_lower for term in ['cpi', 'inflation', 'gdp', 'employment', 'unemployment']):
            return 'Economic Indicators'
        elif any(term in name_lower for term in ['money', 'supply', 'm1', 'm2', 'm3']):
            return 'Money Supply'
        elif any(term in name_lower for term in ['credit', 'bank', 'loan']):
            return 'Financial Markets'
        elif any(term in name_lower for term in ['commodity', 'energy', 'metals', 'agriculture']):
            return 'Commodity Prices'
        elif any(term in name_lower for term in ['housing', 'house', 'home']):
            return 'Housing'
        elif any(term in name_lower for term in ['business', 'confidence', 'capacity']):
            return 'Business Indicators'
        else:
            return 'Other'
    
    def store_series_data(self, df: pd.DataFrame) -> int:
        """Store series data in database"""
        if df is None or df.empty:
            return 0
        
        try:
            with self.get_connection() as conn:
                # Prepare data for insertion
                series_code = df.iloc[0]['series_code']
                series_name = df.iloc[0]['series_name']
                category = self.get_series_category(series_name)
                
                # Add additional columns
                df['frequency'] = 'Daily'  # Default, can be updated with metadata
                df['unit'] = ''
                df['category'] = category
                
                # Select columns for database
                columns = ['series_code', 'series_name', 'date', 'value', 
                          'frequency', 'unit', 'category']
                
                # Use INSERT OR REPLACE to handle duplicates
                df[columns].to_sql('boc_economic_data', conn, if_exists='append', 
                                  index=False, method='multi')
                
                logger.info(f"Stored {len(df)} records for {series_code}")
                return len(df)
                
        except Exception as e:
            logger.error(f"Error storing data: {e}")
            return 0
    
    def store_series_metadata(self, metadata: Dict) -> bool:
        """Store series metadata in database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Add category
                metadata['category'] = self.get_series_category(metadata['series_name'])
                
                cursor.execute('''
                    INSERT OR REPLACE INTO boc_series_metadata 
                    (series_code, series_name, description, frequency, unit, 
                     category, source, first_observation, last_observation)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metadata['series_code'],
                    metadata['series_name'],
                    metadata['description'],
                    metadata['frequency'],
                    metadata['unit'],
                    metadata['category'],
                    metadata['source'],
                    metadata['first_observation'],
                    metadata['last_observation']
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error storing metadata: {e}")
            return False
    
    def get_latest_data_date(self, series_code: str) -> Optional[str]:
        """Get the latest date we have data for a series"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT MAX(date) FROM boc_economic_data 
                    WHERE series_code = ?
                ''', (series_code,))
                
                result = cursor.fetchone()
                return result[0] if result and result[0] else None
                
        except Exception as e:
            logger.error(f"Error getting latest date for {series_code}: {e}")
            return None
    
    def update_series(self, series_code: str, series_name: str) -> bool:
        """Update a single economic series"""
        try:
            # Get the latest date we have data for
            latest_date = self.get_latest_data_date(series_code)
            
            # If we have data, fetch only newer data
            start_date = None
            if latest_date:
                # Start from day after latest date
                start_dt = datetime.strptime(latest_date, '%Y-%m-%d') + timedelta(days=1)
                start_date = start_dt.strftime('%Y-%m-%d')
                logger.info(f"Updating {series_code} from {start_date}")
            else:
                # Get 2 years of historical data for new series
                start_dt = datetime.now() - timedelta(days=2*365)
                start_date = start_dt.strftime('%Y-%m-%d')
                logger.info(f"Fetching {series_code} from {start_date} (new series)")
            
            # Fetch data
            df = self.fetch_series_data(series_code, start_date)
            
            if df is not None and not df.empty:
                # Store data
                records_stored = self.store_series_data(df)
                
                # Fetch and store metadata
                metadata = self.fetch_series_metadata(series_code)
                if metadata:
                    self.store_series_metadata(metadata)
                
                logger.info(f"Updated {series_code}: {records_stored} new records")
                return True
            else:
                logger.info(f"No new data for {series_code}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating {series_code}: {e}")
            return False
    
    def update_all_series(self) -> Dict[str, int]:
        """Update all Bank of Canada economic series"""
        results = {
            'successful': 0,
            'failed': 0,
            'total_records': 0
        }
        
        logger.info(f"Updating {len(self.BOC_SERIES)} Bank of Canada series")
        
        for series_name, series_code in self.BOC_SERIES.items():
            try:
                logger.info(f"Updating {series_name} ({series_code})")
                
                if self.update_series(series_code, series_name):
                    results['successful'] += 1
                else:
                    results['failed'] += 1
                
                # Rate limiting - be respectful to BOC servers
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error updating {series_name}: {e}")
                results['failed'] += 1
        
        logger.info(f"BOC update complete. Success: {results['successful']}, "
                   f"Failed: {results['failed']}")
        
        return results
    
    def get_series_data(self, series_code: str, days: int = 365) -> Optional[pd.DataFrame]:
        """Retrieve stored data for a series"""
        try:
            with self.get_connection() as conn:
                cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                
                query = '''
                    SELECT date, value, series_name, category, unit
                    FROM boc_economic_data 
                    WHERE series_code = ? AND date >= ?
                    ORDER BY date DESC
                '''
                
                df = pd.read_sql(query, conn, params=(series_code, cutoff_date))
                
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.sort_values('date')
                
                return df if not df.empty else None
                
        except Exception as e:
            logger.error(f"Error retrieving data for {series_code}: {e}")
            return None
    
    def get_latest_values(self) -> Dict[str, float]:
        """Get the most recent value for each series"""
        try:
            with self.get_connection() as conn:
                query = '''
                    SELECT e1.series_code, e1.value, e1.date, m.series_name
                    FROM boc_economic_data e1
                    JOIN boc_series_metadata m ON e1.series_code = m.series_code
                    WHERE e1.date = (
                        SELECT MAX(date) 
                        FROM boc_economic_data e2 
                        WHERE e2.series_code = e1.series_code
                    )
                    ORDER BY m.category, m.series_name
                '''
                
                df = pd.read_sql(query, conn)
                
                # Convert to dictionary with series names as keys
                latest_values = {}
                for _, row in df.iterrows():
                    # Use human-readable name
                    name = self.get_series_name(row['series_code'])
                    latest_values[name] = {
                        'value': row['value'],
                        'date': row['date'],
                        'series_code': row['series_code']
                    }
                
                return latest_values
                
        except Exception as e:
            logger.error(f"Error getting latest values: {e}")
            return {}
    
    def get_database_stats(self) -> Dict:
        """Get statistics about stored Bank of Canada data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Count total records
                cursor.execute("SELECT COUNT(*) FROM boc_economic_data")
                total_records = cursor.fetchone()[0]
                
                # Count series
                cursor.execute("SELECT COUNT(DISTINCT series_code) FROM boc_economic_data")
                series_count = cursor.fetchone()[0]
                
                # Date range
                cursor.execute("SELECT MIN(date), MAX(date) FROM boc_economic_data")
                date_range = cursor.fetchone()
                
                # Records by category
                cursor.execute('''
                    SELECT category, COUNT(*) 
                    FROM boc_economic_data 
                    GROUP BY category 
                    ORDER BY COUNT(*) DESC
                ''')
                category_counts = dict(cursor.fetchall())
                
                return {
                    'total_records': total_records,
                    'series_count': series_count,
                    'date_range': {
                        'start': date_range[0],
                        'end': date_range[1]
                    },
                    'category_counts': category_counts,
                    'last_updated': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting BOC database stats: {e}")
            return {}

# Utility functions for integration
def get_key_economic_indicators() -> Dict[str, str]:
    """Get a subset of key indicators for dashboard display"""
    return {
        'Bank Rate': 'V39079',
        'CAD/USD': 'FXUSDCAD', 
        'CPI': 'V41690973',
        'Unemployment': 'V2062812',
        'GDP Growth': 'V65201210',
        'TSX Composite': 'V122620'
    }

def format_economic_value(value: float, series_name: str) -> str:
    """Format economic values for display"""
    if 'rate' in series_name.lower() or 'cpi' in series_name.lower():
        return f"{value:.2f}%"
    elif 'cad' in series_name.lower() and 'usd' in series_name.lower():
        return f"${value:.4f}"
    elif 'index' in series_name.lower():
        return f"{value:,.0f}"
    elif 'gdp' in series_name.lower():
        return f"${value:,.0f}M"
    else:
        return f"{value:.2f}"