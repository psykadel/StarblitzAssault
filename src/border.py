"""Manages game borders with horizontal scrolling effect."""

import pygame

from config.config import SCREEN_WIDTH, SCREEN_HEIGHT


class Border:
    """Represents a horizontally scrolling border (top or bottom of screen)."""

    def __init__(
        self, image_path: str, is_top: bool, scroll_speed: float = 2.0, max_height: int = 75
    ):
        """Initializes a border layer.

        Args:
            image_path: Path to the border image file.
            is_top: If True, places the border at the top of the screen, otherwise at the bottom.
            scroll_speed: Horizontal scrolling speed in pixels per frame.
            max_height: Maximum height of the border in pixels.
        """
        try:
            self.original_image = pygame.image.load(image_path).convert_alpha()

            orig_width, orig_height = self.original_image.get_size()
            scale_factor = min(max_height / orig_height, 1.0)  # Don't scale up if smaller than max_height
            new_width = int(orig_width * scale_factor)
            new_height = int(orig_height * scale_factor)

            self.image = pygame.transform.scale(self.original_image, (new_width, new_height))
        except (pygame.error, FileNotFoundError) as e:
            print(f"Error loading border image: {image_path} - {e}")
            # Create a fallback surface (small grey rectangle)
            self.image = pygame.Surface((SCREEN_WIDTH, 20)).convert_alpha()
            self.image.fill((50, 50, 50))  # Dark grey fallback

        self.is_top = is_top
        self.rect = self.image.get_rect()

        if self.is_top:
            self.y_position = -1
        else:
            self.y_position = SCREEN_HEIGHT - self.rect.height + 1

        self.scroll_speed = scroll_speed
        self.scroll = 0.0
        self.image_width = self.image.get_width()

    def update(self) -> None:
        """Updates the scroll position of the border."""
        self.scroll += self.scroll_speed
        if self.scroll >= self.image_width:
            self.scroll %= self.image_width

    def draw(self, surface: pygame.Surface) -> None:
        """Draws the scrolling border onto the given surface."""
        screen_width = surface.get_width()

        # Calculate number of tiles needed for coverage
        num_tiles = (screen_width // self.image_width) + 2

        start_x = -(self.scroll % self.image_width)

        for i in range(num_tiles):
            x_pos = start_x + (i * self.image_width)
            surface.blit(self.image, (x_pos, self.y_position))
