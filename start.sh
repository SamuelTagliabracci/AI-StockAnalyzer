#!/bin/bash

# Function to cleanup processes on exit
cleanup() {
    echo "Stopping services..."
    kill $FLASK_PID $HTTP_PID 2>/dev/null
    wait $FLASK_PID $HTTP_PID 2>/dev/null
    echo "Services stopped."
}

# Set up trap to cleanup on script exit
trap cleanup EXIT

# Check if virtual environment exists and is activated
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo ""
    echo "📋 Please run these commands to set up the virtual environment:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    echo ""
    echo "Then run ./start.sh again"
    exit 1
fi

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
    
    if [ -z "$VIRTUAL_ENV" ]; then
        echo "❌ Failed to activate virtual environment!"
        echo ""
        echo "📋 Try running these commands manually:"
        echo "   source venv/bin/activate"
        echo "   pip install -r requirements.txt"
        echo "   ./start.sh"
        exit 1
    fi
fi

# Check if requirements are installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Dependencies not installed. Installing requirements..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies!"
        echo "Please run: pip install -r requirements.txt"
        exit 1
    fi
fi

# Start Flask app (no CLI flags needed, GUI controls everything now)
python3 run.py --port 5000 &
FLASK_PID=$!

# Start HTTP server
python3 -m http.server 8080 &
HTTP_PID=$!

echo ""
echo "🚀 Services started successfully!"
echo ""
echo "📊 Web Interface: http://localhost:8080/frontend/public/"
echo ""
echo "Press Ctrl+C to stop services"

# Wait for both processes
wait