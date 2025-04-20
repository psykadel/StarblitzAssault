#!/bin/bash

echo "Building Starblitz Assault Installer for macOS"
echo "=============================================="

# Create necessary directories
echo "Setting up build environment..."
mkdir -p .temp/pyinstaller
mkdir -p .temp/dmg_build

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
if [ -d "dist/Starblitz Assault.app" ]; then
    echo "Cleaning previous app..."
    rm -rf "dist/Starblitz Assault.app"
fi
if [ -f "dist/Starblitz Assault" ]; then
    echo "Cleaning previous executable..."
    rm -f "dist/Starblitz Assault"
fi
if [ -f "dist/StarblitzAssault-macOS.dmg" ]; then
    echo "Cleaning previous DMG..."
    rm -f "dist/StarblitzAssault-macOS.dmg"
fi

# Get current architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

# Run PyInstaller
echo "Building installer with PyInstaller..."
python3 -m PyInstaller \
    --name="Starblitz Assault" \
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

# Create the DMG file
echo "Creating DMG file..."
DMG_NAME="StarblitzAssault-macOS.dmg"
DMG_PATH="dist/${DMG_NAME}"
APP_PATH="dist/Starblitz Assault.app"

# Create a temporary directory for DMG contents
DMG_TEMP_DIR=".temp/dmg_build"
rm -rf "${DMG_TEMP_DIR}"
mkdir -p "${DMG_TEMP_DIR}"

# Copy the app to the temporary directory
cp -R "${APP_PATH}" "${DMG_TEMP_DIR}/"

# Create symlink to Applications folder
ln -s /Applications "${DMG_TEMP_DIR}/Applications"

# Create the DMG using a temporary sparse image to avoid space issues
SPARSE_IMAGE=".temp/tmp_starblitz.sparseimage"
VOLUME_NAME="Starblitz Assault"

# Remove existing sparse image if it exists
if [ -f "${SPARSE_IMAGE}" ]; then
    rm -f "${SPARSE_IMAGE}"
fi

# Calculate needed size (app size + 20MB buffer)
APP_SIZE=$(du -sm "${APP_PATH}" | cut -f1)
DMG_SIZE=$((APP_SIZE + 20))

# Create a temporary sparse image
hdiutil create -size ${DMG_SIZE}m -type SPARSE -fs HFS+ -volname "${VOLUME_NAME}" "${SPARSE_IMAGE}"

# Mount the sparse image
hdiutil attach "${SPARSE_IMAGE}" -mountpoint "/Volumes/${VOLUME_NAME}"

# Copy the contents to the mounted image
cp -R "${DMG_TEMP_DIR}"/* "/Volumes/${VOLUME_NAME}/"

# Unmount the image
hdiutil detach "/Volumes/${VOLUME_NAME}" -force

# Convert the sparse image to compressed DMG
hdiutil convert "${SPARSE_IMAGE}" -format UDZO -o "${DMG_PATH}"

# Clean up
rm -f "${SPARSE_IMAGE}"
rm -rf "${DMG_TEMP_DIR}"

echo
echo "Build complete!"
echo "The app bundle can be found at: dist/Starblitz Assault.app"
echo "The DMG installer can be found at: dist/StarblitzAssault-macOS.dmg"
echo
