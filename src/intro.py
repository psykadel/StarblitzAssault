"""Intro sequence for Starblitz Assault game."""

import os
import random
import math
import pygame
from typing import Optional, Any

from config.config import SCREEN_WIDTH, SCREEN_HEIGHT

try:
    from src.sound_manager import SoundManager
    SOUND_MANAGER_AVAILABLE = True
except ImportError:
    SoundManager = None  # type: ignore
    SOUND_MANAGER_AVAILABLE = False

# Constants for the intro
FADE_SPEED = 2.0  # Alpha change per frame
INTRO_DURATION = 6000  # Duration in milliseconds before starting fade to game
STAR_COUNT = 120  # Simple stars
PARTICLE_COUNT = 80  # Colorful particles
WARP_SPEED = 0.02  # Logo warping speed
WARP_AMOUNT = 5  # Maximum pixel displacement for warping
PULSE_SPEED = 0.004  # Logo pulse speed
PULSE_AMOUNT = 0.02  # Logo scale pulse range (1.0 ± this value)
GRID_SIZE = 40  # Size of cosmic grid cells
GRID_LINE_BRIGHTNESS = 15  # Very subtle
SHOOTING_STAR_COUNT = 3  # Number of shooting stars

class Star:
    """A star in the scrolling background."""
    
    def __init__(self):
        """Initialize a star with position, size, and brightness."""
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(0, SCREEN_HEIGHT)
        self.size = random.randint(1, 3)
        self.brightness = random.randint(150, 255)
        self.speed = random.uniform(0.5, 2.0)
        
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


class ColorParticle:
    """A colorful particle that moves in a pattern."""
    
    def __init__(self, center_x: int, center_y: int):
        """Initialize a colorful particle."""
        self.center_x = center_x
        self.center_y = center_y
        self.angle = random.uniform(0, math.pi * 2)
        self.radius = random.uniform(50, 250)  # Distance from center
        self.speed = random.uniform(0.003, 0.008)  # Rotation speed
        self.size = random.randint(2, 4)
        
        # Pick a color scheme (no alpha blending)
        color_scheme = random.randint(0, 3)
        if color_scheme == 0:  # Blues
            self.color = (random.randint(20, 100), random.randint(100, 200), random.randint(180, 255))
        elif color_scheme == 1:  # Reds
            self.color = (random.randint(180, 255), random.randint(20, 100), random.randint(20, 150))
        elif color_scheme == 2:  # Greens
            self.color = (random.randint(20, 150), random.randint(180, 255), random.randint(20, 100))
        else:  # Purples
            self.color = (random.randint(150, 220), random.randint(20, 100), random.randint(180, 255))
            
        # Orbital direction
        self.direction = 1 if random.random() > 0.5 else -1
        
        # Pulsing size
        self.pulse_speed = random.uniform(0.03, 0.08)
        self.pulse_angle = random.uniform(0, math.pi * 2)
        
    def update(self) -> None:
        """Update particle position and appearance."""
        # Update orbit
        self.angle += self.speed * self.direction
        
        # Update pulse
        self.pulse_angle += self.pulse_speed
        
    def draw(self, surface: pygame.Surface) -> None:
        """Draw particle on the surface."""
        # Calculate position based on orbit
        x = self.center_x + math.cos(self.angle) * self.radius
        y = self.center_y + math.sin(self.angle) * self.radius
        
        # Calculate current size based on pulse
        pulse_factor = 0.5 + math.sin(self.pulse_angle) * 0.5  # Range 0-1
        current_size = max(1, int(self.size * pulse_factor))
        
        # Draw particle
        pygame.draw.circle(
            surface,
            self.color,
            (int(x), int(y)),
            current_size
        )


