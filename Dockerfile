# Use Ubuntu 20.04 as base image
FROM ubuntu:20.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    pkg-config \
    libopencv-dev \
    python3 \
    python3-pip \
    python3-dev \
    libopencv-contrib-dev \
    libopencv-dev \
    libgtk2.0-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libatlas-base-dev \
    gfortran \
    wget \
    curl \
    dcraw \
    rawtherapee \
    imagemagick \
    libmagickcore-6.q16-6-extra \
    && rm -rf /var/lib/apt/lists/*

# Configure ImageMagick to use dcraw for DNG files
RUN sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick-6/policy.xml && \
    sed -i '/<policy domain="delegate" rights="none" pattern="HTTPS" \/>/d' /etc/ImageMagick-6/policy.xml && \
    sed -i '/<policy domain="delegate" rights="none" pattern="HTTP" \/>/d' /etc/ImageMagick-6/policy.xml && \
    sed -i '/<policy domain="coder" rights="none" pattern="PDF" \/>/d' /etc/ImageMagick-6/policy.xml

# Increase ImageMagick memory and disk limits
RUN sed -i 's/<policy domain="resource" name="memory" value=".*"/<policy domain="resource" name="memory" value="4GiB"/' /etc/ImageMagick-6/policy.xml && \
    sed -i 's/<policy domain="resource" name="map" value=".*"/<policy domain="resource" name="map" value="4GiB"/' /etc/ImageMagick-6/policy.xml && \
    sed -i 's/<policy domain="resource" name="disk" value=".*"/<policy domain="resource" name="disk" value="4GiB"/' /etc/ImageMagick-6/policy.xml && \
    sed -i 's/<policy domain="resource" name="area" value=".*"/<policy domain="resource" name="area" value="2GiB"/' /etc/ImageMagick-6/policy.xml

# Add dcraw delegate for DNG files to ImageMagick
RUN echo '<delegate decode="dng:decode" command="dcraw -c -w -6 -T %i > %o.tiff; mv %o.tiff %o"/>' >> /etc/ImageMagick-6/delegates.xml

# Set working directory
WORKDIR /app

# Copy the entire project
COPY . .

# Build the fisheye stitcher
RUN mkdir -p build && \
    cd build && \
    cmake .. && \
    make -j4

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/stitched /app/input

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Set ImageMagick environment variables for runtime
ENV MAGICK_MEMORY_LIMIT=4GiB
ENV MAGICK_MAP_LIMIT=4GiB
ENV MAGICK_DISK_LIMIT=4GiB
ENV MAGICK_AREA_LIMIT=2GiB
ENV MAGICK_TMPDIR=/tmp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Make startup script executable
RUN chmod +x /app/start.sh

# Run the application
CMD ["/app/start.sh"]

# Alternative: Direct gunicorn command (uncomment if start.sh fails)
# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
