"""Defines the player character (Starblitz fighter)."""

import pygame
import os
from typing import TYPE_CHECKING, Tuple, List

# Import the Bullet class
from src.projectile import Bullet
# Import the sprite loading utility
from src.utils.sprite_loader import load_sprite_sheet, DEFAULT_CROP_BORDER_PIXELS

# Import config variables
from src.config import (
    SPRITES_DIR,
    PLAYER_SPEED,
    PLAYER_SHOOT_DELAY,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PLAYFIELD_TOP_Y,    # Import playfield boundaries
    PLAYFIELD_BOTTOM_Y,
    # WHITE, # Not needed for convert_alpha()
)

# Constants for animation
ANIMATION_SPEED_MS = 75 # Milliseconds per frame
PLAYER_SCALE_FACTOR = 0.25 # Adjusted scale factor for bigger ship

# Avoid circular imports for type checking - though not strictly needed now
# if TYPE_CHECKING:
#     pass # No forward refs needed currently

class Player(pygame.sprite.Sprite):
    """Represents the player-controlled spaceship."""
    def __init__(self, all_sprites: pygame.sprite.Group, bullets: pygame.sprite.Group) -> None:
        """Initializes the player sprite."""
        super().__init__()

        self.all_sprites = all_sprites
        self.bullets = bullets
        self.frames: List[pygame.Surface] = []
        # Load frames using the utility function
        self.load_sprites()

        # --- Initialization continues after load_sprites sets self.frames ---
        if not self.frames:
            print("Error: Player frames list is empty after loading!")
            raise SystemExit()

        # Animation state
        self.frame_index: int = 0
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.last_frame_update: int = pygame.time.get_ticks()

        # Initial position for side-scroller (e.g., left middle)
        # Position is set after getting the rect from the loaded/scaled/cropped image
        self.rect.left = 50
        self.rect.centery = SCREEN_HEIGHT // 2

        # Movement state (primarily vertical for side-scroller)
        self.speed_x: float = 0
        self.speed_y: float = 0

        # Shooting cooldown timer
        self.last_shot_time: int = pygame.time.get_ticks()

    def load_sprites(self) -> None:
        """Loads animation frames using the utility function."""
        self.frames = load_sprite_sheet(
            filename="main-character.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=PLAYER_SCALE_FACTOR,
            crop_border=3 # Increase crop specifically for player
            # grid_dimensions=(3, 3) # This is the default in the utility
        )
        # Error handling is done within load_sprite_sheet, which raises SystemExit

    def _animate(self) -> None:
        """Cycles through the animation frames."""
        now = pygame.time.get_ticks()
        if now - self.last_frame_update > ANIMATION_SPEED_MS:
            self.last_frame_update = now
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            # Update image and rect (important to keep center position)
            old_center = self.rect.center
            self.image = self.frames[self.frame_index]
            self.rect = self.image.get_rect(center=old_center)
            self.mask = pygame.mask.from_surface(self.image) # Update mask if using pixel-perfect collision

    def update(self) -> None:
        """Updates the player's position, animation, and handles continuous shooting."""
        self._animate()

        # Update position
        self.rect.x += self.speed_x
        self.rect.y += self.speed_y

        # Keep player on screen (Adjust boundaries for side-scroller)
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
        # Use playfield boundaries for vertical movement
        if self.rect.top < PLAYFIELD_TOP_Y:
            self.rect.top = PLAYFIELD_TOP_Y
        if self.rect.bottom > PLAYFIELD_BOTTOM_Y:
            self.rect.bottom = PLAYFIELD_BOTTOM_Y

        # Check for continuous shooting
        self._handle_continuous_shooting()

    def _handle_continuous_shooting(self) -> None:
        """Checks if the shoot key is held and calls shoot() if allowed."""
        keys = pygame.key.get_pressed() # Get state of all keys
        if keys[pygame.K_SPACE]:
            self.shoot() # shoot() already handles the cooldown

    def handle_input(self, event: pygame.event.Event) -> None:
        """Handles player input for movement (KEYDOWN/KEYUP). Shooting handled in update."""
        if event.type == pygame.KEYDOWN:
            # Adjusted for side-scroller (Up/Down primary)
            if event.key == pygame.K_UP:
                self.speed_y = -PLAYER_SPEED
            elif event.key == pygame.K_DOWN:
                self.speed_y = PLAYER_SPEED
            # Optional: Allow limited horizontal movement
            elif event.key == pygame.K_LEFT:
                 self.speed_x = -PLAYER_SPEED / 2 # Slower horizontal?
            elif event.key == pygame.K_RIGHT:
                 self.speed_x = PLAYER_SPEED / 2
            # Remove single-press shooting from here
            # elif event.key == pygame.K_SPACE:
            #     self.shoot()

        if event.type == pygame.KEYUP:
            # Stop movement only if the released key matches the current direction
            if event.key == pygame.K_UP and self.speed_y < 0:
                self.speed_y = 0
            elif event.key == pygame.K_DOWN and self.speed_y > 0:
                self.speed_y = 0
            elif event.key == pygame.K_LEFT and self.speed_x < 0:
                 self.speed_x = 0
            elif event.key == pygame.K_RIGHT and self.speed_x > 0:
                 self.speed_x = 0

    def shoot(self) -> None:
        """Creates a projectile sprite (bullet) firing forward."""
        now = pygame.time.get_ticks()
        if now - self.last_shot_time > PLAYER_SHOOT_DELAY:
            self.last_shot_time = now
            # Bullet starts at the front-center of the player
            bullet = Bullet(self.rect.right, self.rect.centery)
            self.all_sprites.add(bullet)
            self.bullets.add(bullet)
            # Optional: Play shooting sound
            # print("Player shoots!") # Keep for debugging if needed
