"""Main game loop and event handling."""

import pygame
import os # Import os
import random # Import random for random range
import math # Import math for trig functions
# from pygame._sdl2 import Window # Removed - No longer using maximize

# Import game components and config
from src.player import Player
from src.background import BackgroundLayer # Import BackgroundLayer
from src.enemy import EnemyType1 # Import the specific enemy class
from src.config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FPS,
    BLACK,
    BACKGROUNDS_DIR, # Import background directory path
    ENEMY_SPAWN_RATE, # Import spawn rate from config
    PLAYFIELD_TOP_Y,    # Add missing playfield boundary import
    PLAYFIELD_BOTTOM_Y,  # Add missing playfield boundary import
    PLAYER_SPEED,  # Added PLAYER_SPEED from config
    PLAYER_SHOOT_DELAY  # Added for laser sound timing
)
# Remove the non-existent imports
# from src.utils.constants import *
# from src.debug import draw_debug_info
# from src.hud import HUD

# Import sound manager
from src.sound_manager import SoundManager

# Define background speeds
BG_LAYER_SPEEDS = [0.5, 1.0, 1.5] # Slowest to fastest

# Enemy pattern types
PATTERN_VERTICAL = 0   # Enemies in a straight vertical line
PATTERN_HORIZONTAL = 1 # Enemies in a straight horizontal line
PATTERN_DIAGONAL = 2   # Enemies in a diagonal line
PATTERN_V_SHAPE = 3    # Enemies in a V formation
PATTERN_COUNT = 4      # Total number of patterns

