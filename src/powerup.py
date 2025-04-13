"""Powerup system for the Starblitz Assault game."""

import math
import random
from enum import IntEnum, auto
from typing import Any, Dict, List, Optional, Tuple

import pygame

# Import config variables
from config.config import POWERUP_ALPHA, SCREEN_HEIGHT, SCREEN_WIDTH, SPRITES_DIR, POWERUP_GLOW_RATIO
from src.animated_sprite import AnimatedSprite
from src.logger import get_logger
from src.particle import ParticleSystem
from src.sprite_loader import load_sprite_sheet

# Get a logger for this module
logger = get_logger(__name__)


# Define PowerupType enum (moved from config/sprite_constants.py)
class PowerupType(IntEnum):
    """Maps powerup names to their sprite index in powerups.png (0-based)."""

    TRIPLE_SHOT = 0
    RAPID_FIRE = 1
    SHIELD = 2
    HOMING_MISSILES = 3
    POWER_RESTORE = 4  # Index shift: was 5
    SCATTER_BOMB = 5  # Index shift: was 6
    TIME_WARP = 6  # Index shift: was 7
    MEGA_BLAST = 7  # Index shift: was 8
    LASER_BEAM = 8  # New powerup type
    DRONE = 9  # Drone powerup - spawns a drone that shoots enemies


# Create a list of active powerup types for easy iteration/random selection
ACTIVE_POWERUP_TYPES = list(PowerupType)

# Constants for powerups
POWERUP_SCALE_FACTOR = 0.15  # Reduced even further to make powerups extremely small
POWERUP_ANIMATION_SPEED_MS = 120  # Animate slightly faster than player
POWERUP_FLOAT_SPEED = 1.0  # Base horizontal speed
POWERUP_DURATION = 10000  # 10 seconds for temporary powerups
POWERUP_BLINK_START = 8000  # When to start blinking (2 seconds before expiry)

# Powerup colors for different types
POWERUP_COLORS = {
    PowerupType.TRIPLE_SHOT: (255, 220, 0),  # Golden
    PowerupType.RAPID_FIRE: (0, 255, 255),  # Cyan
    PowerupType.SHIELD: (0, 100, 255),  # Blue
    PowerupType.HOMING_MISSILES: (255, 0, 255),  # Magenta
    PowerupType.POWER_RESTORE: (0, 255, 0),  # Green
    PowerupType.SCATTER_BOMB: (255, 128, 0),  # Orange
    PowerupType.TIME_WARP: (128, 0, 255),  # Purple
    PowerupType.MEGA_BLAST: (255, 0, 128),  # Pink
    PowerupType.LASER_BEAM: (20, 255, 100),  # Bright Green (for Laser)
    PowerupType.DRONE: (180, 180, 180),  # Light Grey (for Drone)
}


