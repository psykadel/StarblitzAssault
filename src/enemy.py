"""Defines enemy types and behaviors."""

import pygame
import random
import os
import math
from typing import TYPE_CHECKING, List, Optional

# Import the sprite loading utility
from src.sprite_loader import load_sprite_sheet, DEFAULT_CROP_BORDER_PIXELS
from src.enemy_bullet import EnemyBullet, BouncingBullet, SpiralBullet, ExplosiveBullet, HomingBullet, WaveBullet
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
            crop_border=DEFAULT_CROP_BORDER_PIXELS
        )

        if not self.frames:
            logger.error("EnemyType1 frames list is empty after loading!")
            # Fallback or raise error - Parent init already created a rect
            self.kill()  # Remove this instance if loading failed
            return
            
        # Flip the sprites horizontally
        self.frames = [pygame.transform.flip(frame, True, False) for frame in self.frames]

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
            crop_border=DEFAULT_CROP_BORDER_PIXELS
        )
        
        if not self.frames:
            logger.error("EnemyShooter frames list is empty after loading!")
            self.kill()
            return
            
        # Flip the sprites horizontally
        self.frames = [pygame.transform.flip(frame, True, False) for frame in self.frames]
            
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

# Enemy Type 3: Oscillating movement pattern with wave projectiles
class EnemyType3(Enemy):
    """Enemy that moves in a vertical oscillating pattern and fires wave projectiles."""
    
    def __init__(self, player_ref, bullet_group, *groups) -> None:
        super().__init__(*groups)
        
        self.player_ref = player_ref
        self.bullet_group = bullet_group
        self.last_shot_time = pygame.time.get_ticks()
        
        # Oscillation parameters
        self.oscillation_amplitude = 100  # pixels
        self.oscillation_speed = 0.05
        self.oscillation_time = 0
        self.base_y = 0  # Will be set when positioned
        
        self.frames = load_sprite_sheet(
            filename="enemy3.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=ENEMY1_SCALE_FACTOR,
            crop_border=DEFAULT_CROP_BORDER_PIXELS
        )
        
        if not self.frames:
            logger.error("EnemyType3 frames list is empty after loading!")
            self.kill()
            return
            
        # Flip the sprites horizontally
        self.frames = [pygame.transform.flip(frame, True, False) for frame in self.frames]
            
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        
        # Make sure to synchronize the float position trackers with the rect position
        self._pos_x = float(self.rect.x)
        self._pos_y = float(self.rect.y)
        
        # Set movement speed (slightly slower than standard)
        self.set_speed(ENEMY1_SPEED_X * 0.8, 0)

    def update(self) -> None:
        # Store the original base_y if this is the first update
        if self.base_y == 0:
            self.base_y = self._pos_y
        
        # Update oscillation time
        self.oscillation_time += self.oscillation_speed
        
        # Calculate vertical position using sine wave
        vertical_offset = self.oscillation_amplitude * math.sin(self.oscillation_time)
        self._pos_y = self.base_y + vertical_offset
        
        # Update rect position from float position
        self.rect.y = round(self._pos_y)
        
        # Call parent update for animation and horizontal movement
        super().update()
        
        # Shooting logic
        now = pygame.time.get_ticks()
        if now - self.last_shot_time > ENEMY_SHOOTER_COOLDOWN_MS * 1.5:  # Slower fire rate
            self.last_shot_time = now
            self._fire_wave_projectiles()

    def _fire_wave_projectiles(self) -> None:
        """Fire projectiles that move in a wave pattern."""
        if not self.player_ref:
            return
            
        # Fire two wave bullets with opposite wave patterns
        bullet_up = WaveBullet(self.rect.center, -1, self.bullet_group)
        bullet_down = WaveBullet((self.rect.centerx, self.rect.centery + 10), -1, self.bullet_group)
        
        # Offset the waves so they appear to alternate
        bullet_down.distance_traveled = bullet_up.wave_frequency * math.pi
        
        logger.debug(f"Enemy fired wave bullets from {self.rect.center}")

