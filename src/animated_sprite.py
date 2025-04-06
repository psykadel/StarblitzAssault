"""Base class for animated sprites in the game."""

import pygame
from typing import List, Optional, Tuple

class AnimatedSprite(pygame.sprite.Sprite):
    """Base class for sprites with frame-based animation."""
    
    def __init__(self, animation_speed_ms: int, *groups) -> None:
        """Initialize the animated sprite.
        
        Args:
            animation_speed_ms: Milliseconds between animation frames
            *groups: Sprite groups to add this sprite to
        """
        super().__init__(*groups)
        
        # Animation properties
        self.frames: List[pygame.Surface] = []
        self.frame_index: int = 0
        self.animation_speed_ms = animation_speed_ms
        self.last_frame_update: int = pygame.time.get_ticks()
        
        # Create placeholder image/rect until frames are loaded
        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)  # 1x1 transparent placeholder
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        
        # Movement properties
        self.speed_x: float = 0
        self.speed_y: float = 0
        
        # Track position with floats for smoother movement
        self._pos_x: float = 0
        self._pos_y: float = 0
    
    def animate(self) -> None:
        """Update the animation frame based on elapsed time."""
        if not self.frames:
            return  # Don't animate if no frames
        
        now = pygame.time.get_ticks()
        if now - self.last_frame_update > self.animation_speed_ms:
            self.last_frame_update = now
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            
            # Update image and rect (maintaining position)
            old_center = self.rect.center
            self.image = self.frames[self.frame_index]
            self.rect = self.image.get_rect(center=old_center)
            self.mask = pygame.mask.from_surface(self.image)
    
    def update(self) -> None:
        """Update the sprite (animate and move)."""
        self.animate()
        
        # Update float positions first
        self._pos_x += self.speed_x
        self._pos_y += self.speed_y
        
        # Apply to rect as integers
        self.rect.x = round(self._pos_x)
        self.rect.y = round(self._pos_y)
    
    def set_position(self, x: float, y: float) -> None:
        """Set the sprite's position.
        
        Args:
            x: The x-coordinate
            y: The y-coordinate
        """
        self._pos_x = x
        self._pos_y = y
        self.rect.x = round(x)
        self.rect.y = round(y)
    
    def set_speed(self, speed_x: float, speed_y: float) -> None:
        """Set the sprite's movement speed.
        
        Args:
            speed_x: Horizontal speed in pixels per frame
            speed_y: Vertical speed in pixels per frame
        """
        self.speed_x = speed_x
        self.speed_y = speed_y
        
    @property
    def position(self) -> Tuple[float, float]:
        """Get the current position as a tuple."""
        return (self._pos_x, self._pos_y)
        
    # Override rect properties to ensure float position is updated
    @property
    def topleft(self) -> Tuple[int, int]:
        """Get the topleft position."""
        return self.rect.topleft
        
    @topleft.setter
    def topleft(self, pos: Tuple[float, float]) -> None:
        """Set both the rect and float position."""
        x, y = pos
        self._pos_x = float(x)
        self._pos_y = float(y)
        self.rect.topleft = (round(x), round(y)) 