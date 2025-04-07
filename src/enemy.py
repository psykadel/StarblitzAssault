"""Defines enemy types and behaviors."""

import pygame
import random
import os
import math
from typing import TYPE_CHECKING, List, Optional

# Import the sprite loading utility
from src.sprite_loader import load_sprite_sheet
from src.enemy_bullet import EnemyBullet, BouncingBullet, SpiralBullet, ExplosiveBullet, HomingBullet, WaveBullet
from src.animated_sprite import AnimatedSprite
from src.logger import get_logger

# Import config variables and constants
from config.config import (
    SPRITES_DIR,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PLAYFIELD_TOP_Y,
    PLAYFIELD_BOTTOM_Y,
    ENEMY_SCALE_FACTOR,
    ENEMY_ANIMATION_SPEED_MS,
    ENEMY_SPEED_X,
    ENEMY_SHOOTER_COOLDOWN_MS,
    ENEMY_TYPES,
    ENEMY_TYPE_NAMES,
    BASE_ENEMY_FREQUENCIES,
    ENEMY_UNLOCK_THRESHOLDS,
    FREQUENCY_SCALING,
    MAX_FREQUENCIES,
    MIN_FREQUENCIES
)

# Get a logger for this module
logger = get_logger(__name__)

def get_enemy_weights(difficulty_level: float) -> List[int]:
    """Calculate enemy spawn weights based on current difficulty level.
    
    Args:
        difficulty_level: Current game difficulty level
        
    Returns:
        List of weights for each enemy type (index corresponds to enemy type)
    """
    weights = [0] * 6  # Initialize weights for all 6 enemy types
    
    for enemy_type, base_freq in BASE_ENEMY_FREQUENCIES.items():
        # Skip if enemy type is not yet unlocked at this difficulty
        if difficulty_level < ENEMY_UNLOCK_THRESHOLDS.get(enemy_type, 1.0):
            weights[enemy_type] = 0
            continue
            
        # Calculate weight based on difficulty scaling
        difficulty_factor = difficulty_level - 1  # Difficulty 1 is baseline (factor = 0)
        scaled_frequency = base_freq + (FREQUENCY_SCALING[enemy_type] * difficulty_factor)
        
        # Apply min/max constraints
        scaled_frequency = max(MIN_FREQUENCIES[enemy_type], scaled_frequency)
        scaled_frequency = min(MAX_FREQUENCIES[enemy_type], scaled_frequency)
        
        weights[enemy_type] = int(scaled_frequency)  # Cast to int to fix linter error
        
    # Normalize to ensure sum is 100
    weight_sum = sum(weights)
    if weight_sum > 0:  # Avoid division by zero
        weights = [int(w * 100 / weight_sum) for w in weights]
        
    # Ensure minimum weight for all unlocked enemy types
    for enemy_type in ENEMY_TYPES.values():
        if difficulty_level >= ENEMY_UNLOCK_THRESHOLDS.get(enemy_type, 1.0) and weights[enemy_type] < MIN_FREQUENCIES[enemy_type]:
            weights[enemy_type] = MIN_FREQUENCIES[enemy_type]
    
    # Ensure weights sum to 100 (adjust highest weight if needed)
    weight_sum = sum(weights)
    if weight_sum != 100:
        # Find the enemy type with highest frequency and adjust it
        max_idx = weights.index(max(weights))
        weights[max_idx] += (100 - weight_sum)
    
    return weights

class Enemy(AnimatedSprite):
    """Base class for all enemy types."""
    def __init__(self, *groups) -> None:
        """Initializes a generic enemy sprite."""
        super().__init__(ENEMY_ANIMATION_SPEED_MS, *groups)

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
            scale_factor=ENEMY_SCALE_FACTOR,
            alignment='right'
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
        self.set_speed(ENEMY_SPEED_X, 0)  # No vertical movement for now

# New enemy class that shoots bullets towards the player
class EnemyType2(Enemy):
    """Enemy that shoots bullets at the player."""
    
    def __init__(self, player_ref, bullet_group, *groups) -> None:
        super().__init__(*groups)
        
        self.player_ref = player_ref
        self.bullet_group = bullet_group
        self.last_shot_time = pygame.time.get_ticks()
        
        self.frames = load_sprite_sheet(
            filename="enemy2.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=ENEMY_SCALE_FACTOR,
            alignment='right'
        )
        
        if not self.frames:
            logger.error("EnemyType2 frames list is empty after loading!")
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
        self.set_speed(ENEMY_SPEED_X, 0)

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
            scale_factor=ENEMY_SCALE_FACTOR,
            alignment='right'
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
        self.set_speed(ENEMY_SPEED_X * 0.8, 0)

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
            scale_factor=ENEMY_SCALE_FACTOR,
            alignment='right'
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
        self.set_speed(ENEMY_SPEED_X * 1.2, random.uniform(-2, 2))

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
            scale_factor=ENEMY_SCALE_FACTOR,
            alignment='right'
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
        self.set_speed(ENEMY_SPEED_X * 0.7, 0)  # Slower horizontal movement

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

