"""
Main entry point for the TSX Stock Analyzer
Usage: python run.py [options]
"""

import sys
import argparse
from startup import initialize_app, print_startup_banner
from main_application import TSXAnalyzerApp

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='TSX Stock Analyzer - Professional stock analysis for TSX companies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                          # Start with default settings
  python run.py --host 0.0.0.0 --port 8080  # Bind to all interfaces on port 8080
  python run.py --initialize             # Initialize database on startup
  python run.py --auto-update            # Enable auto-update on startup
  python run.py --debug                  # Enable debug mode
        """
    )
    
    parser.add_argument('--host', 
                       default='localhost',
                       help='Host to bind the server to (default: localhost)')
    
    parser.add_argument('--port', 
                       type=int,
                       default=5000,
                       help='Port to bind the server to (default: 5000)')
    
    parser.add_argument('--debug', 
                       action='store_true',
                       help='Enable debug mode')
    
    parser.add_argument('--initialize', 
                       action='store_true',
                       help='Initialize database with TSX companies on startup')
    
    parser.add_argument('--auto-update', 
                       action='store_true',
                       help='Enable auto-update on startup')
    
    parser.add_argument('--config-check', 
                       action='store_true',
                       help='Check configuration and exit')
    
    parser.add_argument('--version', 
                       action='version',
                       version='TSX Stock Analyzer v1.0.0')
    
    return parser.parse_args()

def main():
    """Main entry point"""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Print banner (unless doing config check)
        if not args.config_check:
            print_startup_banner()
        
        # Initialize application
        print("Initializing application...")
        config = initialize_app()
        print("Application initialized successfully")
        
        # Configuration check mode
        if args.config_check:
            print("\n📋 Configuration Check:")
            print(f"  Environment: {config.__class__.__name__}")
            print(f"  Database: {config.DATABASE_PATH}")
            print(f"  Host: {config.HOST}")
            print(f"  Port: {config.PORT}")
            print(f"  Debug: {config.DEBUG}")
            print(f"  Rate Limit: {config.RATE_LIMIT_DELAY}s")
            print(f"  TSX Symbols: {len(config.TSX_SYMBOLS)} companies")
            print("✅ Configuration is valid")
            return 0
        
        # Import here to avoid circular imports
        from main_application import TSXAnalyzerApp
        
        # Create and configure the application
        print("Creating TSX Analyzer application...")
        app = TSXAnalyzerApp(db_path=config.DATABASE_PATH, config=config)
        
        # Initialize database if requested
        if args.initialize:
            print("🔄 Initializing database with TSX companies...")
            app.initialize_system()
            print("✅ Database initialization complete")
        
        # Enable auto-update if requested
        if args.auto_update:
            print("🔄 Enabling auto-update...")
            app.start_auto_update()
            print("✅ Auto-update enabled (1 company every 5 seconds)")
        
        # Print access information
        print(f"🌐 Web interface: http://{args.host}:{args.port}")
        print(f"📊 API endpoint: http://{args.host}:{args.port}/api")
        print("📝 Press Ctrl+C to stop the server")
        print("=" * 50)
        
        # Start the application
        print("Starting Flask application...")
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
        return 0
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    main()