# Enemy Type 4: Erratic movement with spiral projectiles and homing missiles
class EnemyType4(Enemy):
    """Enemy that moves erratically and fires spiraling projectiles and homing missiles."""
    
    def __init__(self, player_ref, bullet_group, *groups) -> None:
        super().__init__(*groups)
        
        self.player_ref = player_ref
        self.bullet_group = bullet_group
        self.last_shot_time = pygame.time.get_ticks()
        self.last_homing_shot_time = pygame.time.get_ticks() - 1500  # Offset to not fire both at once
        self.direction_change_time = pygame.time.get_ticks()
        self.direction_change_delay = 1000  # ms between direction changes
        self.homing_shot_cooldown = ENEMY_SHOOTER_COOLDOWN_MS * 3  # Longer cooldown for homing shots
        
        self.frames = load_sprite_sheet(
            filename="enemy4.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=ENEMY1_SCALE_FACTOR,
            crop_border=DEFAULT_CROP_BORDER_PIXELS
        )
        
        if not self.frames:
            logger.error("EnemyType4 frames list is empty after loading!")
            self.kill()
            return
            
        # Flip the sprites horizontally
        self.frames = [pygame.transform.flip(frame, True, False) for frame in self.frames]
            
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        
        # Make sure to synchronize the float position trackers with the rect position
        self._pos_x = float(self.rect.x)
        self._pos_y = float(self.rect.y)
        
        # Set initial movement speed (horizontal component is fixed)
        self.set_speed(ENEMY1_SPEED_X * 1.2, random.uniform(-2, 2))

    def update(self) -> None:
        # Call the parent class update for animation and basic movement
        super().update()
        
        # Change direction randomly
        now = pygame.time.get_ticks()
        if now - self.direction_change_time > self.direction_change_delay:
            self.direction_change_time = now
            # Keep moving left but change vertical direction randomly
            self.set_speed(self.speed_x, random.uniform(-2, 2))
        
        # Ensure enemy stays within playfield vertically
        if self.rect.top < PLAYFIELD_TOP_Y:
            self.rect.top = PLAYFIELD_TOP_Y
            self._pos_y = float(self.rect.y)
            self.speed_y = abs(self.speed_y)  # Reverse direction
        
        if self.rect.bottom > PLAYFIELD_BOTTOM_Y:
            self.rect.bottom = PLAYFIELD_BOTTOM_Y
            self._pos_y = float(self.rect.y)
            self.speed_y = -abs(self.speed_y)  # Reverse direction
        
        # Shooting logic for spiral bullets
        now = pygame.time.get_ticks()
        if now - self.last_shot_time > ENEMY_SHOOTER_COOLDOWN_MS:
            self.last_shot_time = now
            self._fire_spiral_projectile()
            
        # Separate timing for homing bullets
        if now - self.last_homing_shot_time > self.homing_shot_cooldown:
            self.last_homing_shot_time = now
            self._fire_homing_projectile()

    def _fire_spiral_projectile(self) -> None:
        """Fire spiral projectiles in multiple directions."""
        if not self.player_ref:
            return
        
        # Fire multiple spiral projectiles in different directions
        for angle in range(0, 360, 72):  # 5 bullets in a circle
            bullet = SpiralBullet(self.rect.center, angle, self.bullet_group)
        
        logger.debug(f"Enemy fired spiral bullets from {self.rect.center}")
        
    def _fire_homing_projectile(self) -> None:
        """Fire a homing projectile that follows the player."""
        if not self.player_ref:
            return
            
        # Create one homing bullet that tracks the player
        bullet = HomingBullet(self.rect.center, self.player_ref, self.bullet_group)
        logger.debug(f"Enemy fired homing bullet from {self.rect.center}")

