#!/usr/bin/env python
"""Simple sound generator for testing."""

import os
import math
import wave
import struct
import array
import random

# Set parameters
SAMPLE_RATE = 44100  # CD quality
MAX_AMPLITUDE = 32767  # 16-bit audio
SOUND_DIR = 'assets/sounds'

def ensure_dir_exists(directory):
    """Create directory if it doesn't exist."""
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
            print(f"Created directory: {directory}")
        except OSError as e:
            print(f"Error creating directory: {e}")
            return False
    return True

def generate_laser_sound(filename, duration=0.2, freq_start=880, freq_end=220):
    """Generate a simple laser sound and save as WAV."""
    # Ensure directory exists
    if not ensure_dir_exists(SOUND_DIR):
        return False
    
    filepath = os.path.join(SOUND_DIR, f"{filename}.wav")
    
    # Calculate number of frames/samples
    num_frames = int(SAMPLE_RATE * duration)
    
    # Create audio data (mono)
    audio_data = array.array('h', [0] * num_frames)
    
    # Generate simple frequency sweep
    for i in range(num_frames):
        t = i / SAMPLE_RATE
        # Linear frequency sweep
        freq = freq_start + (freq_end - freq_start) * (i / num_frames)
        # Simple sine wave with amplitude envelope
        amplitude = MAX_AMPLITUDE * (1.0 - i / num_frames) * 0.7
        audio_data[i] = int(amplitude * math.sin(2 * math.pi * freq * t))
    
    # Save to WAV file
    try:
        with wave.open(filepath, 'w') as wav_file:
            # Set parameters: channels, sample width, framerate, num frames, compression, compression name
            wav_file.setparams((1, 2, SAMPLE_RATE, num_frames, 'NONE', 'not compressed'))
            wav_file.writeframes(audio_data.tobytes())
        print(f"Saved sound to {filepath}")
        return True
    except (OSError, IOError) as e:
        print(f"Error saving sound file: {e}")
        return False

def generate_explosion_sound(filename, duration=0.5):
    """Generate a simple explosion sound and save as WAV."""
    # Ensure directory exists
    if not ensure_dir_exists(SOUND_DIR):
        return False
    
    filepath = os.path.join(SOUND_DIR, f"{filename}.wav")
    
    # Calculate number of frames/samples
    num_frames = int(SAMPLE_RATE * duration)
    
    # Create audio data (mono)
    audio_data = array.array('h', [0] * num_frames)
    
    # Generate noise with decay
    for i in range(num_frames):
        # Amplitude decreases over time
        amplitude = MAX_AMPLITUDE * (1.0 - (i / num_frames) ** 0.5) * 0.8
        # Random noise
        audio_data[i] = int(amplitude * random.uniform(-1.0, 1.0))
    
    # Save to WAV file
    try:
        with wave.open(filepath, 'w') as wav_file:
            wav_file.setparams((1, 2, SAMPLE_RATE, num_frames, 'NONE', 'not compressed'))
            wav_file.writeframes(audio_data.tobytes())
        print(f"Saved sound to {filepath}")
        return True
    except (OSError, IOError) as e:
        print(f"Error saving sound file: {e}")
        return False

def generate_powerup_sound(filename, duration=0.4, base_freq=440.0):
    """Generate a simple powerup sound and save as WAV."""
    # Ensure directory exists
    if not ensure_dir_exists(SOUND_DIR):
        return False
    
    filepath = os.path.join(SOUND_DIR, f"{filename}.wav")
    
    # Calculate number of frames/samples
    num_frames = int(SAMPLE_RATE * duration)
    
    # Create audio data (mono)
    audio_data = array.array('h', [0] * num_frames)
    
    # Generate ascending notes
    for i in range(num_frames):
        t = i / SAMPLE_RATE
        progress = i / num_frames
        
        # Different frequencies for different parts of the sound
        if progress < 0.33:
            freq = base_freq
        elif progress < 0.66:
            freq = base_freq * 1.25  # Major third
        else:
            freq = base_freq * 1.5  # Perfect fifth
        
        # Amplitude with slight fade-in and fade-out
        if progress < 0.1:
            amp = progress * 10  # Fade in
        elif progress > 0.8:
            amp = (1 - progress) * 5  # Fade out
        else:
            amp = 1.0
            
        amplitude = MAX_AMPLITUDE * 0.7 * amp
        audio_data[i] = int(amplitude * math.sin(2 * math.pi * freq * t))
    
    # Save to WAV file
    try:
        with wave.open(filepath, 'w') as wav_file:
            wav_file.setparams((1, 2, SAMPLE_RATE, num_frames, 'NONE', 'not compressed'))
            wav_file.writeframes(audio_data.tobytes())
        print(f"Saved sound to {filepath}")
        return True
    except (OSError, IOError) as e:
        print(f"Error saving sound file: {e}")
        return False

def generate_sounds():
    """Generate all game sounds."""
    # Generate laser variants
    generate_laser_sound("laser1", duration=0.2, freq_start=880, freq_end=220)
    generate_laser_sound("laser2", duration=0.15, freq_start=1100, freq_end=440)
    generate_laser_sound("laser3", duration=0.3, freq_start=660, freq_end=110)
    
    # Generate explosion variants
    generate_explosion_sound("explosion_small", duration=0.5)
    generate_explosion_sound("explosion_medium", duration=0.8)
    generate_explosion_sound("explosion_large", duration=1.0)
    
    # Generate powerup sounds
    generate_powerup_sound("powerup1", duration=0.4, base_freq=440)
    generate_powerup_sound("powerup2", duration=0.5, base_freq=523.25)
    
    print("Sound generation complete!")

if __name__ == "__main__":
    generate_sounds() 