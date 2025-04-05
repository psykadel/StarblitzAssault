#!/usr/bin/env python
"""
Sound Effects Generator for Starblitz Assault

This script generates procedural sound effects for the game.
Run this script to generate all necessary game sounds.
"""

import os
import sys

# Add the root directory to the path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.utils.sound_generator import SoundGenerator
except ImportError as e:
    print(f"Error importing SoundGenerator: {e}")
    print("Make sure to run this script from the project root or assets directory.")
    sys.exit(1)

def main():
    print("Starblitz Assault - Sound Effects Generator")
    print("------------------------------------------")
    
    # Create sound generator
    generator = SoundGenerator()
    
    # Generate all sounds
    print("Generating sound effects...")
    generated_files = generator.generate_all_sounds()
    
    # Report results
    if generated_files:
        print(f"\nSuccessfully generated {len(generated_files)} sound effects:")
        for file_path in generated_files:
            print(f"  - {os.path.basename(file_path)}")
        print("\nAll sounds have been saved to the assets/sounds directory.")
    else:
        print("\nNo sound effects were generated. Check for errors above.")
    
    print("\nYou can now use these sounds in the game!")

if __name__ == "__main__":
    main() 