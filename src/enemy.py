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
            alignment='right'
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

# Enemy Type 6: Teleporting enemy with bouncing projectiles
class EnemyType6(Enemy):
    """Enemy that teleports around the screen and fires bouncing projectiles."""
    
    def __init__(self, player_ref, bullet_group, *groups) -> None:
        super().__init__(*groups)
        
        self.player_ref = player_ref
        self.bullet_group = bullet_group
        self.last_shot_time = pygame.time.get_ticks()
        
        # Teleportation parameters
        self.teleport_delay = 2000  # ms between teleports
        self.last_teleport_time = pygame.time.get_ticks()
        self.teleport_radius = 150  # Teleport within this distance of previous position
        self.teleport_effect_duration = 15  # Frames for teleport effect
        self.teleport_effect = 0  # Current frame of teleport effect
        
        # Load frames
        self.frames = load_sprite_sheet(
            filename="enemy6.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=ENEMY1_SCALE_FACTOR,
            alignment='right'
        )
        
        if not self.frames:
            logger.error("EnemyType6 frames list is empty after loading!")
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
        
        # Set initial movement speed (slower than standard)
        self.set_speed(ENEMY1_SPEED_X * 0.6, 0)
        
        # Alpha for teleport effect
        self.alpha = 255
        self.teleporting = False

    def update(self) -> None:
        # Handle teleport visual effect
        if self.teleport_effect > 0:
            self.teleport_effect -= 1
            # Make sprite fade in during teleport effect
            self.alpha = int(255 * (1 - (self.teleport_effect / self.teleport_effect_duration)))
            # Apply alpha to image
            for i, frame in enumerate(self.frames):
                self.frames[i] = frame.copy()
                self.frames[i].set_alpha(self.alpha)
            
            # Update current image
            self.image = self.frames[self.frame_index]
        
        # Call parent update for animation and movement
        super().update()
        
        # Check if it's time to teleport
        now = pygame.time.get_ticks()
        if now - self.last_teleport_time > self.teleport_delay:
            self.last_teleport_time = now
            self._teleport()
        
        # Shooting logic: fire bouncing bullets
        if now - self.last_shot_time > ENEMY_SHOOTER_COOLDOWN_MS * 1.5:
            self.last_shot_time = now
            self._fire_bouncing_projectiles()
    
    def _teleport(self) -> None:
        """Teleport to a new random position."""
        # Set teleport effect
        self.teleport_effect = self.teleport_effect_duration
        
        # Current position
        current_x = self._pos_x
        current_y = self._pos_y
        
        # Generate new position within the screen boundaries and within teleport radius
        new_x = max(SCREEN_WIDTH * 0.5, min(SCREEN_WIDTH - self.rect.width, 
                    current_x + random.uniform(-self.teleport_radius, self.teleport_radius)))
        new_y = max(PLAYFIELD_TOP_Y, min(PLAYFIELD_BOTTOM_Y - self.rect.height, 
                    current_y + random.uniform(-self.teleport_radius, self.teleport_radius)))
        
        # Set new position
        self._pos_x = new_x
        self._pos_y = new_y
        self.rect.x = round(new_x)
        self.rect.y = round(new_y)
        
        logger.debug(f"Enemy teleported from ({current_x}, {current_y}) to ({new_x}, {new_y})")
        
    def _fire_bouncing_projectiles(self) -> None:
        """Fire projectiles that bounce off screen boundaries."""
        if not self.player_ref:
            return
        
        # Fire 3 bouncing bullets in different directions
        for i in range(3):
            bullet = BouncingBullet(self.rect.center, self.bullet_group)
        
        logger.debug(f"Enemy fired bouncing bullets from {self.rect.center}")

