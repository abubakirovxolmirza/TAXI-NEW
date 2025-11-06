#!/bin/bash

echo "========================================"
echo "Taxi Service Backend - Quick Start"
echo "========================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.example to .env and configure it."
    echo ""
    exit 1
fi

# Install/update dependencies
echo "Checking dependencies..."
pip install -q -r requirements.txt
echo "Dependencies installed."
echo ""

# Start the application
echo "========================================"
echo "Starting Taxi Service API..."
echo "Server will be available at: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python main.py
