"""
Database Manager for TSX Stock Analyzer
Handles all database operations in a clean, modular way
"""

import sqlite3
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages all database operations for the TSX analyzer"""
    
    def __init__(self, db_path: str = "tsx_analyzer.db"):
        self.db_path = db_path
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
        """Initialize database with all required tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Companies table - TSX composite companies
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS companies (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    sector TEXT,
                    industry TEXT,
                    market_cap REAL,
                    employees INTEGER,
                    description TEXT,
                    website TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    last_updated TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Daily price data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_prices (
                    symbol TEXT,
                    date DATE,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    adj_close REAL,
                    volume INTEGER,
                    PRIMARY KEY (symbol, date),
                    FOREIGN KEY (symbol) REFERENCES companies (symbol)
                )
            ''')
            
            # Fundamental data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fundamentals (
                    symbol TEXT,
                    date DATE,
                    pe_ratio REAL,
                    forward_pe REAL,
                    peg_ratio REAL,
                    price_to_book REAL,
                    debt_to_equity REAL,
                    roe REAL,
                    profit_margin REAL,
                    revenue_growth REAL,
                    earnings_growth REAL,
                    dividend_yield REAL,
                    payout_ratio REAL,
                    beta REAL,
                    current_ratio REAL,
                    quick_ratio REAL,
                    PRIMARY KEY (symbol, date),
                    FOREIGN KEY (symbol) REFERENCES companies (symbol)
                )
            ''')
            
            # Analysis results
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_results (
                    symbol TEXT,
                    analysis_date TIMESTAMP,
                    total_score INTEGER,
                    fundamental_score INTEGER,
                    technical_score INTEGER,
                    momentum_score INTEGER,
                    risk_score INTEGER,
                    recommendation TEXT,
                    current_price REAL,
                    target_price REAL,
                    conservative_buy_price REAL,
                    aggressive_buy_price REAL,
                    upside_potential REAL,
                    risk_percentage REAL,
                    PRIMARY KEY (symbol, analysis_date),
                    FOREIGN KEY (symbol) REFERENCES companies (symbol)
                )
            ''')
            
            # System settings
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Data ingestion log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ingestion_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    data_type TEXT,
                    start_date DATE,
                    end_date DATE,
                    records_inserted INTEGER,
                    success BOOLEAN,
                    error_message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_daily_prices_symbol_date ON daily_prices(symbol, date DESC)',
                'CREATE INDEX IF NOT EXISTS idx_analysis_results_symbol_date ON analysis_results(symbol, analysis_date DESC)',
                'CREATE INDEX IF NOT EXISTS idx_companies_sector ON companies(sector)',
                'CREATE INDEX IF NOT EXISTS idx_companies_active ON companies(is_active)',
                'CREATE INDEX IF NOT EXISTS idx_ingestion_log_symbol ON ingestion_log(symbol, timestamp DESC)'
            ]
            
            for index in indexes:
                cursor.execute(index)
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    # Companies methods
    def add_company(self, company_data: Dict) -> bool:
        """Add or update company information"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO companies 
                    (symbol, name, sector, industry, market_cap, employees, description, website, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    company_data['symbol'],
                    company_data.get('name', ''),
                    company_data.get('sector', ''),
                    company_data.get('industry', ''),
                    company_data.get('market_cap', 0),
                    company_data.get('employees', 0),
                    company_data.get('description', ''),
                    company_data.get('website', ''),
                    datetime.now()
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding company {company_data.get('symbol')}: {e}")
            return False
    
    def get_all_companies(self, active_only: bool = True) -> List[Dict]:
        """Get all companies from database"""
        try:
            with self.get_connection() as conn:
                query = "SELECT * FROM companies"
                if active_only:
                    query += " WHERE is_active = 1"
                query += " ORDER BY market_cap DESC"
                
                df = pd.read_sql(query, conn)
                return df.to_dict('records')
        except Exception as e:
            logger.error(f"Error getting companies: {e}")
            return []
    
    def get_company(self, symbol: str) -> Optional[Dict]:
        """Get single company information"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM companies WHERE symbol = ?", (symbol,))
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            logger.error(f"Error getting company {symbol}: {e}")
            return None
    
    # Price data methods
    def add_price_data(self, symbol: str, price_data: pd.DataFrame) -> int:
        """Add price data for a symbol"""
        try:
            with self.get_connection() as conn:
                # Prepare data
                df = price_data.copy()
                df['symbol'] = symbol
                
                # Use INSERT OR REPLACE to handle duplicates
                records_added = df.to_sql('daily_prices', conn, if_exists='append', 
                                        index=False, method='multi')
                
                # Log the ingestion
                self.log_ingestion(symbol, 'price_data', df['date'].min(), 
                                 df['date'].max(), len(df), True)
                
                return len(df)
        except Exception as e:
            logger.error(f"Error adding price data for {symbol}: {e}")
            self.log_ingestion(symbol, 'price_data', None, None, 0, False, str(e))
            return 0
    
    def get_price_data(self, symbol: str, days: int = 252, 
                      start_date: Optional[str] = None, 
                      end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Get price data for a symbol"""
        try:
            with self.get_connection() as conn:
                if start_date and end_date:
                    query = '''
                        SELECT date, open, high, low, close, adj_close, volume
                        FROM daily_prices 
                        WHERE symbol = ? AND date BETWEEN ? AND ?
                        ORDER BY date ASC
                    '''
                    params = (symbol, start_date, end_date)
                else:
                    query = '''
                        SELECT date, open, high, low, close, adj_close, volume
                        FROM daily_prices 
                        WHERE symbol = ?
                        ORDER BY date DESC 
                        LIMIT ?
                    '''
                    params = (symbol, days)
                
                df = pd.read_sql(query, conn, params=params)
                
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    if not (start_date and end_date):
                        df = df.sort_values('date')  # Sort ascending for analysis
                    df.reset_index(drop=True, inplace=True)
                
                return df if not df.empty else None
        except Exception as e:
            logger.error(f"Error getting price data for {symbol}: {e}")
            return None
    
    def get_latest_price_date(self, symbol: str) -> Optional[str]:
        """Get the latest date we have price data for a symbol"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT MAX(date) FROM daily_prices WHERE symbol = ?
                ''', (symbol,))
                result = cursor.fetchone()
                return result[0] if result and result[0] else None
        except Exception as e:
            logger.error(f"Error getting latest price date for {symbol}: {e}")
            return None
    
    # Fundamentals methods
    def add_fundamental_data(self, symbol: str, fundamental_data: Dict) -> bool:
        """Add fundamental data for a symbol"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO fundamentals 
                    (symbol, date, pe_ratio, forward_pe, peg_ratio, price_to_book, 
                     debt_to_equity, roe, profit_margin, revenue_growth, earnings_growth,
                     dividend_yield, payout_ratio, beta, current_ratio, quick_ratio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol,
                    datetime.now().date(),
                    fundamental_data.get('pe_ratio'),
                    fundamental_data.get('forward_pe'),
                    fundamental_data.get('peg_ratio'),
                    fundamental_data.get('price_to_book'),
                    fundamental_data.get('debt_to_equity'),
                    fundamental_data.get('roe'),
                    fundamental_data.get('profit_margin'),
                    fundamental_data.get('revenue_growth'),
                    fundamental_data.get('earnings_growth'),
                    fundamental_data.get('dividend_yield'),
                    fundamental_data.get('payout_ratio'),
                    fundamental_data.get('beta'),
                    fundamental_data.get('current_ratio'),
                    fundamental_data.get('quick_ratio')
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding fundamental data for {symbol}: {e}")
            return False
    
    def get_latest_fundamentals(self, symbol: str) -> Optional[Dict]:
        """Get latest fundamental data for a symbol"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM fundamentals 
                    WHERE symbol = ? 
                    ORDER BY date DESC 
                    LIMIT 1
                ''', (symbol,))
                
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            logger.error(f"Error getting fundamentals for {symbol}: {e}")
            return None
    
    # Analysis results methods
    def save_analysis_result(self, analysis_result: Dict) -> bool:
        """Save analysis result to database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Ensure all numeric values are properly converted
                total_score = int(analysis_result.get('total_score', 0))
                fundamental_score = int(analysis_result.get('fundamental_score', 0))
                technical_score = int(analysis_result.get('technical_score', 0))
                momentum_score = int(analysis_result.get('momentum_score', 0))
                risk_score = int(analysis_result.get('risk_score', 0))
                
                pricing = analysis_result.get('pricing', {})
                current_price = float(pricing.get('current_price', 0))
                target_price = float(pricing.get('target_price', 0))
                conservative_buy_price = float(pricing.get('conservative_buy_price', 0))
                aggressive_buy_price = float(pricing.get('aggressive_buy_price', 0))
                upside_potential = float(pricing.get('upside_potential', 0))
                risk_percentage = float(analysis_result.get('risk_percentage', 0))
                
                cursor.execute('''
                    INSERT OR REPLACE INTO analysis_results 
                    (symbol, analysis_date, total_score, fundamental_score, technical_score,
                     momentum_score, risk_score, recommendation, current_price, target_price,
                     conservative_buy_price, aggressive_buy_price, upside_potential, risk_percentage)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    analysis_result['symbol'],
                    datetime.now(),
                    total_score,
                    fundamental_score,
                    technical_score,
                    momentum_score,
                    risk_score,
                    analysis_result['recommendation'],
                    current_price,
                    target_price,
                    conservative_buy_price,
                    aggressive_buy_price,
                    upside_potential,
                    risk_percentage
                ))
                
                conn.commit()
                logger.info(f"Saved analysis for {analysis_result['symbol']}: Total score {total_score}")
                return True
        except Exception as e:
            logger.error(f"Error saving analysis result for {analysis_result.get('symbol')}: {e}")
            return False
    
    def get_latest_analysis(self, symbol: str) -> Optional[Dict]:
        """Get latest analysis result for a symbol"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM analysis_results 
                    WHERE symbol = ? 
                    ORDER BY analysis_date DESC 
                    LIMIT 1
                ''', (symbol,))
                
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    result = dict(zip(columns, row))
                    
                    # Clean up data types
                    numeric_fields = ['total_score', 'fundamental_score', 'technical_score', 
                                    'momentum_score', 'risk_score', 'current_price', 'target_price',
                                    'conservative_buy_price', 'aggressive_buy_price', 'upside_potential',
                                    'risk_percentage']
                    
                    for field in numeric_fields:
                        if field in result and result[field] is not None:
                            try:
                                # Convert bytes to float if needed
                                if isinstance(result[field], bytes):
                                    result[field] = float(result[field].decode('utf-8'))
                                else:
                                    result[field] = float(result[field])
                            except (ValueError, AttributeError):
                                result[field] = 0.0
                    
                    return result
                return None
        except Exception as e:
            logger.error(f"Error getting analysis for {symbol}: {e}")
            return None
    
    def get_all_latest_analyses(self) -> List[Dict]:
        """Get latest analysis for all companies"""
        try:
            with self.get_connection() as conn:
                query = '''
                    SELECT a.*, c.name, c.sector 
                    FROM analysis_results a
                    JOIN companies c ON a.symbol = c.symbol
                    WHERE a.analysis_date = (
                        SELECT MAX(analysis_date) 
                        FROM analysis_results a2 
                        WHERE a2.symbol = a.symbol
                    )
                    AND c.is_active = 1
                    ORDER BY a.total_score DESC
                '''
                df = pd.read_sql(query, conn)
                
                # Convert to records and ensure proper data types
                records = df.to_dict('records')
                
                # Clean up data types
                for record in records:
                    # Convert numeric fields to proper types
                    numeric_fields = ['total_score', 'fundamental_score', 'technical_score', 
                                    'momentum_score', 'risk_score', 'current_price', 'target_price',
                                    'conservative_buy_price', 'aggressive_buy_price', 'upside_potential',
                                    'risk_percentage']
                    
                    for field in numeric_fields:
                        if field in record and record[field] is not None:
                            try:
                                # Convert bytes to float if needed
                                if isinstance(record[field], bytes):
                                    record[field] = float(record[field].decode('utf-8'))
                                else:
                                    record[field] = float(record[field])
                            except (ValueError, AttributeError):
                                record[field] = 0.0
                
                return records
        except Exception as e:
            logger.error(f"Error getting all analyses: {e}")
            return []
    
    # Utility methods
    def log_ingestion(self, symbol: str, data_type: str, start_date: Optional[str], 
                     end_date: Optional[str], records: int, success: bool, 
                     error_message: Optional[str] = None):
        """Log data ingestion attempts"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO ingestion_log 
                    (symbol, data_type, start_date, end_date, records_inserted, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (symbol, data_type, start_date, end_date, records, success, error_message))
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging ingestion: {e}")
    
    def get_system_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get system setting value"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
                result = cursor.fetchone()
                return result[0] if result else default
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default
    
    def set_system_setting(self, key: str, value: str) -> bool:
        """Set system setting value"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO system_settings (key, value, updated_at)
                    VALUES (?, ?, ?)
                ''', (key, value, datetime.now()))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            return False
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # File size
                if os.path.exists(self.db_path):
                    stats['file_size_mb'] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)
                else:
                    stats['file_size_mb'] = 0
                
                # Record counts
                tables = ['companies', 'daily_prices', 'fundamentals', 'analysis_results']
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f'{table}_count'] = cursor.fetchone()[0]
                
                # Date ranges
                cursor.execute("SELECT MIN(date), MAX(date) FROM daily_prices")
                date_range = cursor.fetchone()
                stats['price_data_range'] = {
                    'start': date_range[0],
                    'end': date_range[1]
                }
                
                return stats
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    def cleanup_old_data(self, days_to_keep: int = 365):
        """Clean up old analysis results (keep price data)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cutoff_date = datetime.now() - timedelta(days=days_to_keep)
                
                cursor.execute('''
                    DELETE FROM analysis_results 
                    WHERE analysis_date < ?
                ''', (cutoff_date,))
                
                cursor.execute('''
                    DELETE FROM ingestion_log 
                    WHERE timestamp < ?
                ''', (cutoff_date,))
                
                conn.commit()
                logger.info(f"Cleaned up data older than {days_to_keep} days")
                return True
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            return False