"""Boss battle introduction sequence for Starblitz Assault."""

import math
import os
import random
from typing import List, Optional, Tuple, Any

import pygame
import numpy as np

from config.config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    IMAGES_DIR,
    BOSS_BULLET_COLORS,
)
from src.sound_manager import SoundManager


class RainbowStar:
    """A colorful star that moves in a swirling pattern."""
    
    def __init__(self, center_x: int, center_y: int):
        """Initialize a rainbow star.
        
        Args:
            center_x: Center x-coordinate for the swirl
            center_y: Center y-coordinate for the swirl
        """
        self.center_x = center_x
        self.center_y = center_y
        self.angle = random.uniform(0, math.pi * 2)
        self.radius = random.uniform(50, 350)
        self.orbit_speed = random.uniform(0.01, 0.05)
        self.size = random.randint(2, 6)
        self.pulse_speed = random.uniform(0.05, 0.12)
        self.pulse_angle = random.uniform(0, math.pi * 2)
        self.color_index = random.randint(0, len(BOSS_BULLET_COLORS) - 1)
        self.color_shift_speed = random.uniform(0.02, 0.1)
        self.direction = random.choice([-1, 1])
        self.trail_length = random.randint(3, 8)
        self.trail_positions = []
        
    def update(self) -> None:
        """Update star position and appearance."""
        # Update orbit
        self.angle += self.orbit_speed * self.direction
        
        # Update pulse
        self.pulse_angle += self.pulse_speed
        
        # Calculate position
        x = self.center_x + math.cos(self.angle) * self.radius
        y = self.center_y + math.sin(self.angle) * self.radius
        
        # Store current position for trail
        self.trail_positions.append((x, y))
        if len(self.trail_positions) > self.trail_length:
            self.trail_positions.pop(0)
            
        # Shift color
        self.color_index = (self.color_index + self.color_shift_speed) % len(BOSS_BULLET_COLORS)
    
    def draw(self, surface: pygame.Surface) -> None:
        """Draw star with trailing effect on the surface."""
        if len(self.trail_positions) <= 1:
            return
            
        # Calculate current size based on pulse
        pulse_factor = 0.5 + math.sin(self.pulse_angle) * 0.5  # Range 0-1
        current_size = max(1, int(self.size * pulse_factor))
        
        # Draw trail
        for i in range(len(self.trail_positions) - 1):
            # Get two adjacent positions
            pos1 = self.trail_positions[i]
            pos2 = self.trail_positions[i + 1]
            
            # Calculate color based on trail position
            trail_progress = i / (len(self.trail_positions) - 1)
            color_idx = int((self.color_index + trail_progress * 3) % len(BOSS_BULLET_COLORS))
            color = BOSS_BULLET_COLORS[color_idx]
            
            # Draw line segment
            thickness = max(1, int(current_size * (i / len(self.trail_positions))))
            pygame.draw.line(
                surface,
                color,
                (int(pos1[0]), int(pos1[1])),
                (int(pos2[0]), int(pos2[1])),
                thickness
            )
        
        # Draw the star at the current position
        if self.trail_positions:
            pos = self.trail_positions[-1]
            color_idx = int(self.color_index) % len(BOSS_BULLET_COLORS)
            color = BOSS_BULLET_COLORS[color_idx]
            pygame.draw.circle(
                surface,
                color,
                (int(pos[0]), int(pos[1])),
                current_size
            )


