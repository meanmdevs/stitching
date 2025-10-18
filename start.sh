#!/bin/bash
# Startup script for Fisheye Stitcher Service

echo "Starting Fisheye Stitcher Service..."

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
        exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 app:app
    else
        echo "Gunicorn not found, falling back to Flask development server..."
        exec python3 app.py
    fi
else
    echo "Starting Flask development server..."
    exec python3 app.py
fi
