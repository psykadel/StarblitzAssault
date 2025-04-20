"""Objective screen for Starblitz Assault game."""

import os
import random
import math
import pygame
from typing import Any, Optional, List

from config.config import SCREEN_WIDTH, SCREEN_HEIGHT

class Star:
    """A star in the starfield background."""
    
    def __init__(self, speed_factor: float = 1.0):
        """Initialize a star with random position, size, and speed."""
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(0, SCREEN_HEIGHT)
        self.size = random.randint(1, 3)
        self.brightness = random.randint(150, 255)
        self.speed = random.uniform(0.5, 2.0) * speed_factor
        
    def update(self) -> None:
        """Update star position."""
        # Move star from right to left
        self.x -= self.speed
        
        # Wrap around when off screen
        if self.x < 0:
            self.x = SCREEN_WIDTH
            self.y = random.randint(0, SCREEN_HEIGHT)
            
    def draw(self, surface: pygame.Surface) -> None:
        """Draw star on the surface."""
        pygame.draw.rect(
            surface, 
            (self.brightness, self.brightness, self.brightness),
            (int(self.x), int(self.y), self.size, self.size)
        )

class Starfield:
    """Manages multiple layers of stars with parallax effect."""
    
    def __init__(self, num_layers: int = 3, stars_per_layer: int = 50):
        """Initialize starfield with multiple layers of stars."""
        self.layers: List[List[Star]] = []
        
        # Create layers with increasing speed for parallax effect
        for i in range(num_layers):
            speed_factor = 0.5 + i * 0.8  # Increasing speed factor for each layer
            layer = [Star(speed_factor) for _ in range(stars_per_layer)]
            self.layers.append(layer)
    
    def update(self) -> None:
        """Update all stars in all layers."""
        for layer in self.layers:
            for star in layer:
                star.update()
    
    def draw(self, surface: pygame.Surface) -> None:
        """Draw all stars in all layers."""
        for layer in self.layers:
            for star in layer:
                star.draw(surface)

class LightningEffect:
    """Creates lightning effects for the objective screen."""
    
    def __init__(self):
        """Initialize lightning effect."""
        self.bolts = []
        self.active = False
        self.flash_alpha = 0
        self.next_bolt_time = 0
        
    def update(self):
        """Update lightning effects."""
        current_time = pygame.time.get_ticks()
        
        # Randomly trigger new lightning
        if not self.active and random.random() < 0.03:  # 3% chance per frame
            self.active = True
            self.create_bolt()
            self.flash_alpha = random.randint(30, 60)
            self.next_bolt_time = current_time + random.randint(100, 200)
            
        # Create follow-up bolts
        if self.active and current_time >= self.next_bolt_time:
            if random.random() < 0.7:  # 70% chance for another bolt
                self.create_bolt()
                self.flash_alpha = random.randint(20, 40)
                self.next_bolt_time = current_time + random.randint(100, 200)
            else:
                self.active = False
                
        # Fade out flash
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - 3)
            
        # Remove old lightning bolts
        self.bolts = [bolt for bolt in self.bolts if bolt['life'] > 0]
        
        # Update remaining bolts
        for bolt in self.bolts:
            bolt['life'] -= 1
            
    def create_bolt(self):
        """Create a new lightning bolt."""
        # Start positions near the edges
        start_edge = random.randint(0, 3)  # 0=top, 1=right, 2=bottom, 3=left
        
        if start_edge == 0:  # Top
            start_x = random.randint(0, SCREEN_WIDTH)
            start_y = 0
        elif start_edge == 1:  # Right
            start_x = SCREEN_WIDTH
            start_y = random.randint(0, SCREEN_HEIGHT)
        elif start_edge == 2:  # Bottom
            start_x = random.randint(0, SCREEN_WIDTH)
            start_y = SCREEN_HEIGHT
        else:  # Left
            start_x = 0
            start_y = random.randint(0, SCREEN_HEIGHT)
            
        # Create lightning segments
        segments = []
        x, y = start_x, start_y
        center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        
        # Number of segments based on distance to center
        dist_to_center = math.sqrt((center_x - x)**2 + (center_y - y)**2)
        num_segments = int(dist_to_center / 30)  # One segment per ~30px
        
        for i in range(num_segments):
            # Calculate progression toward center (0.0 to 1.0)
            t = (i + 1) / num_segments
            
            # Target next position (closer to center with some randomness)
            target_x = x + (center_x - x) * (1 / num_segments) + random.randint(-15, 15)
            target_y = y + (center_y - y) * (1 / num_segments) + random.randint(-15, 15)
            
            # Create segment
            segments.append(((x, y), (target_x, target_y)))
            
            # Update current position
            x, y = target_x, target_y
        
        # Add final segment to center
        segments.append(((x, y), (center_x + random.randint(-10, 10), center_y + random.randint(-10, 10))))
        
        # Create bolt with random color (blue/cyan tones)
        bolt = {
            'segments': segments,
            'color': (
                random.randint(100, 150),  # Red (low)
                random.randint(150, 240),  # Green (med-high)
                random.randint(200, 255),  # Blue (high)
            ),
            'width': random.randint(1, 3),  # Random thickness
            'life': random.randint(5, 10)  # Frames to live
        }
        
        self.bolts.append(bolt)
        
    def draw(self, surface):
        """Draw all lightning effects."""
        # Draw screen flash
        if self.flash_alpha > 0:
            flash_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash_surface.fill((150, 180, 255, self.flash_alpha))  # Blueish flash
            surface.blit(flash_surface, (0, 0))
            
        # Draw lightning bolts
        for bolt in self.bolts:
            for segment in bolt['segments']:
                pygame.draw.line(
                    surface,
                    bolt['color'],
                    segment[0],  # Start point
                    segment[1],  # End point
                    bolt['width']  # Line width
                )


