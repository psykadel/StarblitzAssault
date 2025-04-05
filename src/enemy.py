"""Defines enemy types and behaviors."""

import pygame
import random
import os # Import os
from typing import TYPE_CHECKING, List

# Import the sprite loading utility
from src.utils.sprite_loader import load_sprite_sheet, DEFAULT_CROP_BORDER_PIXELS
from src.enemy_bullet import EnemyBullet

# Import config variables and constants
from src.config import (
    SPRITES_DIR,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PLAYFIELD_TOP_Y,    # Import playfield boundaries
    PLAYFIELD_BOTTOM_Y
)

# Constants for enemy
ENEMY1_SCALE_FACTOR = 0.20 # Adjust scale as needed
ENEMY1_ANIMATION_SPEED_MS = 100 # Animation speed
ENEMY1_SPEED_X = -3 # Pixels per frame (moving left)

# Avoid circular imports for type checking
# if TYPE_CHECKING:
#     pass

class Enemy(pygame.sprite.Sprite):
    """Base class for all enemy types."""
    def __init__(self, *groups) -> None: # Accept sprite groups
        """Initializes a generic enemy sprite."""
        super().__init__(*groups) # Pass groups to Sprite initializer
        self.frames: List[pygame.Surface] = []
        self.frame_index: int = 0
        # Initialize with placeholder surface/rect/mask before specific type loads
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA) # 1x1 transparent placeholder
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.last_frame_update: int = pygame.time.get_ticks()

        # Movement speed - subclasses should override
        self.speed_x: float = 0
        self.speed_y: float = 0

        # Default starting position removed - will be set externally after init
        # self.rect.topleft = (SCREEN_WIDTH + 50, random.randrange(0, SCREEN_HEIGHT))

    def _animate(self) -> None:
        """Cycles through the animation frames."""
        if not self.frames: return # Don't animate if no frames

        now = pygame.time.get_ticks()
        if now - self.last_frame_update > ENEMY1_ANIMATION_SPEED_MS: # Use enemy-specific constant
            self.last_frame_update = now
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            # Update image and rect
            # Check if frames exist before accessing index
            if self.frames and 0 <= self.frame_index < len(self.frames):
                old_center = self.rect.center
                self.image = self.frames[self.frame_index]
                self.rect = self.image.get_rect(center=old_center)
                self.mask = pygame.mask.from_surface(self.image)
            # else: print(f"Warning: Invalid frame index {self.frame_index} in Enemy._animate" )

    def update(self) -> None:
        """Updates the enemy's position and animation."""
        self._animate()
        # Convert float position changes to int before updating rect
        new_x = self.rect.x + self.speed_x
        new_y = self.rect.y + self.speed_y
        self.rect.x = int(new_x)
        self.rect.y = int(new_y)

        # Remove if it moves completely off the left side of the screen
        if self.rect.right < 0:
            self.kill() # Remove sprite from all groups

    def shoot(self) -> None:
        """Allows enemy to shoot projectiles."""
        # Placeholder for enemy shooting logic - implement later if needed
        pass

    # No common load_sprites needed in base if each enemy type loads differently
    # def load_sprites(self) -> None:
    #     pass

# Renaming Grunt to represent enemy1 specifically
class EnemyType1(Enemy):
    """Represents the enemy type from enemy1.png."""
    def __init__(self, *groups) -> None:
        super().__init__(*groups)

        # Load frames using the utility function
        # Break long function call
        self.frames = load_sprite_sheet(
            filename="enemy1.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=ENEMY1_SCALE_FACTOR,
            crop_border=DEFAULT_CROP_BORDER_PIXELS,
            flip_horizontal=True # Flip the enemy sprite
        )

        if not self.frames:
            print("Error: EnemyType1 frames list is empty after loading!")
            # Fallback or raise error - Parent init already created a rect
            self.kill() # Remove this instance if loading failed
            return

        # Set initial image and rect based on loaded frames
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)

        # Initial position setting moved out of __init__
        # self.rect.left = SCREEN_WIDTH + random.randrange(50, 200) # Start further off screen
        # # Ensure spawn is within playfield boundaries, adjusting for enemy height
        # max_top_y = PLAYFIELD_BOTTOM_Y - self.rect.height
        # min_top_y = PLAYFIELD_TOP_Y
        # if max_top_y < min_top_y: # Handle cases where enemy is taller than playfield
        #     max_top_y = min_top_y
        # self.rect.top = random.randrange(min_top_y, max_top_y + 1)

        # Set movement speed
        self.speed_x = ENEMY1_SPEED_X
        self.speed_y = 0 # No vertical movement for now

# New enemy class that shoots bullets towards the player
class EnemyShooter(Enemy):
    ENEMY_SHOOT_COOLDOWN_MS = 1500  # milliseconds throttle between shots

    def __init__(self, player_ref, bullet_group, *groups) -> None:
        super().__init__(*groups)
        self.player_ref = player_ref
        self.bullet_group = bullet_group
        self.frames = load_sprite_sheet(
            filename="enemy2.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=ENEMY1_SCALE_FACTOR,
            crop_border=DEFAULT_CROP_BORDER_PIXELS,
            flip_horizontal=True
        )
        if not self.frames:
            print("Error: EnemyShooter frames list is empty after loading!")
            self.kill()
            return
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.speed_x = ENEMY1_SPEED_X
        self.speed_y = 0
        self.last_shot_time = pygame.time.get_ticks()

    def update(self) -> None:
        # Animate and move the shooter enemy
        self._animate()
        new_x = self.rect.x + self.speed_x
        new_y = self.rect.y + self.speed_y
        self.rect.x = int(new_x)
        self.rect.y = int(new_y)
        
        # Shooting logic: fire a bullet toward the player's current position
        now = pygame.time.get_ticks()
        if now - self.last_shot_time > self.ENEMY_SHOOT_COOLDOWN_MS:
            self.last_shot_time = now
            target_pos = self.player_ref.rect.center
            EnemyBullet(self.rect.center, target_pos, self.bullet_group)
        
        # Remove the enemy if it moves completely off screen
        if self.rect.right < 0:
            self.kill()

# Add more enemy classes as needed (e.g., Charger, Shooter, Boss)
