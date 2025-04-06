"""Main game loop and event handling."""

import pygame
import os # Import os
import random # Import random for random range
import math # Import math for trig functions
from pygame._sdl2.video import Window
from enum import IntEnum
from typing import List, Dict, Tuple, Optional, Any, Set

# Import game components
from src.player import Player
from src.background import BackgroundLayer # Import BackgroundLayer
from src.enemy import EnemyType1 # Import the specific enemy class
from src.enemy import EnemyShooter # Import shooter class
from src.sound_manager import SoundManager
from src.logger import get_logger
from src.border import Border
from src.explosion import Explosion # Import the Explosion class

# Import config variables
from config.game_config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FPS,
    BLACK,
    BACKGROUNDS_DIR,
    ENEMY_SPAWN_RATE,
    PLAYFIELD_TOP_Y,
    PLAYFIELD_BOTTOM_Y,
    PLAYER_SPEED,
    PLAYER_SHOOT_DELAY,
    WAVE_TIMER_EVENT_ID,
    WAVE_DELAY_MS,
    PATTERN_TYPES,
    WHITE,
    RED,
    DEFAULT_FONT_SIZE
)

# Get logger for this module
logger = get_logger(__name__)

# Define background speeds
BG_LAYER_SPEEDS = [0.5, 1.0, 1.5] # Slowest to fastest

# Enemy pattern types
PATTERN_VERTICAL = PATTERN_TYPES["VERTICAL"]
PATTERN_HORIZONTAL = PATTERN_TYPES["HORIZONTAL"]
PATTERN_DIAGONAL = PATTERN_TYPES["DIAGONAL"]
PATTERN_V_SHAPE = PATTERN_TYPES["V_SHAPE"]
PATTERN_COUNT = len(PATTERN_TYPES)

# Use the event ID from config
WAVE_TIMER_EVENT = WAVE_TIMER_EVENT_ID

# Wave patterns
class PatternType(IntEnum):
    VERTICAL = 0
    HORIZONTAL = 1
    DIAGONAL = 2
    V_FORMATION = 3

# Use IntEnum names for readability
PATTERN_VERTICAL = PatternType.VERTICAL
PATTERN_HORIZONTAL = PatternType.HORIZONTAL
PATTERN_DIAGONAL = PatternType.DIAGONAL
PATTERN_V_FORMATION = PatternType.V_FORMATION

