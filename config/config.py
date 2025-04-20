"""Centralized game configuration settings."""

import logging
import os
from typing import Dict, List, Optional, Tuple

import pygame

# ==============================================================================
# GENERAL SETTINGS
# ==============================================================================

# Frame rate
FPS: int = 60

# Default animation speed
DEFAULT_ANIMATION_SPEED_MS: int = 75  # Milliseconds per frame

# Game Event IDs
WAVE_TIMER_EVENT_ID: int = pygame.USEREVENT + 1


# ==============================================================================
# LOGGING SETTINGS
# ==============================================================================

# Can be set to logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, or logging.CRITICAL
LOG_LEVEL: int = logging.WARNING


# ==============================================================================
# DEBUG SETTINGS
# ==============================================================================

DEBUG_FORCE_ENEMY_TYPE: bool = False
DEBUG_ENEMY_TYPE_INDEX: int = 7  # Enemy type to use when DEBUG_FORCE_ENEMY_TYPE is True

DEBUG_FORCE_POWERUP_TYPE: bool = False
DEBUG_POWERUP_TYPE_INDEX: int = 9  # PowerupType index to use when DEBUG_FORCE_POWERUP_TYPE is True


# ==============================================================================
# DIRECTORY PATHS
# ==============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SPRITES_DIR = os.path.join(ASSETS_DIR, "sprites")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
MUSIC_DIR = os.path.join(ASSETS_DIR, "music")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
BACKGROUNDS_DIR = os.path.join(ASSETS_DIR, "backgrounds")


# ==============================================================================
# SCREEN AND DISPLAY SETTINGS
# ==============================================================================

# Screen dimensions
SCREEN_WIDTH: int = 1024
SCREEN_HEIGHT: int = 600

# Playfield boundaries (Y-axis)
PLAYFIELD_TOP_Y: int = 75
PLAYFIELD_BOTTOM_Y: int = SCREEN_HEIGHT - 75

# UI transparency settings
LOGO_ALPHA: int = 128  # Alpha value (0-255) for game logo transparency

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


# ==============================================================================
# ASSET SETTINGS
# ==============================================================================

# Sprite sheet settings
DEFAULT_SPRITE_SHEET_GRID: Tuple[int, int] = (3, 3)
DEFAULT_CROP_BORDER_PIXELS: int = 2


# ==============================================================================
# PLAYER SETTINGS
# ==============================================================================

PLAYER_SPEED: float = 6.0  # pixels per frame
PLAYER_SHOOT_DELAY: int = 200  # Milliseconds
PLAYER_SCALE_FACTOR: float = 0.25
PLAYER_ANIMATION_SPEED_MS: int = 75  # Milliseconds per frame
PLAYER_FIRE_DELAY: int = 200  # milliseconds between shots
PLAYER_SHIELD_DURATION: int = 5000  # duration of shield powerup in ms


# ==============================================================================
# BULLET SETTINGS
# ==============================================================================

BULLET_SPEED: float = 12.0  # pixels per frame
BULLET_SIZE: Tuple[int, int] = (10, 4)
ENEMY_BULLET_SPEED: float = 6.0  # pixels per frame
HOMING_MISSILE_SPEED: float = 3.0  # pixels per frame
EXPLOSIVE_BULLET_SPEED: float = 4.0  # pixels per frame


# ==============================================================================
# ENEMY SETTINGS
# ==============================================================================

# --- General Enemy Settings ---
ENEMY_SPAWN_RATE: int = 1000  # milliseconds
WAVE_DELAY_MS: int = 5000  # Time between enemy waves (milliseconds)
ENEMY_SCALE_FACTOR: float = 0.20
ENEMY_ANIMATION_SPEED_MS: int = 100  # Animation speed
ENEMY_SPEED_X: float = -3.0  # Pixels per frame (moving left)
ENEMY_SHOOTER_COOLDOWN_MS: int = 1500  # milliseconds between shots
ENEMY_HIT_DELAY: int = 50  # milliseconds flash when hit
ENEMY_BASE_SCORE: int = 100

