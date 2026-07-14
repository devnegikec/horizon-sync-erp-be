#!/bin/bash

# Development startup script for Identity Service
# This script sets up the development environment and starts the service

echo "========================================="
echo "Identity Service - Development Mode"
echo "========================================="
echo ""

# Check if .env exists, if not copy from .env.development
if [ ! -f .env ]; then
    echo "📋 Creating .env from .env.development..."
    cp .env.development .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  Please review and update .env with your local settings"
    echo ""
else
    echo "✅ .env file already exists"
    echo ""
fi

# Display current configuration
echo "📝 Current Configuration:"
echo "   Environment: development"
echo "   Cookie Secure: false (HTTP allowed)"
echo "   Cookie SameSite: lax"
echo "   Port: 8000"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt --quiet

echo ""
echo "========================================="
echo "🚀 Starting Identity Service..."
echo "========================================="
echo ""
echo "📍 API will be available at:"
echo "   - http://localhost:8000"
echo "   - Docs: http://localhost:8000/docs"
echo "   - Health: http://localhost:8000/health"
echo ""
echo "🍪 Cookie Settings (Development):"
echo "   - Secure: false (HTTP allowed)"
echo "   - SameSite: lax"
echo "   - HttpOnly: true"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the service
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