class Game:
    """Main game class managing the game loop, state, and events."""
    def __init__(self):
        pygame.init()
        # Consider adding mixer init for sounds later: pygame.mixer.init()

        # Load configuration - Use config for window size, remove RESIZABLE
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT)) # Removed RESIZABLE flag
        # Store screen size directly from config for windowed mode
        self.current_screen_width = SCREEN_WIDTH
        self.current_screen_height = SCREEN_HEIGHT

        # Remove maximize logic
        # try:
        #     Window.from_display_module().maximize()
        #     # After maximizing, get the *actual* screen size for background scaling
        #     self.current_screen_width, self.current_screen_height = self.screen.get_size()
        # except ImportError:
        #     print("Warning: pygame._sdl2 not available. Cannot maximize window.")
        #     self.current_screen_width, self.current_screen_height = SCREEN_WIDTH, SCREEN_HEIGHT
        #     # Fallback or alternative fullscreen method could go here if desired
        # except (pygame.error, AttributeError, TypeError) as e: # More specific exceptions
        #      print(f"Warning: Error maximizing window: {e}")
        #      self.current_screen_width, self.current_screen_height = SCREEN_WIDTH, SCREEN_HEIGHT

        pygame.display.set_caption("Starblitz Assault") # From game.mdc

        self.clock = pygame.time.Clock()
        self.is_running = True

        # Initialize background layers
        self.background_layers = []
        bg_image_path = os.path.join(BACKGROUNDS_DIR, "starfield.png")
        initial_offsets = [0, 100, 200] # Default fallback offsets
        bg_image_width = 0 # Default fallback width
        if os.path.exists(bg_image_path):
            # Calculate approximate initial offsets based on screen width
            # Get image width *after* scaling to screen height for better offsets
            try:
                # Use a variable to hold the temporary layer
                _temp_layer = BackgroundLayer(bg_image_path, 0, self.current_screen_height)
                bg_image_width = _temp_layer.image_width
                # Use more distinct offsets (e.g., 0, 1/4, 3/4) only if width is valid
                if bg_image_width > 0:
                    initial_offsets = [0, bg_image_width / 4, bg_image_width * 3 / 4]
                del _temp_layer # Clean up temporary layer
            except (pygame.error, FileNotFoundError, ZeroDivisionError, AttributeError) as e: # Specific exceptions
                logger.warning(f"Could not get background width for offsets: {e}. Using defaults.")
                # Defaults already set above

            for i, speed in enumerate(BG_LAYER_SPEEDS):
                offset = initial_offsets[i % len(initial_offsets)] # Cycle through offsets
                layer = BackgroundLayer(bg_image_path, speed, self.current_screen_height, initial_scroll=offset)
                self.background_layers.append(layer)
        else:
            logger.warning(f"Background image not found at {bg_image_path}. Skipping background.")

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
        self.enemies = pygame.sprite.Group() # Group for enemies
        self.bullets = pygame.sprite.Group() # Group specifically for bullets
        self.enemy_bullets = pygame.sprite.Group() # Group for enemy bullets
        self.explosions = pygame.sprite.Group() # Group for explosion effects

        # Initialize game components
        self.player = Player(self.bullets, self.all_sprites)
        # self.level_manager = LevelManager() # Not used yet

        # Initialize sound manager
        self.sound_manager = SoundManager()
        
        # Start background music
        self.sound_manager.play_music("background-music-level-1.mp3", loops=-1)
        
        # Laser sound timer - for continuous fire sound
        self.last_laser_sound_time = 0

        # Enemy bullet tracking
        self.previous_enemy_bullet_count = 0
        
        # Simple wave management state
        self.wave_active = False
        pygame.time.set_timer(WAVE_TIMER_EVENT, WAVE_DELAY_MS) # Timer for next wave
        
        # Game over state
        self.game_over = False
        self.game_over_font = pygame.font.SysFont(None, DEFAULT_FONT_SIZE * 2)

    def run(self):
        """Starts and manages the main game loop."""
        while self.is_running:
            # Check for window resize events (optional but good for resizable window) - REMOVED
            # self.handle_resize()
            self._handle_events()
            self._update()
            self._render()
            self.clock.tick(FPS) # Use FPS from config

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
                elif event.key == pygame.K_SPACE and not self.player.is_firing:
                    self.player.start_firing()
                    # Initial laser sound will be handled in _update
                
                # Volume control keys
                elif event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:
                    current_volume = pygame.mixer.music.get_volume()
                    self.sound_manager.set_music_volume(max(0.0, current_volume - 0.1))
                    logger.info(f"Music volume: {pygame.mixer.music.get_volume():.1f}")
                    
                elif event.key == pygame.K_PLUS or event.key == pygame.K_KP_PLUS or event.key == pygame.K_EQUALS:
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
                        
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    self.player.stop_firing()
            elif event.type == WAVE_TIMER_EVENT:
                # Select a random pattern type
                pattern_type = random.randint(0, 3)  # 0-3 for our four pattern types
                
                # Random count of enemies between 4 and 7
                count = random.randint(4, 7)
                
                # <<< Add logic to decide if wave contains shooters
                has_shooters = random.choice([True, False]) # 50% chance for now

                logger.info(f"Spawning wave of {count} enemies with pattern {pattern_type}{' (shooters)' if has_shooters else ''}")
                self.spawn_enemy_wave(count, pattern_type=pattern_type, spawn_shooters=has_shooters) # <<< Pass shooter flag
                
                # Play wave spawn sound
                self.sound_manager.play("powerup1", "enemy")
                
                # Reset the timer for the next wave
                pygame.time.set_timer(WAVE_TIMER_EVENT, random.randint(3000, 5000))
            elif event.type == pygame.USEREVENT:
                # This is the game over delay timer
                self.is_running = False
                pygame.time.set_timer(pygame.USEREVENT, 0)  # Disable the timer

    def spawn_enemy_wave(self, count: int, pattern_type: int = 0, spawn_shooters: bool = False): # <<< Add spawn_shooters flag
        """Creates a new wave of enemies based on the given pattern type."""
        if pattern_type == PATTERN_VERTICAL:
            # Vertical formation - enemies in a vertical line
            # Calculate spacing based on playfield height and enemy count
            playfield_height = PLAYFIELD_BOTTOM_Y - PLAYFIELD_TOP_Y
            spacing = playfield_height / (count + 1)  # +1 for proper spacing at edges
            self._spawn_vertical_pattern(count, int(spacing), spawn_shooters=spawn_shooters) # <<< Pass flag
            
        elif pattern_type == PATTERN_HORIZONTAL:
            # Horizontal formation - enemies in a horizontal line
            self._spawn_horizontal_pattern(count, spawn_shooters=spawn_shooters) # <<< Pass flag
            
        elif pattern_type == PATTERN_DIAGONAL:
            # Diagonal formation - enemies in a diagonal line
            self._spawn_diagonal_pattern(count, spawn_shooters=spawn_shooters) # <<< Pass flag
            
        elif pattern_type == PATTERN_V_FORMATION:
            # V formation - enemies in a V shape
            self._spawn_v_pattern(count, spawn_shooters=spawn_shooters) # <<< Pass flag
            
        else:
            # Default to vertical pattern if unknown pattern type
            logger.warning(f"Unknown pattern type: {pattern_type}. Using vertical formation.")
            playfield_height = PLAYFIELD_BOTTOM_Y - PLAYFIELD_TOP_Y
            spacing = playfield_height / (count + 1)
            self._spawn_vertical_pattern(count, int(spacing), spawn_shooters=spawn_shooters) # <<< Pass flag

    def _spawn_vertical_pattern(self, count: int, spacing_y: int, spawn_shooters: bool = False): # <<< Add spawn_shooters flag
        """Creates a vertical line of enemies entering from right."""
        # Calculate the playfield height for spacing
        playfield_height = PLAYFIELD_BOTTOM_Y - PLAYFIELD_TOP_Y
        
        # Fixed enemy height estimate
        enemy_height = 40
        
        # Total pattern height
        total_height = (count - 1) * spacing_y + enemy_height
        
        # Center the pattern vertically
        start_y = PLAYFIELD_TOP_Y + (playfield_height - total_height) // 2
        
        # Fixed horizontal offset past right edge
        x_pos = SCREEN_WIDTH + 50
        
        # Create the enemies
        for i in range(count):
            y_pos = start_y + i * spacing_y
            # <<< Choose enemy type based on flag
            if spawn_shooters:
                enemy = EnemyShooter(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            else:
                enemy = EnemyType1(self.all_sprites, self.enemies)
            # Use the property setter instead of direct rect access
            enemy.topleft = (x_pos, y_pos)

    def _spawn_horizontal_pattern(self, count: int, spawn_shooters: bool = False): # <<< Add spawn_shooters flag
        """Creates a horizontal line of enemies entering from right."""
        # Spacing between enemies horizontally
        spacing_x = 60
        
        # Center the pattern vertically in the playfield
        y_pos = (PLAYFIELD_TOP_Y + PLAYFIELD_BOTTOM_Y) // 2
        
        # Base horizontal position
        base_x = SCREEN_WIDTH + 50
        
        # Create the enemies
        for i in range(count):
            x_pos = base_x + i * spacing_x
            # <<< Choose enemy type based on flag
            if spawn_shooters:
                enemy = EnemyShooter(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            else:
                enemy = EnemyType1(self.all_sprites, self.enemies)
            # Use the property setter instead of direct rect access
            enemy.topleft = (x_pos, y_pos)

    def _spawn_diagonal_pattern(self, count: int, spawn_shooters: bool = False): # <<< Add spawn_shooters flag
        """Creates a diagonal line of enemies entering from right."""
        # Spacing between enemies
        spacing_x = 50
        spacing_y = 50
        
        # Start position (top of playfield)
        start_x = SCREEN_WIDTH + 50
        
        # Adjust start_y based on count to keep the pattern within the playfield
        available_height = PLAYFIELD_BOTTOM_Y - PLAYFIELD_TOP_Y - 40 # 40 is enemy height estimate
        max_drop = (count - 1) * spacing_y
        
        if max_drop > available_height:
            # Scale down spacing to fit
            spacing_y = available_height / (count - 1) if count > 1 else 0
        
        start_y = PLAYFIELD_TOP_Y + 20 # Start near top with a small margin
        
        # Create the enemies
        for i in range(count):
            x_pos = start_x + i * spacing_x
            y_pos = start_y + i * spacing_y
            # <<< Choose enemy type based on flag
            if spawn_shooters:
                enemy = EnemyShooter(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            else:
                enemy = EnemyType1(self.all_sprites, self.enemies)
            # Use the property setter instead of direct rect access
            enemy.topleft = (x_pos, y_pos)

    def _spawn_v_pattern(self, count: int, spawn_shooters: bool = False): # <<< Add spawn_shooters flag
        """Creates a V-shaped formation of enemies entering from right."""
        # Need an odd number for the V-pattern to look symmetrical
        if count % 2 == 0:
            count += 1
        
        # Center enemy is at the front of the V
        center_index = count // 2
        
        # Spacing between enemies
        spacing_x = 40
        spacing_y = 40
        
        # Center position
        center_x = SCREEN_WIDTH + 50
        center_y = (PLAYFIELD_TOP_Y + PLAYFIELD_BOTTOM_Y) // 2
        
        # Create the enemies
        for i in range(count):
            # Calculate position relative to center
            index_from_center = i - center_index
            
            # X increases as we go away from center in either direction
            x_pos = center_x + abs(index_from_center) * spacing_x
            
            # Y increases as we go away from center
            y_pos = center_y + index_from_center * spacing_y
            
            # <<< Choose enemy type based on flag
            if spawn_shooters:
                enemy = EnemyShooter(self.player, self.enemy_bullets, self.all_sprites, self.enemies)
            else:
                enemy = EnemyType1(self.all_sprites, self.enemies)
            # Use the property setter instead of direct rect access
            enemy.topleft = (x_pos, y_pos)

    def _update(self):
        """Updates the state of all game objects and handles collisions."""
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
            self.sound_manager.play("laser", "player")
            self.last_laser_sound_time = current_time
            
        # Check for new enemy bullets by comparing counts
        current_enemy_bullet_count = len(self.enemy_bullets)
        if current_enemy_bullet_count > self.previous_enemy_bullet_count:
            # New enemy bullets were created
            self.sound_manager.play("laser", "enemy")
        self.previous_enemy_bullet_count = current_enemy_bullet_count
        
        # Update background layers
        for layer in self.background_layers:
            layer.update()
        
        # Update border layers
        for border in self.borders:
            border.update()
            
        # Update player and other sprites
        self.all_sprites.update() # This calls update() on Player, Bullets, and Enemies
        self.enemy_bullets.update()
        self.explosions.update() # Update explosion animations
        # self.level_manager.update() # Update level/spawn enemies later

        # Check for collisions
        self._handle_collisions()

        # Check for game over conditions later
        pass

    def _handle_collisions(self):
        """Checks and handles collisions between game objects."""
        # Collision: Player Bullets vs Enemies
        # pygame.sprite.groupcollide detects collisions between sprites in two groups.
        # The two booleans determine if the colliding sprites should be killed (removed).
        # True means kill the sprite upon collision.
        # We use pygame.sprite.collide_mask for pixel-perfect collision detection.
        hits = pygame.sprite.groupcollide(self.enemies, self.bullets, True, True, pygame.sprite.collide_mask)
        for enemy in hits: # Iterate through enemies that were hit
             # Play enemy explosion sound
            self.sound_manager.play("explosion2", "enemy")
            # TODO: Add score for hitting enemies
            # TODO: Spawn explosion effect

        # Skip collision handling if player is not alive
        if not self.player.is_alive:
            return

        # We'll still detect collisions but damage handling is in take_damage
        # which checks for invincibility

        # Collision: Player vs Enemies
        # We check if the player sprite collides with any sprite in the enemies group.
        # True means the enemy sprite is killed on collision.
        # We handle player death/damage logic separately.
        enemy_hits = pygame.sprite.spritecollide(self.player, self.enemies, True, pygame.sprite.collide_mask)
        if enemy_hits:
            # Play player explosion sound for each enemy hit
            for enemy in enemy_hits:
                self.sound_manager.play("explosion2", "enemy")
                
            # Play hit sound for player
            self.sound_manager.play("hit1", "player")
            logger.warning("Player hit by enemy!")
            # Apply damage to player
            player_alive = self.player.take_damage()
            if not player_alive:
                self._handle_game_over()

        # Collision: Player vs Enemy Bullets
        enemy_bullet_hits = pygame.sprite.spritecollide(self.player, self.enemy_bullets, True, pygame.sprite.collide_mask)
        if enemy_bullet_hits:
            # Play a different sound for bullet hit
            self.sound_manager.play("hit1", "player")
            logger.warning("Player hit by enemy bullet!")
            # Apply damage to player
            player_alive = self.player.take_damage()
            if not player_alive:
                self._handle_game_over()

    def _render(self):
        """Draws the game state to the screen."""
        # Explicitly fill the screen first to prevent smearing artifacts
        self.screen.fill(BLACK)

        # Draw background layers (slowest first)
        for layer in self.background_layers:
            layer.draw(self.screen)

        # Draw player and other sprites on top
        self.all_sprites.draw(self.screen)
        # Draw enemy bullets
        self.enemy_bullets.draw(self.screen)
        # Draw explosions
        self.explosions.draw(self.screen)
        
        # Fill any gaps at screen edges with black to ensure borders are flush
        pygame.draw.rect(self.screen, BLACK, (0, 0, SCREEN_WIDTH, PLAYFIELD_TOP_Y))
        pygame.draw.rect(self.screen, BLACK, (0, PLAYFIELD_BOTTOM_Y, SCREEN_WIDTH, SCREEN_HEIGHT - PLAYFIELD_BOTTOM_Y))
        
        # Draw border layers on top of everything
        for border in self.borders:
            border.draw(self.screen)
            
        # Draw power bar
        if self.player.is_alive:
            power_bar = self.player.get_power_bar_image()
            power_bar_rect = power_bar.get_rect()
            power_bar_rect.topleft = (20, 15)  # Position in top-left corner with margin
            self.screen.blit(power_bar, power_bar_rect)
            
        # Draw game over message if necessary
        if self.game_over:
            game_over_text = self.game_over_font.render("GAME OVER", True, RED)
            text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(game_over_text, text_rect)
            
        pygame.display.flip()
        
    def _handle_game_over(self):
        """Handles the game over state when player loses all power."""
        # Play explosion sound
        self.sound_manager.play("explosion1", "player")
        logger.warning("Game over - Player destroyed!")
        
        # Create explosion effect at the player's position
        explosion_size = (100, 100)  # Size of the explosion
        Explosion(self.player.rect.center, explosion_size, self.explosions)
        
        # Make player invisible but don't remove from groups yet
        self.player.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        
        # Set game over flag
        self.game_over = True
        
        # We'll keep the game running until the explosion animation completes
        # Set a timer for game end
        pygame.time.set_timer(pygame.USEREVENT, 2000)  # 2 seconds delay
