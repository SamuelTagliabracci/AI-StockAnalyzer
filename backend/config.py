"""
Configuration file for the multi-market Stock Analyzer
Centralized configuration management

The investable universe spans US large caps (NASDAQ/NYSE) and TSX (Toronto).
Exchange/currency are tagged per-symbol from yfinance at ingest time, not guessed
from suffixes — see DataIngestionManager.get_company_info.
"""

import os
from datetime import timedelta

class Config:
    """Base configuration"""
    
    # Database settings
    DATABASE_PATH = "tsx_analyzer_dev.db"
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # API settings
    HOST = "localhost"
    PORT = 5000
    
    # Yahoo Finance settings
    RATE_LIMIT_DELAY = 1
    MAX_RETRIES = 3
    REQUEST_TIMEOUT = 30
    
    # Analysis settings
    DEFAULT_ANALYSIS_PERIOD = int(os.environ.get('ANALYSIS_PERIOD', 252))  # trading days
    MIN_DATA_POINTS = 20
    
    # Auto-update settings
    AUTO_UPDATE_INTERVAL = int(os.environ.get('UPDATE_INTERVAL', 10))  # seconds
    MAX_COMPANIES_PER_HOUR = int(os.environ.get('MAX_COMPANIES_PER_HOUR', 360))
    
    # Data retention
    DATA_RETENTION_DAYS = int(os.environ.get('DATA_RETENTION_DAYS', 365))
    LOG_RETENTION_DAYS = int(os.environ.get('LOG_RETENTION_DAYS', 30))
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'tsx_analyzer.log')
    
    # US large caps — NASDAQ / NYSE. yfinance tickers (no suffix → USD).
    US_SYMBOLS = [
        # Mega-cap technology
        'AAPL',   # Apple
        'MSFT',   # Microsoft
        'NVDA',   # NVIDIA
        'GOOGL',  # Alphabet (Class A)
        'AMZN',   # Amazon
        'META',   # Meta Platforms
        'AVGO',   # Broadcom
        'ORCL',   # Oracle
        'ADBE',   # Adobe
        'CRM',    # Salesforce
        'AMD',    # Advanced Micro Devices
        'INTC',   # Intel
        'MU',     # Micron Technology
        'CSCO',   # Cisco
        'QCOM',   # Qualcomm
        'TXN',    # Texas Instruments

        # Consumer & retail
        'TSLA',   # Tesla
        'HD',     # Home Depot
        'NKE',    # Nike
        'MCD',    # McDonald's
        'SBUX',   # Starbucks
        'COST',   # Costco
        'WMT',    # Walmart
        'PG',     # Procter & Gamble
        'KO',     # Coca-Cola
        'PEP',    # PepsiCo
        'DIS',    # Walt Disney

        # Financials
        'JPM',    # JPMorgan Chase
        'BAC',    # Bank of America
        'V',      # Visa
        'MA',     # Mastercard
        'GS',     # Goldman Sachs
        'MS',     # Morgan Stanley
        'BRK-B',  # Berkshire Hathaway (Class B)

        # Healthcare
        'UNH',    # UnitedHealth
        'JNJ',    # Johnson & Johnson
        'LLY',    # Eli Lilly
        'PFE',    # Pfizer
        'ABBV',   # AbbVie
        'MRK',    # Merck

        # Energy & industrials
        'XOM',    # Exxon Mobil
        'CVX',    # Chevron
        'BA',     # Boeing
        'CAT',    # Caterpillar
        'GE',     # GE Aerospace

        # Communications
        'NFLX',   # Netflix
        'T',      # AT&T
        'VZ',     # Verizon
    ]

    # TSX Composite Index companies - Current valid symbols (2025)
    TSX_SYMBOLS = [
        # Financials - Big Banks & Insurance
        'RY.TO',    # Royal Bank of Canada
        'TD.TO',    # Toronto-Dominion Bank  
        'BNS.TO',   # Bank of Nova Scotia
        'BMO.TO',   # Bank of Montreal
        'CM.TO',    # Canadian Imperial Bank of Commerce
        'NA.TO',    # National Bank of Canada
        'MFC.TO',   # Manulife Financial
        'SLF.TO',   # Sun Life Financial
        'GWO.TO',   # Great-West Lifeco
        'IFC.TO',   # Intact Financial
        'FFH.TO',   # Fairfax Financial Holdings
        
        # Technology
        'SHOP.TO',  # Shopify Inc.
        'CSU.TO',   # Constellation Software
        'TRI.TO',   # Thomson Reuters
        'OTEX.TO',  # Open Text Corporation
        'LSPD.TO',  # Lightspeed Commerce
        
        # Energy
        'CNQ.TO',   # Canadian Natural Resources
        'SU.TO',    # Suncor Energy
        'IMO.TO',   # Imperial Oil
        'CVE.TO',   # Cenovus Energy
        'TRP.TO',   # TC Energy Corporation
        'ARX.TO',   # ARC Resources
        'TOU.TO',   # Tourmaline Oil
        'MEG.TO',   # MEG Energy
        'WCP.TO',   # Whitecap Resources
        
        # Infrastructure & Transportation  
        'ENB.TO',   # Enbridge Inc.
        'CNR.TO',   # Canadian National Railway
        'CP.TO',    # Canadian Pacific Kansas City
        'WCN.TO',   # Waste Connections
        'PPL.TO',   # Pembina Pipeline
        
        # Mining & Materials
        'ABX.TO',   # Barrick Gold
        'AEM.TO',   # Agnico Eagle Mines
        'WPM.TO',   # Wheaton Precious Metals
        'FM.TO',    # First Quantum Minerals
        'K.TO',     # Kinross Gold
        'FNV.TO',   # Franco-Nevada
        'NTR.TO',   # Nutrien
        'CCO.TO',   # Cameco Corporation
        
        # Real Estate & Asset Management
        'BAM.TO',   # Brookfield Asset Management
        'BN.TO',    # Brookfield Corporation
        
        # Consumer & Retail
        'L.TO',     # Loblaw Companies
        'ATD.TO',   # Alimentation Couche-Tard
        'DOL.TO',   # Dollarama Inc.
        'CTC.TO',   # Canadian Tire
        'GOOS.TO',  # Canada Goose Holdings
        
        # Telecommunications
        'BCE.TO',   # BCE Inc.
        'T.TO',     # TELUS Corporation
        'RCI-B.TO', # Rogers Communications
        'QBR-B.TO', # Quebecor Inc.
        
        # Utilities
        'FTS.TO',   # Fortis Inc.
        'EMA.TO',   # Emera Incorporated
        'AQN.TO',   # Algonquin Power & Utilities
        'H.TO',     # Hydro One Limited
        'CU.TO',    # Canadian Utilities
        
        # Industrials
        'WSP.TO',   # WSP Global Inc.
        'STN.TO',   # Stantec Inc.
        'BYD.TO',   # Boyd Group Services
        'TIH.TO',   # Toromont Industries
        'CAE.TO',   # CAE Inc.
        'MGA.TO',   # Magna International
        
        # Healthcare
        'WELL.TO',  # WELL Health Technologies
        
        # Additional Large Caps
        'AC.TO',    # Air Canada
        'DOO.TO',   # BRP Inc.
        'NFI.TO',   # NFI Group Inc.
        'KEY.TO',   # Keyera Corp.

        # ETFs / split-share funds (note: thin/absent fundamentals — beta etc. may be null)
        'DFN.TO',   # Dividend 15 Split Corp.
        'HCAL.TO',  # Hamilton Enhanced Canadian Bank ETF
    ]

    # The full investable universe ingestion + analysis run against.
    # US first (larger, more liquid), then TSX. Note 'T' (AT&T, US) is distinct
    # from 'T.TO' (TELUS, TSX) — the suffix keeps them unambiguous.
    UNIVERSE = US_SYMBOLS + TSX_SYMBOLS

    # Scoring weights (must sum to 100)
    FUNDAMENTAL_WEIGHT = 40
    TECHNICAL_WEIGHT = 30
    MOMENTUM_WEIGHT = 30
    
    # Risk scoring parameters
    VOLATILITY_THRESHOLDS = {
        'low': 0.25,
        'medium': 0.45,
        'high': 0.65
    }
    
    BETA_THRESHOLDS = {
        'low': 0.8,
        'medium': 1.2,
        'high': 1.5
    }
    
    # Recommendation thresholds
    RECOMMENDATION_THRESHOLDS = {
        'STRONG_BUY': 80,
        'BUY': 70,
        'MODERATE_BUY': 60,
        'HOLD': 50,
        'WEAK_HOLD': 40,
        'CONSIDER_SELLING': 30,
        'SELL': 0
    }


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    DATABASE_PATH = "tsx_analyzer_dev.db"
    RATE_LIMIT_DELAY = 1
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    RATE_LIMIT_DELAY = 1
    SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-key-change-immediately')
    
    def validate(self):
        """Validate production configuration"""
        if self.SECRET_KEY == 'fallback-key-change-immediately' or not self.SECRET_KEY:
            raise ValueError("SECRET_KEY environment variable must be set in production")


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_PATH = "tsx_analyzer_dev.db"
    RATE_LIMIT_DELAY = 1
    LOG_LEVEL = 'WARNING'


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
