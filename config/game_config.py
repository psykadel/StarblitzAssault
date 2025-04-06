"""Game configuration settings."""

from typing import Tuple, Optional, Dict, Any
import os
import pygame

# Base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
SPRITES_DIR = os.path.join(ASSETS_DIR, 'sprites')
SOUNDS_DIR = os.path.join(ASSETS_DIR, 'sounds')
MUSIC_DIR = os.path.join(ASSETS_DIR, 'music')
IMAGES_DIR = os.path.join(ASSETS_DIR, 'images')
BACKGROUNDS_DIR = os.path.join(ASSETS_DIR, 'backgrounds')

# Screen dimensions
SCREEN_WIDTH: int = 1024
SCREEN_HEIGHT: int = 600

# Playfield boundaries (Y-axis)
PLAYFIELD_TOP_Y: int = 75
PLAYFIELD_BOTTOM_Y: int = SCREEN_HEIGHT - 75

# Frame rate
FPS: int = 60

# Player settings
PLAYER_SPEED: float = 5.0
PLAYER_SHOOT_DELAY: int = 200  # milliseconds
PLAYER_SCALE_FACTOR: float = 0.25
PLAYER_ANIMATION_SPEED_MS: int = 75  # Milliseconds per frame

# Enemy settings
ENEMY_SPAWN_RATE: int = 1000  # milliseconds
WAVE_DELAY_MS: int = 5000  # Time between enemy waves (milliseconds)
ENEMY1_SCALE_FACTOR: float = 0.20
ENEMY1_ANIMATION_SPEED_MS: int = 100  # Animation speed
ENEMY1_SPEED_X: float = -3.0  # Pixels per frame (moving left)
ENEMY_SHOOTER_COOLDOWN_MS: int = 1500  # milliseconds between shots

# Animation settings
DEFAULT_ANIMATION_SPEED_MS: int = 75  # Milliseconds per frame

# Sprite sheet settings
DEFAULT_SPRITE_SHEET_GRID: Tuple[int, int] = (3, 3)
DEFAULT_CROP_BORDER_PIXELS: int = 2

# Colors
WHITE: Tuple[int, int, int] = (255, 255, 255)
BLACK: Tuple[int, int, int] = (0, 0, 0)
RED: Tuple[int, int, int] = (255, 0, 0)
GREEN: Tuple[int, int, int] = (0, 255, 0)
BLUE: Tuple[int, int, int] = (0, 0, 255)
YELLOW: Tuple[int, int, int] = (255, 255, 0)

# Font settings
DEFAULT_FONT_SIZE: int = 24
DEFAULT_FONT_NAME: Optional[str] = None  # Use default pygame font

# Sound settings
DEFAULT_SOUND_VOLUME: float = 0.5
DEFAULT_MUSIC_VOLUME: float = 0.3

# Event types
WAVE_TIMER_EVENT_ID: int = pygame.USEREVENT + 1

# Pattern types for enemy waves
PATTERN_TYPES = {
    "VERTICAL": 0,    # Enemies in a straight vertical line
    "HORIZONTAL": 1,  # Enemies in a straight horizontal line
    "DIAGONAL": 2,    # Enemies in a diagonal line
    "V_SHAPE": 3      # Enemies in a V formation
}
PATTERN_COUNT: int = 4  # Total number of patterns 