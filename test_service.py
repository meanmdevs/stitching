#!/usr/bin/env python3
"""
Test script for the Fisheye Stitcher Web Service
"""

import os
import sys
import tempfile
import requests
from pathlib import Path

def test_local_service():
    """Test the service running locally"""
    print("Testing Fisheye Stitcher Web Service...")
    
    # Check if we have a test image
    test_image_path = Path("input/image.jpg")
    if not test_image_path.exists():
        print("❌ No test image found at input/image.jpg")
        print("Please ensure you have a dual fisheye test image")
        return False
    
    print(f"✅ Found test image: {test_image_path}")
    
    # Test health endpoint
    try:
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check passed: {health_data}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Service not running. Please start the service first:")
        print("   python3 app.py")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False
    
    # Test info endpoint
    try:
        response = requests.get("http://localhost:5000/info", timeout=5)
        if response.status_code == 200:
            info_data = response.json()
            print(f"✅ Service info: {info_data['service']} v{info_data['version']}")
        else:
            print(f"❌ Info endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Info endpoint error: {e}")
    
    # Test stitching endpoint
    try:
        print("🔄 Testing stitching endpoint...")
        with open(test_image_path, 'rb') as f:
            files = {'image': f}
            response = requests.post("http://localhost:5000/stitch", files=files, timeout=30)
        
        if response.status_code == 200:
            # Save the result
            output_path = "test_stitched_output.jpg"
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"✅ Stitching successful! Output saved to: {output_path}")
            return True
        else:
            print(f"❌ Stitching failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Stitching test error: {e}")
        return False

def test_docker_build():
    """Test Docker build process"""
    print("\nTesting Docker build...")
    
    # Check if Docker is available
    try:
        import subprocess
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Docker available: {result.stdout.strip()}")
        else:
            print("❌ Docker not available")
            return False
    except FileNotFoundError:
        print("❌ Docker not installed")
        return False
    
    # Test Docker build
    try:
        print("🔄 Building Docker image...")
        result = subprocess.run(["docker", "build", "-t", "fisheye-stitcher-test", "."], 
                              capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print("✅ Docker build successful!")
            return True
        else:
            print(f"❌ Docker build failed:")
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("❌ Docker build timed out")
        return False
    except Exception as e:
        print(f"❌ Docker build error: {e}")
        return False

if __name__ == "__main__":
    print("Fisheye Stitcher Web Service Test Suite")
    print("=" * 50)
    
    # Test local service
    local_success = test_local_service()
    
    # Test Docker build
    docker_success = test_docker_build()
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Local Service: {'✅ PASS' if local_success else '❌ FAIL'}")
    print(f"Docker Build:  {'✅ PASS' if docker_success else '❌ FAIL'}")
    
    if local_success and docker_success:
        print("\n🎉 All tests passed! Your service is ready for deployment.")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        sys.exit(1)
