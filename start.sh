#!/bin/bash
set -e

echo "🚀 Starting Media Download Service (Scalable Architecture)..."

# Ensure temp directory exists
mkdir -p /tmp/mediadownloads

# Start docker-compose
docker-compose up -d

echo ""
echo "✅ Services are starting up!"
echo "📍 API / Frontend : http://localhost:8000"
echo "📍 MinIO Console  : http://localhost:9001 (minioadmin / change_me_in_production)"
echo "📍 API Docs       : http://localhost:8000/docs"
echo ""
echo "To view logs, run: docker-compose logs -f"
echo "To stop, run: docker-compose down"
