"""Defines enemy types and behaviors."""

import pygame
import random
import os # Import os
from typing import TYPE_CHECKING, List, Optional, Tuple

# Import the sprite loading utility
from src.utils.sprite_loader import load_sprite_sheet, DEFAULT_CROP_BORDER_PIXELS

# Import the enemy projectile
from src.projectile import EnemyProjectile

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
ENEMY1_SHOOT_DELAY = 2000  # Milliseconds between shots
ENEMY1_SHOOT_CHANCE = 0.02  # 2% chance per frame to shoot when able

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
        
        # Shooting properties
        self.can_shoot: bool = True
        self.last_shot_time: int = pygame.time.get_ticks()
        self.shoot_delay: int = ENEMY1_SHOOT_DELAY  # Default delay
        self.shoot_chance: float = ENEMY1_SHOOT_CHANCE  # Default chance
        
        # Reference to sprite groups for adding projectiles
        self.all_sprites: Optional[pygame.sprite.Group] = None
        self.enemy_projectiles: Optional[pygame.sprite.Group] = None

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
            
        # Check if should shoot
        if self.can_shoot and self.all_sprites and self.enemy_projectiles:
            self._try_shoot()

    def _try_shoot(self) -> None:
        """Try to shoot a projectile based on chance and cooldown."""
        now = pygame.time.get_ticks()
        
        # Check if enough time has passed since the last shot
        if now - self.last_shot_time > self.shoot_delay:
            # Random chance to fire
            if random.random() < self.shoot_chance:
                self.shoot()
                self.last_shot_time = now

    def shoot(self) -> None:
        """Shoot a projectile towards the player."""
        if not self.all_sprites or not self.enemy_projectiles:
            return
            
        # Create projectile at the left edge of the enemy
        projectile = EnemyProjectile(self.rect.left, self.rect.centery)
        
        # Add to sprite groups
        self.all_sprites.add(projectile)
        self.enemy_projectiles.add(projectile)
        
        # Sound effect will be handled in the game loop
        # We'll use an event to notify the game loop that an enemy has shot
        pygame.event.post(pygame.event.Event(
            pygame.USEREVENT, 
            {"type": "enemy_shoot", "position": self.rect.center}
        ))

    def set_projectile_groups(self, all_sprites: pygame.sprite.Group, 
                            enemy_projectiles: pygame.sprite.Group) -> None:
        """Set the sprite groups for adding projectiles."""
        self.all_sprites = all_sprites
        self.enemy_projectiles = enemy_projectiles

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

# Add more enemy classes as needed (e.g., Charger, Shooter, Boss)