class PowerupParticle(pygame.sprite.Sprite):
    """Particle effect for powerups."""

    def __init__(
        self,
        position: Tuple[float, float],
        velocity: Tuple[float, float],
        color: Tuple[int, int, int],
        size: int,
        lifetime: int,
        gravity: float = 0.05,
        drag: float = 0.98,
        *groups,
    ) -> None:
        """Initialize a new particle.

        Args:
            position: Starting position (x, y)
            velocity: Initial velocity (vx, vy)
            color: RGB color tuple
            size: Particle size in pixels
            lifetime: How many frames the particle lives
            gravity: Downward acceleration per frame
            drag: Velocity multiplier per frame (0.98 = 2% slowdown)
            groups: Sprite groups to add to
        """
        super().__init__(*groups)
        self.pos_x, self.pos_y = position
        self.vel_x, self.vel_y = velocity
        self.color = color
        self.size = size
        self.initial_size = size
        self.lifetime = lifetime
        self.age = 0
        self.gravity = gravity
        self.drag = drag

        # Create the image with glow effect
        self._create_particle_image()

        self.rect = self.image.get_rect(center=(int(self.pos_x), int(self.pos_y)))

    def _create_particle_image(self):
        """Create particle image with glow effect."""
        # Create larger surface to accommodate glow
        glow_size = self.size * 3  # Increased glow size for better effect
        total_size = glow_size * 2

        self.image = pygame.Surface((total_size, total_size), pygame.SRCALPHA)

        # Inner core (full brightness)
        pygame.draw.circle(
            self.image,
            (*self.color, 255),  # Full alpha
            (total_size // 2, total_size // 2),
            self.size // 2,
        )

        # Middle glow
        pygame.draw.circle(
            self.image,
            (*self.color, 180),  # Increased alpha for better visibility
            (total_size // 2, total_size // 2),
            self.size,
        )

        # Outer glow (very faint)
        pygame.draw.circle(
            self.image,
            (*self.color, 100),  # Increased alpha for outer glow
            (total_size // 2, total_size // 2),
            glow_size,
        )

        # Add additional highlight for sparkle effect
        highlight_pos = (total_size // 2 - self.size // 3, total_size // 2 - self.size // 3)
        highlight_size = max(2, self.size // 4)
        pygame.draw.circle(
            self.image, (255, 255, 255, 200), highlight_pos, highlight_size  # White highlight
        )

    def update(self) -> None:
        """Update particle position and appearance."""
        self.age += 1
        if self.age >= self.lifetime:
            self.kill()
            return

        # Apply drag and gravity
        self.vel_x *= self.drag
        self.vel_y *= self.drag
        self.vel_y += self.gravity

        # Update position
        self.pos_x += self.vel_x
        self.pos_y += self.vel_y

        # Update rect
        self.rect.centerx = int(self.pos_x)
        self.rect.centery = int(self.pos_y)

        # Fade out as particle ages
        fade_factor = 1 - (self.age / self.lifetime)
        new_size = max(1, int(self.initial_size * fade_factor))

        if new_size != self.size or self.age % 5 == 0:  # Update less frequently for performance
            self.size = new_size
            # Recreate the image with new size
            self._create_particle_image()
            # Keep the same center position
            old_center = self.rect.center
            self.rect = self.image.get_rect(center=old_center)


class Powerup(AnimatedSprite):
    """Base class for all powerups."""

    def __init__(
        self,
        powerup_type: PowerupType,
        x: float,
        y: float,
        *groups,
        particles_group: Optional[pygame.sprite.Group] = None,
        game_ref=None,
    ) -> None:
        """Initialize a powerup.

        Args:
            powerup_type: Index of the powerup type (0-8)
            x: Initial x position
            y: Initial y position
            groups: Sprite groups to add to
            particles_group: Optional group for particle effects
            game_ref: Reference to the game instance
        """
        super().__init__(POWERUP_ANIMATION_SPEED_MS, *groups)

        # Store the type as Enum member
        self.powerup_type_enum = powerup_type
        self.powerup_type = int(powerup_type)  # Keep integer for indexing colors/etc.
        self.type_name = powerup_type.name  # Get name from Enum

        # Store game reference
        self.game_ref = game_ref

        # Get color for this powerup type
        self.color = POWERUP_COLORS.get(powerup_type, (255, 255, 255))

        # Create special effect surface instead of using sprite
        self.size = 20  # Base size for powerup
        self.glow_size = self.size * POWERUP_GLOW_RATIO
        self.image = self._create_special_effect_surface()

        # Setup rect and position
        self.rect = self.image.get_rect(center=(int(x), int(y)))
        self.mask = pygame.mask.from_surface(self.image)

        # Store a single frame for animation
        self.frames = [self.image]
        self.frame_index = 0

        # Position tracking for smoother movement
        self.pos_x = float(x)
        self.pos_y = float(y)

        # Create a position tuple for internal tracking
        self._position_x = float(x)
        self._position_y = float(y)

        # Movement parameters - straight movement like enemies
        self.speed_x = -POWERUP_FLOAT_SPEED * 0.75  # 75% of enemy speed
        self.speed_y = 0

        # Additional movement parameters for compatibility with all update methods
        self.move_speed = POWERUP_FLOAT_SPEED * 0.75
        self.move_speed_mod = 0

        # Particle effect parameters
        self.particles_group = particles_group
        self.particle_timer = 0
        self.particle_interval = 40  # Reduced interval for more frequent particles

        # Initialize last_particle_time to 0 to create particles immediately
        self.last_particle_time = 0

        # Initialize elapsed time for animations
        self.elapsed_time = 0

        # Animation parameters
        self.pulse_timer = 0

        # Pre-spawn some particles immediately
        if self.particles_group is not None:
            self._pre_spawn_initial_particles()

        logger.info(f"Created {self.type_name} powerup at ({x}, {y})")

    def _pre_spawn_initial_particles(self):
        """Spawn a small burst of particles when the powerup is created."""
        # Spawn a few particles slightly ahead and behind the starting position
        for _ in range(5):  # Spawn 5 initial particles
            # Vary starting position slightly around the powerup center
            offset_x = random.uniform(-10, 20) 
            offset_y = random.uniform(-10, 10)
            start_pos = (self.pos_x + offset_x, self.pos_y + offset_y)
            
            # Give them a small initial velocity mostly outwards
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, 1.5)
            vel = (math.cos(angle) * speed, math.sin(angle) * speed)
            
            size = random.randint(2, 5)
            lifetime = random.randint(20, 40)
            
            PowerupParticle(
                start_pos,
                vel,
                self.color,
                size,
                lifetime,
                0.02,
                0.96,
                self.particles_group,
            )

    def _create_special_effect_surface(self) -> pygame.Surface:
        """Create a special effect surface for the powerup."""
        total_size = int(self.glow_size * 2)
        surface = pygame.Surface((total_size, total_size), pygame.SRCALPHA)
        center = (total_size // 2, total_size // 2)

        # Base color from powerup type
        color = self.color

        # Get pulse factor if it exists, otherwise use default
        pulse_factor = getattr(self, "current_pulse_factor", 1.0)

        # Core glow - keep this stable (not affected by pulse)
        core_radius = max(3, self.size // 3)
        pygame.draw.circle(surface, (*color, 255), center, core_radius)  # Full alpha

        # Middle glow layer - subtle pulse
        middle_radius = int(self.size * (0.9 + 0.1 * pulse_factor))
        pygame.draw.circle(surface, (*color, 180), center, middle_radius)

        # Outer glow layer - more noticeable pulse
        outer_radius = int(self.glow_size * pulse_factor)
        pygame.draw.circle(surface, (*color, 100), center, outer_radius)

        # Add unique effects based on powerup type
        if self.powerup_type == PowerupType.TRIPLE_SHOT:
            # Triple golden rays
            for angle in range(0, 360, 120):
                self._draw_ray(surface, center, angle, color, self.size * 1.2)

        elif self.powerup_type == PowerupType.RAPID_FIRE:
            # Lightning-like sparks - use predefined angles instead of random angles
            preset_angles = [0, 45, 90, 135, 180, 225, 270, 315]
            for angle in preset_angles:
                # Use a fixed pattern length based on powerup size
                length = self.size * (1.0 + (angle % 90) / 180)
                self._draw_lightning(surface, center, angle, color, length)

        elif self.powerup_type == PowerupType.SHIELD:
            # Shield ring - stable size with pulse opacity
            shield_radius = int(self.size * 1.3)
            shield_alpha = int(180 + 40 * pulse_factor)  # Pulse opacity instead of size
            pygame.draw.circle(
                surface,
                (*color, shield_alpha),
                center,
                shield_radius,
                max(2, int(self.size // 6)),  # Thickness
            )

        elif self.powerup_type == PowerupType.HOMING_MISSILES:
            # Target-like pattern - fixed sizes
            circle_sizes = [
                int(self.size * 0.5),
                int(self.size * 0.8),
                int(self.size * 1.1),
                int(self.size * 1.4),
            ]
            line_width = max(1, int(self.size // 10))

            # Draw each circle at a fixed size
            for i, radius in enumerate(circle_sizes):
                if radius > 0:  # Ensure we don't draw 0-radius circles
                    # Alternate the pulse effect on different rings
                    ring_alpha = 150
                    if i % 2 == 0:  # Even circles pulse in opacity
                        ring_alpha = int(130 + 40 * pulse_factor)

                    pygame.draw.circle(surface, (*color, ring_alpha), center, radius, line_width)

        elif self.powerup_type == PowerupType.POWER_RESTORE:
            # Healing cross - stable size
            width = max(2, int(self.size // 4))
            length = int(self.size * 1.2)
            # Vertical line
            pygame.draw.rect(
                surface,
                (*color, 220),
                (center[0] - width // 2, center[1] - length // 2, width, length),
            )
            # Horizontal line
            pygame.draw.rect(
                surface,
                (*color, 220),
                (center[0] - length // 2, center[1] - width // 2, length, width),
            )

        elif self.powerup_type == PowerupType.SCATTER_BOMB:
            # Explosion-like pattern - fixed angles
            for i in range(8):
                angle = i * 45  # Even distribution
                # Vary ray length slightly with pulse
                ray_length = self.size * (1.2 + 0.1 * pulse_factor)
                self._draw_explosion_ray(surface, center, angle, color, ray_length)

        elif self.powerup_type == PowerupType.TIME_WARP:
            # Clock-like pattern
            # Draw clock face - fixed size
            clock_radius = int(self.size * 1.2)
            pygame.draw.circle(
                surface, (*color, 180), center, clock_radius, max(1, int(self.size // 8))
            )

            # Use current rotation angle for hands
            hand_length = self.size * 0.8
            current_rotation = getattr(self, "rotation_angle", 0)

            # Hour hand (shorter)
            hour_angle = math.radians(current_rotation)
            hour_end_x = center[0] + int(math.cos(hour_angle) * hand_length * 0.6)
            hour_end_y = center[1] + int(math.sin(hour_angle) * hand_length * 0.6)
            pygame.draw.line(
                surface,
                (*color, 230),
                center,
                (hour_end_x, hour_end_y),
                max(1, int(self.size // 6)),
            )

            # Minute hand (longer)
            minute_angle = math.radians((current_rotation * 12) % 360)  # 12x faster
            minute_end_x = center[0] + int(math.cos(minute_angle) * hand_length)
            minute_end_y = center[1] + int(math.sin(minute_angle) * hand_length)
            pygame.draw.line(
                surface,
                (*color, 230),
                center,
                (minute_end_x, minute_end_y),
                max(1, int(self.size // 10)),
            )

        elif self.powerup_type == PowerupType.MEGA_BLAST:
            # Star-burst pattern - even distribution
            for i in range(8):
                angle = i * 45  # Even distribution
                # Vary ray length slightly with pulse
                ray_length = self.size * (1.4 + 0.1 * pulse_factor)
                self._draw_star_ray(surface, center, angle, color, ray_length)

        # Add highlight for sparkle effect - fixed position
        highlight_pos = (center[0] - self.size // 3, center[1] - self.size // 3)
        highlight_size = max(2, self.size // 4)
        pygame.draw.circle(
            surface, (255, 255, 255, 200), highlight_pos, highlight_size  # White highlight
        )

        return surface

    def _draw_ray(self, surface, center, angle, color, length):
        """Draw a ray emanating from the center."""
        rad_angle = math.radians(angle)
        end_x = center[0] + int(math.cos(rad_angle) * length)
        end_y = center[1] + int(math.sin(rad_angle) * length)
        width = max(2, int(self.size // 5))

        pygame.draw.line(surface, (*color, 200), center, (end_x, end_y), width)

        # Add a glow at the end of the ray
        pygame.draw.circle(surface, (*color, 150), (end_x, end_y), width)

    def _draw_lightning(self, surface, center, angle, color, length):
        """Draw a lightning-like zigzag from the center."""
        rad_angle = math.radians(angle)
        current_x, current_y = center

        # Use a fixed seed based on angle and powerup type for consistency
        # This prevents random flickering while still looking random
        # Avoid using pos_x/pos_y since they might not be set during initialization
        try:
            seed = int(
                (getattr(self, "pos_x", 0) * 100)
                + getattr(self, "pos_y", 0)
                + self.powerup_type * 1000
                + angle * 10
            )
        except:
            # Fallback if anything goes wrong with the calculation
            seed = int(angle * 100) + self.powerup_type * 1000 + 42

        local_random = random.Random(seed)

        segments = local_random.randint(3, 5)
        segment_length = length / segments
        width = max(1, int(self.size // 8))

        for i in range(segments):
            # Randomize the angle slightly for each segment (but using seeded random)
            segment_angle = rad_angle + math.radians(local_random.uniform(-30, 30))
            next_x = current_x + math.cos(segment_angle) * segment_length
            next_y = current_y + math.sin(segment_angle) * segment_length

            # Draw the segment
            pygame.draw.line(
                surface,
                (*color, 220 - (40 * i)),  # Fade out towards the end
                (int(current_x), int(current_y)),
                (int(next_x), int(next_y)),
                width,
            )

            current_x, current_y = next_x, next_y

    def _draw_explosion_ray(self, surface, center, angle, color, length):
        """Draw an explosion-like ray from center."""
        rad_angle = math.radians(angle)
        end_x = center[0] + int(math.cos(rad_angle) * length)
        end_y = center[1] + int(math.sin(rad_angle) * length)
        width = max(2, int(self.size // 6))

        # Draw main ray
        pygame.draw.line(surface, (*color, 200), center, (end_x, end_y), width)

        # Use a fixed seed for consistent random effects
        # Use a simple calculation that's safe even during initialization
        seed = int(angle * 100 + self.powerup_type * 1000)
        local_random = random.Random(seed)

        # Add smaller rays at the end
        for i in range(2):
            branch_angle = rad_angle + math.radians(local_random.uniform(-45, 45))
            branch_length = length * local_random.uniform(0.3, 0.5)
            branch_end_x = end_x + int(math.cos(branch_angle) * branch_length)
            branch_end_y = end_y + int(math.sin(branch_angle) * branch_length)

            pygame.draw.line(
                surface,
                (*color, 150),
                (end_x, end_y),
                (branch_end_x, branch_end_y),
                max(1, width // 2),
            )

    def _draw_star_ray(self, surface, center, angle, color, length):
        """Draw a star-like ray from center."""
        rad_angle = math.radians(angle)

        # Main ray
        end_x = center[0] + int(math.cos(rad_angle) * length)
        end_y = center[1] + int(math.sin(rad_angle) * length)
        width = max(2, int(self.size // 5))

        # Draw thicker line with gradient effect
        steps = 3
        for i in range(steps):
            step_width = max(1, width * (steps - i) // steps)
            step_alpha = 255 - (i * 50)
            pygame.draw.line(surface, (*color, step_alpha), center, (end_x, end_y), step_width)

        # Add glow at the tip
        pygame.draw.circle(surface, (*color, 180), (end_x, end_y), width * 1.5)

    @property
    def position(self) -> Tuple[float, float]:
        """Return the powerup's current position."""
        return (self.pos_x, self.pos_y)

    def update(self) -> None:
        """Update powerup position and appearance."""
        # Call parent update for animation
        super().update()

        # Update position
        self.pos_x += self.speed_x
        self.pos_y += self.speed_y
        self.rect.centerx = int(self.pos_x)
        self.rect.centery = int(self.pos_y)

        # Update internal position tracking
        self._position_x = self.pos_x
        self._position_y = self.pos_y

        # Get current time for consistent animation
        current_time = pygame.time.get_ticks()

        # Very slow, smooth pulse effect using time-based animation
        # This creates a gentle "breathing" effect instead of vibration
        pulse_period = 3000  # 3 seconds for a complete pulse cycle (slower)
        pulse_progress = (current_time % pulse_period) / pulse_period

        # Use sine wave for smooth transition (0.9-1.1 range - more subtle)
        pulse_factor = 0.9 + 0.2 * (0.5 + 0.5 * math.sin(pulse_progress * math.pi * 2))

        # Store for use in drawing
        self.current_pulse_factor = pulse_factor

        # Smooth rotation using time
        if self.powerup_type_enum == PowerupType.TIME_WARP:
            # Faster rotation for time warp
            rotation_period = 4000  # 4 seconds per rotation (slower)
        else:
            rotation_period = 7000  # 7 seconds per rotation (much slower)

        rotation_progress = (current_time % rotation_period) / rotation_period
        self.rotation_angle = rotation_progress * 360  # 0-360 degrees

        # Only update visual occasionally - less frequent updates for stability
        visual_update_interval = 16  # ms between visual updates (longer interval)
        if (
            not hasattr(self, "last_visual_update")
            or current_time - self.last_visual_update >= visual_update_interval
        ):

            self.last_visual_update = current_time

            # Store current center for position preservation
            old_center = self.rect.center

            # Use fixed base sizes instead of pulsing the core size
            # This keeps the main shape stable while only the glow breathes
            self.size = 20  # Fixed base size
            self.glow_size = self.size * POWERUP_GLOW_RATIO  # Size controlled by config

            # Create new surface with current pulse factor
            self.image = self._create_special_effect_surface()

            # Store as original for rotation
            self.original_image = self.image.copy()

            # Handle rotation - always rotate for smooth animation
            if self.powerup_type_enum not in [PowerupType.SHIELD, PowerupType.POWER_RESTORE]:
                # Rotate the stored original image
                self.image = pygame.transform.rotate(self.original_image, self.rotation_angle)

            # Restore position
            self.rect = self.image.get_rect(center=old_center)
            self.mask = pygame.mask.from_surface(self.image)

        # Create trail particles at intervals
        if self.particles_group and current_time - self.last_particle_time > self.particle_interval:
            self._create_trail_particles()
            self.last_particle_time = current_time

        # Remove if off screen
        if self.rect.right < 0:
            self.kill()

    def _create_trail_particles(self) -> None:
        """Create trailing particles behind the powerup."""
        if not self.particles_group:
            return

        # Get color for this powerup
        color = self.color

        # Create more particles (3-5) at and around the powerup
        for _ in range(random.randint(3, 5)):
            # Position randomly around the powerup, not just behind
            position = (
                self.rect.centerx + random.randint(-self.rect.width // 3, self.rect.width // 3),
                self.rect.centery + random.randint(-self.rect.height // 3, self.rect.height // 3),
            )

            # Random velocity - particles spread in all directions
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(0.5, 2.0)
            vel_x = math.cos(angle) * speed
            vel_y = math.sin(angle) * speed

            # Larger particles with longer lifetime
            size = random.randint(3, 6)  # Increased size
            lifetime = random.randint(15, 30)  # Longer lifetime

            # Create particle
            PowerupParticle(
                position, (vel_x, vel_y), color, size, lifetime, 0.01, 0.95, self.particles_group
            )

        # Also create a "wake" of smaller particles behind the powerup
        for _ in range(2):
            wake_pos = (
                self.rect.right + random.randint(-3, 3),
                self.rect.centery + random.randint(-8, 8),
            )

            # Mostly trailing behind
            vel_x = random.uniform(0.8, 1.8)  # Slightly faster
            vel_y = random.uniform(-0.4, 0.4)  # Slight vertical spread

            # Smaller but still visible
            size = random.randint(2, 4)
            lifetime = random.randint(10, 20)

            # Create particle
            PowerupParticle(
                wake_pos, (vel_x, vel_y), color, size, lifetime, 0.01, 0.92, self.particles_group
            )

    def apply_effect(self, player) -> None:
        """Apply the powerup effect to the player.

        This method should be overridden by subclasses.
        """
        logger.info(f"Collected {self.type_name} powerup")

        # Base implementation doesn't modify power level
        # Power level restoration happens only in PowerRestorePowerup

    def _create_collection_effect(self, position: Tuple[int, int]) -> None:
        """Create a visual effect when powerup is collected."""
        if not self.particles_group:
            return

        # Get color for this powerup
        color = self.color

        # Create a burst of particles
        for _ in range(30):  # Increased for more dramatic effect
            # Random angle and speed
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.0, 4.0)  # Increased speed

            vel_x = math.cos(angle) * speed
            vel_y = math.sin(angle) * speed

            # Random size and lifetime
            size = random.randint(3, 8)
            lifetime = random.randint(40, 80)  # Longer lifetime

            # Create particle
            PowerupParticle(
                position, (vel_x, vel_y), color, size, lifetime, 0.03, 0.96, self.particles_group
            )
