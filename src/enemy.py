"""Defines enemy types and behaviors."""

import pygame
import random
import os
from typing import TYPE_CHECKING, List, Optional

# Import the sprite loading utility
from src.sprite_loader import load_sprite_sheet, DEFAULT_CROP_BORDER_PIXELS
from src.enemy_bullet import EnemyBullet
from src.animated_sprite import AnimatedSprite
from src.logger import get_logger

# Import config variables and constants
from config.game_config import (
    SPRITES_DIR,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PLAYFIELD_TOP_Y,
    PLAYFIELD_BOTTOM_Y,
    ENEMY1_SCALE_FACTOR,
    ENEMY1_ANIMATION_SPEED_MS,
    ENEMY1_SPEED_X,
    ENEMY_SHOOTER_COOLDOWN_MS
)

# Get a logger for this module
logger = get_logger(__name__)

class Enemy(AnimatedSprite):
    """Base class for all enemy types."""
    def __init__(self, *groups) -> None:
        """Initializes a generic enemy sprite."""
        super().__init__(ENEMY1_ANIMATION_SPEED_MS, *groups)

    def update(self) -> None:
        """Updates the enemy's position and animation."""
        # Call parent update for animation and movement
        super().update()

        # Remove if it moves completely off the left side of the screen
        if self.rect.right < 0:
            self.kill()  # Remove sprite from all groups
            logger.debug(f"Enemy killed - moved off screen")

    def shoot(self) -> None:
        """Allows enemy to shoot projectiles."""
        # Placeholder for enemy shooting logic - implement in subclasses
        pass

# Renaming Grunt to represent enemy1 specifically
class EnemyType1(Enemy):
    """Represents the basic enemy type."""
    def __init__(self, *groups) -> None:
        super().__init__(*groups)

        # Load frames using the utility function
        self.frames = load_sprite_sheet(
            filename="enemy1.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=ENEMY1_SCALE_FACTOR,
            crop_border=DEFAULT_CROP_BORDER_PIXELS,
            flip_horizontal=True  # Flip the enemy sprite
        )

        if not self.frames:
            logger.error("EnemyType1 frames list is empty after loading!")
            # Fallback or raise error - Parent init already created a rect
            self.kill()  # Remove this instance if loading failed
            return

        # Set initial image and rect based on loaded frames
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        
        # Make sure to synchronize the float position trackers with the rect position
        self._pos_x = float(self.rect.x)
        self._pos_y = float(self.rect.y)

        # Set movement speed
        self.set_speed(ENEMY1_SPEED_X, 0)  # No vertical movement for now

# New enemy class that shoots bullets towards the player
class EnemyShooter(Enemy):
    """Enemy that shoots bullets at the player."""
    
    def __init__(self, player_ref, bullet_group, *groups) -> None:
        super().__init__(*groups)
        
        self.player_ref = player_ref
        self.bullet_group = bullet_group
        self.last_shot_time = pygame.time.get_ticks()
        
        self.frames = load_sprite_sheet(
            filename="enemy2.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=ENEMY1_SCALE_FACTOR,
            crop_border=DEFAULT_CROP_BORDER_PIXELS,
            flip_horizontal=True
        )
        
        if not self.frames:
            logger.error("EnemyShooter frames list is empty after loading!")
            self.kill()
            return
            
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        
        # Make sure to synchronize the float position trackers with the rect position
        self._pos_x = float(self.rect.x)
        self._pos_y = float(self.rect.y)
        
        # Set movement speed
        self.set_speed(ENEMY1_SPEED_X, 0)

    def update(self) -> None:
        # Call the parent class update for animation and basic movement
        super().update()
        
        # Shooting logic: fire a bullet toward the player's current position
        now = pygame.time.get_ticks()
        if now - self.last_shot_time > ENEMY_SHOOTER_COOLDOWN_MS:
            self.last_shot_time = now
            self._fire_at_player()

    def _fire_at_player(self) -> None:
        """Fire a bullet at the player's current position."""
        if not self.player_ref:
            return
            
        target_pos = self.player_ref.rect.center
        # Create a new enemy bullet
        bullet = EnemyBullet(self.rect.center, target_pos, self.bullet_group)
        logger.debug(f"Enemy fired bullet from {self.rect.center} toward {target_pos}")
        # Sound will be handled in the game_loop where we have access to the sound manager

# Add more enemy classes as needed (e.g., Charger, Shooter, Boss)
