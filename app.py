#!/usr/bin/env python3
"""
Fisheye Stitcher Web Service
A Flask web application that provides fisheye image stitching as a service.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template_string, flash, redirect, url_for, render_template
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from PIL import Image
import logging
import uuid
import requests
import base64
from io import BytesIO
import threading

# Import our filter system
sys.path.insert(0, os.path.dirname(__file__))
from real_estate_filters_enhanced import RealEstateFiltersEnhanced

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Detect ImageMagick command (convert for older versions, magick for newer)
MAGICK_CMD = None
for cmd in ['convert', 'magick']:
    if shutil.which(cmd):
        MAGICK_CMD = cmd
        logger.info(f"Found ImageMagick command: {cmd}")
        break

if MAGICK_CMD is None:
    logger.warning("ImageMagick not found in PATH")

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25MB max file size
app.secret_key = os.environ.get("FLASK_SECRET", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImlhdCI6MTUxNjIzOTAyMn0.KMUFsIDTnFmyG3nMiGM6H9FNFUROf3wh7SmqJp-QV30")
app.config['UPLOAD_FOLDER'] = '/tmp/real_estate_uploads'
app.config['SECRET_KEY'] = 'SECRET_KEY'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

processing_status = {}

# Configuration
PROJECT_ROOT = Path(__file__).parent
BUILD_DIR = PROJECT_ROOT / "build"
BINARY_PATH = BUILD_DIR / "bin" / "fisheyeStitcher"
UTILS_DIR = PROJECT_ROOT / "utils"
MLS_MAP_PATH = UTILS_DIR / "grid_xd_yd_3840x1920.yml.gz"
ALLOWED_EXTENSIONS = {'.dng', '.DNG'}
MAX_DOWNLOAD_SIZE_MB = 300  # per file limit
ALLOWED_EXTENSION_ENHANCE = {'png', 'jpg', 'jpeg', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSION_ENHANCE

# Filter metadata
FILTERS_INFO = {
    "best": [
        {"id": "warm-sunset", "name": "Warm Sunset Combo ⭐", "desc": "Sky replacement + warm tone"},
        {"id": "luxury", "name": "Luxury Estate", "desc": "High-end professional look"},
        {"id": "modern", "name": "Modern Minimal", "desc": "Clean contemporary style"},
    ],
    "quality": [
        {"id": "hdr-pro", "name": "HDR Pro", "desc": "Professional detail enhancement"},
        {"id": "balanced", "name": "Balanced Pro", "desc": "All-purpose professional"},
        {"id": "magazine", "name": "Magazine Editorial", "desc": "High-end editorial quality"},
        {"id": "architectural", "name": "Architectural", "desc": "Sharp detailed style"},
    ],
    "atmosphere": [
        {"id": "golden-hour", "name": "Golden Hour", "desc": "Sunset/sunrise glow"},
        {"id": "warm-natural", "name": "Natural Warmth", "desc": "Inviting warmth"},
        {"id": "cinematic", "name": "Cinematic", "desc": "Movie-like grading"},
        {"id": "moody", "name": "Moody Dramatic", "desc": "Dark dramatic atmosphere"},
        {"id": "twilight", "name": "Twilight Magic", "desc": "Blue hour effect"},
    ],
    "brightness": [
        {"id": "crisp-clean", "name": "Crisp & Clean", "desc": "Ultra-sharp bright"},
        {"id": "bright-airy", "name": "Bright & Airy", "desc": "Spacious light feeling"},
        {"id": "fresh-bright", "name": "Fresh & Bright", "desc": "Energetic bright"},
        {"id": "vibrant", "name": "Vibrant Pop", "desc": "Eye-catching colors"},
        {"id": "soft-elegant", "name": "Soft Elegant", "desc": "Elegant sophisticated"},
    ],
    "sky": [
        {"id": "sky-dramatic", "name": "Dramatic Sky", "desc": "Enhance existing sky"},
        {"id": "sky-blue", "name": "Blue Sky Replace", "desc": "Perfect blue sky"},
        {"id": "sky-sunset", "name": "Sunset Sky Replace", "desc": "Beautiful sunset"},
    ]
}

INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <title>HDR Merge from URLs</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial;
                max-width: 900px;
                margin: 40px auto;
            }
            textarea {
                width: 100%;
                height: 200px;
                font-family: monospace;
            }
            .card {
                border: 1px solid #ddd;
                padding: 20px;
                border-radius: 8px;
            }
            .flash {
                padding: 10px;
                border-radius: 6px;
                margin-bottom: 10px;
            }
            .danger {
                background: #ffe5e5;
                border: 1px solid #ff9ea0;
            }
            .warning {
                background: #fff6e0;
                border: 1px solid #ffd38a;
            }
        </style>
    </head>
    <body>
        <h1>HDR Merge — DNG URLs</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, msg in messages %}
                <div class="flash {{ category }}">{{ msg }}</div>
            {% endfor %}
        {% endif %}
        {% endwith %}

        <div class="card">
            <form method="post">
                <p>Enter one or more DNG file URLs (one per line):</p>
                <textarea
                    name="urls"
                    placeholder="https://example.com/image1.dng
https://example.com/image2.dng"
                ></textarea>

                <p>
                    <label for="method">Merge method:</label>
                    <select id="method" name="method">
                        <option value="mean">Mean</option>
                        <option value="median">Median</option>
                        <option value="max">Max</option>
                    </select>
                </p>
                <p><button type="submit">Merge HDR</button></p>
            </form>
        </div>
    </body>
</html>"""