# Enemy Type 5: Seeking behavior with explosive projectiles
class EnemyType5(Enemy):
    """Enemy that seeks the player's vertical position and fires explosive and advanced homing projectiles."""
    
    def __init__(self, player_ref, bullet_group, *groups) -> None:
        super().__init__(*groups)
        
        self.player_ref = player_ref
        self.bullet_group = bullet_group
        self.last_explosive_shot_time = pygame.time.get_ticks()
        self.last_homing_shot_time = pygame.time.get_ticks() - 2000  # Offset to not fire both at once
        
        # Movement parameters
        self.vertical_speed = 2.0  # Max speed for vertical tracking
        
        # Firing parameters
        self.explosive_cooldown = ENEMY_SHOOTER_COOLDOWN_MS * 2
        self.homing_cooldown = ENEMY_SHOOTER_COOLDOWN_MS * 2.5
        
        self.frames = load_sprite_sheet(
            filename="enemy5.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=ENEMY1_SCALE_FACTOR,
            crop_border=DEFAULT_CROP_BORDER_PIXELS
        )
        
        if not self.frames:
            logger.error("EnemyType5 frames list is empty after loading!")
            self.kill()
            return
            
        # Flip the sprites horizontally
        self.frames = [pygame.transform.flip(frame, True, False) for frame in self.frames]
            
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        
        # Make sure to synchronize the float position trackers with the rect position
        self._pos_x = float(self.rect.x)
        self._pos_y = float(self.rect.y)
        
        # Set initial movement speed
        self.set_speed(ENEMY1_SPEED_X * 0.7, 0)  # Slower horizontal movement

    def update(self) -> None:
        # Track player's vertical position
        if self.player_ref:
            # Calculate vertical distance to player
            player_y = self.player_ref.rect.centery
            distance_y = player_y - self.rect.centery
            
            # Set vertical speed proportional to distance (with a max)
            if abs(distance_y) > 10:  # Small dead zone to prevent jitter
                self.speed_y = max(min(distance_y * 0.05, self.vertical_speed), -self.vertical_speed)
            else:
                self.speed_y = 0
        
        # Call parent update for animation and movement
        super().update()
        
        # Get current time once for both weapon systems
        now = pygame.time.get_ticks()
        
        # Explosive projectile firing logic
        if now - self.last_explosive_shot_time > self.explosive_cooldown:
            self.last_explosive_shot_time = now
            self._fire_explosive_projectile()
            
        # Homing projectile firing logic
        if now - self.last_homing_shot_time > self.homing_cooldown:
            self.last_homing_shot_time = now
            self._fire_advanced_homing_projectile()

    def _fire_explosive_projectile(self) -> None:
        """Fire a projectile that explodes after a short time."""
        if not self.player_ref:
            return
        
        # Create a new explosive bullet
        bullet = ExplosiveBullet(self.rect.center, self.bullet_group)
        logger.debug(f"Enemy fired explosive bullet from {self.rect.center}")
        
    def _fire_advanced_homing_projectile(self) -> None:
        """Fire advanced homing projectiles that track the player."""
        if not self.player_ref:
            return
            
        # Fire two homing bullets, one from each "wing" of the enemy
        offset_left = (-20, -5)  # Offset from center for left projectile
        offset_right = (-20, 5)  # Offset for right projectile
        
        # Calculate spawn positions
        left_pos = (self.rect.centerx + offset_left[0], self.rect.centery + offset_left[1])
        right_pos = (self.rect.centerx + offset_right[0], self.rect.centery + offset_right[1])
        
        # Create the homing bullets
        bullet1 = HomingBullet(left_pos, self.player_ref, self.bullet_group)
        bullet2 = HomingBullet(right_pos, self.player_ref, self.bullet_group)
        
        logger.debug(f"Enemy fired advanced homing bullets from {self.rect.center}")

# Add more enemy classes as needed (e.g., Charger, Shooter, Boss)
