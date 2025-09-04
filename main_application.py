"""
Main TSX Stock Analyzer Application
Orchestrates the entire system with web API and background processing
"""

import logging
import threading
import time
import schedule
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
import json
import os

# Import our modular components
from database_manager import DatabaseManager
from data_ingestion_manager import DataIngestionManager
from stock_analyzer import StockAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tsx_analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TSXAnalyzerApp:
    """Main application class that orchestrates all components"""
    
    def __init__(self, db_path: str = "tsx_analyzer.db", config=None):
        self.db = DatabaseManager(db_path)
        self.ingestion_manager = DataIngestionManager(self.db, config)
        self.analyzer = StockAnalyzer(self.db)
        
        # Application state
        self.auto_update_enabled = False
        self.update_thread = None
        self.stop_event = threading.Event()
        self.last_update_time = datetime.now()
        self.current_company_index = 0
        self.progress = {'active': False}
        
        # Initialize Flask app
        self.app = Flask(__name__)
        CORS(self.app)
        self.setup_routes()
        
        # Schedule daily maintenance
        schedule.every().day.at("02:00").do(self.daily_maintenance)
        
        logger.info("TSX Analyzer Application initialized")
    
    def setup_routes(self):
        """Setup Flask API routes"""
        
        @self.app.route('/')
        def index():
            """Serve the main web interface"""
            try:
                # Serve the new app interface
                with open('frontend/public/app.html', 'r', encoding='utf-8') as f:
                    return f.read()
            except FileNotFoundError:
                return '''
                <!DOCTYPE html>
                <html>
                <head><title>TSX Analyzer - Interface Not Found</title></head>
                <body>
                    <h1>TSX Analyzer Backend Running</h1>
                    <p>Main interface not found. Please ensure frontend/public/app.html exists.</p>
                    <p>API endpoints available at <a href="/api/">/api/</a></p>
                </body>
                </html>
                '''
        
        @self.app.route('/api/stocks')
        def get_stocks():
            """Get all stocks with latest analysis"""
            try:
                # Get all configured symbols plus any companies in the database
                all_symbols = set(self.ingestion_manager.TSX_SYMBOLS)
                companies = self.db.get_all_companies()
                
                # Add any database companies not in config (shouldn't happen but just in case)
                for company in companies:
                    all_symbols.add(company['symbol'])
                
                stocks = []
                
                # Process each symbol
                for symbol in sorted(all_symbols):
                    # Get company info from database if available
                    company = next((c for c in companies if c['symbol'] == symbol), {'symbol': symbol})
                    
                    # Try to get analysis first
                    analysis = self.db.get_latest_analysis(symbol)
                    
                    if analysis:
                        # Full analysis available - format price data
                        latest_price_data = self.db.get_price_data(symbol, days=2)
                        price = None
                        change = None
                        change_percent = None
                        volume = None
                        market_cap = None
                        
                        if latest_price_data is not None and not latest_price_data.empty:
                            latest = latest_price_data.iloc[-1]
                            price = latest['close']
                            if len(latest_price_data) > 1:
                                prev = latest_price_data.iloc[-2]['close']
                                change = price - prev
                                change_percent = (change / prev) * 100 if prev > 0 else 0
                            volume = latest.get('volume')
                        
                        # Get company info for market cap
                        if company:
                            market_cap = company.get('market_cap')
                        
                        stocks.append({
                            'symbol': symbol,
                            'company_name': company.get('name', company.get('long_name', symbol)),
                            'price': float(price) if price is not None else None,
                            'change': float(change) if change is not None else None,
                            'change_percent': float(change_percent) if change_percent is not None else None,
                            'volume': int(volume) if volume is not None else None,
                            'market_cap': float(market_cap) if market_cap is not None else None,
                            'score': int(analysis.get('total_score')) if analysis.get('total_score') is not None else None,
                            'recommendation': analysis.get('recommendation'),
                            'target_price': float(analysis.get('target_price')) if analysis.get('target_price') is not None else None,
                            'analysis_date': analysis.get('analysis_date')
                        })
                    else:
                        # Check if we have basic price data
                        latest_price_data = self.db.get_price_data(symbol, days=2)
                        price = None
                        change = None
                        change_percent = None
                        volume = None
                        
                        if latest_price_data is not None and not latest_price_data.empty:
                            latest = latest_price_data.iloc[-1]
                            price = latest['close']
                            if len(latest_price_data) > 1:
                                prev = latest_price_data.iloc[-2]['close']
                                change = price - prev
                                change_percent = (change / prev) * 100 if prev > 0 else 0
                            volume = latest.get('volume')
                        
                        stocks.append({
                            'symbol': symbol,
                            'company_name': company.get('name', company.get('long_name', symbol)),
                            'price': float(price) if price is not None else None,
                            'change': float(change) if change is not None else None,
                            'change_percent': float(change_percent) if change_percent is not None else None,
                            'volume': int(volume) if volume is not None else None,
                            'market_cap': float(company.get('market_cap')) if company.get('market_cap') else None,
                            'score': None,
                            'recommendation': None,
                            'target_price': None,
                            'analysis_date': None
                        })
                
                return jsonify({
                    'stocks': stocks,
                    'total': len(stocks),
                    'configured_symbols': len(self.ingestion_manager.TSX_SYMBOLS)
                })
                        
            except Exception as e:
                logger.error(f"Error getting stocks: {e}")
                return jsonify({'error': str(e)}), 500
        
        # New API endpoints for the modern web interface
        @self.app.route('/api/stocks/<symbol>/update', methods=['POST'])
        def update_stock(symbol):
            """Update a specific stock's data"""
            try:
                success = self.ingestion_manager.update_company_data(symbol)
                if success:
                    return jsonify({'success': True, 'message': f'{symbol} updated successfully'})
                else:
                    return jsonify({'success': False, 'message': f'Failed to update {symbol}'}), 400
            except Exception as e:
                logger.error(f"Error updating stock {symbol}: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/stocks/update-all', methods=['POST'])
        def update_all_stocks():
            """Start batch update of all stocks"""
            try:
                # Set progress tracking
                self.progress = {
                    'active': True,
                    'operation': 'update',
                    'total': len(self.ingestion_manager.TSX_SYMBOLS),
                    'completed': 0,
                    'status': 'Starting batch update'
                }
                
                # Start update in background thread
                def batch_update():
                    for i, symbol in enumerate(self.ingestion_manager.TSX_SYMBOLS):
                        try:
                            self.progress['completed'] = i
                            self.progress['status'] = f'Updating {symbol}'
                            self.ingestion_manager.update_company_data(symbol)
                        except Exception as e:
                            logger.error(f"Error updating {symbol}: {e}")
                    
                    self.progress['active'] = False
                    self.progress['status'] = 'Batch update complete'
                
                threading.Thread(target=batch_update, daemon=True).start()
                return jsonify({'success': True, 'message': 'Batch update started'})
                
            except Exception as e:
                logger.error(f"Error starting batch update: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/stocks/analyze-all', methods=['POST'])
        def analyze_all_stocks():
            """Start batch analysis of all stocks"""
            try:
                # Get companies that have data
                companies = self.db.get_all_companies()
                
                # Set progress tracking
                self.progress = {
                    'active': True,
                    'operation': 'analyze',
                    'total': len(companies),
                    'completed': 0,
                    'status': 'Starting batch analysis'
                }
                
                # Start analysis in background thread
                def batch_analyze():
                    for i, company in enumerate(companies):
                        try:
                            symbol = company['symbol']
                            self.progress['completed'] = i
                            self.progress['status'] = f'Analyzing {symbol}'
                            self.analyzer.analyze_stock(symbol)
                        except Exception as e:
                            logger.error(f"Error analyzing {symbol}: {e}")
                    
                    self.progress['active'] = False
                    self.progress['status'] = 'Batch analysis complete'
                
                threading.Thread(target=batch_analyze, daemon=True).start()
                return jsonify({'success': True, 'message': 'Batch analysis started'})
                
            except Exception as e:
                logger.error(f"Error starting batch analysis: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/progress')
        def get_progress():
            """Get current batch operation progress"""
            return jsonify(getattr(self, 'progress', {
                'active': False,
                'operation': None,
                'total': 0,
                'completed': 0,
                'status': 'No operation in progress'
            }))
        
        @self.app.route('/api/symbols')
        def get_symbols():
            """Get all configured symbols"""
            try:
                return jsonify({
                    'symbols': self.ingestion_manager.TSX_SYMBOLS,
                    'total': len(self.ingestion_manager.TSX_SYMBOLS)
                })
            except Exception as e:
                logger.error(f"Error getting symbols: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/symbols', methods=['POST'])
        def add_symbol():
            """Add a new symbol to the configuration"""
            try:
                data = request.get_json()
                symbol = data.get('symbol', '').upper().strip()
                
                if not symbol:
                    return jsonify({'success': False, 'error': 'Symbol is required'}), 400
                
                if symbol in self.ingestion_manager.TSX_SYMBOLS:
                    return jsonify({'success': False, 'error': 'Symbol already exists'}), 400
                
                # Add to the in-memory list
                self.ingestion_manager.TSX_SYMBOLS.append(symbol)
                
                # Update config.py file
                self._update_config_symbols()
                
                return jsonify({'success': True, 'message': f'{symbol} added successfully'})
                
            except Exception as e:
                logger.error(f"Error adding symbol: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/symbols/<symbol>', methods=['DELETE'])
        def remove_symbol(symbol):
            """Remove a symbol from the configuration"""
            try:
                symbol = symbol.upper()
                
                if symbol not in self.ingestion_manager.TSX_SYMBOLS:
                    return jsonify({'success': False, 'error': 'Symbol not found'}), 404
                
                # Remove from the in-memory list
                self.ingestion_manager.TSX_SYMBOLS.remove(symbol)
                
                # Update config.py file
                self._update_config_symbols()
                
                return jsonify({'success': True, 'message': f'{symbol} removed successfully'})
                
            except Exception as e:
                logger.error(f"Error removing symbol: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/settings')
        def get_settings():
            """Get current configuration settings"""
            try:
                # Read settings directly from config.py file
                with open('config.py', 'r') as f:
                    content = f.read()
                
                settings = {}
                
                # Extract values from the config file
                import re
                patterns = {
                    'DATABASE_PATH': r'DATABASE_PATH\s*=\s*["\']([^"\']*)["\']',
                    'HOST': r'HOST\s*=\s*["\']([^"\']*)["\']', 
                    'PORT': r'PORT\s*=\s*(\d+)',
                    'RATE_LIMIT_DELAY': r'RATE_LIMIT_DELAY\s*=\s*([0-9.]+)',
                    'MAX_RETRIES': r'MAX_RETRIES\s*=\s*(\d+)',
                    'REQUEST_TIMEOUT': r'REQUEST_TIMEOUT\s*=\s*(\d+)',
                    'DEFAULT_ANALYSIS_PERIOD': r'DEFAULT_ANALYSIS_PERIOD\s*=.*?(\d+)',
                    'MIN_DATA_POINTS': r'MIN_DATA_POINTS\s*=\s*(\d+)',
                    'AUTO_UPDATE_INTERVAL': r'AUTO_UPDATE_INTERVAL\s*=.*?(\d+)',
                    'MAX_COMPANIES_PER_HOUR': r'MAX_COMPANIES_PER_HOUR\s*=.*?(\d+)',
                    'LOG_LEVEL': r'LOG_LEVEL\s*=\s*["\']([^"\']*)["\']'
                }
                
                for key, pattern in patterns.items():
                    match = re.search(pattern, content)
                    if match:
                        value = match.group(1)
                        # Convert numeric values
                        if key in ['PORT', 'MAX_RETRIES', 'REQUEST_TIMEOUT', 'DEFAULT_ANALYSIS_PERIOD', 
                                  'MIN_DATA_POINTS', 'AUTO_UPDATE_INTERVAL', 'MAX_COMPANIES_PER_HOUR']:
                            value = int(value)
                        elif key in ['RATE_LIMIT_DELAY']:
                            value = float(value)
                        settings[key] = value
                
                return jsonify(settings)
                
            except Exception as e:
                logger.error(f"Error getting settings: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/settings', methods=['POST'])
        def update_settings():
            """Update configuration settings"""
            try:
                data = request.get_json()
                
                # Update config.py file
                self._update_config_file(data)
                
                return jsonify({'success': True, 'message': 'Settings updated successfully'})
                
            except Exception as e:
                logger.error(f"Error updating settings: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
    
    def _update_config_symbols(self):
        """Update the TSX_SYMBOLS list in config.py"""
        try:
            with open('config.py', 'r') as f:
                content = f.read()
            
            # Create the new symbols list
            symbols_str = ',\n        '.join([f"'{symbol}'" for symbol in sorted(self.ingestion_manager.TSX_SYMBOLS)])
            new_symbols_section = f'    TSX_SYMBOLS = [\n        {symbols_str}\n    ]'
            
            # Replace the existing TSX_SYMBOLS section
            pattern = r'TSX_SYMBOLS = \[[^\]]*\]'
            new_content = re.sub(pattern, new_symbols_section.strip(), content, flags=re.DOTALL)
            
            with open('config.py', 'w') as f:
                f.write(new_content)
                
            logger.info("Updated TSX_SYMBOLS in config.py")
            
        except Exception as e:
            logger.error(f"Error updating config.py symbols: {e}")
            raise
    
    def _update_config_file(self, settings):
        """Update configuration values in config.py"""
        try:
            with open('config.py', 'r') as f:
                content = f.read()
            
            # Update each setting with more precise patterns
            for key, value in settings.items():
                if isinstance(value, str):
                    # For string values, look for the exact pattern
                    pattern = f'({key}\\s*=\\s*)["\'][^"\']*["\']'
                    replacement = f'\\1"{value}"'
                else:
                    # For numeric values, look for the exact pattern  
                    pattern = f'({key}\\s*=\\s*)[0-9.]+'
                    replacement = f'\\1{value}'
                
                content = re.sub(pattern, replacement, content)
            
            with open('config.py', 'w') as f:
                f.write(content)
                
            logger.info(f"Updated config.py settings: {list(settings.keys())}")
            
        except Exception as e:
            logger.error(f"Error updating config.py: {e}")
            raise
    
    def daily_maintenance(self):
        """Daily maintenance tasks"""
        logger.info("Running daily maintenance")
        
        try:
            # Reset rate limits
            self.ingestion_manager.reset_rate_limits()
            
            # Clean up old log files (keep last 30 days)
            # TODO: Implement log cleanup
            
            # Database maintenance
            stats = self.db.get_database_stats()
            logger.info(f"Database stats: {stats}")
            
        except Exception as e:
            logger.error(f"Error during daily maintenance: {e}")
    
    def initialize_system(self):
        """Initialize the system with basic data"""
        logger.info("Initializing TSX Analyzer system...")
        
        try:
            # Check if we already have companies
            companies = self.db.get_all_companies()
            
            if len(companies) < 10:  # Initialize if we have fewer than 10 companies
                logger.info("Initializing with TSX companies...")
                self.ingestion_manager.initialize_tsx_companies()
            else:
                logger.info(f"Database already contains {len(companies)} companies")
            
            # Try to analyze a few companies to ensure everything works
            test_symbols = ['SHOP.TO', 'RY.TO', 'TD.TO']
            for symbol in test_symbols:
                if any(c['symbol'] == symbol for c in companies):
                    logger.info(f"Testing analysis for {symbol}")
                    analysis = self.analyzer.analyze_stock(symbol)
                    if analysis:
                        logger.info(f"Test analysis successful for {symbol}")
                        break
            
            logger.info("System initialization complete")
            
        except Exception as e:
            logger.error(f"Error during system initialization: {e}")
    
    def run(self, host='localhost', port=5000, debug=False):
        """Run the Flask application"""
        try:
            logger.info(f"Starting TSX Analyzer web server on http://{host}:{port}")
            self.app.run(host=host, port=port, debug=debug, threaded=True)
        except KeyboardInterrupt:
            logger.info("Shutting down application...")
        except Exception as e:
            logger.error(f"Error running application: {e}")
            raise

if __name__ == "__main__":
    try:
        app = TSXAnalyzerApp()
        app.run(host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise