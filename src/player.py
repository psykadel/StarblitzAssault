"""Defines the player character (Starblitz fighter)."""

import pygame
import os
import random
from typing import TYPE_CHECKING, Tuple, List

# Import the Bullet class
from src.projectile import Bullet
# Import the sprite loading utility
from src.sprite_loader import load_sprite_sheet, DEFAULT_CROP_BORDER_PIXELS
# Import base animated sprite
from src.animated_sprite import AnimatedSprite
# Import logger
from src.logger import get_logger

# Import config variables
from config.game_config import (
    SPRITES_DIR, PLAYER_SPEED, PLAYER_SHOOT_DELAY, SCREEN_WIDTH,
    SCREEN_HEIGHT, PLAYFIELD_TOP_Y, PLAYFIELD_BOTTOM_Y,
    PLAYER_SCALE_FACTOR, PLAYER_ANIMATION_SPEED_MS
)

# Get a logger for this module
logger = get_logger(__name__)

class Player(AnimatedSprite):
    """Represents the player-controlled spaceship."""
    def __init__(self, bullets: pygame.sprite.Group, *groups) -> None:
        """Initializes the player sprite."""
        super().__init__(PLAYER_ANIMATION_SPEED_MS, *groups)

        self.bullets = bullets
        # Load frames using the utility function
        self.load_sprites()

        # Check if sprite loading was successful
        if not self.frames:
            logger.error("Player frames list is empty after loading!")
            raise SystemExit()

        # Set initial image from frames
        self.frame_index = 0
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)

        # Initial position for side-scroller (e.g., left middle)
        self.rect.left = 50
        self.rect.centery = SCREEN_HEIGHT // 2
        # Initialize float position trackers
        self._pos_x = float(self.rect.x)
        self._pos_y = float(self.rect.y)

        # Shooting cooldown timer
        self.last_shot_time: int = pygame.time.get_ticks()
        
        # Flag to track continuous firing state
        self.is_firing: bool = False

    def load_sprites(self) -> None:
        """Loads animation frames using the utility function."""
        self.frames = load_sprite_sheet(
            filename="main-character.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=PLAYER_SCALE_FACTOR,
            crop_border=5 # Try a larger crop (was 4)
        )
        # Error handling is done within load_sprite_sheet, which raises SystemExit

    def update(self) -> None:
        """Updates the player's position, animation, and handles continuous shooting."""
        # Call parent update for animation and movement
        super().update()

        # Update position - Apply diagonal movement normalization for consistent speed
        if self.speed_x != 0 and self.speed_y != 0:
            # Normalize diagonal movement to maintain consistent speed
            # Using approximately 0.7071 (1/sqrt(2)) for normalization
            self.speed_x *= 0.7071
            self.speed_y *= 0.7071

        # Keep player on screen (Adjust boundaries for side-scroller)
        if self.rect.left < 0:
            self.rect.left = 0
            self._pos_x = float(self.rect.x)
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self._pos_x = float(self.rect.x)
        # Use playfield boundaries for vertical movement
        if self.rect.top < PLAYFIELD_TOP_Y:
            self.rect.top = PLAYFIELD_TOP_Y
            self._pos_y = float(self.rect.y)
        if self.rect.bottom > PLAYFIELD_BOTTOM_Y:
            self.rect.bottom = PLAYFIELD_BOTTOM_Y
            self._pos_y = float(self.rect.y)

        # Check for continuous shooting
        if self.is_firing:
            self.shoot() # shoot() already handles the cooldown

    def start_firing(self) -> None:
        """Begins continuous firing."""
        self.is_firing = True
        
    def stop_firing(self) -> None:
        """Stops continuous firing."""
        self.is_firing = False

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
            all_sprites_group = self.groups()[0] if self.groups() else None
            if all_sprites_group:
                Bullet(self.rect.right, self.rect.centery, all_sprites_group, self.bullets)
                logger.debug(f"Player fired bullet at position {self.rect.right}, {self.rect.centery}")
            # The sound is now played in the game_loop when firing starts
