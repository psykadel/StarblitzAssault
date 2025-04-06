"""Manages background layers for parallax scrolling."""

import pygame
import os
import sys
from typing import TYPE_CHECKING, Tuple, List, Dict, Optional

from config.game_config import SCREEN_WIDTH

if TYPE_CHECKING:
    from src.config import SCREEN_WIDTH

class BackgroundLayer:
    """Represents a single horizontally scrolling background layer."""

    def __init__(self, image_path: str, scroll_speed: float, screen_height: int, initial_scroll: float = 0.0):
        """Initializes the background layer.

        Args:
            image_path: Path to the background image file.
            scroll_speed: Horizontal speed of the layer (pixels per frame).
                          Positive values scroll left-to-right (image moves left).
            screen_height: The height of the game screen for scaling.
            initial_scroll: The starting horizontal scroll offset.
        """
        try:
            # Load and potentially scale image to screen height while maintaining aspect ratio
            self.original_image = pygame.image.load(image_path).convert_alpha()
            img_w, img_h = self.original_image.get_size()
            scale = screen_height / img_h
            scaled_w = int(img_w * scale)
            self.image = pygame.transform.scale(self.original_image, (scaled_w, screen_height))
        except (pygame.error, FileNotFoundError, ZeroDivisionError) as e: # Specific exceptions
            print(f"Error loading background image: {image_path} - {e}")
            # Create a fallback surface
            self.image = pygame.Surface((100, screen_height)).convert()
            self.image.fill((50, 50, 50)) # Dark grey fallback

        self.rect = self.image.get_rect()
        self.scroll_speed = scroll_speed
        self.image_width = self.image.get_width()
        # Ensure initial scroll wraps correctly if it's larger than width
        self.scroll = initial_scroll % self.image_width

    def update(self) -> None:
        """Updates the scroll position of the layer."""
        self.scroll += self.scroll_speed
        # Reset scroll to prevent large numbers and maintain seamless tiling
        if abs(self.scroll) > self.image_width:
            self.scroll %= self.image_width

    def draw(self, surface: pygame.Surface) -> None:
        """Draws the tiled background layer onto the given surface."""
        screen_width = surface.get_width()

        # Calculate the integer scroll position for blitting
        int_scroll = int(self.scroll)

        # Draw the image multiple times to cover the screen
        # Start by drawing the part of the image determined by the scroll
        surface.blit(self.image, (-int_scroll, 0))

        # If the first image doesn't cover the screen, draw another one to its right
        if -int_scroll + self.image_width < screen_width:
            surface.blit(self.image, (-int_scroll + self.image_width, 0))

        # If the scrolled image starts off-screen to the left, draw one before it
        if -int_scroll > 0:
            surface.blit(self.image, (-int_scroll - self.image_width, 0)) 