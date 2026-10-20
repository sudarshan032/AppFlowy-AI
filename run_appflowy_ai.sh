#!/bin/bash

# run_appflowy_ai.sh
# One-click script to start AppFlowy with Local AI Features
# Setup:
#   1. Checks for Ollama
#   2. Starts Python AI Backend (port 8001)
#   3. Starts Flutter Frontend

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== AppFlowy AI Launcher ===${NC}"

# 1. Check Prerequisites
echo -e "${BLUE}[1/3] Checking prerequisites...${NC}"

# Check Ollama
if ! pgrep -x "ollama" > /dev/null; then
    echo -e "${RED}Error: Ollama is not running.${NC}"
    echo "Please start Ollama with 'ollama serve' in a separate terminal."
    exit 1
fi
echo -e "${GREEN}✓ Ollama is running${NC}"

# Check Python Venv
if [ ! -d "agent/venv" ]; then
    echo -e "${RED}Error: Python virtual environment not found in agent/venv${NC}"
    echo "Please run setup first or check installation."
    exit 1
fi
echo -e "${GREEN}✓ Python venv found${NC}"

# 2. Start AI Backend
echo -e "${BLUE}[2/3] Starting AI Backend (port 8001)...${NC}"
source agent/venv/bin/activate
# Run in background, log to file
uvicorn ai_plugin.api.app:app --app-dir agent --host 0.0.0.0 --port 8001 > ai_backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ AI Backend started (PID: $BACKEND_PID)${NC}"
echo "  Tail logs with: tail -f ai_backend.log"

# Function to cleanup background process on exit
cleanup() {
    echo -e "\n${BLUE}Shutting down...${NC}"
    if ps -p $BACKEND_PID > /dev/null; then
        echo "Stopping AI Backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
    fi
    echo -e "${GREEN}Goodbye!${NC}"
}
trap cleanup EXIT

# 3. Start Flutter Frontend
echo -e "${BLUE}[3/3] Starting AppFlowy Flutter App...${NC}"
cd appflowy/frontend/appflowy_flutter

# Check if flutter is installed
if ! command -v flutter &> /dev/null; then
    echo -e "${RED}Error: flutter command not found.${NC}"
    exit 1
fi

echo -e "${GREEN}Launching Flutter... (Press 'R' in terminal to reload)${NC}"
# Run flutter (this blocks until app is closed)
flutter run -d macos

# Script continues to cleanup trap when flutter run exits
