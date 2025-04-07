"""Utility functions for loading sprite sheets."""

import pygame
import os
import logging
from typing import List, Tuple, Optional
import math
import sys

from src.logger import get_logger
from config.config import DEFAULT_SPRITE_SHEET_GRID

# Get a logger for this module
logger = get_logger(__name__)

# Default crop border is no longer needed with mask-based detection
# DEFAULT_CROP_BORDER_PIXELS = 2

def find_sprite_bounds_and_anchor(surface: pygame.Surface) -> Optional[Tuple[pygame.Rect, Tuple[int, int]]]:
    """
    Find the bounding box of non-transparent pixels and the rightmost pixel anchor.

    Args:
        surface: The surface (representing a single grid cell) to analyze.

    Returns:
        A tuple containing:
        - pygame.Rect: The bounding box of the sprite content within the surface.
        - Tuple[int, int]: The coordinates (x, y) of the rightmost non-transparent 
                           pixel relative to the bounding box's top-left corner.
        Returns None if the surface is empty or entirely transparent.
    """
    try:
        mask = pygame.mask.from_surface(surface)
    except ValueError:
        logger.warning("Could not create mask from surface (possibly 0 size).")
        return None
        
    bounding_rects = mask.get_bounding_rects()
    if not bounding_rects:
        return None  # No content found

    # Find the largest bounding box manually to help type checker
    largest_rect = None
    max_area = -1
    for rect in bounding_rects:
        if isinstance(rect, pygame.Rect):
             area = rect.width * rect.height
             if area > max_area:
                  max_area = area
                  largest_rect = rect
        else:
             logger.warning(f"Unexpected item in bounding_rects: {type(rect)}")

    if not largest_rect:
        logger.warning("Could not find a valid Rect in mask bounding rects.")
        return None
    
    bounds_rect: pygame.Rect = largest_rect # Now we know it's a Rect
    
    # Find the rightmost pixel within the bounding box
    # Use attributes of the bounds_rect object directly
    x_min = bounds_rect.x
    y_min = bounds_rect.y
    width = bounds_rect.width
    height = bounds_rect.height
    x_max = x_min + width
    y_max = y_min + height
    
    rightmost_x_abs = -1
    rightmost_y_abs = -1
    
    found = False
    # Iterate columns from right to left within the bounds
    for x in range(x_max - 1, x_min - 1, -1):
        # Iterate rows within the bounds
        for y in range(y_min, y_max):
            if mask.get_at((x, y)):
                rightmost_x_abs = x
                rightmost_y_abs = y # Use the first y found in this rightmost column
                found = True
                break # Found the rightmost column, stop searching rows
        if found:
            break # Found the rightmost pixel, stop searching columns
            
    if not found:
         # Should not happen if get_bounding_rects found something, but safety check
         logger.warning("Mask bounding rect found, but no non-transparent pixel within?")
         return None

    # Calculate anchor relative to the bounding box top-left
    rightmost_anchor_relative = (rightmost_x_abs - x_min, rightmost_y_abs - y_min)

    return bounds_rect, rightmost_anchor_relative


