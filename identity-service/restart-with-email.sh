#!/bin/bash

echo "🔄 Restarting Identity Service with Email Configuration..."
echo ""

# Stop containers
echo "📦 Stopping containers..."
docker-compose down

# Rebuild (optional - uncomment if you want to rebuild)
# echo "🔨 Rebuilding containers..."
# docker-compose build --no-cache

# Start containers
echo "🚀 Starting containers..."
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 5

# Check if containers are running
echo ""
echo "📊 Container Status:"
docker-compose ps

# Check email configuration
echo ""
echo "📧 Email Configuration:"
docker exec identity_api env | grep -E "(EMAIL|SMTP)" || echo "❌ Could not read email config"

# Show logs
echo ""
echo "📝 Recent logs (press Ctrl+C to exit):"
docker-compose logs -f --tail=50 api
