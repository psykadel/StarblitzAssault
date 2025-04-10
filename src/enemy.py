"""Defines enemy types and behaviors."""

import math
import os
import random
from typing import TYPE_CHECKING, List, Optional

import pygame

# Import config variables and constants
from config.config import (
    BASE_ENEMY_FREQUENCIES,
    ENEMY_ANIMATION_SPEED_MS,
    ENEMY_SCALE_FACTOR,
    ENEMY_SHOOTER_COOLDOWN_MS,
    ENEMY_SPEED_X,
    ENEMY_TYPE_NAMES,
    ENEMY_TYPES,
    ENEMY_UNLOCK_THRESHOLDS,
    FREQUENCY_SCALING,
    MAX_FREQUENCIES,
    MIN_FREQUENCIES,
    PLAYFIELD_BOTTOM_Y,
    PLAYFIELD_TOP_Y,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SPRITES_DIR,
)
from src.animated_sprite import AnimatedSprite
from src.enemy_bullet import (
    BouncingBullet,
    EnemyBullet,
    ExplosiveBullet,
    HomingBullet,
    SpiralBullet,
    WaveBullet,
)
from src.logger import get_logger

# Import the sprite loading utility
from src.sprite_loader import load_sprite_sheet

# Get a logger for this module
logger = get_logger(__name__)


