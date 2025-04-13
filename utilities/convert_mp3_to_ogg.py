import os
from pydub import AudioSegment

def convert_mp3_to_ogg():
    """Convert all MP3 files in assets/sounds to OGG format."""
    sounds_dir = "assets/sounds"
    
    # Get all MP3 files
    mp3_files = [f for f in os.listdir(sounds_dir) if f.endswith('.mp3')]
    
    if not mp3_files:
        print("No MP3 files found in the sounds directory.")
        return
    
    print(f"Found {len(mp3_files)} MP3 files to convert.")
    
    for mp3_file in mp3_files:
        mp3_path = os.path.join(sounds_dir, mp3_file)
        ogg_file = os.path.splitext(mp3_file)[0] + '.ogg'
        ogg_path = os.path.join(sounds_dir, ogg_file)
        
        # Skip if OGG version already exists
        if os.path.exists(ogg_path):
            print(f"OGG version of {mp3_file} already exists, skipping.")
            continue
        
        try:
            # Load MP3 and export as OGG
            sound = AudioSegment.from_mp3(mp3_path)
            sound.export(ogg_path, format="ogg")
            print(f"Converted {mp3_file} to {ogg_file}")
        except Exception as e:
            print(f"Error converting {mp3_file}: {e}")

if __name__ == "__main__":
    convert_mp3_to_ogg() 