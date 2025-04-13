#!/bin/bash

SOUNDS_DIR="assets/sounds"

# Find all MP3 files
MP3_FILES=$(find "$SOUNDS_DIR" -name "*.mp3")
COUNT=$(echo "$MP3_FILES" | wc -l)

echo "Found $COUNT MP3 files to convert."

# Convert each MP3 file to OGG
for MP3_FILE in $MP3_FILES; do
  OGG_FILE="${MP3_FILE%.mp3}.ogg"
  
  # Skip if OGG version already exists
  if [ -f "$OGG_FILE" ]; then
    echo "OGG version of $(basename "$MP3_FILE") already exists, skipping."
    continue
  fi
  
  echo "Converting $(basename "$MP3_FILE") to $(basename "$OGG_FILE")..."
  ffmpeg -loglevel error -i "$MP3_FILE" "$OGG_FILE"
  
  if [ $? -eq 0 ]; then
    echo "Conversion successful: $(basename "$OGG_FILE")"
  else
    echo "Error converting $(basename "$MP3_FILE")"
  fi
done

echo "Conversion complete!" 