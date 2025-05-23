"""Boss battle implementation for Starblitz Assault."""

from __future__ import annotations

import math
import os
import random
from typing import List, Optional, Tuple, TYPE_CHECKING

import pygame
import numpy

# Import Game type only for type checking to avoid circular import
if TYPE_CHECKING:
    from src.game_loop import Game

from config.config import (
    IMAGES_DIR,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    PLAYFIELD_TOP_Y,
    PLAYFIELD_BOTTOM_Y,
    BOSS_BULLET_COLORS,
)
from src.logger import get_logger
from src.enemy_bullet import EnemyBullet
from src.explosion import Explosion
from src.particle import ParticleSystem

# Get logger for this module
logger = get_logger(__name__)

# Boss battle constants
BOSS_MAX_HEALTH = 150
BOSS_MOVEMENT_SPEED = 2
BOSS_TENTACLE_COUNT = 15

# Enumerate attack patterns directly for clarity
class AttackPattern:
    SPIRAL = 0
    RADIAL = 1
    WAVE = 2
    TARGETED = 3
    RAIN = 4

# Add at the top, after imports
TWOPI = math.pi * 2  # For performance in tight loops

class RainbowParticle(pygame.sprite.Sprite):
    """A special particle with rainbow trail effect for boss death animation."""
    
    # Class variable to track total active particles and limit them
    active_particles = 0
    max_particles = 150  # Limit total particles for performance
    
    def __init__(
        self,
        position: Tuple[float, float],
        velocity: Tuple[float, float],
        color: Tuple[int, int, int],
        size: int,
        lifetime: int,
        trail_length: int = 5,
        particles_group: Optional[pygame.sprite.Group] = None
    ) -> None:
        """Initialize a rainbow particle.
        
        Args:
            position: Starting position (x, y)
            velocity: Initial velocity (vx, vy)
            color: Initial RGB color
            size: Particle size in pixels
            lifetime: How many frames the particle lives
            trail_length: Number of trail segments to maintain
            particles_group: Sprite group to add to
        """
        # Check if we've reached the particle limit
        if RainbowParticle.active_particles >= RainbowParticle.max_particles:
            # Don't create this particle if we're at the limit
            return
            
        # Filter out None values from groups
        valid_groups = [g for g in [particles_group] if g is not None]
        super().__init__(*valid_groups)
        
        # Increment active particle count
        RainbowParticle.active_particles += 1
        
        # Position and movement
        self.pos = list(position)  # Exact position as float
        self.velocity = list(velocity)
        
        # Appearance
        self.color = color
        self.size = size
        self.initial_size = size
        self.glow = True
        
        # Lifetime
        self.lifetime = lifetime
        self.age = 0
        
        # Trail properties - use shorter trails for better performance
        self.trail_length = min(trail_length, 7)  # Cap trail length for performance
        
        # Store positions more efficiently - just store the positions, not copies
        self.trail_positions = []
        for _ in range(self.trail_length):
            self.trail_positions.append([position[0], position[1]])
        
        self.trail_colors = []
        
        # Initialize trail colors (rainbow sequence)
        for i in range(self.trail_length):
            # Get color from rainbow palette with offset
            color_idx = (i * 2) % len(BOSS_BULLET_COLORS)
            self.trail_colors.append(BOSS_BULLET_COLORS[color_idx])
        
        # Create initial image
        self._update_image()
        
        # Optimization: Only update the image every few frames
        self.update_frequency = 2  # Update image every 2 frames
    
    def _update_image(self):
        """Update the particle image with current properties."""
        # Calculate fade factor based on age (1.0 at start, 0.0 at end)
        life_factor = 1.0 - (self.age / self.lifetime)
        
        # Calculate current size with slight pulsation
        pulse = 1.0 + (math.sin(self.age * 0.2) * 0.15)  # Subtle pulse effect
        current_size = int(self.size * life_factor * pulse * 1.5)  # 50% larger particles
        
        # Simplified size calculation - use fixed size based on max possible trail
        width = max(96, current_size * 8)  # Larger surface for bigger particles
        height = max(96, current_size * 8)
        
        # Create surface with alpha channel
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # Calculate center position in the image
        center_x = width // 2
        center_y = height // 2
        
        # Draw trail first (so particle appears on top) - simplified for performance
        for i, (trail_pos, trail_color) in enumerate(zip(self.trail_positions, self.trail_colors)):
            # Only draw every other trail segment for better performance
            if i % 2 == 0 or i == len(self.trail_positions) - 1:
                # Calculate relative position on image
                rel_x = center_x + int(trail_pos[0] - self.pos[0])
                rel_y = center_y + int(trail_pos[1] - self.pos[1])
                
                # Calculate size and alpha based on position in trail
                segment_factor = 1.0 - (i / self.trail_length)
                # Larger trail segments
                segment_size = max(2, int(current_size * segment_factor * 0.8))
                # Higher baseline opacity (less transparent)
                segment_alpha = int(220 * segment_factor * life_factor)
                
                # Make trail colors more vibrant by increasing saturation
                r, g, b = trail_color
                # Find dominant color channel and enhance it
                max_channel = max(r, g, b)
                if max_channel > 0:
                    boost_factor = 1.3  # Boost color saturation
                    if r == max_channel:
                        r = min(255, int(r * boost_factor))
                    elif g == max_channel:
                        g = min(255, int(g * boost_factor))
                    elif b == max_channel:
                        b = min(255, int(b * boost_factor))
                enhanced_color = (r, g, b)
                
                # Draw trail segment with enhanced color
                segment_color = (*enhanced_color, segment_alpha)
                pygame.draw.circle(self.image, segment_color, (rel_x, rel_y), segment_size)
                
                # Add improved glow
                if self.glow and segment_size > 1:
                    glow_size = segment_size * 1.8  # Larger glow
                    glow_color = (*enhanced_color, segment_alpha // 2)  # More visible glow
                    pygame.draw.circle(self.image, glow_color, (rel_x, rel_y), glow_size)
        
        # Draw main particle on top with enhanced color
        r, g, b = self.color
        max_channel = max(r, g, b)
        if max_channel > 0:
            boost_factor = 1.3
            if r == max_channel:
                r = min(255, int(r * boost_factor))
            elif g == max_channel:
                g = min(255, int(g * boost_factor))
            elif b == max_channel:
                b = min(255, int(b * boost_factor))
        enhanced_main_color = (r, g, b)
        
        # More opaque main particle
        main_color = (*enhanced_main_color, min(255, int(255 * life_factor)))
        pygame.draw.circle(self.image, main_color, (center_x, center_y), current_size)
        
        # Add enhanced glow to main particle
        if self.glow:
            glow_size = current_size * 1.8  # Larger glow
            glow_color = (min(255, enhanced_main_color[0] + 70), 
                min(255, enhanced_main_color[1] + 70),
                min(255, enhanced_main_color[2] + 70),
                           min(255, int(120 * life_factor)))  # Brighter, more visible glow
            pygame.draw.circle(self.image, glow_color, (center_x, center_y), glow_size)
        
        # Position the sprite correctly
        self.rect = self.image.get_rect(center=(int(self.pos[0]), int(self.pos[1])))
    
    def update(self):
        """Update the particle position, appearance and lifetime."""
        # Update age and kill if expired
        self.age += 1
        if self.age >= self.lifetime:
            self.kill()
            # Decrement active particle count when killed
            RainbowParticle.active_particles -= 1
            return
        
        # Update trail positions (shift old positions down)
        # Only update every other frame for performance
        if self.age % 2 == 0:
            # Remove oldest position
            if len(self.trail_positions) > 0:
                self.trail_positions.pop()
            # Add current position at front
            self.trail_positions.insert(0, [self.pos[0], self.pos[1]])
        
        # Apply movement
        self.pos[0] += self.velocity[0]
        self.pos[1] += self.velocity[1]
        
        # Apply drag (slow down gradually)
        self.velocity[0] *= 0.98
        self.velocity[1] *= 0.98
        
        # Update rect position even if we don't update the image
        self.rect.center = (int(self.pos[0]), int(self.pos[1]))
        
        # Shift colors for rainbow cycling effect less frequently
        if self.age % 6 == 0:  # Was 3
            self.trail_colors.append(self.trail_colors.pop(0))  # Rotate colors
            # Update main particle color too
            self.color = self.trail_colors[0]
        
        # Only update the image periodically for better performance
        if self.age % self.update_frequency == 0:
            self._update_image()

class BossTentacle:
    """A tentacle extension from the boss that moves independently."""
    
    def __init__(self, boss: 'Boss', index: int):
        """Initialize a boss tentacle.
        
        Args:
            boss: The parent Boss instance
            index: The tentacle index (for positioning)
        """
        self.boss = boss
        self.index = index
        self.length = random.randint(150, 250)
        self.width = random.randint(12, 20)
        self.angle = (TWOPI / BOSS_TENTACLE_COUNT) * index
        self.angular_speed = random.uniform(0.01, 0.05) * random.choice([-1, 1])
        self.extension_speed = random.uniform(0.2, 0.8)
        self.max_extension = random.randint(40, 70)
        self.extension = 0
        self.extension_direction = 1
        self.segments = 12
        self.color_shift = random.randint(0, 7)  # Start at a random color in the rainbow
        self.base_color_index = self.color_shift
    
    def update(self):
        """Update tentacle position and animation."""
        # Update angle
        self.angle += self.angular_speed
        
        # Update extension
        self.extension += self.extension_speed * self.extension_direction
        if self.extension > self.max_extension:
            self.extension_direction = -1
        elif self.extension < -self.max_extension:
            self.extension_direction = 1
        
        # Shift base color slowly over time
        self.base_color_index = (self.base_color_index + 0.02) % len(BOSS_BULLET_COLORS)
    
    def draw(self, surface: pygame.Surface):
        """Draw the tentacle on the given surface.
        
        Args:
            surface: The pygame Surface to draw on
        """
        boss_center = self.boss.rect.center
        
        # Calculate segment positions along tentacle
        points = []
        angle = self.angle
        length = self.length
        width = self.width
        base_color_index = self.base_color_index
        segments = self.segments
        for i in range(segments + 1):
            progress = i / segments
            segment_length = length * progress
            wave_intensity = 10 + self.extension * progress
            wave_x = math.sin(angle + progress * 5) * wave_intensity * progress
            wave_y = math.cos(angle + progress * 5) * wave_intensity * progress
            x = boss_center[0] - math.cos(angle) * segment_length + wave_x
            y = boss_center[1] - math.sin(angle) * segment_length + wave_y
            points.append((x, y))
        
        # Draw segments as lines with rainbow gradient
        if len(points) > 1:
            for i in range(len(points) - 1):
                progress = i / (len(points) - 1)
                color_index = int((base_color_index + progress * 3) % len(BOSS_BULLET_COLORS))
                next_color_index = (color_index + 1) % len(BOSS_BULLET_COLORS)
                color_blend = (base_color_index + progress * 3) % 1.0
                color1 = BOSS_BULLET_COLORS[color_index]
                color2 = BOSS_BULLET_COLORS[next_color_index]
                color = (
                    int(color1[0] * (1 - color_blend) + color2[0] * color_blend),
                    int(color1[1] * (1 - color_blend) + color2[1] * color_blend),
                    int(color1[2] * (1 - color_blend) + color2[2] * color_blend)
                )
                seg_width = max(1, int(width * (1 - progress * 0.8)))
                pygame.draw.line(surface, color, points[i], points[i+1], seg_width)
        
        # Draw a glowing point at the end
        if points:
            glow_radius = max(3, int(width * 0.5))
            end_point = points[-1]
            pygame.draw.circle(surface, BOSS_BULLET_COLORS[int(base_color_index) % len(BOSS_BULLET_COLORS)], 
                              (int(end_point[0]), int(end_point[1])), glow_radius)

class RainbowBullet(EnemyBullet):
    """A rainbow-colored bullet fired by the boss."""
    
    def __init__(self, x: float, y: float, speed_x: float, speed_y: float, color_index: int):
        """Initialize a rainbow bullet.
        
        Args:
            x: Initial x position
            y: Initial y position
            speed_x: Horizontal speed
            speed_y: Vertical speed
            color_index: Index into the BOSS_BULLET_COLORS array
        """
        # Initialize position
        pygame.sprite.Sprite.__init__(self)
        self.color_index = color_index
        self.color = BOSS_BULLET_COLORS[color_index]
        self.size = random.randint(4, 8)  # Varied bullet sizes
        self.damage = 10  # Boss bullets deal more damage
        self.pulse_speed = random.uniform(0.05, 0.15)
        self.pulse_state = random.random() * math.pi * 2
        
        # Create the bullet image
        self.image = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        self.draw_bullet()
        
        # Create a mask for collision detection
        self.mask = pygame.mask.from_surface(self.image)
        
        # Store position as floating point for precise movement
        self.pos_x = float(x)
        self.pos_y = float(y)
        
        # Store velocity directly
        self.velocity = (speed_x, speed_y)
    
    def draw_bullet(self):
        """Draw the bullet with its current color and size."""
        # Clear the surface
        self.image.fill((0, 0, 0, 0))
        
        # Calculate pulsing effect
        pulse_factor = 0.2 * math.sin(self.pulse_state) + 1.0
        current_size = max(2, int(self.size * pulse_factor))
        
        # Draw the main circle
        pygame.draw.circle(self.image, self.color, 
                         (self.image.get_width() // 2, self.image.get_height() // 2), 
                         current_size)
        
        # Draw a lighter core
        lighter_color = (
            min(255, self.color[0] + 80),
            min(255, self.color[1] + 80),
            min(255, self.color[2] + 80)
        )
        pygame.draw.circle(self.image, lighter_color, 
                         (self.image.get_width() // 2, self.image.get_height() // 2), 
                         max(1, current_size // 2))
    
    def update(self):
        """Update the bullet position and appearance."""
        # Move using velocity
        self.pos_x += self.velocity[0]
        self.pos_y += self.velocity[1]
        
        # Update rect position from floating point position
        self.rect.centerx = int(self.pos_x)
        self.rect.centery = int(self.pos_y)
        
        # Update pulsing effect
        self.pulse_state += self.pulse_speed
        self.draw_bullet()
        
        # Slowly cycle through colors for additional rainbow effect
        if random.random() < 0.02:
            self.color_index = (self.color_index + 1) % len(BOSS_BULLET_COLORS)
            self.color = BOSS_BULLET_COLORS[self.color_index]
        
        # Kill if off screen
        if (self.rect.right < 0 or self.rect.left > SCREEN_WIDTH or
            self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT):
            self.kill()

class Boss(pygame.sprite.Sprite):
    """The final boss enemy for Starblitz Assault."""
    
    def __init__(self, player, *groups):
        """Initialize the boss.
        
        Args:
            player: The player sprite (for targeted attacks)
            groups: Sprite groups to add to
        """
        # Make sure we don't pass None as a group
        groups = [g for g in groups if g is not None]
        super().__init__(*groups)
        self.player = player
        
        # Reference to the game object (will be set by the game)
        self.game_ref: Optional['Game'] = None
        
        # Load boss sprite
        self.original_image = pygame.image.load(os.path.join(IMAGES_DIR, "boss.png")).convert_alpha()
        
        # Flip the boss image horizontally
        self.original_image = pygame.transform.flip(self.original_image, False, False)
        
        # Scale the boss to an appropriate size
        width = int(SCREEN_WIDTH * 0.25)  # 25% of screen width
        height = int(self.original_image.get_height() * (width / self.original_image.get_width()))
        self.original_image = pygame.transform.scale(self.original_image, (width, height))
        
        self.image = self.original_image.copy()
        self.rect = self.image.get_rect()
        
        # Position boss on the right side of the screen
        self.rect.right = SCREEN_WIDTH - 100
        self.rect.centery = SCREEN_HEIGHT // 2
        
        # Movement variables
        self.pos_x = float(self.rect.centerx)
        self.pos_y = float(self.rect.centery)
        self.target_y = self.pos_y
        self.vertical_direction = 1
        self.movement_speed = BOSS_MOVEMENT_SPEED
        self.movement_amplitude = 150  # How far up/down the boss moves
        
        # Health and state variables
        self.max_health = BOSS_MAX_HEALTH
        self.health = self.max_health
        self.is_defeated = False
        self.phase = 1  # Boss phases (1-3) increasing in difficulty
        
        # Attack pattern variables - SIMPLIFIED
        self.attack_pattern = AttackPattern.TARGETED
        
        # Base bullet firing cooldown
        self.bullet_timer = 0
        self.bullet_interval = 500
        
        # Pattern-specific timers
        self.pattern_timer = 0
        self.pattern_duration = 8000  # Pattern lasts for 8 seconds
        
        # Bullet properties
        self.bullet_speed = 5.5  # Reduced from 6.0 to 5.5 to make bullets even slower
        
        # Tentacles
        self.tentacles = [BossTentacle(self, i) for i in range(BOSS_TENTACLE_COUNT)]
        
        # Special effects
        self.glow_intensity = 0
        self.glow_direction = 1
        self.sparkle_timer = 0
        self.distortion_phase = 0
        
        # Sound effect timers
        
        # Add new variables for death animation
        self.death_animation_active = False
        self.death_animation_timer = 0
        self.death_animation_duration = 480
        self.death_explosion_interval = 8  # Create new explosions every 8 frames
        self.opacity = 255  # For fade out effect
        self.animation_complete = False  # Flag to indicate when death animation has finished
        self.animation_near_complete = False  # Flag to indicate when animation is almost done
        
        logger.info("Boss initialized")
    
    def update(self):
        """Update boss position, state, and attack patterns."""
        # Handle death animation if active instead of normal updates
        if self.death_animation_active:
            self._update_death_animation()
            return
        
        # Don't update if defeated
        if self.is_defeated:
            return
        
        # Update glow effect
        self.glow_intensity += 0.05 * self.glow_direction
        if self.glow_intensity > 1.0:
            self.glow_intensity = 1.0
            self.glow_direction = -1
        elif self.glow_intensity < 0.2:
            self.glow_intensity = 0.2
            self.glow_direction = 1
        
        # Update sparkle timer
        self.sparkle_timer += 1
        
        # Apply visual effects to the boss image
        self._update_boss_image()
        
        # Update tentacles
        for tentacle in self.tentacles:
            tentacle.update()
        
        # Update movement pattern - Float up and down menacingly
        # Choose a new target position when close to current target
        pos_y = self.pos_y
        target_y = self.target_y
        movement_speed = self.movement_speed
        if abs(pos_y - target_y) < 10:
            playfield_height = PLAYFIELD_BOTTOM_Y - PLAYFIELD_TOP_Y
            mid_y = PLAYFIELD_TOP_Y + playfield_height / 2
            self.target_y = mid_y + random.uniform(-self.movement_amplitude, self.movement_amplitude)
            self.target_y = max(PLAYFIELD_TOP_Y + 50, min(PLAYFIELD_BOTTOM_Y - 50, self.target_y))
        if pos_y < target_y:
            self.pos_y += movement_speed
        else:
            self.pos_y -= movement_speed
        
        # Apply small random horizontal movement
        if random.random() < 0.03:
            self.pos_x += random.uniform(-1, 1)
        
        # Keep boss within bounds
        max_right = SCREEN_WIDTH - 80
        min_right = SCREEN_WIDTH - 200
        self.pos_x = max(min_right, min(max_right, self.pos_x))
        
        # Update boss rect with floating point position
        self.rect.centerx = int(self.pos_x)
        self.rect.centery = int(self.pos_y)
        
        # Check if it's time to change attack pattern
        self.pattern_timer += 1000 / 60  # Approximate ms per frame
        if self.pattern_timer >= self.pattern_duration:
            self.change_attack_pattern()
            self.pattern_timer = 0
        
        # Update bullet firing - we keep track of timing here
        # but the actual firing happens in game_loop.py
        self.bullet_timer += 1000 / 60  # Approximate ms per frame
    
    def _update_boss_image(self):
        """Apply visual effects to the boss image with better performance."""
        # Reduce update frequency slightly further
        if self.sparkle_timer % 4 != 0:
            return
        
        # Start with the original image
        self.image = self.original_image.copy()
        
        # Update distortion phase
        self.distortion_phase += 0.1
        
        # Calculate health percentage and distortion intensity
        health_percent = self.health / self.max_health
        distortion_intensity = ((1.0 - health_percent) * 1.8) + 0.2
        
        # Create a surface for the final image
        new_surface = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        
        # Create a mask of non-transparent pixels
        # This will be used to only apply effects to visible parts of the image
        mask = pygame.mask.from_surface(self.original_image)
        mask_surface = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
        
        # Divide the image into horizontal slices and apply distortion
        slice_height = 10
        img_height = self.image.get_height()
        num_slices = img_height // slice_height
        
        for i in range(num_slices):
            # Random horizontal offset that increases with lower health
            offset_x = int(random.uniform(-10, 10) * distortion_intensity) if random.random() < 0.3 * distortion_intensity else 0
            
            # Source rectangle (from original image)
            slice_y = i * slice_height
            source_rect = pygame.Rect(0, slice_y, self.image.get_width(), slice_height)
            
            # Destination rectangle (on new surface)
            dest_rect = pygame.Rect(offset_x, slice_y, self.image.get_width(), slice_height)
            
            # Copy slice with offset
            new_surface.blit(self.image, dest_rect, source_rect)
        
        # Apply color shifting based on health (gets more intense at lower health)
        if random.random() < 0.4 * distortion_intensity:
            # Random color shift
            color_surface = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
            
            # Choose a random color tint
            color_index = random.randint(0, len(BOSS_BULLET_COLORS) - 1)
            tint_color = BOSS_BULLET_COLORS[color_index]
            
            # Fill with semi-transparent color
            alpha = int(50 * distortion_intensity)
            color_surface.fill((tint_color[0], tint_color[1], tint_color[2], alpha))
            
            # Apply the tint only to non-transparent parts using the mask
            color_surface.blit(mask_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            
            # Apply the tint
            new_surface.blit(color_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        
        # Add occasional glitch lines (horizontal) - only on non-transparent areas
        # Reduce intensity calculation slightly and frequency check
        glitch_intensity_factor = distortion_intensity * 0.8
        if random.random() < 0.25 * glitch_intensity_factor: # Reduced base chance
            num_lines = max(1, int(2.5 * glitch_intensity_factor)) # Reduced max lines
            img_width = self.image.get_width()
            for _ in range(num_lines):
                # Find a row with non-transparent pixels
                found_valid_line = False
                line_y = 0  # Default value to avoid unbound error
                attempts = 0
                while not found_valid_line and attempts < 10:  # Limit attempts to avoid infinite loop
                    line_y = random.randint(0, img_height - 1)
                    # Check if this row has non-transparent pixels
                    for x in range(img_width):
                        if mask.get_at((x, line_y)):  # Check if pixel is opaque
                            found_valid_line = True
                            break
                    attempts += 1
                
                if found_valid_line:
                    line_height = random.randint(2, 8)
                    line_color = (255, 255, 255, 150) if random.random() < 0.5 else BOSS_BULLET_COLORS[random.randint(0, len(BOSS_BULLET_COLORS) - 1)]
                    
                    # Create a line surface
                    line_surface = pygame.Surface((new_surface.get_width(), line_height), pygame.SRCALPHA)
                    line_surface.fill(line_color)
                    
                    # Mask the line to only affect non-transparent parts
                    line_mask = pygame.Surface((new_surface.get_width(), line_height), pygame.SRCALPHA)
                    # Extract the relevant slice from the mask
                    for x in range(new_surface.get_width()):
                        for y_offset in range(line_height):
                            y = min(line_y + y_offset, self.image.get_height() - 1)
                            if y < self.image.get_height() and x < self.image.get_width() and mask.get_at((x, y)):
                                line_mask.set_at((x, y_offset), (255, 255, 255, 255))
                    
                    # Apply the mask to the line
                    line_surface.blit(line_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                    
                    # Draw the masked line
                    new_surface.blit(line_surface, (0, line_y))
        
        # Update the boss image with the distorted version
        self.image = new_surface
    
    def change_attack_pattern(self):
        """Change to a different attack pattern."""
        # Choose a new pattern different from the current one
        available_patterns = [
            AttackPattern.SPIRAL,
            AttackPattern.RADIAL,
            AttackPattern.WAVE,
            AttackPattern.TARGETED,
            AttackPattern.RAIN
        ]
        
        if self.attack_pattern in available_patterns:
            available_patterns.remove(self.attack_pattern)
        
            self.attack_pattern = random.choice(available_patterns)
        
        logger.info(f"Boss changed to attack pattern: {self.attack_pattern}")
    
    def fire_bullet(self) -> List[RainbowBullet]:
        """Fire bullets based on the current attack pattern.
        
        Returns:
            A list of RainbowBullet instances
        """
        bullets = []
        
        # Log the start of bullet firing process
        logger.debug(f"Boss firing bullets with pattern: {self.attack_pattern}")
        
        # Starting position is the left side (front) of the boss
        start_x = self.rect.left
        start_y = self.rect.centery
        
        # If player doesn't exist or is defeated, fire straight left
        if not self.player or not self.player.is_alive:
            target_angle = math.pi  # Left direction
        else:
            # Calculate angle to player
            player_x, player_y = self.player.rect.center
            dx = player_x - start_x
            dy = player_y - start_y
            target_angle = math.atan2(dy, dx)
        
        if self.attack_pattern == AttackPattern.TARGETED:
            # TARGETED PATTERN: Shoots directly at player with minimal spread
            # Reduced bullet count for lower difficulty
            count = max(1, self.phase // 2)
            
            for i in range(count):
                # Small aim variation to make player dodge
                angle = target_angle
                if count > 1:
                    # Only add variation if firing multiple bullets
                    angle += random.uniform(-0.3, 0.3) # Wider spread to require dodging
                
                # Calculate velocity
                speed_multiplier = 1.0 + (self.phase * 0.2)  # Reduced multiplier
                speed_x = math.cos(angle) * self.bullet_speed * speed_multiplier
                speed_y = math.sin(angle) * self.bullet_speed * speed_multiplier
                
                # Rainbow color
                color_index = (i + pygame.time.get_ticks() // 100) % len(BOSS_BULLET_COLORS)
                
                # Create the bullet
                bullet = RainbowBullet(
                    start_x, 
                    start_y, 
                    speed_x, 
                    speed_y, 
                    color_index
                )
                bullets.append(bullet)
        
        elif self.attack_pattern == AttackPattern.SPIRAL:
            # SPIRAL PATTERN: Shoots in an expanding spiral
            # Use time-based angle for continuous spinning effect
            base_angle = pygame.time.get_ticks() * 0.001 * (1.0 + self.phase * 0.15)  # Slower rotation
            # Reduced bullet count for lower difficulty
            count = 1 + self.phase  # Was 2 + self.phase
            
            for i in range(count):
                # Calculate angle with spiral arrangement
                angle = base_angle + (2 * math.pi / count) * i
                
                # Calculate velocity with increasing speed based on phase
                speed_multiplier = 1.0 + (self.phase * 0.15)  # Reduced multiplier
                speed_x = math.cos(angle) * self.bullet_speed * speed_multiplier
                speed_y = math.sin(angle) * self.bullet_speed * speed_multiplier
                
                # Rainbow color
                color_index = (i + pygame.time.get_ticks() // 100) % len(BOSS_BULLET_COLORS)
                
                # Create the bullet
                bullet = RainbowBullet(
                    start_x, 
                    start_y, 
                    speed_x, 
                    speed_y, 
                    color_index
                )
                bullets.append(bullet)
        
        elif self.attack_pattern == AttackPattern.RADIAL:
            # RADIAL PATTERN: Shoots in all directions
            # Reduced bullet count for lower difficulty
            count = 4 + self.phase
            
            # Phase 3 adds an alternating rotation to the radial pattern
            rotation_offset = 0
            if self.phase == 3:
                # Create alternating pattern with time
                rotation_offset = (pygame.time.get_ticks() // 500) % 2 * (math.pi / count)
            
            for i in range(count):
                # Calculate angle for even distribution in a circle
                angle = rotation_offset + (2 * math.pi / count) * i
                
                # Calculate velocity with increasing speed based on phase
                speed_multiplier = 1.0 + (self.phase * 0.1)  # Reduced multiplier
                speed_x = math.cos(angle) * self.bullet_speed * speed_multiplier
                speed_y = math.sin(angle) * self.bullet_speed * speed_multiplier
                
                # Rainbow color
                color_index = (i + pygame.time.get_ticks() // 100) % len(BOSS_BULLET_COLORS)
                
                # Create the bullet
                bullet = RainbowBullet(
                    start_x, 
                    start_y, 
                    speed_x, 
                    speed_y, 
                    color_index
                )
                bullets.append(bullet)
        
        elif self.attack_pattern == AttackPattern.WAVE:
            # WAVE PATTERN: Shoots in a wave formation toward player's general direction
            # Reduced bullet count for lower difficulty
            count = max(1, self.phase) # Was 1 + self.phase
            
            # Wave intensity increases with phase
            wave_factor = math.sin(pygame.time.get_ticks() * 0.002) * (0.2 + self.phase * 0.15)  # Reduced factor
            
            for i in range(count):
                # Base direction toward player
                base_angle = target_angle
                
                # Vertical spacing
                vertical_spacing = 40
                vertical_offset = (i - (count - 1) / 2) * vertical_spacing
                bullet_y = start_y + vertical_offset
                
                # Add wave-like movement with increasing complexity in higher phases
                angle = base_angle + wave_factor
                
                # Phase 3: Add sinusoidal speed variation
                speed_multiplier = 1.0 + (self.phase * 0.15)  # Reduced multiplier
                if self.phase == 3:
                    # Bullets in phase 3 have varying speeds
                    speed_multiplier *= 0.8 + 0.4 * math.sin(i * 0.7)
                
                # Calculate velocity
                speed_x = math.cos(angle) * self.bullet_speed * speed_multiplier
                speed_y = math.sin(angle) * self.bullet_speed * speed_multiplier
                
                # Rainbow color
                color_index = (i + pygame.time.get_ticks() // 100) % len(BOSS_BULLET_COLORS)
                
                # Create the bullet
                bullet = RainbowBullet(
                    start_x, 
                    bullet_y, 
                    speed_x, 
                    speed_y, 
                    color_index
                )
                bullets.append(bullet)
        
        elif self.attack_pattern == AttackPattern.RAIN:
            # RAIN PATTERN: Bullets come from top of screen
            # Reduced bullet count for lower difficulty
            count = max(1, self.phase // 2) # Was max(1, self.phase // 2 + 1)
            
            # Wider targeting area to make bullets more spread out
            player_targeting_width = 300 + (self.phase * 50)
            
            for i in range(count):
                # Random position along top of screen, focusing near player but with more spread
                if self.player and self.player.is_alive:
                    min_x = max(50, self.player.rect.centerx - player_targeting_width)
                    max_x = min(SCREEN_WIDTH - 50, self.player.rect.centerx + player_targeting_width)
                else:
                    min_x = 50
                    max_x = SCREEN_WIDTH - 50
                
                rain_x = random.randint(min_x, max_x)
                rain_y = PLAYFIELD_TOP_Y
                
                # Target with much less accuracy (more random)
                if self.player and self.player.is_alive:
                    # Minimal prediction, mostly random
                    prediction_factor = 0.05 * self.phase  # Greatly reduced from 0.15
                    
                    # Try to predict where player will be, with high randomness
                    if hasattr(self.player, 'speed_x') and hasattr(self.player, 'speed_y'):
                        aim_x = self.player.rect.centerx + (self.player.speed_x * prediction_factor * 60)
                        aim_y = self.player.rect.centery + (self.player.speed_y * prediction_factor * 60)
                    else:
                     aim_x = self.player.rect.centerx
                     aim_y = self.player.rect.centery
                else:
                    # Default aiming if no player
                    aim_x = SCREEN_WIDTH // 2
                    aim_y = SCREEN_HEIGHT // 2
                
                # Add more randomness to aim to make it easier to dodge
                aim_variance = 200
                aim_x += random.uniform(-aim_variance, aim_variance)
                
                # Calculate direction vector
                dx = aim_x - rain_x
                dy = aim_y - rain_y
                
                # Normalize and scale by speed
                magnitude = max(1.0, math.sqrt(dx * dx + dy * dy))
                
                # Slower bullets for rain pattern
                speed_multiplier = 0.8 + (self.phase * 0.1)  # Reduced from 1.0 base
                
                speed_x = (dx / magnitude) * self.bullet_speed * speed_multiplier
                speed_y = (dy / magnitude) * self.bullet_speed * speed_multiplier
                
                # Rainbow color
                color_index = (i + pygame.time.get_ticks() // 100) % len(BOSS_BULLET_COLORS)
                
                # Create the bullet
                bullet = RainbowBullet(
                    rain_x, 
                    rain_y, 
                    speed_x, 
                    speed_y, 
                    color_index
                )
                bullets.append(bullet)
        
        # Phase 3: Occasionally fire from tentacle tips for ultimate challenge
        if self.phase == 3 and random.random() < 0.05:  # 5% chance in phase 3
            # Choose a random tentacle
            tentacle = random.choice(self.tentacles)
            
            # Fire from the tip of the tentacle
            boss_center = self.rect.center
            
            # Calculate tentacle tip position (this is simplified; in a real implementation,
            # we would access the actual positions calculated in the tentacle's draw method)
            # Here we approximate the position
            segment_length = tentacle.length
            wave_intensity = 10 + tentacle.extension
            
            # Calculate wave effect 
            wave_x = math.sin(tentacle.angle) * wave_intensity
            wave_y = math.cos(tentacle.angle) * wave_intensity
            
            # Calculate tip position based on angle and length
            tip_x = boss_center[0] - math.cos(tentacle.angle) * segment_length + wave_x
            tip_y = boss_center[1] - math.sin(tentacle.angle) * segment_length + wave_y
            
            # Calculate direction - either toward player or in random direction
            if random.random() < 0.7 and self.player and self.player.is_alive:  # 70% chance to target player
                # Target player
                dx = self.player.rect.centerx - tip_x
                dy = self.player.rect.centery - tip_y
                angle = math.atan2(dy, dx)
            else:
                # Random direction
                angle = random.uniform(0, TWOPI)
                
            # Calculate velocity - these are faster than normal bullets
            tentacle_bullet_speed = self.bullet_speed * 1.3  # Reduced from 1.5
            speed_x = math.cos(angle) * tentacle_bullet_speed
            speed_y = math.sin(angle) * tentacle_bullet_speed
            
            # Create the bullet with tentacle's color
            color_index = int(tentacle.base_color_index) % len(BOSS_BULLET_COLORS)
            bullet = RainbowBullet(
                tip_x,
                tip_y,
                speed_x,
                speed_y,
                color_index
            )
            
            # Add to bullets list
            bullets.append(bullet)
        
        # Add an occasional "surprise burst" (sporadic extra shots) to make player move
        if random.random() < 0.05:  # 5% chance for surprise burst
            surprise_count = 1
            for _ in range(surprise_count):
                # Fire in a semi-random direction, but with player bias
                if self.player and self.player.is_alive:
                    # Calculate angle to player with randomness
                    player_x, player_y = self.player.rect.center
                    dx = player_x - start_x
                    dy = player_y - start_y
                    base_angle = math.atan2(dy, dx)
                    angle = base_angle + random.uniform(-0.7, 0.7)  # Add significant randomness
                else:
                    # Random angle if no player
                    angle = random.uniform(0, TWOPI)
            
                # Higher speed for surprise shots
                surprise_speed = self.bullet_speed * 1.1
                speed_x = math.cos(angle) * surprise_speed
                speed_y = math.sin(angle) * surprise_speed
                
                # Random bright color
                color_index = random.randint(0, len(BOSS_BULLET_COLORS) - 1)
                
                # Create the bullet
                bullet = RainbowBullet(
                    start_x + random.uniform(-20, 20),  # Add some position variation
                    start_y + random.uniform(-20, 20), 
                    speed_x, 
                    speed_y, 
                    color_index
                )
                bullets.append(bullet)
        
        return bullets
    
    def draw_tentacles(self, surface: pygame.Surface):
        """Draw all tentacles.
        
        Args:
            surface: Surface to draw on
        """
        for tentacle in self.tentacles:
            tentacle.draw(surface)
    
    def draw_health_bar(self, surface: pygame.Surface):
        """Draw the boss health bar at the top of the screen.
        
        Args:
            surface: Surface to draw on
        """
        bar_width = SCREEN_WIDTH - 200
        bar_height = 15
        bar_x = 100
        bar_y = 50
        
        # Calculate health percentage
        health_percent = self.health / self.max_health
        current_width = int(bar_width * health_percent)
        
        # Draw background
        pygame.draw.rect(surface, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))
        
        # Draw health bar with gradient based on health
        if health_percent > 0:
            # Create a rainbow-colored health bar
            for i in range(current_width):
                progress = i / bar_width
                color_index = int(progress * len(BOSS_BULLET_COLORS))
                color = BOSS_BULLET_COLORS[color_index % len(BOSS_BULLET_COLORS)]
                
                # Add pulsing effect based on glow intensity
                pulse = int(self.glow_intensity * 50)
                color = (
                    min(255, color[0] + pulse),
                    min(255, color[1] + pulse),
                    min(255, color[2] + pulse)
                )
                
                pygame.draw.line(surface, color, 
                               (bar_x + i, bar_y), 
                               (bar_x + i, bar_y + bar_height))
        
        # Draw border
        pygame.draw.rect(surface, (200, 200, 200), (bar_x, bar_y, bar_width, bar_height), 2)
        
        # Add "BOSS" text
        font = pygame.font.SysFont(None, 30)
        text = font.render("BOSS", True, (255, 255, 255))
        surface.blit(text, (bar_x - 70, bar_y))
    
    def _update_death_animation(self):
        """Update the boss death animation."""
        try:
            # Increment the timer
            self.death_animation_timer += 1
            
            # Calculate animation progress based on the CORRECT duration
            animation_progress = min(1.0, self.death_animation_timer / self.death_animation_duration)
            
            # Create a dramatic visual effect instead of just fading out
            # Only start fading at 75% of the animation
            late_fade_progress = max(0, (animation_progress - 0.75) * 4)
            self.opacity = max(50, int(255 * (1 - late_fade_progress)))
            
            # Apply glitch/distortion effect that increases with time
            self._apply_glitch_effect(animation_progress * 0.8)
            
            # Set the opacity and apply color pulsing
            if self.original_image:
                try:
                    glitch_image = self.original_image.copy()
                    
                    # Add color pulsing effect (cycles through rainbow colors)
                    pulse_color_idx = int((self.death_animation_timer / 5) % len(BOSS_BULLET_COLORS))
                    pulse_color = BOSS_BULLET_COLORS[pulse_color_idx]
                    pulse_surface = pygame.Surface(glitch_image.get_size(), pygame.SRCALPHA)
                    pulse_alpha = int(80 * (1 - late_fade_progress))  # Pulse intensity
                    pulse_surface.fill((pulse_color[0], pulse_color[1], pulse_color[2], pulse_alpha))
                    glitch_image.blit(pulse_surface, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
                    
                    # Apply opacity at the end
                    if self.opacity < 255:
                        glitch_image.fill((255, 255, 255, self.opacity), None, pygame.BLEND_RGBA_MULT)
                    
                    self.image = glitch_image
                except Exception as e:
                    logger.error(f"Error applying death visual effects: {e}")
            
            # Every 3 frames for first half, every 2 frames for second half
            explosion_interval = 3 if animation_progress < 0.5 else 2
            
            # Create rainbow stream effects throughout the animation
            # More intense as the animation progresses - but with fewer particles
            # Reduce frequency - only create streams every 6 frames to reduce load
            rainbow_interval = 6
            if self.death_animation_timer % rainbow_interval == 0:
                # Intensity increases as animation progresses
                intensity = 0.5 + (animation_progress * 0.5)
                
                # Create fewer emission points for better performance
                if random.random() < 0.8:  # 80% chance for boss body emissions
                    # Create only 1-2 emission points on the boss
                    num_boss_points = 1 if animation_progress < 0.5 else 2
                    for _ in range(num_boss_points):
                        offset_x = random.randint(-int(self.rect.width * 0.3), int(self.rect.width * 0.3))
                        offset_y = random.randint(-int(self.rect.height * 0.3), int(self.rect.height * 0.3))
                        pos = (self.rect.centerx + offset_x, self.rect.centery + offset_y)
                        self._create_rainbow_stream_effect(pos, intensity)
                
                # Only add screen-wide emissions if we have particle capacity
                if animation_progress > 0.3 and RainbowParticle.active_particles < RainbowParticle.max_particles * 0.7:
                    # Much fewer emission points for performance - scale with animation progress
                    # Just 1-4 points maximum instead of scaling up to larger numbers
                    num_emission_points = 1 + int(animation_progress * 3)
                    
                    for _ in range(num_emission_points):
                        # Choose random position on screen
                        if random.random() < 0.6:  # 60% chance to stay near boss
                            max_dist = 150 + int(animation_progress * 200)  # Reduced range
                            pos_x = self.rect.centerx + random.randint(-max_dist, max_dist)
                            pos_y = self.rect.centery + random.randint(-max_dist, max_dist)
                        else:
                            # Fully random position across playable area
                            pos_x = random.randint(100, SCREEN_WIDTH - 100)
                            pos_y = random.randint(PLAYFIELD_TOP_Y, PLAYFIELD_BOTTOM_Y)
                        
                        # Ensure position is within screen bounds
                        pos_x = max(0, min(SCREEN_WIDTH, pos_x))
                        pos_y = max(PLAYFIELD_TOP_Y, min(PLAYFIELD_BOTTOM_Y, pos_y))
                        
                        # Create rainbow stream at this position with reduced intensity for performance
                        self._create_rainbow_stream_effect((pos_x, pos_y), intensity * 0.6)
                
                # Create mega burst for dramatic effect at key animation points
                # Only at 2 key points instead of 3 for better performance
                if (animation_progress > 0.5 and animation_progress < 0.52) or \
                   (animation_progress > 0.85 and animation_progress < 0.87):
                    # Only create mega burst if we have particle capacity
                    if RainbowParticle.active_particles < RainbowParticle.max_particles * 0.5:
                        self._create_rainbow_mega_burst()
            
            # Create shockwave effects less frequently for performance
            if self.death_animation_timer % 45 == 0:  # Was 30 or 15
                try:
                    # More intense shockwaves as animation progresses
                    size = 80 + int(animation_progress * 150)  # Reduced size range
                    self._create_shockwave_effect(size=size)

                except Exception as e:
                    logger.error(f"Error creating shockwave effect: {e}")
            
            # Destroy tentacles progressively
            if self.tentacles:
                try:
                    # More aggressive tentacle destruction as animation progresses
                    destruction_chance = 0.05 + animation_progress * 0.2
                    if random.random() < destruction_chance:
                        # Determine how many tentacles to destroy
                        num_tentacles = max(1, min(len(self.tentacles), 
                                                int(1 + animation_progress * 5)))
                        
                        for _ in range(num_tentacles):
                            if not self.tentacles:
                                break
                            
                            tentacle = random.choice(self.tentacles)
                            self.tentacles.remove(tentacle)
                except Exception as e:
                    logger.error(f"Error destroying tentacles: {e}")
            
            # Signal that the animation is nearly complete at 90%
            if animation_progress >= 0.9 and not self.animation_near_complete:
                self.animation_near_complete = True
                logger.info("Boss death animation nearly complete")
                
                # Boss is fully destroyed, remove it from sprite groups
                self.kill()
                self.animation_complete = True
                logger.info("Boss death animation complete - 8 SECONDS COMPLETED, BOSS REMOVED")

        except Exception as e:
            logger.error(f"Error in boss death animation: {e}")
            # Failsafe: if animation errors, just remove the boss
            self.kill()
            self.animation_complete = True
    
    def _create_shockwave_effect(self, position=None, size=100, color=None):
        """Create a shockwave ring effect.
        
        Args:
            position: Center position for the shockwave, defaults to boss center
            size: Maximum size of the shockwave
            color: Base color for the shockwave
        """
        try:
            if hasattr(self, 'game_ref') and self.game_ref is not None:
                particles_group = getattr(self.game_ref, 'particles', None)
                
                # Use boss center if no position provided
                if position is None:
                    position = self.rect.center
                
                # Use white if no color provided
                if color is None:
                    color = (255, 255, 255)
                
                # Create color ranges with higher alpha at center
                r, g, b = color
                color_ranges = [
                        (max(0, r-30), min(255, r+30), max(0, g-30), min(255, g+30), max(0, b-30), min(255, b+30))
                ]
            
                # Create particles in a ring pattern
                num_particles = int(size / 2)
                for i in range(num_particles):
                    angle = random.uniform(0, math.pi * 2)
                    distance = size * 0.8  # Fixed distance for ring effect
                    
                    # Calculate position on the ring
                    x = int(position[0] + math.cos(angle) * distance)
                    y = int(position[1] + math.sin(angle) * distance)
                    
                    # Calculate direction (outward from center)
                    direction = (math.cos(angle), math.sin(angle))
                    
                    # Calculate speed for this particle
                    speed = random.uniform(1.0, 2.0)
                    velocity_x = direction[0] * speed
                    velocity_y = direction[1] * speed
                    
                    # Create particle
                    ParticleSystem.create_explosion(
                        position=(x, y),
                        count=1,
                        size_range=(3, 6),
                        color_ranges=color_ranges,
                        speed_range=(1.0, 2.0),  # This will be multiplied by direction internally
                        lifetime_range=(15, 30),
                        gravity=0.0,
                        group=particles_group
                    )
        except Exception as e:
            logger.error(f"Error creating shockwave effect: {e}")
    
    def _create_rainbow_stream_effect(self, position=None, intensity=1.0):
        """Create a stream of rainbow-colored particles from the boss.
        
        Args:
            position: Center position to emit particles from, defaults to boss center
            intensity: Controls the number and speed of particles (0.0-1.0)
        """
        try:
            if hasattr(self, 'game_ref') and self.game_ref is not None:
                particles_group = getattr(self.game_ref, 'particles', None)
            
                # Use boss center if no position provided
                if position is None:
                    position = self.rect.center
            
                # Check if we have too many particles already - stop creating more if over 80% capacity
                if RainbowParticle.active_particles > RainbowParticle.max_particles * 0.8:
                    return
            
                # Scale particle count with intensity - dramatically reduced count
                base_particle_count = 3  # Was 6
                particle_count = min(int(base_particle_count * intensity) + 1, 4)  # Cap at 4 particles 
                
                # Create streams in fewer directions for better performance
                directions = 6
                # Only use a subset of directions each time for variety
                direction_offset = random.randint(0, directions-1)
                actual_directions = min(directions, 4)  # Cap at 4 directions
            
                for i in range(actual_directions):
                    # Distribute directions evenly but with offset for variety
                    dir_idx = (direction_offset + i * (directions // actual_directions)) % directions
                    base_angle = (dir_idx * math.pi * 2 / directions)  # Evenly spaced angles
                
                    # For each direction, create a stream of particles with rainbow colors
                    for j in range(particle_count):
                        # Skip some particles randomly for better performance
                        if random.random() > 0.7:  # 30% chance to skip
                            continue
                            
                        # Randomize angle slightly within the direction
                        angle = base_angle + random.uniform(-0.2, 0.2)  # Reduced spread
                        
                        # Calculate randomized distance from center
                        distance = random.uniform(5, 30)  # Reduced range
                        
                        # Emission position (slightly randomized from center)
                        x = position[0] + math.cos(angle) * distance * 0.2
                        y = position[1] + math.sin(angle) * distance * 0.2
                        
                        # Direction vector
                        direction = (math.cos(angle), math.sin(angle))
                        
                        # Speed increases with intensity - reduced for performance
                        base_speed = 2.5 + (3.0 * intensity)  # Reduced base speed
                        speed = random.uniform(base_speed * 0.7, base_speed * 1.2)
                        velocity = (direction[0] * speed, direction[1] * speed)
                    
                        # Get rainbow color
                        color_index = (i + j) % len(BOSS_BULLET_COLORS)
                        color = BOSS_BULLET_COLORS[color_index]
                        
                        # Enhanced color - make it more vibrant
                        r, g, b = color
                        max_channel = max(r, g, b)
                        if max_channel > 0:
                            # Boost the dominant color channel to make colors more vibrant
                            boost_factor = 1.3
                            if r == max_channel:
                                r = min(255, int(r * boost_factor))
                            elif g == max_channel:
                                g = min(255, int(g * boost_factor))
                            elif b == max_channel:
                                b = min(255, int(b * boost_factor))
                        color = (r, g, b)
                        
                        # Larger size for more visibility but maintain performance
                        size = random.randint(5, 9)
                        
                        # Maintain optimized lifetime
                        lifetime = random.randint(int(30 * intensity), int(50 * intensity))
                        
                        # Maintain optimized trail length
                        trail_length = random.randint(3, 6)
                    
                        # Create rainbow particle
                        if particles_group:
                            RainbowParticle(
                                position=(x, y),
                                velocity=velocity,
                                color=color,
                                size=size,
                                lifetime=lifetime,
                                trail_length=trail_length,
                                particles_group=particles_group
                            )
            
                # Add fewer radial burst particles for better performance - reduced probability
                if intensity > 0.4 and random.random() < 0.4 and RainbowParticle.active_particles < RainbowParticle.max_particles * 0.7:
                    burst_count = min(int(8 * intensity), 10)
                    for _ in range(burst_count):
                        # Skip some particles randomly for performance
                        if random.random() > 0.7:  # 30% chance to skip
                            continue
                    
                        # Random angle (full 360 degrees)
                        angle = random.uniform(0, math.pi * 2)
                        
                        # Random distance from center
                        distance = random.uniform(15, 40)  # Reduced slightly
                        
                        # Emission position
                        x = position[0] + math.cos(angle) * distance * 0.3
                        y = position[1] + math.sin(angle) * distance * 0.3
                        
                        # Reduced velocity for better performance
                        speed = random.uniform(4.0, 7.0) * intensity  # Reduced from 6.0-10.0
                        velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
                        
                        # Random color from rainbow palette
                        color = BOSS_BULLET_COLORS[random.randint(0, len(BOSS_BULLET_COLORS) - 1)]
                        
                        # Moderate size, shorter lifetime
                        if particles_group:
                            RainbowParticle(
                                position=(x, y),
                                velocity=velocity,
                                color=color,
                                size=random.randint(4, 8),  # Reduced from 5-10
                                lifetime=random.randint(20, 40),  # Reduced from 25-50
                                trail_length=3,  # Reduced from 4
                                particles_group=particles_group
                            )
        except Exception as e:
            logger.error(f"Error creating rainbow stream effect: {e}")
    
    def _create_rainbow_mega_burst(self):
        """Create a spectacular burst of rainbow particles that fills the screen."""
        try:
            if hasattr(self, 'game_ref') and self.game_ref is not None:
                particles_group = getattr(self.game_ref, 'particles', None)
                
                if not particles_group:
                    return
                
                # Reduced number of emission centers for better performance
                num_centers = random.randint(2, 4)
                
                # Create multiple emission centers around the screen
                for _ in range(num_centers):
                    # Check if we have too many particles already
                    if RainbowParticle.active_particles > RainbowParticle.max_particles * 0.9:
                        return
                        
                    # Choose a position - biased toward the boss
                    if random.random() < 0.7:  # Increased chance to stay near boss
                        # Near boss
                        pos_x = self.rect.centerx + random.randint(-150, 150)  # Reduced range
                        pos_y = self.rect.centery + random.randint(-150, 150)  # Reduced range
                    else:
                        # Anywhere on screen
                        pos_x = random.randint(100, SCREEN_WIDTH - 100)
                        pos_y = random.randint(PLAYFIELD_TOP_Y + 50, PLAYFIELD_BOTTOM_Y - 50)
                    
                    # Ensure within screen bounds
                    pos_x = max(0, min(SCREEN_WIDTH, pos_x))
                    pos_y = max(PLAYFIELD_TOP_Y, min(PLAYFIELD_BOTTOM_Y, pos_y))
                    
                    # Create a moderate number of particles from this center
                    num_particles = random.randint(10, 15)  # Was 20-30
                    
                    for i in range(num_particles):
                        # Skip some particles randomly for performance
                        if random.random() > 0.8:  # 20% chance to skip
                            continue
                            
                        # Random angle in all directions
                        angle = random.uniform(0, math.pi * 2)
                        
                        # Moderate speed for good performance
                        speed = random.uniform(5.0, 9.0)
                        velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
                        
                        # Random rainbow color
                        color_index = (i * 397) % len(BOSS_BULLET_COLORS)  # Use prime number for better distribution
                        color = BOSS_BULLET_COLORS[color_index]
                        
                        # Enhance color vibrancy
                        r, g, b = color
                        max_channel = max(r, g, b)
                        if max_channel > 0:
                            # Boost the dominant color channel to make colors more vibrant
                            boost_factor = 1.3
                            if r == max_channel:
                                r = min(255, int(r * boost_factor))
                            elif g == max_channel:
                                g = min(255, int(g * boost_factor))
                            elif b == max_channel:
                                b = min(255, int(b * boost_factor))
                        color = (r, g, b)
                        
                        # Create particle with moderate trail but larger size
                        RainbowParticle(
                            position=(pos_x, pos_y),
                            velocity=velocity,
                            color=color,
                            size=random.randint(6, 12),
                            lifetime=random.randint(40, 80),
                            trail_length=random.randint(4, 7),
                            particles_group=particles_group
                        )
        except Exception as e:
            logger.error(f"Error creating rainbow mega burst: {e}")
    
    def _create_electrical_arc(self, start_pos, end_pos, color):
        """Create an electrical arc effect between two points.
        
        Args:
            start_pos: Starting position (x, y)
            end_pos: Ending position (x, y)
            color: Base color for the arc
        """
        try:
            if hasattr(self, 'game_ref') and self.game_ref is not None:
                particles_group = getattr(self.game_ref, 'particles', None)
                
                # Calculate distance and direction
                dx = end_pos[0] - start_pos[0]
                dy = end_pos[1] - start_pos[1]
                distance = math.sqrt(dx * dx + dy * dy)
                
                # Normalize direction
                if distance > 0:
                    dx /= distance
                    dy /= distance
                
                # Create jagged lightning effect with particles
                steps = int(distance / 5)  # One particle every ~5 pixels
                
                for i in range(steps):
                    # Calculate base position along the line
                    progress = i / steps
                    base_x = start_pos[0] + dx * distance * progress
                    base_y = start_pos[1] + dy * distance * progress
                    
                    # Add randomness for jagged effect
                    jag_amount = random.uniform(-10, 10)
                    perpendicular_x = -dy * jag_amount
                    perpendicular_y = dx * jag_amount
                    
                    x = base_x + perpendicular_x
                    y = base_y + perpendicular_y
                    
                    # Slightly vary the color
                    r, g, b = color
                    color_variation = random.uniform(0.9, 1.1)
                    particle_color = (
                        min(255, int(r * color_variation)),
                        min(255, int(g * color_variation)),
                        min(255, int(b * color_variation))
                    )
                    
                    # Create color ranges
                    color_ranges = [
                        (max(0, particle_color[0]-20), min(255, particle_color[0]+20),
                         max(0, particle_color[1]-20), min(255, particle_color[1]+20),
                         max(0, particle_color[2]-20), min(255, particle_color[2]+20))
                    ]
                    
                    # Create a particle at this point
                    if i % 2 == 0:  # Only place particles at every other step for performance
                        ParticleSystem.create_explosion(
                            position=(x, y),
                            count=1,
                            size_range=(2, 4),
                            color_ranges=color_ranges,
                            speed_range=(0.1, 0.5),
                            lifetime_range=(10, 20),
                            gravity=0.0,
                            group=particles_group
                        )
        except Exception as e:
            logger.error(f"Error creating electrical arc: {e}")
    
    def _apply_glitch_effect(self, intensity):
        """Apply a glitch/distortion effect to the boss image.
        
        Args:
            intensity: How strong the effect should be (0.0 to 1.0)
        """
        try:
            if intensity > 0:
                # Only apply if we actually have an image
                if self.image:
                    # Get the current image
                    current_image = self.image.copy()
                    width, height = current_image.get_size()
                    
                    # Create a new surface for the distorted image
                    distorted = pygame.Surface((width, height), pygame.SRCALPHA)
                    
                    # Apply random color shifts
                    if random.random() < intensity * 0.5:
                        # Choose a random color channel to amplify
                        channel = random.choice(["r", "g", "b"])
                        
                        # Get pixel array
                        pixel_array = pygame.surfarray.pixels3d(current_image)
                        
                        # Modify the chosen channel
                        if channel == "r":
                            pixel_array[:,:,0] = numpy.clip(pixel_array[:,:,0] * 1.5, 0, 255)
                        elif channel == "g":
                            pixel_array[:,:,1] = numpy.clip(pixel_array[:,:,1] * 1.5, 0, 255)
                        else:  # "b"
                            pixel_array[:,:,2] = numpy.clip(pixel_array[:,:,2] * 1.5, 0, 255)
                        
                        # Delete the array reference to update the surface
                        del pixel_array
                    
                    # Apply horizontal glitch lines
                    num_lines = int(intensity * 10)
                    for _ in range(num_lines):
                        y = random.randint(0, height-1)
                        line_height = random.randint(1, 5)
                        offset = random.randint(-10, 10)
                        
                        # Slice part of the image and shift it
                        if y + line_height < height:
                            slice_rect = pygame.Rect(0, y, width, line_height)
                            slice_surf = current_image.subsurface(slice_rect).copy()
                            distorted.blit(slice_surf, (offset, y))
                    
                    # Apply the distorted parts over the original image
                    current_image.blit(distorted, (0, 0), special_flags=pygame.BLEND_ADD)
                    self.image = current_image
        except Exception as e:
            logger.error(f"Error applying glitch effect: {e}")
    
    def take_damage(self, damage, hit_position=None):
        """Take damage and update health.
        
        Args:
            damage: Amount of damage to take
            hit_position: Optional position where the hit occurred for visual effects
            
        Returns:
            Boolean indicating if this damage defeated the boss
        """
        # Reduce boss health
        self.health -= damage
        
        # Clamp health to minimum of zero
        self.health = max(0, self.health)
        
        # Check for boss defeated
        if self.health <= 0 and not self.is_defeated:
            self.is_defeated = True
            self.death_animation_active = True
            self.animation_complete = False
            self.animation_near_complete = False
            self.death_animation_timer = 0
            
            # Play boss explosion sound when animation starts
            if hasattr(self, 'game_ref') and self.game_ref is not None and hasattr(self.game_ref, 'sound_manager'):
                try:
                    # Try with 'enemy' category first (what worked before)
                    logger.info("Attempting to play bossexplode1.ogg with category 'enemy'")
                    self.game_ref.sound_manager.play("bossexplode1", "enemy")
                except Exception as e:
                    # If that fails, try with other categories
                    logger.warning(f"Failed to play with 'enemy' category: {e}, trying alternatives")
                    try:
                        # Try with other common categories
                        self.game_ref.sound_manager.play("bossexplode1", "explosion")
                    except Exception:
                        try:
                            # Try with no category as last resort
                            self.game_ref.sound_manager.play("bossexplode1")
                        except Exception as e2:
                            logger.error(f"All attempts to play bossexplode1.ogg failed: {e2}")
            
            # Spawn Power Restore powerup
            if hasattr(self, 'game_ref') and self.game_ref is not None:
                try:
                    from src.powerup import PowerupType
                    from src.powerup_types import create_powerup

                    # Corrected arguments for create_powerup
                    powerup = create_powerup(
                        PowerupType.POWER_RESTORE,
                        self.rect.centerx,
                        self.rect.centery,
                        self.game_ref.all_sprites,  # Group 1
                        self.game_ref.powerups,     # Group 2
                        particles_group=self.game_ref.particles, # Keyword arg
                        game_ref=self.game_ref                   # Keyword arg
                    )
                except Exception as e:
                    logger.error(f"Error spawning Power Restore powerup: {e}")
            
            return True
        
        # Check for phase change based on health percentage
        health_percent = self.health / self.max_health
        
        # Update phase based on health percentage
        if health_percent <= 0.3 and self.phase < 3:
            new_phase = 3
            self.phase = new_phase
            logger.info(f"Boss advancing to phase {self.phase}")
        elif health_percent <= 0.6 and self.phase < 2:
            new_phase = 2
            self.phase = new_phase
            logger.info(f"Boss advancing to phase {self.phase}")
        
        return False
    
    def _create_defeat_explosion(self, explosions_group=None):
        """Create a spectacular multi-part explosion when the boss is defeated."""
        # Create multiple explosion centers around the boss
        try:
            num_explosions = 15
            explosion_centers = []
            
            # Create random positions for explosions
            for _ in range(num_explosions):
                offset_x = random.randint(-self.rect.width // 2, self.rect.width // 2)
                offset_y = random.randint(-self.rect.height // 2, self.rect.height // 2)
                
                # Random delay for cascade effect
                delay_ms = random.randint(0, 300)
                
                explosion_centers.append((self.rect.centerx + offset_x, self.rect.centery + offset_y, delay_ms))
            
            # Create explosions at different sizes for visual variety
            for x, y, delay in explosion_centers:
                # Apply the delay for cascade effect
                if delay > 0:
                    pygame.time.delay(delay)
                    
                # Randomize size for more visual interest - Bigger explosions
                scale = random.uniform(1.5, 3.5)
                size = (int(70 * scale), int(70 * scale))
                
                # Use safe group passing pattern
                if explosions_group:
                    explosion = Explosion((x, y), size, "enemy", explosions_group)
                else:
                    explosion = Explosion((x, y), size, "enemy")
                
                # Add smaller secondary explosions - use safe group passing
                if random.random() < 0.8:
                    for _ in range(random.randint(2, 4)):
                        # Define offsets INSIDE this loop to ensure they are bound
                        offset_x = random.randint(-40, 40)
                        offset_y = random.randint(-40, 40)
                        secondary_pos = (x + offset_x, y + offset_y)
                        secondary_size = (random.randint(20, 50), random.randint(20, 50))
                        if explosions_group:
                            secondary = Explosion(
                                secondary_pos, 
                                secondary_size, 
                                "enemy", 
                                explosions_group
                            )
                        else:
                            secondary = Explosion(
                                secondary_pos, 
                                secondary_size, 
                                "enemy",
                            )
        except Exception as e:
            logger.error(f"Error creating defeat explosion: {e}")

def create_boss(player) -> Boss:
    """Factory function to create a boss instance.
    
    Args:
        player: The player sprite
        
    Returns:
        A new Boss instance
    """
    # Create the boss without passing any groups - they'll be added later
    return Boss(player)
