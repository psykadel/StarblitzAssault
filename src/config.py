"""Game configuration settings."""

import os

# Screen dimensions
SCREEN_WIDTH: int = 1024 # Reduced width
SCREEN_HEIGHT: int = 600  # Reduced height

# Playfield boundaries (Y-axis)
PLAYFIELD_TOP_Y: int = 75 # Adjusted for smaller height
PLAYFIELD_BOTTOM_Y: int = SCREEN_HEIGHT - 75 # Adjusted for smaller height

# Frame rate
FPS: int = 60

# Player settings
PLAYER_SPEED: float = 5.0
PLAYER_SHOOT_DELAY: int = 200 # milliseconds

# Enemy settings
ENEMY_SPAWN_RATE: int = 1000 # milliseconds

# Paths (using os.path.join as per python.mdc)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
SPRITES_DIR = os.path.join(ASSETS_DIR, 'sprites')
SOUNDS_DIR = os.path.join(ASSETS_DIR, 'sounds')
MUSIC_DIR = os.path.join(ASSETS_DIR, 'music')
IMAGES_DIR = os.path.join(ASSETS_DIR, 'images')
BACKGROUNDS_DIR = os.path.join(ASSETS_DIR, 'backgrounds')

# Colors (example)
WHITE: tuple[int, int, int] = (255, 255, 255)
BLACK: tuple[int, int, int] = (0, 0, 0)
RED: tuple[int, int, int] = (255, 0, 0)

# Font settings (example)
DEFAULT_FONT_SIZE: int = 24
DEFAULT_FONT_NAME: str | None = None # Use default pygame font

# Add other configuration variables as needed...
