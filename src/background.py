"""Manages background layers for parallax scrolling."""

import math
import random
from typing import List

import pygame

from config.config import (
    DECORATION_ALPHA,
    DECORATION_BOTTOM_PADDING,
    DECORATION_MAX_SIZE,
    DECORATION_MIN_HORIZONTAL_SPACING,
    DECORATION_MIN_SIZE,
    DECORATION_TOP_PADDING,
)

class BackgroundLayer:
    """Represents a single horizontally scrolling background layer."""

    def __init__(
        self,
        image_path: str,
        scroll_speed: float,
        screen_height: int,
        initial_scroll: float = 0.0,
        vertical_offset: int = 0,
    ):
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
        except (pygame.error, FileNotFoundError, ZeroDivisionError) as e:  # Specific exceptions
            print(f"Error loading background image: {image_path} - {e}")
            # Create a fallback surface
            self.image = pygame.Surface((100, screen_height)).convert()
            self.image.fill((50, 50, 50))  # Dark grey fallback

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
        needed_tiles = (
            math.ceil(screen_width / self.image_width) + 2
        )  # Add extra for smooth scrolling

        # Draw multiple instances of the image to ensure smooth scrolling
        for i in range(-1, needed_tiles):
            tile_position = (-int_scroll + i * self.image_width, self.vertical_offset)
            surface.blit(self.image, tile_position)

        # This approach ensures that tiles are always scrolling in smoothly from the right
        # rather than suddenly appearing at the edge of the screen


class BackgroundDecorations:
    """Manages decorative elements that appear in the background with parallax effect."""

    def __init__(
        self,
        decoration_paths: List[str],
        scroll_speed: float,
        screen_width: int,
        screen_height: int,
        playfield_top: int,
        playfield_bottom: int,
    ):
        """Initialize the background decorations layer.

        Args:
            decoration_paths: List of paths to decoration image files.
            scroll_speed: Horizontal scrolling speed (pixels per frame).
            screen_width: Width of the game screen.
            screen_height: Height of the game screen.
            playfield_top: Top boundary of playfield.
            playfield_bottom: Bottom boundary of playfield.
        """
        self.decorations = []
        self.screen_width = screen_width
        self.screen_height = screen_height
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

                # Apply transparency
                img_with_alpha = img.copy()
                alpha_value = DECORATION_ALPHA
                img_with_alpha.fill((255, 255, 255, alpha_value), None, pygame.BLEND_RGBA_MULT)

                self.decoration_images.append(img_with_alpha)
            except (pygame.error, FileNotFoundError) as e:
                print(f"Error loading decoration image: {path} - {e}")

        # Only proceed if we have loaded images
        if self.decoration_images:
            # Calculate an appropriate number of decorations based on screen width and horizontal spacing
            # to ensure we have enough to fill the screen and then some
            decoration_count = max(
                5, int((screen_width * 2) / DECORATION_MIN_HORIZONTAL_SPACING) + 2
            )
            self._create_random_decorations(decoration_count)
        else:
            print("No decoration images loaded.")

    def _create_random_decorations(self, count: int) -> None:
        """Create a set of randomly positioned decorations.

        Args:
            count: Number of decorations to create.
        """
        self.decorations = []

        current_x = -100

        last_used_image = None

        last_y_section = None

        top_limit = self.playfield_top + DECORATION_TOP_PADDING
        bottom_limit = self.playfield_bottom - DECORATION_BOTTOM_PADDING
        usable_height = bottom_limit - top_limit

        num_sections = 4
        section_height = usable_height / num_sections

        on_screen_count = count // 2

        for i in range(count):
            if last_used_image is not None and len(self.decoration_images) > 1:
                available_images = [img for img in self.decoration_images if img != last_used_image]
                img = random.choice(available_images)
            else:
                img = random.choice(self.decoration_images)

            last_used_image = img
            img_width, img_height = img.get_size()

            if i > 0:
                # Add minimum spacing plus some randomness
                current_x += DECORATION_MIN_HORIZONTAL_SPACING + random.randint(0, 200)

            if i == on_screen_count and current_x < self.screen_width:
                # Ensure the first off-screen decoration is actually off-screen
                # while respecting minimum spacing from the last on-screen decoration
                current_x = max(
                    current_x + DECORATION_MIN_HORIZONTAL_SPACING, self.screen_width + 100
                )

            if last_y_section is not None:
                available_sections = [s for s in range(num_sections) if s != last_y_section]
                section = random.choice(available_sections)
            else:
                section = random.randint(0, num_sections - 1)

            last_y_section = section

            section_top = top_limit + section * section_height
            section_bottom = min(section_top + section_height, bottom_limit - img_height)

            if section_bottom <= section_top:
                section_bottom = section_top + 1

            y = random.randint(int(section_top), int(section_bottom))

            self.decorations.append(
                {
                    "image": img,
                    "pos": [float(current_x), float(y)],
                    "width": img_width,
                    "height": img_height,
                    "last_section": section,  # Store section instead of exact Y
                }
            )

    def update(self) -> None:
        """Update the positions of all decorations."""
        for decoration in self.decorations:
            decoration["pos"][0] -= self.scroll_speed

            if decoration["pos"][0] < -decoration["width"]:
                rightmost_x = self.screen_width
                rightmost_decoration = None

                for d in self.decorations:
                    if d != decoration and d["pos"][0] > rightmost_x:
                        rightmost_x = d["pos"][0]
                        rightmost_decoration = d

                new_x = max(
                    rightmost_x + DECORATION_MIN_HORIZONTAL_SPACING + random.randint(0, 200),
                    self.screen_width + 100,
                )
                decoration["pos"][0] = new_x

                top_limit = self.playfield_top + DECORATION_TOP_PADDING
                bottom_limit = self.playfield_bottom - DECORATION_BOTTOM_PADDING
                usable_height = bottom_limit - top_limit

                num_sections = 4
                section_height = usable_height / num_sections

                current_section = decoration["last_section"]
                available_sections = [s for s in range(num_sections) if s != current_section]
                new_section = random.choice(available_sections)
                decoration["last_section"] = new_section

                section_top = top_limit + new_section * section_height
                section_bottom = min(
                    section_top + section_height, bottom_limit - decoration["height"]
                )

                if section_bottom <= section_top:
                    section_bottom = section_top + 1

                y = random.randint(int(section_top), int(section_bottom))
                decoration["pos"][1] = y

                if len(self.decoration_images) > 1:
                    current_img = decoration["image"]
                    nearby_img = rightmost_decoration["image"] if rightmost_decoration else None

                    available_images = [
                        img
                        for img in self.decoration_images
                        if img != current_img and img != nearby_img
                    ]

                    if available_images:
                        new_img = random.choice(available_images)
                    else:
                        other_images = [img for img in self.decoration_images if img != current_img]
                        if other_images:
                            new_img = random.choice(other_images)
                        else:
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
            pos = (int(decoration["pos"][0]), int(decoration["pos"][1]))
            surface.blit(decoration["image"], pos)