RESULT_TEMPLATE = """<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8" />
        <title>HDR Merge Result</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial;
                max-width: 900px;
                margin: 40px auto;
            }
            .card {
                border: 1px solid #ddd;
                padding: 20px;
                border-radius: 8px;
            }
            img {
                max-width: 100%;
                height: auto;
                display: block;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <h1>Merged Image</h1>
        <div class="card">
            <p><a href="{{ result_url }}" target="_blank">Open image in new tab</a> — you can right-click to save.</p>
            <img src="{{ result_url }}" alt="Merged result" />
            <p style="font-size: 0.9rem; color: #666">
                If the image doesn't render, download via the link above. Temporary working directory: <code>{{ tmpdir }}</code>
            </p>
            <p><a href="{{ url_for('index') }}">Merge more</a></p>
        </div>
    </body>
</html>"""

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fisheye Stitcher Service</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .upload-area {
            border: 2px dashed #ccc;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            margin: 20px 0;
            background-color: #fafafa;
        }
        .upload-area:hover {
            border-color: #999;
            background-color: #f0f0f0;
        }
        input[type="file"] {
            margin: 10px 0;
        }
        button {
            background-color: #007bff;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #0056b3;
        }
        button:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        .result {
            margin-top: 20px;
            padding: 20px;
            background-color: #e9ecef;
            border-radius: 5px;
            display: none;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .loading {
            text-align: center;
            color: #666;
        }
        .image-preview {
            max-width: 100%;
            margin: 10px 0;
            border-radius: 5px;
        }
        .api-info {
            margin-top: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .code {
            background-color: #f1f1f1;
            padding: 10px;
            border-radius: 3px;
            font-family: monospace;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🐠 Fisheye Stitcher Service</h1>
        <p style="text-align: center; color: #666;">
            Upload a dual fisheye image to create a panoramic stitched image
        </p>
        
        <div class="upload-area">
            <h3>Upload Dual Fisheye Image</h3>
            <form id="uploadForm" enctype="multipart/form-data">
                <input type="file" id="imageFile" name="image" accept="image/*" required>
                <br><br>
                <button type="submit" id="submitBtn">Stitch Image</button>
            </form>
        </div>
        
        <div id="result" class="result"></div>
        
        <div class="api-info">
            <h3>API Usage</h3>
            <p>You can also use this service programmatically:</p>
            <div class="code">
POST /stitch<br>
Content-Type: multipart/form-data<br>
Body: image file (dual fisheye image)
            </div>
            <p><strong>Response:</strong> Stitched panoramic image (JPEG)</p>
        </div>
    </div>

    <script>
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const fileInput = document.getElementById('imageFile');
            const submitBtn = document.getElementById('submitBtn');
            const resultDiv = document.getElementById('result');
            
            if (!fileInput.files[0]) {
                showResult('Please select an image file.', 'error');
                return;
            }
            
            submitBtn.disabled = true;
            submitBtn.textContent = 'Processing...';
            resultDiv.style.display = 'block';
            resultDiv.className = 'result loading';
            resultDiv.innerHTML = 'Processing your fisheye image...';
            
            const formData = new FormData();
            formData.append('image', fileInput.files[0]);
            
            try {
                const response = await fetch('/stitch', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    showResult(`
                        <h4>✅ Stitching Complete!</h4>
                        <p>Your panoramic image is ready:</p>
                        <img src="${url}" alt="Stitched Image" class="image-preview">
                        <br><br>
                        <a href="${url}" download="stitched_image.jpg" style="color: #007bff;">Download Image</a>
                    `, 'success');
                } else {
                    const error = await response.text();
                    showResult(`Error: ${error}`, 'error');
                }
            } catch (error) {
                showResult(`Error: ${error.message}`, 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Stitch Image';
            }
        });
        
        function showResult(message, type) {
            const resultDiv = document.getElementById('result');
            resultDiv.style.display = 'block';
            resultDiv.className = `result ${type}`;
            resultDiv.innerHTML = message;
        }
    </script>
</body>
</html>
"""

def find_magick_executable():
    for cmd in ("magick", "convert"):
        try:
            subprocess.run([cmd, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return cmd
        except Exception:
            pass
    return None

MAGICK_CMD = find_magick_executable()

def download_file(url, dest_folder):
    local_filename = dest_folder / f"{uuid.uuid4().hex}_{os.path.basename(url.split('?')[0])}"
    headers = {"User-Agent": "HDRMerge/1.0"}
    with requests.get(url, stream=True, headers=headers, timeout=60) as r:
        r.raise_for_status()
        total_size = 0
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_size += len(chunk)
                    if total_size > MAX_DOWNLOAD_SIZE_MB * 1024 * 1024:
                        raise ValueError(f"File exceeds {MAX_DOWNLOAD_SIZE_MB}MB limit")
    return local_filename

def ensure_binary_exists():
    """Ensure the fisheye stitcher binary exists and is built."""
    if not BINARY_PATH.exists():
        logger.info("Building fisheye stitcher binary...")
        try:
            # Create build directory if it doesn't exist
            BUILD_DIR.mkdir(exist_ok=True)
            
            # Run cmake and make
            subprocess.run(["cmake", ".."], cwd=BUILD_DIR, check=True)
            subprocess.run(["make", "-j4"], cwd=BUILD_DIR, check=True)
            
            if not BINARY_PATH.exists():
                raise RuntimeError("Failed to build fisheye stitcher binary")
                
            logger.info("Binary built successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Build failed: {e}")
            raise RuntimeError("Failed to build fisheye stitcher binary")
    else:
        logger.info("Binary already exists")

def download_file(url, dest_dir, max_size_mb=MAX_DOWNLOAD_SIZE_MB):
    """Download a file from URL to destination directory with size limit."""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Check content length
        content_length = response.headers.get('Content-Length')
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            if size_mb > max_size_mb:
                raise ValueError(f"File too large: {size_mb:.1f}MB (max {max_size_mb}MB)")
        
        # Generate unique filename
        original_name = Path(url.split('?')[0]).name
        unique_id = uuid.uuid4().hex[:32]
        safe_name = f"{unique_id}_{secure_filename(original_name)}"
        dest_path = dest_dir / safe_name
        
        # Download with size check
        total_size = 0
        max_size_bytes = max_size_mb * 1024 * 1024
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    total_size += len(chunk)
                    if total_size > max_size_bytes:
                        dest_path.unlink(missing_ok=True)
                        raise ValueError(f"File exceeded size limit during download")
                    f.write(chunk)
        
        logger.info(f"Downloaded {url} to {dest_path} ({total_size / 1024 / 1024:.1f}MB)")
        return dest_path
        
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to download {url}: {str(e)}")

def validate_image(image_path):
    """Validate that the uploaded image is a valid dual fisheye image."""
    try:
        # Read image with OpenCV
        img = cv2.imread(str(image_path))
        if img is None:
            return False, "Invalid image format"
        
        height, width = img.shape[:2]
        
        # Check if image dimensions are reasonable for dual fisheye
        if width < 1000 or height < 500:
            return False, "Image too small. Expected dual fisheye image with width >= 1000px"
        
        # Check if width is roughly 2x height (typical for dual fisheye)
        aspect_ratio = width / height
        if aspect_ratio < 1.5 or aspect_ratio > 3.0:
            logger.warning(f"Unusual aspect ratio: {aspect_ratio:.2f}. Expected ~2.0 for dual fisheye")
        
        return True, "Valid image"
        
    except Exception as e:
        return False, f"Error validating image: {str(e)}"

def stitch_image(input_path, output_path):
    """Run the fisheye stitcher on the input image."""
    try:
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_input = Path(temp_dir) / "input.jpg"
            temp_output_dir = Path(temp_dir) / "output"
            temp_output_dir.mkdir()
            
            # Copy input to temp location
            shutil.copy2(input_path, temp_input)
            
            # Run the fisheye stitcher
            cmd = [
                str(BINARY_PATH),
                "--out_dir", str(temp_output_dir),
                "--img_nm", "stitched",
                "--img_path", str(temp_input),
                "--mls_map_path", str(MLS_MAP_PATH),
                "--enb_light_compen", "false",
                "--enb_refine_align", "false",
                "--mode", "image"
            ]
            
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                logger.error(f"Stitcher failed: {result.stderr}")
                raise RuntimeError(f"Stitching failed: {result.stderr}")
            
            # Find the output file
            output_files = list(temp_output_dir.glob("*_blend.jpg"))
            if not output_files:
                raise RuntimeError("No output file generated")
            
            # Copy output to final location
            shutil.copy2(output_files[0], output_path)
            logger.info(f"Stitching completed successfully: {output_path}")
            
    except subprocess.TimeoutExpired:
        raise RuntimeError("Stitching timed out (60s)")
    except Exception as e:
        logger.error(f"Stitching error: {e}")
        raise

@app.route('/')
def index():
    """Serve the main web interface."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/stitch', methods=['POST'])
def stitch():
    """API endpoint to stitch fisheye images."""
    try:
        # Check if image file is present
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No image file selected'}), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            file.save(temp_file.name)
            temp_input_path = temp_file.name
        
        try:
            # Validate image
            is_valid, message = validate_image(temp_input_path)
            if not is_valid:
                return jsonify({'error': message}), 400
            
            # Create output file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_output:
                temp_output_path = temp_output.name
            
            # Stitch the image
            stitch_image(temp_input_path, temp_output_path)
            
            # Return the stitched image
            return send_file(
                temp_output_path,
                mimetype='image/jpeg',
                as_attachment=True,
                download_name='stitched_image.jpg'
            )
            
        finally:
            # Clean up temporary files
            try:
                os.unlink(temp_input_path)
                if 'temp_output_path' in locals():
                    os.unlink(temp_output_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error in stitch endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'binary_exists': BINARY_PATH.exists(),
        'mls_map_exists': MLS_MAP_PATH.exists()
    })

@app.route('/info')
def info():
    """Service information endpoint."""
    return jsonify({
        'service': 'Fisheye Stitcher',
        'version': '1.0.0',
        'description': 'Web service for stitching dual fisheye camera images into panoramic images',
        'endpoints': {
            'POST /stitch': 'Stitch a dual fisheye image',
            'GET /health': 'Health check',
            'GET /info': 'Service information'
        }
    })

@app.route('/hdr-merge', methods=['GET', 'POST'])
def hdr_merge():
    if request.method == 'POST':
        urls_raw = request.form.get('urls', '').strip()
        method = request.form.get('method', 'mean').lower()
        if not urls_raw:
            flash("No URLs provided.", "danger")
            return redirect(request.url)

        urls = [u.strip() for u in urls_raw.splitlines() if u.strip()]
        if not urls:
            flash("Please enter valid DNG URLs (one per line).", "danger")
            return redirect(request.url)

        tmp_dir = Path(tempfile.mkdtemp(prefix="hdr_merge_"))
        saved_paths = []

        try:
            for url in urls:
                ext = Path(url.split('?')[0]).suffix
                if ext not in ALLOWED_EXTENSIONS:
                    flash(f"Skipping unsupported file type: {url}", "warning")
                    continue
                app.logger.info(f"Downloading {url}")
                saved_paths.append(str(download_file(url, tmp_dir)))

            if len(saved_paths) == 0:
                flash("No valid DNG URLs downloaded.", "danger")
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return redirect(request.url)

            if MAGICK_CMD is None:
                flash("ImageMagick not found. Install it and ensure 'magick' is in PATH.", "danger")
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return redirect(request.url)

            # Convert DNG files to TIFF using dcraw
            app.logger.info(f"Converting {len(saved_paths)} DNG files to TIFF...")
            converted_paths = []
            
            for dng_path in saved_paths:
                try:
                    # Output TIFF path
                    tiff_path = str(Path(dng_path).with_suffix('.tiff'))
                    
                    # Use dcraw to convert DNG to 16-bit TIFF
                    # -c: write to stdout
                    # -w: use camera white balance
                    # -T: output TIFF
                    # -6: 16-bit output
                    # -q 3: high quality interpolation
                    dcraw_cmd = ['dcraw', '-c', '-w', '-T', '-6', '-q', '3', dng_path]
                    
                    app.logger.info(f"Converting {Path(dng_path).name} to TIFF...")
                    
                    with open(tiff_path, 'wb') as f:
                        result = subprocess.run(
                            dcraw_cmd,
                            stdout=f,
                            stderr=subprocess.PIPE,
                            timeout=60
                        )
                    
                    if result.returncode != 0:
                        app.logger.error(f"dcraw failed for {dng_path}: {result.stderr.decode()}")
                        continue
                    
                    if Path(tiff_path).exists() and Path(tiff_path).stat().st_size > 0:
                        converted_paths.append(tiff_path)
                        app.logger.info(f"Successfully converted {Path(dng_path).name}")
                    else:
                        app.logger.error(f"dcraw produced empty file for {dng_path}")
                        
                except subprocess.TimeoutExpired:
                    app.logger.error(f"dcraw timeout for {dng_path}")
                except Exception as e:
                    app.logger.error(f"Error converting {dng_path}: {e}")
            
            if not converted_paths:
                flash("Failed to convert any DNG files to TIFF. Check server logs.", "danger")
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return redirect(request.url)
            
            app.logger.info(f"Successfully converted {len(converted_paths)} files to TIFF")

            # Resize TIFFs to reduce memory usage (optional but recommended)
            # Convert 16-bit to 8-bit and resize to reasonable dimensions
            app.logger.info("Optimizing TIFFs for merging...")
            optimized_paths = []
            
            for tiff_path in converted_paths:
                try:
                    optimized_path = str(Path(tiff_path).with_suffix('.optimized.tiff'))
                    
                    # Use ImageMagick to convert to 8-bit and resize if too large
                    optimize_cmd = [
                        MAGICK_CMD, tiff_path,
                        "-depth", "8",           # Convert to 8-bit (reduces file size by 50%)
                        "-resize", "4096x4096>", # Resize if larger than 4096px (keep aspect ratio)
                        "-compress", "LZW",      # Add compression
                        optimized_path
                    ]
                    
                    result = subprocess.run(
                        optimize_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=30
                    )
                    
                    if result.returncode == 0 and Path(optimized_path).exists():
                        optimized_paths.append(optimized_path)
                        # Delete original large TIFF to save space
                        Path(tiff_path).unlink(missing_ok=True)
                    else:
                        # If optimization fails, use original
                        app.logger.warning(f"Failed to optimize {tiff_path}, using original")
                        optimized_paths.append(tiff_path)
                        
                except Exception as e:
                    app.logger.error(f"Error optimizing {tiff_path}: {e}")
                    optimized_paths.append(tiff_path)
            
            app.logger.info(f"Optimized {len(optimized_paths)} TIFFs for merging")

            output_filename = f"merged_{uuid.uuid4().hex}.jpg"
            output_path = tmp_dir / output_filename

            # Now merge the optimized TIFF files with ImageMagick
            cmd = [MAGICK_CMD] + optimized_paths + [
                "-evaluate-sequence", method,
                "-auto-level",
                "-quality", "95",
                str(output_path)
            ]

            app.logger.info("Running ImageMagick merge command...")
            completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=180)
            if completed.returncode != 0:
                err = completed.stderr or completed.stdout or "ImageMagick failed"
                print("MAGICK STDERR:", err)
                flash(f"ImageMagick error: {err}", "danger")
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return redirect(request.url)

            return render_template_string(
                RESULT_TEMPLATE,
                result_url=url_for('get_result_file', tmpdir=tmp_dir.name, filename=output_filename),
                output_name=output_filename,
                tmpdir=tmp_dir.name,
                urls=urls
            )
        except Exception as e:
            import traceback
            print("\n\n=== ERROR TRACEBACK START ===")
            traceback.print_exc()
            print("=== ERROR TRACEBACK END ===\n\n")
            flash(f"Error: {e}", "danger")
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return redirect(request.url)

    return render_template_string(INDEX_TEMPLATE)

