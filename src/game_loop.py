"""Main game loop and game state management."""

import logging
import os
import random
import sys
from enum import IntEnum  # Add IntEnum import
from typing import Dict, List, Optional, Tuple, Set, Union, Any

import pygame
import numpy as np
from pygame.locals import KEYDOWN, MOUSEBUTTONDOWN, QUIT  # No longer need VIDEORESIZE

# Import configuration constants
from config.config import (
    BACKGROUNDS_DIR,
    BLACK,
    DEBUG_ENEMY_TYPE_INDEX,
    DEBUG_FORCE_ENEMY_TYPE,
    DECORATION_FILES,
    DEFAULT_FONT_SIZE,
    DIFFICULTY_MAX_LEVEL,
    ENEMY_SHOOTER_COOLDOWN_MS,
    ENEMY_TYPE_NAMES,
    ENEMY_TYPES,
    FPS,
    LOGO_ALPHA,
    PATTERN_TYPES,
    PLAYER_SHOOT_DELAY,
    PLAYER_SPEED,
    PLAYFIELD_BOTTOM_Y,
    PLAYFIELD_TOP_Y,
    POWERUP_DIFFICULTY_SCALING,
    POWERUP_MAX_SPAWN_INTERVAL_MS,
    POWERUP_MIN_DIFFICULTY_INTERVAL_MS,
    POWERUP_MIN_SPAWN_INTERVAL_MS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    WAVE_DELAY_MS,
    WAVE_TIMER_EVENT_ID,
    WHITE,
    SOUNDS_DIR,
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
from src.powerup import ACTIVE_POWERUP_TYPES, PowerupParticle, PowerupType
from src.projectile import Bullet, ScatterProjectile
from src.sound_manager import SoundManager

# Get logger for this module
logger = get_logger(__name__)

# Define background speeds
BG_LAYER_SPEEDS = [0.5, 1.0, 1.5, 2.0]  # Slowest to fastest (added a fourth speed)

# Use the event ID from config
WAVE_TIMER_EVENT = WAVE_TIMER_EVENT_ID


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

        # Difficulty progression
        self.difficulty_level = 1.0  # Starting difficulty (will increase over time)
        self.max_difficulty = 10.0  # Maximum difficulty cap
        self.difficulty_increase_rate = 0.2  # Significantly increased from 0.05 to 0.2
        self.game_start_time = pygame.time.get_ticks()  # Track game duration

        # Consider adding mixer init for sounds later: pygame.mixer.init()

        # Load configuration - Use config for window size, remove RESIZABLE
        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT)
        )  # Removed RESIZABLE flag
        # Store screen size directly from config for windowed mode
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

        # Start background music
        self.sound_manager.play_music("background-music.mp3", loops=-1)

        # Laser sound timer - for continuous fire sound
        self.last_laser_sound_time = 0

        # Enemy bullet tracking
        self.previous_enemy_bullet_count = 0

        # Simple wave management state
        self.wave_active = False
        self.wave_count = 0  # Track number of waves for difficulty progression
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

    def run(self):
        """Starts and manages the main game loop."""
        # No longer force spawn a powerup at start

        while self.is_running:
            # Check for window resize events (optional but good for resizable window) - REMOVED
            # self.handle_resize()
            self._handle_events()
            self._update()
            self._render()
            self.clock.tick(FPS)  # Use FPS from config

        pygame.quit()

    # Optional: Handle window resizing - REMOVED
    # def handle_resize(self):
    #     for event in pygame.event.get(pygame.VIDEORESIZE):
    #         self.current_screen_width, self.current_screen_height = event.size
    #         self.screen = pygame.display.set_mode((self.current_screen_width, self.current_screen_height), pygame.RESIZABLE)
    #         # Optionally recreate/rescale background layers if needed

    def _handle_events(self):
        """Process all game events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.is_running = False
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
                        EnemyType7(self.player, self.enemy_bullets, self.all_sprites, self.enemies),
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
                self._update_difficulty()

                # Select a random pattern type
                pattern_type = random.randint(0, 3)  # 0-3 for our four pattern types

                # Scale number of enemies based on difficulty (4-7 base, up to 8-12 at max difficulty)
                min_enemies = 4 + int(
                    (self.difficulty_level - 1) / 1.5
                )  # Increases by 1 every 1.5 difficulty levels (faster)
                max_enemies = 7 + int(
                    (self.difficulty_level - 1) / 1
                )  # Increases by 1 every difficulty level (faster)
                min_enemies = min(min_enemies, 10)  # Higher cap (was 8)
                max_enemies = min(max_enemies, 15)  # Higher cap (was 12)

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
                        list(range(len(enemy_weights))),  # Options are 0-5 for all enemy types
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

                # Play wave spawn sound
                self.sound_manager.play("explosion2", "enemy")

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
        )  # Increased from 0.05 to 0.1 per level, max 70% (was 50%)

        # Override global cooldown with difficulty-adjusted value (using monkey patching)
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
        )  # Increased from 0.1 to 0.15 (15% per level)

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
        ):  # Changed from PATTERN_V_FORMATION to PATTERN_V_SHAPE
            # V formation - enemies in a V shape
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
        """Creates a vertical line of enemies entering from right.

        Args:
            count: Number of enemies to spawn
            spacing_y: Vertical spacing between enemies
            enemy_type_index: Type of enemy to spawn (0: EnemyType1, 1: EnemyType2,
                              2: EnemyType3, 3: EnemyType4, 4: EnemyType5,
                              5: EnemyType6, 6: EnemyType7, 7: EnemyType8)
            speed_modifier: Multiplier for enemy speed based on difficulty
        """
        # Calculate the playfield height for spacing
        playfield_height = PLAYFIELD_BOTTOM_Y - PLAYFIELD_TOP_Y

        # Apply border margin to prevent spawning too close to borders
        border_margin = 50
        usable_height = playfield_height - (2 * border_margin)

        # Fixed enemy height estimate
        enemy_height = 40

        # Total pattern height
        total_height = (count - 1) * spacing_y + enemy_height

        # Center the pattern vertically within the usable area
        start_y = PLAYFIELD_TOP_Y + border_margin + (usable_height - total_height) // 2

        # Fixed horizontal offset past right edge
        x_pos = SCREEN_WIDTH + 50

        # Create the enemies
        for i in range(count):
            y_pos = start_y + i * spacing_y

            # Create the enemy based on the specified type
            if enemy_type_index == 1:
                enemy = EnemyType2(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 2:
                enemy = EnemyType3(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 3:
                enemy = EnemyType4(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 4:
                enemy = EnemyType5(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 5:
                enemy = EnemyType6(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 6:
                enemy = EnemyType7(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 7:
                enemy = EnemyType8(self.player, self.all_sprites, self.enemies)
            else:
                enemy = EnemyType1(self.all_sprites, self.enemies)

            # Apply speed modifier based on difficulty
            enemy.speed_x *= speed_modifier

            # Adjust shooting cooldowns based on enemy type
            if isinstance(enemy, EnemyType2):
                # Basic shooter - uses ENEMY_SHOOTER_COOLDOWN_MS directly
                enemy.last_shot_time = pygame.time.get_ticks()  # Reset timer
            elif isinstance(enemy, EnemyType3):
                # Wave projectile enemy - uses ENEMY_SHOOTER_COOLDOWN_MS * 1.5
                enemy.last_shot_time = pygame.time.get_ticks()  # Reset timer
            elif isinstance(enemy, EnemyType4):
                # Spiral shooter - has multiple cooldowns
                enemy.last_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.last_homing_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.homing_shot_cooldown = max(
                    1000, int(enemy.homing_shot_cooldown / speed_modifier)
                )
            elif isinstance(enemy, EnemyType5):
                # Advanced shooter - has multiple cooldowns
                enemy.last_explosive_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.last_homing_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.explosive_cooldown = max(1000, int(enemy.explosive_cooldown / speed_modifier))
                enemy.homing_cooldown = max(1000, int(enemy.homing_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType6):
                # Teleporting enemy with bouncing projectiles
                enemy.last_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.last_teleport_time = pygame.time.get_ticks()  # Reset teleport timer
                enemy.teleport_delay = max(1000, int(enemy.teleport_delay / speed_modifier))
            elif isinstance(enemy, EnemyType7):
                # Reflector enemy with laser and shield
                enemy.last_reflection_time = pygame.time.get_ticks()  # Reset reflection timer
                enemy.last_laser_time = pygame.time.get_ticks()  # Reset laser timer
                enemy.reflection_cooldown = max(1000, int(enemy.reflection_cooldown / speed_modifier))
                enemy.laser_cooldown = max(1000, int(enemy.laser_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType8):
                # Lightboard enemy
                enemy.last_charge_time = pygame.time.get_ticks()  # Reset charge timer
                enemy.charge_cooldown = max(1000, int(enemy.charge_cooldown / speed_modifier))
            else:
                enemy = EnemyType1(self.all_sprites, self.enemies)

            # Use the property setter instead of direct rect access
            enemy.topleft = (x_pos, y_pos)

    def _spawn_horizontal_pattern(
        self, count: int, enemy_type_index: int = 0, speed_modifier: float = 1.0
    ):
        """Creates a horizontal line of enemies entering from right.

        Args:
            count: Number of enemies to spawn
            enemy_type_index: Type of enemy to spawn
            speed_modifier: Multiplier for enemy speed based on difficulty
        """
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

            # Create the enemy based on the specified type
            if enemy_type_index == 1:
                enemy = EnemyType2(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 2:
                enemy = EnemyType3(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 3:
                enemy = EnemyType4(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 4:
                enemy = EnemyType5(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 5:
                enemy = EnemyType6(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 6:
                enemy = EnemyType7(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 7:
                enemy = EnemyType8(self.player, self.all_sprites, self.enemies)
            else:
                enemy = EnemyType1(self.all_sprites, self.enemies)

            # Apply speed modifier based on difficulty
            enemy.speed_x *= speed_modifier

            # Adjust shooting cooldowns based on enemy type
            if isinstance(enemy, EnemyType2):
                # Basic shooter - uses ENEMY_SHOOTER_COOLDOWN_MS directly
                enemy.last_shot_time = pygame.time.get_ticks()  # Reset timer
            elif isinstance(enemy, EnemyType3):
                # Wave projectile enemy - uses ENEMY_SHOOTER_COOLDOWN_MS * 1.5
                enemy.last_shot_time = pygame.time.get_ticks()  # Reset timer
            elif isinstance(enemy, EnemyType4):
                # Spiral shooter - has multiple cooldowns
                enemy.last_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.last_homing_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.homing_shot_cooldown = max(
                    1000, int(enemy.homing_shot_cooldown / speed_modifier)
                )
            elif isinstance(enemy, EnemyType5):
                # Advanced shooter - has multiple cooldowns
                enemy.last_explosive_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.last_homing_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.explosive_cooldown = max(1000, int(enemy.explosive_cooldown / speed_modifier))
                enemy.homing_cooldown = max(1000, int(enemy.homing_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType6):
                # Teleporting enemy with bouncing projectiles
                enemy.last_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.last_teleport_time = pygame.time.get_ticks()  # Reset teleport timer
                enemy.teleport_delay = max(1000, int(enemy.teleport_delay / speed_modifier))
            elif isinstance(enemy, EnemyType7):
                # Reflector enemy with laser and shield
                enemy.last_reflection_time = pygame.time.get_ticks()  # Reset reflection timer
                enemy.last_laser_time = pygame.time.get_ticks()  # Reset laser timer
                enemy.reflection_cooldown = max(1000, int(enemy.reflection_cooldown / speed_modifier))
                enemy.laser_cooldown = max(1000, int(enemy.laser_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType8):
                # Lightboard enemy
                enemy.last_charge_time = pygame.time.get_ticks()  # Reset charge timer
                enemy.charge_cooldown = max(1000, int(enemy.charge_cooldown / speed_modifier))
            else:
                enemy = EnemyType1(self.all_sprites, self.enemies)

            # Use the property setter instead of direct rect access
            enemy.topleft = (x_pos, y_pos)

    def _spawn_diagonal_pattern(
        self, count: int, enemy_type_index: int = 0, speed_modifier: float = 1.0
    ):
        """Creates a diagonal line of enemies entering from right.

        Args:
            count: Number of enemies to spawn
            enemy_type_index: Type of enemy to spawn (0-6)
            speed_modifier: Multiplier for enemy speed based on difficulty
        """
        # Spacing between enemies
        spacing_x = 50
        spacing_y = 50

        # Apply border margin to prevent spawning too close to borders
        border_margin = 50

        # Start position (respecting top margin)
        start_x = SCREEN_WIDTH + 50
        start_y = PLAYFIELD_TOP_Y + border_margin

        # Adjust start_y based on count to keep the pattern within the playfield
        available_height = (
            PLAYFIELD_BOTTOM_Y - PLAYFIELD_TOP_Y - (2 * border_margin) - 40
        )  # 40 is enemy height estimate
        max_drop = (count - 1) * spacing_y

        if max_drop > available_height:
            # Scale down spacing to fit within available height with margins
            spacing_y = available_height / (count - 1) if count > 1 else 0

        # Create the enemies
        for i in range(count):
            x_pos = start_x + i * spacing_x
            y_pos = start_y + i * spacing_y

            # Create the enemy based on the specified type
            if enemy_type_index == 1:
                enemy = EnemyType2(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 2:
                enemy = EnemyType3(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 3:
                enemy = EnemyType4(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 4:
                enemy = EnemyType5(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 5:
                enemy = EnemyType6(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 6:
                enemy = EnemyType7(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 7:
                enemy = EnemyType8(self.player, self.all_sprites, self.enemies)
            else:
                enemy = EnemyType1(self.all_sprites, self.enemies)

            # Apply speed modifier based on difficulty
            enemy.speed_x *= speed_modifier

            # Adjust shooting cooldowns based on enemy type
            if isinstance(enemy, EnemyType2):
                # Basic shooter - uses ENEMY_SHOOTER_COOLDOWN_MS directly
                enemy.last_shot_time = pygame.time.get_ticks()  # Reset timer
            elif isinstance(enemy, EnemyType3):
                # Wave projectile enemy - uses ENEMY_SHOOTER_COOLDOWN_MS * 1.5
                enemy.last_shot_time = pygame.time.get_ticks()  # Reset timer
            elif isinstance(enemy, EnemyType4):
                # Spiral shooter - has multiple cooldowns
                enemy.last_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.last_homing_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.homing_shot_cooldown = max(
                    1000, int(enemy.homing_shot_cooldown / speed_modifier)
                )
            elif isinstance(enemy, EnemyType5):
                # Advanced shooter - has multiple cooldowns
                enemy.last_explosive_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.last_homing_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.explosive_cooldown = max(1000, int(enemy.explosive_cooldown / speed_modifier))
                enemy.homing_cooldown = max(1000, int(enemy.homing_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType6):
                # Teleporting enemy with bouncing projectiles
                enemy.last_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.last_teleport_time = pygame.time.get_ticks()  # Reset teleport timer
                enemy.teleport_delay = max(1000, int(enemy.teleport_delay / speed_modifier))
            elif isinstance(enemy, EnemyType7):
                # Reflector enemy with laser and shield
                enemy.last_reflection_time = pygame.time.get_ticks()  # Reset reflection timer
                enemy.last_laser_time = pygame.time.get_ticks()  # Reset laser timer
                enemy.reflection_cooldown = max(1000, int(enemy.reflection_cooldown / speed_modifier))
                enemy.laser_cooldown = max(1000, int(enemy.laser_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType8):
                # Lightboard enemy
                enemy.last_charge_time = pygame.time.get_ticks()  # Reset charge timer
                enemy.charge_cooldown = max(1000, int(enemy.charge_cooldown / speed_modifier))
            else:
                enemy = EnemyType1(self.all_sprites, self.enemies)

            # Use the property setter instead of direct rect access
            enemy.topleft = (x_pos, y_pos)

    def _spawn_v_pattern(self, count: int, enemy_type_index: int = 0, speed_modifier: float = 1.0):
        """Creates a V-shaped formation of enemies entering from right.

        Args:
            count: Number of enemies to spawn
            enemy_type_index: Type of enemy to spawn (0-6)
            speed_modifier: Multiplier for enemy speed based on difficulty
        """
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

            # Create the enemy based on the specified type
            if enemy_type_index == 1:
                enemy = EnemyType2(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 2:
                enemy = EnemyType3(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 3:
                enemy = EnemyType4(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 4:
                enemy = EnemyType5(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 5:
                enemy = EnemyType6(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 6:
                enemy = EnemyType7(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            elif enemy_type_index == 7:
                enemy = EnemyType8(self.player, self.all_sprites, self.enemies)
            else:
                enemy = EnemyType1(self.all_sprites, self.enemies)

            # Apply speed modifier based on difficulty
            enemy.speed_x *= speed_modifier

            # Adjust shooting cooldowns based on enemy type
            if isinstance(enemy, EnemyType2):
                # Basic shooter - uses ENEMY_SHOOTER_COOLDOWN_MS directly
                enemy.last_shot_time = pygame.time.get_ticks()  # Reset timer
            elif isinstance(enemy, EnemyType3):
                # Wave projectile enemy - uses ENEMY_SHOOTER_COOLDOWN_MS * 1.5
                enemy.last_shot_time = pygame.time.get_ticks()  # Reset timer
            elif isinstance(enemy, EnemyType4):
                # Spiral shooter - has multiple cooldowns
                enemy.last_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.last_homing_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.homing_shot_cooldown = max(
                    1000, int(enemy.homing_shot_cooldown / speed_modifier)
                )
            elif isinstance(enemy, EnemyType5):
                # Advanced shooter - has multiple cooldowns
                enemy.last_explosive_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.last_homing_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.explosive_cooldown = max(1000, int(enemy.explosive_cooldown / speed_modifier))
                enemy.homing_cooldown = max(1000, int(enemy.homing_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType6):
                # Teleporting enemy with bouncing projectiles
                enemy.last_shot_time = pygame.time.get_ticks()  # Reset timer
                enemy.last_teleport_time = pygame.time.get_ticks()  # Reset teleport timer
                enemy.teleport_delay = max(1000, int(enemy.teleport_delay / speed_modifier))
            elif isinstance(enemy, EnemyType7):
                # Reflector enemy with laser and shield
                enemy.last_reflection_time = pygame.time.get_ticks()  # Reset reflection timer
                enemy.last_laser_time = pygame.time.get_ticks()  # Reset laser timer
                enemy.reflection_cooldown = max(1000, int(enemy.reflection_cooldown / speed_modifier))
                enemy.laser_cooldown = max(1000, int(enemy.laser_cooldown / speed_modifier))
            elif isinstance(enemy, EnemyType8):
                # Lightboard enemy
                enemy.last_charge_time = pygame.time.get_ticks()  # Reset charge timer
                enemy.charge_cooldown = max(1000, int(enemy.charge_cooldown / speed_modifier))
            else:
                enemy = EnemyType1(self.all_sprites, self.enemies)

            # Use the property setter instead of direct rect access
            enemy.topleft = (x_pos, y_pos)

    def _update(self):
        """Updates the state of all game objects and handles collisions."""
        # Skip updates if game is paused or over
        # (We'll implement a proper pause later, for now we don't use this)
        if self.is_paused:
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
        # Import for type checking
        from src.player import MAX_POWER_LEVEL
        from src.powerup import PowerupType

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
        chosen_powerup_enum = random.choice(available_types)
        powerup_type_index = chosen_powerup_enum.value  # Get the integer value
        powerup_type_name = chosen_powerup_enum.name  # Get the name

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
        """Checks and handles collisions between game objects."""
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
                        self.sound_manager.play("shield", "enemy")
                    except Exception as e:
                        # Fallback to another common sound if shield isn't available
                        try:
                            self.sound_manager.play("hit1", "enemy")
                        except Exception:
                            logger.warning(f"Failed to play shield or fallback sound: {e}")
                else:
                    # Regular enemy hit handling
                    bullet.kill()
                    enemy.kill()
                    self._process_enemy_destruction(enemy)

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
                # PowerupType.LASER_BEAM: (0, 255, 0), # Removed
                PowerupType.POWER_RESTORE: (255, 255, 255),
                PowerupType.SCATTER_BOMB: (255, 128, 0),
                PowerupType.TIME_WARP: (128, 0, 255),
                PowerupType.MEGA_BLAST: (255, 0, 128),
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
            # Play player explosion sound for each enemy hit
            for enemy in enemy_hits:
                try:
                    self.sound_manager.play("explosion2", "enemy")
                except Exception as e:
                    logger.warning(f"Failed to play explosion sound: {e}")

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

            # Play hit sound for player
            try:
                self.sound_manager.play("hit1", "player")
            except Exception as e:
                logger.warning(f"Failed to play hit sound: {e}")

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

            # Play hit sound
            try:
                self.sound_manager.play("hit1", "player")
            except Exception as e:
                logger.warning(f"Failed to play hit sound: {e}")

            # Check for game over
            if not player_survived:
                self._handle_game_over()

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

        # Draw particles
        self.particles.draw(self.screen)

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

        # Draw score in upper right corner
        score_text = self.score_font.render(f"SCORE: {self.score}", True, WHITE)
        score_rect = score_text.get_rect(topright=(SCREEN_WIDTH - 20, 15))
        self.screen.blit(score_text, score_rect)

        # Draw difficulty level indicator
        difficulty_text = self.score_font.render(f"WAVE: {self.wave_count}", True, WHITE)
        difficulty_rect = difficulty_text.get_rect(topright=(SCREEN_WIDTH - 20, 45))
        self.screen.blit(difficulty_text, difficulty_rect)

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

        # Create explosion effect at the player's position
        explosion_size = (120, 120)  # Larger size for the player explosion
        Explosion(
            self.player.rect.center,
            explosion_size,
            "player",
            self.explosions,
            particles_group=self.particles,
        )

        # Make player invisible but don't remove from groups yet
        self.player.image = pygame.Surface((1, 1), pygame.SRCALPHA)

        # Set game over flag and initialize animation
        self.game_over = True
        self.game_over_start_time = pygame.time.get_ticks()
        self.game_over_animation_complete = False

        # No longer set a timer to end the game - player can restart with space

    def _reset_game(self):
        """Reset the game state to start a new game."""
        # Reset core game state
        self.game_over = False
        self.score = 0
        self.wave_count = 0
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

        help_font = pygame.font.SysFont(None, 20)  # Slightly larger font
        controls = [
            "ARROWS - Move",  # Changed : to -
            "SPACE - Fire",
            "B - Scatter Bomb",
            # Removed SHIFT mechanic
            "M - Toggle Music",
            "+/- - Volume",
            # Removed "D - Debug Enemy Types" line
        ]

        y_pos = SCREEN_HEIGHT - 10 - (len(controls) * 22)  # Increased spacing
        for i, text in enumerate(controls):
            # Shadow
            shadow_surf = help_font.render(text, True, (0, 0, 0))
            self.screen.blit(shadow_surf, (11, y_pos + 1))

            # Text
            # Brighter text colors for better readability
            color = (230, 230, 230)  # Almost white for commands
            text_surf = help_font.render(text, True, color)

            self.screen.blit(text_surf, (10, y_pos))
            y_pos += 22  # Increased spacing
