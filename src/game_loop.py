"""Main game loop and event handling."""

import pygame
import os # Import os
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
    PLAYFIELD_BOTTOM_Y  # Add missing playfield boundary import
)

# Define background speeds
BG_LAYER_SPEEDS = [0.5, 1.0, 1.5] # Slowest to fastest

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

        pygame.display.set_caption("Starblitz Assault") # From game.mdc

        self.clock = pygame.time.Clock()
        self.is_running = True

        # Initialize background layers
        self.background_layers = []
        bg_image_path = os.path.join(BACKGROUNDS_DIR, "starfield.png")
        if os.path.exists(bg_image_path):
            # Calculate approximate initial offsets based on screen width
            # Get image width *after* scaling to screen height for better offsets
            try:
                temp_layer_for_width = BackgroundLayer(bg_image_path, 0, self.current_screen_height)
                bg_image_width = temp_layer_for_width.image_width
                # Use more distinct offsets (e.g., 0, 1/4, 3/4)
                initial_offsets = [0, bg_image_width / 4, bg_image_width * 3 / 4]
                del temp_layer_for_width # Clean up temporary layer
            except Exception:
                print("Warning: Could not get background width for offsets. Using defaults.")
                initial_offsets = [0, 100, 200] # Fallback offsets

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
        """Processes user input and game events."""
        # No need to filter resize events anymore
        events = pygame.event.get() # Get all events
        # Or: events = pygame.event.get(exclude=pygame.VIDEORESIZE)

        for event in events:
            if event.type == pygame.QUIT:
                self.is_running = False
            # Handle wave timer event
            elif event.type == WAVE_TIMER_EVENT:
                self.spawn_enemy_wave(count=5, spacing_y=80) # Example wave

            # Pass other events to the player for input handling
            self.player.handle_input(event)

    def spawn_enemy_wave(self, count: int, spacing_y: int):
        """Spawns a simple wave of enemies.

        Args:
            count: Number of enemies in the wave.
            spacing_y: Vertical spacing between enemies.
        """
        # Basic example: Spawn enemies in a vertical line entering from right
        # Calculate starting Y to center the wave approximately
        # Need enemy height - get it from a temporary instance
        # Note: This assumes all EnemyType1 are the same height
        try:
            temp_enemy = EnemyType1()
            enemy_height = temp_enemy.rect.height
            temp_enemy.kill()
            total_wave_height = (count - 1) * spacing_y + enemy_height
            start_y = max(PLAYFIELD_TOP_Y, (self.current_screen_height - total_wave_height) // 2)
        except Exception as e:
            print(f"Warning: Could not get enemy height for wave positioning: {e}. Using default Y.")
            start_y = PLAYFIELD_TOP_Y + 50 # Fallback start position
            enemy_height = 50 # Fallback height

        for i in range(count):
            y_pos = start_y + i * spacing_y
            # Ensure the calculated position is within bounds
            y_pos = max(PLAYFIELD_TOP_Y, min(y_pos, PLAYFIELD_BOTTOM_Y - enemy_height))
            # Create enemy instance, no need to manually set position here
            # as __init__ now handles random Y within playfield
            # Instead, we could modify __init__ or add a method to set specific pos
            # For now, let's stick to the random Y pos within __init__
            # but trigger multiple spawns for a 'wave'
            EnemyType1(self.all_sprites, self.enemies)

        # Optionally, restart the wave timer here or base it on enemies cleared
        # pygame.time.set_timer(WAVE_TIMER_EVENT, WAVE_DELAY_MS) # Simple restart

    def _update(self):
        """Updates the state of all game objects and handles collisions."""
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
        for enemy_hit in hits:
            # Optional: Add explosion effect, score increase, etc.
            print(f"Enemy hit!")
            pass

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
