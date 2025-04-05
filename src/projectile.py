"""Defines projectiles like the player's laser."""

import pygame
from typing import TYPE_CHECKING

# Import SCREEN_WIDTH for runtime use
from src.config import SCREEN_WIDTH

# Keep TYPE_CHECKING block empty or remove if no longer needed
if TYPE_CHECKING:
    pass # No type-checking-only imports needed currently

class Bullet(pygame.sprite.Sprite):
    """Represents a laser bullet fired by the player."""
    def __init__(self, left: float, center_y: float) -> None:
        """Initializes the bullet sprite."""
        super().__init__()

        # Simple visual representation for the laser (horizontal)
        self.image = pygame.Surface([10, 4]) # Width > Height
        self.image.fill((0, 255, 0)) # Green laser
        self.rect = self.image.get_rect()

        # Position the bullet based on player's position
        self.rect.left = left
        self.rect.centery = center_y

        # Set horizontal speed
        self.speed_x: float = 10 # Move rightwards

    def update(self) -> None:
        """Moves the bullet horizontally and removes it if off-screen."""
        self.rect.x += self.speed_x
        # Remove bullet if its RIGHT edge goes off the right edge of the screen
        if self.rect.left > SCREEN_WIDTH:
            self.kill() # Removes sprite from all groups 