# --- Enemy Types ---
ENEMY_TYPES = {
    "BASIC": 0,      # Basic enemy (EnemyType1)
    "SHOOTER": 1,    # Enemy that shoots bullets at player (EnemyType2)
    "WAVE": 2,       # Enemy that moves in wave pattern and fires wave projectiles (EnemyType3)
    "SPIRAL": 3,     # Enemy that moves erratically and fires spiral projectiles (EnemyType4)
    "SEEKER": 4,     # Enemy that tracks player and fires homing projectiles (EnemyType5)
    "TELEPORTER": 5, # Enemy that teleports and fires bouncing projectiles (EnemyType6)
    "REFLECTOR": 6,  # Enemy that reflects player bullets and fires laser beams (EnemyType7)
    "LIGHTBOARD": 7, # Enemy that rides a lightboard and tries to collide with player (EnemyType8)
}

# --- Enemy Type Names (for UI/logging) ---
ENEMY_TYPE_NAMES = {
    ENEMY_TYPES["BASIC"]: "Basic",
    ENEMY_TYPES["SHOOTER"]: "Shooter",
    ENEMY_TYPES["WAVE"]: "Wave",
    ENEMY_TYPES["SPIRAL"]: "Spiral",
    ENEMY_TYPES["SEEKER"]: "Seeker",
    ENEMY_TYPES["TELEPORTER"]: "Teleporter",
    ENEMY_TYPES["REFLECTOR"]: "Reflector",
    ENEMY_TYPES["LIGHTBOARD"]: "Lightboard",
}

# --- Enemy Sprite Files ---
ENEMY_SPRITE_FILES = {
    ENEMY_TYPES["BASIC"]: "enemy1.png",
    ENEMY_TYPES["SHOOTER"]: "enemy2.png",
    ENEMY_TYPES["WAVE"]: "enemy3.png",
    ENEMY_TYPES["SPIRAL"]: "enemy4.png",
    ENEMY_TYPES["SEEKER"]: "enemy5.png",
    ENEMY_TYPES["TELEPORTER"]: "enemy6.png",
    ENEMY_TYPES["REFLECTOR"]: "enemy7.png",
    ENEMY_TYPES["LIGHTBOARD"]: "enemy8.png",
}

# --- Enemy Wave Pattern Types ---
PATTERN_TYPES = {
    "VERTICAL": 0,    # Enemies in a straight vertical line
    "HORIZONTAL": 1,  # Enemies in a straight horizontal line
    "DIAGONAL": 2,    # Enemies in a diagonal line
    "V_SHAPE": 3,     # Enemies in a V formation
}
PATTERN_COUNT: int = len(PATTERN_TYPES)  # Total number of patterns

# --- Enemy Spawn Boundary Settings ---
SPAWN_BASE_BORDER_MARGIN: int = 80  # Base margin from playfield edges
SPAWN_DIAGONAL_SPACING_X: int = 60  # Horizontal spacing for diagonal patterns
SPAWN_DIAGONAL_SPACING_Y: int = 60  # Vertical spacing for diagonal patterns (maximum)

# Extra spawn margins for specific enemy types
SPAWN_EXTRA_MARGINS: Dict[int, int] = {
    ENEMY_TYPES["REFLECTOR"]: 40,  # EnemyType7 - extra large margin
    ENEMY_TYPES["LIGHTBOARD"]: 30, # EnemyType8 - larger than standard margin
    ENEMY_TYPES["SEEKER"]: 20,     # EnemyType5 - above standard margin
    ENEMY_TYPES["SPIRAL"]: 20,     # EnemyType4 - above standard margin
}

# --- Pattern Spawn Settings ---
SPAWN_HORIZONTAL_BORDER_MARGIN: int = 50
SPAWN_VERTICAL_BORDER_MARGIN: int = 50
SPAWN_V_PATTERN_BORDER_MARGIN: int = 50


# ==============================================================================
# BACKGROUND DECORATION SETTINGS
# ==============================================================================

# Total number of decoration files in the assets/backgrounds folder
DECORATION_FILES: int = 6  # Files are named decoration1.png through decoration6.png

# --- Appearance ---
DECORATION_ALPHA: int = 70  # Alpha value (0-255) for decoration transparency
DECORATION_MIN_SIZE: int = 120  # Minimum size for decorations
DECORATION_MAX_SIZE: int = 180  # Maximum size for decorations

