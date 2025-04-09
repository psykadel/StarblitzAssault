"""Centralized game configuration settings."""

import logging
import os
from typing import Dict, List, Optional, Tuple

import pygame

# ------------------------------------------------------------------------------
# LOGGING SETTINGS
# ------------------------------------------------------------------------------
# Can be set to logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, or logging.CRITICAL
LOG_LEVEL: int = logging.WARNING

# ------------------------------------------------------------------------------
# DIRECTORY PATHS
# ------------------------------------------------------------------------------
# Base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SPRITES_DIR = os.path.join(ASSETS_DIR, "sprites")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
BACKGROUNDS_DIR = os.path.join(ASSETS_DIR, "backgrounds")

# ------------------------------------------------------------------------------
# SCREEN AND DISPLAY SETTINGS
# ------------------------------------------------------------------------------
# Screen dimensions
SCREEN_WIDTH: int = 1024
SCREEN_HEIGHT: int = 600

# Playfield boundaries (Y-axis)
PLAYFIELD_TOP_Y: int = 75
PLAYFIELD_BOTTOM_Y: int = SCREEN_HEIGHT - 75

# UI transparency settings
LOGO_ALPHA: int = 128  # Alpha value (0-255) for game logo transparency

# ------------------------------------------------------------------------------
# GAME MECHANICS SETTINGS
# ------------------------------------------------------------------------------
# Frame rate
FPS: int = 60

# Player settings
PLAYER_SPEED: float = 4.0
PLAYER_SHOOT_DELAY: int = 200  # Milliseconds
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

# ------------------------------------------------------------------------------
# ENEMY SETTINGS
# ------------------------------------------------------------------------------
# Basic enemy settings
ENEMY_SPAWN_RATE: int = 1000  # milliseconds
WAVE_DELAY_MS: int = 5000  # Time between enemy waves (milliseconds)
ENEMY_SCALE_FACTOR: float = 0.20
ENEMY_ANIMATION_SPEED_MS: int = 100  # Animation speed
ENEMY_SPEED_X: float = -3.0  # Pixels per frame (moving left)
ENEMY_SHOOTER_COOLDOWN_MS: int = 1500  # milliseconds between shots

# Enemy type identifiers - used to reference enemy types consistently across the codebase
ENEMY_TYPES = {
    "BASIC": 0,  # Basic enemy (EnemyType1)
    "SHOOTER": 1,  # Enemy that shoots bullets at player (EnemyType2)
    "WAVE": 2,  # Enemy that moves in wave pattern and fires wave projectiles (EnemyType3)
    "SPIRAL": 3,  # Enemy that moves erratically and fires spiral projectiles (EnemyType4)
    "SEEKER": 4,  # Enemy that tracks player and fires homing projectiles (EnemyType5)
    "TELEPORTER": 5,  # Enemy that teleports and fires bouncing projectiles (EnemyType6)
    "REFLECTOR": 6,  # Enemy that reflects player bullets and fires laser beams (EnemyType7)
}

# Enemy type names for logging and UI display
ENEMY_TYPE_NAMES = {
    ENEMY_TYPES["BASIC"]: "Basic",
    ENEMY_TYPES["SHOOTER"]: "Shooter",
    ENEMY_TYPES["WAVE"]: "Wave",
    ENEMY_TYPES["SPIRAL"]: "Spiral",
    ENEMY_TYPES["SEEKER"]: "Seeker",
    ENEMY_TYPES["TELEPORTER"]: "Teleporter",
    ENEMY_TYPES["REFLECTOR"]: "Reflector",
}

# Enemy sprite sheet filenames
ENEMY_SPRITE_FILES = {
    ENEMY_TYPES["BASIC"]: "enemy1.png",
    ENEMY_TYPES["SHOOTER"]: "enemy2.png",
    ENEMY_TYPES["WAVE"]: "enemy3.png",
    ENEMY_TYPES["SPIRAL"]: "enemy4.png",
    ENEMY_TYPES["SEEKER"]: "enemy5.png",
    ENEMY_TYPES["TELEPORTER"]: "enemy6.png",
    ENEMY_TYPES["REFLECTOR"]: "enemy7.png",
}

# ------------------------------------------------------------------------------
# PATTERN TYPES FOR ENEMY WAVES
# ------------------------------------------------------------------------------
PATTERN_TYPES = {
    "VERTICAL": 0,  # Enemies in a straight vertical line
    "HORIZONTAL": 1,  # Enemies in a straight horizontal line
    "DIAGONAL": 2,  # Enemies in a diagonal line
    "V_SHAPE": 3,  # Enemies in a V formation
}
PATTERN_COUNT: int = len(PATTERN_TYPES)  # Total number of patterns

