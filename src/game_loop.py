"""Main game loop and game state management."""

from __future__ import annotations

import logging
import os
import random
import math
from collections import deque
from enum import IntEnum
from typing import Tuple

import pygame

# Import configuration constants
from config.config import (
    BACKGROUNDS_DIR,
    BLACK,
    DEBUG_ENEMY_TYPE_INDEX,
    DEBUG_FORCE_ENEMY_TYPE,
    DECORATION_FILES,
    DEFAULT_FONT_SIZE,
    ENEMY_SHOOTER_COOLDOWN_MS,
    ENEMY_TYPE_NAMES,
    FPS,
    LOGO_ALPHA,
    PATTERN_TYPES,
    PLAYER_SHOOT_DELAY,
    PLAYER_SPEED,
    PLAYFIELD_BOTTOM_Y,
    PLAYFIELD_TOP_Y,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    WAVE_DELAY_MS,
    WAVE_TIMER_EVENT_ID,
    WHITE,
    DEBUG_FORCE_POWERUP_TYPE,
    DEBUG_POWERUP_TYPE_INDEX,
    BOSS_WAVE_NUMBER,
)
from src.background import BackgroundDecorations, BackgroundLayer
from src.border import Border
from src.enemy import (
    EnemyType1,
    EnemyType2,
    EnemyType3,
    EnemyType4,
    EnemyType5,
    EnemyType6,
    EnemyType7,
    EnemyType8,
    get_enemy_weights,
)
from src.explosion import Explosion
from src.logger import get_logger, setup_logger

# Import game components
from src.player import MAX_POWER_LEVEL, Player
from src.power_particles import PowerParticleSystem
from src.powerup import PowerupType
from src.sound_manager import SoundManager
from src.particle import FlameParticle

# Import boss components
from src.boss_battle import create_boss
from src.boss_intro import run_boss_intro

# Get logger for this module
logger = get_logger(__name__)

# Define background speeds
BG_LAYER_SPEEDS = [0.5, 1.0, 1.5, 2.0]  # Slowest to fastest

# Use the event ID from config
WAVE_TIMER_EVENT = WAVE_TIMER_EVENT_ID

# Rainbow colors for boss blood explosions
BOSS_BLOOD_COLORS = [
    (255, 0, 0),    # Red
    (255, 165, 0),  # Orange
    (255, 255, 0),  # Yellow
    (0, 255, 0),    # Green
    (0, 0, 255),    # Blue
    (75, 0, 130),   # Indigo
    (148, 0, 211),  # Violet
    (255, 192, 203) # Pink
]