# Enemy Type 6: Teleporting enemy with bouncing projectiles
class EnemyType6(Enemy):
    """Enemy that teleports around and fires bouncing projectiles."""
    
    def __init__(self, player_ref, bullet_group, *groups) -> None:
        super().__init__(*groups)
        
        self.player_ref = player_ref
        self.bullet_group = bullet_group
        self.last_shot_time = pygame.time.get_ticks()
        
        # Teleport parameters
        self.teleport_delay = 3000  # ms between teleports
        self.last_teleport_time = pygame.time.get_ticks()
        self.teleport_effect_active = False
        self.teleport_effect_start = 0
        self.teleport_effect_duration = 500  # Effect lasts 500ms
        self.original_image = None  # Store original image for teleport effect
        
        # Movement parameters
        self.direction_x = -1  # Start moving left
        self.direction_y = random.choice([-1, 1])  # Random initial vertical direction
        
        self.frames = load_sprite_sheet(
            filename="enemy6.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=ENEMY_SCALE_FACTOR,
            alignment='right'
        )
        
        if not self.frames:
            logger.error("EnemyType6 frames list is empty after loading!")
            self.kill()
            return
            
        # Flip the sprites horizontally
        self.frames = [pygame.transform.flip(frame, True, False) for frame in self.frames]
            
        self.image = self.frames[self.frame_index]
        self.original_image = self.image.copy()  # Store for teleport effect
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        
        # Make sure to synchronize the float position trackers with the rect position
        self._pos_x = float(self.rect.x)
        self._pos_y = float(self.rect.y)
        
        # Set initial movement speed
        self.set_speed(ENEMY_SPEED_X * 0.6 * self.direction_x, 
                       ENEMY_SPEED_X * 0.4 * self.direction_y)

    def update(self) -> None:
        # Handle teleport visual effect
        now = pygame.time.get_ticks()
        
        if self.teleport_effect_active:
            # Calculate effect progress (0.0 to 1.0)
            elapsed = now - self.teleport_effect_start
            progress = min(1.0, elapsed / self.teleport_effect_duration)
            
            if progress < 1.0:
                # Create semi-transparent effect
                alpha = int(255 * (1.0 - progress))
                if self.original_image:
                    self.image = self.original_image.copy()
                    self.image.set_alpha(alpha)
            else:
                # End of effect
                self.teleport_effect_active = False
                if self.original_image:
                    self.image = self.original_image.copy()
                
                # Update the mask after image change
                self.mask = pygame.mask.from_surface(self.image)
        
        # Check if it's time to teleport
        if not self.teleport_effect_active and now - self.last_teleport_time > self.teleport_delay:
            self._teleport()
        
        # Call parent update for animation and movement
        super().update()
        
        # Ensure enemy stays within playfield vertically
        if self.rect.top < PLAYFIELD_TOP_Y:
            self.rect.top = PLAYFIELD_TOP_Y
            self._pos_y = float(self.rect.y)
            self.direction_y = 1
            self.speed_y = abs(self.speed_y)
        
        if self.rect.bottom > PLAYFIELD_BOTTOM_Y:
            self.rect.bottom = PLAYFIELD_BOTTOM_Y
            self._pos_y = float(self.rect.y)
            self.direction_y = -1
            self.speed_y = -abs(self.speed_y)
        
        # Shooting logic
        if not self.teleport_effect_active and now - self.last_shot_time > ENEMY_SHOOTER_COOLDOWN_MS * 1.8:
            self.last_shot_time = now
            self._fire_bouncing_projectiles()
    
    def _teleport(self) -> None:
        """Teleport to a random position on screen and reverse movement direction."""
        self.last_teleport_time = pygame.time.get_ticks()
        
        # Start teleport disappear effect
        self.teleport_effect_active = True
        self.teleport_effect_start = pygame.time.get_ticks()
        
        # Calculate new position
        new_x = random.randint(int(SCREEN_WIDTH * 0.5), int(SCREEN_WIDTH * 0.9))
        new_y = random.randint(PLAYFIELD_TOP_Y + 50, PLAYFIELD_BOTTOM_Y - 50)
        
        # Update position
        self.rect.center = (new_x, new_y)
        self._pos_x = float(self.rect.x)
        self._pos_y = float(self.rect.y)
        
        # Reverse movement direction
        self.direction_x = -1  # Always move left after teleport
        self.direction_y *= -1  # Reverse vertical direction
        
        # Update movement speeds
        self.set_speed(ENEMY_SPEED_X * 0.6 * self.direction_x, 
                      ENEMY_SPEED_X * 0.4 * self.direction_y)
        
        logger.debug(f"Enemy teleported to {self.rect.center}")
    
    def _fire_bouncing_projectiles(self) -> None:
        """Fire bouncing projectiles."""
        if not self.player_ref:
            return
        
        # Create two bouncing bullets with slightly different angles
        for angle_offset in [-20, 20]:
            # Calculate angle toward player
            dx = self.player_ref.rect.centerx - self.rect.centerx
            dy = self.player_ref.rect.centery - self.rect.centery
            angle = math.atan2(dy, dx)
            angle = math.degrees(angle) + angle_offset
            
            # Create the bouncing bullet
            bullet = BouncingBullet(self.rect.center, angle, self.bullet_group)
        
        logger.debug(f"Enemy fired bouncing bullets from {self.rect.center}")

# Add more enemy classes as needed (e.g., Charger, Shooter, Boss)
