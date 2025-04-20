"""Particle effects for the power bar."""

import math
import random
from typing import Optional, Tuple

import pygame

from src.logger import get_logger
from src.particle import Particle

# Get a logger for this module
logger = get_logger(__name__)


class PowerParticle(Particle):
    """Specialized particle for power bar effects."""

    def __init__(
        self,
        position: Tuple[float, float],
        velocity: Tuple[float, float],
        color: Tuple[int, int, int],
        size: int,
        lifetime: int,
        gravity: float = 0.0,
        *groups,
    ) -> None:
        """Initialize a power particle with enhanced glow effect."""
        super().__init__(position, velocity, color, size, lifetime, gravity, *groups)

        # Create power particle surface with stronger glow
        self.size = size
        self.original_size = size

        # Create a larger surface to accommodate the stronger glow
        glow_size = size * 3
        self.image = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)

        # Draw main particle
        pygame.draw.circle(self.image, color, (glow_size, glow_size), size)

        # Draw enhanced glow with multiple layers
        glow_color1 = tuple(min(255, c + 50) for c in color)
        glow_color2 = tuple(min(255, c + 100) for c in color)

        # Inner glow (stronger)
        pygame.draw.circle(self.image, (*glow_color2, 150), (glow_size, glow_size), int(size * 1.7))
        # Outer glow (softer)
        pygame.draw.circle(self.image, (*glow_color1, 80), (glow_size, glow_size), int(size * 2.5))

        # Position and rect
        self.rect = self.image.get_rect(center=position)
        self.pos = list(position)  # Exact floating point position


class PowerParticleSystem:
    """Creates particle effects for power bar changes."""

    @staticmethod
    def create_power_change_effect(
        position: Tuple[float, float],
        color: Tuple[int, int, int],
        is_decrease: bool = False,
        group: Optional[pygame.sprite.Group] = None,
    ) -> list:
        """Create particles for power bar change.

        Args:
            position: Center position to emit particles from
            color: Base color of particles (typically matching the power bar)
            is_decrease: True if power decreased, False if increased
            group: Optional sprite group to add particles to

        Returns:
            List of created particles
        """
        particles = []

        # Parameters based on whether power increased or decreased
        if is_decrease:
            # Power decreased - more dramatic, red-tinted particles
            count = 15
            size_range = (3, 8)
            speed_range = (2.0, 5.0)
            lifetime_range = (30, 60)
            gravity = 0.02
            # Add some red tint to base color for decrease
            color = (min(255, color[0] + 80), max(0, color[1] - 40), max(0, color[2] - 40))
        else:
            # Power increased - gentler, brighter particles
            count = 10
            size_range = (2, 6)
            speed_range = (1.5, 4.0)
            lifetime_range = (25, 50)
            gravity = 0.01
            # Add some brightness for increase
            color = (min(255, color[0] + 30), min(255, color[1] + 30), min(255, color[2] + 30))

        # Create particles in an arc pattern facing upward
        for _ in range(count):
            # Constrained angle for direction - upward arc
            if is_decrease:
                # Wider arc for decrease, more explosive
                angle = random.uniform(-math.pi * 0.8, math.pi * 0.8)
            else:
                # Narrower upward arc for increase
                angle = random.uniform(-math.pi * 0.6, math.pi * 0.6)

            # Randomize speed
            speed = random.uniform(*speed_range)

            # Calculate velocity components
            vel_x = math.cos(angle) * speed
            vel_y = math.sin(angle) * speed

            # Random size
            size = random.randint(*size_range)

            # Vary color slightly
            r_var = random.randint(-20, 20)
            g_var = random.randint(-20, 20)
            b_var = random.randint(-20, 20)

            particle_color = (
                max(0, min(255, color[0] + r_var)),
                max(0, min(255, color[1] + g_var)),
                max(0, min(255, color[2] + b_var)),
            )

            # Random lifetime
            lifetime = random.randint(*lifetime_range)

            # Create particle with specialized PowerParticle
            particle = PowerParticle(
                position, (vel_x, vel_y), particle_color, size, lifetime, gravity, group
            )

            particles.append(particle)

        logger.debug(f"Created {len(particles)} power bar particles")
        return particles
