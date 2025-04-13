"""Particle system for visual effects like explosions."""

import math
import random
from typing import List, Optional, Tuple

import pygame

from src.logger import get_logger

# Get a logger for this module
logger = get_logger(__name__)


class Particle(pygame.sprite.Sprite):
    """Individual particle for visual effects."""

    def __init__(
        self,
        position: Tuple[float, float],
        velocity: Tuple[float, float],
        color: Tuple[int, int, int],
        size: int,
        lifetime: int,
        gravity: float = 0.0,
        decay: float = 0.97,
        *groups
    ) -> None:
        """Initialize a single particle.

        Args:
            position: The (x, y) starting position of the particle
            velocity: The (vx, vy) initial velocity of the particle
            color: The (r, g, b) color of the particle
            size: The radius of the particle in pixels
            lifetime: How long the particle should exist in frames
            gravity: Optional downward acceleration
            decay: How quickly the particle velocity decays (0.97 = 3% slower each frame)
            *groups: Sprite groups to add this particle to
        """
        super().__init__(*groups)

        # Create particle surface with glow effect
        self.size = size
        self.original_size = size

        # Create a larger surface to accommodate the glow
        glow_size = size * 2
        self.image = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)

        # Draw main particle
        pygame.draw.circle(self.image, color, (glow_size, glow_size), size)

        # Draw simple glow
        glow_color = tuple(min(255, c + 70) for c in color)
        pygame.draw.circle(self.image, (*glow_color, 120), (glow_size, glow_size), int(size * 1.5))

        # Position and rect
        self.rect = self.image.get_rect(center=position)
        self.pos = list(position)  # Exact floating point position

        # Movement
        self.velocity = list(velocity)
        self.gravity = gravity
        self.decay = decay

        # Lifetime tracking
        self.lifetime = lifetime
        self.age = 0

        # Color transition
        self.color = color
        self.end_color = self._choose_end_color(color)

        # Alpha handling
        self.alpha = 255

    def _choose_end_color(self, start_color: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Choose simpler end color for transition."""
        if random.random() < 0.4:
            return (255, 0, 0)  # Red
        elif random.random() < 0.7:
            return (0, 0, 0)  # Black
        else:
            return start_color  # Keep original color

    def update(self) -> None:
        """Update the particle position, appearance and lifetime."""
        # Update age
        self.age += 1
        if self.age >= self.lifetime:
            self.kill()
            return

        # Apply physics
        self.velocity[0] *= self.decay
        self.velocity[1] *= self.decay
        self.velocity[1] += self.gravity

        # Update position
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
        self.rect.center = (int(self.pos[0]), int(self.pos[1]))

        # Update appearance only occasionally to improve performance
        if self.age % 5 == 0 or self.age == 1:
            # Calculate life factor (1.0 at start, 0.0 at end)
            life_factor = 1 - (self.age / self.lifetime)

            # Fade out alpha
            self.alpha = int(255 * life_factor)
            self.image.set_alpha(self.alpha)

            # Transition color only on certain frames
            if self.age % 10 == 0:
                current_color = tuple(
                    int(c * life_factor + e * (1 - life_factor))
                    for c, e in zip(self.color, self.end_color)
                )

                # Get center and size
                center = self.rect.center

                # Recreate image with new color
                glow_size = self.size * 2
                self.image = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)

                # Draw main particle
                pygame.draw.circle(self.image, current_color, (glow_size, glow_size), self.size)

                # Add simplified glow
                glow_color = tuple(min(255, c + 70) for c in current_color)
                pygame.draw.circle(
                    self.image, (*glow_color, 120), (glow_size, glow_size), int(self.size * 1.5)
                )

                # Restore position
                self.rect = self.image.get_rect(center=center)

                # Apply alpha
                self.image.set_alpha(self.alpha)


class FlameParticle(pygame.sprite.Sprite):
    """Particle effect for flamethrower weapon."""

    def __init__(
        self,
        position: Tuple[float, float],
        velocity: Tuple[float, float],
        color: Tuple[int, int, int],
        size: int,
        lifetime: int,
        damage: int = 5,
        *groups
    ) -> None:
        """Initialize a new flame particle.

        Args:
            position: Starting position (x, y)
            velocity: Initial velocity (vx, vy)
            color: RGB color tuple
            size: Particle size in pixels
            lifetime: How many frames the particle lives
            damage: How much damage the particle does on hit
            groups: Sprite groups to add to
        """
        super().__init__(*groups)
        self.pos_x, self.pos_y = position
        self.vel_x, self.vel_y = velocity
        self.base_color = color
        self.size = size
        self.initial_size = size
        self.lifetime = lifetime
        self.age = 0
        self.damage = damage
        
        # Vertical drift parameters for "spray" effect
        self.drift_direction = random.choice([-1, 1])  # Up or down
        self.drift_amount = random.uniform(0.02, 0.05)  # Subtle drift
        self.drift_cycle = random.uniform(0, math.pi*2)  # Random start phase
        
        # Create the initial flame particle image
        self._create_flame_image()
        
        # Setup collision rect
        self.rect = self.image.get_rect(center=(int(self.pos_x), int(self.pos_y)))
        
        # Set up a mask for better collision detection
        self.mask = pygame.mask.from_surface(self.image)
        
    def _create_flame_image(self):
        """Create a flame particle with realistic fire colors and glow."""
        # Create larger surface to accommodate glow
        glow_size = self.size * 3
        total_size = glow_size * 2
        
        self.image = pygame.Surface((total_size, total_size), pygame.SRCALPHA)
        center = (total_size // 2, total_size // 2)
        
        # Base fire colors (from center to edge)
        colors = [
            (255, 255, 220),  # White-yellow (core)
            (255, 200, 50),   # Yellow
            (255, 130, 0),    # Orange
            self.base_color,  # Base color (usually red)
            (80, 0, 0)        # Dark red (edge)
        ]
        
        # Life factor affects appearance (new particles are brighter)
        life_factor = 1 - (self.age / self.lifetime)
        
        # Draw flame layers from outside in
        for i, color in enumerate(reversed(colors)):
            radius = int(self.size * (1 - i/len(colors)) * 2)
            alpha = int(200 * life_factor) if i < len(colors)-1 else int(100 * life_factor)
            pygame.draw.circle(
                self.image,
                (*color, alpha),
                center,
                radius
            )
            
        # Add some random flicker/sparks
        if random.random() < 0.4:
            spark_pos = (
                center[0] + random.randint(-int(self.size/2), int(self.size/2)),
                center[1] + random.randint(-int(self.size/2), int(self.size/2))
            )
            spark_size = max(2, int(self.size / 4 * life_factor))
            pygame.draw.circle(
                self.image,
                (255, 255, 200, 200),  # Bright yellow spark
                spark_pos,
                spark_size
            )

    def update(self) -> None:
        """Update the flame particle position, appearance and lifetime."""
        # Update age
        self.age += 1
        if self.age >= self.lifetime:
            self.kill()
            return
        
        # Apply "spray" drift - oscillating vertical movement
        self.drift_cycle += 0.1
        vertical_drift = math.sin(self.drift_cycle) * self.drift_amount * self.drift_direction
        self.vel_y += vertical_drift
        
        # Slightly slow down over time for more natural look
        slowdown_factor = 0.98
        self.vel_x *= slowdown_factor
        
        # Update position
        self.pos_x += self.vel_x
        self.pos_y += self.vel_y
        self.rect.center = (int(self.pos_x), int(self.pos_y))
        
        # Update appearance every few frames for performance
        if self.age % 3 == 0:
            life_factor = 1 - (self.age / self.lifetime)
            
            # Gradually decrease size as flame burns out
            new_size = max(2, int(self.initial_size * (0.8 + 0.2 * life_factor)))
            if new_size != self.size:
                self.size = new_size
                
            # Update flame appearance
            self._create_flame_image()
            
            # Keep the same center position
            old_center = self.rect.center
            self.rect = self.image.get_rect(center=old_center)
            
            # Update mask for accurate collision detection
            self.mask = pygame.mask.from_surface(self.image)


class ParticleSystem:
    """Manages groups of particles for effects like explosions."""

    @staticmethod
    def create_explosion(
        position: Tuple[float, float],
        count: int,
        size_range: Tuple[int, int],
        color_ranges: List[Tuple[int, int, int, int, int, int]],
        speed_range: Tuple[float, float],
        lifetime_range: Tuple[int, int],
        gravity: float = 0.1,
        group: Optional[pygame.sprite.Group] = None,
    ) -> List[Particle]:
        """Create a burst of particles for an explosion effect.

        Args:
            position: Center position of the explosion
            count: Number of particles to create
            size_range: (min_size, max_size) for particles
            color_ranges: List of (min_r, max_r, min_g, max_g, min_b, max_b) for random colors
            speed_range: (min_speed, max_speed) for particle velocity
            lifetime_range: (min_frames, max_frames) for particle lifetime
            gravity: Downward acceleration to apply to particles
            group: Optional sprite group to add particles to

        Returns:
            List of created particles
        """
        particles = []

        for _ in range(count):
            # Random angle for direction - full 360 degrees
            angle = random.uniform(0, 2 * math.pi)

            # Higher base speed for longer travel
            speed = random.uniform(*speed_range) * 1.5

            # Calculate velocity components
            vel_x = math.cos(angle) * speed
            vel_y = math.sin(angle) * speed

            # Random size - larger than before
            size = random.randint(*size_range) * 2

            # Random color from ranges
            color_range = random.choice(color_ranges)
            color = (
                random.randint(color_range[0], color_range[1]),  # Red
                random.randint(color_range[2], color_range[3]),  # Green
                random.randint(color_range[4], color_range[5]),  # Blue
            )

            # Random lifetime - longer to travel further
            lifetime = random.randint(*lifetime_range) * 1.2

            # Create particle
            particle = Particle(
                position, (vel_x, vel_y), color, size, int(lifetime), gravity, 0.97, group
            )
            particles.append(particle)

        return particles
