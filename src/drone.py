"""Drone implementation for the Drone powerup."""

import math
import random
from typing import Optional, Tuple

import pygame

from src.logger import get_logger
from src.projectile import Bullet

# Get a logger for this module
logger = get_logger(__name__)

# Constants for drone behavior
DRONE_ORBIT_RADIUS = 70  # Increased orbit radius for visibility
DRONE_ORBIT_SPEED = 0.03  # Speed of orbit rotation (radians per update)
DRONE_SHOOT_DELAY = 80  # Drastically reduced from 200 to 80 ms for near-continuous firing
DRONE_SHOOT_RANGE = 800  # Increased range to cover more of the screen
DRONE_SIZE = (25, 16)  # Increased size from (15, 10) to (25, 16)


class Drone(pygame.sprite.Sprite):
    """A drone that orbits the player and shoots at nearby enemies."""

    def __init__(
        self,
        player,
        enemies_group: pygame.sprite.Group,
        bullets_group: pygame.sprite.Group,
        all_sprites_group: pygame.sprite.Group,
        *groups
    ) -> None:
        """Initialize a drone.

        Args:
            player: The player sprite this drone orbits around
            enemies_group: Group containing enemy sprites to target
            bullets_group: Group to add bullets to
            all_sprites_group: Group for all sprites
            groups: Additional groups to add to
        """
        # Store the groups for later removal
        self.all_groups = [all_sprites_group] + list(groups)
        
        super().__init__(all_sprites_group, *groups)

        # Store references
        self.player = player
        self.enemies_group = enemies_group
        self.bullets_group = bullets_group
        self.all_sprites_group = all_sprites_group

        # Initialize orbit parameters first to avoid attribute errors
        self.orbit_speed = DRONE_ORBIT_SPEED
        self.orbit_radius = DRONE_ORBIT_RADIUS
        self.orbit_wobble = 0
        self.wobble_direction = 1
        self.orbit_angle = random.uniform(0, math.pi * 2)  # Random starting angle

        # Create a simple drone sprite
        self.original_image = self._create_drone_surface()
        self.image = self.original_image.copy()

        # Set initial position relative to player
        initial_pos = self._calculate_orbit_position()
        self.rect = self.image.get_rect(center=initial_pos)
        self.mask = pygame.mask.from_surface(self.image)

        # Shooting state
        self.last_shot_time = pygame.time.get_ticks()
        self.target_enemy = None
        self.shooting_cooldown = DRONE_SHOOT_DELAY
        
        # Particle trail timer
        self.particle_timer = 0

        logger.info(f"Drone created at {initial_pos}")

    def _create_drone_surface(self) -> pygame.Surface:
        """Create the drone surface with a nice visual effect."""
        # Create a surface for the drone with alpha channel
        surface = pygame.Surface((DRONE_SIZE[0] + 10, DRONE_SIZE[1] + 10), pygame.SRCALPHA)  # Add padding for glow
        
        # Draw a glow effect around the drone
        glow_radius = max(DRONE_SIZE) // 1.5
        glow_center = (surface.get_width() // 2, surface.get_height() // 2)
        for radius in range(int(glow_radius), 0, -2):
            alpha = 100 - (radius * 80 // int(glow_radius))
            pygame.draw.circle(
                surface,
                (100, 180, 255, alpha),  # Light blue glow
                glow_center,
                radius
            )
        
        # Draw the main body (light gray triangle with metallic effect)
        body_center = (surface.get_width() // 2, surface.get_height() // 2)
        body_points = [
            (body_center[0] + DRONE_SIZE[0]//2 - 2, body_center[1]),  # Nose
            (body_center[0] - DRONE_SIZE[0]//2, body_center[1] - DRONE_SIZE[1]//2 + 2),  # Top left
            (body_center[0] - DRONE_SIZE[0]//2, body_center[1] + DRONE_SIZE[1]//2 - 2),  # Bottom left
        ]
        pygame.draw.polygon(surface, (220, 220, 230), body_points)  # Lighter gray
        
        # Add detail lines to the body for texture
        pygame.draw.line(
            surface,
            (180, 180, 190),
            (body_center[0] - DRONE_SIZE[0]//4, body_center[1] - DRONE_SIZE[1]//4),
            (body_center[0] + DRONE_SIZE[0]//4, body_center[1])
        )
        pygame.draw.line(
            surface,
            (180, 180, 190),
            (body_center[0] - DRONE_SIZE[0]//4, body_center[1] + DRONE_SIZE[1]//4),
            (body_center[0] + DRONE_SIZE[0]//4, body_center[1])
        )
        
        # Add blue engine glow at the back (brighter and larger)
        engine_center = (body_center[0] - DRONE_SIZE[0]//2, body_center[1])
        engine_points = [
            (engine_center[0], engine_center[1] - DRONE_SIZE[1]//3),  # Top
            (engine_center[0], engine_center[1] + DRONE_SIZE[1]//3),  # Bottom
            (engine_center[0] - DRONE_SIZE[0]//2.5, engine_center[1]),  # Tip
        ]
        pygame.draw.polygon(surface, (80, 180, 255, 230), engine_points)  # Brighter blue glow
        
        # Add multiple weapon indicators (red dots) to show it's well-armed
        # Main weapon
        pygame.draw.circle(
            surface, 
            (255, 50, 50),  # Red
            (body_center[0] + DRONE_SIZE[0]//2 - 4, body_center[1]), 
            3  # Larger dot
        )
        # Secondary weapons
        pygame.draw.circle(
            surface, 
            (255, 100, 100),  # Lighter red
            (body_center[0] + DRONE_SIZE[0]//4, body_center[1] - DRONE_SIZE[1]//3), 
            2
        )
        pygame.draw.circle(
            surface, 
            (255, 100, 100),  # Lighter red
            (body_center[0] + DRONE_SIZE[0]//4, body_center[1] + DRONE_SIZE[1]//3), 
            2
        )
        
        return surface

    def _calculate_orbit_position(self) -> Tuple[int, int]:
        """Calculate the drone's position based on orbit around player."""
        # Add a small wobble to the orbit radius
        # Add a check to handle the case where orbit_wobble might not be initialized yet
        wobble_amount = math.sin(getattr(self, 'orbit_wobble', 0)) * 10
        current_radius = self.orbit_radius + wobble_amount
        
        # Calculate position on the orbit circle
        offset_x = math.cos(self.orbit_angle) * current_radius
        offset_y = math.sin(self.orbit_angle) * current_radius
        
        # Get player position
        player_x, player_y = self.player.rect.center
        
        return (int(player_x + offset_x), int(player_y + offset_y))

    def _find_target(self) -> Optional[pygame.sprite.Sprite]:
        """Find the nearest targetable enemy."""
        if not self.enemies_group:
            return None

        player_x, player_y = self.player.rect.center
        nearest_enemy = None
        nearest_distance = float('inf')

        for enemy in self.enemies_group:
            # Skip if the enemy is not visible on screen
            if enemy.rect.right < 0:
                continue
                
            # Calculate distance to enemy
            distance = math.hypot(
                enemy.rect.centerx - player_x,
                enemy.rect.centery - player_y
            )
            
            # Check if in range and closer than current nearest
            if distance < DRONE_SHOOT_RANGE and distance < nearest_distance:
                nearest_enemy = enemy
                nearest_distance = distance
                
        return nearest_enemy

    def _shoot_at_target(self, target) -> None:
        """Fire a bullet at the target enemy."""
        if not target or not target.alive():
            return
            
        # Create a bullet at the drone's position
        bullet = Bullet(self.rect.centerx, self.rect.centery, self.bullets_group, self.all_sprites_group)
        
        # Calculate direction to target
        target_x, target_y = target.rect.center
        dx = target_x - self.rect.centerx
        dy = target_y - self.rect.centery
        
        # Normalize direction
        distance = math.hypot(dx, dy)
        if distance > 0:
            dx /= distance
            dy /= distance
            
            # Set bullet velocity toward target with increased speed (1.3x faster)
            base_velocity = bullet.velocity_x * 1.3
            bullet.velocity_x = dx * base_velocity
            bullet.velocity_y = dy * base_velocity
            
            # Rotate bullet image to match direction
            angle = math.degrees(math.atan2(-dy, dx))
            bullet.image = pygame.transform.rotate(bullet.image, angle)
            
            # Update bullet rect and mask after rotation
            old_center = bullet.rect.center
            bullet.rect = bullet.image.get_rect(center=old_center)
            bullet.mask = pygame.mask.from_surface(bullet.image)
            
        logger.debug(f"Drone fired at enemy at {target.rect.center}")

    def update(self) -> None:
        """Update the drone's position and behavior."""
        current_time = pygame.time.get_ticks()
        
        # Update orbit position
        self.orbit_angle += self.orbit_speed
        if self.orbit_angle > math.pi * 2:
            self.orbit_angle -= math.pi * 2
            
        # Update wobble
        self.orbit_wobble += 0.1 * self.wobble_direction
        if abs(self.orbit_wobble) > 1.0:
            self.wobble_direction *= -1
            
        # Calculate new position
        new_pos = self._calculate_orbit_position()
        self.rect.center = new_pos
        
        # Find and track a target
        if not self.target_enemy or not self.target_enemy.alive():
            self.target_enemy = self._find_target()
            
        # Check if it's time to shoot
        if current_time - self.last_shot_time > self.shooting_cooldown:
            # If we have a target, shoot at it
            if self.target_enemy:
                self._shoot_at_target(self.target_enemy)
            # Otherwise shoot forward in the direction the drone is facing
            else:
                self._shoot_forward()
            self.last_shot_time = current_time
            
        # Rotate the drone to face its direction of movement
        movement_angle = (self.orbit_angle + math.pi/2) % (math.pi * 2)
        rotation_angle = math.degrees(movement_angle)
        self.image = pygame.transform.rotate(self.original_image, -rotation_angle)
        
        # Ensure the rect stays centered at the calculated position
        old_center = self.rect.center
        self.rect = self.image.get_rect(center=old_center)
        self.mask = pygame.mask.from_surface(self.image)
        
    def _shoot_forward(self) -> None:
        """Fire a bullet in the direction the drone is facing."""
        # Create a bullet at the drone's position
        bullet = Bullet(self.rect.centerx, self.rect.centery, self.bullets_group, self.all_sprites_group)
        
        # Calculate direction based on drone rotation
        movement_angle = (self.orbit_angle + math.pi/2) % (math.pi * 2)
        
        # Set bullet velocity in the direction the drone is facing
        base_velocity = bullet.velocity_x * 1.3
        bullet.velocity_x = math.cos(movement_angle) * base_velocity
        bullet.velocity_y = math.sin(movement_angle) * base_velocity
        
        # Rotate bullet image to match direction
        angle = math.degrees(math.atan2(-bullet.velocity_y, bullet.velocity_x))
        bullet.image = pygame.transform.rotate(bullet.image, angle)
        
        # Update bullet rect and mask after rotation
        old_center = bullet.rect.center
        bullet.rect = bullet.image.get_rect(center=old_center)
        bullet.mask = pygame.mask.from_surface(bullet.image)
        
        logger.debug(f"Drone fired in direction {angle} degrees")

    def kill(self) -> None:
        """Override the kill method to ensure removal from all groups."""
        # Log the removal
        logger.info(f"Drone at {self.rect.center} being removed")
        
        # Make sure we're removed from all groups
        for group in self.all_groups:
            if self in group:
                group.remove(self)
        
        # Call the parent kill method
        super().kill() 