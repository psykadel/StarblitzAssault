"""Manages background layers for parallax scrolling."""

import pygame
import os
import sys
from typing import TYPE_CHECKING, Tuple, List, Dict, Optional
import random
import math

from src.logger import get_logger
from config.config import (
    DECORATION_COUNT,
    DECORATION_ALPHA,
    DECORATION_MIN_SIZE,
    DECORATION_MAX_SIZE,
    DECORATION_MIN_SPACING,
    DECORATION_MAX_SPACING,
    DECORATION_RESPAWN_MIN_SPACING,
    DECORATION_RESPAWN_MAX_SPACING
)

class BackgroundLayer:
    """Represents a single horizontally scrolling background layer."""

    def __init__(self, image_path: str, scroll_speed: float, screen_height: int, initial_scroll: float = 0.0, vertical_offset: int = 0):
        """Initializes the background layer.

        Args:
            image_path: Path to the background image file.
            scroll_speed: Horizontal speed of the layer (pixels per frame).
                          Positive values scroll left-to-right (image moves left).
            screen_height: The height of the game screen for scaling.
            initial_scroll: The starting horizontal scroll offset.
            vertical_offset: The vertical offset for the layer (positive moves down, negative moves up).
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
        # Store vertical offset
        self.vertical_offset = vertical_offset

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
        # Apply vertical offset to all blit operations
        
        # Calculate how many tiles we need to cover the screen width
        needed_tiles = math.ceil(screen_width / self.image_width) + 2  # Add extra for smooth scrolling
        
        # Draw multiple instances of the image to ensure smooth scrolling
        for i in range(-1, needed_tiles):
            tile_position = (-int_scroll + i * self.image_width, self.vertical_offset)
            surface.blit(self.image, tile_position)
            
        # This approach ensures that tiles are always scrolling in smoothly from the right
        # rather than suddenly appearing at the edge of the screen

class BackgroundDecorations:
    """Manages decorative elements that appear in the background with parallax effect."""
    
    def __init__(self, decoration_paths: List[str], scroll_speed: float, screen_width: int, 
                 screen_height: int, playfield_top: int, playfield_bottom: int, 
                 decoration_count: int = DECORATION_COUNT):
        """Initialize the background decorations layer.
        
        Args:
            decoration_paths: List of paths to decoration image files.
            scroll_speed: Horizontal scrolling speed (pixels per frame).
            screen_width: Width of the game screen.
            screen_height: Height of the game screen.
            playfield_top: Top boundary of playfield.
            playfield_bottom: Bottom boundary of playfield.
            decoration_count: Number of decorations to display, defaults to DECORATION_COUNT.
        """
        self.decorations = []
        self.screen_width = screen_width
        self.scroll_speed = scroll_speed
        
        # Playable area boundaries
        self.playfield_top = playfield_top
        self.playfield_bottom = playfield_bottom
        
        # Track last used images to avoid repetition
        self.last_used_images = {}
        
        # Load all decoration images
        self.decoration_images = []
        for path in decoration_paths:
            try:
                # Load image with alpha channel
                img = pygame.image.load(path).convert_alpha()
                
                # Make the decorations bigger (increase size)
                max_size = DECORATION_MAX_SIZE
                width, height = img.get_size()
                if width > 0 and height > 0:  # Avoid division by zero
                    # Scale up smaller images to be larger
                    min_size = DECORATION_MIN_SIZE
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
                # Set alpha according to the constant
                alpha_value = DECORATION_ALPHA  # Use constant value for transparency
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
        
        # Use spacing constants from config
        min_spacing = DECORATION_MIN_SPACING
        max_spacing = DECORATION_MAX_SPACING
        
        # Create decorations with well-spaced positions
        # Calculate spacing dynamically based on screen width and decoration count with randomization
        total_width = self.screen_width + 800  # Include area off screen to the right
        
        # Start position for first decoration (slightly off-screen to the left)
        current_x = -100
        
        # Track previous y position and image to ensure variety
        prev_y = None
        prev_img = None
        
        # Define y sections to ensure good vertical distribution
        y_section_height = playable_height / 4  # Divide playfield into 4 sections
        
        for i in range(count):
            # Choose a random image that's different from the previous one
            if prev_img is not None and len(self.decoration_images) > 1:
                available_images = [img for img in self.decoration_images if img != prev_img]
                img = random.choice(available_images)
            else:
                img = random.choice(self.decoration_images)
            
            prev_img = img  # Track this image as the previous one for next iteration
            img_width, img_height = img.get_size()
            
            # Position with padding to avoid edges
            padding = 30
            
            # Ensure proper initial x distribution
            if i < count // 2:
                # Place first half on screen with proper spacing
                random_spacing = random.randint(min_spacing, max_spacing)
                if i > 0:  # Add spacing after first decoration
                    current_x += random_spacing
                x = current_x
                current_x = x + img_width
            else:
                # Place second half off-screen to the right with proper spacing
                if i == count // 2:  # Reset position for first off-screen decoration
                    current_x = self.screen_width + 100
                else:
                    # Add spacing between off-screen decorations
                    random_spacing = random.randint(min_spacing, max_spacing)
                    current_x += random_spacing
                x = current_x
                current_x = x + img_width
            
            # Choose a section for this decoration to ensure good vertical distribution
            # Each decoration is placed in a different section than its neighbors when possible
            if prev_y is None:
                # First decoration - choose any section
                section = random.randint(0, 3)
            else:
                # Avoid placing in the same section as the previous decoration
                prev_section = int((prev_y - self.playfield_top) / y_section_height)
                available_sections = [s for s in range(4) if s != prev_section]
                section = random.choice(available_sections)
            
            # Random y position within the chosen section with padding
            section_top = self.playfield_top + section * y_section_height
            section_bottom = section_top + y_section_height
            
            # Adjust for padding and image height
            y_min = max(section_top, self.playfield_top + padding)
            y_max = min(section_bottom, self.playfield_bottom - img_height - padding)
            
            # Ensure y_max is greater than y_min
            if y_max <= y_min:
                y_max = y_min + 1
                
            # Convert to int for random.randint
            y = random.randint(int(y_min), int(y_max))
            prev_y = y  # Track this y position for next iteration
            
            # Add to decorations list
            self.decorations.append({
                "image": img,
                "pos": [float(x), float(y)],  # Use float for smooth movement
                "width": img_width,
                "height": img_height,
                "last_y": y  # Store the initial y position
            })
    
    def update(self) -> None:
        """Update the positions of all decorations."""
        # Store all current y positions to ensure vertical variation
        current_y_positions = [d["pos"][1] for d in self.decorations]
        
        for i, decoration in enumerate(self.decorations):
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
                
                # Reset position to right of all other decorations with randomized spacing
                min_spacing = DECORATION_RESPAWN_MIN_SPACING
                max_spacing = DECORATION_RESPAWN_MAX_SPACING
                spacing = random.randint(min_spacing, max_spacing)
                new_x = max(rightmost_x + spacing, self.screen_width + 300)
                decoration["pos"][0] = new_x
                
                # Get the last y position for this decoration
                last_y = decoration["last_y"]
                
                # Divide playfield into sections for better vertical distribution
                playable_height = self.playfield_bottom - self.playfield_top
                section_height = playable_height / 4
                
                # Determine which section the last position was in
                last_section = int((last_y - self.playfield_top) / section_height)
                
                # Choose a different section for the new position
                available_sections = [s for s in range(4) if s != last_section]
                new_section = random.choice(available_sections)
                
                # Calculate y range for the chosen section
                section_top = self.playfield_top + new_section * section_height
                section_bottom = section_top + section_height
                
                # Apply padding and account for decoration height
                padding = 30
                y_min = max(section_top + padding, self.playfield_top + padding)
                y_max = min(section_bottom - padding, self.playfield_bottom - decoration["height"] - padding)
                
                # Ensure y_max is greater than y_min
                if y_max <= y_min:
                    y_max = y_min + 1
                
                # Set new y position - convert to int for random.randint
                new_y = random.randint(int(y_min), int(y_max))
                decoration["pos"][1] = new_y
                decoration["last_y"] = new_y  # Update the stored y position
                
                # Choose a new image that is different from current image and nearby decorations
                if self.decoration_images and len(self.decoration_images) > 1:
                    current_img = decoration["image"]
                    
                    # Get images of nearby decorations (both left and right if possible)
                    nearby_images = []
                    
                    # Find decorations that are visibly nearby (within 1.5 screen widths)
                    for d in self.decorations:
                        if d != decoration:
                            # Check if decoration is within visible range
                            x_distance = abs(d["pos"][0] - new_x)
                            if x_distance < self.screen_width * 1.5:
                                nearby_images.append(d["image"])
                    
                    # Add rightmost decoration's image if it exists
                    if rightmost_decoration:
                        nearby_images.append(rightmost_decoration["image"])
                    
                    # Get images that are different from current and nearby
                    available_images = [img for img in self.decoration_images 
                                       if img != current_img and img not in nearby_images]
                    
                    # If we have alternatives, choose one; otherwise pick any that's different from current
                    if available_images:
                        new_img = random.choice(available_images)
                    else:
                        # Fall back to just avoiding the current image
                        other_images = [img for img in self.decoration_images if img != current_img]
                        if other_images:
                            new_img = random.choice(other_images)
                        else:
                            # Very unlikely case: only one decoration image available
                            new_img = random.choice(self.decoration_images)
                    
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