# Custom Pygame Events
# ENEMY_SPAWN_EVENT = pygame.USEREVENT + 1 # Removed - using wave logic
WAVE_TIMER_EVENT = pygame.USEREVENT + 1 # Timer to trigger next wave
WAVE_DELAY_MS = 5000 # Time between enemy waves (milliseconds)

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
                print(f"Warning: Could not get background width for offsets: {e}. Using defaults.")
                # Defaults already set above

            for i, speed in enumerate(BG_LAYER_SPEEDS):
                offset = initial_offsets[i % len(initial_offsets)] # Cycle through offsets
                layer = BackgroundLayer(bg_image_path, speed, self.current_screen_height, initial_scroll=offset)
                self.background_layers.append(layer)
        else:
            print(f"Warning: Background image not found at {bg_image_path}. Skipping background.")

        # Initialize sprite groups
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group() # Group for enemies
        self.bullets = pygame.sprite.Group() # Group specifically for bullets

        # Initialize game components
        self.player = Player(self.all_sprites, self.bullets)
        self.all_sprites.add(self.player)
        # self.level_manager = LevelManager() # Not used yet

        # Initialize sound manager
        self.sound_manager = SoundManager()
        
        # Start background music
        self.sound_manager.play_music("background-music-level-1.mp3", loops=-1)
        
        # Laser sound timer - for continuous fire sound
        self.last_laser_sound_time = 0

        # Simple wave management state
        self.wave_active = False
        pygame.time.set_timer(WAVE_TIMER_EVENT, WAVE_DELAY_MS) # Timer for next wave

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
                    print(f"Music volume: {pygame.mixer.music.get_volume():.1f}")
                    
                elif event.key == pygame.K_PLUS or event.key == pygame.K_KP_PLUS or event.key == pygame.K_EQUALS:
                    current_volume = pygame.mixer.music.get_volume()
                    self.sound_manager.set_music_volume(min(1.0, current_volume + 0.1))
                    print(f"Music volume: {pygame.mixer.music.get_volume():.1f}")
                    
                # Music toggle (M key)
                elif event.key == pygame.K_m:
                    if pygame.mixer.music.get_busy():
                        self.sound_manager.pause_music()
                        print("Music paused")
                    else:
                        self.sound_manager.unpause_music()
                        print("Music resumed")
                        
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    self.player.stop_firing()
            elif event.type == WAVE_TIMER_EVENT:
                # Select a random pattern type
                pattern_type = random.randint(0, 3)  # 0-3 for our four pattern types
                
                # Random count of enemies between 4 and 7
                count = random.randint(4, 7)
                
                print(f"Spawning wave of {count} enemies with pattern {pattern_type}")
                self.spawn_enemy_wave(count, pattern_type=pattern_type)
                
                # Play wave spawn sound
                self.sound_manager.play("powerup1", "enemy")
                
                # Reset the timer for the next wave
                pygame.time.set_timer(WAVE_TIMER_EVENT, random.randint(3000, 5000))

    def spawn_enemy_wave(self, count: int, pattern_type: int = PATTERN_VERTICAL):
        """
        Spawns a wave of enemies in a specific pattern.
        
        Args:
            count: Number of enemies to spawn
            pattern_type: The formation pattern to use
        """
        # Choose the pattern function based on pattern_type
        if pattern_type == PATTERN_VERTICAL:
            spacing_y = 60  # Vertical spacing between enemies
            self._spawn_vertical_pattern(count, spacing_y)
        elif pattern_type == PATTERN_HORIZONTAL:
            self._spawn_horizontal_pattern(count)
        elif pattern_type == PATTERN_DIAGONAL:
            self._spawn_diagonal_pattern(count)
        elif pattern_type == PATTERN_V_SHAPE:
            self._spawn_v_pattern(count)
        else:
            # Default to vertical pattern if invalid pattern type
            spacing_y = 60
            self._spawn_vertical_pattern(count, spacing_y)

    def _spawn_vertical_pattern(self, count: int, spacing_y: int):
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
            enemy = EnemyType1(self.all_sprites, self.enemies)
            enemy.rect.topleft = (int(x_pos), int(y_pos))

    def _spawn_horizontal_pattern(self, count: int):
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
            enemy = EnemyType1(self.all_sprites, self.enemies)
            enemy.rect.topleft = (int(x_pos), int(y_pos))

    def _spawn_diagonal_pattern(self, count: int):
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
            enemy = EnemyType1(self.all_sprites, self.enemies)
            enemy.rect.topleft = (int(x_pos), int(y_pos))

    def _spawn_v_pattern(self, count: int):
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
            
            enemy = EnemyType1(self.all_sprites, self.enemies)
            enemy.rect.topleft = (int(x_pos), int(y_pos))

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
            laser_variant = random.choice(["laser1", "laser2", "laser3"])
            self.sound_manager.play(laser_variant, "player")
            self.last_laser_sound_time = current_time
            
        # Update background layers
        for layer in self.background_layers:
            layer.update()
        # Update player and other sprites
        self.all_sprites.update() # This calls update() on Player, Bullets, and Enemies
        # self.level_manager.update() # Update level/spawn enemies later

        # Check for collisions
        self._handle_collisions()

        # Check for game over conditions later
        pass

    def _handle_collisions(self):
        """Checks and handles collisions between game objects."""
        # Check for bullet hitting enemies
        # groupcollide finds collisions between two groups
        # The two True arguments mean both the bullet and the enemy are killed upon collision
        hits = pygame.sprite.groupcollide(self.enemies, self.bullets, True, True)
        # hits is a dictionary where keys are enemies hit, values are lists of bullets that hit them
        
        # Count hits for feedback, but no need to loop
        if hits:
            print(f"Enemies hit: {len(hits)}")
            # Play explosion sound
            explosion_type = random.choice(["explosion_small", "explosion_medium", "explosion_large"])
            self.sound_manager.play(explosion_type, "explosion")
            # Optional: Add explosion effect, score increase, etc.
            # Future: play explosion sound or spawn explosion animation

        # Check for player hitting enemies (optional: game over?)
        # player_hits = pygame.sprite.spritecollide(self.player, self.enemies, False) # False: player doesn't die instantly
        # if player_hits:
        #     print("Player collided with enemy!")
            # Handle player taking damage or game over

    def _render(self):
        """Draws the game state to the screen."""
        # Explicitly fill the screen first to prevent smearing artifacts
        self.screen.fill(BLACK)

        # Draw background layers (slowest first)
        for layer in self.background_layers:
            layer.draw(self.screen)

        # Draw player and other sprites on top
        self.all_sprites.draw(self.screen)
        # Draw UI elements (score, health, etc.) later
        pygame.display.flip()
