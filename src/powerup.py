"""Powerup system for the Starblitz Assault game."""

import pygame
import math
import random
from enum import IntEnum, auto
from typing import Optional, Tuple, List, Dict, Any

from src.animated_sprite import AnimatedSprite
from src.sprite_loader import load_sprite_sheet
from src.particle import ParticleSystem
from src.logger import get_logger

# Import config variables
from config.config import (
    SPRITES_DIR, SCREEN_WIDTH, SCREEN_HEIGHT
)

# Get a logger for this module
logger = get_logger(__name__)

# Define PowerupType enum (moved from config/sprite_constants.py)
class PowerupType(IntEnum):
    """Maps powerup names to their sprite index in powerups.png (0-based)."""
    TRIPLE_SHOT = 0
    RAPID_FIRE = 1
    SHIELD = 2
    HOMING_MISSILES = 3
    POWER_RESTORE = 4 # Index shift: was 5
    SCATTER_BOMB = 5  # Index shift: was 6
    TIME_WARP = 6     # Index shift: was 7
    MEGA_BLAST = 7    # Index shift: was 8

# Create a list of active powerup types for easy iteration/random selection
ACTIVE_POWERUP_TYPES = list(PowerupType)

# Constants for powerups
POWERUP_SCALE_FACTOR = 0.15  # Reduced even further to make powerups extremely small
POWERUP_ANIMATION_SPEED_MS = 120  # Animate slightly faster than player
POWERUP_FLOAT_SPEED = 1.0  # Base horizontal speed
POWERUP_DURATION = 10000  # 10 seconds for temporary powerups
POWERUP_BLINK_START = 8000  # When to start blinking (2 seconds before expiry)

# Powerup types list is now effectively defined by PowerupType Enum
# POWERUP_TYPES = [...]

