"""Explosion effect for ship destruction."""

import pygame
import random
from typing import Tuple, List

from src.animated_sprite import AnimatedSprite
from src.logger import get_logger

# Get a logger for this module
logger = get_logger(__name__)

class Explosion(AnimatedSprite):
    """Animated explosion effect that removes itself after playing once."""
    
    def __init__(self, position: Tuple[int, int], size: Tuple[int, int], *groups) -> None:
        """Initialize an explosion effect at the given position.
        
        Args:
            position: The center position (x, y) for the explosion
            size: The size (width, height) of the explosion
            *groups: Sprite groups to add this explosion to
        """
        # Use a faster animation speed for explosion
        super().__init__(80, *groups)
        
        # Create an explosion animation with growing circles
        self.frames = self._create_explosion_frames(size)
        
        # Set initial image
        self.frame_index = 0
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect(center=position)
        self.mask = pygame.mask.from_surface(self.image)
        
        # Keep track of whether the animation has completed
        self.animation_complete = False
        
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
            (255, 255, 200),   # Bright yellow
            (255, 165, 0),     # Orange
            (255, 69, 0),      # Red-orange
            (255, 0, 0),       # Red
            (139, 0, 0)        # Dark red
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
                if x_offset*x_offset + y_offset*y_offset <= radius*radius:
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