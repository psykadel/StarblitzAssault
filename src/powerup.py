"""Powerup system for the Starblitz Assault game."""

import pygame
import math
import random
from typing import Optional, Tuple, List, Dict, Any

from src.animated_sprite import AnimatedSprite
from src.sprite_loader import load_sprite_sheet, DEFAULT_CROP_BORDER_PIXELS
from src.particle import ParticleSystem
from src.logger import get_logger

# Import config variables
from config.game_config import (
    SPRITES_DIR, SCREEN_WIDTH, SCREEN_HEIGHT
)

# Get a logger for this module
logger = get_logger(__name__)

# Constants for powerups
POWERUP_SCALE_FACTOR = 0.15  # Reduced even further to make powerups extremely small
POWERUP_ANIMATION_SPEED_MS = 120  # Animate slightly faster than player
POWERUP_FLOAT_SPEED = 1.0  # Base horizontal speed
POWERUP_DURATION = 10000  # 10 seconds for temporary powerups
POWERUP_BLINK_START = 8000  # When to start blinking (2 seconds before expiry)

# Powerup types
POWERUP_TYPES = [
    "TRIPLE_SHOT",       # 0: Triple shot - fire 3 bullets at once
    "RAPID_FIRE",        # 1: Increased fire rate
    "SHIELD",            # 2: Temporary invulnerability
    "HOMING_MISSILES",   # 3: Bullets track enemies
    "PULSE_BEAM",        # 4: Charged powerful beam attack
    "POWER_RESTORE",     # 5: Restore player's health/power level
    "SCATTER_BOMB",      # 6: Explodes into multiple projectiles
    "TIME_WARP",         # 7: Slow down enemies and bullets
    "MEGA_BLAST"         # 8: Screen-clearing explosion
]

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
        
        # Create the image
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(
            self.image,
            color,
            (size // 2, size // 2),
            size // 2
        )
        self.rect = self.image.get_rect(center=(int(self.pos_x), int(self.pos_y)))
    
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
            self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            alpha = int(255 * fade_factor)
            color_with_alpha = (*self.color, alpha)
            pygame.draw.circle(
                self.image,
                color_with_alpha,
                (self.size // 2, self.size // 2),
                self.size // 2
            )
            old_center = self.rect.center
            self.rect = self.image.get_rect(center=old_center)

class Powerup(AnimatedSprite):
    """Base class for all powerups."""
    
    def __init__(self, powerup_type: int, x: float, y: float, 
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
        
        # Store the type
        self.powerup_type = powerup_type
        self.type_name = POWERUP_TYPES[powerup_type]
        
        # Store game reference
        self.game_ref = game_ref
        
        # Load animation frames
        self.frames = self._load_powerup_frames(powerup_type)
        
        # Set initial image
        self.frame_index = 0
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect(center=(x, y))
        self.mask = pygame.mask.from_surface(self.image)
        
        # Position tracking for smoother movement
        self.pos_x = float(x)
        self.pos_y = float(y)
        
        # Movement parameters - straight movement like enemies
        self.speed_x = -POWERUP_FLOAT_SPEED * 0.75  # 75% of enemy speed
        self.speed_y = 0
        
        # Particle effect parameters
        self.particles_group = particles_group
        self.particle_timer = 0
        self.particle_interval = 100  # ms between particle emissions
        
        # Track the last time we created particles
        self.last_particle_time = pygame.time.get_ticks()
        
        # Initialize elapsed time for animations
        self.elapsed_time = 0
        
        logger.info(f"Created {self.type_name} powerup at ({x}, {y})")
    
    def _load_powerup_frames(self, powerup_type: int) -> List[pygame.Surface]:
        """Load the animation frames for this powerup type."""
        # Load the sprite sheet
        try:
            all_frames = load_sprite_sheet(
                filename="powerups.png",
                sprite_dir=SPRITES_DIR,
                scale_factor=POWERUP_SCALE_FACTOR,
                crop_border=DEFAULT_CROP_BORDER_PIXELS
            )
            
            # Log details for debugging
            logger.info(f"Loaded powerup sprite sheet with {len(all_frames)} frames")
            
            # Return only the frames for this powerup type (assuming 9 types in a 3x3 grid)
            if len(all_frames) >= 9:
                # Calculate the index based on the grid layout (3x3)
                # In a 3x3 grid, the frames are loaded in row-major order:
                # 0 1 2
                # 3 4 5
                # 6 7 8
                frame_index = powerup_type
                if frame_index < len(all_frames):
                    logger.info(f"Using frame {frame_index} for powerup type {self.type_name}")
                    return [all_frames[frame_index]]  # Each powerup uses one sprite
                else:
                    logger.error(f"Powerup type {powerup_type} exceeds available frames {len(all_frames)}")
            else:
                logger.error(f"Powerup sprite sheet has insufficient frames: {len(all_frames)}")
        except Exception as e:
            logger.error(f"Error loading powerup sprite sheet: {e}")
        
        # Return a fallback colored rectangle if we couldn't load the proper sprite
        fallback = pygame.Surface((30, 30), pygame.SRCALPHA)
        colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255),
            (255, 255, 0), (255, 0, 255), (0, 255, 255),
            (255, 128, 0), (128, 0, 255), (0, 255, 128)
        ]
        color = colors[powerup_type % len(colors)]
        pygame.draw.rect(fallback, color, (0, 0, 30, 30))
        logger.warning(f"Using fallback colored rectangle for powerup type {self.type_name}")
        return [fallback]
    
    def update(self) -> None:
        """Update the powerup's position and animation."""
        super().update()  # Handle animation from parent class
        
        # Apply horizontal movement (continuously move left like enemies)
        self.pos_x += self.speed_x
        
        # Update rect from float position
        self.rect.centerx = round(self.pos_x)
        self.rect.centery = round(self.pos_y)
        
        # Update elapsed time
        self.elapsed_time = pygame.time.get_ticks()
        
        # Apply subtle pulsing effect
        pulse_factor = 0.05  # Very subtle pulsing
        pulse_scale = 1.0 + (math.sin(self.elapsed_time * 0.003) * pulse_factor)
        
        # Store current center before scaling
        current_center = self.rect.center
        
        # Scale from original frame
        scaled_size = (
            int(self.frames[self.frame_index].get_width() * pulse_scale),
            int(self.frames[self.frame_index].get_height() * pulse_scale)
        )
        self.image = pygame.transform.scale(self.frames[self.frame_index], scaled_size)
        
        # Restore center position
        self.rect = self.image.get_rect(center=current_center)
        
        # Create particles at intervals
        now = pygame.time.get_ticks()
        if now - self.last_particle_time > self.particle_interval and self.particles_group:
            self.last_particle_time = now
            self._create_trail_particles()
            
        # Remove if completely off left edge of screen
        if self.rect.right < -50:
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
            (255, 255, 255),  # PULSE_BEAM: White
            (0, 255, 0),      # POWER_RESTORE: Green
            (255, 128, 0),    # SCATTER_BOMB: Orange
            (128, 0, 255),    # TIME_WARP: Purple
            (255, 0, 128),    # MEGA_BLAST: Pink
        ]
        color = colors[self.powerup_type % len(colors)]
        
        # Create 1-2 particles at the rear of the powerup
        for _ in range(random.randint(1, 2)):
            position = (
                self.rect.right + random.randint(-3, 3),
                self.rect.centery + random.randint(-5, 5)
            )
            
            # Random velocity
            vel_x = random.uniform(0.5, 1.5)  # Opposite direction of movement
            vel_y = random.uniform(-0.3, 0.3)
            
            # Random size and lifetime
            size = random.randint(2, 4)  # Smaller particles
            lifetime = random.randint(10, 20)  # Shorter lifetime
            
            # Create particle
            PowerupParticle(
                position, (vel_x, vel_y), color,
                size, lifetime, 0.01, 0.95,
                self.particles_group
            )
    
    def apply_effect(self, player) -> None:
        """Apply the powerup effect to the player.
        
        This method should be overridden by subclasses.
        """
        logger.info(f"Collected {self.type_name} powerup")
        
        # Basic implementation - restore some power
        if player.power_level < 5:
            player.power_level += 1
            logger.info(f"Power increased to {player.power_level}")
        
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
            (255, 255, 255),  # PULSE_BEAM: White
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