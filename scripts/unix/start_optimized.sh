#!/bin/bash
# Optimized startup script for Linux/Mac
# Fast initialization with production configuration

echo "========================================"
echo "  Intelligent Development Assistant"
echo "  Optimized Startup (Fast Mode)"
echo "========================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please run: python -m venv venv"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found!"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "IMPORTANT: Please edit .env and add your HF_API_TOKEN"
    echo "Press Enter to continue once you've updated .env..."
    read
fi

# Set environment for production
CONFIG_FILE="config/config.production.yaml"

# Check if production config exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Production config not found at $CONFIG_FILE"
    echo "Please ensure config.production.yaml exists"
    exit 1
fi

echo "Starting with optimized configuration..."
echo "Config: $CONFIG_FILE"
echo ""

# Start the application with production config
python main.py --config "$CONFIG_FILE"

# Deactivate virtual environment on exit
deactivate