# Add a new custom explosion class for rainbow blood
class RainbowBloodExplosion(Explosion):
    """Special rainbow blood explosion for boss hits."""
    
    def __init__(self, position, size, color, *groups):
        """Initialize the rainbow blood explosion.
        
        Args:
            position: Position tuple (x, y)
            size: Size tuple (width, height)
            color: RGB color tuple for the blood
            *groups: Sprite groups to add to. The caller should use the 
                     pattern `*(group,) if group else ()` to pass arguments.
        """
        # Pass the received groups tuple directly to the parent class.
        # The parent class's __init__ will handle filtering Nones if necessary, 
        # but our calling pattern ensures groups is already safe.
        super().__init__(position, size, "enemy", *groups)
        
        self.rainbow_color = color
        
        # Recreate frames with custom color if parent created them.
        if hasattr(self, 'frames') and self.frames:
            self._recreate_frames_with_color(color)
        else:
            logger.warning("RainbowBloodExplosion: Parent Explosion did not create frames.")
    
    def _recreate_frames_with_color(self, color):
        """Recreate explosion frames with the specified color."""
        for i, frame in enumerate(self.frames):
            # Create a copy of the frame
            new_frame = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
            
            # Get alpha data from original frame
            alpha_data = pygame.surfarray.array_alpha(frame)
            
            # Fill with the new color
            new_frame.fill((0, 0, 0, 0))  # Clear with transparent
            
            # Get frame dimensions
            width, height = frame.get_size()
            center = (width // 2, height // 2)
            radius = min(width, height) // 2
            
            # Main explosion circle with custom color
            pygame.draw.circle(new_frame, color, center, radius)
            
            # Add glow effect
            glow_color = (
                min(255, color[0] + 50),
                min(255, color[1] + 50),
                min(255, color[2] + 50)
            )
            pygame.draw.circle(new_frame, glow_color, center, max(1, radius // 2))
            
            # Apply original alpha
            pygame.surfarray.pixels_alpha(new_frame)[:] = alpha_data
            
            # Replace the frame
            self.frames[i] = new_frame
        
        # Reset current frame
        self.image = self.frames[self.frame_index]

# Define pattern types as IntEnum for better type checking and readability
class PatternType(IntEnum):
    VERTICAL = PATTERN_TYPES["VERTICAL"]
    HORIZONTAL = PATTERN_TYPES["HORIZONTAL"]
    DIAGONAL = PATTERN_TYPES["DIAGONAL"]
    V_SHAPE = PATTERN_TYPES["V_SHAPE"]

# Text notification for powerups
class PowerupNotification(pygame.sprite.Sprite):
    """Animated text notification for powerup collection."""

    def __init__(
        self, text: str, color: Tuple[int, int, int], position: Tuple[int, int], *groups
    ) -> None:
        """Initialize a new text notification.

        Args:
            text: The text to display
            color: RGB color tuple for the text
            position: Starting position (x, y)
            groups: Sprite groups to add to
        """
        # Filter out None values from groups to avoid errors
        groups = [g for g in groups if g is not None]
        super().__init__(*groups)

        # Text properties
        self.font = pygame.font.SysFont(None, 36)  # Larger font for better visibility
        self.text = text
        self.color = color
        self.alpha = 255  # Start fully opaque

        # Create the initial text image with an outline for better visibility
        self.original_surface = self.font.render(self.text, True, self.color)

        # Create a slightly larger surface with black outline
        outline_size = 2
        self.image = pygame.Surface(
            (
                self.original_surface.get_width() + outline_size * 2,
                self.original_surface.get_height() + outline_size * 2,
            ),
            pygame.SRCALPHA,
        )

        # Draw black outline
        outline_surface = self.font.render(self.text, True, (0, 0, 0))
        for dx in range(-outline_size, outline_size + 1):
            for dy in range(-outline_size, outline_size + 1):
                if dx != 0 or dy != 0:
                    self.image.blit(outline_surface, (outline_size + dx, outline_size + dy))

        # Draw actual text on top
        self.image.blit(self.original_surface, (outline_size, outline_size))

        self.rect = self.image.get_rect(center=position)

        # Movement and animation
        self.pos_y = float(position[1])
        self.speed_y = -1.5  # Move upward slightly faster
        self.lifetime = 90  # 1.5 seconds at 60fps
        self.age = 0

    def update(self) -> None:
        """Update the notification's position and appearance."""
        self.age += 1
        if self.age >= self.lifetime:
            self.kill()
            return

        # Move upward
        self.pos_y += self.speed_y
        self.rect.centery = round(self.pos_y)

        # Fade out gradually
        if self.age > self.lifetime * 0.5:  # Start fading halfway through lifetime
            fade_progress = (self.age - (self.lifetime * 0.5)) / (self.lifetime * 0.5)
            self.alpha = int(255 * (1 - fade_progress))

            # Create a new surface with the updated alpha
            new_image = self.image.copy()
            new_image.set_alpha(self.alpha)
            self.image = new_image

class Game:
    """Main game class managing the game loop, state, and events."""

    def __init__(self):
        pygame.init()
        logger.info("Initializing game")

        # Game state
        self.is_running = True
        self.is_paused = False
        self.debug_mode = True  # Enable debug mode by default
        self.boss_defeat_handled = False  # Track if we've handled the boss defeat

        # Difficulty progression
        self.difficulty_level = 1.0  # Starting difficulty (will increase over time)
        self.max_difficulty = 10.0  # Maximum difficulty cap
        self.difficulty_increase_rate = 0.2
        self.game_start_time = pygame.time.get_ticks()  # Track game duration

        # Consider adding mixer init for sounds later: pygame.mixer.init()

        # Load configuration - Use config for window size, add FULLSCREEN and SCALED
        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED
        )
        # Store the configured resolution, not necessarily the actual display resolution
        self.current_screen_width = SCREEN_WIDTH
        self.current_screen_height = SCREEN_HEIGHT

        pygame.display.set_caption("Starblitz Assault")  # From game.mdc

        self.clock = pygame.time.Clock()

        # Initialize background layers
        self.background_layers = []
        # Use the three different starfield images with different scroll speeds for parallax
        # Adding starfield3.png again for the fourth layer
        starfield_images = ["starfield1.png", "starfield2.png", "starfield3.png", "starfield3.png"]

        # Randomize vertical offsets to avoid repeating patterns
        vertical_offsets = [random.randint(-50, 50) for _ in range(len(starfield_images))]
        # Make the fourth layer have a more distinct vertical offset
        if len(vertical_offsets) >= 4:
            vertical_offsets[3] = random.randint(
                30, 80
            )  # More pronounced positive offset for distant stars effect

        # Different initial horizontal offsets for each layer
        # These will be recalculated more accurately after loading the images
        initial_offsets = [0, 100, 200, 300]  # Default fallback offsets (added a fourth offset)

        for i, (image_name, speed) in enumerate(zip(starfield_images, BG_LAYER_SPEEDS)):
            bg_image_path = os.path.join(BACKGROUNDS_DIR, image_name)

            if os.path.exists(bg_image_path):
                try:
                    # Create a temporary layer to get the image width for better offsets
                    _temp_layer = BackgroundLayer(
                        bg_image_path,
                        0,
                        self.current_screen_height,
                        vertical_offset=vertical_offsets[i],  # Apply vertical offset
                    )

                    bg_image_width = _temp_layer.image_width

                    # Calculate better horizontal offsets if width is valid
                    if bg_image_width > 0:
                        # Distribute the layers at different horizontal positions
                        if i == 0:
                            offset = 0
                        elif i == 1:
                            offset = bg_image_width / 4  # One quarter of the way
                        elif i == 2:
                            offset = bg_image_width * 2 / 4  # Two quarters of the way
                        else:
                            offset = bg_image_width * 3 / 4  # Three quarters of the way
                    else:
                        offset = initial_offsets[i]

                    del _temp_layer  # Clean up temporary layer

                    # Create the actual layer with appropriate offsets and speed
                    layer = BackgroundLayer(
                        bg_image_path,
                        speed,
                        self.current_screen_height,
                        initial_scroll=offset,
                        vertical_offset=vertical_offsets[i],  # Apply same vertical offset
                    )
                    self.background_layers.append(layer)

                except (pygame.error, FileNotFoundError, ZeroDivisionError, AttributeError) as e:
                    logger.warning(f"Could not load background image {image_name}: {e}")
            else:
                logger.warning(f"Background image not found at {bg_image_path}")

        # Fallback if no backgrounds were loaded
        if not self.background_layers:
            logger.warning("No background images loaded. Using default starfield.")
            bg_image_path = os.path.join(BACKGROUNDS_DIR, "starfield.png")
            if os.path.exists(bg_image_path):
                for i, speed in enumerate(BG_LAYER_SPEEDS):
                    offset = initial_offsets[i % len(initial_offsets)]
                    layer = BackgroundLayer(
                        bg_image_path, speed, self.current_screen_height, initial_scroll=offset
                    )
                    self.background_layers.append(layer)
            else:
                logger.warning(
                    f"Default background image not found at {bg_image_path}. No backgrounds will be used."
                )

        # Initialize background decorations
        decoration_paths = []
        for i in range(1, DECORATION_FILES + 1):
            decoration_path = os.path.join(BACKGROUNDS_DIR, f"decoration{i}.png")
            if os.path.exists(decoration_path):
                decoration_paths.append(decoration_path)
            else:
                logger.warning(f"Decoration image not found: {decoration_path}")

        # Check if we have any decoration files
        if len(decoration_paths) == 0:
            logger.warning("No decoration files found. Background decorations will be disabled.")

        # Create the decorations layer with a middle-ground scroll speed (between layer speeds)
        self.bg_decorations = BackgroundDecorations(
            decoration_paths=decoration_paths,
            scroll_speed=1.2,  # Speed between background layer speeds
            screen_width=self.current_screen_width,
            screen_height=self.current_screen_height,
            playfield_top=PLAYFIELD_TOP_Y,
            playfield_bottom=PLAYFIELD_BOTTOM_Y,
        )

        # Initialize border layers
        self.borders = []
        top_border_path = os.path.join(BACKGROUNDS_DIR, "border-upper.png")
        bottom_border_path = os.path.join(BACKGROUNDS_DIR, "border-lower.png")

        # Add top border
        if os.path.exists(top_border_path):
            self.borders.append(Border(top_border_path, True, 1.5))
        else:
            logger.warning(f"Top border image not found at {top_border_path}")

        # Add bottom border
        if os.path.exists(bottom_border_path):
            self.borders.append(Border(bottom_border_path, False, 1.5))
        else:
            logger.warning(f"Bottom border image not found at {bottom_border_path}")

        # Initialize sprite groups
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()  # Group for enemies
        self.bullets = pygame.sprite.Group()  # Group specifically for bullets
        self.enemy_bullets = pygame.sprite.Group()  # Group for enemy bullets
        self.explosions = pygame.sprite.Group()  # Group for explosion effects
        self.particles = pygame.sprite.Group()  # Group for particles
        self.powerups = pygame.sprite.Group()  # Group for powerups
        self.notifications = pygame.sprite.Group()  # Group for text notifications

        # Initialize game components
        self.player = Player(self.bullets, self.all_sprites, game_ref=self)
        # self.level_manager = LevelManager() # Not used yet

        # Load the game logo
        logo_path = os.path.join("assets", "images", "logo.png")
        try:
            self.logo = pygame.image.load(logo_path).convert_alpha()
            # Scale the logo to an appropriate size for the top of the screen
            # Increase logo height by 50% (from 20% to 30% of screen height)
            logo_height = int(SCREEN_HEIGHT * 0.3)  # 30% of screen height (50% bigger than before)
            logo_width = int(logo_height * (self.logo.get_width() / self.logo.get_height()))
            self.logo = pygame.transform.scale(self.logo, (logo_width, logo_height))

            # Apply alpha transparency from config
            logo_with_alpha = self.logo.copy()
            logo_with_alpha.fill((255, 255, 255, LOGO_ALPHA), None, pygame.BLEND_RGBA_MULT)
            self.logo = logo_with_alpha

            logger.info(f"Loaded game logo: {logo_path}")
        except (pygame.error, FileNotFoundError) as e:
            logger.error(f"Failed to load game logo: {e}")
            self.logo = None

        # Initialize sound manager
        self.sound_manager = SoundManager()

        # Laser sound timer - for continuous fire sound
        self.last_laser_sound_time = 0

        # Enemy bullet tracking
        self.previous_enemy_bullet_count = 0

        # Simple wave management state
        self.wave_active = False
        self.wave_count = 0  # Track number of waves for difficulty progression
        self.max_wave_count = 0  # Track maximum wave reached
        pygame.time.set_timer(WAVE_TIMER_EVENT, WAVE_DELAY_MS)  # Timer for next wave

        # Game over state
        self.game_over = False
        self.game_over_font = pygame.font.SysFont(None, DEFAULT_FONT_SIZE * 2)

        # Game over animation
        self.game_over_start_time = 0
        self.game_over_animation_duration = 3000  # 3 seconds total animation
        self.game_over_animation_complete = False

        # Load game over image
        game_over_path = os.path.join("assets", "images", "game-over.png")
        try:
            self.game_over_image = pygame.image.load(game_over_path).convert_alpha()
            # Scale to reasonable size
            img_width, img_height = self.game_over_image.get_size()
            scale_factor = min(SCREEN_WIDTH * 0.7 / img_width, SCREEN_HEIGHT * 0.4 / img_height)
            new_size = (int(img_width * scale_factor), int(img_height * scale_factor))
            self.game_over_image = pygame.transform.scale(self.game_over_image, new_size)
            logger.info(f"Loaded game over image: {game_over_path}")
        except (pygame.error, FileNotFoundError) as e:
            logger.error(f"Failed to load game over image: {e}")
            self.game_over_image = None

        # Scoring system
        self.score = 0
        self.score_font = pygame.font.SysFont(None, DEFAULT_FONT_SIZE)
        self.previous_player_power = self.player.power_level

        # Powerup system
        self.powerup_timer = 0
        # Calculate initial spawn interval based on difficulty
        self.powerup_spawn_interval = self._calculate_powerup_interval()
        self.last_powerup_time = pygame.time.get_ticks()
        # Track the last spawned powerup type to avoid repeats
        self.last_powerup_type = None

        # Don't spawn a powerup immediately
        self.last_powerup_time = pygame.time.get_ticks() + 10000  # 10 second initial delay

        # Initialize enemy pools and preload sprites
        self._init_enemy_pools()

        # Add boss-related attributes
        self.boss = None
        self.is_boss_battle = False
        self.boss_bullets = pygame.sprite.Group()  # Initialize as empty group
        self.boss_sprites = pygame.sprite.Group()  # Initialize boss sprites group
        self.boss_defeated = False

    def _init_enemy_pools(self):
        """Initialize object pools for enemies to reduce instantiation overhead."""
        # Create sprite sheet cache to avoid reloading the same sheets
        self.sprite_sheet_cache = {}
        
        # Create enemy pools with preloaded instances
        self.enemy_pools = {}
        for enemy_type in range(8):  # We have 8 enemy types (0-7)
            self.enemy_pools[enemy_type] = deque()
            
        # Preload some instances for each enemy type
        self._preload_enemy_instances()
    
    def _preload_enemy_instances(self):
        """Preload some enemy instances to avoid instantiation during gameplay."""
        # Number of instances to preload for each enemy type
        preload_count = 10
        
        # Temporarily create enemy instances outside the visible area
        for enemy_type in range(8):
            for _ in range(preload_count):
                enemy = self._create_enemy_instance(enemy_type)
                if enemy:
                    # Move it off-screen
                    enemy.topleft = (SCREEN_WIDTH * 2, 0)
                    # Kill it to remove from sprite groups but keep the instance
                    enemy.kill()
                    # Store in the appropriate pool
                    self.enemy_pools[enemy_type].append(enemy)
    
    def _create_enemy_instance(self, enemy_type_index):
        """Create a new enemy instance of the specified type."""
        if enemy_type_index == 0:
            return EnemyType1(self.all_sprites, self.enemies)
        elif enemy_type_index == 1:
            return EnemyType2(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
        elif enemy_type_index == 2:
            return EnemyType3(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
        elif enemy_type_index == 3:
            return EnemyType4(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
        elif enemy_type_index == 4:
            return EnemyType5(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
        elif enemy_type_index == 5:
            return EnemyType6(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
        elif enemy_type_index == 6:
            return EnemyType7(self.player, self.enemy_bullets, self.all_sprites, self.enemies, game_ref=self)
        elif enemy_type_index == 7:
            return EnemyType8(self.player, self.all_sprites, self.enemies)
        return None
    
    def _get_enemy_from_pool(self, enemy_type_index):
        """Get an enemy from the pool or create a new one if the pool is empty."""
        if enemy_type_index in self.enemy_pools and self.enemy_pools[enemy_type_index]:
            # Reuse an existing enemy from the pool
            enemy = self.enemy_pools[enemy_type_index].popleft()
            if enemy:
                # Add it back to the sprite groups
                self.all_sprites.add(enemy)
                self.enemies.add(enemy)
                # Reset its state (position will be set by the caller)
                if hasattr(enemy, 'reset'):
                    enemy.reset()
                return enemy
        
        # Create a new enemy if the pool is empty or we got None
        return self._create_enemy_instance(enemy_type_index)

    def run(self):
        """Starts and manages the main game loop."""
        # No longer force spawn a powerup at start

        # Reset the wave timer when the game starts running
        # This ensures waves will spawn correctly even after multiple screen transitions
        pygame.time.set_timer(WAVE_TIMER_EVENT, WAVE_DELAY_MS)
        logger.info("Wave timer reset at game start")
        
        while self.is_running:
            # Check for window resize events (optional but good for resizable window) - REMOVED
            # self.handle_resize()
            self._handle_events()
            self._update()
            self._render()
            self.clock.tick(FPS)  # Use FPS from config

        pygame.quit()

    def _handle_events(self):
        """Process all game events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.is_running = False
                # Add debug key handlers
                elif event.key in [pygame.K_F1, pygame.K_F2, pygame.K_F3, pygame.K_F4, 
                                  pygame.K_F5, pygame.K_F6, pygame.K_F7, pygame.K_F8]:
                    self._handle_debug_keys(event)
                elif event.key == pygame.K_SPACE:
                    if self.game_over and self.game_over_animation_complete:
                        # Only allow restart when animation is complete
                        self._reset_game()
                    elif not self.player.is_firing:
                        self.player.start_firing()
                        # Initial laser sound will be handled in _update

                # B key for Scatter Bomb - check state dict
                elif event.key == pygame.K_b:
                    scatter_state = self.player.active_powerups_state.get("SCATTER_BOMB")
                    if scatter_state and scatter_state.get("charges", 0) > 0:
                        # Player method handles checking state and firing
                        self.player._fire_scatter_bomb()
                        logger.info("Scatter Bomb triggered with B key")

                # Volume control keys
                elif event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:
                    current_volume = pygame.mixer.music.get_volume()
                    self.sound_manager.set_music_volume(max(0.0, current_volume - 0.1))
                    logger.info(f"Music volume: {pygame.mixer.music.get_volume():.1f}")

                elif (
                    event.key == pygame.K_PLUS
                    or event.key == pygame.K_KP_PLUS
                    or event.key == pygame.K_EQUALS
                ):
                    current_volume = pygame.mixer.music.get_volume()
                    self.sound_manager.set_music_volume(min(1.0, current_volume + 0.1))
                    logger.info(f"Music volume: {pygame.mixer.music.get_volume():.1f}")

                # Music toggle (M key)
                elif event.key == pygame.K_m:
                    if pygame.mixer.music.get_busy():
                        self.sound_manager.pause_music()
                        logger.info("Music paused")
                    else:
                        self.sound_manager.unpause_music()
                        logger.info("Music resumed")

                # Log level controls (1-5 keys) - for development/debugging
                elif event.key == pygame.K_1:
                    setup_logger(logging.DEBUG)
                    logger.debug("Log level set to DEBUG")
                elif event.key == pygame.K_2:
                    setup_logger(logging.INFO)
                    logger.info("Log level set to INFO")
                elif event.key == pygame.K_3:
                    setup_logger(logging.WARNING)
                    logger.warning("Log level set to WARNING")
                elif event.key == pygame.K_4:
                    setup_logger(logging.ERROR)
                    logger.error("Log level set to ERROR")
                elif event.key == pygame.K_5:
                    setup_logger(logging.CRITICAL)
                    logger.critical("Log level set to CRITICAL")

                elif event.key == pygame.K_t:
                    # Test mode - spawn one of each enemy type
                    logger.info("Test mode - spawning all enemy types")

                    # Spawn position
                    x_pos = SCREEN_WIDTH - 100
                    y_spacing = (
                        PLAYFIELD_BOTTOM_Y - PLAYFIELD_TOP_Y
                    ) / 9  # Increased spacing for better visibility

                    # Spawn one of each enemy type
                    enemies = [
                        EnemyType1(self.all_sprites, self.enemies),
                        EnemyType2(self.player, self.enemy_bullets, self.all_sprites, self.enemies),
                        EnemyType3(self.player, self.enemy_bullets, self.all_sprites, self.enemies),
                        EnemyType4(self.player, self.enemy_bullets, self.all_sprites, self.enemies),
                        EnemyType5(self.player, self.enemy_bullets, self.all_sprites, self.enemies),
                        EnemyType6(self.player, self.enemy_bullets, self.all_sprites, self.enemies),
                        EnemyType7(self.player, self.enemy_bullets, self.all_sprites, self.enemies, game_ref=self),
                        EnemyType8(self.player, self.all_sprites, self.enemies),
                    ]

                    # Position them vertically stacked with descriptive text
                    enemy_names = ["Basic", "Shooter", "Wave", "Spiral", "Seeker", "Teleporter", "Reflector", "New Enemy"]
                    font = pygame.font.SysFont(None, 24)

                    for i, (enemy, name) in enumerate(zip(enemies, enemy_names)):
                        y_pos = PLAYFIELD_TOP_Y + (i + 1) * y_spacing
                        enemy.topleft = (x_pos, y_pos)

                        # Create a text label for the enemy - we'll draw it directly in render
                        text_surf = font.render(name, True, (255, 255, 255))
                        text_rect = text_surf.get_rect(
                            midright=(x_pos - 20, y_pos + enemy.rect.height // 2)
                        )
                        # Store the text surface and rect for later rendering
                        enemy.label_text = text_surf
                        enemy.label_rect = text_rect

                    # Log the test
                    logger.info(f"Spawned {len(enemies)} test enemies")

                elif event.key == pygame.K_p:
                    # Test mode - spawn all powerup types
                    logger.info("Test mode - spawning all powerup types")

                    # Spawn position - staggered offscreen
                    y_spacing = (PLAYFIELD_BOTTOM_Y - PLAYFIELD_TOP_Y) / 10

                    # Spawn one of each powerup type
                    for i in range(9):  # 9 powerup types (0-8)
                        # Spawn position staggered from top to bottom and right to left
                        x_pos = SCREEN_WIDTH + 20 + (i * 40)  # Stagger right to left
                        y_pos = PLAYFIELD_TOP_Y + (i + 1) * y_spacing

                        # Spawn the powerup
                        self._spawn_powerup_of_type(i, x_pos, y_pos)

            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    self.player.stop_firing()
            elif event.type == WAVE_TIMER_EVENT:
                # Skip wave spawning if game is over
                if self.game_over:
                    # Cancel the wave timer when game is over
                    pygame.time.set_timer(WAVE_TIMER_EVENT, 0)
                    return

                # Update wave count and difficulty
                self.wave_count += 1
                self.max_wave_count = max(self.max_wave_count, self.wave_count)
                self._update_difficulty()

                # Check if it's time for the boss battle
                if self.wave_count == BOSS_WAVE_NUMBER and not self.is_boss_battle and not self.boss_defeated:
                    logger.info("BOSS WAVE! Spawning boss battle!")
                    self._start_boss_battle()
                    # Longer delay before any further waves after boss is defeated
                    pygame.time.set_timer(WAVE_TIMER_EVENT, 0)  # Stop regular wave timer
                    return  # Skip normal wave spawning

                # Select a random pattern type
                pattern_type = random.randint(0, 3)  # 0-3 for our four pattern types

                # Scale number of enemies based on difficulty (4-7 base, up to 8-12 at max difficulty)
                min_enemies = 4 + int(
                    (self.difficulty_level - 1) / 1.5
                )  # Increases by 1 every 1.5 difficulty levels (faster)
                max_enemies = 7 + int(
                    (self.difficulty_level - 1) / 1
                )  # Increases by 1 every difficulty level (faster)
                min_enemies = min(min_enemies, 10)
                max_enemies = min(max_enemies, 15)

                count = random.randint(min_enemies, max_enemies)

                # Get enemy weights based on current difficulty level
                enemy_weights = get_enemy_weights(self.difficulty_level)

                # Log weights for debugging if needed
                if self.wave_count % 5 == 0:  # Log every 5 waves
                    logger.debug(f"Enemy weights: {enemy_weights}")

                # Choose an enemy type based on the weights or use debug enemy type
                if DEBUG_FORCE_ENEMY_TYPE:
                    enemy_type_index = DEBUG_ENEMY_TYPE_INDEX
                    logger.info(f"DEBUG: Forcing enemy type {DEBUG_ENEMY_TYPE_INDEX}")
                else:
                    enemy_type_index = random.choices(
                        list(range(len(enemy_weights))),
                        weights=enemy_weights,
                        k=1,
                    )[0]

                # Get enemy name for logging
                enemy_name = ENEMY_TYPE_NAMES.get(enemy_type_index, f"Unknown({enemy_type_index})")

                logger.info(
                    f"Wave {self.wave_count} - Difficulty {self.difficulty_level:.1f}: Spawning {count} {enemy_name} enemies with pattern {pattern_type}"
                )
                self.spawn_enemy_wave(
                    count, pattern_type=pattern_type, enemy_type_index=enemy_type_index
                )

                # Calculate next wave delay based on difficulty (quicker waves at higher difficulty)
                # Base delay decreases as difficulty increases
                base_delay = max(3000, 7000 - int(self.difficulty_level * 400))

                # Add random variation (±20%)
                variation = int(base_delay * 0.2)  # 20% of base delay
                next_wave_delay = random.randint(base_delay - variation, base_delay + variation)

                # Ensure minimum and maximum bounds
                next_wave_delay = max(2000, min(next_wave_delay, 8000))

                # Set timer for next wave
                pygame.time.set_timer(WAVE_TIMER_EVENT, next_wave_delay)
                logger.debug(f"Next wave in {next_wave_delay/1000:.1f} seconds")

    def _update_difficulty(self):
        """Updates the difficulty level based on game progression."""
        # Increase difficulty with each wave, but cap at maximum
        self.difficulty_level = min(
            self.max_difficulty, 1.0 + (self.wave_count * self.difficulty_increase_rate)
        )

        # Calculate modified cooldown times based on difficulty
        # Faster shooting at higher difficulty (up to 70% reduction)
        cooldown_reduction = min(
            0.7, (self.difficulty_level - 1) * 0.1
        )

        # Override global cooldown with difficulty-adjusted value
        import src.enemy

        src.enemy.ENEMY_SHOOTER_COOLDOWN_MS = int(
            ENEMY_SHOOTER_COOLDOWN_MS * (1.0 - cooldown_reduction)
        )

        # Display difficulty level in the console for debugging
        if self.wave_count % 5 == 0:  # Log every 5 waves
            logger.info(
                f"Difficulty increased to: {self.difficulty_level:.1f} (Wave {self.wave_count})"
            )
            logger.info(
                f"Enemy cooldown reduced to: {src.enemy.ENEMY_SHOOTER_COOLDOWN_MS}ms (from {ENEMY_SHOOTER_COOLDOWN_MS}ms)"
            )

    def spawn_enemy_wave(self, count: int, pattern_type: int = 0, enemy_type_index: int = 0):
        """Creates a new wave of enemies based on the given pattern type."""
        # Apply difficulty-based speed modifier
        speed_modifier = (
            1.0 + (self.difficulty_level - 1) * 0.15
        )

        # Define border margin to keep enemies away from borders
        border_margin = 50  # Pixels to keep away from top/bottom playfield borders

        if pattern_type == PatternType.VERTICAL:
            # Vertical formation - enemies in a vertical line
            # Calculate spacing based on playfield height and enemy count
            playfield_height = PLAYFIELD_BOTTOM_Y - PLAYFIELD_TOP_Y
            spacing = playfield_height / (count + 1)  # +1 for proper spacing at edges
            self._spawn_vertical_pattern(count, int(spacing), enemy_type_index, speed_modifier)

        elif pattern_type == PatternType.HORIZONTAL:
            # Horizontal formation - enemies in a horizontal line
            self._spawn_horizontal_pattern(count, enemy_type_index, speed_modifier)

        elif pattern_type == PatternType.DIAGONAL:
            # Diagonal formation - enemies in a diagonal line
            self._spawn_diagonal_pattern(count, enemy_type_index, speed_modifier)

        elif (
            pattern_type == PatternType.V_SHAPE
        ):
            self._spawn_v_pattern(count, enemy_type_index, speed_modifier)

        else:
            # Default to vertical pattern if unknown pattern type
            logger.warning(f"Unknown pattern type: {pattern_type}. Using vertical formation.")
            playfield_height = PLAYFIELD_BOTTOM_Y - PLAYFIELD_TOP_Y
            spacing = playfield_height / (count + 1)
            self._spawn_vertical_pattern(count, int(spacing), enemy_type_index, speed_modifier)

    def _spawn_vertical_pattern(
        self, count: int, spacing_y: int, enemy_type_index: int = 0, speed_modifier: float = 1.0
    ):
        """Creates a vertical line of enemies entering from right."""
        # Calculate positioning parameters (this doesn't change)
        playfield_height = PLAYFIELD_BOTTOM_Y - PLAYFIELD_TOP_Y
        border_margin = 50
        usable_height = playfield_height - (2 * border_margin)
        enemy_height = 40
        total_height = (count - 1) * spacing_y + enemy_height
        start_y = PLAYFIELD_TOP_Y + border_margin + (usable_height - total_height) // 2
        x_pos = SCREEN_WIDTH + 50

        # Batch enemy creation for improved performance
        for i in range(count):
            y_pos = start_y + i * spacing_y
            
            # Get an enemy from the pool instead of creating a new one
            enemy = self._get_enemy_from_pool(enemy_type_index)
            
            # Skip if we couldn't create a valid enemy
            if not enemy:
                continue
            
            # Apply speed modifier based on difficulty
            if hasattr(enemy, 'speed_x'):
                enemy.speed_x *= speed_modifier
            
            # Reset timers and cooldowns
            if isinstance(enemy, EnemyType2):
                enemy.last_shot_time = pygame.time.get_ticks()
            elif isinstance(enemy, EnemyType3):
                enemy.last_shot_time = pygame.time.get_ticks()
            elif isinstance(enemy, EnemyType4):
                enemy.last_shot_time = pygame.time.get_ticks()
                enemy.last_homing_shot_time = pygame.time.get_ticks()
                enemy.homing_shot_cooldown = max(1000, int(enemy.homing_shot_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType5):
                enemy.last_explosive_shot_time = pygame.time.get_ticks()
                enemy.last_homing_shot_time = pygame.time.get_ticks()
                enemy.explosive_cooldown = max(1000, int(enemy.explosive_cooldown / speed_modifier))
                enemy.homing_cooldown = max(1000, int(enemy.homing_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType6):
                enemy.last_shot_time = pygame.time.get_ticks()
                enemy.last_teleport_time = pygame.time.get_ticks()
                enemy.teleport_delay = max(1000, int(enemy.teleport_delay / speed_modifier))
            elif isinstance(enemy, EnemyType7):
                enemy.last_reflection_time = pygame.time.get_ticks()
                enemy.last_laser_time = pygame.time.get_ticks()
                enemy.reflection_cooldown = max(1000, int(enemy.reflection_cooldown / speed_modifier))
                enemy.laser_cooldown = max(1000, int(enemy.laser_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType8):
                enemy.last_charge_time = pygame.time.get_ticks()
                enemy.charge_cooldown = max(1000, int(enemy.charge_cooldown / speed_modifier))

            # Position the enemy
            if hasattr(enemy, 'topleft'):
                enemy.topleft = (x_pos, y_pos)

    def _spawn_horizontal_pattern(
        self, count: int, enemy_type_index: int = 0, speed_modifier: float = 1.0
    ):
        """Creates a horizontal line of enemies entering from right."""
        # Spacing between enemies horizontally
        spacing_x = 60

        # Apply border margin to prevent spawning too close to borders
        border_margin = 50

        # Center the pattern vertically in the playfield with border margin
        playfield_center_y = (PLAYFIELD_TOP_Y + PLAYFIELD_BOTTOM_Y) // 2
        # Adjust center position if too close to borders
        y_pos = max(
            PLAYFIELD_TOP_Y + border_margin,
            min(PLAYFIELD_BOTTOM_Y - border_margin, playfield_center_y),
        )

        # Base horizontal position
        base_x = SCREEN_WIDTH + 50

        # Create the enemies
        for i in range(count):
            x_pos = base_x + i * spacing_x

            # Get an enemy from the pool instead of creating a new one
            enemy = self._get_enemy_from_pool(enemy_type_index)
            
            # Skip if we couldn't create a valid enemy
            if not enemy:
                continue
            
            # Apply speed modifier based on difficulty
            if hasattr(enemy, 'speed_x'):
                enemy.speed_x *= speed_modifier
            
            # Reset timers and cooldowns - same for all patterns
            if isinstance(enemy, EnemyType2):
                enemy.last_shot_time = pygame.time.get_ticks()
            elif isinstance(enemy, EnemyType3):
                enemy.last_shot_time = pygame.time.get_ticks()
            elif isinstance(enemy, EnemyType4):
                enemy.last_shot_time = pygame.time.get_ticks()
                enemy.last_homing_shot_time = pygame.time.get_ticks()
                enemy.homing_shot_cooldown = max(1000, int(enemy.homing_shot_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType5):
                enemy.last_explosive_shot_time = pygame.time.get_ticks()
                enemy.last_homing_shot_time = pygame.time.get_ticks()
                enemy.explosive_cooldown = max(1000, int(enemy.explosive_cooldown / speed_modifier))
                enemy.homing_cooldown = max(1000, int(enemy.homing_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType6):
                enemy.last_shot_time = pygame.time.get_ticks()
                enemy.last_teleport_time = pygame.time.get_ticks()
                enemy.teleport_delay = max(1000, int(enemy.teleport_delay / speed_modifier))
            elif isinstance(enemy, EnemyType7):
                enemy.last_reflection_time = pygame.time.get_ticks()
                enemy.last_laser_time = pygame.time.get_ticks()
                enemy.reflection_cooldown = max(1000, int(enemy.reflection_cooldown / speed_modifier))
                enemy.laser_cooldown = max(1000, int(enemy.laser_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType8):
                enemy.last_charge_time = pygame.time.get_ticks()
                enemy.charge_cooldown = max(1000, int(enemy.charge_cooldown / speed_modifier))

            # Position the enemy
            if hasattr(enemy, 'topleft'):
                enemy.topleft = (x_pos, y_pos)

    def _spawn_diagonal_pattern(
        self, count: int, enemy_type_index: int = 0, speed_modifier: float = 1.0
    ):
        """Creates a diagonal line of enemies entering from right."""
        # Apply larger border margin to prevent spawning outside visible area
        border_margin = 70
        
        # Use even larger margin for EnemyType7 which has a taller sprite
        if enemy_type_index == 6:  # EnemyType7 index is 6
            border_margin = 100  # Extra large margin for the Reflector enemy
        
        # Calculate usable playfield height
        playfield_height = PLAYFIELD_BOTTOM_Y - PLAYFIELD_TOP_Y - (2 * border_margin)
        
        # Fixed horizontal spacing
        spacing_x = 60
        
        # Direction - negative for diagonal down, positive for diagonal up
        direction = 1 if random.random() < 0.5 else -1
        
        # Calculate maximum safe vertical distance
        max_vertical_distance = (count - 1) * 60  # Using max possible spacing of 60
        
        # Check if the pattern would exceed playfield bounds and adjust spacing if needed
        if max_vertical_distance > playfield_height:
            # Scale down spacing to fit within available height
            spacing_y = (playfield_height * 0.8) / (count - 1) if count > 1 else playfield_height
        else:
            spacing_y = min(60, playfield_height / (count + 1))  # Use default spacing if it fits, with extra safety margin
        
        # Set safe boundaries for enemy spawn positions
        safe_top = PLAYFIELD_TOP_Y + border_margin
        safe_bottom = PLAYFIELD_BOTTOM_Y - border_margin
        
        # Calculate start position based on direction
        if direction == 1:  # Diagonal up
            # Start at a safer position (higher up from bottom)
            start_y = safe_bottom - 20
            if enemy_type_index == 6:  # Additional offset for EnemyType7
                start_y -= 30
        else:  # Diagonal down
            # Start at a safer position (lower down from top)
            start_y = safe_top + 20
            if enemy_type_index == 6:  # Additional offset for EnemyType7
                start_y += 30
        
        start_x = SCREEN_WIDTH + 50
        
        # Create the enemies
        for i in range(count):
            x_pos = start_x + i * spacing_x
            y_pos = start_y + (i * spacing_y * direction)
            
            # Apply strict bounds checking - ensure enemies always stay within safe area
            y_pos = max(safe_top, min(safe_bottom, y_pos))
            
            # Get an enemy from the pool instead of creating a new one
            enemy = self._get_enemy_from_pool(enemy_type_index)
            
            # Skip if we couldn't create a valid enemy
            if not enemy:
                continue
                
            # Apply speed modifier based on difficulty
            if hasattr(enemy, 'speed_x'):
                enemy.speed_x *= speed_modifier
            
            # Reset timers and cooldowns - using the same code for all patterns
            if isinstance(enemy, EnemyType2):
                enemy.last_shot_time = pygame.time.get_ticks()
            elif isinstance(enemy, EnemyType3):
                enemy.last_shot_time = pygame.time.get_ticks()
            elif isinstance(enemy, EnemyType4):
                enemy.last_shot_time = pygame.time.get_ticks()
                enemy.last_homing_shot_time = pygame.time.get_ticks()
                enemy.homing_shot_cooldown = max(1000, int(enemy.homing_shot_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType5):
                enemy.last_explosive_shot_time = pygame.time.get_ticks()
                enemy.last_homing_shot_time = pygame.time.get_ticks()
                enemy.explosive_cooldown = max(1000, int(enemy.explosive_cooldown / speed_modifier))
                enemy.homing_cooldown = max(1000, int(enemy.homing_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType6):
                enemy.last_shot_time = pygame.time.get_ticks()
                enemy.last_teleport_time = pygame.time.get_ticks()
                enemy.teleport_delay = max(1000, int(enemy.teleport_delay / speed_modifier))
            elif isinstance(enemy, EnemyType7):
                enemy.last_reflection_time = pygame.time.get_ticks()
                enemy.last_laser_time = pygame.time.get_ticks()
                enemy.reflection_cooldown = max(1000, int(enemy.reflection_cooldown / speed_modifier))
                enemy.laser_cooldown = max(1000, int(enemy.laser_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType8):
                enemy.last_charge_time = pygame.time.get_ticks()
                enemy.charge_cooldown = max(1000, int(enemy.charge_cooldown / speed_modifier))

            # Position the enemy - here we use set_pos to ensure center is positioned properly
            if hasattr(enemy, 'topleft'):
                enemy.topleft = (x_pos, y_pos)
                
                # Final safety check - if still out of bounds after positioning, adjust
                if hasattr(enemy, 'rect'):
                    # More aggressive adjustment for EnemyType7 which has a taller sprite
                    bottom_margin = 40 if isinstance(enemy, EnemyType7) else 20
                    top_margin = 40 if isinstance(enemy, EnemyType7) else 20
                    
                    if enemy.rect.bottom > PLAYFIELD_BOTTOM_Y - bottom_margin:
                        # If bottom is too low, pull it up
                        enemy.rect.bottom = PLAYFIELD_BOTTOM_Y - bottom_margin
                        if hasattr(enemy, '_pos_y'):
                            enemy._pos_y = float(enemy.rect.y)
                    elif enemy.rect.top < PLAYFIELD_TOP_Y + top_margin:
                        # If top is too high, push it down
                        enemy.rect.top = PLAYFIELD_TOP_Y + top_margin
                        if hasattr(enemy, '_pos_y'):
                            enemy._pos_y = float(enemy.rect.y)

    def _spawn_v_pattern(self, count: int, enemy_type_index: int = 0, speed_modifier: float = 1.0):
        """Creates a V-shaped formation of enemies entering from right."""
        # Need an odd number for the V-pattern to look symmetrical
        if count % 2 == 0:
            count += 1

        # Center enemy is at the front of the V
        center_index = count // 2

        # Spacing between enemies
        spacing_x = 40

        # Apply border margin to prevent spawning too close to borders
        border_margin = 50
        playfield_height = PLAYFIELD_BOTTOM_Y - PLAYFIELD_TOP_Y - (2 * border_margin)

        # Calculate maximum safe spacing to stay within borders
        max_enemies_from_center = center_index
        max_safe_spacing = (
            playfield_height / (2 * max_enemies_from_center) if max_enemies_from_center > 0 else 40
        )
        spacing_y = min(40, max_safe_spacing)  # Use smaller of default or safe spacing

        # Center position with border margin
        center_x = SCREEN_WIDTH + 50
        center_y = PLAYFIELD_TOP_Y + border_margin + (playfield_height // 2)

        # Create the enemies
        for i in range(count):
            # Calculate position relative to center
            index_from_center = i - center_index

            # X increases as we go away from center in either direction
            x_pos = center_x + abs(index_from_center) * spacing_x

            # Y increases as we go away from center
            y_pos = center_y + index_from_center * spacing_y

            # Get an enemy from the pool instead of creating a new one
            enemy = self._get_enemy_from_pool(enemy_type_index)
            
            # Skip if we couldn't create a valid enemy
            if not enemy:
                continue
            
            # Apply speed modifier based on difficulty
            if hasattr(enemy, 'speed_x'):
                enemy.speed_x *= speed_modifier
            
            # Reset timers and cooldowns - using the same code for all patterns
            if isinstance(enemy, EnemyType2):
                enemy.last_shot_time = pygame.time.get_ticks()
            elif isinstance(enemy, EnemyType3):
                enemy.last_shot_time = pygame.time.get_ticks()
            elif isinstance(enemy, EnemyType4):
                enemy.last_shot_time = pygame.time.get_ticks()
                enemy.last_homing_shot_time = pygame.time.get_ticks()
                enemy.homing_shot_cooldown = max(1000, int(enemy.homing_shot_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType5):
                enemy.last_explosive_shot_time = pygame.time.get_ticks()
                enemy.last_homing_shot_time = pygame.time.get_ticks()
                enemy.explosive_cooldown = max(1000, int(enemy.explosive_cooldown / speed_modifier))
                enemy.homing_cooldown = max(1000, int(enemy.homing_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType6):
                enemy.last_shot_time = pygame.time.get_ticks()
                enemy.last_teleport_time = pygame.time.get_ticks()
                enemy.teleport_delay = max(1000, int(enemy.teleport_delay / speed_modifier))
            elif isinstance(enemy, EnemyType7):
                enemy.last_reflection_time = pygame.time.get_ticks()
                enemy.last_laser_time = pygame.time.get_ticks()
                enemy.reflection_cooldown = max(1000, int(enemy.reflection_cooldown / speed_modifier))
                enemy.laser_cooldown = max(1000, int(enemy.laser_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType8):
                enemy.last_charge_time = pygame.time.get_ticks()
                enemy.charge_cooldown = max(1000, int(enemy.charge_cooldown / speed_modifier))

            # Position the enemy
            if hasattr(enemy, 'topleft'):
                enemy.topleft = (x_pos, y_pos)

    def _update(self):
        """Update game state for the current frame."""
        # Don't update if paused
        if self.is_paused:
            return

        # Don't update if game over (only animate explosions)
        if self.game_over:
            # Still update explosions during game over
            self.explosions.update()
            return

        # Process keyboard input for player movement
        keys = pygame.key.get_pressed()

        # Reset movement speeds
        self.player.speed_x = 0
        self.player.speed_y = 0

        # Set movement based on keys
        if keys[pygame.K_UP]:
            self.player.speed_y = -PLAYER_SPEED
        if keys[pygame.K_DOWN]:
            self.player.speed_y = PLAYER_SPEED
        if keys[pygame.K_LEFT]:
            self.player.speed_x = -PLAYER_SPEED
        if keys[pygame.K_RIGHT]:
            self.player.speed_x = PLAYER_SPEED

        # Handle continuous laser sounds
        current_time = pygame.time.get_ticks()
        if self.player.is_firing and current_time - self.last_laser_sound_time > PLAYER_SHOOT_DELAY:
            # Play laser sound when the player fires
            try:
                self.sound_manager.play("laser", "player")
                self.last_laser_sound_time = current_time
            except Exception as e:
                logger.warning(f"Failed to play laser sound: {e}")
        elif not self.player.is_firing:
            # Reset the laser sound timer when player stops firing
            # This ensures the sound will play immediately when firing resumes
            self.last_laser_sound_time = 0

        # Check for new enemy bullets by comparing counts
        current_enemy_bullet_count = len(self.enemy_bullets)
        if current_enemy_bullet_count > self.previous_enemy_bullet_count:
            # New enemy bullets were created
            try:
                self.sound_manager.play("laser", "enemy")
            except Exception as e:
                logger.warning(f"Failed to play enemy laser sound: {e}")
        self.previous_enemy_bullet_count = current_enemy_bullet_count

        # Update background layers
        for layer in self.background_layers:
            layer.update()

        # Update background decorations
        self.bg_decorations.update()

        # Update border layers
        for border in self.borders:
            border.update()

        # Update player and other sprites
        self.all_sprites.update()  # This calls update() on Player, Bullets, and Enemies
        self.enemy_bullets.update()
        self.explosions.update()  # Update explosion animations
        self.particles.update()  # Update particles
        self.powerups.update()  # Update powerups
        self.notifications.update()  # Update text notifications

        # Check if it's time to spawn a powerup
        self._check_powerup_spawn()

        # Apply time warp effect if active (check state dict)
        time_warp_active = "TIME_WARP" in self.player.active_powerups_state

        # --- Apply Time Warp Effect ---
        for enemy in self.enemies:
            is_slowed = hasattr(enemy, "is_time_warped") and enemy.is_time_warped

            if time_warp_active and not is_slowed:
                # Apply slow effect
                if hasattr(enemy, "speed_x"):
                    if not hasattr(enemy, "original_speed_x"):  # Store original only once
                        enemy.original_speed_x = enemy.speed_x
                        enemy.original_speed_y = getattr(enemy, "speed_y", 0)
                    enemy.speed_x *= 0.5
                    if hasattr(enemy, "speed_y"):
                        enemy.speed_y *= 0.5
                enemy.is_time_warped = True  # Mark as slowed

            elif not time_warp_active and is_slowed:
                # Restore original speed
                if hasattr(enemy, "original_speed_x"):
                    enemy.speed_x = enemy.original_speed_x
                    if hasattr(enemy, "original_speed_y"):
                        enemy.speed_y = enemy.original_speed_y
                enemy.is_time_warped = False  # Mark as normal speed

        # Slow down enemy bullets
        for bullet in self.enemy_bullets:
            is_slowed = hasattr(bullet, "is_time_warped") and bullet.is_time_warped

            if time_warp_active and not is_slowed:
                # Apply slow effect
                if hasattr(bullet, "velocity"):
                    if not hasattr(bullet, "original_velocity"):
                        bullet.original_velocity = bullet.velocity
                    bullet.velocity = (
                        bullet.original_velocity[0] * 0.5,
                        bullet.original_velocity[1] * 0.5,
                    )
                elif hasattr(bullet, "velocity_x"):
                    if not hasattr(bullet, "original_velocity_x"):
                        bullet.original_velocity_x = bullet.velocity_x
                        bullet.original_velocity_y = bullet.velocity_y
                    bullet.velocity_x *= 0.5
                    bullet.velocity_y *= 0.5
                bullet.is_time_warped = True  # Mark as slowed

            elif not time_warp_active and is_slowed:
                # Restore original speed
                if hasattr(bullet, "original_velocity"):
                    bullet.velocity = bullet.original_velocity
                elif hasattr(bullet, "original_velocity_x"):
                    bullet.velocity_x = bullet.original_velocity_x
                    bullet.velocity_y = bullet.original_velocity_y
                bullet.is_time_warped = False  # Mark as normal speed
        # --- End Time Warp Effect ---

        # Check for collisions
        self._handle_collisions()

        # Update boss
        if self.is_boss_battle and self.boss:
            try:
                # Update the boss sprite (handles regular movement or death animation)
                self.boss_sprites.update()

                # Check if the boss death animation is complete and cleanup is needed
                if self.boss.is_defeated and not self.boss_defeat_handled and hasattr(self.boss, 'animation_complete') and self.boss.animation_complete:
                    logger.info("Boss animation complete flag detected. Handling boss defeat.")
                    self._handle_boss_defeated()

                # --- Boss Firing Logic (only if not defeated/animating) --- 
                elif not self.boss.is_defeated and not self.boss.death_animation_active:
                    try:
                        # Calculate current interval based on phase
                        current_interval = self.boss.bullet_interval * (1.0 - (self.boss.phase - 1) * 0.2)
                        
                        # Check if it's time to fire
                        if self.boss.bullet_timer >= current_interval:
                            # Fire bullets using the pattern system
                            new_bullets = self.boss.fire_bullet()
                            bullet_count = 0
                            if new_bullets:
                                for bullet in new_bullets:
                                    if bullet is not None:
                                        self.boss_bullets.add(bullet)
                                        bullet_count += 1
                            
                            # Log for debugging
                            logger.debug(f"Boss fired {bullet_count} bullets using pattern: {self.boss.attack_pattern}")
                            
                            # Reset the boss's bullet timer
                            self.boss.bullet_timer = 0
                            
                    except Exception as e:
                        logger.error(f"Error creating boss bullets: {e}")
                
                # Update boss bullets (always update even during death anim to let them fly off)
                self.boss_bullets.update()
                
                # Remove bullets that are off-screen
                for bullet in list(self.boss_bullets):
                    if (bullet.rect.right < 0 or bullet.rect.left > SCREEN_WIDTH or
                        bullet.rect.bottom < 0 or bullet.rect.top > SCREEN_HEIGHT):
                        bullet.kill()

            except Exception as e:
                # Catch potential errors if self.boss becomes None unexpectedly during the try block
                if isinstance(e, AttributeError) and "'NoneType' object" in str(e):
                    logger.warning("Boss object became None during update, likely handled.")
                else:
                    logger.error(f"Error updating boss or its bullets: {e}")

        # Check for boss bullets hitting player
        if self.is_boss_battle and not self.player.is_invincible:
            boss_bullet_hits = pygame.sprite.spritecollide(
                self.player, self.boss_bullets, True, pygame.sprite.collide_mask
            )
            
            if boss_bullet_hits:
                # Calculate total damage
                total_damage = sum(getattr(bullet, 'damage', 1) for bullet in boss_bullet_hits)
                
                # Apply damage to player - take_damage() doesn't take any parameters
                self.player.take_damage()
                
                # Play hit sound - changed to a sound that likely exists
                if hasattr(self, 'sound_manager') and self.sound_manager:
                    try:
                        self.sound_manager.play("explosion1", "player")
                    except Exception as e:
                        logger.warning(f"Could not play player hit sound: {e}")
                
                # Check if player destroyed
                if not self.player.is_alive:
                    self._handle_game_over()

    def _check_powerup_spawn(self):
        """Check if it's time to spawn a powerup."""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_powerup_time > self.powerup_spawn_interval:
            self.last_powerup_time = current_time
            # Update the spawn interval for next time based on current difficulty
            self.powerup_spawn_interval = self._calculate_powerup_interval()
            self._spawn_powerup()

    def _calculate_powerup_interval(self) -> int:
        """Calculate powerup spawn interval based on current difficulty level.

        As difficulty increases, powerups spawn more frequently.

        Returns:
            Spawn interval in milliseconds
        """
        # Import the constants
        from config.config import (
            POWERUP_DIFFICULTY_SCALING,
            POWERUP_MAX_SPAWN_INTERVAL_MS,
            POWERUP_MIN_DIFFICULTY_INTERVAL_MS,
            POWERUP_MIN_SPAWN_INTERVAL_MS,
        )

        # Start with max interval at difficulty 1.0
        base_interval = POWERUP_MAX_SPAWN_INTERVAL_MS

        # Calculate reduction based on difficulty level
        difficulty_factor = self.difficulty_level - 1.0  # Zero at difficulty 1.0

        # Apply scaling: interval gets smaller as difficulty increases
        # Use exponential scaling to make the progression feel good
        interval = base_interval * (POWERUP_DIFFICULTY_SCALING**difficulty_factor)

        # Ensure we don't go below the minimum interval
        interval = max(POWERUP_MIN_DIFFICULTY_INTERVAL_MS, interval)

        # Add some randomness (±15%)
        variation = interval * 0.15
        interval = random.uniform(interval - variation, interval + variation)

        # Ensure final interval is within valid range
        interval = max(POWERUP_MIN_SPAWN_INTERVAL_MS, min(interval, POWERUP_MAX_SPAWN_INTERVAL_MS))

        logger.debug(
            f"Calculated powerup interval: {interval/1000:.1f}s at difficulty {self.difficulty_level:.1f}"
        )
        return int(interval)

    def _spawn_powerup(self):
        """Spawn a random powerup."""
        # Don't spawn powerups during the boss battle
        if self.is_boss_battle:
            return

        # Import for type checking
        from src.player import MAX_POWER_LEVEL

        # Check if we should force a specific powerup type
        if DEBUG_FORCE_POWERUP_TYPE:
            try:
                # Convert index to PowerupType enum value
                chosen_powerup_enum = PowerupType(DEBUG_POWERUP_TYPE_INDEX)
                powerup_type_index = chosen_powerup_enum.value
                powerup_type_name = chosen_powerup_enum.name
                logger.info(f"Debug mode: Forcing powerup type {powerup_type_name}")
            except ValueError:
                # Fallback if invalid index
                logger.warning(f"Invalid DEBUG_POWERUP_TYPE_INDEX: {DEBUG_POWERUP_TYPE_INDEX}, using random powerup")
                # Continue with normal random selection
                chosen_powerup_enum = self._select_random_powerup()
                powerup_type_index = chosen_powerup_enum.value
                powerup_type_name = chosen_powerup_enum.name
        else:
            # Normal random selection
            chosen_powerup_enum = self._select_random_powerup()
            powerup_type_index = chosen_powerup_enum.value
            powerup_type_name = chosen_powerup_enum.name

        # Remember this type to avoid repeating next time
        self.last_powerup_type = chosen_powerup_enum

        # Choose a spawn position just off the right side of the screen
        # at a random height within the play field
        x = SCREEN_WIDTH + 20  # Spawn off-screen to the right
        y = random.randint(PLAYFIELD_TOP_Y + 50, PLAYFIELD_BOTTOM_Y - 50)

        # Import here to avoid circular imports
        from src.powerup_types import create_powerup

        # Create the powerup using the integer index
        powerup = create_powerup(
            powerup_type_index,
            x,
            y,
            self.all_sprites,
            self.powerups,
            particles_group=self.particles,
            game_ref=self,  # Pass game reference to powerup
        )

        logger.info(f"Spawned powerup of type {powerup_type_name} at position ({x}, {y})")
        
    def _select_random_powerup(self):
        """Select a random powerup type, filtering out ineligible ones."""
        # Import for type checking
        from src.player import MAX_POWER_LEVEL
        from src.powerup import PowerupType, ACTIVE_POWERUP_TYPES
        
        # Filter out the last powerup type to avoid repetition
        available_types = list(ACTIVE_POWERUP_TYPES)
        if self.last_powerup_type is not None:
            try:
                available_types.remove(self.last_powerup_type)
            except ValueError:
                # Last type not in available types (shouldn't happen)
                pass

        # Filter out POWER_RESTORE if player already has max power
        if (
            self.player.power_level >= MAX_POWER_LEVEL
            and PowerupType.POWER_RESTORE in available_types
        ):
            available_types.remove(PowerupType.POWER_RESTORE)
            logger.debug(
                "Removed POWER_RESTORE from available powerups because player has max power"
            )

        # If we have no available types (shouldn't happen but just in case), use defaults
        if not available_types:
            available_types = [PowerupType.TRIPLE_SHOT, PowerupType.RAPID_FIRE, PowerupType.SHIELD]

        # Choose a random powerup type from the filtered list
        return random.choice(available_types)

    def _spawn_powerup_of_type(self, powerup_type: int, x: float, y: float) -> None:
        """Spawn a powerup of a specific type at a specified position.

        Args:
            powerup_type: Type of powerup to spawn (0-8)
            x: X-coordinate for spawn position
            y: Y-coordinate for spawn position
        """
        # Import here to avoid circular imports
        from src.powerup_types import create_powerup

        # Create the powerup using the integer index
        powerup = create_powerup(
            powerup_type,
            x,
            y,
            self.all_sprites,
            self.powerups,
            particles_group=self.particles,
            game_ref=self,  # Pass game reference to powerup
        )

        # Get the name from the Enum using the integer value
        try:
            powerup_name = PowerupType(powerup_type).name
        except ValueError:
            powerup_name = "Unknown"
        logger.info(f"Spawned powerup of type {powerup_name} at position ({x}, {y})")

    def _handle_collisions(self):
        """Check for and handle all game object collisions."""
        # Collision: Player Bullets vs Enemies
        # First, get all bullet-enemy collisions without killing them yet
        bullet_enemy_dict = pygame.sprite.groupcollide(
            self.bullets, self.enemies, False, False, pygame.sprite.collide_mask
        )

        for bullet, enemies_hit in bullet_enemy_dict.items():
            for enemy in enemies_hit:
                # Check if enemy is a Reflector with active shield
                if isinstance(enemy, EnemyType7) and enemy.reflection_active:
                    # Reflect bullet back at player
                    bullet.kill()
                    
                    # Calculate reflection angle (reverse direction and randomize slightly)
                    reflection_angle = random.uniform(-30, 30)  # Add some random spread
                    
                    # Create bullet at enemy position going in player's direction
                    from src.enemy_bullet import EnemyBullet
                    reflected_bullet = EnemyBullet(
                        enemy.rect.center, 
                        (enemy.rect.centerx - 100, enemy.rect.centery + reflection_angle),
                        self.enemy_bullets
                    )
                    
                    # Play reflection sound effect
                    try:
                        self.sound_manager.play("powerup1", "enemy") # Use powerup1 for reflection
                    except Exception as e:
                        # Fallback to another common sound if shield isn't available
                        try:
                            # self.sound_manager.play("hit1", "enemy") # Removed hit1 sound
                            pass # No fallback sound for reflection for now
                        except Exception:
                            logger.warning(f"Failed to play shield or fallback sound: {e}")
                else:
                    # Check if this is a flame particle or a regular bullet
                    if isinstance(bullet, FlameParticle):
                        # Flame particles apply partial damage and continue burning
                        if hasattr(enemy, "health"):
                            # Apply damage to existing health attribute
                            try:
                                # Get current health
                                current_health = getattr(enemy, "health", 100)
                                # Apply damage
                                new_health = current_health - bullet.damage
                                # Set new health
                                setattr(enemy, "health", new_health)
                                
                                # Create small flame effect at hit position
                                if self.particles:
                                    for _ in range(3):  # Create a few sparks
                                        # Random direction
                                        angle = random.uniform(0, 2 * math.pi)
                                        speed = random.uniform(0.5, 2.0)
                                        vel_x = math.cos(angle) * speed
                                        vel_y = math.sin(angle) * speed
                                        
                                        # Create spark particle
                                        FlameParticle(
                                            (bullet.rect.centerx, bullet.rect.centery),
                                            (vel_x, vel_y),
                                            (255, 60, 0),  # Fiery color
                                            random.randint(2, 4),  # Small size
                                            random.randint(10, 20),  # Short lifetime
                                            0,  # No additional damage for sparks
                                            self.particles
                                        )
                                
                                # Kill enemy if health <= 0
                                if new_health <= 0:
                                    self._process_enemy_destruction(enemy)
                                    enemy.kill()
                            except (AttributeError, TypeError):
                                # Fallback if attribute assignment fails
                                self._process_enemy_destruction(enemy)
                                enemy.kill()
                        else:
                            # Fallback if enemy doesn't use health system
                            self._process_enemy_destruction(enemy)
                            enemy.kill()
                        
                        # Kill the flame particle regardless (it's "used up" on contact)
                        bullet.kill()
                    else:
                        # Regular bullet behavior - instant kill
                        self._process_enemy_destruction(enemy)
                        enemy.kill()
                        bullet.kill()

        # Special collision handling for laser beams - they don't get destroyed on hit
        from src.projectile import LaserBeam
        for bullet in self.bullets:
            # Only process LaserBeam instances
            if isinstance(bullet, LaserBeam):
                # Check collisions with all enemies
                for enemy in self.enemies:
                    if pygame.sprite.collide_mask(bullet, enemy):
                        # Use the damage value from the laser beam
                        enemy.kill()
                        self._process_enemy_destruction(enemy)
                        
                        # Don't kill the laser beam - it continues through enemies
                        # But play a hit sound
                        try:
                            # self.sound_manager.play("hit1", "player") # Removed hit1 sound
                            pass # No sound for laser beam hitting enemy for now
                        except Exception as e:
                            logger.warning(f"Failed to play hit sound: {e}")

        # Skip collision handling if player is not alive
        if not self.player.is_alive:
            return

        # Collision: Player vs Powerups
        powerup_hits = pygame.sprite.spritecollide(
            self.player, self.powerups, True, pygame.sprite.collide_mask
        )
        for powerup in powerup_hits:
            # Apply the powerup effect
            powerup.apply_effect(self.player)

            # Get powerup name and color for notification
            # Use powerup_type_enum.name directly
            powerup_name = powerup.powerup_type_enum.name.replace("_", " ")

            # Colors for notification text (ensure order matches PowerupType Enum)
            notification_colors = {
                PowerupType.TRIPLE_SHOT: (255, 220, 0),
                PowerupType.RAPID_FIRE: (0, 255, 255),
                PowerupType.SHIELD: (0, 100, 255),
                PowerupType.HOMING_MISSILES: (255, 0, 255),
                PowerupType.POWER_RESTORE: (255, 255, 255),
                PowerupType.SCATTER_BOMB: (255, 128, 0),
                PowerupType.TIME_WARP: (128, 0, 255),
                PowerupType.MEGA_BLAST: (255, 0, 128),
                PowerupType.LASER_BEAM: (20, 255, 100),  # Bright Green (for Laser)
            }
            # Get color using the Enum member, default to white
            notification_color = notification_colors.get(powerup.powerup_type_enum, WHITE)

            # Create text notification sprite
            PowerupNotification(
                f"{powerup_name} Activated!",
                notification_color,
                self.player.rect.center,
                self.notifications,  # Add to the notifications group
            )

            # Play powerup sound - use try/except to handle any missing sounds
            try:
                self.sound_manager.play("powerup", "player")
            except Exception as e:
                logger.warning(f"Failed to play powerup sound: {e}")

        # We'll still detect collisions but damage handling is in take_damage
        # which checks for invincibility

        # Collision: Player vs Enemies
        # We check if the player sprite collides with any sprite in the enemies group.
        # True means the enemy sprite is killed on collision.
        # We handle player death/damage logic separately.
        enemy_hits = pygame.sprite.spritecollide(
            self.player, self.enemies, True, pygame.sprite.collide_mask
        )
        if enemy_hits:
            # Play enemy explosion sound for each enemy hit (when player collides with enemy)
            for enemy in enemy_hits:
                try:
                    # This plays the sound for the *enemy* exploding due to the collision
                    self.sound_manager.play("explosion2", "enemy")
                except Exception as e:
                    logger.warning(f"Failed to play explosion sound: {e}") # Generic warning

                # Create explosion at enemy position
                explosion_size = (50, 50)
                Explosion(
                    enemy.rect.center,
                    explosion_size,
                    "enemy",
                    self.explosions,
                    particles_group=self.particles,
                )
                logger.debug(f"Enemy destroyed by collision at {enemy.rect.center}")

            logger.warning("Player hit by enemy!")
            # Apply damage to player
            player_alive = self.player.take_damage()
            if not player_alive:
                self._handle_game_over()

        # Collision: Player vs Enemy Bullets
        bullet_hits = pygame.sprite.spritecollide(
            self.player, self.enemy_bullets, True, pygame.sprite.collide_mask
        )
        if bullet_hits:
            previous_power = self.player.power_level
            player_survived = self.player.take_damage()

            # Create power decrease particles if power changed
            if player_survived and previous_power > self.player.power_level:
                power_bar_pos = self.player.get_power_bar_particles_position()
                power_color = self.player.get_power_bar_color()
                PowerParticleSystem.create_power_change_effect(
                    power_bar_pos, power_color, is_decrease=True, group=self.particles
                )

            # Check for game over
            if not player_survived:
                self._handle_game_over()

        # Check for player bullets hitting boss
        if self.is_boss_battle and self.boss and not self.boss.is_defeated:
            try:
                boss_hits = pygame.sprite.spritecollide(
                    self.boss, self.bullets, True, pygame.sprite.collide_mask
                )
                
                # Process damage if boss was hit
                if boss_hits:
                    # Use a default damage of 1 for each bullet that doesn't have a damage attribute
                    total_damage = sum(getattr(bullet, 'damage', 1) for bullet in boss_hits)
                    
                    # Flag to store defeat status from take_damage
                    boss_was_defeated_this_frame = False
                    
                    try:
                        # Call take_damage, which returns True if this hit defeats the boss
                        boss_was_defeated_this_frame = self.boss.take_damage(total_damage, boss_hits[0].rect.center) # Pass hit positio
                        
                    except Exception as e:
                        logger.error(f"Error in boss take_damage: {e}")
                    
                    # Play hit sound
                    if hasattr(self, 'sound_manager') and self.sound_manager:
                        try:
                            self.sound_manager.play("explosion2", "enemy")
                        except Exception as e:
                            logger.warning(f"Could not play boss hit sound: {e}")
                    
                    # Update score for the hits
                    self.score += len(boss_hits) * 50

            except Exception as e:
                logger.error(f"Error in boss collision detection: {e}")

    def _process_enemy_destruction(self, enemy):
        """Process an enemy that was destroyed."""
        # More points for higher-level enemies
        if isinstance(enemy, EnemyType7):
            self.score += 400  # Reflector enemy
        elif isinstance(enemy, EnemyType8):
            self.score += 450  # Lightboard enemy
        elif isinstance(enemy, EnemyType6):
            self.score += 350  # Teleporter enemy
        elif isinstance(enemy, EnemyType5):
            self.score += 250  # Seeker enemy
        elif isinstance(enemy, EnemyType4):
            self.score += 200  # Spiral enemy
        elif isinstance(enemy, EnemyType3):
            self.score += 150  # Wave enemy
        elif isinstance(enemy, EnemyType2):
            self.score += 100  # Basic shooter enemy
        else:
            self.score += 50  # Basic enemy

        # Play enemy explosion sound - use try/except to handle any missing sounds
        try:
            self.sound_manager.play("explosion2", "enemy")
        except Exception as e:
            logger.warning(f"Failed to play explosion sound: {e}")

        # Create explosion at enemy position
        explosion_size = (50, 50)  # Size for enemy explosion
        Explosion(
            enemy.rect.center,
            explosion_size,
            "enemy",
            self.explosions,
            particles_group=self.particles,
        )
        logger.debug(f"Enemy destroyed at {enemy.rect.center}")

        # Ensure the enemy is removed from all sprite groups
        if enemy in self.enemies:
            enemy.kill()
            
            # Determine enemy type to add to correct pool
            enemy_type = -1
            if isinstance(enemy, EnemyType1): enemy_type = 0
            elif isinstance(enemy, EnemyType2): enemy_type = 1
            elif isinstance(enemy, EnemyType3): enemy_type = 2
            elif isinstance(enemy, EnemyType4): enemy_type = 3
            elif isinstance(enemy, EnemyType5): enemy_type = 4
            elif isinstance(enemy, EnemyType6): enemy_type = 5
            elif isinstance(enemy, EnemyType7): enemy_type = 6
            elif isinstance(enemy, EnemyType8): enemy_type = 7
            
            # Add back to pool if we identified the type
            if enemy_type >= 0:
                # Limit pool size to prevent excessive memory usage
                if len(self.enemy_pools[enemy_type]) < 20:
                    self.enemy_pools[enemy_type].append(enemy)

    def _render(self):
        """Draws the game state to the screen."""
        # Explicitly fill the screen first to prevent smearing artifacts
        self.screen.fill(BLACK)

        # Draw background layers (slowest first)
        for layer in self.background_layers:
            layer.draw(self.screen)

        # Draw background decorations after background layers but before sprites
        self.bg_decorations.draw(self.screen)

        # Draw most sprites
        for sprite in self.all_sprites:
            # Use custom draw method for reflector enemies and lightboard enemies
            if isinstance(sprite, EnemyType7) or isinstance(sprite, EnemyType8):
                sprite.draw(self.screen)
            else:
                self.screen.blit(sprite.image, sprite.rect)

            # Draw any enemy labels (for test mode) - use getattr to avoid linter errors
            if getattr(sprite, "label_text", None) and getattr(sprite, "label_rect", None):
                self.screen.blit(getattr(sprite, "label_text"), getattr(sprite, "label_rect"))

        # Draw enemy bullets
        self.enemy_bullets.draw(self.screen)

        # Draw explosions
        self.explosions.draw(self.screen)

        # Draw powerups
        self.powerups.draw(self.screen)

        # Draw text notifications
        self.notifications.draw(self.screen)

        # Use player's custom draw method for shield and other visuals
        if self.player.is_alive:
            self.player.draw(self.screen)

        # Fill any gaps at screen edges with black to ensure borders are flush
        pygame.draw.rect(self.screen, BLACK, (0, 0, SCREEN_WIDTH, PLAYFIELD_TOP_Y))
        pygame.draw.rect(
            self.screen,
            BLACK,
            (0, PLAYFIELD_BOTTOM_Y, SCREEN_WIDTH, SCREEN_HEIGHT - PLAYFIELD_BOTTOM_Y),
        )

        # Draw border layers on top of everything
        for border in self.borders:
            border.draw(self.screen)

        # Draw custom power bar
        if self.player.is_alive:
            self._draw_power_bar()

            # Draw powerup icons
            self.player.draw_powerup_icons(self.screen)

            # Check if we should emit power change particles
            if self.player.should_emit_particles():
                power_bar_pos = self.player.get_power_bar_particles_position()
                power_color = self.player.get_power_bar_color()

                # Determine if power decreased or increased
                is_decrease = self.previous_player_power > self.player.power_level

                # Create power change particles
                PowerParticleSystem.create_power_change_effect(
                    power_bar_pos, power_color, is_decrease=is_decrease, group=self.particles
                )

            # Update previous power level
            self.previous_player_power = self.player.power_level

        # Draw particles AFTER all other game elements to make them appear on top
        self.particles.draw(self.screen)

        # Draw score in upper right corner
        score_text = self.score_font.render(f"SCORE: {self.score}", True, WHITE)
        score_rect = score_text.get_rect(topright=(SCREEN_WIDTH - 20, 15))
        self.screen.blit(score_text, score_rect)

        # Draw difficulty level indicator
        difficulty_text = self.score_font.render(f"WAVE: {self.wave_count}", True, WHITE)
        difficulty_rect = difficulty_text.get_rect(topright=(SCREEN_WIDTH - 20, 45))
        self.screen.blit(difficulty_text, difficulty_rect)

        # Draw max wave indicator
        max_wave_text = self.score_font.render(f"MAX WAVE: {self.max_wave_count}", True, (200, 200, 200))  # Slightly dimmer color
        max_wave_rect = max_wave_text.get_rect(topright=(SCREEN_WIDTH - 20, 75))
        self.screen.blit(max_wave_text, max_wave_rect)

        # Draw game over message if necessary
        if self.game_over:
            current_time = pygame.time.get_ticks()
            elapsed = current_time - self.game_over_start_time

            if elapsed < self.game_over_animation_duration and self.game_over_image is not None:
                # Animation still in progress
                progress = elapsed / self.game_over_animation_duration  # 0.0 to 1.0

                # Phase 1 (0-40%): Scale up horizontally
                if progress < 0.4:
                    phase_progress = progress / 0.4  # 0.0 to 1.0 within this phase
                    width_scale = 1.0 + phase_progress * 0.5  # Scale from 100% to 150%
                    height_scale = 1.0

                # Phase 2 (40-70%): Scale up vertically
                elif progress < 0.7:
                    phase_progress = (progress - 0.4) / 0.3  # 0.0 to 1.0 within this phase
                    width_scale = 1.5
                    height_scale = 1.0 + phase_progress * 0.5  # Scale from 100% to 150%

                # Phase 3 (70-100%): Squish out of existence
                else:
                    phase_progress = (progress - 0.7) / 0.3  # 0.0 to 1.0 within this phase
                    width_scale = 1.5 - phase_progress * 1.5  # Scale from 150% to 0%
                    height_scale = 1.5 - phase_progress * 1.5  # Scale from 150% to 0%

                # Scale image according to animation phase
                orig_width, orig_height = self.game_over_image.get_size()
                new_width = int(orig_width * width_scale)
                new_height = int(orig_height * height_scale)

                # Only draw if dimensions are valid
                if new_width > 0 and new_height > 0:
                    scaled_image = pygame.transform.scale(
                        self.game_over_image, (new_width, new_height)
                    )
                    image_rect = scaled_image.get_rect(
                        center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)
                    )
                    self.screen.blit(scaled_image, image_rect)

                # Mark animation as complete if we've reached the end
                if progress >= 0.99:
                    self.game_over_animation_complete = True

            else:
                # Animation complete, show wave and score info
                self.game_over_animation_complete = True

                # Display wave reached prominently
                level_font = pygame.font.SysFont(
                    None, DEFAULT_FONT_SIZE * 3
                )  # Larger font for wave
                level_text = level_font.render(
                    f"WAVE {self.wave_count}", True, (255, 215, 0)
                )  # Gold color
                level_rect = level_text.get_rect(
                    center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)
                )
                self.screen.blit(level_text, level_rect)

                # Display final score
                final_score_text = self.score_font.render(f"FINAL SCORE: {self.score}", True, WHITE)
                final_score_rect = final_score_text.get_rect(
                    center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20)
                )
                self.screen.blit(final_score_text, final_score_rect)

                # Display restart prompt
                restart_text = self.score_font.render(
                    "Press Space To Try Again!", True, (0, 255, 0)
                )  # Green text
                restart_rect = restart_text.get_rect(
                    center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70)
                )

                # Make the text blink by checking the time
                if (pygame.time.get_ticks() // 500) % 2 == 0:  # Blinks every 500ms
                    self.screen.blit(restart_text, restart_rect)

        # Draw the game logo at the top center of the screen
        if self.logo is not None:
            logo_rect = self.logo.get_rect(midtop=(SCREEN_WIDTH // 2, 5))
            self.screen.blit(self.logo, logo_rect)

        # Draw help text with controls info
        self._draw_help_text()

        # Draw boss and boss bullets
        if self.is_boss_battle and self.boss:
            # Draw tentacles behind the boss
            self.boss.draw_tentacles(self.screen)
            
            # Draw the boss using the boss_sprites group
            self.boss_sprites.draw(self.screen)
            
            # Draw boss bullets
            self.boss_bullets.draw(self.screen)
            
            # Draw boss health bar
            self.boss.draw_health_bar(self.screen)

        pygame.display.flip()

    def _draw_power_bar(self):
        """Draws the custom power bar with power level indicators."""
        # Get bar position and dimensions from player
        x, y = self.player.power_bar_position
        width = self.player.power_bar_width
        height = self.player.power_bar_height
        border = self.player.power_bar_border

        # Draw outer border (black)
        pygame.draw.rect(self.screen, BLACK, (x, y, width, height))

        # Calculate filled portion width
        filled_width = (width - border * 2) * self.player.power_level / MAX_POWER_LEVEL

        # Draw filled portion with color based on power level
        bar_color = self.player.get_power_bar_color()
        pygame.draw.rect(
            self.screen, bar_color, (x + border, y + border, filled_width, height - border * 2)
        )

        # Draw power level indicators (segment lines)
        segments = MAX_POWER_LEVEL
        segment_width = (width - border * 2) / segments

        for i in range(1, segments):
            segment_x = x + border + i * segment_width
            # Draw segment line
            pygame.draw.line(
                self.screen, BLACK, (segment_x, y + border), (segment_x, y + height - border), 2
            )

        # Draw power level text for clarity
        power_text = self.score_font.render(
            f"POWER: {self.player.power_level}/{MAX_POWER_LEVEL}", True, WHITE
        )
        text_rect = power_text.get_rect(topleft=(x + width + 10, y))
        self.screen.blit(power_text, text_rect)

    def _handle_game_over(self):
        """Handles the game over state when player loses all power."""
        # Cancel the wave timer
        pygame.time.set_timer(WAVE_TIMER_EVENT, 0)

        # Play explosion sound
        self.sound_manager.play("explosion1", "player")
        logger.warning("Game over - Player destroyed!")

        # Make player invisible but don't remove from groups yet
        self.player.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        
        # Explicitly set the player to not alive to prevent rendering
        self.player.is_alive = False
        self.player.visible = False
        
        # Completely remove the player from all sprite groups
        self.player.kill()

        # Set game over flag and initialize animation
        self.game_over = True
        self.game_over_start_time = pygame.time.get_ticks()
        self.game_over_animation_complete = False

        # No longer set a timer to end the game - player can restart with space

    def _create_mega_blast(self, center_position):
        """Creates a mega blast that destroys all enemies and projectiles on screen.
        
        Args:
            center_position: The center position of the mega blast (usually player's position)
        """
        logger.info("Creating mega blast effect")
        
        # Play powerful explosion sound
        try:
            self.sound_manager.play("explosion1", "player")
        except Exception as e:
            logger.warning(f"Failed to play mega blast explosion sound: {e}")
        
        # Destroy all enemies
        for enemy in list(self.enemies):
            # Process each enemy's destruction to get points and effects
            self._process_enemy_destruction(enemy)
        
        # Clear all projectiles (player and enemy bullets)
        for bullet in list(self.bullets):
            bullet.kill()
            
        for enemy_bullet in list(self.enemy_bullets):
            enemy_bullet.kill()
            
        logger.info("Mega blast complete - cleared all enemies and projectiles")

    def _reset_game(self):
        """Reset the game state to start a new game."""
        # Reset core game state
        self.game_over = False
        self.score = 0
        self.wave_count = 0
        # Note: max_wave_count is intentionally not reset to preserve the record
        self.difficulty_level = 1.0

        # Clear all sprite groups
        self.all_sprites.empty()
        self.enemies.empty()
        self.bullets.empty()
        self.enemy_bullets.empty()
        self.explosions.empty()
        self.particles.empty()
        self.powerups.empty()
        self.notifications.empty()

        # Reset game timers
        pygame.time.set_timer(pygame.USEREVENT, 0)  # Disable any pending timers
        pygame.time.set_timer(WAVE_TIMER_EVENT, WAVE_DELAY_MS)  # Reset wave timer

        # Re-initialize player
        self.player = Player(self.bullets, self.all_sprites, game_ref=self)
        self.previous_player_power = self.player.power_level
        self.last_laser_sound_time = 0
        self.previous_enemy_bullet_count = 0
        self.game_start_time = pygame.time.get_ticks()

        # Reset any other game-specific state
        import src.enemy

        src.enemy.ENEMY_SHOOTER_COOLDOWN_MS = ENEMY_SHOOTER_COOLDOWN_MS  # Reset to default

        logger.info("Game reset - starting new game")

        # Reset boss battle state
        self.is_boss_battle = False
        self.boss_defeated = False
        self.boss_defeat_handled = False
        self.boss = None
        
        # Reset boss sprites group
        if hasattr(self, 'boss_sprites'):
            self.boss_sprites.empty()
        else:
            self.boss_sprites = pygame.sprite.Group()

    def _preload_sounds(self):
        """Preload sound effects."""
        # These sounds don't need to be explicitly preloaded anymore
        # as the SoundManager handles fallbacks gracefully
        pass

    def _draw_help_text(self):
        """Draw help text showing controls in bottom left corner."""
        # Only draw help text if player is alive (don't clutter game over screen)
        if not self.player.is_alive or self.game_over:
            return

        help_font = pygame.font.SysFont(None, 20)
        controls = [
            "ARROWS - Move",
            "SPACE - Fire",
            "B - Scatter Bomb",
            "M - Toggle Music",
            "+/- - Volume",
        ]

        y_pos = SCREEN_HEIGHT - 10 - (len(controls) * 22)
        for i, text in enumerate(controls):
            # Shadow
            shadow_surf = help_font.render(text, True, (0, 0, 0))
            self.screen.blit(shadow_surf, (11, y_pos + 1))

            # Brighter text colors for better readability
            color = (230, 230, 230)  # Almost white for commands
            text_surf = help_font.render(text, True, color)

            self.screen.blit(text_surf, (10, y_pos))
            y_pos += 22

    def _start_boss_battle(self):
        """Initialize and start the boss battle."""
        try:
            # --- Play the boss intro sequence --- 
            logger.info("Starting boss intro sequence...")
            intro_completed = run_boss_intro(self.screen, self.sound_manager)
            if not intro_completed:
                logger.warning("Boss intro aborted, game might exit.")
                # Handle intro abortion (e.g., quit game or skip boss battle)
                # If the user quits during the intro, the main loop should catch it.
                pass # Or handle differently if needed
            logger.info("Boss intro sequence finished.")
            # --- End boss intro sequence --- 

            # Explicitly stop player firing state
            if self.player:
                self.player.stop_firing()
                logger.info("Stopped player firing for boss battle.")

            # Make sure we have a sprites group for the boss
            if not hasattr(self, 'boss_sprites'):
                self.boss_sprites = pygame.sprite.Group()
            
            # Create the boss and add it to the boss_sprites group
            self.boss = create_boss(self.player)
            if self.boss is not None:
                self.boss_sprites.add(self.boss)
                self.is_boss_battle = True
                
                # Set the game reference on the boss so it can create explosions
                self.boss.game_ref = self
                
                # Stop all regular enemy spawning
                pygame.time.set_timer(WAVE_TIMER_EVENT, 0)
                
                # Clear any existing enemies to focus on the boss battle
                for enemy in self.enemies:
                    enemy.kill()
                
                # Play boss music or sound effect
                if hasattr(self, 'sound_manager') and self.sound_manager:
                    # TODO: Add boss music if available
                    pass
                    
                logger.info("Boss battle started!")
            else:
                logger.error("Failed to create boss - boss is None")
        except Exception as e:
            logger.error(f"Error starting boss battle: {e}")

    def _handle_boss_defeated(self):
        """Handle the boss being defeated."""
        try:
            logger.info("Boss defeated! Victory!")
            
            # Prevent calling this method multiple times
            if self.boss_defeat_handled:
                return
                
            # Award bonus points
            bonus_points = 10000
            self.score += bonus_points
    
            # Clean up boss battle
            self.is_boss_battle = False
            self.boss_defeated = True
            self.boss_defeat_handled = True
            
            # Safely clear boss and boss sprites
            if hasattr(self, 'boss_sprites') and self.boss_sprites is not None:
                self.boss_sprites.empty()
            self.boss = None
            
            # Clear all boss bullets
            if hasattr(self, 'boss_bullets') and self.boss_bullets is not None:
                self.boss_bullets.empty()
            
            # Resume regular waves after a delay
            logger.info("Resuming regular waves after boss defeat")
            pygame.time.set_timer(WAVE_TIMER_EVENT, WAVE_DELAY_MS * 2)  # Longer delay
            
            # Force a wave spawn after a short delay
            pygame.time.set_timer(WAVE_TIMER_EVENT, WAVE_DELAY_MS * 2, True)
        except Exception as e:
            logger.error(f"Error in boss defeated handler: {e}")
            
    def _handle_debug_keys(self, event):
        """Handle debug key presses."""
        if not self.debug_mode:
            return False
        
        if event.key == pygame.K_F1:
            # Toggle debug mode
            self.debug_mode = not self.debug_mode
            logger.info(f"Debug mode: {self.debug_mode}")
            return True
        elif event.key == pygame.K_F2:
            # Toggle god mode for player
            if hasattr(self.player, 'is_invincible'):
                self.player.is_invincible = not self.player.is_invincible
                logger.info(f"God mode: {self.player.is_invincible}")
            return True
        elif event.key == pygame.K_F7:
            # Test boss battle
            self._test_boss_battle()
            return True
        elif event.key == pygame.K_F8:
            # Test boss death animation
            self._test_boss_death_animation()
            return True
        
        return False

    def _test_boss_battle(self):
        """Start a boss battle for debugging."""
        logger.info("Starting test boss battle")
        self._start_boss_battle()

    def _test_boss_death_animation(self):
        """Test the boss death animation by making the boss take lethal damage."""
        if self.boss and hasattr(self.boss, 'health'):
            # Put boss at 1 health so next hit will defeat it
            self.boss.health = 1
            logger.info("Set boss health to 1 for testing death animation")
            # Make the boss take 10 damage, which should defeat it
            if hasattr(self.boss, 'take_damage'):
                self.boss.take_damage(10)
            else:
                logger.error("Boss does not have take_damage method")
            