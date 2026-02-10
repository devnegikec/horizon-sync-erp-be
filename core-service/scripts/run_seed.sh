#!/bin/bash

# Helper script to run seed scripts inside Docker container
# Usage: ./scripts/run_seed.sh [basic|stock|all]

set -e

SCRIPT_TYPE=${1:-all}

echo "=========================================="
echo "Horizon Sync - Database Seeding"
echo "=========================================="
echo ""

# Check if container is running
if ! docker ps | grep -q horizon_core; then
    echo "❌ Error: horizon_core container is not running"
    echo "   Please start it with: docker-compose up -d"
    exit 1
fi

echo "✓ Container is running"
echo ""

case $SCRIPT_TYPE in
    basic)
        echo "Running basic seed data (items, warehouses, etc.)..."
        docker exec -it horizon_core python scripts/seed_data.py
        ;;
    stock)
        echo "Running stock management seed data..."
        docker exec -it horizon_core python scripts/seed_stock_data_v2.py
        ;;
    all)
        echo "Running all seed scripts..."
        echo ""
        echo "1/2 Running basic seed data..."
        docker exec -it horizon_core python scripts/seed_data.py
        echo ""
        echo "2/2 Running stock seed data..."
        docker exec -it horizon_core python scripts/seed_stock_data_v2.py
        ;;
    *)
        echo "❌ Invalid option: $SCRIPT_TYPE"
        echo ""
        echo "Usage: ./scripts/run_seed.sh [basic|stock|all]"
        echo ""
        echo "Options:"
        echo "  basic  - Run basic seed data (items, warehouses, etc.)"
        echo "  stock  - Run stock management seed data"
        echo "  all    - Run all seed scripts (default)"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "✓ Seeding completed successfully!"
echo "=========================================="