# ------------------------------------------------------------------------------
# BACKGROUND DECORATION SETTINGS
# ------------------------------------------------------------------------------
# Total number of decoration files in the assets/backgrounds folder
DECORATION_FILES: int = 6  # Files are named decoration1.png through decoration6.png

# Appearance settings
DECORATION_ALPHA: int = 70  # Alpha value (0-255) for decoration transparency
DECORATION_MIN_SIZE: int = 120  # Minimum size for decorations
DECORATION_MAX_SIZE: int = 180  # Maximum size for decorations

# Spacing and positioning settings
DECORATION_MIN_HORIZONTAL_SPACING: int = 1000  # Minimum horizontal spacing between decorations
DECORATION_TOP_PADDING: int = 30  # Minimum distance from top of playfield
DECORATION_BOTTOM_PADDING: int = 70  # Minimum distance from bottom of playfield

# ------------------------------------------------------------------------------
# POWERUP SETTINGS
# ------------------------------------------------------------------------------
# Visual settings
POWERUP_ALPHA: int = 90  # Alpha value (0-255) for powerup sprite transparency
POWERUP_GLOW_RATIO: float = 1  # Glow ratio for powerup sprite

# Spawn settings
POWERUP_MIN_SPAWN_INTERVAL_MS: int = 3000  # Minimum spawn interval in milliseconds
POWERUP_MAX_SPAWN_INTERVAL_MS: int = 30000  # Maximum spawn interval in milliseconds

# Frequency scaling with difficulty
POWERUP_DIFFICULTY_SCALING: float = (
    0.85  # Multiplier to reduce spawn interval per difficulty level (< 1.0 means more frequent)
)
POWERUP_MIN_DIFFICULTY_INTERVAL_MS: int = (
    10000  # Minimum spawn interval at max difficulty in milliseconds
)

# Powerup slot constants for display positioning
# These define fixed vertical positions for each powerup type in the status area
POWERUP_SLOTS = {
    "TRIPLE_SHOT": 0,  # Slot 0 (top position)
    "RAPID_FIRE": 1,  # Slot 1
    "SHIELD": 2,  # Slot 2
    "HOMING_MISSILES": 3,  # Slot 3
    "SCATTER_BOMB": 4,  # Slot 4
    "TIME_WARP": 5,  # Slot 5
    # Instant powerups don't need slots:
    # "POWER_RESTORE": N/A  # Instant effect, no persistent display
    # "MEGA_BLAST": N/A     # Instant effect, no persistent display
}

# Powerup display spacing
POWERUP_ICON_SIZE: int = 30  # Size of powerup icons in pixels
POWERUP_ICON_SPACING: int = 32  # Vertical spacing between powerup icons
POWERUP_DISPLAY_START_Y: int = 50  # Y position for the first powerup slot

# ------------------------------------------------------------------------------
# DIFFICULTY SYSTEM
# ------------------------------------------------------------------------------
# Base difficulty settings
DIFFICULTY_STARTING_LEVEL: float = 1.0
DIFFICULTY_MAX_LEVEL: float = 10.0
DIFFICULTY_INCREASE_RATE: float = 0.2

# Base frequencies for each enemy type at difficulty level 1
# Values are percentages (should sum to 100)
BASE_ENEMY_FREQUENCIES = {
    ENEMY_TYPES["BASIC"]: 40,  # 40% chance at difficulty 1
    ENEMY_TYPES["SHOOTER"]: 30,  # 30% chance at difficulty 1
    ENEMY_TYPES["WAVE"]: 10,  # 10% chance at difficulty 1
    ENEMY_TYPES["SPIRAL"]: 10,  # 10% chance at difficulty 1
    ENEMY_TYPES["SEEKER"]: 10,  # 10% chance at difficulty 1
    ENEMY_TYPES["TELEPORTER"]: 0,  # 0% at difficulty 1 (unlocks at difficulty 2)
    ENEMY_TYPES["REFLECTOR"]: 0,  # 0% at difficulty 1 (unlocks at difficulty 2.5)
}

