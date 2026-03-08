#!/bin/bash
# WSL Setup and Launch Script for Short Kinds

echo "========================================"
echo "Short Kinds - WSL Setup & Launch"
echo "========================================"
echo ""

# Check if we're in the right directory
if [ ! -f "backend/main.py" ]; then
    echo "Error: Please run this script from the ShortKinds directory"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment"
        echo "Please install python3-venv: sudo apt install python3-venv"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r backend/requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies"
    exit 1
fi

# Start server
echo ""
echo "========================================"
echo "Starting FastAPI server..."
echo ""
echo "Open your browser and go to:"
echo "http://localhost:8000"
echo ""
echo "API Documentation:"
echo "http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo ""

python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
