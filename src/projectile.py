"""Projectiles for the game."""

import pygame
import math
import random
from typing import Tuple, Optional, List, Any

from src.logger import get_logger
from config.game_config import BULLET_SPEED, BULLET_SIZE

# Get a logger for this module
logger = get_logger(__name__)

class Bullet(pygame.sprite.Sprite):
    """Basic projectile fired by the player."""
    
    def __init__(self, x: int, y: int, *groups) -> None:
        """Initialize a bullet at position (x, y)."""
        super().__init__(*groups)
        
        # Create bullet surface
        self.image = pygame.Surface(BULLET_SIZE, pygame.SRCALPHA)
        # Draw the bullet as a white circle
        pygame.draw.circle(
            self.image, 
            (240, 240, 240),  # Near-white color
            (BULLET_SIZE[0] // 2, BULLET_SIZE[1] // 2), 
            BULLET_SIZE[0] // 2
        )
        
        # Add a subtle glow effect
        glow_size = (BULLET_SIZE[0] + 4, BULLET_SIZE[1] + 4)
        glow_surface = pygame.Surface(glow_size, pygame.SRCALPHA)
        pygame.draw.circle(
            glow_surface,
            (240, 240, 255, 128),  # Semi-transparent white/blue
            (glow_size[0] // 2, glow_size[1] // 2),
            glow_size[0] // 2
        )
        
        # Create the final image with glow
        final_size = (BULLET_SIZE[0] + 4, BULLET_SIZE[1] + 4)
        final_image = pygame.Surface(final_size, pygame.SRCALPHA)
        final_image.blit(glow_surface, (0, 0))
        final_image.blit(self.image, (2, 2))  # Center the bullet on the glow
        self.image = final_image
        
        # Set up rect and mask
        self.rect = self.image.get_rect(center=(x, y))
        self.mask = pygame.mask.from_surface(self.image)
        
        # Set up velocity
        self.velocity_x = BULLET_SPEED
        self.velocity_y = 0
        
        # For precise position tracking
        self.pos_x = float(x)
        self.pos_y = float(y)
        
        # For homing missiles
        self.is_homing = False
        self.target = None
        self.turn_rate = 0.25  # Increased from 0.1 for faster turning
        self.homing_speed = BULLET_SPEED * 0.9  # Slightly faster than before (was 0.85)
        
    def update(self) -> None:
        """Update the bullet's position."""
        if self.is_homing and self.target:
            # Homing missile behavior
            self._update_homing()
        else:
            # Standard bullet behavior
            self.pos_x += self.velocity_x
            self.pos_y += self.velocity_y
        
        # Update rect based on float position
        self.rect.x = round(self.pos_x)
        self.rect.y = round(self.pos_y)
        
        # Remove bullet if it goes off-screen
        if self.rect.left > pygame.display.get_surface().get_width():
            self.kill()
    
    def _update_homing(self) -> None:
        """Update position for homing missile behavior."""
        # Skip if target is gone
        if not self.target or not self.target.alive():
            self.is_homing = False
            return
            
        # Calculate direction to target
        target_x, target_y = self.target.rect.center
        dx = target_x - self.pos_x
        dy = target_y - self.pos_y
        
        # Normalize direction
        distance = math.hypot(dx, dy)
        if distance > 0:
            dx /= distance
            dy /= distance
            
            # Calculate velocity
            angle = math.atan2(dy, dx)
            
            # Smoothly adjust direction
            current_angle = math.atan2(self.velocity_y, self.velocity_x)
            
            # Calculate angle difference (handle wrap-around)
            angle_diff = ((angle - current_angle + math.pi) % (2 * math.pi)) - math.pi
            
            # Update angle based on turn rate - increase turn rate when closer to target for better tracking
            turn_rate_adjusted = self.turn_rate
            if distance < 200:
                # Increase turn rate when getting closer to target
                turn_rate_adjusted = self.turn_rate * (1.5 + (200 - distance) / 100)
                
            new_angle = current_angle + angle_diff * turn_rate_adjusted
            
            # Update velocity components
            self.velocity_x = math.cos(new_angle) * self.homing_speed
            self.velocity_y = math.sin(new_angle) * self.homing_speed
        
        # Apply velocity
        self.pos_x += self.velocity_x
        self.pos_y += self.velocity_y
        
        # Create a trail effect (if pulse_time attribute exists)
        if hasattr(self, 'pulse_time'):
            self.pulse_time += self.pulse_speed
            
            # Update the appearance of the missile to create a pulsing effect
            if random.random() < 0.2:  # Occasionally update appearance
                # Get current missile size
                if hasattr(self, 'original_size'):
                    size = self.original_size
                else:
                    size = self.rect.width
                    self.original_size = size
                
                # Create pulsing effect
                pulse_factor = 1.0 + 0.1 * math.sin(self.pulse_time)
                new_size = int(size * pulse_factor)
                
                # Re-create the image with the pulsed size
                old_center = self.rect.center
                
                # Change appearance for pulsing effect
                self.image = pygame.Surface((new_size, new_size), pygame.SRCALPHA)
                
                # Draw the homing missile
                points = [
                    (new_size - 2, new_size // 2),           # Tip
                    (0, new_size // 4),                      # Bottom left
                    (0, 3 * new_size // 4)                   # Top left
                ]
                pygame.draw.polygon(
                    self.image,
                    (255, 50, 50),  # Bright red
                    points
                )
                
                # Add yellow tip
                pygame.draw.circle(
                    self.image,
                    (255, 255, 0),  # Bright yellow
                    (new_size - 5, new_size // 2),
                    new_size // 4
                )
                
                # Add engine glow
                glow_points = [
                    (0, new_size // 3),                  # Top
                    (0, 2 * new_size // 3),              # Bottom
                    (-new_size // 1.5, new_size // 2)    # Left tip
                ]
                pygame.draw.polygon(
                    self.image,
                    (255, 200, 0, 230),  # More solid orange-yellow glow
                    glow_points
                )
                
                # Update rect and mask
                self.rect = self.image.get_rect(center=old_center)
                self.mask = pygame.mask.from_surface(self.image)
        
    def make_homing(self, target) -> None:
        """Convert this bullet to a homing missile."""
        self.is_homing = True
        self.target = target
        
        # Change appearance to indicate homing status - make larger and more obvious
        size = max(BULLET_SIZE) * 2  # Double the size for better visibility
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        
        # Draw the homing missile as a bright red triangle with yellow tip
        points = [
            (size - 2, size // 2),           # Tip
            (0, size // 4),                  # Bottom left
            (0, 3 * size // 4)               # Top left
        ]
        pygame.draw.polygon(
            self.image,
            (255, 50, 50),  # Brighter red
            points
        )
        
        # Add yellow tip to make it more visible
        pygame.draw.circle(
            self.image,
            (255, 255, 0),  # Bright yellow
            (size - 5, size // 2),
            size // 4
        )
        
        # Add larger, more obvious engine glow
        glow_points = [
            (0, size // 3),                  # Top
            (0, 2 * size // 3),              # Bottom
            (-size // 1.5, size // 2)        # Left tip - extend further
        ]
        pygame.draw.polygon(
            self.image,
            (255, 200, 0, 230),  # More solid orange-yellow glow
            glow_points
        )
        
        # Add pulsing effect variables
        self.pulse_time = 0
        self.pulse_speed = 0.2
        
        # Update rect and mask
        old_center = self.rect.center
        self.rect = self.image.get_rect(center=old_center)
        self.mask = pygame.mask.from_surface(self.image)
        
        # Log that a homing missile was created
        logger.info(f"Created homing missile targeting enemy at {target.rect.center if target else 'unknown'}")


class ScatterProjectile(pygame.sprite.Sprite):
    """Projectile that moves in a specified direction."""
    
    def __init__(self, x: int, y: int, angle: float, speed: float, *groups) -> None:
        """Initialize a scatter projectile.
        
        Args:
            x: Starting X position
            y: Starting Y position
            angle: Direction angle in radians
            speed: Movement speed
            groups: Sprite groups to add to
        """
        super().__init__(*groups)
        
        # Create projectile surface (slightly smaller than regular bullet)
        size = (BULLET_SIZE[0] - 2, BULLET_SIZE[1] - 2)
        self.image = pygame.Surface(size, pygame.SRCALPHA)
        
        # Draw the projectile as a yellow-orange circle
        pygame.draw.circle(
            self.image, 
            (255, 200, 50),  # Yellow-orange color
            (size[0] // 2, size[1] // 2), 
            size[0] // 2
        )
        
        # Set up rect and mask
        self.rect = self.image.get_rect(center=(x, y))
        self.mask = pygame.mask.from_surface(self.image)
        
        # Calculate velocity from angle and speed
        self.velocity_x = math.cos(angle) * speed
        self.velocity_y = math.sin(angle) * speed
        
        # For precise position tracking
        self.pos_x = float(x)
        self.pos_y = float(y)
        
        # Lifetime in frames
        self.lifetime = 60  # 1 second at 60 FPS
        
    def update(self) -> None:
        """Update the projectile's position."""
        # Apply velocity
        self.pos_x += self.velocity_x
        self.pos_y += self.velocity_y
        
        # Update rect based on float position
        self.rect.x = round(self.pos_x)
        self.rect.y = round(self.pos_y)
        
        # Reduce lifetime
        self.lifetime -= 1
        
        # Fade out as it nears end of life
        if self.lifetime < 20:
            # Calculate fade factor (1.0 to 0.0)
            fade = self.lifetime / 20.0
            # Apply alpha
            self.image.set_alpha(int(255 * fade))
        
        # Remove projectile if lifetime ends or it goes off-screen
        screen = pygame.display.get_surface()
        screen_rect = screen.get_rect()
        if (self.lifetime <= 0 or not self.rect.colliderect(screen_rect)):
            self.kill()


class LaserBeam(pygame.sprite.Sprite):
    """Green laser beam attack that fires rapid green laser lines."""
    
    def __init__(self, player_pos: Tuple[int, int], charge_level: float, *groups) -> None:
        """Initialize a laser beam.
        
        Args:
            player_pos: Position of the player firing the beam
            charge_level: Charge level from 0.0 to 1.0
            groups: Sprite groups to add to
        """
        super().__init__(*groups)

        # Calculate beam dimensions
        screen_width = pygame.display.get_surface().get_width()
        beam_start_x = player_pos[0] + 20  # Start a bit in front of player
        beam_length = screen_width - beam_start_x
        
        # Laser line properties based on charge level
        min_height = 3
        max_height = 15
        self.laser_height = min_height + int((max_height - min_height) * charge_level)
        
        # Number of laser lines based on charge level - more lines for more impressive effect
        min_lines = 5
        max_lines = 15
        self.num_laser_lines = min_lines + int((max_lines - min_lines) * charge_level)
        
        # Spacing between laser lines - tighter spacing for higher charge
        self.spacing = max(2, int(15 * (1 - charge_level) + 3))
        
        # Create beam surface - add extra padding for glow effects
        padding = 30
        max_beam_height = self.laser_height * self.num_laser_lines + self.spacing * (self.num_laser_lines - 1) + padding * 2
        self.image = pygame.Surface((beam_length, max_beam_height), pygame.SRCALPHA)
        
        # Bright green laser color
        base_color = (20, 200, 20)  # More saturated green base
        full_charge_color = (150, 255, 150)  # Brighter green
        
        self.r = base_color[0] + int((full_charge_color[0] - base_color[0]) * charge_level)
        self.g = base_color[1] + int((full_charge_color[1] - base_color[1]) * charge_level)
        self.b = base_color[2] + int((full_charge_color[2] - base_color[2]) * charge_level)
        
        # Animation variables
        self.pulse_offset = 0
        self.animation_offset = 0
        self.animation_speed = 0.8 + charge_level * 2.0  # Even faster with higher charge
        self.beam_length = beam_length
        self.padding = padding
        
        # Draw the initial laser lines
        self._draw_laser_lines()
        
        # Set up rect and mask
        self.rect = self.image.get_rect(midleft=(beam_start_x, player_pos[1]))
        self.mask = pygame.mask.from_surface(self.image)
        
        # Set lifetime based on charge level
        min_lifetime = 30
        max_lifetime = 60
        self.lifetime = min_lifetime + int((max_lifetime - min_lifetime) * charge_level)
        
        # Store damage value based on charge
        self.damage = 1 + int(charge_level * 3)  # 1-4 damage
        
        logger.debug(f"Created laser beam with charge {charge_level:.2f}, damage {self.damage}")
    
    def _draw_laser_lines(self) -> None:
        """Draw multiple pulsing laser lines with enhanced visual effects."""
        # Clear the surface
        self.image.fill((0, 0, 0, 0))
        
        # Calculate vertical center of the beam
        total_height = self.image.get_height()
        center_y = total_height // 2
        
        # Calculate starting y-position for first laser line
        start_y = center_y - (self.num_laser_lines * self.laser_height + 
                             (self.num_laser_lines - 1) * self.spacing) // 2
        
        # Add a global pulsing glow effect
        glow_surf = pygame.Surface((self.beam_length, total_height), pygame.SRCALPHA)
        glow_alpha = 30 + int(20 * math.sin(self.animation_offset * 0.5))
        glow_color = (self.r//3, self.g//2, self.r//3, glow_alpha)
        glow_surf.fill(glow_color)
        self.image.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        
        # Draw each laser line
        for i in range(self.num_laser_lines):
            # Y position for this line
            y_pos = start_y + i * (self.laser_height + self.spacing)
            
            # Phase shift for this line to create wave effect
            phase_shift = i * 0.7
            
            # Length modulation for wave-like effect
            length_mod = 0.85 + 0.15 * math.sin(self.animation_offset + phase_shift)
            line_length = int(self.beam_length * length_mod)
            
            # Brightness modulation
            brightness_mod = 0.8 + 0.2 * math.sin(self.animation_offset * 2.0 + phase_shift)
            r = int(self.r * brightness_mod)
            g = int(self.g * brightness_mod)
            b = int(self.b * brightness_mod)
            
            # Draw the laser line - core
            pygame.draw.rect(
                self.image,
                (r, g, b),
                (0, y_pos, line_length, self.laser_height)
            )
            
            # Taper the end of each line for a more laser-like look
            taper_length = min(80, int(line_length * 0.2))
            for x in range(line_length - taper_length, line_length):
                # Calculate fade based on position
                fade = 1.0 - ((x - (line_length - taper_length)) / taper_length)
                # Apply alpha based on fade
                alpha = int(255 * fade)
                # Mix in a white color at the tip for a more energized look
                taper_r = int(r + (255 - r) * (1 - fade))
                taper_g = int(g + (255 - g) * (1 - fade))
                taper_b = int(b + (255 - b) * (1 - fade))
                
                pygame.draw.line(
                    self.image,
                    (taper_r, taper_g, taper_b, alpha),
                    (x, y_pos),
                    (x, y_pos + self.laser_height),
                    1
                )
            
            # Add glow effect with larger width for better visibility
            glow_height = self.laser_height * 4
            glow_surf = pygame.Surface((line_length, glow_height), pygame.SRCALPHA)
            
            # Add a brighter inner glow
            for y in range(glow_height):
                # Distance from center of glow
                dist = abs(y - glow_height/2) / (glow_height/2)
                # Alpha based on distance (falloff) - stronger glow
                alpha = max(0, int(220 * (1 - dist**1.5) * brightness_mod))
                # Only draw if visible
                if alpha > 0:
                    pygame.draw.line(
                        glow_surf, 
                        (min(255, r+50), min(255, g+50), min(255, b+50), alpha),
                        (0, y), 
                        (line_length, y)
                    )
            
            # Draw random energy particles along the beam for added effect
            for _ in range(5):
                if random.random() < 0.7:
                    particle_x = random.randint(0, line_length - 20)
                    particle_y = random.randint(0, glow_height-1)
                    particle_size = random.randint(2, 5)
                    particle_alpha = random.randint(150, 230)
                    pygame.draw.circle(
                        glow_surf,
                        (230, 255, 230, particle_alpha),
                        (particle_x, particle_y),
                        particle_size
                    )
            
            # Blit glow (centered on laser line)
            glow_y = y_pos - (glow_height - self.laser_height) // 2
            self.image.blit(glow_surf, (0, glow_y), special_flags=pygame.BLEND_RGBA_ADD)

    def update(self) -> None:
        """Update the beam's lifetime and animation."""
        # Reduce lifetime
        self.lifetime -= 1
        
        # Update animation
        self.animation_offset += self.animation_speed
        self.pulse_offset += 0.3
        
        # Redraw the laser lines with updated animation
        self._draw_laser_lines()
        
        # Fade out near end of life
        if self.lifetime < 15:
            alpha = int(255 * (self.lifetime / 15.0))
            self.image.set_alpha(alpha)
        
        # Remove when lifetime ends
        if self.lifetime <= 0:
            self.kill() 