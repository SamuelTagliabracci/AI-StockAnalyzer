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
                    currency TEXT,
                    exchange TEXT,
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
            
            # Agent verdicts — one row per (agent, symbol) recommendation. This is the
            # multi-agent ledger: the quant engine, Claude Code, and (later) Ollama models
            # each write their own reasoned call. price_at_call + horizon make every verdict
            # a scoreable prediction (foundation for R5 validation).
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS agent_verdicts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT,
                    confidence REAL,
                    target_price REAL,
                    price_at_call REAL,
                    horizon TEXT,
                    rationale TEXT,
                    model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (symbol) REFERENCES companies (symbol)
                )
            ''')

            # "Smart money" feed: real disclosed trades by insiders, institutions (13F),
            # politicians (STOCK Act), and copy-trade leaders — one row per disclosed trade.
            # source = insider | institution | congress | copytrade. action = BUY | SELL.
            # traded_at is when the trade happened; filed_at is when it became public.
            # (external_id, source) is unique so re-ingesting the same filing is idempotent.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    actor TEXT,
                    actor_role TEXT,
                    action TEXT,
                    shares REAL,
                    value_usd REAL,
                    price REAL,
                    traded_at TEXT,
                    filed_at TEXT,
                    url TEXT,
                    external_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (source, external_id),
                    FOREIGN KEY (symbol) REFERENCES companies (symbol)
                )
            ''')

            # --- Phase 3: paper/real trading -----------------------------------------
            # accounts: one per trader. type 'human' (Sam) or 'agent' (an AI). For agents,
            # agent_key matches the name in agent_verdicts (e.g. 'Qwen2.5 7B') so the loop
            # can find that agent's calls.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT,
                    type TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    agent_key TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (type, display_name)
                )
            ''')
            # cash_balances: per-account wallet, one row per currency (CAD/USD).
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cash_balances (
                    account_id INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    amount REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY (account_id, currency),
                    FOREIGN KEY (account_id) REFERENCES accounts (id)
                )
            ''')
            # holdings: current positions (one row per account+symbol; avg_cost in the
            # stock's own currency). Removed when shares hit 0.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    shares REAL NOT NULL,
                    avg_cost REAL NOT NULL,
                    currency TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (account_id, symbol),
                    FOREIGN KEY (account_id) REFERENCES accounts (id)
                )
            ''')
            # trades: append-only fill ledger. side BUY/SELL, kind paper/real.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    shares REAL NOT NULL,
                    price REAL NOT NULL,
                    currency TEXT,
                    kind TEXT NOT NULL DEFAULT 'paper',
                    rationale TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (account_id) REFERENCES accounts (id)
                )
            ''')

            # Migrations for pre-existing databases (seed DB predates multi-market):
            # add currency/exchange columns if absent, then backfill currency from the
            # symbol suffix so legacy TSX rows are tagged without a full re-ingest.
            existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(companies)")}
            if 'currency' not in existing_cols:
                cursor.execute("ALTER TABLE companies ADD COLUMN currency TEXT")
            if 'exchange' not in existing_cols:
                cursor.execute("ALTER TABLE companies ADD COLUMN exchange TEXT")
            cursor.execute("""
                UPDATE companies SET currency = 'CAD'
                WHERE currency IS NULL AND (
                    symbol LIKE '%.TO' OR symbol LIKE '%.V'
                    OR symbol LIKE '%.CN' OR symbol LIKE '%.NE'
                )
            """)
            cursor.execute("UPDATE companies SET currency = 'USD' WHERE currency IS NULL")

            # Create indexes for better performance
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_daily_prices_symbol_date ON daily_prices(symbol, date DESC)',
                'CREATE INDEX IF NOT EXISTS idx_analysis_results_symbol_date ON analysis_results(symbol, analysis_date DESC)',
                'CREATE INDEX IF NOT EXISTS idx_companies_sector ON companies(sector)',
                'CREATE INDEX IF NOT EXISTS idx_companies_active ON companies(is_active)',
                'CREATE INDEX IF NOT EXISTS idx_ingestion_log_symbol ON ingestion_log(symbol, timestamp DESC)',
                'CREATE INDEX IF NOT EXISTS idx_agent_verdicts_symbol ON agent_verdicts(symbol, agent, created_at DESC)',
                'CREATE INDEX IF NOT EXISTS idx_market_signals_symbol ON market_signals(symbol, filed_at DESC)',
                'CREATE INDEX IF NOT EXISTS idx_market_signals_filed ON market_signals(filed_at DESC)',
                'CREATE INDEX IF NOT EXISTS idx_holdings_account ON holdings(account_id)',
                'CREATE INDEX IF NOT EXISTS idx_trades_account ON trades(account_id, created_at DESC)'
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
                    (symbol, name, sector, industry, market_cap, employees, description, website, currency, exchange, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    company_data['symbol'],
                    company_data.get('name', ''),
                    company_data.get('sector', ''),
                    company_data.get('industry', ''),
                    company_data.get('market_cap', 0),
                    company_data.get('employees', 0),
                    company_data.get('description', ''),
                    company_data.get('website', ''),
                    company_data.get('currency'),
                    company_data.get('exchange'),
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
                    SELECT a.*, c.name, c.sector, c.currency, c.exchange
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

    # Agent verdict methods (multi-agent ledger)
    def add_agent_verdict(self, verdict: Dict) -> bool:
        """Insert one agent verdict (append-only history; latest wins on read)."""
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT INTO agent_verdicts
                    (agent, symbol, action, confidence, target_price, price_at_call,
                     horizon, rationale, model, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    verdict['agent'],
                    verdict['symbol'],
                    verdict.get('action'),
                    verdict.get('confidence'),
                    verdict.get('target_price'),
                    verdict.get('price_at_call'),
                    verdict.get('horizon'),
                    verdict.get('rationale'),
                    verdict.get('model'),
                    verdict.get('created_at') or datetime.now(),
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error adding verdict {verdict.get('agent')}/{verdict.get('symbol')}: {e}")
            return False

    def get_all_latest_agent_verdicts(self) -> Dict[str, List[Dict]]:
        """Latest verdict per (agent, symbol), grouped by symbol. One query for the whole list."""
        try:
            with self.get_connection() as conn:
                query = '''
                    SELECT v.* FROM agent_verdicts v
                    JOIN (
                        SELECT agent, symbol, MAX(created_at) AS mx
                        FROM agent_verdicts GROUP BY agent, symbol
                    ) latest
                    ON v.agent = latest.agent AND v.symbol = latest.symbol
                       AND v.created_at = latest.mx
                '''
                df = pd.read_sql(query, conn)
                grouped: Dict[str, List[Dict]] = {}
                for rec in df.to_dict('records'):
                    grouped.setdefault(rec['symbol'], []).append(rec)
                return grouped
        except Exception as e:
            logger.error(f"Error getting agent verdicts: {e}")
            return {}

    def add_market_signal(self, sig: Dict) -> bool:
        """Insert one smart-money signal; idempotent on (source, external_id).

        Returns True only when a NEW row was inserted (False on duplicate) so callers
        can report accurate counts across repeated ingests.
        """
        try:
            with self.get_connection() as conn:
                cur = conn.execute('''
                    INSERT OR IGNORE INTO market_signals
                    (source, symbol, actor, actor_role, action, shares, value_usd,
                     price, traded_at, filed_at, url, external_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    sig['source'], sig['symbol'], sig.get('actor'), sig.get('actor_role'),
                    sig.get('action'), sig.get('shares'), sig.get('value_usd'),
                    sig.get('price'), sig.get('traded_at'), sig.get('filed_at'),
                    sig.get('url'), sig.get('external_id'),
                ))
                conn.commit()
                return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error adding signal {sig.get('source')}/{sig.get('symbol')}: {e}")
            return False

    def get_market_signals(self, symbols: Optional[List[str]] = None,
                           source: Optional[str] = None, limit: int = 200) -> List[Dict]:
        """Recent smart-money signals, newest filing first. Optional symbol/source filters."""
        try:
            with self.get_connection() as conn:
                clauses, params = [], []
                if symbols:
                    clauses.append(f"symbol IN ({','.join('?' * len(symbols))})")
                    params.extend(symbols)
                if source:
                    clauses.append("source = ?")
                    params.append(source)
                where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
                params.append(limit)
                query = (f"SELECT * FROM market_signals{where} "
                         f"ORDER BY filed_at DESC, id DESC LIMIT ?")
                df = pd.read_sql(query, conn, params=params)
                return df.to_dict('records')
        except Exception as e:
            logger.error(f"Error getting market signals: {e}")
            return []

    # --- Phase 3: accounts / trading ------------------------------------------
    @staticmethod
    def _clean(records: List[Dict]) -> List[Dict]:
        """SQL NULLs come back from pandas as NaN floats — invalid JSON; coerce to None."""
        for r in records:
            for k, v in r.items():
                if isinstance(v, float) and pd.isna(v):
                    r[k] = None
        return records

    def get_or_create_account(self, type: str, display_name: str,
                              email: Optional[str] = None,
                              agent_key: Optional[str] = None) -> Optional[Dict]:
        """Idempotently get (or create) an account, keyed by (type, display_name)."""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO accounts (email, type, display_name, agent_key) "
                    "VALUES (?, ?, ?, ?)", (email, type, display_name, agent_key))
                conn.commit()
                df = pd.read_sql(
                    "SELECT * FROM accounts WHERE type=? AND display_name=?",
                    conn, params=[type, display_name])
                return self._clean(df.to_dict('records'))[0] if not df.empty else None
        except Exception as e:
            logger.error(f"Error get_or_create_account {display_name}: {e}")
            return None

    def list_accounts(self) -> List[Dict]:
        try:
            with self.get_connection() as conn:
                return self._clean(pd.read_sql("SELECT * FROM accounts ORDER BY type, id", conn).to_dict('records'))
        except Exception as e:
            logger.error(f"Error list_accounts: {e}")
            return []

    def get_account(self, account_id: int) -> Optional[Dict]:
        try:
            with self.get_connection() as conn:
                df = pd.read_sql("SELECT * FROM accounts WHERE id=?", conn, params=[account_id])
                return self._clean(df.to_dict('records'))[0] if not df.empty else None
        except Exception as e:
            logger.error(f"Error get_account {account_id}: {e}")
            return None

    def get_cash(self, account_id: int) -> Dict[str, float]:
        """Return {currency: amount} for an account's wallets."""
        try:
            with self.get_connection() as conn:
                df = pd.read_sql("SELECT currency, amount FROM cash_balances WHERE account_id=?",
                                 conn, params=[account_id])
                return {r['currency']: float(r['amount']) for r in df.to_dict('records')}
        except Exception as e:
            logger.error(f"Error get_cash {account_id}: {e}")
            return {}

    def set_cash(self, account_id: int, currency: str, amount: float) -> bool:
        """Set a wallet to an absolute amount (used by manual entry + seeding)."""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO cash_balances (account_id, currency, amount) VALUES (?, ?, ?) "
                    "ON CONFLICT(account_id, currency) DO UPDATE SET amount=excluded.amount",
                    (account_id, currency, float(amount)))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error set_cash {account_id}/{currency}: {e}")
            return False

    def adjust_cash(self, account_id: int, currency: str, delta: float) -> bool:
        """Add delta (can be negative) to a wallet, creating it at 0 first if needed."""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO cash_balances (account_id, currency, amount) VALUES (?, ?, 0)",
                    (account_id, currency))
                conn.execute(
                    "UPDATE cash_balances SET amount = amount + ? WHERE account_id=? AND currency=?",
                    (float(delta), account_id, currency))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error adjust_cash {account_id}/{currency}: {e}")
            return False

    def get_holdings(self, account_id: int) -> List[Dict]:
        try:
            with self.get_connection() as conn:
                return pd.read_sql(
                    "SELECT symbol, shares, avg_cost, currency FROM holdings "
                    "WHERE account_id=? ORDER BY symbol", conn, params=[account_id]).to_dict('records')
        except Exception as e:
            logger.error(f"Error get_holdings {account_id}: {e}")
            return []

    def get_holding(self, account_id: int, symbol: str) -> Optional[Dict]:
        try:
            with self.get_connection() as conn:
                df = pd.read_sql("SELECT * FROM holdings WHERE account_id=? AND symbol=?",
                                 conn, params=[account_id, symbol])
                return df.to_dict('records')[0] if not df.empty else None
        except Exception as e:
            logger.error(f"Error get_holding {account_id}/{symbol}: {e}")
            return None

    def upsert_holding(self, account_id: int, symbol: str, shares: float,
                       avg_cost: float, currency: Optional[str]) -> bool:
        """Set a position. shares<=0 removes it."""
        try:
            with self.get_connection() as conn:
                if shares <= 0:
                    conn.execute("DELETE FROM holdings WHERE account_id=? AND symbol=?",
                                 (account_id, symbol))
                else:
                    conn.execute(
                        "INSERT INTO holdings (account_id, symbol, shares, avg_cost, currency, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?) "
                        "ON CONFLICT(account_id, symbol) DO UPDATE SET "
                        "shares=excluded.shares, avg_cost=excluded.avg_cost, "
                        "currency=excluded.currency, updated_at=excluded.updated_at",
                        (account_id, symbol, float(shares), float(avg_cost), currency, datetime.now()))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error upsert_holding {account_id}/{symbol}: {e}")
            return False

    def add_trade(self, trade: Dict) -> bool:
        """Append a fill to the trade ledger."""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO trades (account_id, symbol, side, shares, price, currency, kind, rationale) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (trade['account_id'], trade['symbol'], trade['side'], float(trade['shares']),
                     float(trade['price']), trade.get('currency'), trade.get('kind', 'paper'),
                     trade.get('rationale')))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error add_trade {trade.get('account_id')}/{trade.get('symbol')}: {e}")
            return False

    def get_trades(self, account_id: int, limit: int = 200) -> List[Dict]:
        try:
            with self.get_connection() as conn:
                return pd.read_sql(
                    "SELECT * FROM trades WHERE account_id=? ORDER BY created_at DESC, id DESC LIMIT ?",
                    conn, params=[account_id, limit]).to_dict('records')
        except Exception as e:
            logger.error(f"Error get_trades {account_id}: {e}")
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