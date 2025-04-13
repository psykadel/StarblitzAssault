"""Projectile classes for the game."""

import math
import os  # For file path handling
import random
from typing import List, Optional, Tuple

import pygame

from config.config import BULLET_SIZE, BULLET_SPEED
from src.logger import get_logger

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
            BULLET_SIZE[0] // 2,
        )

        # Add a subtle glow effect
        glow_size = (BULLET_SIZE[0] + 4, BULLET_SIZE[1] + 4)
        glow_surface = pygame.Surface(glow_size, pygame.SRCALPHA)
        pygame.draw.circle(
            glow_surface,
            (240, 240, 255, 128),  # Semi-transparent white/blue
            (glow_size[0] // 2, glow_size[1] // 2),
            glow_size[0] // 2,
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
        if hasattr(self, "pulse_time"):
            self.pulse_time += self.pulse_speed

            # Update the appearance of the missile to create a pulsing effect
            if random.random() < 0.2:  # Occasionally update appearance
                # Get current missile size
                if hasattr(self, "original_size"):
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
                    (new_size - 2, new_size // 2),  # Tip
                    (0, new_size // 4),  # Bottom left
                    (0, 3 * new_size // 4),  # Top left
                ]
                pygame.draw.polygon(self.image, (255, 50, 50), points)  # Bright red

                # Add yellow tip
                pygame.draw.circle(
                    self.image,
                    (255, 255, 0),  # Bright yellow
                    (new_size - 5, new_size // 2),
                    new_size // 4,
                )

                # Add engine glow
                glow_points = [
                    (0, new_size // 3),  # Top
                    (0, 2 * new_size // 3),  # Bottom
                    (-new_size // 1.5, new_size // 2),  # Left tip
                ]
                pygame.draw.polygon(
                    self.image, (255, 200, 0, 230), glow_points  # More solid orange-yellow glow
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
            (size - 2, size // 2),  # Tip
            (0, size // 4),  # Bottom left
            (0, 3 * size // 4),  # Top left
        ]
        pygame.draw.polygon(self.image, (255, 50, 50), points)  # Brighter red

        # Add yellow tip to make it more visible
        pygame.draw.circle(
            self.image, (255, 255, 0), (size - 5, size // 2), size // 4  # Bright yellow
        )

        # Add larger, more obvious engine glow
        glow_points = [
            (0, size // 3),  # Top
            (0, 2 * size // 3),  # Bottom
            (-size // 1.5, size // 2),  # Left tip - extend further
        ]
        pygame.draw.polygon(
            self.image, (255, 200, 0, 230), glow_points  # More solid orange-yellow glow
        )

        # Add pulsing effect variables
        self.pulse_time = 0
        self.pulse_speed = 0.2

        # Update rect and mask
        old_center = self.rect.center
        self.rect = self.image.get_rect(center=old_center)
        self.mask = pygame.mask.from_surface(self.image)

        # Log that a homing missile was created
        logger.info(
            f"Created homing missile targeting enemy at {target.rect.center if target else 'unknown'}"
        )


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
        size = (BULLET_SIZE[0] * 3, BULLET_SIZE[1] * 3)
        self.image = pygame.Surface(size, pygame.SRCALPHA)

        # Draw the projectile as a yellow-orange circle
        pygame.draw.circle(
            self.image,
            random.choice([(255, 100, 0), (255, 200, 0), (255, 50, 0), (255, 150, 50)]),  # Yellow-orange color
            (size[0] // 2, size[1] // 2),
            size[0] // 2,
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
        self.lifetime = 90  # 1 second at 60 FPS

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
        if self.lifetime <= 0 or not self.rect.colliderect(screen_rect):
            self.kill()


class LaserBeam(pygame.sprite.Sprite):
    """Green laser beam attack that clearly emanates from the player ship."""

    def __init__(self, player_pos: Tuple[int, int], charge_level: float, *groups) -> None:
        """Initialize a laser beam."""
        super().__init__(*groups)

        # Ensure charge level is non-negative before calculations
        charge_level = max(0.0, charge_level)

        # Calculate beam dimensions with offset to start in front of ship
        ship_width_estimate = 50  # Estimated width of player ship
        beam_start_x = player_pos[0] + ship_width_estimate//2  # Start from front of ship
        screen_width = pygame.display.get_surface().get_width()
        beam_length = screen_width - beam_start_x

        # --- Safety Check for beam_length ---
        if beam_length <= 0:
            logger.warning(f"Laser beam started at or beyond screen edge ({beam_start_x=}). Setting length to 1.")
            beam_length = 1
        # --- End Safety Check ---

        # Create a taller surface to accommodate particle effects
        padding = 40  # Increased to allow for wider particle spread
        # Create a thin beam with particle effects
        thin_beam_height = max(1, 4 + int(2 * charge_level))  # Much thinner core beam
        surface_height = thin_beam_height + padding * 2
        
        # Ensure surface dimensions are valid before creating
        if beam_length > 0 and surface_height > 0:
            self.image = pygame.Surface((beam_length, surface_height), pygame.SRCALPHA)
        else:
            # Create a minimal 1x1 surface if dimensions are invalid
            logger.error(f"Invalid dimensions for LaserBeam surface: ({beam_length=}, {surface_height=}). Creating 1x1 surface.")
            self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
            beam_length = 1 # Adjust beam_length to match minimal surface
            thin_beam_height = 1 # Adjust beam_height

        # Store dimensions
        self.beam_length = beam_length
        self.beam_height = thin_beam_height
        self.center_y = surface_height // 2
        self.player_pos = player_pos
        self.surface_height = surface_height
        self.beam_start_x = beam_start_x  # Store the actual start position

        # Animation variables
        self.pulse_time = 0
        self.flow_offset = 0
        self.flow_speed = 2.0 + charge_level * 2.0
        
        # Fade-in animation variables
        self.is_fading_in = True
        self.fade_in_progress = 0.0  # 0.0 to 1.0
        self.fade_in_speed = 0.15    # How quickly the beam extends
        
        # Particle effect variables
        self.particles = []
        self.particle_spawn_rate = int(3 + charge_level * 1.5)  # Further reduced spawn rate
        self.max_particles = 80  # Further reduced max particles
        self.particle_size_range = (1, 3)  # Smaller max size
        self.particle_speed_range = (3, 7)
        self.particle_spread = int(6 + charge_level * 4)  # Further reduced spread

        # Only update visuals every other frame to improve performance
        self.update_frame = True

        # Color cycling for beam and particles
        self.color_phase = 0
        self.color_shift = random.uniform(0, 2 * math.pi)
        
        # Set up rect and mask - Position from the front of the ship
        self.rect = self.image.get_rect(midleft=(beam_start_x, player_pos[1]))

        # Draw initial beam
        self._draw_beam()

        # Create mask from image (important for collision detection)
        self.mask = pygame.mask.from_surface(self.image)

        # Set lifetime and damage
        self.lifetime = 30 + int(15 * charge_level)
        self.damage = 2 + int(charge_level * 4)

        logger.debug(f"Created particle laser beam with charge {charge_level:.2f}")

    def _get_particle_color(self, distance_ratio, size_ratio):
        """Get dynamic color for particles based on position and size."""
        # This method is optimized out in favor of inline color calculations
        # Keep it for compatibility but it's no longer used
        cycle = 0.5 + 0.5 * math.sin(self.color_phase + self.color_shift)
        
        r = int(40 + 80 * cycle)
        g = min(255, int(200 + 55 * (1 - distance_ratio * 0.5)))
        b = int(50 + 80 * cycle * (1 - distance_ratio))
        alpha = max(30, min(200, int(180 * (1 - distance_ratio * 0.3))))
        
        return (r, g, b, alpha)

    def _spawn_particles(self):
        """Create new particles across the entire beam."""
        # Only spawn if we haven't exceeded max particles
        if len(self.particles) >= self.max_particles:
            return
            
        center_y = self.center_y
        
        # Determine visible beam length during fade-in
        visible_length = self.beam_length
        if self.is_fading_in:
            visible_length = int(self.beam_length * self.fade_in_progress)
            
        # Skip if beam isn't visible yet
        if visible_length <= 0:
            return
        
        # Spawn particles throughout the beam
        for _ in range(self.particle_spawn_rate):
            if len(self.particles) >= self.max_particles:
                break
                
            # Randomize particle properties
            size = random.uniform(self.particle_size_range[0], self.particle_size_range[1])
            speed = random.uniform(self.particle_speed_range[0], self.particle_speed_range[1])
            
            # Position particles anywhere along the visible beam
            x_pos = random.uniform(0, visible_length)
            y_offset = random.uniform(-self.particle_spread, self.particle_spread)
            
            # Shorter lifespan for particles that start further along the beam
            max_lifespan = 60 - int(45 * (x_pos / self.beam_length))
            lifespan = random.randint(10, max(10, max_lifespan))
            
            # Create new particle
            particle = {
                'x': x_pos,
                'y': center_y + y_offset,
                'size': size,
                'speed': speed,
                'y_drift': random.uniform(-0.5, 0.5),  # Slow vertical drift
                'lifespan': lifespan,
                'pulse_offset': random.uniform(0, 2 * math.pi),  # Random pulse phase
                'oscillation': random.uniform(0.2, 1.0)  # Random oscillation amplitude
            }
            
            self.particles.append(particle)

    def _update_particles(self):
        """Update all particles' positions and properties."""
        # Update color animation
        self.color_phase += 0.08
        
        # Update particles
        for particle in self.particles[:]:  # Use a copy to safely remove during iteration
            # Move particle
            particle['x'] += particle['speed']
            
            # Add oscillating vertical movement
            y_oscil = math.sin(self.pulse_time * 0.3 + particle['pulse_offset']) * particle['oscillation'] * self.particle_spread * 0.3
            particle['y'] += particle['y_drift'] + y_oscil
            
            # Reduce lifespan
            particle['lifespan'] -= 1
            
            # Remove if expired or out of bounds
            if particle['lifespan'] <= 0 or particle['x'] >= self.beam_length:
                self.particles.remove(particle)

    def _draw_beam(self):
        """Draw the thin central beam and particle effects."""
        # Ensure beam_length is positive before proceeding with drawing calculations that depend on it
        if self.beam_length <= 0:
            # Should not happen due to __init__ checks, but as a failsafe:
            logger.warning("Attempted to draw beam with non-positive length in _draw_beam.")
            return

        # Clear surface
        self.image.fill((0, 0, 0, 0))

        center_y = self.center_y
        
        # Update fade-in animation
        if self.is_fading_in:
            self.fade_in_progress = min(1.0, self.fade_in_progress + self.fade_in_speed)
            if self.fade_in_progress >= 1.0:
                self.is_fading_in = False
        
        # Determine visible beam length
        visible_length = self.beam_length
        if self.is_fading_in:
            visible_length = int(self.beam_length * self.fade_in_progress)
        
        # Only update particles every other frame to improve performance
        self.update_frame = not self.update_frame
        if self.update_frame:
            # Spawn new particles
            self._spawn_particles()
            
            # Update existing particles
            self._update_particles()

        # Draw the thin central beam - only if we have visible length
        if visible_length > 0:
            core_height = max(1, self.beam_height)
            core_top = center_y - core_height // 2
            
            # Create a slightly transparent core beam
            beam_color = (30, 240, 70, 160)  # Bright green, semi-transparent
            pygame.draw.rect(
                self.image,
                beam_color,
                (0, core_top, visible_length, core_height)
            )
        
        # Add subtle pulsing effect, but calculate less frequently
        self.pulse_time += 0.1
        pulse = 0.8 + 0.2 * math.sin(self.pulse_time * 0.5)
        
        # Add a single source point ball instead of multiple circles
        ball_radius = 6
        ball_color = (120, 255, 120, 200)
        pygame.draw.circle(
            self.image,
            ball_color,
            (0, center_y),
            ball_radius
        )
            
        # Draw all particles
        for particle in self.particles:
            # Only draw particles within the visible beam length during fade-in
            if self.is_fading_in and particle['x'] > visible_length:
                continue
                
            # Calculate distance ratio from source (0 at source, 1 at end)
            distance_ratio = particle['x'] / self.beam_length
            size_ratio = (particle['size'] - self.particle_size_range[0]) / (self.particle_size_range[1] - self.particle_size_range[0])
            
            # Get dynamic color based on distance and size - simpler calculation
            # Use cached color phase calculation rather than recalculating for each particle
            cycle = 0.5 + 0.5 * math.sin(self.color_phase + self.color_shift)
            
            # Simplified color calculation - fewer branches and calculations
            r = int(40 + 80 * cycle)
            g = min(255, int(200 + 55 * (1 - distance_ratio * 0.5)))
            b = int(50 + 80 * cycle * (1 - distance_ratio))
            alpha = max(30, min(200, int(180 * (1 - distance_ratio * 0.3))))
            
            color = (r, g, b, alpha)
            
            # Draw the particle - with smaller max size
            x, y = int(particle['x']), int(particle['y'])
            size = max(1, particle['size'])  # Simplified size calculation
            
            pygame.draw.circle(
                self.image,
                color,
                (x, y),
                size
            )
        
        # Add occasional energy bursts, but less frequently
        if random.random() < 0.1:  # Reduced from 0.2 to 0.1 (50% reduction)
            # Only create bursts within visible beam
            burst_x = random.randint(0, min(int(visible_length * 0.9), 300)) if visible_length > 0 else 0
            burst_y = center_y + random.randint(-self.particle_spread // 2, self.particle_spread // 2)
            burst_radius = random.randint(2, 6)  # Smaller burst radius
            burst_alpha = random.randint(40, 100)
            
            # Draw energy burst
            pygame.draw.circle(
                self.image,
                (180, 255, 100, burst_alpha),
                (burst_x, burst_y),
                burst_radius
            )
        
        # If beam is still fading in, create a leading edge effect
        if self.is_fading_in and visible_length > 0:
            # Create a bright leading edge glow (with circular glow instead of vertical lines)
            edge_x = visible_length - 5
            
            # Use a single, simplified glow at the leading edge
            pygame.draw.circle(
                self.image,
                (180, 255, 150, 120),
                (edge_x, center_y),
                self.particle_spread // 2
            )

        # Don't update mask every frame - only update when particles are updated
        if self.update_frame:
            # Update mask for accurate collision detection
            self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        """Update the beam animation and lifetime."""
        # Reduce lifetime
        self.lifetime -= 1

        # Redraw with updated animation
        self._draw_beam()
        
        # Fade out at end of life
        if self.lifetime < 10:
            alpha = int(255 * (self.lifetime / 10.0))
            self.image.set_alpha(alpha)

        # Remove when expired
        if self.lifetime <= 0:
            self.kill()
