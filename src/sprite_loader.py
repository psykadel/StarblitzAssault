"""Utility for loading sprite sheets."""

import pygame
import os
import math
from typing import List, Optional, Tuple, Dict, Any
import sys

from src.logger import get_logger
from config.game_config import DEFAULT_SPRITE_SHEET_GRID

# Get a logger for this module
logger = get_logger(__name__)

# Default crop border in pixels, to remove edges between sprites
DEFAULT_CROP_BORDER_PIXELS = 2

def load_sprite_sheet(filename: str,
                     sprite_dir: str,
                     scale_factor: float = 1.0,
                     grid_size: Tuple[int, int] = DEFAULT_SPRITE_SHEET_GRID,
                     crop_border: int = DEFAULT_CROP_BORDER_PIXELS) -> List[pygame.Surface]:
    """Load all sprites from a sprite sheet.
    
    Args:
        filename: Name of the sprite sheet file
        sprite_dir: Directory containing the sprite sheet
        scale_factor: Scale factor for the sprites (1.0 = original size)
        grid_size: Grid dimensions (cols, rows) of the sprite sheet
        crop_border: Number of pixels to crop from each edge of each sprite
        
    Returns:
        List of pygame Surfaces containing each sprite image
    
    Raises:
        FileNotFoundError: If the sprite sheet file is not found
        pygame.error: If there is an error loading the image
    """
    # Build the full path to the sprite sheet
    sprite_sheet_path = os.path.join(sprite_dir, filename)
    
    # Check if file exists before trying to load
    if not os.path.exists(sprite_sheet_path):
        error_msg = f"Sprite sheet not found: {sprite_sheet_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    try:
        # Load the sprite sheet with alpha channel support
        sprite_sheet = pygame.image.load(sprite_sheet_path).convert_alpha()
        logger.info(f"Loaded sprite sheet: {filename} ({sprite_sheet.get_width()}x{sprite_sheet.get_height()})")
        
        # Get dimensions of the sprite sheet
        sheet_width = sprite_sheet.get_width()
        sheet_height = sprite_sheet.get_height()
        
        # Calculate individual sprite dimensions
        cols, rows = grid_size
        sprite_width = sheet_width // cols
        sprite_height = sheet_height // rows
        
        logger.info(f"Sprite sheet dimensions: {sheet_width}x{sheet_height}")
        logger.info(f"Individual sprite dimensions: {sprite_width}x{sprite_height}")
        logger.info(f"Grid size: {cols}x{rows}")
        
        # List to store all extracted sprites
        sprites = []
        
        # Extract each sprite based on grid position with smart content detection
        for row in range(rows):
            for col in range(cols):
                # Calculate top-left corner position of the grid cell
                x = col * sprite_width
                y = row * sprite_height
                
                # Extract the full grid cell first (without cropping)
                full_cell = pygame.Surface((sprite_width, sprite_height), pygame.SRCALPHA)
                full_cell.blit(sprite_sheet, (0, 0), (x, y, sprite_width, sprite_height))
                
                # Find the actual sprite bounds within the cell (non-transparent pixels)
                bounds = find_sprite_bounds(full_cell)
                
                if bounds:
                    # We found actual content, use these bounds with a small padding
                    padding = 2  # Add a small padding around the detected sprite
                    x_min, y_min, x_max, y_max = bounds
                    
                    # Apply padding but ensure we stay within the cell
                    x_min = max(0, x_min - padding)
                    y_min = max(0, y_min - padding)
                    x_max = min(sprite_width, x_max + padding)
                    y_max = min(sprite_height, y_max + padding)
                    
                    # Create the actual sprite surface from the detected bounds
                    sprite_width_content = x_max - x_min
                    sprite_height_content = y_max - y_min
                    
                    # Make sure we have valid dimensions
                    if sprite_width_content <= 0 or sprite_height_content <= 0:
                        # Fallback to default cropping
                        rect = pygame.Rect(
                            x + crop_border,
                            y + crop_border,
                            sprite_width - (2 * crop_border),
                            sprite_height - (2 * crop_border)
                        )
                    else:
                        # Use smart detected bounds
                        rect = pygame.Rect(
                            x + x_min,
                            y + y_min,
                            sprite_width_content,
                            sprite_height_content
                        )
                else:
                    # No content found, use default crop
                    rect = pygame.Rect(
                        x + crop_border,
                        y + crop_border,
                        sprite_width - (2 * crop_border),
                        sprite_height - (2 * crop_border)
                    )
                
                # Extract the sprite using the rect
                sprite = pygame.Surface(rect.size, pygame.SRCALPHA)
                sprite.blit(sprite_sheet, (0, 0), rect)
                
                # Scale if needed
                if scale_factor != 1.0:
                    new_width = int(rect.width * scale_factor)
                    new_height = int(rect.height * scale_factor)
                    sprite = pygame.transform.scale(sprite, (new_width, new_height))
                
                sprites.append(sprite)
                logger.debug(f"Extracted sprite from {filename} at position ({rect.x}, {rect.y}), size ({rect.width}, {rect.height})")
        
        logger.info(f"Extracted {len(sprites)} sprites from {filename}")
        return sprites
    except pygame.error as e:
        error_msg = f"Error loading sprite sheet: {sprite_sheet_path} - {str(e)}"
        logger.error(error_msg)
        print(error_msg)
        raise 