# --- Spacing and Positioning ---
DECORATION_MIN_HORIZONTAL_SPACING: int = 1000  # Minimum horizontal spacing
DECORATION_TOP_PADDING: int = 30  # Minimum distance from top of playfield
DECORATION_BOTTOM_PADDING: int = 80  # Minimum distance from bottom of playfield


# ==============================================================================
# POWERUP SETTINGS
# ==============================================================================

# --- General Powerup Settings ---
POWERUP_ALPHA: int = 90  # Alpha value (0-255) for powerup sprite transparency
POWERUP_GLOW_RATIO: float = 1  # Glow ratio for powerup sprite

# --- Spawn Settings ---
POWERUP_MIN_SPAWN_INTERVAL_MS: int = 5000  # Minimum spawn interval in milliseconds
POWERUP_MAX_SPAWN_INTERVAL_MS: int = 25000  # Maximum spawn interval in milliseconds

# --- Frequency Scaling with Difficulty ---
POWERUP_DIFFICULTY_SCALING: float = (
    0.85  # Multiplier to reduce spawn interval per difficulty level (< 1.0 means more frequent)
)
POWERUP_MIN_DIFFICULTY_INTERVAL_MS: int = (
    10000  # Minimum spawn interval at max difficulty in milliseconds
)

# --- Specific Powerup Settings ---
FLAMETHROWER_DURATION: int = 8000  # 8 seconds duration
FLAME_PARTICLE_DAMAGE: int = 5  # Damage per flame particle hit
FLAME_PARTICLE_LIFETIME: int = 60  # Lifetime of flame particles in frames
FLAME_SPAWN_DELAY: int = 80  # Milliseconds between flame particle spawns
FLAME_SPRAY_ANGLE: float = 0.8  # Maximum vertical angle deviation in radians (approx 45 degrees)
DRONE_DURATION: int = 15000  # 15 seconds duration (increased)
HOMING_MISSILE_ROTATION_SPEED: float = 3.0  # degrees per frame

# --- Powerup Display Settings ---
# Fixed vertical slots for active powerups in the status area
POWERUP_SLOTS = {
    "TRIPLE_SHOT": 0,     # Slot 0 (top position)
    "RAPID_FIRE": 1,      # Slot 1
    "SHIELD": 2,          # Slot 2
    "HOMING_MISSILES": 3, # Slot 3
    "SCATTER_BOMB": 4,    # Slot 4
    "TIME_WARP": 5,       # Slot 5
    "LASER_BEAM": 6,      # Slot 6
    "DRONE": 7,           # Slot 7
    "FLAMETHROWER": 8,    # Slot 8
    # Instant powerups don't need slots: "POWER_RESTORE", "MEGA_BLAST"
}

POWERUP_ICON_SIZE: int = 30  # Size of powerup icons in pixels
POWERUP_ICON_SPACING: int = 32  # Vertical spacing between powerup icons
POWERUP_DISPLAY_START_Y: int = 50  # Y position for the first powerup slot


# ==============================================================================
# DIFFICULTY SYSTEM
# ==============================================================================

# --- Difficulty Levels ---
DIFFICULTY_STARTING_LEVEL: float = 1.0
DIFFICULTY_MAX_LEVEL: float = 10.0
DIFFICULTY_INCREASE_RATE: float = 0.3  # Increased rate

# --- Base Enemy Frequencies (at difficulty level 1.0) ---
# Values are percentages (should sum to 100)
BASE_ENEMY_FREQUENCIES = {
    ENEMY_TYPES["BASIC"]: 35,      # Reduced
    ENEMY_TYPES["SHOOTER"]: 30,    # Unchanged
    ENEMY_TYPES["WAVE"]: 12,       # Increased
    ENEMY_TYPES["SPIRAL"]: 12,     # Increased
    ENEMY_TYPES["SEEKER"]: 11,     # Increased
    ENEMY_TYPES["TELEPORTER"]: 0,  # Initial 0%
    ENEMY_TYPES["REFLECTOR"]: 0,   # Initial 0%
    ENEMY_TYPES["LIGHTBOARD"]: 0,  # Initial 0%
}