class ShootingStar:
    """A shooting star with a trail."""
    
    def __init__(self):
        """Initialize a shooting star."""
        self.reset()
        
    def reset(self):
        """Reset shooting star to a new position."""
        # Start from either top or right edge
        if random.random() < 0.5:
            self.x = random.randint(0, SCREEN_WIDTH)
            self.y = -10
            self.angle = random.uniform(math.pi * 0.2, math.pi * 0.8)
        else:
            self.x = SCREEN_WIDTH + 10
            self.y = random.randint(0, SCREEN_HEIGHT // 2)
            self.angle = random.uniform(math.pi * 0.6, math.pi * 1.4)
        self.speed = random.uniform(5.0, 15.0)
        self.trail_length = random.randint(10, 30)
        self.brightness = random.randint(200, 255)
        self.active = True
        self.trail_positions = []
        
    def update(self) -> None:
        """Update shooting star position."""
        if not self.active:
            return
            
        # Store current position for trail
        self.trail_positions.append((self.x, self.y))
        
        # Trim trail if too long
        if len(self.trail_positions) > self.trail_length:
            self.trail_positions.pop(0)
            
        # Move based on angle and speed
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        
        # Check if off screen
        if (self.x < -20 or self.x > SCREEN_WIDTH + 20 or 
            self.y < -20 or self.y > SCREEN_HEIGHT + 20):
            # Give a delay before resetting
            self.active = False
            # Reset after a random delay
            pygame.time.set_timer(pygame.USEREVENT + 1, random.randint(500, 3000), 1)
            
    def draw(self, surface: pygame.Surface) -> None:
        """Draw shooting star with trail."""
        if not self.active or len(self.trail_positions) < 2:
            return
            
        # Draw trail
        for i in range(len(self.trail_positions) - 1):
            # Fade trail brightness based on position
            pos_ratio = i / len(self.trail_positions)
            current_brightness = int(self.brightness * pos_ratio)
            color = (current_brightness, current_brightness, current_brightness)
            
            # Draw line segment
            pygame.draw.line(
                surface,
                color,
                (int(self.trail_positions[i][0]), int(self.trail_positions[i][1])),
                (int(self.trail_positions[i+1][0]), int(self.trail_positions[i+1][1])),
                1
            )
            
        # Draw the star itself
        pygame.draw.circle(
            surface,
            (self.brightness, self.brightness, self.brightness),
            (int(self.x), int(self.y)),
            2
        )


class CosmicGrid:
    """A subtle grid effect in the background."""
    
    def __init__(self):
        """Initialize the cosmic grid."""
        self.cell_size = GRID_SIZE
        self.brightness = GRID_LINE_BRIGHTNESS
        self.offset_x = 0
        self.offset_y = 0
        self.speed_x = 0.2
        self.speed_y = 0.1
        
    def update(self) -> None:
        """Update grid position."""
        self.offset_x = (self.offset_x + self.speed_x) % self.cell_size
        self.offset_y = (self.offset_y + self.speed_y) % self.cell_size
        
    def draw(self, surface: pygame.Surface) -> None:
        """Draw the cosmic grid."""
        # Draw vertical lines
        for x in range(0, SCREEN_WIDTH + self.cell_size, self.cell_size):
            pos_x = int(x - self.offset_x)
            pygame.draw.line(
                surface,
                (self.brightness, self.brightness, self.brightness),
                (pos_x, 0),
                (pos_x, SCREEN_HEIGHT),
                1
            )
            
        # Draw horizontal lines
        for y in range(0, SCREEN_HEIGHT + self.cell_size, self.cell_size):
            pos_y = int(y - self.offset_y)
            pygame.draw.line(
                surface,
                (self.brightness, self.brightness, self.brightness),
                (0, pos_y),
                (SCREEN_WIDTH, pos_y),
                1
            )


class IntroSequence:
    """Handles the game intro sequence."""
    
    def __init__(self, screen: pygame.Surface, sound_manager: Any = None):
        """Initialize the intro sequence."""
        self.screen = screen
        self.running = True
        self.clock = pygame.time.Clock()
        self.fade_alpha = 0
        self.fade_out = False
        self.start_time = pygame.time.get_ticks()
        self.sound_manager = sound_manager
        self.using_sound_manager = sound_manager is not None and SOUND_MANAGER_AVAILABLE
        
        # Initialize stars
        self.stars = [Star() for _ in range(STAR_COUNT)]
        
        # Initialize cosmic grid
        self.grid = CosmicGrid()
        
        # Initialize shooting stars
        self.shooting_stars = [ShootingStar() for _ in range(SHOOTING_STAR_COUNT)]
        
        # Load the logo
        logo_path = os.path.join("assets", "images", "logo.png")
        try:
            self.original_logo = pygame.image.load(logo_path).convert_alpha()
            # Calculate appropriate size (50% of screen width max)
            width = min(SCREEN_WIDTH * 0.5, self.original_logo.get_width())
            height = width * (self.original_logo.get_height() / self.original_logo.get_width())
            self.original_logo = pygame.transform.scale(self.original_logo, (int(width), int(height)))
            self.logo = self.original_logo.copy()
        except (pygame.error, FileNotFoundError) as e:
            print(f"Error loading logo: {e}")
            # Create a fallback logo
            self.original_logo = self._create_fallback_logo()
            self.logo = self.original_logo.copy()
            
        # Logo position and effects
        self.logo_rect = self.logo.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.warp_time = 0
        self.pulse_time = 0
        self.current_scale = 1.0
        
        # Create colorful particles
        self.particles = [
            ColorParticle(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2) 
            for _ in range(PARTICLE_COUNT)
        ]
        
        # Music and sound
        self._setup_audio()
        
    def _create_fallback_logo(self) -> pygame.Surface:
        """Create a fallback logo if the image can't be loaded."""
        font_size = 48
        try:
            font = pygame.font.Font(None, font_size)
        except pygame.error:
            font = pygame.font.SysFont("arial", font_size)
            
        text_surface = font.render("STARBLITZ ASSAULT", True, (255, 255, 255))
        return text_surface
        
    def _setup_audio(self) -> None:
        """Set up intro music and sounds."""
        if self.using_sound_manager and self.sound_manager is not None:
            # Use the game's sound manager
            try:
                # Just play background music directly - no intro-specific music
                self.sound_manager.play_music("background-music.mp3", loops=-1, fade_ms=1000)
            except Exception as e:
                print(f"Error playing background music: {e}")
        else:
            # Fallback to direct pygame mixer
            try:
                # Try to initialize mixer if not already done
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                    
                # Play background music directly
                music_path = os.path.join("assets", "music", "background-music.mp3")
                if os.path.exists(music_path):
                    pygame.mixer.music.load(music_path)
                    pygame.mixer.music.set_volume(0.7)
                    pygame.mixer.music.play(-1)  # Loop indefinitely
            except (pygame.error, FileNotFoundError) as e:
                print(f"Could not load background music: {e}")
    
    def _update_stars(self) -> None:
        """Update all stars in the background."""
        for star in self.stars:
            star.update()
    
    def _update_grid(self) -> None:
        """Update cosmic grid."""
        self.grid.update()
    
    def _update_shooting_stars(self) -> None:
        """Update shooting stars."""
        for star in self.shooting_stars:
            star.update()
    
    def _update_particles(self) -> None:
        """Update all particles."""
        for particle in self.particles:
            particle.update()
    
    def _update_logo_effects(self) -> None:
        """Update logo warping and pulsing effects."""
        # Update warp time
        self.warp_time += WARP_SPEED
        
        # Update pulse
        self.pulse_time += PULSE_SPEED
        self.current_scale = 1.0 + math.sin(self.pulse_time) * PULSE_AMOUNT
        
        # Scale the logo for pulse effect
        width = int(self.original_logo.get_width() * self.current_scale)
        height = int(self.original_logo.get_height() * self.current_scale)
        self.logo = pygame.transform.scale(self.original_logo, (width, height))
        
        # Center the scaled logo
        self.logo_rect = self.logo.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            
    def _handle_events(self) -> None:
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                # Skip intro with any key press
                self.fade_out = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Skip intro with mouse click
                self.fade_out = True
            elif event.type >= pygame.USEREVENT + 1 and event.type <= pygame.USEREVENT + SHOOTING_STAR_COUNT:
                # Reset a shooting star
                star_index = event.type - pygame.USEREVENT - 1
                if star_index < len(self.shooting_stars):
                    self.shooting_stars[star_index].reset()
                
    def _draw_grid(self) -> None:
        """Draw cosmic grid."""
        self.grid.draw(self.screen)
                
    def _draw_stars(self) -> None:
        """Draw all stars in the background."""
        for star in self.stars:
            star.draw(self.screen)
    
    def _draw_shooting_stars(self) -> None:
        """Draw shooting stars."""
        for star in self.shooting_stars:
            star.draw(self.screen)
    
    def _draw_particles(self) -> None:
        """Draw all particles."""
        for particle in self.particles:
            particle.draw(self.screen)
    
    def _draw_cosmic_rays(self) -> None:
        """Draw random cosmic rays from the screen edge toward the logo."""
        if random.random() < 0.05:
            start_edge = random.randint(0, 3)
            if start_edge == 0:
                start_x = random.randint(0, SCREEN_WIDTH)
                start_y = 0
            elif start_edge == 1:
                start_x = SCREEN_WIDTH
                start_y = random.randint(0, SCREEN_HEIGHT)
            elif start_edge == 2:
                start_x = random.randint(0, SCREEN_WIDTH)
                start_y = SCREEN_HEIGHT
            else:
                start_x = 0
                start_y = random.randint(0, SCREEN_HEIGHT)
            end_x = SCREEN_WIDTH // 2 + random.randint(-40, 40)
            end_y = SCREEN_HEIGHT // 2 + random.randint(-20, 20)
            color = (
                random.randint(20, 150),
                random.randint(100, 200),
                random.randint(150, 255)
            )
            pygame.draw.line(self.screen, color, (start_x, start_y), (end_x, end_y), 1)
            
    def _draw_fade(self) -> None:
        """Draw fade overlay."""
        if self.fade_out:
            # For fade out, increase alpha
            self.fade_alpha = min(255, self.fade_alpha + FADE_SPEED)
        else:
            # For fade in, decrease alpha
            self.fade_alpha = max(0, self.fade_alpha - FADE_SPEED)
            
        # Draw the fade surface if alpha is non-zero
        if self.fade_alpha > 0:
            # Create a solid surface without alpha
            fade_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            fade_surface.fill((0, 0, 0))
            # Set alpha for the entire surface
            fade_surface.set_alpha(int(self.fade_alpha))
            # Blit to screen
            self.screen.blit(fade_surface, (0, 0))
            
    def update(self) -> None:
        """Update all intro components for one frame."""
        # Check if we should start fading out based on time
        current_time = pygame.time.get_ticks()
        if current_time - self.start_time > INTRO_DURATION and not self.fade_out:
            self.fade_out = True
            
        # Update all components
        self._update_stars()
        self._update_grid()
        self._update_shooting_stars()
        self._update_particles()
        self._update_logo_effects()
        self._handle_events()
        
    def draw(self) -> None:
        """Draw the entire intro sequence for one frame."""
        # Clear the screen
        self.screen.fill((0, 0, 0))
        
        # Draw cosmic grid (very subtle)
        self._draw_grid()
        
        # Draw stars
        self._draw_stars()
        
        # Draw shooting stars
        self._draw_shooting_stars()
        
        # Draw occasional cosmic rays
        self._draw_cosmic_rays()
        
        # Draw particles behind logo
        self._draw_particles()
        
        # Draw logo
        self.screen.blit(self.logo, self.logo_rect)
        
        # Draw fade overlay
        self._draw_fade()
        
    def run(self) -> bool:
        """Run the intro sequence.
        
        Returns:
            True if intro completed normally, False if user quit the game
        """
        # Start with full black screen, fade in
        self.fade_alpha = 255
        
        while self.running:
            # Update components
            self.update()
            
            # Draw everything
            self.draw()
            
            # Update display
            pygame.display.flip()
            
            # Cap framerate
            self.clock.tick(60)
            
            # Check if fade out is complete
            if self.fade_out and self.fade_alpha >= 255:
                # Music is already playing - no transition needed
                break
                
        # Return True if the intro completed (didn't quit)
        return self.running
        
        
def run_intro(screen: Optional[pygame.Surface] = None, sound_manager: Any = None) -> bool:
    """Run the game intro sequence.
    
    Args:
        screen: Optional pygame display surface. If None, a new one will be created.
        sound_manager: Optional sound manager to handle audio
        
    Returns:
        True if intro completed and game should start, False if user quit
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
        
    # Create and run the intro sequence
    intro = IntroSequence(screen, sound_manager)
    result = intro.run()
    
    # Clean up if we created the screen
    if not result and created_screen:
        pygame.quit()
        
    return result


if __name__ == "__main__":
    # Test the intro when run directly
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Starblitz Assault - Intro Test")
    
    # Create a sound manager instance for testing
    sound_mgr = None
    if SOUND_MANAGER_AVAILABLE and SoundManager is not None:
        try:
            sound_mgr = SoundManager()
        except Exception as e:
            print(f"Could not create sound manager: {e}")
    
    result = run_intro(screen, sound_mgr)
    
    if result:
        # In standalone mode, just display a message
        font = pygame.font.Font(None, 36)
        text = font.render("Intro completed! Game would start here.", True, (255, 255, 255))
        text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        
        # Display the message for a few seconds
        screen.fill((0, 0, 0))
        screen.blit(text, text_rect)
        pygame.display.flip()
        
        # Wait for a few seconds or until user closes window
        start_time = pygame.time.get_ticks()
        running = True
        while running and pygame.time.get_ticks() - start_time < 3000:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    
    pygame.quit()