def find_sprite_bounds(surface: pygame.Surface) -> Optional[Tuple[int, int, int, int]]:
    """Find the bounding box of non-transparent pixels in a surface.
    
    Args:
        surface: The surface to analyze
        
    Returns:
        Tuple of (x_min, y_min, x_max, y_max) or None if no content found
    """
    width, height = surface.get_size()
    
    # Initialize bounds to their extreme opposite values
    x_min = width
    y_min = height
    x_max = 0
    y_max = 0
    
    # Track if we found any non-transparent pixels
    found_content = False
    
    # For powerups and orbs, pay special attention to the center area first
    center_x = width // 2
    center_y = height // 2
    
    # Search in expanding circles from the center
    radius_max = int(math.sqrt(width**2 + height**2) / 2)  # Maximum possible radius
    
    # Search outward from center first to prioritize central content
    for radius in range(1, radius_max, 2):
        # Search in a circular pattern
        for angle in range(0, 360, 10):  # 10-degree steps for efficiency
            rad = math.radians(angle)
            x = int(center_x + radius * math.cos(rad))
            y = int(center_y + radius * math.sin(rad))
            
            # Skip if out of bounds
            if x < 0 or y < 0 or x >= width or y >= height:
                continue
                
            # Check if this pixel is non-transparent
            if surface.get_at((x, y))[3] > 0:  # Alpha > 0
                found_content = True
                x_min = min(x_min, x)
                y_min = min(y_min, y)
                x_max = max(x_max, x + 1)  # +1 because max is exclusive
                y_max = max(y_max, y + 1)  # +1 because max is exclusive
    
    # If we didn't find content with the circular search, do a full scan
    if not found_content:
        # Scan all pixels
        for x in range(width):
            for y in range(height):
                if surface.get_at((x, y))[3] > 0:  # Alpha > 0
                    found_content = True
                    x_min = min(x_min, x)
                    y_min = min(y_min, y)
                    x_max = max(x_max, x + 1)  # +1 because max is exclusive
                    y_max = max(y_max, y + 1)  # +1 because max is exclusive
    
    if found_content:
        # Slight adjustment for orbs to shift them down a bit (since orbs tend to be too high)
        # This is specifically for orb-like powerups
        
        # Check if the sprite is taller than it is wide (common for orbs with glow effects)
        height_diff = (y_max - y_min) - (x_max - x_min)
        if height_diff > 0 and height_diff > (y_max - y_min) * 0.2:  # If significantly taller than wide
            # Shift the sprite down by adjusting the y bounds slightly (10% of height)
            shift_amount = int((y_max - y_min) * 0.1)
            y_min = min(height - (y_max - y_min), y_min + shift_amount)
            y_max = min(height, y_max + shift_amount)
        
        return (x_min, y_min, x_max, y_max)
    else:
        # No content found
        return None 