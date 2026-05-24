#!/bin/bash

# AI Teacher Helper Bot Launcher for Linux

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to script directory
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment 'venv' not found."
    echo "Please create it first:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found."
    echo "Please create .env with your configuration:"
    echo "  cp .env.example .env"
    echo "  # Edit .env with your settings"
    exit 1
fi

# Run the bot
echo "🚀 Starting AI Teacher Helper Bot..."
python -m bot.main

# Deactivate virtual environment on exit
deactivate