"""Drone implementation for the Drone powerup."""

import math
import random
from typing import Optional, Tuple

import pygame

from src.logger import get_logger
from src.projectile import Bullet

logger = get_logger(__name__)

# Core drone parameters
DRONE_SIZE = (25, 16)
DRONE_ORBIT_RADIUS = 70
DRONE_ORBIT_SPEED = 0.03
DRONE_SHOOT_DELAY = 80
DRONE_SHOOT_RANGE = 800


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
        self.all_groups = [all_sprites_group] + list(groups)
        super().__init__(all_sprites_group, *groups)

        # Core references
        self.player = player
        self.enemies_group = enemies_group
        self.bullets_group = bullets_group
        self.all_sprites_group = all_sprites_group

        # Orbit parameters
        self.orbit_speed = DRONE_ORBIT_SPEED
        self.orbit_radius = DRONE_ORBIT_RADIUS
        self.orbit_wobble = 0
        self.wobble_direction = 1
        self.orbit_angle = random.uniform(0, math.pi * 2)

        # Sprite setup
        self.original_image = self._create_drone_surface()
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=self._calculate_orbit_position())
        self.mask = pygame.mask.from_surface(self.image)

        # Combat state
        self.last_shot_time = pygame.time.get_ticks()
        self.target_enemy = None
        self.shooting_cooldown = DRONE_SHOOT_DELAY

        logger.info(f"Drone created at {self.rect.center}")

    def _create_drone_surface(self) -> pygame.Surface:
        """Create the drone surface with visual effects."""
        surface = pygame.Surface((DRONE_SIZE[0] + 10, DRONE_SIZE[1] + 10), pygame.SRCALPHA)
        center = (surface.get_width() // 2, surface.get_height() // 2)
        
        # Glow effect
        glow_radius = max(DRONE_SIZE) // 1.5
        for radius in range(int(glow_radius), 0, -2):
            alpha = 100 - (radius * 80 // int(glow_radius))
            pygame.draw.circle(surface, (100, 180, 255, alpha), center, radius)
        
        # Main body
        body_points = [
            (center[0] + DRONE_SIZE[0]//2 - 2, center[1]),
            (center[0] - DRONE_SIZE[0]//2, center[1] - DRONE_SIZE[1]//2 + 2),
            (center[0] - DRONE_SIZE[0]//2, center[1] + DRONE_SIZE[1]//2 - 2),
        ]
        pygame.draw.polygon(surface, (220, 220, 230), body_points)
        
        # Detail lines
        pygame.draw.line(
            surface, (180, 180, 190),
            (center[0] - DRONE_SIZE[0]//4, center[1] - DRONE_SIZE[1]//4),
            (center[0] + DRONE_SIZE[0]//4, center[1])
        )
        pygame.draw.line(
            surface, (180, 180, 190),
            (center[0] - DRONE_SIZE[0]//4, center[1] + DRONE_SIZE[1]//4),
            (center[0] + DRONE_SIZE[0]//4, center[1])
        )
        
        # Engine glow
        engine_points = [
            (center[0] - DRONE_SIZE[0]//2, center[1] - DRONE_SIZE[1]//3),
            (center[0] - DRONE_SIZE[0]//2, center[1] + DRONE_SIZE[1]//3),
            (center[0] - DRONE_SIZE[0], center[1]),
        ]
        pygame.draw.polygon(surface, (80, 180, 255, 230), engine_points)
        
        # Weapon indicators
        pygame.draw.circle(surface, (255, 50, 50), 
                         (center[0] + DRONE_SIZE[0]//2 - 4, center[1]), 3)
        pygame.draw.circle(surface, (255, 100, 100),
                         (center[0] + DRONE_SIZE[0]//4, center[1] - DRONE_SIZE[1]//3), 2)
        pygame.draw.circle(surface, (255, 100, 100),
                         (center[0] + DRONE_SIZE[0]//4, center[1] + DRONE_SIZE[1]//3), 2)
        
        return surface

    def _calculate_orbit_position(self) -> Tuple[int, int]:
        """Calculate the drone's position based on orbit around player."""
        wobble_amount = math.sin(self.orbit_wobble) * 10
        current_radius = self.orbit_radius + wobble_amount
        
        offset_x = math.cos(self.orbit_angle) * current_radius
        offset_y = math.sin(self.orbit_angle) * current_radius
        
        player_x, player_y = self.player.rect.center
        return (int(player_x + offset_x), int(player_y + offset_y))

    def _find_target(self) -> Optional[pygame.sprite.Sprite]:
        """Find the nearest targetable enemy within range."""
        if not self.enemies_group:
            return None

        player_x, player_y = self.player.rect.center
        nearest_enemy = None
        nearest_distance = float('inf')

        for enemy in self.enemies_group:
            if enemy.rect.right < 0:
                continue
                
            distance = math.hypot(
                enemy.rect.centerx - player_x,
                enemy.rect.centery - player_y
            )
            
            if distance < DRONE_SHOOT_RANGE and distance < nearest_distance:
                nearest_enemy = enemy
                nearest_distance = distance
                
        return nearest_enemy

    def _shoot_at_target(self, target) -> None:
        """Fire a bullet at the specified target."""
        if not target or not target.alive():
            return
            
        bullet = Bullet(self.rect.centerx, self.rect.centery, 
                       self.bullets_group, self.all_sprites_group)
        
        dx = target.rect.centerx - self.rect.centerx
        dy = target.rect.centery - self.rect.centery
        
        distance = math.hypot(dx, dy)
        if distance > 0:
            dx, dy = dx / distance, dy / distance
            base_velocity = bullet.velocity_x * 1.3
            bullet.velocity_x = dx * base_velocity
            bullet.velocity_y = dy * base_velocity
            
            angle = math.degrees(math.atan2(-dy, dx))
            bullet.image = pygame.transform.rotate(bullet.image, angle)
            
            bullet.rect = bullet.image.get_rect(center=bullet.rect.center)
            bullet.mask = pygame.mask.from_surface(bullet.image)
            
        logger.debug(f"Drone fired at enemy at {target.rect.center}")

    def _shoot_forward(self) -> None:
        """Fire a bullet in the drone's current direction."""
        bullet = Bullet(self.rect.centerx, self.rect.centery, 
                       self.bullets_group, self.all_sprites_group)
        
        movement_angle = (self.orbit_angle + math.pi/2) % (math.pi * 2)
        base_velocity = bullet.velocity_x * 1.3
        
        bullet.velocity_x = math.cos(movement_angle) * base_velocity
        bullet.velocity_y = math.sin(movement_angle) * base_velocity
        
        angle = math.degrees(math.atan2(-bullet.velocity_y, bullet.velocity_x))
        bullet.image = pygame.transform.rotate(bullet.image, angle)
        
        bullet.rect = bullet.image.get_rect(center=bullet.rect.center)
        bullet.mask = pygame.mask.from_surface(bullet.image)
        
        logger.debug(f"Drone fired in direction {angle} degrees")

    def update(self) -> None:
        """Update the drone's position and behavior."""
        current_time = pygame.time.get_ticks()
        
        # Update orbit
        self.orbit_angle = (self.orbit_angle + self.orbit_speed) % (math.pi * 2)
        self.orbit_wobble += 0.1 * self.wobble_direction
        if abs(self.orbit_wobble) > 1.0:
            self.wobble_direction *= -1
            
        # Update position and rotation
        self.rect.center = self._calculate_orbit_position()
        movement_angle = (self.orbit_angle + math.pi/2) % (math.pi * 2)
        self.image = pygame.transform.rotate(self.original_image, -math.degrees(movement_angle))
        self.rect = self.image.get_rect(center=self.rect.center)
        self.mask = pygame.mask.from_surface(self.image)
        
        # Handle combat
        if not self.target_enemy or not self.target_enemy.alive():
            self.target_enemy = self._find_target()
            
        if current_time - self.last_shot_time > self.shooting_cooldown:
            if self.target_enemy:
                self._shoot_at_target(self.target_enemy)
            else:
                self._shoot_forward()
            self.last_shot_time = current_time

    def kill(self) -> None:
        """Remove the drone from all sprite groups."""
        logger.info(f"Drone at {self.rect.center} being removed")
        for group in self.all_groups:
            group.remove(self)
        super().kill() 