@app.route('/result/<tmpdir>/<filename>')
def get_result_file(tmpdir, filename):
    safe_tmpdir = Path(tempfile.gettempdir()) / tmpdir
    file_path = safe_tmpdir / filename
    if not file_path.exists():
        return "File not found", 404
    return send_file(str(file_path), as_attachment=False, download_name=filename)

@app.route('/hdr-merge-api', methods=['POST'])
def hdr_merge_api():
    """
    API version of hdr_merge — accepts JSON payload with "images" (list of URLs)
    and optional "method" (mean, median, etc.), then returns the final merged HDR image.
    """
    try:
        data = request.get_json()
        urls = data.get('images', [])
        method = data.get('method', 'mean').lower()

        if not urls or not isinstance(urls, list):
            return jsonify({"error": "No valid image URLs provided"}), 400

        tmp_dir = Path(tempfile.mkdtemp(prefix="hdr_merge_api_"))
        saved_paths = []

        # Reuse your same DNG download + convert + merge logic:
        for url in urls:
            ext = Path(url.split('?')[0]).suffix
            if ext not in ALLOWED_EXTENSIONS:
                app.logger.warning(f"Skipping unsupported file type: {url}")
                continue
            app.logger.info(f"Downloading {url}")
            saved_paths.append(str(download_file(url, tmp_dir)))

        if not saved_paths:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return jsonify({"error": "No valid DNG files downloaded."}), 400

        # Convert DNG → TIFF using dcraw (same logic as your form-based route)
        converted_paths = []
        for dng_path in saved_paths:
            tiff_path = str(Path(dng_path).with_suffix('.tiff'))
            dcraw_cmd = ['dcraw', '-c', '-w', '-T', '-6', '-q', '3', dng_path]
            with open(tiff_path, 'wb') as f:
                result = subprocess.run(
                    dcraw_cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    timeout=60
                )
            if result.returncode == 0 and Path(tiff_path).exists():
                converted_paths.append(tiff_path)

        if not converted_paths:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return jsonify({"error": "Failed to convert DNG to TIFF."}), 500

        # Optimize TIFFs using ImageMagick
        optimized_paths = []
        for tiff_path in converted_paths:
            optimized_path = str(Path(tiff_path).with_suffix('.optimized.tiff'))
            optimize_cmd = [
                MAGICK_CMD, tiff_path,
                "-depth", "8",
                "-resize", "4096x4096>",
                "-compress", "LZW",
                optimized_path
            ]
            result = subprocess.run(optimize_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            if result.returncode == 0 and Path(optimized_path).exists():
                optimized_paths.append(optimized_path)
                Path(tiff_path).unlink(missing_ok=True)
            else:
                optimized_paths.append(tiff_path)

        # Merge TIFFs into HDR image using ImageMagick
        output_filename = f"merged_{uuid.uuid4().hex}.jpg"
        output_path = tmp_dir / output_filename

        merge_cmd = [MAGICK_CMD] + optimized_paths + [
            "-evaluate-sequence", method,
            "-auto-level",
            "-quality", "95",
            str(output_path)
        ]
        completed = subprocess.run(
            merge_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180
        )

        if completed.returncode != 0 or not output_path.exists():
            err = completed.stderr or completed.stdout or "ImageMagick merge failed"
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return jsonify({"error": err}), 500

        # ✅ Return final HDR image directly
        return send_file(output_path, mimetype='image/jpeg')

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/enhancement')
def enhancement():
    return render_template('index.html')

@app.route('/api/filters', methods=['GET'])
def get_filters():
    """Get list of available filters"""
    return jsonify(FILTERS_INFO)

@app.route('/api/upload', methods=['POST'])
def upload_image():
    """Handle image upload"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Use JPG, PNG, or BMP'}), 400
    
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower()
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}.{ext}")
        file.save(filepath)
        
        # Get image info
        img = Image.open(filepath)
        width, height = img.size
        file_size = os.path.getsize(filepath)
        
        # Convert to base64 for preview
        img.thumbnail((800, 800), Image.Resampling.LANCZOS)
        buffered = BytesIO()
        img.save(buffered, format=ext.upper() if ext != 'jpg' else 'JPEG')
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': filename,
            'width': width,
            'height': height,
            'size': file_size,
            'preview': f"data:image/{ext};base64,{img_str}"
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/apply-filter', methods=['POST'])
def apply_filter():
    """Apply filter to image"""
    data = request.json
    
    file_id = data.get('file_id')
    filter_name = data.get('filter')
    intensity = float(data.get('intensity', 1.0))
    
    if not file_id or not filter_name:
        return jsonify({'error': 'Missing file_id or filter'}), 400
    
    # Find the uploaded file
    filepath = None
    for ext in ['jpg', 'jpeg', 'png', 'bmp']:
        test_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}.{ext}")
        if os.path.exists(test_path):
            filepath = test_path
            break
    
    if not filepath:
        return jsonify({'error': 'File not found'}), 404
    
    # Start processing in background
    job_id = str(uuid.uuid4())
    processing_status[job_id] = {'status': 'processing', 'progress': 0}
    
    thread = threading.Thread(
        target=process_filter,
        args=(job_id, filepath, filter_name, intensity)
    )
    thread.start()
    
    return jsonify({
        'success': True,
        'job_id': job_id
    })

def process_filter(job_id, filepath, filter_name, intensity):
    """Process filter in background thread"""
    try:
        processing_status[job_id]['status'] = 'processing'
        processing_status[job_id]['progress'] = 10
        
        # Create filter instance
        filters = RealEstateFiltersEnhanced(filepath)
        
        processing_status[job_id]['progress'] = 30
        
        # Filter mapping
        filter_map = {
            'hdr-pro': filters.apply_hdr_pro,
            'luxury': filters.apply_luxury_estate,
            'modern': filters.apply_modern_minimal,
            'golden-hour': filters.apply_golden_hour,
            'crisp-clean': filters.apply_crisp_clean,
            'sky-dramatic': filters.apply_dramatic_sky,
            'sky-sunset': filters.replace_sky_sunset,
            'sky-blue': filters.replace_sky_blue,
            'cinematic': filters.apply_cinematic,
            'bright-airy': filters.apply_bright_airy,
            'vibrant': filters.apply_vibrant_pop,
            'soft-elegant': filters.apply_soft_elegance,
            'warm-natural': filters.apply_natural_warmth,
            'architectural': filters.apply_architectural,
            'moody': filters.apply_moody_dramatic,
            'magazine': filters.apply_magazine_editorial,
            'warm-sunset': filters.apply_warm_sunset_combo,
            'twilight': filters.apply_twilight_magic,
            'fresh-bright': filters.apply_fresh_bright,
            'balanced': filters.apply_balanced_pro,
        }
        
        processing_status[job_id]['progress'] = 50
        
        # Apply filter
        result_image = filter_map[filter_name](intensity=intensity)
        
        processing_status[job_id]['progress'] = 80
        
        # Save result
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_result.jpg")
        result_image.save(output_path, quality=98, optimize=False)
        
        # Create preview
        result_image.thumbnail((800, 800), Image.Resampling.LANCZOS)
        buffered = BytesIO()
        result_image.save(buffered, format='JPEG')
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        processing_status[job_id] = {
            'status': 'complete',
            'progress': 100,
            'preview': f"data:image/jpeg;base64,{img_str}",
            'output_path': output_path,
            'file_size': os.path.getsize(output_path)
        }
        
    except Exception as e:
        processing_status[job_id] = {
            'status': 'error',
            'error': str(e)
        }

@app.route('/api/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get processing status"""
    if job_id not in processing_status:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(processing_status[job_id])

@app.route('/api/download/<job_id>', methods=['GET'])
def download_result(job_id):
    """Download processed image"""
    if job_id not in processing_status:
        return jsonify({'error': 'Job not found'}), 404
    
    status = processing_status[job_id]
    
    if status['status'] != 'complete':
        return jsonify({'error': 'Processing not complete'}), 400
    
    output_path = status['output_path']
    
    if not os.path.exists(output_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(
        output_path,
        mimetype='image/jpeg',
        as_attachment=True,
        download_name='enhanced_image.jpg'
    )

if __name__ == '__main__':
    # Ensure binary exists before starting
    try:
        ensure_binary_exists()
    except Exception as e:
        logger.error(f"Failed to ensure binary exists: {e}")
        sys.exit(1)
    
    # Start the Flask app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Fisheye Stitcher Service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
