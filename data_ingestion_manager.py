"""
Data Ingestion Manager for TSX Stock Analyzer
Handles data fetching from Yahoo Finance with rate limiting and error handling
"""

import yfinance as yf
import pandas as pd
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from database_manager import DatabaseManager
import json

logger = logging.getLogger(__name__)

class DataIngestionManager:
    """Manages data ingestion from Yahoo Finance with intelligent rate limiting"""
    
    def __init__(self, db_manager: DatabaseManager, config=None):
        self.db = db_manager
        self.daily_limit_reached = False
        self.last_request_time = 0
        
        # Import TSX symbols and settings from config
        try:
            from config import Config
            self.TSX_SYMBOLS = Config.TSX_SYMBOLS
            # Use config values or fallback to Config defaults
            if config:
                self.rate_limit_delay = config.RATE_LIMIT_DELAY
                self.max_retries = config.MAX_RETRIES
                self.request_timeout = config.REQUEST_TIMEOUT
            else:
                self.rate_limit_delay = Config.RATE_LIMIT_DELAY
                self.max_retries = Config.MAX_RETRIES
                self.request_timeout = Config.REQUEST_TIMEOUT
        except ImportError:
            # Fallback list if config import fails
            self.TSX_SYMBOLS = [
                'RY.TO', 'TD.TO', 'BNS.TO', 'BMO.TO', 'CM.TO', 'NA.TO',
                'SHOP.TO', 'CSU.TO', 'OTEX.TO', 'LSPD.TO', 'CNQ.TO', 'SU.TO'
            ]
            self.rate_limit_delay = 1.0
            self.max_retries = 3
            self.request_timeout = 30
        
        # Load rate limit settings from database (can override config)
        self._load_settings()
    
    def _load_settings(self):
        """Load ingestion settings from database"""
        delay = self.db.get_system_setting('rate_limit_delay', '1')
        self.rate_limit_delay = float(delay)
        
        limit_status = self.db.get_system_setting('daily_limit_reached', 'false')
        self.daily_limit_reached = limit_status.lower() == 'true'
        
        # Reset daily limit if it's a new day
        last_reset = self.db.get_system_setting('last_limit_reset')
        today = datetime.now().date().isoformat()
        
        if last_reset != today:
            self.daily_limit_reached = False
            self.db.set_system_setting('daily_limit_reached', 'false')
            self.db.set_system_setting('last_limit_reset', today)
    
    def _respect_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _handle_rate_limit_error(self, error: str):
        """Handle rate limit errors by increasing delay"""
        if 'rate limit' in error.lower() or '429' in error:
            self.rate_limit_delay = min(self.rate_limit_delay * 2, 60)  # Max 60 seconds
            self.db.set_system_setting('rate_limit_delay', str(self.rate_limit_delay))
            logger.warning(f"Rate limit hit, increasing delay to {self.rate_limit_delay}s")
            
            # Check if we should mark daily limit as reached
            if self.rate_limit_delay >= 30:
                self.daily_limit_reached = True
                self.db.set_system_setting('daily_limit_reached', 'true')
                logger.error("Daily rate limit likely reached")
    
    def get_company_info(self, symbol: str) -> Optional[Dict]:
        """Get company information from Yahoo Finance"""
        if self.daily_limit_reached:
            logger.warning(f"Daily limit reached, skipping company info for {symbol}")
            return None
        
        try:
            self._respect_rate_limit()
            
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info or 'regularMarketPrice' not in info:
                logger.warning(f"No valid info returned for {symbol}")
                return None
            
            company_data = {
                'symbol': symbol,
                'name': info.get('longName', info.get('shortName', symbol)),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0),
                'employees': info.get('fullTimeEmployees', 0),
                'description': info.get('longBusinessSummary', ''),
                'website': info.get('website', '')
            }
            
            return company_data
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error getting company info for {symbol}: {error_msg}")
            self._handle_rate_limit_error(error_msg)
            return None
    
    def get_fundamental_data(self, symbol: str) -> Optional[Dict]:
        """Get fundamental data from Yahoo Finance"""
        if self.daily_limit_reached:
            logger.warning(f"Daily limit reached, skipping fundamentals for {symbol}")
            return None
        
        try:
            self._respect_rate_limit()
            
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info:
                return None
            
            fundamental_data = {
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'peg_ratio': info.get('pegRatio'),
                'price_to_book': info.get('priceToBook'),
                'debt_to_equity': info.get('debtToEquity'),
                'roe': info.get('returnOnEquity'),
                'profit_margin': info.get('profitMargins'),
                'revenue_growth': info.get('revenueGrowth'),
                'earnings_growth': info.get('earningsGrowth'),
                'dividend_yield': info.get('dividendYield'),
                'payout_ratio': info.get('payoutRatio'),
                'beta': info.get('beta'),
                'current_ratio': info.get('currentRatio'),
                'quick_ratio': info.get('quickRatio')
            }
            
            return fundamental_data
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error getting fundamentals for {symbol}: {error_msg}")
            self._handle_rate_limit_error(error_msg)
            return None
    
    def get_price_data(self, symbol: str, start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        """Get historical price data from Yahoo Finance"""
        if self.daily_limit_reached:
            logger.warning(f"Daily limit reached, skipping price data for {symbol}")
            return None
        
        try:
            self._respect_rate_limit()
            
            ticker = yf.Ticker(symbol)
            
            # Determine date range
            if start_date is None:
                # Default to 5 years or company inception
                start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
            
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            # Get historical data
            data = ticker.history(start=start_date, end=end_date)
            
            if data.empty:
                logger.warning(f"No price data returned for {symbol}")
                return None
            
            # Clean and prepare data
            data = data.reset_index()
            data.columns = [col.lower().replace(' ', '_') for col in data.columns]
            
            # Rename columns to match database schema
            column_mapping = {
                'date': 'date',
                'open': 'open',
                'high': 'high', 
                'low': 'low',
                'close': 'close',
                'adj_close': 'adj_close',
                'volume': 'volume'
            }
            
            # Handle different possible column names
            for old_col in list(data.columns):
                for expected, new_name in column_mapping.items():
                    if expected in old_col or old_col.endswith(expected):
                        column_mapping[old_col] = new_name
                        break
            
            data = data.rename(columns=column_mapping)
            
            # Ensure we have required columns
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in data.columns]
            
            if missing_cols:
                logger.error(f"Missing required columns for {symbol}: {missing_cols}")
                return None
            
            # Add adj_close if missing
            if 'adj_close' not in data.columns:
                data['adj_close'] = data['close']
            
            # Convert date column
            data['date'] = pd.to_datetime(data['date']).dt.date
            
            # Select only required columns
            final_cols = ['date', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
            data = data[final_cols]
            
            return data
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error getting price data for {symbol}: {error_msg}")
            self._handle_rate_limit_error(error_msg)
            return None
    
    def update_company_data(self, symbol: str) -> bool:
        """Update company info, fundamental data, and price data for a symbol"""
        success = True
        
        # Update company info
        company_info = self.get_company_info(symbol)
        if company_info:
            if not self.db.add_company(company_info):
                success = False
        else:
            success = False
        
        # Update fundamental data
        fundamental_data = self.get_fundamental_data(symbol)
        if fundamental_data:
            if not self.db.add_fundamental_data(symbol, fundamental_data):
                success = False
        else:
            success = False
        
        # Update price data
        if not self.update_price_data(symbol):
            success = False
        
        return success
    
    def update_price_data(self, symbol: str, force_full_update: bool = False) -> bool:
        """Update price data for a symbol (only fetch new data)"""
        try:
            if force_full_update:
                # Get all available data
                start_date = None
                logger.info(f"Performing full price data update for {symbol}")
            else:
                # Get only new data since last update
                latest_date = self.db.get_latest_price_date(symbol)
                if latest_date:
                    # Start from day after latest date
                    start_date = (datetime.strptime(latest_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                    
                    # Check if we need to update (don't fetch today's data repeatedly)
                    if start_date >= datetime.now().strftime('%Y-%m-%d'):
                        logger.info(f"Price data for {symbol} is up to date")
                        return True
                else:
                    # No existing data, get last 2 years
                    start_date = (datetime.now() - timedelta(days=2*365)).strftime('%Y-%m-%d')
            
            # Fetch price data
            price_data = self.get_price_data(symbol, start_date)
            
            if price_data is not None and not price_data.empty:
                records_added = self.db.add_price_data(symbol, price_data)
                logger.info(f"Added {records_added} price records for {symbol}")
                return records_added > 0
            else:
                logger.warning(f"No new price data for {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating price data for {symbol}: {e}")
            return False
    
    def initialize_tsx_companies(self) -> int:
        """Initialize database with TSX composite companies"""
        logger.info("Initializing TSX composite companies...")
        successful_updates = 0
        
        for i, symbol in enumerate(self.TSX_SYMBOLS):
            if self.daily_limit_reached:
                logger.warning("Daily limit reached, stopping initialization")
                break
            
            logger.info(f"Initializing {symbol} ({i+1}/{len(self.TSX_SYMBOLS)})")
            
            # Check if company already exists
            existing_company = self.db.get_company(symbol)
            if existing_company:
                logger.info(f"Company {symbol} already exists, skipping")
                successful_updates += 1
                continue
            
            # Add company data
            if self.update_company_data(symbol):
                successful_updates += 1
                logger.info(f"Successfully initialized {symbol}")
            else:
                logger.error(f"Failed to initialize {symbol}")
            
            # Small delay between companies
            time.sleep(0.5)
        
        logger.info(f"Initialized {successful_updates}/{len(self.TSX_SYMBOLS)} companies")
        return successful_updates
    
    def update_all_price_data(self, max_companies: int = None) -> Dict[str, int]:
        """Update price data for all companies"""
        companies = self.db.get_all_companies()
        if max_companies:
            companies = companies[:max_companies]
        
        results = {
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
        
        logger.info(f"Updating price data for {len(companies)} companies")
        
        for i, company in enumerate(companies):
            if self.daily_limit_reached:
                logger.warning("Daily limit reached, stopping price updates")
                results['skipped'] = len(companies) - i
                break
            
            symbol = company['symbol']
            logger.info(f"Updating price data for {symbol} ({i+1}/{len(companies)})")
            
            if self.update_price_data(symbol):
                results['successful'] += 1
            else:
                results['failed'] += 1
            
            # Progress logging
            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {i+1}/{len(companies)} companies processed")
        
        logger.info(f"Price update complete. Success: {results['successful']}, "
                   f"Failed: {results['failed']}, Skipped: {results['skipped']}")
        
        return results
    
    def update_single_company(self, symbol: str, include_price_data: bool = True) -> bool:
        """Update all data for a single company"""
        logger.info(f"Updating all data for {symbol}")
        
        success = True
        
        # Update company and fundamental data
        if not self.update_company_data(symbol):
            success = False
        
        # Update price data if requested
        if include_price_data:
            if not self.update_price_data(symbol):
                success = False
        
        return success
    
    def get_update_queue(self, max_companies: int = 10) -> List[str]:
        """Get list of companies that need updates (oldest first)"""
        try:
            companies = self.db.get_all_companies()
            
            # Sort by last update date (oldest first)
            update_queue = []
            for company in companies:
                symbol = company['symbol']
                
                # Check when we last updated price data
                latest_price_date = self.db.get_latest_price_date(symbol)
                
                if latest_price_date is None:
                    # Never updated, high priority
                    priority = 0
                else:
                    # Days since last update
                    last_update = datetime.strptime(latest_price_date, '%Y-%m-%d')
                    days_old = (datetime.now() - last_update).days
                    priority = days_old
                
                update_queue.append((symbol, priority))
            
            # Sort by priority (highest first) and return symbols
            update_queue.sort(key=lambda x: x[1], reverse=True)
            return [symbol for symbol, _ in update_queue[:max_companies]]
            
        except Exception as e:
            logger.error(f"Error getting update queue: {e}")
            return []
    
    def reset_rate_limits(self):
        """Reset rate limiting (call this daily or when limits reset)"""
        self.daily_limit_reached = False
        self.rate_limit_delay = 1
        self.db.set_system_setting('daily_limit_reached', 'false')
        self.db.set_system_setting('rate_limit_delay', '1')
        logger.info("Rate limits reset")
    
    def get_ingestion_status(self) -> Dict:
        """Get current status of data ingestion"""
        return {
            'daily_limit_reached': self.daily_limit_reached,
            'current_rate_limit_delay': self.rate_limit_delay,
            'total_companies': len(self.TSX_SYMBOLS),
            'companies_in_db': len(self.db.get_all_companies()),
            'last_limit_reset': self.db.get_system_setting('last_limit_reset'),
            'database_stats': self.db.get_database_stats()
        }