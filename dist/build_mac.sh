#!/bin/bash

echo "Building Starblitz Assault Installer for macOS"
echo "=============================================="

# Create necessary directories
echo "Setting up build environment..."
mkdir -p .temp/pyinstaller

# Get absolute path to project root
PROJECT_ROOT="$(pwd)"

# Set environment variables for PyInstaller
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1

# Clean previous build files if they exist
if [ -d ".temp/pyinstaller" ]; then
    echo "Cleaning temporary PyInstaller directory..."
    rm -rf .temp/pyinstaller
    mkdir -p .temp/pyinstaller
fi
if [ -d "dist/StarblitzAssault.app" ]; then
    echo "Cleaning previous app..."
    rm -rf dist/StarblitzAssault.app
fi

# Get current architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

# Run PyInstaller
echo "Building installer with PyInstaller..."
python3 -m PyInstaller \
    --name=StarblitzAssault \
    --onefile \
    --windowed \
    --clean \
    --noconfirm \
    --workpath=.temp/pyinstaller \
    --specpath=.temp/pyinstaller \
    --distpath=dist \
    --add-data="${PROJECT_ROOT}/assets:assets" \
    --add-data="${PROJECT_ROOT}/config:config" \
    --icon="${PROJECT_ROOT}/starblitz-icon.icns" \
    --osx-bundle-identifier=com.starblitzassault.game \
    main.py

# Check if build was successful
if [ $? -ne 0 ]; then
    echo "Build failed with error code $?"
    exit $?
fi

# Make the installer executable
if [ -f dist/StarblitzAssault-macOS ]; then
    chmod +x dist/StarblitzAssault-macOS
    echo "Made macOS installer executable."
fi

# Clean build files
if [ -f "dist/StarblitzAssault" ]; then
    echo "Removing standalone executable..."
    rm -f dist/StarblitzAssault
fi

echo
echo "Installer build complete!"
echo "The installer can be found in the dist directory."
echo 