# --- Enemy Unlock Thresholds (difficulty level) ---
ENEMY_UNLOCK_THRESHOLDS = {
    ENEMY_TYPES["BASIC"]: 1.0,     # Start
    ENEMY_TYPES["SHOOTER"]: 1.0,   # Start
    ENEMY_TYPES["WAVE"]: 1.0,      # Start
    ENEMY_TYPES["SPIRAL"]: 1.0,    # Start
    ENEMY_TYPES["SEEKER"]: 1.0,    # Start
    ENEMY_TYPES["TELEPORTER"]: 1.5,
    ENEMY_TYPES["REFLECTOR"]: 2.0,
    ENEMY_TYPES["LIGHTBOARD"]: 2.0,
}

# --- Frequency Scaling per Difficulty Level ---
# How frequencies change with difficulty (positive = more frequent, negative = less frequent)
FREQUENCY_SCALING = {
    ENEMY_TYPES["BASIC"]: -4.0,     # Increased negative scaling
    ENEMY_TYPES["SHOOTER"]: 1.0,    # Reduced positive scaling
    ENEMY_TYPES["WAVE"]: 1.2,      # Increased positive scaling
    ENEMY_TYPES["SPIRAL"]: 1.3,    # Increased positive scaling
    ENEMY_TYPES["SEEKER"]: 1.8,    # Increased positive scaling
    ENEMY_TYPES["TELEPORTER"]: 2.5, # Increased positive scaling
    ENEMY_TYPES["REFLECTOR"]: 2.5,  # Increased positive scaling
    ENEMY_TYPES["LIGHTBOARD"]: 3.0, # Increased positive scaling
}

# --- Maximum Enemy Frequencies (percentage) ---
MAX_FREQUENCIES = {
    ENEMY_TYPES["BASIC"]: 35,      # Reduced max
    ENEMY_TYPES["SHOOTER"]: 40,    # Reduced max
    ENEMY_TYPES["WAVE"]: 20,       # Unchanged
    ENEMY_TYPES["SPIRAL"]: 22,     # Increased max
    ENEMY_TYPES["SEEKER"]: 25,     # Unchanged
    ENEMY_TYPES["TELEPORTER"]: 22, # Increased max
    ENEMY_TYPES["REFLECTOR"]: 22,  # Increased max
    ENEMY_TYPES["LIGHTBOARD"]: 25, # Unchanged
}

# --- Minimum Enemy Frequencies (percentage, once unlocked) ---
MIN_FREQUENCIES = {
    ENEMY_TYPES["BASIC"]: 5,       # Unchanged
    ENEMY_TYPES["SHOOTER"]: 10,     # Unchanged
    ENEMY_TYPES["WAVE"]: 6,       # Increased min
    ENEMY_TYPES["SPIRAL"]: 6,      # Increased min
    ENEMY_TYPES["SEEKER"]: 6,      # Increased min
    ENEMY_TYPES["TELEPORTER"]: 3,  # Increased min
    ENEMY_TYPES["REFLECTOR"]: 4,   # Increased min
    ENEMY_TYPES["LIGHTBOARD"]: 5,  # Increased min
}


# ==============================================================================
# SOUND AND MUSIC SETTINGS
# ==============================================================================

DEFAULT_SOUND_VOLUME: float = 0.5
DEFAULT_MUSIC_VOLUME: float = 0.3


# ==============================================================================
# ANIMATION SETTINGS (General)
# ==============================================================================

# These were duplicated earlier, consolidating here if not specific
ANIMATION_DELAY: int = 100  # milliseconds between animation frames (use DEFAULT_ANIMATION_SPEED_MS?)
EXPLOSION_ANIMATION_DELAY: int = 50  # milliseconds between explosion frames


# ==============================================================================
# BOSS BATTLE SETTINGS
# ==============================================================================

# Wave number when the boss appears
BOSS_WAVE_NUMBER: int = 25

# Rainbow colors for boss effects
BOSS_BULLET_COLORS: List[Tuple[int, int, int]] = [
    (255, 0, 0),    # Red
    (255, 165, 0),  # Orange
    (255, 255, 0),  # Yellow
    (0, 255, 0),    # Green
    (0, 0, 255),    # Blue
    (75, 0, 130),   # Indigo
    (148, 0, 211),  # Violet
    (255, 192, 203) # Pink
]

# Other boss settings are defined in a dedicated boss module (e.g., boss_battle.py)