class ObjectiveScreen:
    """Displays the game objective screen with effects."""
    
    def __init__(self, screen: pygame.Surface):
        """Initialize the objective screen."""
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Load objective image
        objective_path = os.path.join("assets", "images", "objective.png")
        try:
            self.objective_img = pygame.image.load(objective_path).convert_alpha()
            # Scale image to fit screen (70% of screen width)
            width = int(SCREEN_WIDTH * 0.7)
            height = int(width * (self.objective_img.get_height() / self.objective_img.get_width()))
            self.objective_img = pygame.transform.scale(self.objective_img, (width, height))
            # Store a clean copy of the image for VHS effect
            self.original_img = self.objective_img.copy()
        except (pygame.error, FileNotFoundError) as e:
            print(f"Error loading objective image: {e}")
            # Create fallback text
            self.objective_img = self._create_fallback_image()
            self.original_img = self.objective_img.copy()
            
        # Center position with slight offset for vibration
        self.img_rect = self.objective_img.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.base_x = self.img_rect.x
        self.base_y = self.img_rect.y
        
        # Vibration effect properties
        self.vibration_intensity = 1.5  # Maximum pixel displacement
        self.vibration_time = 0  # Time counter for vibration
        
        # VHS effect properties
        self.static_intensity = 0.15  # Static noise intensity (0.0 to 1.0)
        self.scanline_intensity = 0.1  # Scanline darkness
        self.glitch_timer = 0
        self.glitch_interval = random.randint(30, 90)  # Frames between glitches
        self.is_glitching = False
        self.glitch_duration = 0
        
        # Pre-create static textures for better performance
        self.static_textures = self._create_static_textures(5)  # Create 5 pre-computed static textures
        self.current_static_index = 0
        self.static_update_counter = 0
        
        # Pre-create scanline effect
        self.scanline_overlay = self._create_scanline_overlay()
        
        # Fade properties
        self.fade_alpha = 255  # Start with fade in
        self.fade_in = True  # Start with fade in
        self.fade_out = False  # Trigger this to begin fade out
        self.fade_speed = 2.0  # Alpha change per frame
        
        # Lighting effects
        self.lightning = LightningEffect()
        
        # Starfield effect
        self.starfield = Starfield(num_layers=3, stars_per_layer=60)
        
        # Start time for automatic transition
        self.start_time = pygame.time.get_ticks()
        self.display_duration = 5000  # 5 seconds before auto fade-out
        
    def _create_fallback_image(self) -> pygame.Surface:
        """Create fallback image if objective.png can't be loaded."""
        font_size = 48
        try:
            font = pygame.font.Font(None, font_size)
        except pygame.error:
            font = pygame.font.SysFont("arial", font_size)
            
        text_surface = font.render("MISSION OBJECTIVE", True, (255, 255, 255))
        return text_surface
    
    def _create_static_textures(self, count: int) -> List[pygame.Surface]:
        """Create multiple static noise textures for the VHS effect."""
        width, height = self.objective_img.get_size()
        textures = []
        
        for _ in range(count):
            static = pygame.Surface((width, height), pygame.SRCALPHA)
            
            # Create fewer random pixels for better performance
            for _ in range(width * height // 20):  # Only fill about 5% of pixels
                x = random.randint(0, width - 1)
                y = random.randint(0, height - 1)
                alpha = random.randint(0, 100)
                color = pygame.Color(
                    random.randint(180, 255),
                    random.randint(180, 255),
                    random.randint(180, 255),
                    alpha
                )
                # Use set_at instead of PixelArray to avoid linter error
                static.set_at((x, y), color)
                
            textures.append(static)
                
        return textures
    
    def _create_scanline_overlay(self) -> pygame.Surface:
        """Create a pre-computed scanline overlay."""
        width, height = self.objective_img.get_size()
        scanlines = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # Draw lines every other row
        for y in range(0, height, 2):
            pygame.draw.line(
                scanlines,
                (0, 0, 0, int(self.scanline_intensity * 255)),
                (0, y),
                (width, y)
            )
            
        return scanlines
    
    def _apply_simpler_vhs_effect(self):
        """Apply a more efficient VHS-style effect to the objective image."""
        # Update glitch state
        self.glitch_timer += 1
        if self.glitch_timer >= self.glitch_interval and not self.is_glitching:
            self.is_glitching = True
            self.glitch_duration = random.randint(3, 6)
            self.glitch_timer = 0
        
        if self.is_glitching:
            self.glitch_duration -= 1
            if self.glitch_duration <= 0:
                self.is_glitching = False
                self.glitch_interval = random.randint(30, 90)
        
        # Start with a clean copy of the original image
        self.objective_img = self.original_img.copy()
        
        # RGB Splitting effect - simplified version
        if self.is_glitching:
            # Only apply RGB splitting during glitches
            rgb_shift = int(random.uniform(1.5, 2.5))
            
            # Create a red-shifted copy
            red_copy = self.original_img.copy()
            red_rect = red_copy.get_rect(center=(self.img_rect.centerx - rgb_shift, self.img_rect.centery))
            
            # Create a blue-shifted copy 
            blue_copy = self.original_img.copy()
            blue_rect = blue_copy.get_rect(center=(self.img_rect.centerx + rgb_shift, self.img_rect.centery))
            
            # Blend them
            self.screen.blit(red_copy, red_rect, special_flags=pygame.BLEND_ADD)
            self.screen.blit(blue_copy, blue_rect, special_flags=pygame.BLEND_ADD)
            return  # Skip the normal rendering since we rendered directly
        
        # For non-glitch frames, just apply scanlines and static
        # Add scanlines (pre-computed)
        self.objective_img.blit(self.scanline_overlay, (0, 0))
        
        # Add static (use pre-computed textures)
        self.static_update_counter += 1
        if self.static_update_counter >= 3:  # Only update static every 3 frames
            self.static_update_counter = 0
            self.current_static_index = (self.current_static_index + 1) % len(self.static_textures)
            
        # Apply the current static texture
        current_static = self.static_textures[self.current_static_index]
        static_alpha = int(self.static_intensity * 180)
        if self.is_glitching:
            static_alpha = int(min(1.0, self.static_intensity * 2) * 180)
        
        current_static.set_alpha(static_alpha)
        self.objective_img.blit(current_static, (0, 0), special_flags=pygame.BLEND_ADD)
    
    def update(self):
        """Update the objective screen for one frame."""
        current_time = pygame.time.get_ticks()
        
        # Check for auto fade-out
        if current_time - self.start_time > self.display_duration and not self.fade_out:
            self.fade_out = True
            
        # Update fade
        if self.fade_in:
            self.fade_alpha = max(0, self.fade_alpha - self.fade_speed)
            if self.fade_alpha <= 0:
                self.fade_in = False
        elif self.fade_out:
            self.fade_alpha = min(255, self.fade_alpha + self.fade_speed)
            
        # Update vibration
        self.vibration_time += 0.2
        
        # Calculate vibration offset using sine functions for natural movement
        vibration_x = math.sin(self.vibration_time * 0.9) * self.vibration_intensity
        vibration_y = math.sin(self.vibration_time * 1.1) * self.vibration_intensity
        
        # Apply vibration to image position - convert to int to fix linter error
        self.img_rect.x = int(self.base_x + vibration_x)
        self.img_rect.y = int(self.base_y + vibration_y)
        
        # Update starfield
        self.starfield.update()
        
        # Update lightning effects
        self.lightning.update()
        
    def handle_events(self):
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                # Skip objective screen with any key press
                self.fade_out = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Skip objective screen with mouse click
                self.fade_out = True
                
    def draw(self):
        """Draw the objective screen."""
        # Clear screen
        self.screen.fill((0, 0, 0))
        
        # Draw starfield as background
        self.starfield.draw(self.screen)
        
        # Draw lightning effects behind objective image
        self.lightning.draw(self.screen)
        
        # Apply VHS effects and draw
        if self.is_glitching:
            # For glitching frames, apply direct RGB shift to the screen
            self._apply_simpler_vhs_effect()
        else:
            # For normal frames, apply effects to the image then blit
            self._apply_simpler_vhs_effect()
            self.screen.blit(self.objective_img, self.img_rect)
        
        # Draw fade overlay
        if self.fade_alpha > 0:
            fade_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            fade_surface.fill((0, 0, 0))
            # Convert fade_alpha to int to fix linter error
            fade_surface.set_alpha(int(self.fade_alpha))
            self.screen.blit(fade_surface, (0, 0))
            
    def run(self) -> bool:
        """Run the objective screen sequence.
        
        Returns:
            True if objective screen completed normally, False if user quit the game
        """
        # Start with full black screen
        self.fade_alpha = 255
        self.fade_in = True
        
        while self.running:
            # Handle events
            self.handle_events()
            
            # Update
            self.update()
            
            # Draw
            self.draw()
            
            # Update display
            pygame.display.flip()
            
            # Cap framerate
            self.clock.tick(60)
            
            # Check if fade out is complete
            if self.fade_out and self.fade_alpha >= 255:
                break
                
        return self.running


def run_objective_screen(screen: Optional[pygame.Surface] = None) -> bool:
    """Run the objective screen.
    
    Args:
        screen: Optional pygame display surface. If None, a new one will be created.
        
    Returns:
        True if objective screen completed and game should start, False if user quit
    """
    # Initialize pygame if not already done
    if not pygame.get_init():
        pygame.init()
        
    # Create screen if not provided
    created_screen = False
    if screen is None:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Starblitz Assault")
        created_screen = True
        
    # Create and run the objective screen
    objective = ObjectiveScreen(screen)
    result = objective.run()
    
    # Clean up if we created the screen
    if not result and created_screen:
        pygame.quit()
        
    return result


if __name__ == "__main__":
    # Test the objective screen when run directly
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Starblitz Assault - Objective Test")
    
    result = run_objective_screen(screen)
    
    if result:
        # In standalone mode, just quit
        print("Objective screen completed!")
    
    pygame.quit() 