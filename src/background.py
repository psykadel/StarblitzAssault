"""Manages background layers for parallax scrolling."""

import pygame
import os
import sys
from typing import TYPE_CHECKING, Tuple, List, Dict, Optional
import random

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

class BackgroundDecorations:
    """Manages decorative elements that appear in the background with parallax effect."""
    
    def __init__(self, decoration_paths: List[str], scroll_speed: float, screen_width: int, 
                 screen_height: int, playfield_top: int, playfield_bottom: int, 
                 decoration_count: int = 20):
        """Initialize the background decorations layer.
        
        Args:
            decoration_paths: List of paths to decoration image files.
            scroll_speed: Horizontal scrolling speed (pixels per frame).
            screen_width: Width of the game screen.
            screen_height: Height of the game screen.
            playfield_top: Top boundary of playfield.
            playfield_bottom: Bottom boundary of playfield.
            decoration_count: Number of decorations to display.
        """
        self.decorations = []
        self.screen_width = screen_width
        self.scroll_speed = scroll_speed
        
        # Playable area boundaries
        self.playfield_top = playfield_top
        self.playfield_bottom = playfield_bottom
        
        # Load all decoration images
        self.decoration_images = []
        for path in decoration_paths:
            try:
                # Load image with alpha channel
                img = pygame.image.load(path).convert_alpha()
                
                # Make the decorations bigger (increase size)
                max_size = 180  # Increased maximum size
                width, height = img.get_size()
                if width > 0 and height > 0:  # Avoid division by zero
                    # Scale up smaller images to be larger
                    min_size = 120  # Increased minimum size
                    if width < min_size and height < min_size:
                        scale_factor = min_size / max(width, height)
                        new_size = (int(width * scale_factor), int(height * scale_factor))
                        img = pygame.transform.scale(img, new_size)
                    # Scale down larger images if needed
                    width, height = img.get_size()  # Get new dimensions after possible resizing
                    if width > max_size or height > max_size:
                        scale_factor = max_size / max(width, height)
                        new_size = (int(width * scale_factor), int(height * scale_factor))
                        img = pygame.transform.scale(img, new_size)
                
                # Make the decorations dimmer by reducing alpha
                # Create a copy of the image with reduced alpha
                img_with_alpha = img.copy()
                # Increase alpha to 60 (slightly more visible but still subtle)
                alpha_value = 60  # 0-255, where 0 is transparent and 255 is opaque
                img_with_alpha.fill((255, 255, 255, alpha_value), None, pygame.BLEND_RGBA_MULT)
                
                self.decoration_images.append(img_with_alpha)
            except (pygame.error, FileNotFoundError) as e:
                print(f"Error loading decoration image: {path} - {e}")
        
        # Only proceed if we have loaded images
        if self.decoration_images:
            # Create random decorations
            self._create_random_decorations(decoration_count)
        else:
            print("No decoration images loaded.")
    
    def _create_random_decorations(self, count: int) -> None:
        """Create a set of randomly positioned decorations.
        
        Args:
            count: Number of decorations to create.
        """
        # Clear any existing decorations
        self.decorations = []
        
        # Playable area height
        playable_height = self.playfield_bottom - self.playfield_top
        
        # Minimum spacing between decorations (to prevent overlaps)
        min_spacing = 250  # Significant distance between decorations
        
        # Create decorations with well-spaced positions
        # Divide screen into sections
        section_width = (self.screen_width + 800) // count
        
        for i in range(count):
            # Choose a random image
            img = random.choice(self.decoration_images)
            img_width, img_height = img.get_size()
            
            # Position in a specific section with padding to avoid edges
            padding = 30
            # Each decoration gets its own section with randomness within that section
            section_start = i * section_width
            x = random.randint(section_start, section_start + section_width - img_width)
            
            # Ensure proper initial x distribution (some on screen, some off-screen right)
            if i < count // 2:
                # Place half on screen
                x = random.randint(-20, self.screen_width - img_width)
            else:
                # Place half off-screen to the right
                x = random.randint(self.screen_width, self.screen_width + 800)
            
            # Random y position with padding from playfield boundaries
            y = random.randint(self.playfield_top + padding, 
                              self.playfield_bottom - img_height - padding)
            
            # Add to decorations list
            self.decorations.append({
                "image": img,
                "pos": [float(x), float(y)],  # Use float for smooth movement
                "width": img_width,
                "height": img_height
            })
    
    def update(self) -> None:
        """Update the positions of all decorations."""
        for decoration in self.decorations:
            # Move decoration based on scroll speed
            decoration["pos"][0] -= self.scroll_speed
            
            # If decoration goes off-screen left, move it back to the right
            if decoration["pos"][0] < -decoration["width"]:
                # Find the rightmost decoration
                rightmost_x = self.screen_width
                rightmost_decoration = None
                for d in self.decorations:
                    if d != decoration and d["pos"][0] > rightmost_x:
                        rightmost_x = d["pos"][0] + d["width"]
                        rightmost_decoration = d
                
                # Reset position to right of all other decorations with increased spacing
                min_spacing = 600  # Increased spacing significantly
                new_x = max(rightmost_x + min_spacing, self.screen_width + 300)
                decoration["pos"][0] = new_x
                
                # Randomize vertical position too
                decoration["pos"][1] = random.randint(
                    self.playfield_top + 30, 
                    self.playfield_bottom - decoration["height"] - 30
                )
                
                # Choose a new image that is different from current and rightmost decoration
                if self.decoration_images and len(self.decoration_images) > 1:
                    current_img = decoration["image"]
                    rightmost_img = rightmost_decoration["image"] if rightmost_decoration else None
                    
                    # Get images that are different from current and rightmost
                    available_images = [img for img in self.decoration_images 
                                       if img != current_img and img != rightmost_img]
                    
                    # If we have alternatives, choose one
                    if available_images:
                        new_img = random.choice(available_images)
                        decoration["image"] = new_img
                        decoration["width"] = new_img.get_width()
                        decoration["height"] = new_img.get_height()
    
    def draw(self, surface: pygame.Surface) -> None:
        """Draw all decorations onto the given surface.
        
        Args:
            surface: The pygame surface to draw on.
        """
        for decoration in self.decorations:
            # Convert float position to integers for blitting
            pos = (int(decoration["pos"][0]), int(decoration["pos"][1]))
            surface.blit(decoration["image"], pos) 