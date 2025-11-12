#!/bin/bash

# Script to organize files in a directory by their extension.
# It recursively finds all files and moves them into subdirectories
# named after their extension at the top level of the target directory.

TARGET_DIR="$1"

if [ -z "$TARGET_DIR" ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory '$TARGET_DIR' not found."
    exit 1
fi

echo "Organizing files in '$TARGET_DIR'..."

# Find all files, excluding hidden files
find "$TARGET_DIR" -type f -not -path '*/.*' | while read -r file; do
    # Get the extension
    extension="${file##*.}"
    
    # Check if there is an extension and it's not the file itself
    if [ "$extension" != "" ] && [ "$extension" != "$(basename "$file")" ]; then
        # Define the destination directory for this extension
        ext_dir="$TARGET_DIR/$extension"
        
        # Create the extension directory if it doesn't exist
        mkdir -p "$ext_dir"
        
        # Move the file
        echo "Moving '$file' to '$ext_dir/'"
        mv "$file" "$ext_dir/"
    fi
done

# Optional: Clean up empty directories left behind
echo "Cleaning up empty subdirectories..."
find "$TARGET_DIR" -mindepth 1 -type d -empty -delete

echo "Organization complete."
