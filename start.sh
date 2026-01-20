#!/bin/bash
# AppFlowy + AI Agent Startup Script
# Run this from the project root to start both services

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FLUTTER_DIR="$PROJECT_ROOT/appflowy/frontend/appflowy_flutter"

echo "🚀 Starting AppFlowy AI Development Environment..."
echo "================================================="

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    kill $AGENT_PID 2>/dev/null || true
    kill $FLUTTER_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Python Agent in background
echo "🤖 Starting AI Agent (port 8000)..."
cd "$PROJECT_ROOT"
source venv/bin/activate
PYTHONPATH="${PYTHONPATH}:${PROJECT_ROOT}" uvicorn agent.orchestrator.main:app --host 0.0.0.0 --port 8000 --reload &
AGENT_PID=$!

# Give agent a moment to start
sleep 2

# Start Flutter app
echo "📱 Starting AppFlowy Flutter..."
cd "$FLUTTER_DIR"
flutter run -d macos --debug &
FLUTTER_PID=$!

echo ""
echo "✅ Both services started!"
echo "   - AI Agent: http://localhost:8000"
echo "   - Flutter: Running on macOS"
echo ""
echo "Press Ctrl+C to stop both services."

# Wait for both processes
wait $FLUTTER_PID $AGENT_PID
