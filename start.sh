#!/bin/bash
# Startup script for Fisheye Stitcher Service

echo "Starting Fisheye Stitcher Service..."

# Check required tools
if ! command -v dcraw &> /dev/null; then
    echo "ERROR: dcraw not found. DNG processing will fail."
    exit 1
fi

if ! command -v convert &> /dev/null && ! command -v magick &> /dev/null; then
    echo "ERROR: ImageMagick not found."
    exit 1
fi

echo "✓ dcraw found: $(dcraw 2>&1 | head -n1)"
echo "✓ ImageMagick found"

# Ensure the binary exists
if [ ! -f "/app/build/bin/fisheyeStitcher" ]; then
    echo "Building fisheye stitcher binary..."
    cd /app
    mkdir -p build
    cd build
    cmake ..
    make -j4
    cd ..
fi

# Create necessary directories
mkdir -p /app/stitched /app/input

# Start the application
echo "Starting web service..."
if [ "$FLASK_ENV" = "production" ]; then
    # Check if gunicorn is available
    if command -v gunicorn &> /dev/null; then
        echo "Starting with gunicorn..."
        exec gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 300 app:app
    else
        echo "Gunicorn not found, falling back to Flask development server..."
        exec python3 app.py
    fi
else
    echo "Starting Flask development server..."
    exec python3 app.py
fi
