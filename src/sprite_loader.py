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
        
        # Extract each sprite based on grid position
        for row in range(rows):
            for col in range(cols):
                # Calculate top-left corner position
                x = col * sprite_width
                y = row * sprite_height  # Corrected from sprite_width
                
                # Create rect for extracting the sprite
                # Apply crop border to avoid edge artifacts
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
                logger.debug(f"Extracted sprite from {filename} at position ({x}, {y}), size ({rect.width}, {rect.height})")
        
        logger.info(f"Extracted {len(sprites)} sprites from {filename}")
        return sprites
    except pygame.error as e:
        error_msg = f"Error loading sprite sheet: {sprite_sheet_path} - {str(e)}"
        logger.error(error_msg)
        print(error_msg)
        raise 