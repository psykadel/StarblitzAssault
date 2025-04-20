#!/usr/bin/env python3
"""
Icon maker utility for StarblitzAssault
Converts a PNG image to Windows (.ico) and Mac (.icns) format icons
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path
from PIL import Image

def find_project_root() -> Path:
    """Find the project root directory (where starblitz-icon.png is located)"""
    current_dir = Path(__file__).parent.absolute()
    root_dir = current_dir.parent
    
    if not (root_dir / "starblitz-icon.png").exists():
        print("Error: starblitz-icon.png not found in the project root directory")
        sys.exit(1)
    
    return root_dir

def create_windows_icon(source_path: Path, output_path: Path) -> None:
    """Create Windows .ico file from PNG"""
    print(f"Creating Windows icon (.ico) from {source_path}")
    
    # Windows icons typically include multiple sizes
    sizes = [16, 32, 48, 64, 128, 256]
    
    try:
        img = Image.open(source_path)
        img.save(output_path, format="ICO", sizes=[(size, size) for size in sizes])
        print(f"Windows icon saved to {output_path}")
    except Exception as e:
        print(f"Error creating Windows icon: {e}")
        sys.exit(1)

def create_mac_icon(source_path: Path, output_path: Path) -> None:
    """Create Mac .icns file from PNG"""
    print(f"Creating Mac icon (.icns) from {source_path}")
    
    # macOS icons require multiple sized PNG files in a specific folder structure
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        iconset_path = temp_path / "icon.iconset"
        os.makedirs(iconset_path, exist_ok=True)
        
        # Mac icon sizes
        icon_sizes = [16, 32, 64, 128, 256, 512, 1024]
        
        try:
            img = Image.open(source_path)
            
            # Create different sized icons
            for size in icon_sizes:
                # Standard resolution
                resized_img = img.resize((size, size), Image.Resampling.LANCZOS)
                resized_img.save(iconset_path / f"icon_{size}x{size}.png")
                
                # High resolution (retina)
                if size <= 512:  # Don't create 2048x2048 image
                    resized_img = img.resize((size*2, size*2), Image.Resampling.LANCZOS)
                    resized_img.save(iconset_path / f"icon_{size}x{size}@2x.png")
            
            # Use iconutil to convert the iconset to icns (macOS only)
            if sys.platform == "darwin":
                subprocess.run(["iconutil", "-c", "icns", str(iconset_path), "-o", str(output_path)], check=True)
                print(f"Mac icon saved to {output_path}")
            else:
                print("Warning: Not running on macOS, skipping .icns creation (requires macOS)")
                print("The iconset has been created and can be manually converted on a Mac")
        except Exception as e:
            print(f"Error creating Mac icon: {e}")
            sys.exit(1)

def main():
    """Main function to create icons"""
    root_dir = find_project_root()
    source_png = root_dir / "starblitz-icon.png"
    
    # Output paths
    windows_icon_path = root_dir / "starblitz-icon.ico"
    mac_icon_path = root_dir / "starblitz-icon.icns"
    
    # Create icons
    create_windows_icon(source_png, windows_icon_path)
    create_mac_icon(source_png, mac_icon_path)
    
    print("\nIcon conversion complete!")
    print(f"Windows icon: {windows_icon_path}")
    print(f"Mac icon: {mac_icon_path}")

if __name__ == "__main__":
    main() 