class ElectricSpark:
    """Electric arcs that emanate from behind the boss image."""
    
    def __init__(self, origin_x: float, origin_y: float, max_length: int = 100):
        """Initialize an electric spark.
        
        Args:
            origin_x: Origin x-coordinate
            origin_y: Origin y-coordinate
            max_length: Maximum length of the spark
        """
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.angle = random.uniform(0, math.pi * 2)
        self.length = random.randint(max_length // 2, max_length)
        self.segments = random.randint(5, 12)
        self.lifetime = random.randint(5, 15)
        self.current_life = self.lifetime
        self.thickness = random.randint(2, 4)
        self.color_index = random.uniform(0, len(BOSS_BULLET_COLORS) - 1)
        self.color_shift_speed = random.uniform(0.2, 0.5)
        self.points = self._generate_lightning_path()
        
    def _generate_lightning_path(self) -> List[Tuple[float, float]]:
        """Generate a lightning bolt path with random zigzags.
        
        Returns:
            List of (x, y) coordinate tuples
        """
        points: List[Tuple[float, float]] = [(self.origin_x, self.origin_y)]
        x, y = self.origin_x, self.origin_y
        
        # First segment straight out
        end_x = x + math.cos(self.angle) * self.length
        end_y = y + math.sin(self.angle) * self.length
        
        for i in range(1, self.segments + 1):
            # Progress along the main direction
            progress = i / self.segments
            segment_x = x + (end_x - x) * progress
            segment_y = y + (end_y - y) * progress
            
            # Add randomness, more as we get further from origin
            jitter = self.length * 0.15 * progress
            segment_x += random.uniform(-jitter, jitter)
            segment_y += random.uniform(-jitter, jitter)
            
            points.append((segment_x, segment_y))
            
        return points
    
    def update(self) -> None:
        """Update spark lifetime and appearance."""
        self.current_life -= 1
        self.color_index = (self.color_index + self.color_shift_speed) % len(BOSS_BULLET_COLORS)
        
        # Regenerate lightning path occasionally
        if random.random() < 0.2:
            self.points = self._generate_lightning_path()
    
    def draw(self, surface: pygame.Surface) -> None:
        """Draw the electric spark on the surface."""
        if self.current_life <= 0 or len(self.points) < 2:
            return
            
        # Draw each segment of the lightning
        for i in range(len(self.points) - 1):
            # Get color based on segment and current color index
            segment_progress = i / (len(self.points) - 1)
            color_idx = int((self.color_index + segment_progress * 3) % len(BOSS_BULLET_COLORS))
            color = BOSS_BULLET_COLORS[color_idx]
            
            # Make closer segments brighter and thicker
            alpha_factor = 1.0 - (i / len(self.points)) * 0.5  # Fades out toward the end
            faded_color = (
                color[0], 
                color[1], 
                color[2]
            )
            
            thickness = max(1, int(self.thickness * alpha_factor))
            
            # Draw the segment
            pygame.draw.line(
                surface,
                faded_color,
                (int(self.points[i][0]), int(self.points[i][1])),
                (int(self.points[i+1][0]), int(self.points[i+1][1])),
                thickness
            )


class BossIntroSequence:
    """Handles the epic boss intro sequence."""
    
    def __init__(self, screen: pygame.Surface, sound_manager: Optional[SoundManager] = None):
        """Initialize the boss intro sequence.
        
        Args:
            screen: The pygame display surface
            sound_manager: Optional sound manager for audio
        """
        self.screen = screen
        self.sound_manager = sound_manager
        self.clock = pygame.time.Clock()
        self.running = True
        self.completed = False
        self.elapsed_time = 0
        
        # Constants
        self.INTRO_DURATION = 6000  # ms
        self.STAR_COUNT = 150
        self.SPARK_COUNT = 20
        self.GLITCH_INTENSITY = 0
        self.MAX_GLITCH = 20
        
        # Load boss image
        self.boss_image = self._load_boss_image()
        self.boss_rect = self.boss_image.get_rect()
        self.boss_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        
        # Animation state
        self.boss_scale = 0.1  # Start small
        self.boss_alpha = 0
        self.stars = [
            RainbowStar(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            for _ in range(self.STAR_COUNT)
        ]
        self.sparks = []
        
        # Surfaces for effects
        self.glitch_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.stars_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        
        # Play siren sound
        self._setup_audio()
        
    def _load_boss_image(self) -> pygame.Surface:
        """Load the boss-incoming.png image or create fallback if not found.
        
        Returns:
            Pygame Surface with the boss image
        """
        image_path = os.path.join(IMAGES_DIR, "boss-incoming.png")
        try:
            image = pygame.image.load(image_path).convert_alpha()
            return image
        except (pygame.error, FileNotFoundError):
            # Create fallback image
            fallback = pygame.Surface((400, 200), pygame.SRCALPHA)
            font = pygame.font.SysFont("Arial", 48, bold=True)
            text = font.render("BOSS INCOMING!", True, (255, 50, 50))
            text_rect = text.get_rect(center=(200, 100))
            fallback.blit(text, text_rect)
            return fallback
    
    def _setup_audio(self) -> None:
        """Set up and play intro sounds."""
        if self.sound_manager:
            self.sound_manager.play("siren1", "enemy", volume=0.8)
    
    def _apply_glitch_effect(self, surface: pygame.Surface, intensity: int) -> pygame.Surface:
        """Apply a glitch effect to the given surface.
        
        Args:
            surface: The surface to glitch
            intensity: Glitch intensity level (0-20)
            
        Returns:
            A new surface with the glitch effect applied
        """
        if intensity <= 0:
            return surface.copy()
            
        # Create a copy of the surface to modify
        glitched = surface.copy()
        
        # Random horizontal line displacements
        for _ in range(intensity // 2):
            y = random.randint(0, surface.get_height() - 1)
            height = random.randint(1, 3 + intensity // 4)
            chunk = surface.subsurface((0, y, surface.get_width(), min(height, surface.get_height() - y)))
            offset_x = random.randint(-intensity, intensity) * 2
            glitched.blit(chunk, (offset_x, y))
        
        # Random color channel shifts
        if random.random() < 0.4:
            pixels_array = pygame.surfarray.pixels3d(glitched)
            
            # Shift red channel
            if random.random() < 0.5:
                shift_x = random.randint(-intensity, intensity)
                shift_y = random.randint(-intensity // 2, intensity // 2)
                pixels_array[:,:,0] = np.roll(np.roll(pixels_array[:,:,0], shift_x, axis=0), shift_y, axis=1)
            
            # Shift blue channel
            if random.random() < 0.5:
                shift_x = random.randint(-intensity, intensity)
                shift_y = random.randint(-intensity // 2, intensity // 2)
                pixels_array[:,:,2] = np.roll(np.roll(pixels_array[:,:,2], shift_x, axis=0), shift_y, axis=1)
            
            del pixels_array  # Release the surface lock
        
        return glitched
    
    def update(self) -> None:
        """Update the intro animation state."""
        dt = self.clock.tick(60)
        self.elapsed_time += dt
        
        # Progress as percentage (0-1)
        progress = min(1.0, self.elapsed_time / self.INTRO_DURATION)
        
        # Update stars
        for star in self.stars:
            star.update()
        
        # Update existing sparks and remove dead ones
        self.sparks = [spark for spark in self.sparks if spark.current_life > 0]
        for spark in self.sparks:
            spark.update()
        
        # Add new sparks
        if len(self.sparks) < self.SPARK_COUNT and random.random() < 0.3:
            # Create spark from random position around the boss image
            angle = random.uniform(0, math.pi * 2)
            distance = random.randint(20, 100)
            origin_x = float(self.boss_rect.centerx + math.cos(angle) * distance)
            origin_y = float(self.boss_rect.centery + math.sin(angle) * distance)
            self.sparks.append(ElectricSpark(origin_x, origin_y, max_length=150))
        
        # Update boss image effects
        self.boss_scale = 0.1 + 0.9 * progress
        self.boss_alpha = min(255, int(255 * (progress * 1.5)))
        
        # Update glitch effect intensity
        self.GLITCH_INTENSITY = int(self.MAX_GLITCH * min(1.0, progress * 2))
        if progress > 0.8:
            self.GLITCH_INTENSITY = int(self.MAX_GLITCH * (1.0 - (progress - 0.8) * 5))
        
        # Check if sequence completed
        if self.elapsed_time >= self.INTRO_DURATION:
            self.completed = True
    
    def draw(self) -> None:
        """Draw the intro animation frame."""
        # Clear surfaces
        self.stars_surface.fill((0, 0, 0, 0))
        self.glitch_surface.fill((0, 0, 0, 0))
        
        # Fill the screen with dark background
        self.screen.fill((5, 2, 10))
        
        # Draw stars
        for star in self.stars:
            star.draw(self.stars_surface)
        
        # Apply a slight blur effect to stars (simple approximation)
        self.screen.blit(self.stars_surface, (0, 0))
        
        # Create scaled boss image
        current_scale = self.boss_scale
        scaled_width = int(self.boss_image.get_width() * current_scale)
        scaled_height = int(self.boss_image.get_height() * current_scale)
        scaled_boss = pygame.transform.scale(self.boss_image, (scaled_width, scaled_height))
        
        # Update boss rectangle for current scale
        self.boss_rect = scaled_boss.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        
        # Create a semi-transparent boss image for alpha effect
        boss_with_alpha = scaled_boss.copy()
        if self.boss_alpha < 255:
            boss_with_alpha.set_alpha(self.boss_alpha)
        
        # Draw electricity behind the boss
        for spark in self.sparks:
            spark.draw(self.screen)
        
        # Apply glitch effect to boss image
        if self.GLITCH_INTENSITY > 0:
            boss_with_alpha = self._apply_glitch_effect(boss_with_alpha, self.GLITCH_INTENSITY)
        
        # Draw the boss image
        self.screen.blit(boss_with_alpha, self.boss_rect)
    
    def handle_events(self) -> None:
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                # Only allow quitting with Escape
                if event.key == pygame.K_ESCAPE:
                    self.running = False
    
    def run(self) -> bool:
        """Run the boss intro sequence.
        
        Returns:
            True if intro completed normally, False if aborted
        """
        while self.running and not self.completed:
            self.handle_events()
            self.update()
            self.draw()
            pygame.display.flip()
        
        return self.completed


def run_boss_intro(screen: Optional[pygame.Surface] = None, sound_manager: Optional[SoundManager] = None) -> bool:
    """Run the boss intro sequence.
    
    Args:
        screen: The pygame display surface to draw on
        sound_manager: Sound manager for audio effects
    
    Returns:
        True if intro completed normally, False if aborted
    """
    # Initialize pygame if not already done
    if not pygame.get_init():
        pygame.init()
    
    # Create screen if not provided
    if screen is None:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        
    # Run the intro sequence
    intro = BossIntroSequence(screen, sound_manager)
    result = intro.run()
    
    return result 