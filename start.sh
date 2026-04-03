#!/bin/bash
set -e

echo "🚀 Starting Media Download Service (Google Drive Storage)..."

# Ensure temp directory exists
mkdir -p /tmp/mediadownloads

# Start docker-compose
docker-compose up -d

echo ""
echo "✅ Services are starting up!"
echo "📍 API / Frontend : http://localhost:8000"
echo "📍 API Docs       : http://localhost:8000/docs"
echo "📍 Flower Monitor : http://localhost:5555"
echo ""
echo "To view logs, run: docker-compose logs -f"
echo "To stop, run: docker-compose down"
