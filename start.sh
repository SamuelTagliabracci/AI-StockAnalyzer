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

source venv/bin/activate

# Start Flask app (no CLI flags needed, GUI controls everything now)
python3 run.py --port 5000 &
FLASK_PID=$!

# Start HTTP server
python3 -m http.server 8080 &
HTTP_PID=$!

echo ""
echo "🚀 TSX Stock Analyzer Services Started!"
echo "──────────────────────────────────────────"
echo "Flask API:     http://localhost:5000"
echo "Web Interface: http://localhost:8080/frontend/public/app.html"
echo ""
echo "📊 Use the web interface to:"
echo "   • View all 149 TSX stocks with analytics"
echo "   • Update individual stocks or run batch updates"
echo "   • Manage symbols (add/remove from config)"
echo "   • Configure settings via GUI"
echo ""
echo "Press Ctrl+C to stop both services"
echo "──────────────────────────────────────────"

# Wait for both processes
wait