class PowerupParticle(pygame.sprite.Sprite):
    """Particle effect for powerups."""
    
    def __init__(self, position: Tuple[float, float],
                 velocity: Tuple[float, float],
                 color: Tuple[int, int, int],
                 size: int, lifetime: int,
                 gravity: float = 0.05,
                 drag: float = 0.98,
                 *groups) -> None:
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
        glow_size = self.size * 2
        total_size = glow_size * 2
        
        self.image = pygame.Surface((total_size, total_size), pygame.SRCALPHA)
        
        # Inner core (full brightness)
        pygame.draw.circle(
            self.image,
            (*self.color, 255),  # Full alpha
            (total_size // 2, total_size // 2),
            self.size // 2
        )
        
        # Middle glow
        pygame.draw.circle(
            self.image,
            (*self.color, 150),  # Medium alpha
            (total_size // 2, total_size // 2),
            self.size
        )
        
        # Outer glow (very faint)
        pygame.draw.circle(
            self.image,
            (*self.color, 75),  # Low alpha
            (total_size // 2, total_size // 2),
            glow_size
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
        
        if new_size != self.size:
            self.size = new_size
            # Recreate the image with new size
            self._create_particle_image()
            # Keep the same center position
            old_center = self.rect.center
            self.rect = self.image.get_rect(center=old_center)

class Powerup(AnimatedSprite):
    """Base class for all powerups."""
    
    def __init__(self, powerup_type: PowerupType, x: float, y: float, 
                 *groups, particles_group: Optional[pygame.sprite.Group] = None,
                 game_ref = None) -> None:
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
        self.powerup_type = int(powerup_type) # Keep integer for indexing colors/etc.
        self.type_name = powerup_type.name # Get name from Enum
        
        # Store game reference
        self.game_ref = game_ref
        
        # Load animation frames (will load all frames initially)
        all_available_frames = self._load_powerup_frames(powerup_type)
        
        # Select the specific frame for this powerup type
        # Ensure the index is valid
        if self.powerup_type < 0 or self.powerup_type >= len(all_available_frames):
             logger.error(f"Invalid powerup index {self.powerup_type} for loaded frames (count: {len(all_available_frames)}). Falling back.")
             # Use the first frame as a fallback if index is bad
             correct_frame = all_available_frames[0]
        else:
             correct_frame = all_available_frames[self.powerup_type]
        
        # Store ONLY the correct frame. AnimatedSprite will handle this list.
        self.frames = [correct_frame]
        
        # Set initial image from the single correct frame
        self.frame_index = 0
        self.image = self.frames[self.frame_index] # Set initial image explicitly
        self.rect = self.image.get_rect(center=(int(x), int(y)))
        self.mask = pygame.mask.from_surface(self.image)
        
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
        self.particle_interval = 100  # ms between particle emissions
        
        # Track the last time we created particles
        self.last_particle_time = pygame.time.get_ticks()
        
        # Initialize elapsed time for animations
        self.elapsed_time = 0
        
        # Rotation parameters - Removing direct rotation, handled by AnimatedSprite if needed
        # self.rotation_angle = 0
        # self.rotation_speed = random.uniform(1.0, 3.0)  # Degrees per frame
        
        # Pulsing effect parameters
        self.pulse_timer = 0
        self.pulse_cycle = 60  # Frames for a complete pulse cycle
        
        # Store frame dimensions for scaling (Use first frame as reference)
        self.frame_width = self.image.get_width()
        self.frame_height = self.image.get_height()
        # self.current_frame = 0 # No longer needed, use self.frame_index from parent
        
        # Make orbs semi-transparent - REMOVED for simplification
        # self._make_frames_transparent()
        
        logger.info(f"Created {self.type_name} powerup at ({x}, {y})")
    
    def _load_powerup_frames(self, powerup_type: PowerupType) -> List[pygame.Surface]:
        """Load the animation frames for this powerup type."""
        # Load the sprite sheet
        try:
            # Powerups are static items, use center alignment
            all_frames = load_sprite_sheet(
                filename="powerups.png",
                sprite_dir=SPRITES_DIR,
                scale_factor=POWERUP_SCALE_FACTOR,
                alignment='center' # Center align powerups
            )
            
            # Log details for debugging
            logger.info(f"Loaded powerup sprite sheet with {len(all_frames)} frames. Expecting 9.")
            
            # Check if we got the expected number of frames
            if len(all_frames) < 9:
                 logger.error(f"Powerup sprite sheet has insufficient frames: {len(all_frames)}. Expected 9.")
                 raise ValueError("Insufficient frames in powerup sprite sheet")

            # Assuming 9 powerups, frames 0-8 correspond to types 0-8
            # We return ALL frames, the AnimatedSprite will handle cycling
            # If a specific powerup should NOT animate, it can override update or use specific frames
            return all_frames 

        except Exception as e:
            logger.error(f"Error loading powerup sprite sheet: {e}")
        
        # Return a fallback colored rectangle if we couldn't load the proper sprite
        fallback = pygame.Surface((30, 30), pygame.SRCALPHA)
        colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255),
            (255, 128, 0), (128, 0, 255), (0, 255, 128)
        ]
        # Use the provided type index, not self.powerup_type as it might not be set yet
        # Use the integer value of the enum member for indexing
        color = colors[int(powerup_type) % len(colors)] 
        pygame.draw.rect(fallback, color, (0, 0, 30, 30))
        # Use the name from the enum member
        logger.warning(f"Using fallback colored rectangle for powerup type {powerup_type.name}")
        # Return a list containing the fallback, matching expected return type
        # Provide fallback frames based on the number of defined Enum members
        # Ensure the list has enough elements for indexing, even if they are the same fallback
        num_powerup_types = len(PowerupType)
        return [fallback.copy() for _ in range(num_powerup_types)] # Use copies
    
    @property
    def position(self) -> Tuple[float, float]:
        """Get the current position as a tuple."""
        return (self._position_x, self._position_y)
    
    # Make sure we only have one update method
    # This version handles both the animation and movement/effects
    def update(self) -> None:
        """Update powerup state, including animation and movement."""
        # Handle animation (originally in AnimatedSprite.update)
        # Since self.frames now only has one element, this won't cycle frames,
        # but it still handles the animation timer logic if needed elsewhere.
        super().update()
        
        # Update position
        self._position_x -= self.move_speed * (1 + self.move_speed_mod)
        self.rect.center = (int(self._position_x), int(self._position_y))
        
        # Update the pulsing effect
        self.pulse_timer += 1
        if self.pulse_timer > self.pulse_cycle:
            self.pulse_timer = 0
        
        # Calculate pulse scale based on sine wave
        pulse = math.sin(self.pulse_timer / self.pulse_cycle * math.pi * 2)
        pulse_scale = 1.0 + pulse * 0.1  # Scale between 0.9 and 1.1
        
        # Colors for the glow effect based on powerup type
        colors = [
            (255, 220, 0),    # TRIPLE_SHOT: Golden
            (0, 255, 255),    # RAPID_FIRE: Cyan
            (0, 100, 255),    # SHIELD: Blue
            (255, 0, 255),    # HOMING_MISSILES: Magenta
            (0, 255, 0),      # POWER_RESTORE: Green
            (255, 128, 0),    # SCATTER_BOMB: Orange
            (128, 0, 255),    # TIME_WARP: Purple
            (255, 0, 128),    # MEGA_BLAST: Pink
        ]
        glow_color = colors[self.powerup_type % len(colors)]
        
        # Calculate glow intensity based on pulse
        glow_intensity = 0.5 + pulse * 0.3  # Vary between 0.2 and 0.8
        
        # Get the current animation frame
        # Ensure frame_index is valid
        if not self.frames or self.frame_index >= len(self.frames):
             logger.error(f"Invalid frame index {self.frame_index} for powerup {self.type_name}")
             # Use a fallback image or skip update to prevent crash
             # For now, just skip the glow/scale effect if frame is invalid
             current_base_frame = pygame.Surface((self.frame_width, self.frame_height), pygame.SRCALPHA)
             current_base_frame.fill((128,128,128,128)) # Grey fallback
        else:
             current_base_frame = self.frames[self.frame_index]

        # Scale the base image (use the current animation frame)
        scaled_image = pygame.transform.scale(
            current_base_frame, 
            (int(self.frame_width * pulse_scale), int(self.frame_height * pulse_scale))
        )
        
        # Create a larger surface for the glow effect
        glow_size = max(scaled_image.get_width(), scaled_image.get_height()) * 2
        glow_surface = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
        
        # Draw semi-transparent glowing rings
        center = (glow_size // 2, glow_size // 2)
        for radius in range(glow_size // 4, glow_size // 2, 2):
            # Calculate alpha based on radius (outer rings are more transparent)
            alpha = int(max(0, 150 * (1 - radius / (glow_size / 2)) * glow_intensity))
            # Create a temporary surface for this ring
            ring_surface = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
            pygame.draw.circle(
                ring_surface, (*glow_color, alpha), center, radius
            )
            # Add the ring to the glow surface
            glow_surface.blit(ring_surface, (0, 0))
        
        # Calculate position to center the scaled image on the glow surface
        image_pos = (
            center[0] - scaled_image.get_width() // 2,
            center[1] - scaled_image.get_height() // 2
        )
        
        # Draw the base image on top of the glow
        glow_surface.blit(scaled_image, image_pos)
        
        # Update the powerup's image to the new glow surface
        # This *overwrites* the frame selected by super().update()
        self.image = glow_surface 
        
        # Restore the center position after changing the image size
        old_center = self.rect.center
        self.rect = self.image.get_rect()
        self.rect.center = old_center
        
        # Create a new mask for collision detection
        self.mask = pygame.mask.from_surface(self.image)
        
        # Create trail particles at intervals
        if self.particles_group and pygame.time.get_ticks() - self.last_particle_time > self.particle_interval:
            self._create_trail_particles()
            self.last_particle_time = pygame.time.get_ticks()
        
        # Remove if off screen
        if self.rect.right < 0:
            self.kill()
    
    def _create_trail_particles(self) -> None:
        """Create trailing particles behind the powerup."""
        if not self.particles_group:
            return
        
        # Get color based on powerup type
        colors = [
            (255, 220, 0),    # TRIPLE_SHOT: Golden
            (0, 255, 255),    # RAPID_FIRE: Cyan
            (0, 100, 255),    # SHIELD: Blue
            (255, 0, 255),    # HOMING_MISSILES: Magenta
            (0, 255, 0),      # POWER_RESTORE: Green
            (255, 128, 0),    # SCATTER_BOMB: Orange
            (128, 0, 255),    # TIME_WARP: Purple
            (255, 0, 128),    # MEGA_BLAST: Pink
        ]
        color = colors[self.powerup_type % len(colors)]
        
        # Create more particles (3-5) at and around the powerup
        for _ in range(random.randint(3, 5)):
            # Position randomly around the powerup, not just behind
            position = (
                self.rect.centerx + random.randint(-self.rect.width//2, self.rect.width//2),
                self.rect.centery + random.randint(-self.rect.height//2, self.rect.height//2)
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
                position, (vel_x, vel_y), color,
                size, lifetime, 0.01, 0.95,
                self.particles_group
            )
            
        # Also create a "wake" of smaller particles behind the powerup
        for _ in range(2):
            wake_pos = (
                self.rect.right + random.randint(-3, 3),
                self.rect.centery + random.randint(-8, 8)
            )
            
            # Mostly trailing behind
            vel_x = random.uniform(0.8, 1.8)  # Slightly faster
            vel_y = random.uniform(-0.4, 0.4)  # Slight vertical spread
            
            # Smaller but still visible
            size = random.randint(2, 4)
            lifetime = random.randint(10, 20)
            
            # Create particle
            PowerupParticle(
                wake_pos, (vel_x, vel_y), color,
                size, lifetime, 0.01, 0.92,
                self.particles_group
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
            
        # Get color based on powerup type
        colors = [
            (255, 220, 0),    # TRIPLE_SHOT: Golden
            (0, 255, 255),    # RAPID_FIRE: Cyan
            (0, 100, 255),    # SHIELD: Blue
            (255, 0, 255),    # HOMING_MISSILES: Magenta
            (0, 255, 0),      # POWER_RESTORE: Green
            (255, 128, 0),    # SCATTER_BOMB: Orange
            (128, 0, 255),    # TIME_WARP: Purple
            (255, 0, 128),    # MEGA_BLAST: Pink
        ]
        color = colors[self.powerup_type % len(colors)]
        
        # Create a burst of particles
        for _ in range(20):
            # Random angle and speed
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.0, 3.0)
            
            vel_x = math.cos(angle) * speed
            vel_y = math.sin(angle) * speed
            
            # Random size and lifetime
            size = random.randint(3, 8)
            lifetime = random.randint(30, 60)
            
            # Create particle
            PowerupParticle(
                position, (vel_x, vel_y), color,
                size, lifetime, 0.03, 0.96,
                self.particles_group
            ) 