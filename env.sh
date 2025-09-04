# Environment configuration for TSX Stock Analyzer
# Copy this file to .env and modify as needed

# Flask Environment (development, production, testing)
FLASK_ENV=development

# Flask Configuration
SECRET_KEY="STOCKMARKET"
HOST=localhost
PORT=5000
FLASK_DEBUG=False

# Database Configuration
DATABASE_PATH=tsx_analyzer_dev.db

# Yahoo Finance API Configuration
RATE_LIMIT_DELAY=1.0
MAX_RETRIES=3
REQUEST_TIMEOUT=30

# Analysis Configuration
ANALYSIS_PERIOD=252
MIN_DATA_POINTS=20

# Auto-update Configuration
UPDATE_INTERVAL=10
MAX_COMPANIES_PER_HOUR=360

# Data Retention
DATA_RETENTION_DAYS=365
LOG_RETENTION_DAYS=30

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=tsx_analyzer.log

# Production-specific settings (uncomment for production)
# FLASK_ENV=production
# SECRET_KEY=your-very-secure-secret-key-here
# RATE_LIMIT_DELAY=2.0
# LOG_LEVEL=WARNING
