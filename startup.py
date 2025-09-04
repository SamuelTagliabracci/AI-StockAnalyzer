"""
Startup script for the TSX Stock Analyzer
Handles initialization and environment setup
"""

import os
import sys
import logging
from pathlib import Path
from config import config

def setup_logging(log_level: str = 'INFO', log_file: str = 'tsx_analyzer.log'):
    """Setup logging configuration"""
    
    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    log_file_path = log_dir / log_file
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific logger levels to reduce noise
    logging.getLogger('yfinance').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        ('yfinance', 'yfinance'),
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('flask', 'Flask'),
        ('flask_cors', 'Flask-CORS'),
        ('schedule', 'schedule'),
        ('requests', 'requests')
    ]
    
    missing_packages = []
    
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("📦 Please install them using: pip install -r requirements.txt")
        return False
    
    print("✅ All required dependencies are installed")
    return True

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print(f"❌ Python 3.8+ required. Current version: {sys.version}")
        return False
    
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def create_directories():
    """Create necessary directories"""
    directories = ['logs', 'data', 'backups', 'temp']
    
    for directory in directories:
        path = Path(directory)
        path.mkdir(exist_ok=True)
        logging.info(f"Ensured directory exists: {directory}")

def get_config():
    """Get configuration based on environment"""
    try:
        env = os.environ.get('FLASK_ENV', 'development')
        print(f"Loading configuration for environment: {env}")
        
        config_class = config.get(env, config['default'])
        print(f"Using configuration class: {config_class.__name__}")
        
        # Instantiate the config
        app_config = config_class()
        
        # Validate production config if needed
        if hasattr(app_config, 'validate') and env == 'production':
            print("Validating production configuration...")
            app_config.validate()
            print("Production configuration validated successfully")
        
        return app_config
        
    except Exception as e:
        print(f"Error loading configuration: {e}")
        raise

def validate_config(app_config):
    """Validate configuration settings"""
    issues = []
    
    # Check database path
    db_dir = Path(app_config.DATABASE_PATH).parent
    if not db_dir.exists():
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            issues.append(f"Cannot create database directory: {db_dir}")
    
    # Check port availability
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((app_config.HOST, app_config.PORT))
        sock.close()
    except OSError:
        issues.append(f"Port {app_config.PORT} is already in use")
    
    # Check required environment variables for production
    if app_config.__class__.__name__ == 'ProductionConfig':
        if not os.environ.get('SECRET_KEY'):
            issues.append("SECRET_KEY environment variable not set for production")
    
    if issues:
        print("⚠️  Configuration issues found:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    print("✅ Configuration validated successfully")
    return True

def initialize_app():
    """Initialize the application with proper setup"""
    
    print("Starting TSX Stock Analyzer...")
    print("=" * 50)
    
    # Check Python version
    print("Checking Python version...")
    if not check_python_version():
        sys.exit(1)
    
    # Check dependencies
    print("Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    
    # Get configuration
    print("Loading configuration...")
    app_config = get_config()
    
    # Validate configuration
    print("Validating configuration...")
    if not validate_config(app_config):
        print("Configuration validation failed")
        sys.exit(1)
    
    # Setup logging
    print("Setting up logging...")
    setup_logging(app_config.LOG_LEVEL, app_config.LOG_FILE)
    
    # Create directories
    print("Creating directories...")
    create_directories()
    
    # Log startup info
    logging.info("=" * 50)
    logging.info("TSX Stock Analyzer starting up")
    logging.info(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    logging.info(f"Configuration: {app_config.__class__.__name__}")
    logging.info(f"Database: {app_config.DATABASE_PATH}")
    logging.info(f"Host: {app_config.HOST}:{app_config.PORT}")
    logging.info(f"Rate limit delay: {app_config.RATE_LIMIT_DELAY}s")
    logging.info(f"TSX symbols to track: {len(app_config.TSX_SYMBOLS)}")
    logging.info("=" * 50)
    
    print("Application initialization complete")
    return app_config

def print_startup_banner():
    """Print startup banner"""
    banner = """
    ████████╗███████╗██╗  ██╗    ███████╗████████╗ ██████╗  ██████╗██╗  ██╗
    ╚══██╔══╝██╔════╝╚██╗██╔╝    ██╔════╝╚══██╔══╝██╔═══██╗██╔════╝██║ ██╔╝
       ██║   ███████╗ ╚███╔╝     ███████╗   ██║   ██║   ██║██║     █████╔╝ 
       ██║   ╚════██║ ██╔██╗     ╚════██║   ██║   ██║   ██║██║     ██╔═██╗ 
       ██║   ███████║██╔╝ ██╗    ███████║   ██║   ╚██████╔╝╚██████╗██║  ██╗
       ╚═╝   ╚══════╝╚═╝  ╚═╝    ╚══════╝   ╚═╝    ╚═════╝  ╚═════╝╚═╝  ╚═╝
    
     ██████╗ ███╗   ██╗ █████╗ ██╗  ██╗   ██╗███████╗███████╗██████╗ 
    ██╔═══██╗████╗  ██║██╔══██╗██║  ╚██╗ ██╔╝╚══███╔╝██╔════╝██╔══██╗
    ██║   ██║██╔██╗ ██║███████║██║   ╚████╔╝   ███╔╝ █████╗  ██████╔╝
    ██║   ██║██║╚██╗██║██╔══██║██║    ╚██╔╝   ███╔╝  ██╔══╝  ██╔══██╗
    ╚██████╔╝██║ ╚████║██║  ██║███████╗██║   ███████╗███████╗██║  ██║
     ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝   ╚══════╝╚══════╝╚═╝  ╚═╝
                                                                        
    Professional-grade stock analysis for TSX companies
    Version 1.0.0 | Built with Python, Flask, and Yahoo Finance
    """
    print(banner)