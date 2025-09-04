# TSX Stock Analyzer

A comprehensive stock analysis tool specifically designed for Toronto Stock Exchange (TSX) companies. This application provides real-time data ingestion, technical analysis, and a web-based interface for monitoring TSX stock performance.

## Features

- **Real-time Data Ingestion**: Automated fetching of stock data from Yahoo Finance for TSX companies
- **Technical Analysis**: Built-in stock analysis with technical indicators and performance metrics
- **Web Interface**: Flask-based API with web interface for easy interaction
- **Background Processing**: Automated data updates and maintenance tasks
- **SQLite Database**: Local storage for historical data and analysis results
- **Rate-limited API Calls**: Respectful data fetching with configurable rate limits
- **Comprehensive Logging**: Detailed logging for monitoring and debugging

## Prerequisites

- Python 3.8 or higher
- pip package manager

## Installation

1. Clone or download the project:
```bash
git clone https://github.com/SamuelTagliabracci/AI-StockAnalyzer.git
cd AI-StockAnalyzer
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

1. **Start the application** (recommended):
```bash
./start.sh
```
This will start both the Flask API server and HTTP server for the web interface.

2. **Access the application**:
- Web Interface: http://localhost:8080/frontend/public/
- Flask API: http://localhost:5000
- API Endpoints: http://localhost:5000/api

## Usage Options

### Primary Method: Using start.sh

The recommended way to run the application is with the start script:

```bash
./start.sh
```

This script will:
- Activate the virtual environment
- Start the Flask API on port 5000
- Start the HTTP server on port 8080 for the web interface
- Set up proper cleanup on exit

### Alternative: Direct Python Execution

For advanced users or development, you can run the Flask app directly:

```bash
python run.py [OPTIONS]
```

**Available Options:**
- `--host HOST`: Host to bind the server to (default: localhost)
- `--port PORT`: Port to bind the server to (default: 5000)
- `--debug`: Enable debug mode
- `--initialize`: Initialize database with TSX companies on startup
- `--auto-update`: Enable auto-update on startup
- `--config-check`: Check configuration and exit
- `--version`: Show version information

### Examples

```bash
# Check configuration
python run.py --config-check

# Debug mode with initialization
python run.py --debug --initialize

# Bind to all interfaces on port 8080
python run.py --host 0.0.0.0 --port 8080
```

## API Endpoints

### Stock Data
- `GET /api/stocks` - Get all stocks with latest analysis
- `GET /api/stock/<symbol>` - Get detailed analysis for a specific stock
- `GET /api/stock/<symbol>/chart` - Get chart data for a stock

### System Management
- `GET /api/status` - Get system status
- `POST /api/initialize` - Initialize the database
- `POST /api/auto-update/start` - Start auto-update
- `POST /api/auto-update/stop` - Stop auto-update
- `GET /api/progress` - Get update progress

### Data Management
- `POST /api/update/<symbol>` - Update specific stock data
- `POST /api/update/all` - Update all stock data
- `POST /api/analyze/<symbol>` - Run analysis for specific stock

## Configuration

The application uses a configuration system with environment variable support. Key settings include:

- **Database**: SQLite database path (default: `tsx_analyzer_dev.db`)
- **API Limits**: Rate limiting and retry settings
- **Analysis**: Technical analysis parameters
- **Auto-update**: Update intervals and batch sizes

Environment variables can be set for production deployment:
```bash
export FLASK_DEBUG=false
export DATABASE_PATH=tsx_analyzer_prod.db
export ANALYSIS_PERIOD=252
export MAX_COMPANIES_PER_HOUR=360
```

## Project Structure

```
├── main_application.py     # Main Flask application
├── run.py                 # Application entry point
├── startup.py             # Application initialization
├── config.py              # Configuration management
├── database_manager.py    # SQLite database operations
├── data_ingestion_manager.py  # Yahoo Finance data fetching
├── stock_analyzer.py      # Technical analysis engine
├── boc_data_manager.py    # Bank of Canada economic data
├── utils.py               # Utility functions
├── requirements.txt       # Python dependencies
├── frontend/              # Web interface files
├── data/                  # Data storage
├── logs/                  # Log files
├── backups/               # Database backups
└── ARCHIVE/               # Archived/unused files
```

## Technical Analysis Features

The application provides comprehensive technical analysis including:

- **Price Metrics**: Current price, daily changes, volume analysis
- **Moving Averages**: Simple and exponential moving averages
- **Technical Indicators**: RSI, MACD, Bollinger Bands
- **Performance Metrics**: Returns, volatility, risk assessments
- **Trend Analysis**: Support/resistance levels, trend identification

## Data Sources

- **Stock Data**: Yahoo Finance API via `yfinance` library
- **Economic Data**: Bank of Canada API for economic indicators
- **Company Information**: TSX company listings and metadata

## Development

For development work:

1. Install development dependencies:
```bash
pip install -r requirements_dev.txt
```

2. Run with debug mode:
```bash
python run.py --debug
```

## Monitoring and Maintenance

- **Logs**: Check `tsx_analyzer.log` for application logs
- **Database**: SQLite database is automatically maintained
- **Backups**: Database backups are created in `/backups/`
- **Auto-maintenance**: Daily cleanup runs at 2:00 AM

## Troubleshooting

### Common Issues

1. **Module not found**: Ensure virtual environment is activated
2. **Database locked**: Stop all running instances before restart
3. **API rate limits**: Reduce `MAX_COMPANIES_PER_HOUR` in config
4. **Port in use**: Change port with `--port` argument

### Getting Help

- Check logs in `tsx_analyzer.log`
- Run `python run.py --config-check` to verify configuration
- Ensure all dependencies are installed with `pip install -r requirements.txt`

## License

This project is for educational and personal use. Please respect data provider terms of service when using their APIs.

## Version

Current Version: 1.0.0

---

**Note**: This application is designed for analysis and educational purposes. Always consult with financial professionals before making investment decisions.
