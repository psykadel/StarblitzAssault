"""Particle system for visual effects like explosions."""

import pygame
import random
import math
from typing import Tuple, List, Optional

from src.logger import get_logger

# Get a logger for this module
logger = get_logger(__name__)

class Particle(pygame.sprite.Sprite):
    """Individual particle for visual effects."""
    
    def __init__(self, position: Tuple[float, float], velocity: Tuple[float, float], 
                 color: Tuple[int, int, int], size: int, lifetime: int, 
                 gravity: float = 0.0, decay: float = 0.97, *groups) -> None:
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
            return (0, 0, 0)    # Black
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
                pygame.draw.circle(self.image, (*glow_color, 120), (glow_size, glow_size), int(self.size * 1.5))
                
                # Restore position
                self.rect = self.image.get_rect(center=center)
                
                # Apply alpha
                self.image.set_alpha(self.alpha)

class ParticleSystem:
    """Manages groups of particles for effects like explosions."""
    
    @staticmethod
    def create_explosion(position: Tuple[float, float], count: int, size_range: Tuple[int, int],
                       color_ranges: List[Tuple[int, int, int, int, int, int]],
                       speed_range: Tuple[float, float], lifetime_range: Tuple[int, int],
                       gravity: float = 0.1, group: Optional[pygame.sprite.Group] = None) -> List[Particle]:
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
                random.randint(color_range[4], color_range[5])   # Blue
            )
            
            # Random lifetime - longer to travel further
            lifetime = random.randint(*lifetime_range) * 1.2
            
            # Create particle
            particle = Particle(position, (vel_x, vel_y), color, size, int(lifetime), gravity, 0.97, group)
            particles.append(particle)
            
        return particles 