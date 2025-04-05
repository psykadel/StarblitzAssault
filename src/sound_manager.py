"""Sound management and playback system for the game."""

import os
import pygame
import random
from typing import Dict, Optional
from src.config import SOUNDS_DIR

class SoundManager:
    """Manages loading, caching, and playing game sound effects."""
    
    def __init__(self):
        """Initialize the sound manager and load sounds."""
        # Initialize the mixer with good settings for modern hardware
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        # Dictionary to cache loaded sounds
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        
        # Sound effects channels
        self.channels = {
            'player': pygame.mixer.Channel(0),  # Player weapons and effects
            'enemy': pygame.mixer.Channel(1),   # Enemy sounds
            'explosion': pygame.mixer.Channel(2), # Explosion sounds
            'powerup': pygame.mixer.Channel(3),  # Powerup sounds
            'ui': pygame.mixer.Channel(4)        # UI feedback sounds
        }
        
        # Set volume levels for channels
        for channel in self.channels.values():
            channel.set_volume(0.7)
        
        # Load sounds if they exist
        self._load_sounds()
    
    def _load_sounds(self):
        """Load sound files from the sounds directory."""
        if not os.path.exists(SOUNDS_DIR):
            print(f"Warning: Sounds directory not found at {SOUNDS_DIR}")
            return
            
        for filename in os.listdir(SOUNDS_DIR):
            if filename.endswith(('.wav', '.ogg')):
                try:
                    sound_path = os.path.join(SOUNDS_DIR, filename)
                    sound_name = os.path.splitext(filename)[0]
                    self.sounds[sound_name] = pygame.mixer.Sound(sound_path)
                    print(f"Loaded sound: {sound_name}")
                except pygame.error as e:
                    print(f"Error loading sound {filename}: {e}")
    
    def play(self, sound_name: str, channel_name: str = 'player') -> bool:
        """
        Play a sound on the specified channel.
        
        Args:
            sound_name: Name of the sound file (without extension)
            channel_name: Name of the channel to play on
            
        Returns:
            bool: True if the sound played successfully, False otherwise
        """
        if sound_name not in self.sounds:
            # Check if we have a generated sound
            if sound_name.startswith('gen_'):
                return False  # For now, we'll handle generated sounds separately
            print(f"Warning: Sound '{sound_name}' not found")
            return False
            
        if channel_name not in self.channels:
            print(f"Warning: Channel '{channel_name}' not found")
            return False
            
        self.channels[channel_name].play(self.sounds[sound_name])
        return True
    
    def stop_all(self):
        """Stop all playing sounds."""
        pygame.mixer.stop()
    
    def stop_channel(self, channel_name: str):
        """Stop sounds on a specific channel."""
        if channel_name in self.channels:
            self.channels[channel_name].stop()
    
    def set_volume(self, volume: float, channel_name: Optional[str] = None):
        """
        Set volume level for all channels or a specific channel.
        
        Args:
            volume: Volume level (0.0 to 1.0)
            channel_name: Channel to adjust or None for all channels
        """
        volume = max(0.0, min(1.0, volume))  # Clamp between 0 and 1
        
        if channel_name is None:
            # Set volume for all channels
            for channel in self.channels.values():
                channel.set_volume(volume)
        elif channel_name in self.channels:
            self.channels[channel_name].set_volume(volume)
        else:
            print(f"Warning: Channel '{channel_name}' not found") 