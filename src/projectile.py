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

        # Position the bullet based on player's position - ensure ints for rect
        self.rect.left = int(left)
        self.rect.centery = int(center_y)

        # Set horizontal speed
        self.speed_x: float = 10 # Move rightwards

    def update(self) -> None:
        """Moves the bullet horizontally and removes it if off-screen."""
        # Ensure integer position updates
        new_x = self.rect.x + self.speed_x
        self.rect.x = int(new_x)
        
        # Remove bullet if its RIGHT edge goes off the right edge of the screen
        if self.rect.left > SCREEN_WIDTH:
            self.kill() # Removes sprite from all groups 

class EnemyProjectile(pygame.sprite.Sprite):
    """Represents a projectile fired by enemies."""
    def __init__(self, right: float, center_y: float, speed_x: float = -7.0) -> None:
        """
        Initializes the enemy projectile sprite.
        
        Args:
            right: Right edge position (where the projectile starts)
            center_y: Vertical center position
            speed_x: Horizontal speed (negative for leftward movement)
        """
        super().__init__()

        # Visual representation - red enemy projectile
        self.image = pygame.Surface([8, 3])
        self.image.fill((255, 60, 60))  # Red projectile
        self.rect = self.image.get_rect()

        # Position the projectile based on enemy's position
        self.rect.right = int(right)
        self.rect.centery = int(center_y)

        # Set horizontal speed (negative to move leftward)
        self.speed_x: float = speed_x

    def update(self) -> None:
        """Moves the projectile horizontally and removes it if off-screen."""
        # Update position with float-to-int conversion
        new_x = self.rect.x + self.speed_x
        self.rect.x = int(new_x)
        
        # Remove projectile if it goes off the left edge of the screen
        if self.rect.right < 0:
            self.kill()  # Removes sprite from all groups 