#!/bin/bash

# MinerU Installation Script for DocForge MVP
# This script installs MinerU and its dependencies for PDF processing

set -e

echo "Installing MinerU for DocForge PDF processing..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Check Python version (MinerU requires Python 3.8+)
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python 3.8+ is required. Current version: $python_version"
    exit 1
fi

echo "Python version check passed: $python_version"

# Install system dependencies based on OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Installing Linux system dependencies..."
    sudo apt-get update
    sudo apt-get install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Installing macOS system dependencies..."
    if command -v brew &> /dev/null; then
        brew install opencv
    else
        echo "Warning: Homebrew not found. You may need to install OpenCV manually."
    fi
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "Windows detected. Please ensure Visual C++ redistributables are installed."
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install MinerU and dependencies
echo "Installing MinerU..."
pip install magic-pdf>=0.7.0

# Install additional dependencies
echo "Installing additional dependencies..."
pip install Pillow>=10.0.0 pandas>=2.0.0 numpy>=1.24.0

# Optional: Install OCR dependencies (commented out by default due to size)
# echo "Installing OCR dependencies (optional)..."
# pip install paddlepaddle>=2.5.0 paddleocr>=2.7.0

echo "Installation completed successfully!"
echo ""
echo "To use MinerU in your project:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Run your DocForge application"
echo ""
echo "Note: If you encounter issues, check the MinerU documentation:"
echo "https://github.com/opendatalab/MinerU"