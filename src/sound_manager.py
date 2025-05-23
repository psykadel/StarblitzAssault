"""Sound manager for the game."""

import os
from typing import Dict, Optional

import pygame

from config.config import DEFAULT_SOUND_VOLUME, MUSIC_DIR, SOUNDS_DIR, DEBUG_MUTE_MUSIC
from src.logger import get_logger

# Get a logger for this module
logger = get_logger(__name__)


class SoundManager:
    """Manages game sound effects and music."""

    def __init__(self) -> None:
        """Initialize the sound manager."""
        # Dictionary to store loaded sounds
        self.sounds: Dict[str, Dict[str, pygame.mixer.Sound]] = {"player": {}, "enemy": {}}
        # Dictionary to store sound durations (in milliseconds)
        self.sound_durations: Dict[str, Dict[str, int]] = {"player": {}, "enemy": {}}
        
        # Track currently looping sounds to stop them when needed
        self.looping_sounds: Dict[str, Dict[str, pygame.mixer.Channel]] = {"player": {}, "enemy": {}}

        # Ensure pygame mixer is initialized
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        # Create sounds directory if it doesn't exist
        os.makedirs(SOUNDS_DIR, exist_ok=True)

        # Current volume settings - these must be set BEFORE loading sounds
        self.volume = DEFAULT_SOUND_VOLUME
        self.music_volume = DEFAULT_SOUND_VOLUME
        self.current_music = None

        # Load sound effects
        self._load_sounds()

    def _load_sounds(self) -> None:
        """Load all sound effects into memory."""
        # Create silent fallbacks for all required sounds
        self._create_silent_sound("laser", "player")
        self._create_silent_sound("explosion1", "player")
        self._create_silent_sound("powerup", "player")
        self._create_silent_sound("flamethrower", "player")  # Add flamethrower fallback
        self._create_silent_sound("flamethrower1", "player")  # Add flamethrower1 fallback
        self._create_silent_sound("silent", "player")  # Special silent sound for stopping effects
        self._create_silent_sound("laserbeam", "player")  # Add laserbeam fallback

        self._create_silent_sound("laser", "enemy")
        self._create_silent_sound("explosion2", "enemy")
        self._create_silent_sound("powerup", "enemy")  # Fallback sound for enemy powerup

        # Try to load actual sound files - use .ogg files
        self._try_load_sound("laser", "laser1.ogg", "player")
        self._try_load_sound("explosion1", "explosion1.ogg", "player")
        self._try_load_sound("powerup", "powerup1.ogg", "player")
        self._try_load_sound("flamethrower", "laser1.ogg", "player")
        self._try_load_sound("flamethrower1", "flamethrower1.ogg", "player")  # Dedicated flamethrower sound
        self._try_load_sound("laserbeam", "laserbeam1.ogg", "player")  # Load looping laser beam sound
        self._try_load_sound("shiphit1", "shiphit1.ogg", "player")  # Load player hit sound

        # Use player powerup sound for enemy too
        self._try_load_sound("explosion2", "explosion2.ogg", "enemy")
        self._try_load_sound("powerup1", "powerup1.ogg", "enemy")
        self._try_load_sound("bossexplode1", "bossexplode1.ogg", "enemy")  # Load boss explosion sound
        self._try_load_sound("siren1", "siren1.ogg", "enemy")  # Load siren sound for boss intro

    def _create_silent_sound(self, name: str, category: str) -> None:
        """Create a silent sound as a fallback.

        Args:
            name: Reference name for the sound
            category: Category the sound belongs to
        """
        try:
            # Create a silent sound (1 second of silence)
            # Use a buffer with proper format for pygame: 44100Hz, 16-bit, mono
            buffer_size = 44100 * 2  # 1 second of 16-bit mono audio
            silence_buffer = bytearray(buffer_size)
            silent_sound = pygame.mixer.Sound(buffer=bytes(silence_buffer))
            silent_sound.set_volume(0.01)  # Set to very low volume instead of zero
            self.sounds[category][name] = silent_sound
            logger.debug(f"Created silent fallback for {category}/{name}")
        except Exception as e:
            logger.error(f"Failed to create silent sound: {e}")
            # Create the smallest possible sound buffer as last resort
            try:
                minimal_buffer = bytearray(32)  # Smallest possible buffer
                minimal_sound = pygame.mixer.Sound(buffer=bytes(minimal_buffer))
                minimal_sound.set_volume(0)  # Mute it completely
                self.sounds[category][name] = minimal_sound
                logger.debug(f"Created minimal fallback for {category}/{name}")
            except Exception as e2:
                logger.error(f"Failed to create even minimal sound: {e2}")
                # If we really can't create any sound, log it but don't crash

    def _try_load_sound(self, name: str, filename: str, category: str = "player") -> None:
        """Try to load a sound file, using fallback if it doesn't exist.

        Args:
            name: Reference name for the sound
            filename: Filename of the sound file
            category: Category the sound belongs to
        """
        # First try the exact filename
        sound_path = os.path.join(SOUNDS_DIR, filename)

        # If not found, try with .ogg extension (many sound files are in .ogg format)
        if not os.path.exists(sound_path):
            # Get the filename without extension
            basename = os.path.splitext(filename)[0]
            ogg_filename = f"{basename}.ogg"
            ogg_path = os.path.join(SOUNDS_DIR, ogg_filename)

            if os.path.exists(ogg_path):
                sound_path = ogg_path
                logger.info(f"Using OGG version of sound: {ogg_filename}")
            else:
                logger.warning(
                    f"Sound file not found: {sound_path} or {ogg_path} - using silent fallback"
                )
                return

        try:
            sound = pygame.mixer.Sound(sound_path)
            # Set volume higher for sound effects to make them more audible
            sound.set_volume(self.volume * 1.5)
            self.sounds[category][name] = sound
            # Store duration in milliseconds
            duration_ms = int(sound.get_length() * 1000)
            if category not in self.sound_durations:
                self.sound_durations[category] = {}
            self.sound_durations[category][name] = duration_ms
            logger.debug(f"Loaded sound: {os.path.basename(sound_path)} as {category}/{name} (Duration: {duration_ms}ms)")
        except pygame.error as e:
            logger.error(f"Failed to load sound {filename}: {e} - using silent fallback")

    def play(self, name: str, category: str = "player", volume: Optional[float] = None, fadeout_ms: int = 0) -> None:
        """Play a sound effect.

        Args:
            name: Name of the sound to play
            category: Category the sound belongs to
            volume: Optional volume override for this play only
            fadeout_ms: Optional fadeout time in milliseconds for currently playing instances
        """
        # First make sure the category exists
        if category not in self.sounds:
            logger.warning(f"Sound category {category} not found")
            return

        # If we need to fadeout other instances of this sound before playing
        if fadeout_ms > 0 and name in self.sounds[category]:
            try:
                # Fadeout previous instances of this sound
                self.sounds[category][name].fadeout(fadeout_ms)
            except Exception as e:
                logger.warning(f"Failed to fadeout sound {category}/{name}: {e}")

        # Check if the sound exists and is not None
        if name in self.sounds[category] and self.sounds[category][name] is not None:
            try:
                # Stop the sound if it's already playing to make it start over immediately
                self.sounds[category][name].stop()
                
                # Temporarily boost volume for this play
                current_volume = self.sounds[category][name].get_volume()
                
                # Use override volume if provided
                if volume is not None:
                    self.sounds[category][name].set_volume(volume)
                # Make sure laser sounds are much quieter
                elif name == "laser":
                    # For laser sounds, set a fixed volume rather than multiplying the current volume
                    # This prevents volume decay over repeated plays
                    self.sounds[category][name].set_volume(self.volume * 0.25)  # 25% of base volume
                else:
                    self.sounds[category][name].set_volume(min(1.0, current_volume * 1.5))

                # Adjust volume for flamethrower1 sound to be slightly lower
                if name == "flamethrower1":
                    self.sounds[category][name].set_volume(min(0.8, current_volume))

                # Play the sound
                self.sounds[category][name].play()

                # Reset to original volume after a short delay (we'll let mixer handle this)
                return
            except pygame.error as e:
                logger.error(f"Failed to play sound {category}/{name}: {e}")
                # Continue to try fallbacks

        # If we get here, either the sound doesn't exist or playing it failed
        # Try to use a fallback
        fallbacks = {
            "beam": "laser", 
            "scatter": "explosion1",
            "flamethrower": "laser",  # Fallback sound for flamethrower (uses laser)
            "flamethrower1": "flamethrower"  # Fallback to regular flamethrower sound
        }

        # Check if we have a fallback
        if name in fallbacks:
            fallback_name = fallbacks[name]
            if (
                fallback_name in self.sounds[category]
                and self.sounds[category][fallback_name] is not None
            ):
                try:
                    # Stop the fallback sound if it's already playing
                    self.sounds[category][fallback_name].stop()
                    self.sounds[category][fallback_name].play()
                    logger.debug(f"Used fallback sound {fallback_name} for {name}")
                    return
                except pygame.error as e:
                    logger.error(f"Failed to play fallback sound {category}/{fallback_name}: {e}")

        logger.warning(f"Sound {category}/{name} not found and no fallback available")

    def set_volume(self, volume: float) -> None:
        """Set the volume for all sounds.

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        # Clamp volume to valid range
        self.volume = max(0.0, min(1.0, volume))

        # Update all loaded sounds
        for category in self.sounds:
            for sound in self.sounds[category].values():
                sound.set_volume(self.volume)

    def play_music(self, music_name: str, loops: int = -1, fade_ms: int = 1000) -> bool:
        """Play background music.

        Args:
            music_name: Filename of the music file
            loops: Number of times to repeat (-1 = infinite loop)
            fade_ms: Fade-in time in milliseconds

        Returns:
            bool: True if music started successfully, False otherwise
        """
        # Check the debug flag first
        if DEBUG_MUTE_MUSIC:
            logger.info("Music muted due to DEBUG_MUTE_MUSIC flag.")
            # Stop any currently playing music if muted
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()  # Unload to be sure
            self.current_music = None
            return False

        if not music_name:
            return False

        # Create music directory if it doesn't exist
        os.makedirs(MUSIC_DIR, exist_ok=True)

        # Build the full path to the music file
        music_path = os.path.join(MUSIC_DIR, music_name)

        if not os.path.exists(music_path):
            logger.warning(f"Music file not found: {music_path}")
            return False

        try:
            # Stop any currently playing music with a fade-out
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(fade_ms)

            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)

            self.current_music = music_name
            logger.info(f"Playing music: {music_name}")
            return True
        except pygame.error as e:
            logger.error(f"Error playing music {music_name}: {e}")
            return False

    def set_music_volume(self, volume: float) -> None:
        """Set the volume level for music.

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self.music_volume = max(0.0, min(1.0, volume))  # Clamp between 0 and 1
        pygame.mixer.music.set_volume(self.music_volume)

    def pause_music(self) -> None:
        """Pause the currently playing music."""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()

    def unpause_music(self) -> None:
        """Unpause the currently paused music."""
        pygame.mixer.music.unpause()

    def stop_music(self, fade_ms: int = 1000) -> None:
        """Stop the currently playing music with a fade-out.

        Args:
            fade_ms: Fade-out time in milliseconds
        """
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(fade_ms)
            self.current_music = None

    def play_loop(self, name: str, category: str = "player", volume: Optional[float] = None) -> None:
        """Play a sound effect in a loop until explicitly stopped.
        
        Args:
            name: Name of the sound to play in a loop
            category: Category the sound belongs to
            volume: Optional volume override
        """
        # First make sure the category exists
        if category not in self.sounds:
            logger.warning(f"Sound category {category} not found")
            return
        
        # Check if the sound exists and is not None
        if name in self.sounds[category] and self.sounds[category][name] is not None:
            try:
                # Find an available channel for the looping sound
                # Look for a free channel starting from channel 1 (reserving channel 0 for non-looping sounds)
                for channel_id in range(1, pygame.mixer.get_num_channels()):
                    channel = pygame.mixer.Channel(channel_id)
                    if not channel.get_busy():
                        # Apply volume settings
                        sound = self.sounds[category][name]
                        loop_volume = volume if volume is not None else self.volume * 0.6  # Default to 60% of normal volume for loops
                        sound.set_volume(loop_volume)
                        
                        # Start looping and store the channel for later reference
                        channel.play(sound, loops=-1)  # Loop indefinitely
                        
                        # Store the channel for later reference to stop it
                        if category not in self.looping_sounds:
                            self.looping_sounds[category] = {}
                        self.looping_sounds[category][name] = channel
                        
                        logger.debug(f"Started looping sound {category}/{name} on channel {channel_id}")
                        return
                
                # If we get here, no free channel was found
                logger.warning(f"No free channel available for looping sound {category}/{name}")
                return
                
            except pygame.error as e:
                logger.error(f"Failed to play looping sound {category}/{name}: {e}")
                
        # If we get here, either the sound doesn't exist or playing it failed
        # Try to use a fallback
        fallbacks = {
            "laserbeam": "laser"
        }
        
        # Check if we have a fallback
        if name in fallbacks:
            fallback_name = fallbacks[name]
            self.play_loop(fallback_name, category, volume)  # Try playing the fallback in a loop
        else:
            logger.warning(f"Looping sound {category}/{name} not found and no fallback available")
    
    def stop_loop(self, name: str, category: str = "player", fade_ms: int = 0) -> None:
        """Stop a looping sound.
        
        Args:
            name: Name of the sound to stop
            category: Category the sound belongs to
            fade_ms: Optional fadeout time in milliseconds
        """
        # Check if we have a record of this looping sound
        if (category in self.looping_sounds and 
            name in self.looping_sounds[category] and 
            self.looping_sounds[category][name] is not None):
            
            channel = self.looping_sounds[category][name]
            
            try:
                if fade_ms > 0:
                    channel.fadeout(fade_ms)
                else:
                    channel.stop()
                
                # Remove the channel reference
                del self.looping_sounds[category][name]
                logger.debug(f"Stopped looping sound {category}/{name}")
            except Exception as e:
                logger.error(f"Failed to stop looping sound {category}/{name}: {e}")
        else:
            logger.debug(f"No looping sound found to stop: {category}/{name}")

    def get_sound_duration(self, name: str, category: str = "player") -> Optional[int]:
        """Get the duration of a loaded sound in milliseconds.

        Args:
            name: Name of the sound
            category: Category of the sound

        Returns:
            Optional[int]: Duration in milliseconds, or None if not found.
        """
        return self.sound_durations.get(category, {}).get(name)