def get_enemy_weights(difficulty_level: float) -> List[int]:
    """Calculate enemy spawn weights based on current difficulty level.

    Args:
        difficulty_level: Current game difficulty level

    Returns:
        List of weights for each enemy type (index corresponds to enemy type)
    """
    weights = [0] * 8  # Initialize weights for all 8 enemy types

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
        if (
            difficulty_level >= ENEMY_UNLOCK_THRESHOLDS.get(enemy_type, 1.0)
            and weights[enemy_type] < MIN_FREQUENCIES[enemy_type]
        ):
            weights[enemy_type] = MIN_FREQUENCIES[enemy_type]

    # Ensure weights sum to 100 (adjust highest weight if needed)
    weight_sum = sum(weights)
    if weight_sum != 100:
        # Find the enemy type with highest frequency and adjust it
        max_idx = weights.index(max(weights))
        weights[max_idx] += 100 - weight_sum

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
            alignment="right",
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
            alignment="right",
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
            alignment="right",
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
        self.last_homing_shot_time = (
            pygame.time.get_ticks() - 1500
        )  # Offset to not fire both at once
        self.direction_change_time = pygame.time.get_ticks()
        self.direction_change_delay = 1000  # ms between direction changes
        self.homing_shot_cooldown = (
            ENEMY_SHOOTER_COOLDOWN_MS * 3
        )  # Longer cooldown for homing shots

        self.frames = load_sprite_sheet(
            filename="enemy4.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=ENEMY_SCALE_FACTOR,
            alignment="right",
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
        self.last_homing_shot_time = (
            pygame.time.get_ticks() - 2000
        )  # Offset to not fire both at once

        # Movement parameters
        self.vertical_speed = 2.0  # Max speed for vertical tracking

        # Firing parameters
        self.explosive_cooldown = ENEMY_SHOOTER_COOLDOWN_MS * 2
        self.homing_cooldown = ENEMY_SHOOTER_COOLDOWN_MS * 2.5

        self.frames = load_sprite_sheet(
            filename="enemy5.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=ENEMY_SCALE_FACTOR,
            alignment="right",
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
                self.speed_y = max(
                    min(distance_y * 0.05, self.vertical_speed), -self.vertical_speed
                )
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
            alignment="right",
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
        self.set_speed(
            ENEMY_SPEED_X * 0.6 * self.direction_x, ENEMY_SPEED_X * 0.4 * self.direction_y
        )

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
        if (
            not self.teleport_effect_active
            and now - self.last_shot_time > ENEMY_SHOOTER_COOLDOWN_MS * 1.8
        ):
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
        self.set_speed(
            ENEMY_SPEED_X * 0.6 * self.direction_x, ENEMY_SPEED_X * 0.4 * self.direction_y
        )

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


# Enemy Type 7: Reflector enemy that can reflect player bullets and fire laser beams
class EnemyType7(Enemy):
    """Reflector enemy that can reflect player bullets and fire laser beams."""

    def __init__(self, player_ref, bullet_group, *groups) -> None:
        super().__init__(*groups)

        self.player_ref = player_ref
        self.bullet_group = bullet_group
        
        # Load the sprite frames
        self.frames = load_sprite_sheet(
            filename="enemy7.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=ENEMY_SCALE_FACTOR,
            alignment="right",
        )

        if not self.frames:
            logger.error("EnemyType7 frames list is empty after loading!")
            self.kill()
            return

        # Flip the sprites horizontally
        self.frames = [pygame.transform.flip(frame, True, False) for frame in self.frames]

        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)

        # Position tracking
        self._pos_x = float(self.rect.x)
        self._pos_y = float(self.rect.y)

        # Reflection shield properties
        self.reflection_active = False
        self.reflection_cooldown = random.randint(3000, 5000)  # ms between reflections
        self.reflection_duration = 2000  # ms the reflection shield is active
        self.last_reflection_time = 0
        self.reflection_radius = 40  # pixels
        self.shield_pulse_offset = 0  # For pulsating effect
        self.shield_pulse_speed = 0.2  # Speed of pulse animation
        
        # Simplified laser attack properties
        self.max_laser_shots = random.randint(1, 2)  # Each enemy can fire only 1-2 lasers
        self.laser_shots_fired = 0
        self.can_fire_laser = False  # Will be set to true when enemy is in position
        self.min_laser_x = SCREEN_WIDTH * 0.6  # Only fire when in the right 60% of screen
        self.laser_cooldown = random.randint(1500, 3000)  # Much longer cooldown
        self.last_laser_time = pygame.time.get_ticks()
        
        # Movement pattern: strafing horizontally
        self.initial_speed_x = ENEMY_SPEED_X * 0.6  # Slower horizontal movement
        self.strafe_speed_y = 2.0  # Vertical movement during strafing
        self.strafe_direction = 1 if random.random() > 0.5 else -1  # Random initial direction
        self.strafe_time = 0
        self.strafe_period = 180  # Full strafe cycle duration in frames (3 seconds at 60fps)
        
        # Visual effects
        self.shield_color = (100, 200, 255)  # Blue shield
        self.shield_color2 = (50, 150, 255)  # Darker blue for gradient
        self.shield_alpha = 0  # Start with invisible shield
        
        # Initial speed
        self.set_speed(self.initial_speed_x, 0)

    def update(self) -> None:
        # Call the parent class update for animation and basic movement
        super().update()
        
        now = pygame.time.get_ticks()
        
        # Update strafe movement
        self.strafe_time = (self.strafe_time + 1) % self.strafe_period
        # Calculate vertical speed based on sine wave
        progress = self.strafe_time / self.strafe_period
        vertical_offset = math.sin(progress * 2 * math.pi) * self.strafe_speed_y
        self.set_speed(self.initial_speed_x, vertical_offset * self.strafe_direction)
        
        # Update shield pulse animation
        self.shield_pulse_offset = (self.shield_pulse_offset + self.shield_pulse_speed) % 10
        
        # Handle reflection shield
        if not self.reflection_active and now - self.last_reflection_time > self.reflection_cooldown:
            # Activate reflection
            self.reflection_active = True
            self.last_reflection_time = now
            # Play shield activation sound (handled in game_loop)
        elif self.reflection_active and now - self.last_reflection_time > self.reflection_duration:
            # Deactivate reflection
            self.reflection_active = False
            # Reset cooldown
            self.reflection_cooldown = random.randint(3000, 5000)
            
        # Update shield alpha for visual effect
        if self.reflection_active:
            self.shield_alpha = min(180, self.shield_alpha + 15)  # Fade in
        else:
            self.shield_alpha = max(0, self.shield_alpha - 15)  # Fade out
            
        # SIMPLIFIED LASER FIRING LOGIC
        # Only fire if we haven't reached max shots and we're in the right part of the screen
        if self.laser_shots_fired < self.max_laser_shots:
            # Check if we're in position to fire
            if self.rect.right < SCREEN_WIDTH and self.rect.right > self.min_laser_x:
                # Only fire after cooldown
                if now - self.last_laser_time > self.laser_cooldown:
                    self._fire_laser()
                    self.last_laser_time = now
                    self.laser_shots_fired += 1
                    # Increase cooldown after each shot to prevent rapid firing
                    self.laser_cooldown = random.randint(2000, 4000)

    def draw(self, surface):
        """Override draw method to add reflection shield visual."""
        # Draw the enemy sprite
        surface.blit(self.image, self.rect)
        
        # Draw reflection shield if active
        if self.shield_alpha > 0:
            # Get current pulse size for outer and inner rings
            pulse_size = 4 + math.sin(self.shield_pulse_offset) * 3
            inner_radius = self.reflection_radius - pulse_size
            
            # Create shield surface
            shield_surf = pygame.Surface((self.reflection_radius * 2 + 10, self.reflection_radius * 2 + 10), pygame.SRCALPHA)
            shield_center = (self.reflection_radius + 5, self.reflection_radius + 5)
            
            # Draw outer glow
            glow_color = (*self.shield_color, max(20, self.shield_alpha // 3))
            pygame.draw.circle(shield_surf, glow_color, shield_center, self.reflection_radius + 5)
            
            # Draw main shield
            shield_color_with_alpha = (*self.shield_color, self.shield_alpha)
            pygame.draw.circle(shield_surf, shield_color_with_alpha, shield_center, self.reflection_radius)
            
            # Draw inner ring
            inner_color = (*self.shield_color2, self.shield_alpha)
            pygame.draw.circle(shield_surf, inner_color, shield_center, inner_radius)
            
            # Draw hexagonal pattern for tech look
            if self.shield_alpha > 80:  # Only show pattern when shield is more visible
                segments = 6  # Hexagonal pattern
                line_thickness = 2
                for i in range(segments):
                    angle1 = 2 * math.pi * i / segments
                    angle2 = 2 * math.pi * ((i + 1) % segments) / segments
                    
                    # Middle ring
                    middle_radius = self.reflection_radius * 0.75
                    start_pos = (
                        shield_center[0] + middle_radius * math.cos(angle1),
                        shield_center[1] + middle_radius * math.sin(angle1)
                    )
                    end_pos = (
                        shield_center[0] + middle_radius * math.cos(angle2),
                        shield_center[1] + middle_radius * math.sin(angle2)
                    )
                    line_color = (220, 240, 255, min(255, self.shield_alpha + 40))
                    pygame.draw.line(shield_surf, line_color, start_pos, end_pos, line_thickness)
            
            # Add a bright border
            border_color = (200, 230, 255, min(255, self.shield_alpha + 50))
            pygame.draw.circle(shield_surf, border_color, shield_center, self.reflection_radius, 2)
            
            # Blit to screen
            shield_rect = shield_surf.get_rect(center=self.rect.center)
            surface.blit(shield_surf, shield_rect)
    
    def _fire_laser(self) -> None:
        """Fire a laser beam from the enemy."""
        if not self.bullet_group:
            return
            
        # Fire laser from front of ship aimed at player
        from src.enemy_bullet import LaserBeam
        
        # Fire from left side (facing the player)
        laser_start = (self.rect.left, self.rect.centery)
        # Direction is leftward (negative x) - laser extends toward player side
        LaserBeam(laser_start, 8, self.bullet_group)
        # Sound will be handled in game_loop


# Enemy Type 8: Lightboard racer that tries to collide with the player
class EnemyType8(Enemy):
    """Enemy that rides a lightboard and tries to directly collide with the player."""

    def __init__(self, player_ref, *groups) -> None:
        super().__init__(*groups)

        self.player_ref = player_ref
        
        # Special parameters for the lightboard enemy
        self.charge_cooldown = 2000  # ms between charges
        self.last_charge_time = pygame.time.get_ticks()
        self.is_charging = False
        self.charge_speed = 8.0  # Higher speed during charge
        self.normal_speed = -1.5  # Slower base speed (moves left)
        self.charge_duration = 1500  # ms
        self.charge_start_time = 0
        
        # Particle effect parameters
        self.particle_timer = 0
        self.particle_spawn_rate = 5  # frames between particle spawns
        self.light_trail = []  # Store light trail particles
        self.max_trail_length = 15
        self.trail_colors = [
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
            (255, 255, 0),  # Yellow
            (0, 255, 0),    # Green
            (255, 128, 0)   # Orange
        ]

        # Load sprite frames
        self.frames = load_sprite_sheet(
            filename="enemy8.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=ENEMY_SCALE_FACTOR * 1.2,  # Slightly larger than other enemies
            alignment="right",
        )

        if not self.frames:
            logger.error("EnemyType8 frames list is empty after loading!")
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
        self.set_speed(self.normal_speed, 0)
        
        # Light effect surfaces
        self.glow_surface = None
        self._create_glow_surface()

    def _create_glow_surface(self):
        """Create a glowing effect surface."""
        size = max(self.rect.width, self.rect.height) * 2
        self.glow_surface = pygame.Surface((size, size), pygame.SRCALPHA)
        
        # Create a radial gradient
        center = size // 2
        max_radius = size // 2 - 5
        for radius in range(max_radius, 0, -1):
            alpha = int(80 * (radius / max_radius))
            color = random.choice(self.trail_colors) + (alpha,)
            pygame.draw.circle(self.glow_surface, color, (center, center), radius)

    def update(self) -> None:
        """Update the enemy's behavior, movement and effects."""
        # Call parent update for animation
        super().update()
        
        now = pygame.time.get_ticks()
        
        # Check if we are currently in a charge
        if self.is_charging:
            # If charge duration completed, go back to normal movement
            if now - self.charge_start_time > self.charge_duration:
                self.is_charging = False
                self.set_speed(self.normal_speed, 0)
                logger.debug("Lightboard enemy ended charge")
        else:
            # If not charging, check if it's time to charge
            if now - self.last_charge_time > self.charge_cooldown and self.player_ref:
                # Start a charge toward the player's current position
                self._start_charge()
                self.last_charge_time = now
                self.charge_start_time = now
        
        # Update light trail particles
        self.particle_timer += 1
        if self.is_charging and self.particle_timer >= self.particle_spawn_rate:
            self.particle_timer = 0
            self._spawn_trail_particle()
            
        # Maintain trail length
        while len(self.light_trail) > self.max_trail_length:
            self.light_trail.pop(0)
            
        # Update trail particles
        for particle in self.light_trail:
            particle["alpha"] -= 5
            if particle["alpha"] <= 0:
                self.light_trail.remove(particle)

    def _start_charge(self) -> None:
        """Start a charge toward the player's current position."""
        if not self.player_ref:
            return
            
        self.is_charging = True
        
        # Calculate direction to player
        target_x, target_y = self.player_ref.rect.center
        current_x, current_y = self.rect.center
        
        # Calculate the angle
        dx = target_x - current_x
        dy = target_y - current_y
        
        # Normalize the direction
        distance = max(1, math.sqrt(dx * dx + dy * dy))
        dx /= distance
        dy /= distance
        
        # Set velocity toward player
        self.set_speed(dx * self.charge_speed, dy * self.charge_speed)
        logger.debug(f"Lightboard enemy charging at player from {(current_x, current_y)} to {(target_x, target_y)}")

    def _spawn_trail_particle(self) -> None:
        """Spawn a light trail particle behind the enemy."""
        color = random.choice(self.trail_colors)
        
        offset_x = random.randint(-5, 5)
        offset_y = random.randint(-5, 5)
        
        particle = {
            "pos": (self.rect.centerx + offset_x, self.rect.centery + offset_y),
            "color": color,
            "size": random.randint(5, 15),
            "alpha": 200
        }
        
        self.light_trail.append(particle)

    def draw(self, surface):
        """Custom draw method to render the light trail and glow effects."""
        # Draw light trail particles first
        for particle in self.light_trail:
            pos = particle["pos"]
            color = particle["color"] + (particle["alpha"],)
            size = particle["size"]
            glow_rect = pygame.Rect(0, 0, size * 2, size * 2)
            glow_rect.center = pos
            
            # Create a small surface for this particle with alpha
            particle_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(particle_surf, color, (size, size), size)
            
            # Draw the particle
            surface.blit(particle_surf, glow_rect)
        
        # Draw glow effect during charge
        if self.is_charging and self.glow_surface:
            glow_rect = self.glow_surface.get_rect(center=self.rect.center)
            surface.blit(self.glow_surface, glow_rect)
        
        # Draw the enemy sprite on top
        surface.blit(self.image, self.rect)


# Add more enemy classes as needed (e.g., Charger, Shooter, Boss)
