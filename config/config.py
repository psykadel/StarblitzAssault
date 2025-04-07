"""Centralized game configuration settings."""

import os
import pygame
import logging
from typing import Dict, List, Tuple, Optional

#------------------------------------------------------------------------------
# LOGGING SETTINGS
#------------------------------------------------------------------------------
# Can be set to logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, or logging.CRITICAL
LOG_LEVEL: int = logging.WARNING

#------------------------------------------------------------------------------
# DIRECTORY PATHS
#------------------------------------------------------------------------------
# Base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
SPRITES_DIR = os.path.join(ASSETS_DIR, 'sprites')
SOUNDS_DIR = os.path.join(ASSETS_DIR, 'sounds')
MUSIC_DIR = os.path.join(ASSETS_DIR, 'music')
IMAGES_DIR = os.path.join(ASSETS_DIR, 'images')
BACKGROUNDS_DIR = os.path.join(ASSETS_DIR, 'backgrounds')

#------------------------------------------------------------------------------
# SCREEN AND DISPLAY SETTINGS
#------------------------------------------------------------------------------
# Screen dimensions
SCREEN_WIDTH: int = 1024
SCREEN_HEIGHT: int = 600

# Playfield boundaries (Y-axis)
PLAYFIELD_TOP_Y: int = 75
PLAYFIELD_BOTTOM_Y: int = SCREEN_HEIGHT - 75

#------------------------------------------------------------------------------
# GAME MECHANICS SETTINGS
#------------------------------------------------------------------------------
# Frame rate
FPS: int = 60

# Player settings
PLAYER_SPEED: float = 4.0
PLAYER_SHOOT_DELAY: int = 200  # milliseconds
PLAYER_SCALE_FACTOR: float = 0.25
PLAYER_ANIMATION_SPEED_MS: int = 75  # Milliseconds per frame

# Bullet settings
BULLET_SPEED: float = 10.0
BULLET_SIZE: Tuple[int, int] = (10, 4)

# Animation settings
DEFAULT_ANIMATION_SPEED_MS: int = 75  # Milliseconds per frame

# Sprite sheet settings
DEFAULT_SPRITE_SHEET_GRID: Tuple[int, int] = (3, 3)
DEFAULT_CROP_BORDER_PIXELS: int = 2

#------------------------------------------------------------------------------
# ENEMY SETTINGS
#------------------------------------------------------------------------------
# Basic enemy settings
ENEMY_SPAWN_RATE: int = 1000  # milliseconds
WAVE_DELAY_MS: int = 5000  # Time between enemy waves (milliseconds)
ENEMY1_SCALE_FACTOR: float = 0.20
ENEMY1_ANIMATION_SPEED_MS: int = 100  # Animation speed
ENEMY1_SPEED_X: float = -3.0  # Pixels per frame (moving left)
ENEMY_SHOOTER_COOLDOWN_MS: int = 1500  # milliseconds between shots

# Enemy type identifiers - used to reference enemy types consistently across the codebase
ENEMY_TYPES = {
    "BASIC": 0,       # Basic enemy (EnemyType1)
    "SHOOTER": 1,     # Enemy that shoots bullets at player (EnemyType2) 
    "WAVE": 2,        # Enemy that moves in wave pattern and fires wave projectiles (EnemyType3)
    "SPIRAL": 3,      # Enemy with erratic movement and spiral projectiles (EnemyType4)
    "SEEKER": 4,      # Enemy that tracks player and fires homing projectiles (EnemyType5)
    "TELEPORTER": 5,  # Enemy that teleports and fires bouncing projectiles (EnemyType6)
}

# Enemy type names for logging and UI display
ENEMY_TYPE_NAMES = {
    ENEMY_TYPES["BASIC"]: "Basic",
    ENEMY_TYPES["SHOOTER"]: "Shooter",
    ENEMY_TYPES["WAVE"]: "Wave",
    ENEMY_TYPES["SPIRAL"]: "Spiral", 
    ENEMY_TYPES["SEEKER"]: "Seeker",
    ENEMY_TYPES["TELEPORTER"]: "Teleporter",
}

# Enemy sprite sheet filenames
ENEMY_SPRITE_FILES = {
    ENEMY_TYPES["BASIC"]: "enemy1.png",
    ENEMY_TYPES["SHOOTER"]: "enemy2.png",
    ENEMY_TYPES["WAVE"]: "enemy3.png",
    ENEMY_TYPES["SPIRAL"]: "enemy4.png",
    ENEMY_TYPES["SEEKER"]: "enemy5.png",
    ENEMY_TYPES["TELEPORTER"]: "enemy6.png",
}

#------------------------------------------------------------------------------
# PATTERN TYPES FOR ENEMY WAVES
#------------------------------------------------------------------------------
PATTERN_TYPES = {
    "VERTICAL": 0,    # Enemies in a straight vertical line
    "HORIZONTAL": 1,  # Enemies in a straight horizontal line
    "DIAGONAL": 2,    # Enemies in a diagonal line
    "V_SHAPE": 3      # Enemies in a V formation
}
PATTERN_COUNT: int = len(PATTERN_TYPES)  # Total number of patterns