# Enemy Type 7: Rotating formation enemy with wave bullets
class EnemyType7(Enemy):
    """Enemy that rotates around a point and fires wave bullets in patterns."""
    
    def __init__(self, player_ref, bullet_group, *groups) -> None:
        super().__init__(*groups)
        
        self.player_ref = player_ref
        self.bullet_group = bullet_group
        self.last_shot_time = pygame.time.get_ticks()
        
        # Rotation parameters
        self.orbit_center_x = 0  # Will be set when positioned
        self.orbit_radius = 80
        self.angle = random.uniform(0, 360)
        self.rotation_speed = 1.5  # Degrees per frame
        
        # Bullet pattern parameters
        self.pattern_index = 0
        self.patterns = ["fan", "alternating"]
        self.current_pattern = self.patterns[0]
        self.pattern_change_delay = 5000  # ms between pattern changes
        self.last_pattern_change = pygame.time.get_ticks()
        
        # Load frames
        self.frames = load_sprite_sheet(
            filename="enemy7.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=ENEMY1_SCALE_FACTOR,
            alignment='right'
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
        
        # Make sure to synchronize the float position trackers with the rect position
        self._pos_x = float(self.rect.x)
        self._pos_y = float(self.rect.y)
        
        # No direct movement - orbit point will move
        self.set_speed(0, 0)

    def update(self) -> None:
        # Set orbit center if this is the first update
        if self.orbit_center_x == 0:
            self.orbit_center_x = self._pos_x + 100  # Orbit center is ahead of initial position
            self.orbit_center_y = self._pos_y
        
        # Orbital movement
        self.angle = (self.angle + self.rotation_speed) % 360
        
        # Calculate orbit center movement (it drifts left)
        self.orbit_center_x -= ENEMY1_SPEED_X * 0.5
        
        # Calculate position based on orbit
        rad_angle = math.radians(self.angle)
        self._pos_x = self.orbit_center_x + self.orbit_radius * math.cos(rad_angle)
        self._pos_y = self.orbit_center_y + self.orbit_radius * math.sin(rad_angle)
        
        # Update rect position from float position
        self.rect.x = round(self._pos_x)
        self.rect.y = round(self._pos_y)
        
        # Pattern change logic
        now = pygame.time.get_ticks()
        if now - self.last_pattern_change > self.pattern_change_delay:
            self.last_pattern_change = now
            self.pattern_index = (self.pattern_index + 1) % len(self.patterns)
            self.current_pattern = self.patterns[self.pattern_index]
        
        # Call animation update but not movement (we handle movement manually)
        AnimatedSprite.update(self)
        
        # Check if sprite is off-screen
        if self.rect.right < 0:
            self.kill()
            logger.debug(f"Enemy killed - moved off screen")
            return
        
        # Shooting logic based on current pattern
        now = pygame.time.get_ticks()
        if now - self.last_shot_time > ENEMY_SHOOTER_COOLDOWN_MS * 1.2:
            self.last_shot_time = now
            if self.current_pattern == "fan":
                self._fire_fan_pattern()
            elif self.current_pattern == "alternating":
                self._fire_alternating_pattern()
    
    def _fire_fan_pattern(self) -> None:
        """Fire wave bullets in a fan pattern."""
        if not self.player_ref:
            return
        
        # Fire 3 wave bullets in different directions
        for i in range(-1, 2):
            bullet = WaveBullet((self.rect.centerx, self.rect.centery + i * 15), -1, self.bullet_group)
            
            # Offset the wave phase for visual effect
            bullet.distance_traveled = i * bullet.wave_frequency * math.pi
        
        logger.debug(f"Enemy fired fan pattern wave bullets from {self.rect.center}")
    
    def _fire_alternating_pattern(self) -> None:
        """Fire alternating wave bullets above and below."""
        if not self.player_ref:
            return
        
        # Alternate between top and bottom
        offset = 20 if (pygame.time.get_ticks() // 1000) % 2 == 0 else -20
        
        # Fire a wave bullet
        bullet = WaveBullet((self.rect.centerx, self.rect.centery + offset), -1, self.bullet_group)
        
        logger.debug(f"Enemy fired alternating wave bullet from {self.rect.center}")

# Enemy Type 8: Phasing shield enemy with multiple attack modes
class EnemyType8(Enemy):
    """Enemy with phasing shield that alternates between spiral and explosive projectiles."""
    
    def __init__(self, player_ref, bullet_group, *groups) -> None:
        super().__init__(*groups)
        
        self.player_ref = player_ref
        self.bullet_group = bullet_group
        self.last_shot_time = pygame.time.get_ticks()
        
        # Shield parameters
        self.has_shield = True
        self.shield_health = 3  # Hit count before shield deactivates
        self.shield_recharge_delay = 4000  # ms until shield recharges
        self.last_shield_hit = 0
        self.shield_color = (0, 200, 255)  # Cyan shield
        self.shield_alpha = 180  # Semi-transparent
        
        # Attack mode parameters
        self.attack_modes = ["spiral", "explosive"]
        self.current_mode_index = 0
        self.current_mode = self.attack_modes[0]
        self.mode_change_delay = 3500  # ms between mode changes
        self.last_mode_change = pygame.time.get_ticks()
        
        # Movement pattern
        self.direction_x = -1  # Start moving left
        self.direction_y = random.choice([-1, 1])  # Random initial vertical direction
        self.direction_change_delay = 1500  # ms between direction changes
        self.last_direction_change = pygame.time.get_ticks()
        
        # Load frames
        self.frames = load_sprite_sheet(
            filename="enemy8.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=ENEMY1_SCALE_FACTOR,
            alignment='right'
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
        
        # Set movement speed
        self.set_speed(ENEMY1_SPEED_X * 0.8 * self.direction_x, 
                       ENEMY1_SPEED_X * 0.5 * self.direction_y)
        
        # Create shield surface
        self.shield_image = None
        self._update_shield()

    def _update_shield(self):
        """Update the shield visual based on current state."""
        if not self.has_shield:
            self.shield_image = None
            return
        
        # Create a transparent surface slightly larger than the sprite
        shield_size = (self.rect.width + 20, self.rect.height + 20)
        self.shield_image = pygame.Surface(shield_size, pygame.SRCALPHA)
        
        # Draw the shield as a transparent ellipse
        shield_color = (*self.shield_color, self.shield_alpha)
        pygame.draw.ellipse(
            self.shield_image,
            shield_color,
            (0, 0, shield_size[0], shield_size[1]),
            3  # Line width
        )

    def update(self) -> None:
        # Shield recharge logic
        now = pygame.time.get_ticks()
        if not self.has_shield and now - self.last_shield_hit > self.shield_recharge_delay:
            self.has_shield = True
            self.shield_health = 3
            self._update_shield()
            logger.debug(f"Enemy shield recharged")
        
        # Direction change logic
        if now - self.last_direction_change > self.direction_change_delay:
            self.last_direction_change = now
            # Reverse vertical direction
            self.direction_y *= -1
            self.speed_y = ENEMY1_SPEED_X * 0.5 * self.direction_y
        
        # Attack mode change logic
        if now - self.last_mode_change > self.mode_change_delay:
            self.last_mode_change = now
            self.current_mode_index = (self.current_mode_index + 1) % len(self.attack_modes)
            self.current_mode = self.attack_modes[self.current_mode_index]
        
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
        
        # Shooting logic based on current mode
        if now - self.last_shot_time > ENEMY_SHOOTER_COOLDOWN_MS:
            self.last_shot_time = now
            if self.current_mode == "spiral":
                self._fire_spiral_projectiles()
            elif self.current_mode == "explosive":
                self._fire_explosive_projectiles()
    
    def hit(self):
        """Handle being hit by player projectile. Returns True if damaged, False if shielded."""
        if self.has_shield:
            self.shield_health -= 1
            if self.shield_health <= 0:
                self.has_shield = False
                self.last_shield_hit = pygame.time.get_ticks()
                self._update_shield()
                logger.debug(f"Enemy shield depleted")
            return False
        return True
    
    def draw(self, surface):
        """Override draw to add shield."""
        # Draw the sprite
        surface.blit(self.image, self.rect)
        
        # Draw the shield if active
        if self.has_shield and self.shield_image:
            shield_rect = self.shield_image.get_rect(center=self.rect.center)
            surface.blit(self.shield_image, shield_rect)
    
    def _fire_spiral_projectiles(self) -> None:
        """Fire spiral projectiles in a pattern."""
        if not self.player_ref:
            return
        
        # Fire 2 spiral projectiles at different angles
        for angle in range(0, 360, 180):  # 2 bullets in opposite directions
            bullet = SpiralBullet(self.rect.center, angle, self.bullet_group)
        
        logger.debug(f"Enemy fired spiral bullets from {self.rect.center}")
    
    def _fire_explosive_projectiles(self) -> None:
        """Fire explosive projectiles."""
        if not self.player_ref:
            return
        
        # Create an explosive bullet
        bullet = ExplosiveBullet(self.rect.center, self.bullet_group)
        
        logger.debug(f"Enemy fired explosive bullet from {self.rect.center}")

# Add more enemy classes as needed (e.g., Charger, Shooter, Boss)
