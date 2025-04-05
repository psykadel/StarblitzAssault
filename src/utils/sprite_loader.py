"""Utility function for loading and processing sprite sheets."""

import pygame
import os
from typing import List, Tuple

# --- Constants ---
DEFAULT_SPRITE_SHEET_GRID: Tuple[int, int] = (3, 3) # Default grid dimensions (cols, rows)
DEFAULT_CROP_BORDER_PIXELS: int = 2 # Pixels to crop from each side

# --- Function ---
def load_sprite_sheet(
    filename: str,
    sprite_dir: str,
    grid_dimensions: Tuple[int, int] = DEFAULT_SPRITE_SHEET_GRID,
    scale_factor: float = 1.0,
    crop_border: int = DEFAULT_CROP_BORDER_PIXELS,
    flip_horizontal: bool = False
) -> List[pygame.Surface]:
    """Loads a sprite sheet, parses it into frames, crops borders, scales, and optionally flips.

    Assumes the sprite sheet has a transparent background (alpha channel).

    Args:
        filename: The name of the sprite sheet file.
        sprite_dir: The directory containing the sprite sheet.
        grid_dimensions: A tuple (columns, rows) indicating the grid layout.
        scale_factor: The factor by which to scale each frame (e.g., 0.5 for half size).
        crop_border: The number of pixels to crop from *each* side (top, bottom, left, right)
                     of each frame *before* scaling. Set to 0 to disable cropping.
        flip_horizontal: If True, flips each frame horizontally.

    Returns:
        A list of pygame.Surface objects, one for each frame.

    Raises:
        SystemExit: If the file cannot be loaded, grid dimensions are invalid,
                    or no frames are extracted.
    """
    sprite_sheet_path = os.path.join(sprite_dir, filename)
    try:
        # Load the sheet and ensure it has per-pixel alpha transparency
        sprite_sheet = pygame.image.load(sprite_sheet_path).convert_alpha()
    except (pygame.error, FileNotFoundError) as e: # Specific exceptions
        print(f"Error loading sprite sheet: {sprite_sheet_path} - {e}")
        raise SystemExit(e)

    # Get dimensions
    sheet_width, sheet_height = sprite_sheet.get_size()
    cols, rows = grid_dimensions
    if cols <= 0 or rows <= 0:
        print(f"Error: Invalid grid dimensions {grid_dimensions} for {filename}")
        raise SystemExit()

    # Calculate dimensions of a single sprite cell on the sheet
    sprite_width = sheet_width // cols
    sprite_height = sheet_height // rows

    # Ensure crop amount is valid
    crop_px = max(0, crop_border) # Cannot be negative
    # Prevent cropping more than half the width/height
    crop_px = min(crop_px, sprite_width // 2, sprite_height // 2)

    # Calculate final cropped dimensions
    cropped_width = sprite_width - (2 * crop_px)
    cropped_height = sprite_height - (2 * crop_px)

    # Debug info to help diagnose crop issues
    if "main-character.png" in filename:
        print(f"Player sprite crop info - Sheet size: {sheet_width}x{sheet_height}")
        print(f"Sprite cell: {sprite_width}x{sprite_height}, Crop: {crop_px}")
        print(f"Final cropped size: {cropped_width}x{cropped_height}")

    # Check if cropping makes the dimensions invalid
    if cropped_width <= 0 or cropped_height <= 0:
        print(f"Warning: Cropping {crop_px}px results in <=0 dimension for {filename}. Disabling crop for this sheet.")
        crop_px = 0
        cropped_width = sprite_width
        cropped_height = sprite_height

    frames: List[pygame.Surface] = []

    # Iterate through the grid
    for row_idx in range(rows):
        for col_idx in range(cols):
            # Calculate the rect of the *source* sprite on the main sheet
            source_rect_on_sheet = pygame.Rect(
                col_idx * sprite_width + crop_px,      # X position (start after left crop)
                row_idx * sprite_height + crop_px,     # Y position (start after top crop)
                cropped_width,                         # Width (after left/right crop)
                cropped_height                         # Height (after top/bottom crop)
            )

            # Create a new surface for the individual frame (with transparency)
            # Size is the final cropped size before scaling
            frame_surface = pygame.Surface((cropped_width, cropped_height), pygame.SRCALPHA)

            # Blit the specific cropped area from the sprite sheet onto the new surface
            # The destination position on the new surface is (0, 0)
            frame_surface.blit(sprite_sheet, (0, 0), area=source_rect_on_sheet)

            # Scale the resulting cropped frame if needed
            if scale_factor != 1.0:
                original_size = frame_surface.get_size()
                try:
                    new_size = (max(1, int(original_size[0] * scale_factor)),
                                max(1, int(original_size[1] * scale_factor)))
                    frame_surface = pygame.transform.scale(frame_surface, new_size)
                except (ValueError, pygame.error) as e: # Specify pygame.error too
                     # Catch potential errors from scaling (e.g., too large)
                     # Break long print statement
                    print(f"Warning: Error scaling frame {len(frames)} in {filename}: "
                          f"{e}. Using unscaled cropped size.")

            # Flip the frame horizontally if requested
            if flip_horizontal:
                frame_surface = pygame.transform.flip(frame_surface, True, False)

            frames.append(frame_surface)

    # Final check if any frames were actually extracted
    if not frames:
         print(f"Error: No frames extracted from {sprite_sheet_path}")
         raise SystemExit()

    return frames
