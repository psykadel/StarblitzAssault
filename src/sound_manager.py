"""Sound management and playback system for the game."""

import os
import pygame
import random
from typing import Dict, Optional
from config.game_config import SOUNDS_DIR, MUSIC_DIR, DEFAULT_SOUND_VOLUME, DEFAULT_MUSIC_VOLUME
from src.logger import get_logger

# Get a logger for this module
logger = get_logger(__name__)

class SoundManager:
    """Manages loading, caching, and playing game sound effects and music."""
    
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
            channel.set_volume(0.5)  # Default volume for all channels
        
        # Sound-specific volume settings - applied during sound loading
        self.sound_volume_settings = {
            'laser': 0.1,  # Very low volume for laser sound
            'explosion1': 0.5,
            'explosion2': 0.5,
            'hit1': 0.5,
            'powerup1': 0.5
        }
        
        # Current music track
        self.current_music: Optional[str] = None
        self.music_volume: float = 0.5  # Default music volume
        
        # Load sounds if they exist
        self._load_sounds()
    
    def _load_sounds(self):
        """Load sound files from the sounds directory."""
        if not os.path.exists(SOUNDS_DIR):
            print(f"Warning: Sounds directory not found at {SOUNDS_DIR}")
            return
            
        for filename in os.listdir(SOUNDS_DIR):
            if filename.endswith(('.ogg', '.wav')):
                try:
                    sound_path = os.path.join(SOUNDS_DIR, filename)
                    sound_name = os.path.splitext(filename)[0]
                    
                    # Special case for laser1/2/3 - map them all to "laser"
                    if sound_name in ['laser1', 'laser2', 'laser3']:
                        sound_name = 'laser'
                        # Only load once
                        if 'laser' in self.sounds:
                            continue
                    
                    # Load the sound
                    self.sounds[sound_name] = pygame.mixer.Sound(sound_path)
                    
                    # Apply sound-specific volume if defined
                    if sound_name in self.sound_volume_settings:
                        self.sounds[sound_name].set_volume(self.sound_volume_settings[sound_name])
                    
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
        # Map laser1/2/3 to just "laser"
        if sound_name in ['laser1', 'laser2', 'laser3']:
            sound_name = 'laser'
            
        if sound_name not in self.sounds:
            # Check if we have a generated sound
            if sound_name.startswith('gen_'):
                return False  # For now, we'll handle generated sounds separately
            print(f"Warning: Sound '{sound_name}' not found")
            return False
            
        if channel_name not in self.channels:
            print(f"Warning: Channel '{channel_name}' not found")
            return False
            
        # Just play the sound - volume is already set on the Sound object
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
    
    def set_sound_volume(self, sound_name: str, volume: float):
        """
        Set volume for a specific sound.
        
        Args:
            sound_name: Name of the sound
            volume: Volume level (0.0 to 1.0)
        """
        if sound_name in self.sounds:
            volume = max(0.0, min(1.0, volume))  # Clamp between 0 and 1
            self.sounds[sound_name].set_volume(volume)
            # Update the setting for future reference
            self.sound_volume_settings[sound_name] = volume
        else:
            print(f"Warning: Sound '{sound_name}' not found")
        
    def play_music(self, music_name: str, loops: int = -1, fade_ms: int = 1000) -> bool:
        """
        Play background music.
        
        Args:
            music_name: Filename (with extension) of the music file in the music directory
            loops: Number of times to repeat (-1 = infinite loop)
            fade_ms: Fade-in time in milliseconds
            
        Returns:
            bool: True if music started successfully, False otherwise
        """
        if not music_name:
            return False
            
        # Build the full path to the music file
        music_path = os.path.join(MUSIC_DIR, music_name)
        
        if not os.path.exists(music_path):
            print(f"Warning: Music file not found: {music_path}")
            return False
            
        try:
            # Stop any currently playing music with a fade-out
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(fade_ms)
                
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
            
            self.current_music = music_name
            print(f"Playing music: {music_name}")
            return True
        except pygame.error as e:
            print(f"Error playing music {music_name}: {e}")
            return False
    
    def stop_music(self, fade_ms: int = 1000):
        """
        Stop the currently playing music with a fade-out.
        
        Args:
            fade_ms: Fade-out time in milliseconds
        """
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(fade_ms)
            self.current_music = None
    
    def set_music_volume(self, volume: float):
        """
        Set the volume level for music.
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self.music_volume = max(0.0, min(1.0, volume))  # Clamp between 0 and 1
        pygame.mixer.music.set_volume(self.music_volume)
    
    def pause_music(self):
        """Pause the currently playing music."""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
    
    def unpause_music(self):
        """Unpause the currently paused music."""
        pygame.mixer.music.unpause() 