def load_sprite_sheet(filename: str,
                     sprite_dir: str,
                     scale_factor: float = 1.0,
                     grid_size: Tuple[int, int] = DEFAULT_SPRITE_SHEET_GRID,
                     alignment: Optional[str] = 'right', # 'right', 'center', or None
                     align_margin: int = 5) -> List[pygame.Surface]:
    """
    Load sprites from a grid-based sheet, aligning content within each frame's canvas.

    Args:
        filename: Name of the sprite sheet file.
        sprite_dir: Directory containing the sprite sheet.
        scale_factor: Scale factor for the final sprite canvases (1.0 = original).
        grid_size: Grid dimensions (cols, rows) of the sprite sheet.
        alignment: How to align sprite content within the cell canvas:
                   - 'right': Align based on the rightmost pixel (good for animations).
                   - 'center': Center the content bounding box within the canvas.
                   - None or other: Blit content at its detected bounding box position.
                   Defaults to 'right'.
        align_margin: The target margin (pixels) used for 'right' alignment.
                            Defaults to 5.

    Returns:
        List of pygame Surfaces (canvases), each containing one aligned sprite. 
        Frames are consistently sized based on the grid cell dimensions.

    Raises:
        FileNotFoundError: If the sprite sheet file is not found.
        pygame.error: If there is an error loading the image.
    """
    sprite_sheet_path = os.path.join(sprite_dir, filename)
    if not os.path.exists(sprite_sheet_path):
        error_msg = f"Sprite sheet not found: {sprite_sheet_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    try:
        sprite_sheet = pygame.image.load(sprite_sheet_path).convert_alpha()
        logger.info(f"Loaded sprite sheet: {filename} ({sprite_sheet.get_width()}x{sprite_sheet.get_height()})")

        sheet_width, sheet_height = sprite_sheet.get_size()
        cols, rows = grid_size
        
        if cols <= 0 or rows <= 0:
             error_msg = f"Invalid grid size: {grid_size} for sprite sheet {filename}"
             logger.error(error_msg)
             raise ValueError(error_msg)

        # Calculate dimensions of a single grid cell (canvas size)
        cell_width = sheet_width // cols
        cell_height = sheet_height // rows
        
        if cell_width <= 0 or cell_height <= 0:
             error_msg = f"Calculated zero cell dimension for {filename} with grid {grid_size}"
             logger.error(error_msg)
             raise ValueError(error_msg)

        logger.info(f"Grid: {cols}x{rows}, Cell Size: {cell_width}x{cell_height}")

        aligned_sprites = []
        for row in range(rows):
            for col in range(cols):
                # Define the rectangle for the current cell on the sprite sheet
                cell_rect = pygame.Rect(col * cell_width, row * cell_height, cell_width, cell_height)
                
                # Extract the surface for the current cell
                try:
                    cell_surface = sprite_sheet.subsurface(cell_rect).copy()
                except ValueError as e:
                     logger.error(f"Error extracting cell ({col},{row}) from {filename}: {e}")
                     # Create an empty canvas as fallback for this cell
                     canvas = pygame.Surface((cell_width, cell_height), pygame.SRCALPHA)
                     aligned_sprites.append(canvas)
                     continue # Skip to next cell

                # Find sprite bounds and the rightmost anchor point within the cell
                bounds_data = find_sprite_bounds_and_anchor(cell_surface)

                # Create the final canvas for this frame (transparent)
                # Use original cell dimensions before scaling
                canvas = pygame.Surface((cell_width, cell_height), pygame.SRCALPHA)
                canvas.fill((0,0,0,0)) 

                if bounds_data:
                    content_bounds_rect, rightmost_anchor = bounds_data
                    x_min, y_min, content_width, content_height = content_bounds_rect
                    anchor_x_rel, anchor_y_rel = rightmost_anchor

                    # Extract the actual sprite content using the bounding box
                    content_sprite = cell_surface.subsurface(content_bounds_rect)

                    # Calculate blit position based on chosen alignment
                    if alignment == 'right':
                        # Calculate the target X for the rightmost anchor on the canvas
                        target_anchor_x = cell_width - align_margin
                        # Calculate blit X to align the relative anchor point with the target
                        blit_x = target_anchor_x - anchor_x_rel
                        # Vertically center the content
                        blit_y = (cell_height // 2) - (content_height // 2)
                        logger.debug(f"Cell({col},{row}): Right-aligning. AnchorRel=({anchor_x_rel},{anchor_y_rel}), TargetX={target_anchor_x}, Blit=({blit_x},{blit_y})")
                    elif alignment == 'center':
                        # Calculate blit X/Y to center the content bounding box
                        blit_x = (cell_width // 2) - (content_width // 2)
                        blit_y = (cell_height // 2) - (content_height // 2)
                        logger.debug(f"Cell({col},{row}): Center-aligning. ContentSize=({content_width},{content_height}), Blit=({blit_x},{blit_y})")
                    else: # alignment is None or unrecognized
                        # Blit content at its original position relative to the cell top-left
                        blit_x = x_min
                        blit_y = y_min
                        logger.debug(f"Cell({col},{row}): No alignment (None). Bounds=({x_min},{y_min}), Blit=({blit_x},{blit_y})")
                    
                    # Blit the extracted content onto the canvas at the calculated position
                    canvas.blit(content_sprite, (blit_x, blit_y))
                    # logger.debug(f"Aligned sprite from cell ({col},{row}) of {filename}. Anchor: {anchor_x_rel},{anchor_y_rel}. Blit Pos: {blit_x},{blit_y}") # Redundant log

                else:
                    # No content found in this cell, canvas remains transparent
                    logger.debug(f"No content found in cell ({col},{row}) of {filename}. Added empty canvas.")

                # Scale the final canvas if needed
                if scale_factor != 1.0:
                    # Ensure dimensions are positive after scaling
                    scaled_width = max(1, int(cell_width * scale_factor))
                    scaled_height = max(1, int(cell_height * scale_factor))
                    try:
                        canvas = pygame.transform.scale(canvas, (scaled_width, scaled_height))
                    except ValueError as e:
                         logger.error(f"Error scaling canvas for cell ({col},{row}) from {filename}: {e}")
                         # Use unscaled canvas as fallback
                         pass


                aligned_sprites.append(canvas)

        logger.info(f"Extracted and aligned {len(aligned_sprites)} sprites from {filename}")
        return aligned_sprites

    except pygame.error as e:
        error_msg = f"Pygame error loading/processing sprite sheet: {sprite_sheet_path} - {str(e)}"
        logger.error(error_msg)
        raise  # Re-raise the exception
    except ValueError as e: # Catch potential ValueErrors from subsurface/other issues
         error_msg = f"ValueError processing sprite sheet: {sprite_sheet_path} - {str(e)}"
         logger.error(error_msg)
         raise # Re-raise


# Example usage (can be kept for testing or removed)
if __name__ == '__main__':
    # This example needs adjustment if run directly, as assets path might be relative
    # It also doesn't demonstrate the right-alignment well without a specific sheet
    pygame.init()
    print("Running sprite_loader example...")

    # Example: Load player ship sheet (assuming it exists and needs alignment)
    try:
        # Adjust path relative to workspace root if necessary
        base_dir = os.path.dirname(os.path.dirname(__file__)) # Go up one level from src
        sprite_sheet_file = os.path.join(base_dir, 'assets', 'sprites', 'main-character.png')
        print(f"Attempting to load: {sprite_sheet_file}")
        
        # Use a scale factor if desired
        scale = 0.5 
        sprites = load_sprite_sheet(
            filename='main-character.png', 
            sprite_dir=os.path.join(base_dir, 'assets', 'sprites'), 
            grid_size=(3, 3), # Assuming 3x3 grid
            scale_factor=scale,
            alignment='right',
            align_margin=10 # Example margin
        )
        
        if sprites:
            print(f"Loaded {len(sprites)} aligned sprites.")
            # Get size from the first scaled sprite canvas
            sprite_size = sprites[0].get_size()
            screen_width = sprite_size[0] * 5 # Display a few side-by-side
            screen_height = sprite_size[1] * 2
            screen = pygame.display.set_mode((screen_width, screen_height))
            pygame.display.set_caption("Aligned Sprite Test")
            clock = pygame.time.Clock()
            index = 0
            running = True
            
            # Draw grid lines for visualization
            def draw_grid(surf, sprite_w, sprite_h, grid_cols, grid_rows):
                for i in range(1, grid_cols):
                    pygame.draw.line(surf, (100, 100, 100), (i * sprite_w, 0), (i * sprite_w, surf.get_height()))
                for i in range(1, grid_rows):
                     pygame.draw.line(surf, (100, 100, 100), (0, i * sprite_h), (surf.get_width(), i * sprite_h))

            frame_count = 0
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                
                screen.fill((30, 30, 30))
                
                # Display current frame large
                screen.blit(sprites[index], (sprite_size[0] * 2, sprite_size[1] // 2)) 
                # Draw box around it
                pygame.draw.rect(screen, (255,0,0), (sprite_size[0] * 2, sprite_size[1] // 2, sprite_size[0], sprite_size[1]), 1)

                # Draw reference line near right edge
                ref_x = sprite_size[0] * 2 + sprite_size[0] - int(10 * scale) # Aligned margin
                pygame.draw.line(screen, (0, 255, 0), (ref_x, sprite_size[1] // 2), (ref_x, sprite_size[1] // 2 + sprite_size[1]))


                pygame.display.flip()
                
                # Slow down frame rate to see animation clearly
                frame_count += 1
                if frame_count % 30 == 0: # Change sprite every 30 frames (0.5s at 60fps)
                    index = (index + 1) % len(sprites)
                    
                clock.tick(60) 
        else:
            print('No sprites loaded.')
            
    except FileNotFoundError as e:
         print(f"Error: {e}")
    except Exception as e:
         print(f"An unexpected error occurred: {e}")
         pygame.quit()
         sys.exit()

    pygame.quit()
    print("Sprite_loader example finished.") 