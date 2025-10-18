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
from flask import Flask, request, jsonify, send_file, render_template_string
from werkzeug.utils import secure_filename
import cv2
import numpy as np
from PIL import Image
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configuration
PROJECT_ROOT = Path(__file__).parent
BUILD_DIR = PROJECT_ROOT / "build"
BINARY_PATH = BUILD_DIR / "bin" / "fisheyeStitcher"
UTILS_DIR = PROJECT_ROOT / "utils"
MLS_MAP_PATH = UTILS_DIR / "grid_xd_yd_3840x1920.yml.gz"

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
