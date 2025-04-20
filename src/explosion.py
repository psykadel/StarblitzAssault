"""Explosion effect for ship destruction."""

import random
from typing import List, Literal, Optional, Tuple

import pygame

from src.animated_sprite import AnimatedSprite
from src.logger import get_logger
from src.particle import Particle, ParticleSystem

# Get a logger for this module
logger = get_logger(__name__)


class Explosion(AnimatedSprite):
    """Animated explosion effect that removes itself after playing once."""

    def __init__(
        self,
        position: Tuple[int, int],
        size: Tuple[int, int],
        explosion_type: Literal["enemy", "player"] = "enemy",
        *groups,
        particles_group: Optional[pygame.sprite.Group] = None,
    ) -> None:
        """Initialize an explosion effect at the given position.

        Args:
            position: The center position (x, y) for the explosion
            size: The size (width, height) of the explosion
            explosion_type: Type of explosion - "enemy" or "player" for different effects
            *groups: Sprite groups to add this explosion to
            particles_group: Optional group to add particles to (separate from explosion)
        """
        # Filter out None values from groups
        valid_groups = [g for g in groups if g is not None]
        
        # Use a faster animation speed for explosion
        super().__init__(80, *valid_groups)

        # Create an explosion animation with growing circles
        self.frames = self._create_explosion_frames(size)

        # Set initial image
        self.frame_index = 0
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect(center=position)

        # Keep track of whether the animation has completed
        self.animation_complete = False

        # Store all particles created for this explosion
        self.particles = []

        # Store particles group reference
        self.particles_group = particles_group

        # Create particles based on explosion type
        if explosion_type == "enemy":
            self._create_enemy_explosion_particles(position)
        else:  # player explosion
            self._create_player_explosion_particles(position)

    def _create_enemy_explosion_particles(self, position: Tuple[int, int]) -> None:
        """Create particles for enemy explosion."""
        # Bright, fiery colors for enemy explosions
        color_ranges = [
            (200, 255, 100, 200, 0, 100),  # Yellow-orange range
            (200, 255, 0, 100, 0, 50),  # Red-orange range
            (255, 255, 200, 255, 0, 50),  # Bright yellow range
            (150, 255, 150, 255, 150, 255),  # White-yellow range
        ]

        # Create a burst of particles - fewer but bigger
        self.particles = ParticleSystem.create_explosion(
            position=position,
            count=15,
            size_range=(3, 8),
            color_ranges=color_ranges,
            speed_range=(2.0, 5.0),
            lifetime_range=(25, 45),
            gravity=0.03,
            group=self.particles_group,
        )

        logger.debug(f"Created {len(self.particles)} particles for enemy explosion")

    def _create_player_explosion_particles(self, position: Tuple[int, int]) -> None:
        """Create particles for player explosion - more dramatic!"""
        # Main explosion particles - vibrant colors
        color_ranges = [
            (200, 255, 200, 255, 0, 100),  # Yellow-white range
            (200, 255, 0, 100, 0, 50),  # Red-orange range
            (150, 255, 150, 255, 150, 255),  # White range
            (0, 100, 100, 255, 200, 255),  # Blue range (special)
        ]

        # Initial burst - fewer but bigger particles
        initial_burst = ParticleSystem.create_explosion(
            position=position,
            count=25,
            size_range=(5, 14),
            color_ranges=color_ranges,
            speed_range=(3.0, 7.0),
            lifetime_range=(35, 65),
            gravity=0.02,
            group=self.particles_group,
        )

        self.particles.extend(initial_burst)

        # Add one delayed secondary explosion
        # Random offset from center for secondary explosion
        offset_x = random.randint(-20, 20)
        offset_y = random.randint(-20, 20)
        secondary_pos = (position[0] + offset_x, position[1] + offset_y)

        secondary = ParticleSystem.create_explosion(
            position=secondary_pos,
            count=10,
            size_range=(4, 12),
            color_ranges=color_ranges,
            speed_range=(2.0, 5.0),
            lifetime_range=(25, 55),
            gravity=0.03,
            group=self.particles_group,
        )

        self.particles.extend(secondary)

        logger.debug(f"Created {len(self.particles)} particles for player explosion")

    def _create_explosion_frames(self, size: Tuple[int, int]) -> List[pygame.Surface]:
        """Create explosion animation frames.

        Args:
            size: The maximum size of the explosion

        Returns:
            List of surfaces with the explosion animation frames
        """
        frames = []
        num_frames = 10
        max_width, max_height = size

        colors = [
            (255, 255, 200),  # Bright yellow
            (255, 165, 0),  # Orange
            (255, 69, 0),  # Red-orange
            (255, 0, 0),  # Red
            (139, 0, 0),  # Dark red
        ]

        # Create frames with increasing size
        for i in range(num_frames):
            # Calculate size as a percentage of max
            scale = (i + 1) / num_frames
            width = int(max_width * scale)
            height = int(max_height * scale)

            # Add some randomness to the explosion shape
            frame = pygame.Surface((width, height), pygame.SRCALPHA)

            # Choose a color based on frame index
            color_idx = min(i // 2, len(colors) - 1)
            color = colors[color_idx]

            # Draw explosion shape - center circle with some random particles
            radius = min(width, height) // 2
            center = (width // 2, height // 2)

            # Main explosion circle
            pygame.draw.circle(frame, color, center, radius)

            # Add some random particles for a more dynamic effect
            for _ in range(10):
                particle_radius = random.randint(2, max(3, radius // 4))
                x_offset = random.randint(-radius, radius)
                y_offset = random.randint(-radius, radius)

                # Only draw if within circle bounds
                if x_offset * x_offset + y_offset * y_offset <= radius * radius:
                    particle_pos = (center[0] + x_offset, center[1] + y_offset)
                    pygame.draw.circle(frame, (255, 255, 255), particle_pos, particle_radius)

            frames.append(frame)

        return frames

    def update(self) -> None:
        """Update the explosion animation, kill when complete."""
        # If animation is already complete, no need to update
        if self.animation_complete:
            return

        # Current frame index before animating
        previous_index = self.frame_index

        # Call parent update for animation
        super().update()

        # If we've looped back to the beginning, we're done
        if self.frame_index < previous_index:
            self.kill()
            self.animation_complete = True
            logger.debug("Explosion animation complete")
