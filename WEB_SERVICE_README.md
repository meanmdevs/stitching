# Fisheye Stitcher Web Service

A web service that provides fisheye image stitching as a service. This service takes dual fisheye camera images and creates panoramic stitched images.

## Features

-   **Web Interface**: User-friendly web interface for uploading and processing images
-   **REST API**: Programmatic access via HTTP API
-   **Docker Support**: Containerized for easy deployment
-   **Render.com Ready**: Pre-configured for deployment on Render.com

## API Endpoints

### Web Interface

-   `GET /` - Main web interface for uploading images

### API Endpoints

-   `POST /stitch` - Stitch a dual fisheye image

    -   **Content-Type**: `multipart/form-data`
    -   **Body**: Image file (dual fisheye image)
    -   **Response**: Stitched panoramic image (JPEG)

-   `GET /health` - Health check endpoint
-   `GET /info` - Service information

## Local Development

### Prerequisites

-   Docker
-   Python 3.8+
-   OpenCV
-   CMake
-   C++17 compiler

### Running Locally

1. **Using Docker (Recommended)**:

    ```bash
    # Build the Docker image
    docker build -t fisheye-stitcher .

    # Run the container
    docker run -p 5000:5000 fisheye-stitcher
    ```

2. **Using Python directly**:

    ```bash
    # Install dependencies
    pip install -r requirements.txt

    # Build the C++ binary
    mkdir build && cd build
    cmake .. && make -j4
    cd ..

    # Run the Flask app
    python app.py
    ```

3. **Access the service**:
    - Web Interface: http://localhost:5000
    - API: http://localhost:5000/stitch

## Deployment to Render.com

### Using Docker (Recommended)

1. **Connect your repository** to Render.com
2. **Create a new Web Service**:

    - Environment: Docker
    - Dockerfile Path: `./Dockerfile`
    - Plan: Starter or higher
    - Region: Choose your preferred region

3. **Deploy**: Render will automatically build and deploy your service

### Using render.yaml

The `render.yaml` file is pre-configured for easy deployment:

```bash
# Push your code to GitHub/GitLab
git add .
git commit -m "Add web service"
git push origin main

# Connect repository to Render.com
# Render will automatically detect render.yaml and deploy
```

## Usage Examples

### Web Interface

1. Open the web interface at your deployed URL
2. Upload a dual fisheye image
3. Click "Stitch Image"
4. Download the resulting panoramic image

### API Usage

**cURL Example**:

```bash
curl -X POST \
  -F "image=@your_dual_fisheye_image.jpg" \
  https://your-service-url.onrender.com/stitch \
  --output stitched_image.jpg
```

**Python Example**:

```python
import requests

url = "https://your-service-url.onrender.com/stitch"
files = {"image": open("dual_fisheye_image.jpg", "rb")}

response = requests.post(url, files=files)
if response.status_code == 200:
    with open("stitched_image.jpg", "wb") as f:
        f.write(response.content)
    print("Stitching completed!")
else:
    print(f"Error: {response.text}")
```

**JavaScript Example**:

```javascript
const formData = new FormData()
formData.append('image', fileInput.files[0])

fetch('https://your-service-url.onrender.com/stitch', {
    method: 'POST',
    body: formData,
})
    .then((response) => response.blob())
    .then((blob) => {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'stitched_image.jpg'
        a.click()
    })
```

## Image Requirements

-   **Format**: JPEG, PNG, or other OpenCV-supported formats
-   **Size**: Minimum 1000x500 pixels
-   **Aspect Ratio**: Approximately 2:1 (width:height) for dual fisheye images
-   **Content**: Should contain two fisheye images side by side

## Performance

-   **Processing Time**: Typically 1-3 seconds per image
-   **Memory Usage**: ~200-500MB per request
-   **Concurrent Requests**: Supports multiple simultaneous requests
-   **Timeout**: 60 seconds per request

## Troubleshooting

### Common Issues

1. **Build Failures**:

    - Ensure all dependencies are installed
    - Check that OpenCV is properly installed
    - Verify C++17 compiler support

2. **Image Processing Errors**:

    - Verify image format and size
    - Check that the image contains dual fisheye content
    - Ensure sufficient memory is available

3. **Deployment Issues**:
    - Check Render.com logs for build errors
    - Verify all required files are included
    - Ensure Dockerfile is in the root directory

### Health Check

The service includes a health check endpoint at `/health` that returns:

```json
{
    "status": "healthy",
    "binary_exists": true,
    "mls_map_exists": true
}
```

## License

This project is licensed under the same license as the original fisheyeStitcher project.

## Support

For issues related to:

-   **Web Service**: Check the logs and health endpoint
-   **Core Stitching**: Refer to the original fisheyeStitcher documentation
-   **Deployment**: Check Render.com documentation and logs