#------------------------------------------------------------------------------
# DIFFICULTY SYSTEM
#------------------------------------------------------------------------------
# Base difficulty settings
DIFFICULTY_STARTING_LEVEL: float = 1.0
DIFFICULTY_MAX_LEVEL: float = 10.0
DIFFICULTY_INCREASE_RATE: float = 0.2

# Base frequencies for each enemy type at difficulty level 1
# Values are percentages (should sum to 100)
BASE_ENEMY_FREQUENCIES = {
    ENEMY_TYPES["BASIC"]: 40,       # 40% chance at difficulty 1
    ENEMY_TYPES["SHOOTER"]: 30,     # 30% chance at difficulty 1
    ENEMY_TYPES["WAVE"]: 10,        # 10% chance at difficulty 1
    ENEMY_TYPES["SPIRAL"]: 10,      # 10% chance at difficulty 1
    ENEMY_TYPES["SEEKER"]: 10,      # 10% chance at difficulty 1
    ENEMY_TYPES["TELEPORTER"]: 0,   # 0% at difficulty 1 (unlocks at difficulty 2)
}

# Difficulty thresholds for when each enemy type starts to appear
ENEMY_UNLOCK_THRESHOLDS = {
    ENEMY_TYPES["BASIC"]: 1.0,      # Available from start
    ENEMY_TYPES["SHOOTER"]: 1.0,    # Available from start
    ENEMY_TYPES["WAVE"]: 1.0,       # Available from start
    ENEMY_TYPES["SPIRAL"]: 1.0,     # Available from start
    ENEMY_TYPES["SEEKER"]: 1.0,     # Available from start
    ENEMY_TYPES["TELEPORTER"]: 2.0, # Unlocks at difficulty 2.0
}

# Frequency scaling per difficulty level
# Defines how frequencies change with difficulty level
# Positive values mean the frequency increases with difficulty
# Negative values mean the frequency decreases with difficulty
FREQUENCY_SCALING = {
    ENEMY_TYPES["BASIC"]: -3.5,      # Decreases by 3.5% per difficulty level
    ENEMY_TYPES["SHOOTER"]: 1.5,     # Increases by 1.5% per difficulty level
    ENEMY_TYPES["WAVE"]: 1.0,        # Increases by 1.0% per difficulty level
    ENEMY_TYPES["SPIRAL"]: 1.0,      # Increases by 1.0% per difficulty level
    ENEMY_TYPES["SEEKER"]: 1.5,      # Increases by 1.5% per difficulty level
    ENEMY_TYPES["TELEPORTER"]: 2.0,  # Increases by 2.0% per difficulty level once unlocked
}

# Maximum frequency for each enemy type (percentage)
MAX_FREQUENCIES = {
    ENEMY_TYPES["BASIC"]: 40,       # Never higher than initial value
    ENEMY_TYPES["SHOOTER"]: 45,     # Max 45%
    ENEMY_TYPES["WAVE"]: 20,        # Max 20%
    ENEMY_TYPES["SPIRAL"]: 20,      # Max 20%
    ENEMY_TYPES["SEEKER"]: 25,      # Max 25%
    ENEMY_TYPES["TELEPORTER"]: 20,  # Max 20%
}

# Minimum frequency for each enemy type once unlocked (percentage)
MIN_FREQUENCIES = {
    ENEMY_TYPES["BASIC"]: 5,        # Min 5% (always some chance)
    ENEMY_TYPES["SHOOTER"]: 10,     # Min 10%
    ENEMY_TYPES["WAVE"]: 5,         # Min 5%
    ENEMY_TYPES["SPIRAL"]: 5,       # Min 5%
    ENEMY_TYPES["SEEKER"]: 5,       # Min 5%
    ENEMY_TYPES["TELEPORTER"]: 2,   # Min 2%
}

#------------------------------------------------------------------------------
# COLORS
#------------------------------------------------------------------------------
WHITE: Tuple[int, int, int] = (255, 255, 255)
BLACK: Tuple[int, int, int] = (0, 0, 0)
RED: Tuple[int, int, int] = (255, 0, 0)
GREEN: Tuple[int, int, int] = (0, 255, 0)
BLUE: Tuple[int, int, int] = (0, 0, 255)
YELLOW: Tuple[int, int, int] = (255, 255, 0)

#------------------------------------------------------------------------------
# FONT SETTINGS
#------------------------------------------------------------------------------
DEFAULT_FONT_SIZE: int = 24
DEFAULT_FONT_NAME: Optional[str] = None  # Use default pygame font

#------------------------------------------------------------------------------
# SOUND SETTINGS
#------------------------------------------------------------------------------
DEFAULT_SOUND_VOLUME: float = 0.5
DEFAULT_MUSIC_VOLUME: float = 0.3

#------------------------------------------------------------------------------
# EVENT TYPES
#------------------------------------------------------------------------------
WAVE_TIMER_EVENT_ID: int = pygame.USEREVENT + 1

#------------------------------------------------------------------------------
# DEBUG SETTINGS
#------------------------------------------------------------------------------
DEBUG_FORCE_ENEMY_TYPE: bool = False
DEBUG_ENEMY_TYPE_INDEX: int = 5  # Enemy type to use when DEBUG_FORCE_ENEMY_TYPE is True (0-5) 