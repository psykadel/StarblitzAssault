"""Defines the player character (Starblitz fighter)."""

import pygame
import os
import random
from typing import TYPE_CHECKING, Tuple, List

# Import the Bullet class
from src.projectile import Bullet
# Import the sprite loading utility
from src.utils.sprite_loader import load_sprite_sheet, DEFAULT_CROP_BORDER_PIXELS

# Import config variables
from src.config import (
    SPRITES_DIR, PLAYER_SPEED, PLAYER_SHOOT_DELAY, SCREEN_WIDTH,
    SCREEN_HEIGHT, PLAYFIELD_TOP_Y, PLAYFIELD_BOTTOM_Y
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
        
        # Flag to track continuous firing state
        self.is_firing: bool = False
        
        # Hit effect properties
        self.is_flashing: bool = False
        self.flash_start_time: int = 0
        self.flash_duration: int = 200  # Flash duration in milliseconds
        self.original_frames: List[pygame.Surface] = []

    def load_sprites(self) -> None:
        """Loads animation frames using the utility function."""
        self.frames = load_sprite_sheet(
            filename="main-character.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=PLAYER_SCALE_FACTOR,
            crop_border=5 # Try a larger crop (was 4)
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

        # Update position - Apply diagonal movement normalization for consistent speed
        if self.speed_x != 0 and self.speed_y != 0:
            # Normalize diagonal movement to maintain consistent speed
            # Using approximately 0.7071 (1/sqrt(2)) for normalization
            self.speed_x *= 0.7071
            self.speed_y *= 0.7071

        # Apply movement with slight smoothing for better feel
        new_x = self.rect.x + self.speed_x
        new_y = self.rect.y + self.speed_y
        
        # Round to nearest pixel for smoother movement
        self.rect.x = round(new_x)
        self.rect.y = round(new_y)

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
        if self.is_firing:
            self.shoot() # shoot() already handles the cooldown
            
        # Update flash effect if active
        if self.is_flashing:
            self._update_flash()

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
            
            # The sound is now played in the game_loop when firing starts

    def _handle_continuous_shooting(self) -> None:
        """Checks if the shoot key is held and calls shoot() if allowed."""
        keys = pygame.key.get_pressed() # Get state of all keys
        if keys[pygame.K_SPACE]:
            self.is_firing = True
            self.shoot() # shoot() already handles the cooldown
        else:
            self.is_firing = False

    def flash(self) -> None:
        """
        Start a flash effect to indicate the player was hit.
        This temporarily changes the player sprite to a flashing version.
        """
        if not self.is_flashing:
            self.is_flashing = True
            self.flash_start_time = pygame.time.get_ticks()
            
            # Store original frames if not already stored
            if not self.original_frames:
                self.original_frames = self.frames.copy()
            
            # Create flashed (white) versions of all frames
            self.frames = []
            for frame in self.original_frames:
                # Create a white silhouette of the ship
                flashed_frame = frame.copy()
                white_overlay = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
                white_overlay.fill((255, 255, 255, 180))  # Semi-transparent white
                flashed_frame.blit(white_overlay, (0, 0))
                self.frames.append(flashed_frame)
            
            # Update current image to show flash immediately
            old_center = self.rect.center
            self.image = self.frames[self.frame_index]
            self.rect = self.image.get_rect(center=old_center)
    
    def _update_flash(self) -> None:
        """Update the flash effect and revert to normal when duration is over."""
        current_time = pygame.time.get_ticks()
        if current_time - self.flash_start_time > self.flash_duration:
            # Revert to original frames
            self.is_flashing = False
            if self.original_frames:
                self.frames = self.original_frames.copy()
                self.original_frames = []
                
                # Update current image to normal immediately
                old_center = self.rect.center
                self.image = self.frames[self.frame_index]
                self.rect = self.image.get_rect(center=old_center)