# Difficulty thresholds for when each enemy type starts to appear
ENEMY_UNLOCK_THRESHOLDS = {
    ENEMY_TYPES["BASIC"]: 1.0,  # Available from start
    ENEMY_TYPES["SHOOTER"]: 1.0,  # Available from start
    ENEMY_TYPES["WAVE"]: 1.0,  # Available from start
    ENEMY_TYPES["SPIRAL"]: 1.0,  # Available from start
    ENEMY_TYPES["SEEKER"]: 1.0,  # Available from start
    ENEMY_TYPES["TELEPORTER"]: 2.0,  # Unlocks at difficulty 2.0
    ENEMY_TYPES["REFLECTOR"]: 2.0,  # Unlocks at difficulty 2.5
}

# Frequency scaling per difficulty level
# Defines how frequencies change with difficulty level
# Positive values mean the frequency increases with difficulty
# Negative values mean the frequency decreases with difficulty
FREQUENCY_SCALING = {
    ENEMY_TYPES["BASIC"]: -3.5,  # Decreases by 3.5% per difficulty level
    ENEMY_TYPES["SHOOTER"]: 1.5,  # Increases by 1.5% per difficulty level
    ENEMY_TYPES["WAVE"]: 1.0,  # Increases by 1.0% per difficulty level
    ENEMY_TYPES["SPIRAL"]: 1.0,  # Increases by 1.0% per difficulty level
    ENEMY_TYPES["SEEKER"]: 1.5,  # Increases by 1.5% per difficulty level
    ENEMY_TYPES["TELEPORTER"]: 2.0,  # Increases by 2.0% per difficulty level once unlocked
    ENEMY_TYPES["REFLECTOR"]: 2.0,  # Increases by 1.8% per difficulty level once unlocked
}

# Maximum frequency for each enemy type (percentage)
MAX_FREQUENCIES = {
    ENEMY_TYPES["BASIC"]: 40,  # Never higher than initial value
    ENEMY_TYPES["SHOOTER"]: 45,  # Max 45%
    ENEMY_TYPES["WAVE"]: 20,  # Max 20%
    ENEMY_TYPES["SPIRAL"]: 20,  # Max 20%
    ENEMY_TYPES["SEEKER"]: 25,  # Max 25%
    ENEMY_TYPES["TELEPORTER"]: 20,  # Max 20%
    ENEMY_TYPES["REFLECTOR"]: 20,  # Max 20%
}

# Minimum frequency for each enemy type once unlocked (percentage)
MIN_FREQUENCIES = {
    ENEMY_TYPES["BASIC"]: 5,  # Min 5% (always some chance)
    ENEMY_TYPES["SHOOTER"]: 10,  # Min 10%
    ENEMY_TYPES["WAVE"]: 5,  # Min 5%
    ENEMY_TYPES["SPIRAL"]: 5,  # Min 5%
    ENEMY_TYPES["SEEKER"]: 5,  # Min 5%
    ENEMY_TYPES["TELEPORTER"]: 2,  # Min 2%
    ENEMY_TYPES["REFLECTOR"]: 3,  # Min 3%
}

# ------------------------------------------------------------------------------
# COLORS
# ------------------------------------------------------------------------------
WHITE: Tuple[int, int, int] = (255, 255, 255)
BLACK: Tuple[int, int, int] = (0, 0, 0)
RED: Tuple[int, int, int] = (255, 0, 0)
GREEN: Tuple[int, int, int] = (0, 255, 0)
BLUE: Tuple[int, int, int] = (0, 0, 255)
YELLOW: Tuple[int, int, int] = (255, 255, 0)

# ------------------------------------------------------------------------------
# FONT SETTINGS
# ------------------------------------------------------------------------------
DEFAULT_FONT_SIZE: int = 24
DEFAULT_FONT_NAME: Optional[str] = None  # Use default pygame font

# ------------------------------------------------------------------------------
# SOUND SETTINGS
# ------------------------------------------------------------------------------
DEFAULT_SOUND_VOLUME: float = 0.5
DEFAULT_MUSIC_VOLUME: float = 0.3

# ------------------------------------------------------------------------------
# EVENT TYPES
# ------------------------------------------------------------------------------
WAVE_TIMER_EVENT_ID: int = pygame.USEREVENT + 1

# ------------------------------------------------------------------------------
# DEBUG SETTINGS
# ------------------------------------------------------------------------------
DEBUG_FORCE_ENEMY_TYPE: bool = True
DEBUG_ENEMY_TYPE_INDEX: int = 6  # Enemy type to use when DEBUG_FORCE_ENEMY_TYPE is True (0-5)
