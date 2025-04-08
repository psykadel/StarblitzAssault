"""Defines the player character (Starblitz fighter)."""

import pygame
import os
import random
import math
from typing import TYPE_CHECKING, Tuple, List, Optional, Dict, Any

# Import the Bullet class
from src.projectile import Bullet, LaserBeam, ScatterProjectile
# Import the sprite loading utility
from src.sprite_loader import load_sprite_sheet
# Import base animated sprite
from src.animated_sprite import AnimatedSprite
# Import logger
from src.logger import get_logger

# Import config variables
from config.config import (
    SPRITES_DIR, PLAYER_SPEED, PLAYER_SHOOT_DELAY, SCREEN_WIDTH,
    SCREEN_HEIGHT, PLAYFIELD_TOP_Y, PLAYFIELD_BOTTOM_Y,
    PLAYER_SCALE_FACTOR, PLAYER_ANIMATION_SPEED_MS, BULLET_SPEED,
    WHITE, RED, GREEN, YELLOW, POWERUP_SLOTS, POWERUP_ICON_SIZE,
    POWERUP_ICON_SPACING, POWERUP_DISPLAY_START_Y
)

# Import powerup constants
from src.powerup import POWERUP_DURATION
# Import the new constants
from src.powerup import PowerupType

# Get a logger for this module
logger = get_logger(__name__)

# Power level constants
MAX_POWER_LEVEL = 5
POWER_BAR_SCALE = 0.3
INVINCIBILITY_DURATION = 3000

class Player(AnimatedSprite):
    """Represents the player-controlled spaceship."""
    def __init__(self, bullets: pygame.sprite.Group, *groups, game_ref=None) -> None:
        """Initializes the player sprite."""
        super().__init__(PLAYER_ANIMATION_SPEED_MS, *groups)

        self.bullets = bullets
        self.game_ref = game_ref  # Store reference to the game instance
        
        # Load frames using the utility function
        self.load_sprites()
        
        # Speed of movement
        self.speed_x = 0
        self.speed_y = 0

        # Check if sprite loading was successful
        if not self.frames:
            logger.error("Player frames list is empty after loading!")
            raise SystemExit()

        # Set initial image from frames
        self.frame_index = 0
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)

        # Initial position for side-scroller (e.g., left middle)
        self.rect.left = 50
        self.rect.centery = SCREEN_HEIGHT // 2
        # Initialize float position trackers
        self._pos_x = float(self.rect.x)
        self._pos_y = float(self.rect.y)

        # Shooting cooldown timer
        self.last_shot_time: int = pygame.time.get_ticks()
        
        # Flag to track continuous firing state
        self.is_firing: bool = False
        
        # Power level system
        self.power_level = MAX_POWER_LEVEL
        self.previous_power_level = MAX_POWER_LEVEL
        self.is_alive = True
        
        # Power bar colors
        self.power_colors = [
            (255, 0, 0),      # Red (critical)
            (255, 128, 0),    # Orange (low)
            (255, 255, 0),    # Yellow (medium)
            (128, 255, 0),    # Yellow-Green (good)
            (0, 255, 0)       # Green (full)
        ]
        
        # Power bar dimensions
        self.power_bar_width = 200
        self.power_bar_height = 20
        self.power_bar_border = 2
        self.power_bar_position = (20, 15)
        
        # Power bar particle effect timer
        self.power_change_time = 0
        self.particle_cooldown = 200  # ms between particle bursts
        
        # Invincibility system
        self.is_invincible = False
        self.invincibility_timer = 0
        self.blink_counter = 0
        self.visible = True
        
        # Hit animation
        self.is_hit_animating = False
        self.hit_animation_start = 0
        self.hit_animation_duration = 500  # milliseconds
        self.original_image = None
        self.rotation_angle = 0
        
        # Shield meter (Visual only, logic driven by powerup state)
        self.shield_meter_width = 100
        self.shield_meter_height = 8
        self.shield_meter_position = (20, 90)  # Moved down from 70 to 90
        self.shield_max_value = POWERUP_DURATION 
        # self.shield_value = 0 # Shield value derived from state dict
        
        # Centralized Powerup State Management
        self.active_powerups_state: Dict[str, Dict[str, Any]] = {}
        # Example entry: "SHIELD": {"expiry_time": 15000, "index": 2}
        # Example entry: "SCATTER_BOMB": {"charges": 3, "index": 6}
        
        # Store original shoot method reference (used by some powerups)
        self.original_shoot_method = self.shoot 

        # Active powerup visual indicators (using icons)
        # self.active_powerups = [] # Replaced by active_powerups_state
        self.powerup_icon_size = 20
        self.powerup_icon_spacing = 5
        self.powerup_icon_base_y = 55  # Increased from 45 to 55 for more space below power bar

        # Remove individual powerup state flags and timers
        # self.has_triple_shot = False
        # self.triple_shot_expiry = 0
        # self.normal_shoot_delay = PLAYER_SHOOT_DELAY
        # self.has_rapid_fire = False
        # self.rapid_fire_expiry = 0
        # self.rapid_fire_delay = PLAYER_SHOOT_DELAY // 3
        # self.has_shield = False
        # self.shield_expiry = 0
        # self.shield_color = (0, 100, 255, 128)  # Semi-transparent blue
        # self.shield_radius = 35
        # self.shield_pulse = 0
        # self.has_homing_missiles = False
        # self.homing_missiles_expiry = 0
        # self.has_pulse_beam = False # Deprecated
        # self.pulse_beam_expiry = 0 # Deprecated
        # self.pulse_beam_charge = 0 # Deprecated
        # self.max_pulse_beam_charge = 100 # Deprecated
        # self.is_charging = False # Deprecated
        # self.has_laser_beam = False
        # self.laser_beam_expiry = 0
        # self.laser_beam_charge = 0
        # self.max_laser_beam_charge = 100
        # self.is_charging_laser = False
        # self.has_scatter_bomb = False
        # self.scatter_bomb_charges = 0
        # self.has_time_warp = False
        # self.time_warp_expiry = 0

    def load_sprites(self) -> None:
        """Loads animation frames using the utility function."""
        # Player sprite likely benefits from right-alignment for consistency
        self.frames = load_sprite_sheet(
            filename="main-character.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=PLAYER_SCALE_FACTOR,
            # crop_border=5 # No longer used
            alignment='right', # Explicitly state right alignment
            align_margin=5      # Keep a small margin from the right edge
        )
        # Error handling is done within load_sprite_sheet, which raises SystemExit
        
    def update(self) -> None:
        """Updates the player's position, animation, and handles continuous shooting."""
        # Skip update if player is dead
        if not self.is_alive:
            return
            
        # Update hit animation if active
        if self.is_hit_animating:
            current_time = pygame.time.get_ticks()
            elapsed = current_time - self.hit_animation_start
            
            if elapsed < self.hit_animation_duration:
                # Calculate rotation progress (0 to 360 degrees)
                progress = elapsed / self.hit_animation_duration
                self.rotation_angle = progress * 360
                
                # Store center before rotation
                center = self.rect.center
                
                # Rotate image only if original_image exists
                if self.original_image is not None:
                    # Rotate image
                    self.image = pygame.transform.rotate(self.original_image, self.rotation_angle)
                    
                    # Keep the same center
                    self.rect = self.image.get_rect(center=center)
                    
                    # Update mask for collision detection
                    self.mask = pygame.mask.from_surface(self.image)
                    
                    # Maintain alpha value during animation if invincible
                    if self.is_invincible and hasattr(self.image, 'get_alpha') and self.image.get_alpha() is not None:
                        self.image.set_alpha(self.image.get_alpha())
            else:
                # End animation
                self.is_hit_animating = False
                self.image = self.frames[self.frame_index]
                self.mask = pygame.mask.from_surface(self.image)
                
                # Maintain invincibility fade effect after animation ends
                if self.is_invincible and hasattr(self.image, 'set_alpha'):
                    # Get the current alpha from our fade calculation
                    current_time = pygame.time.get_ticks()
                    elapsed = current_time - self.invincibility_timer
                    cycle_position = (elapsed % 1500) / 1500.0
                    fade_factor = 0.5 + 0.5 * math.sin(cycle_position * 2 * math.pi)
                    alpha = int(40 + 180 * fade_factor)
                    self.image.set_alpha(alpha)
        else:
            # Call parent update for animation and movement
            super().update()
            
            # Apply fade effect to the new frame if invincible
            if self.is_invincible and hasattr(self.image, 'set_alpha'):
                current_time = pygame.time.get_ticks()
                elapsed = current_time - self.invincibility_timer
                cycle_position = (elapsed % 1500) / 1500.0
                fade_factor = 0.5 + 0.5 * math.sin(cycle_position * 2 * math.pi)
                alpha = int(40 + 180 * fade_factor)
                self.image.set_alpha(alpha)
        
        # Check if power level has changed
        if self.power_level != self.previous_power_level:
            # Record the time of power change for particle effects
            self.power_change_time = pygame.time.get_ticks()
            self.previous_power_level = self.power_level
        
        # Update position based on speed
        self._pos_x += self.speed_x
        self._pos_y += self.speed_y
        
        # Update rect from float position
        self.rect.x = round(self._pos_x)
        self.rect.y = round(self._pos_y)
        
        # Check for invincibility time out
        self._update_invincibility()
        
        # Check all powerup expirations
        self._check_powerup_expirations()
            
        # Check charging laser beam if active - LASER_BEAM removed
        # if PowerupType.LASER_BEAM.name in self.active_powerups_state and self.active_powerups_state[PowerupType.LASER_BEAM.name].get("is_charging", False):
        #     self._charge_laser_beam()
        
        # Use playfield boundaries for horizontal movement
        if self.rect.left < 0:
            self.rect.left = 0
            self._pos_x = float(self.rect.x)
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self._pos_x = float(self.rect.x)
        
        # Use playfield boundaries for vertical movement
        if self.rect.top < PLAYFIELD_TOP_Y:
            self.rect.top = PLAYFIELD_TOP_Y
            self._pos_y = float(self.rect.y)
        if self.rect.bottom > PLAYFIELD_BOTTOM_Y:
            self.rect.bottom = PLAYFIELD_BOTTOM_Y
            self._pos_y = float(self.rect.y)

        # Check for continuous shooting
        if self.is_firing:
            # Use triple shot if active, otherwise normal shot
            if "TRIPLE_SHOT" in self.active_powerups_state:
                self._shoot_triple()
            else:
                self.shoot() # shoot() already handles the cooldown based on powerup state

        # Update shield meter if shield is active (derived from state)
        # shield_value is calculated in draw method
        # if "SHIELD" in self.active_powerups_state:
        #     current_time = pygame.time.get_ticks()
        #     expiry = self.active_powerups_state["SHIELD"].get("expiry_time", 0)
        #     time_remaining = max(0, expiry - current_time)
        #     self.shield_value = time_remaining
        # else:
        #     self.shield_value = 0

    def start_firing(self) -> None:
        """Begins continuous firing."""
        self.is_firing = True
        
    def stop_firing(self) -> None:
        """Stops continuous firing."""
        self.is_firing = False

    def handle_input(self, event: pygame.event.Event) -> None:
        """Handles player input for movement (KEYDOWN/KEYUP). Shooting handled in update."""
        try:
            if event.type == pygame.KEYDOWN:
                # Adjusted for side-scroller (Up/Down primary)
                if event.key == pygame.K_UP:
                    self.speed_y = -PLAYER_SPEED
                elif event.key == pygame.K_DOWN:
                    self.speed_y = PLAYER_SPEED
                # Optional: Allow limited horizontal movement
                elif event.key == pygame.K_LEFT:
                    self.speed_x = -PLAYER_SPEED / 2 # Slower horizontal?
                elif event.key == pygame.K_RIGHT:
                    self.speed_x = PLAYER_SPEED / 2
                    
                # Special powerup controls
                # Check state dict for scatter bomb availability and charges
                scatter_state = self.active_powerups_state.get("SCATTER_BOMB")
                if event.key == pygame.K_b and scatter_state and scatter_state.get("charges", 0) > 0:
                    self._fire_scatter_bomb()
                # Check state dict for laser beam and set charging flag in state dict
                # LASER_BEAM removed
                # elif event.key == pygame.K_LSHIFT and PowerupType.LASER_BEAM.name in self.active_powerups_state:
                #     self.active_powerups_state[PowerupType.LASER_BEAM.name]["is_charging"] = True
                #     self.active_powerups_state[PowerupType.LASER_BEAM.name]["charge_level"] = 0 # Reset charge level

            if event.type == pygame.KEYUP:
                # Stop movement only if the released key matches the current direction
                if event.key == pygame.K_UP and self.speed_y < 0:
                    self.speed_y = 0
                elif event.key == pygame.K_DOWN and self.speed_y > 0:
                    self.speed_y = 0
                elif event.key == pygame.K_LEFT and self.speed_x < 0:
                    self.speed_x = 0
                elif event.key == pygame.K_RIGHT and self.speed_x > 0:
                    self.speed_x = 0
                    
                # Release charged beam - check state dict
                # LASER_BEAM removed
                # laser_state = self.active_powerups_state.get(PowerupType.LASER_BEAM.name)
                # if event.key == pygame.K_LSHIFT and laser_state and laser_state.get("is_charging", False):
                #     self._fire_laser_beam()
                #     laser_state["is_charging"] = False # Stop charging
        except Exception as e:
            logger.error(f"Error handling input: {e}")
            # Reset speeds to prevent getting stuck moving
            self.speed_x = 0
            self.speed_y = 0

    def shoot(self) -> None:
        """Creates a projectile sprite (bullet) firing forward."""
        now = pygame.time.get_ticks()
        # Use rapid fire delay if active, otherwise normal delay
        shoot_delay = self.active_powerups_state.get("RAPID_FIRE", {}).get("delay", PLAYER_SHOOT_DELAY)
        
        if now - self.last_shot_time > shoot_delay:
            self.last_shot_time = now
            # Bullet starts at the front-center of the player
            all_sprites_group = self.groups()[0] if self.groups() else None
            if all_sprites_group:
                # Create the bullet
                bullet = Bullet(self.rect.right, self.rect.centery, all_sprites_group, self.bullets)
                
                # Make bullet home in on enemies if that powerup is active
                if "HOMING_MISSILES" in self.active_powerups_state and self.game_ref:
                    # Find closest enemy
                    closest_enemy = None
                    closest_dist = float('inf')
                    
                    # Safely get the enemies group
                    enemies = getattr(self.game_ref, 'enemies', None)
                    
                    # Make sure enemies is iterable before trying to iterate
                    if enemies and hasattr(enemies, '__iter__'):
                        for enemy in enemies:
                            if hasattr(enemy, 'rect') and enemy.alive():
                                dist = ((enemy.rect.centerx - self.rect.centerx)**2 + 
                                       (enemy.rect.centery - self.rect.centery)**2)**0.5
                                if dist < closest_dist:
                                    closest_dist = dist
                                    closest_enemy = enemy
                    
                    if closest_enemy:
                        bullet.make_homing(closest_enemy)
                
                logger.debug(f"Player fired bullet at position {self.rect.right}, {self.rect.centery}")
            # The sound is now played in the game_loop when firing starts
    
    def _charge_pulse_beam(self) -> None:
        """Deprecated, replaced by _charge_laser_beam."""
        logger.warning("Pulse beam charging is deprecated.")

    def _charge_laser_beam(self) -> None:
        """Charge up the laser beam while key is held."""
        # LASER_BEAM removed - Method kept as placeholder, could be removed
        logger.warning("Laser beam charging is removed.")
        pass # No-op
        # laser_state = self.active_powerups_state.get(PowerupType.LASER_BEAM.name)
        # if not laser_state or not laser_state.get("is_charging", False):
        #     return # Not active or not charging
        # 
        # max_charge = laser_state.get("max_charge", 100)
        # current_charge = laser_state.get("charge_level", 0)
        # 
        # if current_charge < max_charge:
        #     laser_state["charge_level"] = current_charge + 2  # Charge rate
        #     current_charge = laser_state["charge_level"] # Update for particle logic
        #     
        #     # Create charging particles ... (removed)

    def _fire_pulse_beam(self) -> None:
        """Deprecated, replaced by _fire_laser_beam."""
        logger.warning("Pulse beam firing is deprecated.")

    def _fire_laser_beam(self) -> None:
        """Fire the charged laser beam."""
        # LASER_BEAM removed - Method kept as placeholder, could be removed
        logger.warning("Laser beam firing is removed.")
        pass # No-op
        # laser_state = self.active_powerups_state.get(PowerupType.LASER_BEAM.name)
        # if not laser_state:
        #     return # Laser beam not active
        # 
        # charge_level = laser_state.get("charge_level", 0)
        # max_charge = laser_state.get("max_charge", 100)
        # 
        # if charge_level < 10: # Minimum charge to fire
        #     laser_state["charge_level"] = 0 # Reset charge if too low
        #     return
        #     
        # # Calculate charge percentage ... (removed)
        # # Get sprite groups ... (removed)
        # # Play sound ... (removed)
        # laser_state["charge_level"] = 0
    
    def _fire_scatter_bomb(self) -> None:
        """Fire a scatter bomb that creates projectiles in all directions."""
        scatter_state = self.active_powerups_state.get("SCATTER_BOMB")
        if not scatter_state or scatter_state.get("charges", 0) <= 0:
            return # Not active or no charges
            
        # Reduce available charges in state
        scatter_state["charges"] -= 1
        charges_remaining = scatter_state["charges"]
        
        # If no charges left, remove from active powerups state
        if charges_remaining <= 0:
            # No need to check self.has_scatter_bomb flag
            if "SCATTER_BOMB" in self.active_powerups_state:
                del self.active_powerups_state["SCATTER_BOMB"]
            logger.info("Scatter Bomb depleted")
        
        # Get sprite groups
        all_sprites_group = self.groups()[0] if self.groups() else None
        if all_sprites_group:
            # Create scatter projectiles in all directions
            num_projectiles = 16  # Spread in 16 directions
            for i in range(num_projectiles):
                angle = (i / num_projectiles) * 2 * math.pi
                
                # Create scatter projectile
                ScatterProjectile(
                    self.rect.centerx, self.rect.centery,
                    angle, BULLET_SPEED * 0.75,
                    all_sprites_group, self.bullets
                )
            
            # Play sound
            if self.game_ref and hasattr(self.game_ref, 'sound_manager'):
                try:
                    self.game_ref.sound_manager.play("explosion2", "player")
                except Exception as e:
                    logger.warning(f"Failed to play explosion sound: {e}")
            
            logger.info(f"Fired scatter bomb. {charges_remaining} charges remaining")
            
    def take_damage(self) -> bool:
        """Reduces player's power level when hit.
        
        Returns:
            bool: True if player is still alive, False if game over
        """
        try:
            # Skip damage if player is invincible (standard invincibility)
            if self.is_invincible:
                logger.info("Hit ignored - player is invincible")
                return True
                
            # Skip damage if player has active shield powerup
            if "SHIELD" in self.active_powerups_state:
                logger.info("Hit ignored - player has active shield powerup")
                # Optionally add a shield hit effect here
                return True
                
            self.power_level -= 1
            logger.info(f"Player took damage! Power level: {self.power_level}/{MAX_POWER_LEVEL}")
            
            if self.power_level <= 0:
                self.is_alive = False
                logger.warning("Player power depleted! Game over!")
                return False
                
            # Activate invincibility after taking damage
            self.is_invincible = True
            self.invincibility_timer = pygame.time.get_ticks()
            self.blink_counter = 0
            self.visible = True  # Start visible
            
            # Start hit animation
            self.is_hit_animating = True
            self.hit_animation_start = pygame.time.get_ticks()
            # Make sure we have a valid image to rotate
            if self.image:
                self.original_image = self.image.copy()
            else:
                self.original_image = self.frames[self.frame_index].copy()
            self.rotation_angle = 0
            
            logger.info("Player invincibility activated for 3 seconds")
            return True
        except Exception as e:
            logger.error(f"Error in take_damage: {e}")
            # Return True as a fallback to prevent game crashes
            return True
        
    def get_power_bar_color(self) -> tuple:
        """Returns the current power bar color based on power level."""
        # Guard against invalid power level
        index = max(0, min(MAX_POWER_LEVEL - 1, self.power_level - 1))
        return self.power_colors[index]
        
    def should_emit_particles(self) -> bool:
        """Check if particles should be emitted from the power bar."""
        current_time = pygame.time.get_ticks()
        return (current_time - self.power_change_time < 1000 and 
                (current_time - self.power_change_time) % self.particle_cooldown < 50)
                
    def get_power_bar_particles_position(self) -> tuple:
        """Get the position for power bar particles."""
        # Calculate the current width of the filled power bar
        filled_width = (self.power_bar_width - self.power_bar_border * 2) * self.power_level / MAX_POWER_LEVEL
        
        # Position at the end of the filled portion
        x = self.power_bar_position[0] + self.power_bar_border + filled_width
        y = self.power_bar_position[1] + self.power_bar_height / 2
        
        return (x, y)
    
    def draw(self, surface: pygame.Surface) -> None:
        """Draw the player and any active powerup visuals."""
        # Only draw if player is visible (invincibility blinking)
        if self.visible:
            surface.blit(self.image, self.rect)
            
            # Draw shield if active (check state dict)
            shield_state = self.active_powerups_state.get(PowerupType.SHIELD.name)
            if shield_state:
                # Use shield_pulse from player instance for animation continuity
                if not hasattr(self, 'shield_pulse'): 
                    self.shield_pulse = 0
                    self.shield_particles = []
                    self.last_shield_particle_time = 0
                
                # Update shield pulse value
                self.shield_pulse = (self.shield_pulse + 0.1) % (2 * math.pi)
                pulse_value = 0.7 + 0.3 * math.sin(self.shield_pulse)
                
                # Calculate shield color with pulse
                shield_base_color = shield_state.get("color", (0, 100, 255)) # Default blue
                
                # Create shield surfaces with multiple layers for better effect
                shield_radius = shield_state.get("radius", 40)  # Increased radius
                shield_size = int(shield_radius * 2 * pulse_value)
                
                # Create main shield surface
                shield_surface = pygame.Surface((shield_size * 2, shield_size * 2), pygame.SRCALPHA)
                center = (shield_size, shield_size)
                
                # Draw multiple shield layers with different opacities
                # Outer glow layer
                pygame.draw.circle(
                    shield_surface,
                    (*shield_base_color, 40),  # Very transparent
                    center,
                    shield_size,
                    0  # Filled
                )
                
                # Middle layer
                pygame.draw.circle(
                    shield_surface,
                    (*shield_base_color, 80),  # Semi-transparent
                    center,
                    int(shield_size * 0.85),
                    0  # Filled
                )
                
                # Inner layer
                pygame.draw.circle(
                    shield_surface,
                    (*shield_base_color, 40),  # Semi-transparent
                    center,
                    int(shield_size * 0.7),
                    0  # Filled
                )
                
                # Draw shield border rings
                for i in range(3):
                    ring_size = shield_size - (i * 5)
                    if ring_size > 0:
                        pygame.draw.circle(
                            shield_surface,
                            (*shield_base_color, 160 - i * 30),  # Decreasing opacity
                            center,
                            ring_size,
                            max(1, int(3 * pulse_value))  # Thickness
                        )
                
                # Add energy arcs around the shield
                num_arcs = 8
                for i in range(num_arcs):
                    arc_angle = (i * (360 / num_arcs) + pygame.time.get_ticks() / 50) % 360
                    arc_start = arc_angle - 20
                    arc_end = arc_angle + 20
                    
                    # Calculate arc points
                    arc_points = []
                    for angle in range(int(arc_start), int(arc_end), 5):
                        rad = math.radians(angle)
                        x = center[0] + math.cos(rad) * shield_size
                        y = center[1] + math.sin(rad) * shield_size
                        arc_points.append((x, y))
                    
                    # Only draw if we have enough points
                    if len(arc_points) > 1:
                        pygame.draw.lines(
                            shield_surface,
                            (*shield_base_color, 200),  # More opaque
                            False,  # Don't connect first and last point
                            arc_points,
                            max(1, int(2 * pulse_value))  # Thickness
                        )
                
                # Add electric/energy effect (random small lines near the shield edge)
                num_energy_lines = int(10 * pulse_value)
                for _ in range(num_energy_lines):
                    # Random angle for the energy line
                    energy_angle = random.uniform(0, 360)
                    rad_angle = math.radians(energy_angle)
                    
                    # Inner point near shield edge
                    inner_dist = shield_size * 0.8
                    inner_x = center[0] + math.cos(rad_angle) * inner_dist
                    inner_y = center[1] + math.sin(rad_angle) * inner_dist
                    
                    # Outer point slightly outside shield edge
                    outer_dist = shield_size * 1.1
                    outer_x = center[0] + math.cos(rad_angle) * outer_dist
                    outer_y = center[1] + math.sin(rad_angle) * outer_dist
                    
                    # Draw the energy line
                    pygame.draw.line(
                        shield_surface,
                        (*shield_base_color, 180),
                        (inner_x, inner_y),
                        (outer_x, outer_y),
                        max(1, int(1 * pulse_value))  # Thickness
                    )
                
                # Create highlight effect
                highlight_angle = math.radians(45)  # Highlight at top-left
                highlight_x = center[0] + math.cos(highlight_angle) * (shield_size * 0.5)
                highlight_y = center[1] + math.sin(highlight_angle) * (shield_size * 0.5)
                highlight_size = shield_size // 4
                
                # Draw highlight with gradient
                for i in range(3):
                    highlight_alpha = 150 - (i * 40)
                    current_size = highlight_size - (i * 3)
                    if current_size > 0:
                        pygame.draw.circle(
                            shield_surface,
                            (255, 255, 255, highlight_alpha),
                            (int(highlight_x), int(highlight_y)),
                            current_size
                        )
                
                # Position shield around player
                shield_rect = shield_surface.get_rect(center=self.rect.center)
                surface.blit(shield_surface, shield_rect)
                
                # Create shield particles occasionally
                current_time = pygame.time.get_ticks()
                if current_time - getattr(self, 'last_shield_particle_time', 0) > 100:  # Every 100ms
                    self.last_shield_particle_time = current_time
                    
                    # Create 1-3 particles
                    for _ in range(random.randint(1, 3)):
                        # Random angle around the shield
                        particle_angle = random.uniform(0, 360)
                        rad_angle = math.radians(particle_angle)
                        
                        # Position on shield edge
                        shield_edge_dist = shield_size * random.uniform(0.9, 1.1)
                        particle_x = self.rect.centerx + math.cos(rad_angle) * shield_edge_dist
                        particle_y = self.rect.centery + math.sin(rad_angle) * shield_edge_dist
                        
                        # Create particle data
                        particle = {
                            'pos': [particle_x, particle_y],
                            'vel': [math.cos(rad_angle) * random.uniform(0.5, 1.5),
                                    math.sin(rad_angle) * random.uniform(0.5, 1.5)],
                            'size': random.randint(2, 5),
                            'life': random.randint(10, 30),
                            'age': 0,
                            'color': shield_base_color
                        }
                        
                        # Store in shield particles list
                        if not hasattr(self, 'shield_particles'):
                            self.shield_particles = []
                        self.shield_particles.append(particle)
                
                # Update and draw existing shield particles
                if hasattr(self, 'shield_particles'):
                    new_particles = []
                    for p in self.shield_particles:
                        # Update position
                        p['pos'][0] += p['vel'][0]
                        p['pos'][1] += p['vel'][1]
                        
                        # Update age
                        p['age'] += 1
                        
                        # Skip if too old
                        if p['age'] >= p['life']:
                            continue
                        
                        # Calculate fade
                        fade = 1 - (p['age'] / p['life'])
                        particle_alpha = int(200 * fade)
                        particle_size = max(1, int(p['size'] * fade))
                        
                        # Draw particle
                        pygame.draw.circle(
                            surface,
                            (*p['color'], particle_alpha),
                            (int(p['pos'][0]), int(p['pos'][1])),
                            particle_size
                        )
                        
                        # Keep particle for next frame
                        new_particles.append(p)
                    
                    # Update particles list
                    self.shield_particles = new_particles

        # Draw laser beam charge meter if charging (check state dict)
        # LASER_BEAM removed
        # laser_state = self.active_powerups_state.get(PowerupType.LASER_BEAM.name)
        # if laser_state and laser_state.get("is_charging", False):
        #     charge_level = laser_state.get("charge_level", 0)
        #     max_charge = laser_state.get("max_charge", 100)
        #     if charge_level > 0:
        #         charge_percent = charge_level / max_charge
        #         
        #         # Meter dimensions
        #         ...
        #         (meter_x, meter_y, filled_width, meter_height)
        #     )

        # REMOVE: Shield meter display removed to simplify UI
        # shield_state = self.active_powerups_state.get(PowerupType.SHIELD.name)
        # if shield_state:
        #     # Calculate shield percentage remaining from state
        #     current_time = pygame.time.get_ticks()
        #     expiry_time = shield_state.get("expiry_time", 0)
        #     duration = shield_state.get("duration", POWERUP_DURATION)
        #     time_remaining = max(0, expiry_time - current_time)
        #     shield_percent = time_remaining / duration if duration > 0 else 0
        #     
        #     # Draw shield meter background
        #     pygame.draw.rect(
        #         surface,
        #         (50, 50, 80),  # Dark blue-gray background
        #         (self.shield_meter_position[0], 
        #          self.shield_meter_position[1], 
        #          self.shield_meter_width, 
        #          self.shield_meter_height)
        #     )
        #     
        #     # Draw shield meter fill
        #     filled_width = int(self.shield_meter_width * shield_percent)
        #     pygame.draw.rect(
        #         surface,
        #         (0, 140, 255),  # Shield blue
        #         (self.shield_meter_position[0], 
        #          self.shield_meter_position[1], 
        #          filled_width, 
        #          self.shield_meter_height)
        #     )
        #     
        #     # Draw shield icon
        #     shield_icon_size = 12
        #     pygame.draw.circle(
        #         surface,
        #         (0, 100, 255),  # Shield color
        #         (self.shield_meter_position[0] - 10, 
        #          self.shield_meter_position[1] + self.shield_meter_height // 2),
        #         shield_icon_size // 2,
        #         2  # Line width
        #     )

    def draw_powerup_icons(self, surface: pygame.Surface) -> None:
        """Draw icons for active powerups based on active_powerups_state."""
        # Check the state dictionary directly
        if not self.active_powerups_state:
            return
        
        current_time = pygame.time.get_ticks()
        
        # Position for effects panel
        effects_panel_x = 15
        # Use the constant from config for the start Y position
        start_y = POWERUP_DISPLAY_START_Y
        
        # Create a list of active powerups to check for duplicates and ensure proper ordering
        active_powerups_list = []
        
        for name, state in self.active_powerups_state.items():
            powerup_idx = state.get("index", 999)
            active_powerups_list.append((name, state, powerup_idx))
        
        # Sort by name for consistent ordering regardless of when they were acquired
        active_powerups_list.sort(key=lambda x: x[0])
        
        # Set icon size from config
        icon_size = POWERUP_ICON_SIZE
        spacing = POWERUP_ICON_SPACING
        
        # Track time for animation effects
        animation_time = current_time / 1000  # Convert to seconds for easier math
        
        # Draw each active powerup in its designated slot
        # No need to limit the number of powerups since each has a fixed slot
        logger.debug(f"Drawing {len(active_powerups_list)} powerups")
        
        # Define the powerup colors - match the ones in powerup.py
        powerup_colors = {
            PowerupType.TRIPLE_SHOT.value: (255, 220, 0),    # Golden
            PowerupType.RAPID_FIRE.value: (0, 255, 255),     # Cyan
            PowerupType.SHIELD.value: (0, 100, 255),         # Blue
            PowerupType.HOMING_MISSILES.value: (255, 0, 255),# Magenta
            PowerupType.POWER_RESTORE.value: (0, 255, 0),    # Green
            PowerupType.SCATTER_BOMB.value: (255, 128, 0),   # Orange
            PowerupType.TIME_WARP.value: (128, 0, 255),      # Purple
            PowerupType.MEGA_BLAST.value: (255, 0, 128),     # Pink
        }
        
        # Powerup full names for display - use Enum names as keys
        display_names = {
            PowerupType.TRIPLE_SHOT.name: "TRIPLE SHOT",
            PowerupType.RAPID_FIRE.name: "RAPID FIRE",
            PowerupType.SHIELD.name: "SHIELD",
            PowerupType.HOMING_MISSILES.name: "HOMING MISSILES",
            PowerupType.POWER_RESTORE.name: "POWER RESTORE", # Doesn't persist in state dict
            PowerupType.SCATTER_BOMB.name: "SCATTER BOMB",
            PowerupType.TIME_WARP.name: "TIME WARP",
            PowerupType.MEGA_BLAST.name: "MEGA BLAST" # Doesn't persist in state dict
        }
        
        # Font for powerup name and time
        name_font = pygame.font.SysFont(None, 18)
        time_font = pygame.font.SysFont(None, 16)
        
        # Track used slots for debug purposes
        used_slots = set()
        
        for powerup_name, powerup_state, powerup_idx in active_powerups_list:
            # Map each powerup name to its dedicated slot from config
            # Instant powerups don't get displayed, so no need to worry about them
            slot = POWERUP_SLOTS.get(powerup_name, 999)  # Use 999 as fallback for unknown powerups
            
            if slot in used_slots:
                logger.warning(f"Duplicate slot {slot} for powerup {powerup_name}")
            used_slots.add(slot)
            
            # Calculate Y position based on slot index
            icon_y = start_y + slot * spacing
            
            logger.debug(f"Powerup {powerup_name} drawing at position y={icon_y}, slot={slot}")
            
            # Create a special effect surface for this powerup
            icon_surface = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
            
            # Get color for this powerup
            color = powerup_colors.get(powerup_idx, (128, 128, 128))  # Default to gray if not found
            
            # Create animation values - use consistent seed for each powerup type
            pulse = 0.7 + 0.3 * math.sin(animation_time * 2 + powerup_idx)  # Unique phase for each powerup
            rotation = (animation_time * 15 + powerup_idx * 45) % 360  # Different rotation for each powerup
            
            # Draw special effect icon based on powerup type
            if powerup_name == PowerupType.TRIPLE_SHOT.name:
                # Triple golden rays
                center = (icon_size // 2, icon_size // 2)
                for angle in range(0, 360, 120):
                    # Calculate ray endpoints
                    ray_angle = math.radians(angle + rotation)
                    ray_length = icon_size * 0.4 * pulse
                    end_x = center[0] + math.cos(ray_angle) * ray_length
                    end_y = center[1] + math.sin(ray_angle) * ray_length
                    # Draw ray
                    pygame.draw.line(
                        icon_surface,
                        color,
                        center,
                        (end_x, end_y),
                        max(1, int(icon_size // 8))
                    )
                # Add central glow
                pygame.draw.circle(icon_surface, color, center, int(icon_size // 4))
                pygame.draw.circle(icon_surface, (255, 255, 255, 150), 
                                  (center[0] - 2, center[1] - 2), int(icon_size // 8))
                
            elif powerup_name == PowerupType.RAPID_FIRE.name:
                # Lightning-like effect
                center = (icon_size // 2, icon_size // 2)
                # Use fixed angles for more consistency
                lightning_angles = [0, 60, 120, 180, 240, 300]
                for angle_base in lightning_angles:
                    angle = math.radians(angle_base + rotation)
                    start_x = center[0] + math.cos(angle) * (icon_size // 8)
                    start_y = center[1] + math.sin(angle) * (icon_size // 8)
                    
                    # Create zigzag lightning
                    points = [(start_x, start_y)]
                    current_angle = angle
                    segment_length = icon_size // 6
                    
                    # Use fixed seed for each lightning bolt
                    local_random = random.Random(angle_base + powerup_idx * 100)
                    
                    for _ in range(3):
                        # Randomize angle for zigzag effect
                        current_angle += math.radians(local_random.uniform(-30, 30))
                        next_x = points[-1][0] + math.cos(current_angle) * segment_length
                        next_y = points[-1][1] + math.sin(current_angle) * segment_length
                        points.append((next_x, next_y))
                    
                    # Draw the lightning bolt
                    if len(points) > 1:
                        pygame.draw.lines(icon_surface, color, False, points, max(1, icon_size // 12))
                
                # Add central glow
                pygame.draw.circle(icon_surface, (*color, 180), center, int(icon_size // 4))
                
            elif powerup_name == PowerupType.SHIELD.name:
                # Shield bubble effect
                center = (icon_size // 2, icon_size // 2)
                shield_radius = int(icon_size // 2 * pulse)
                
                # Draw shield circle
                pygame.draw.circle(
                    icon_surface,
                    (*color, 180),
                    center,
                    shield_radius,
                    max(1, int(icon_size // 10))
                )
                
                # Add inner glow
                pygame.draw.circle(
                    icon_surface,
                    (*color, 100),
                    center,
                    max(1, shield_radius - 2)
                )
                
                # Add highlight
                highlight_pos = (center[0] - shield_radius//3, center[1] - shield_radius//3)
                pygame.draw.circle(
                    icon_surface,
                    (255, 255, 255, 150),
                    highlight_pos,
                    max(1, shield_radius // 4)
                )
                
            elif powerup_name == PowerupType.HOMING_MISSILES.name:
                # Target-like icon
                center = (icon_size // 2, icon_size // 2)
                
                # Draw concentric circles (target)
                circle_sizes = [icon_size // 2, icon_size // 3, icon_size // 5]
                for r in circle_sizes:
                    pygame.draw.circle(
                        icon_surface,
                        (*color, 150),
                        center,
                        r,
                        max(1, int(icon_size // 12))
                    )
                
                # Draw crosshairs
                line_length = icon_size // 2 * pulse
                for angle in [0, 90, 180, 270]:
                    rad_angle = math.radians(angle + rotation)
                    end_x = center[0] + math.cos(rad_angle) * line_length
                    end_y = center[1] + math.sin(rad_angle) * line_length
                    pygame.draw.line(
                        icon_surface,
                        (*color, 200),
                        center,
                        (end_x, end_y),
                        max(1, int(icon_size // 12))
                    )
                
            elif powerup_name == PowerupType.POWER_RESTORE.name:
                # Health/power cross
                center = (icon_size // 2, icon_size // 2)
                width = max(2, int(icon_size // 6))
                length = int(icon_size * 0.7 * pulse)
                
                # Vertical line
                pygame.draw.rect(
                    icon_surface,
                    (*color, 220),
                    (center[0] - width//2, center[1] - length//2, width, length)
                )
                # Horizontal line
                pygame.draw.rect(
                    icon_surface,
                    (*color, 220),
                    (center[0] - length//2, center[1] - width//2, length, width)
                )
                
                # Add glow
                pygame.draw.circle(
                    icon_surface,
                    (*color, 100),
                    center,
                    int(icon_size // 3)
                )
                
            elif powerup_name == PowerupType.SCATTER_BOMB.name:
                # Explosion-like rays
                center = (icon_size // 2, icon_size // 2)
                
                # Draw explosion rays
                for angle in range(0, 360, 45):
                    ray_angle = math.radians(angle + rotation)
                    ray_length = icon_size * 0.4 * pulse
                    end_x = center[0] + math.cos(ray_angle) * ray_length
                    end_y = center[1] + math.sin(ray_angle) * ray_length
                    
                    # Draw the ray
                    pygame.draw.line(
                        icon_surface,
                        color,
                        center,
                        (end_x, end_y),
                        max(1, int(icon_size // 8))
                    )
                    
                    # Add secondary rays with fixed pattern
                    branch_angle = ray_angle + math.radians(20)
                    branch_end_x = end_x + math.cos(branch_angle) * (ray_length * 0.3)
                    branch_end_y = end_y + math.sin(branch_angle) * (ray_length * 0.3)
                    
                    pygame.draw.line(
                        icon_surface,
                        color,
                        (end_x, end_y),
                        (branch_end_x, branch_end_y),
                        max(1, int(icon_size // 10))
                    )
                
                # Add central glow
                pygame.draw.circle(icon_surface, (*color, 200), center, int(icon_size // 4))
                
            elif powerup_name == PowerupType.TIME_WARP.name:
                # Clock-like pattern
                center = (icon_size // 2, icon_size // 2)
                
                # Draw clock face
                pygame.draw.circle(
                    icon_surface,
                    (*color, 150),
                    center,
                    int(icon_size // 2 * 0.8 * pulse),
                    max(1, int(icon_size // 10))
                )
                
                # Draw clock hands
                # Hour hand
                hour_angle = math.radians(rotation)
                hour_length = icon_size * 0.25
                hour_end_x = center[0] + math.cos(hour_angle) * hour_length
                hour_end_y = center[1] + math.sin(hour_angle) * hour_length
                pygame.draw.line(
                    icon_surface,
                    (*color, 220),
                    center,
                    (hour_end_x, hour_end_y),
                    max(1, int(icon_size // 8))
                )
                
                # Minute hand
                minute_angle = math.radians(rotation * 12)  # Faster rotation
                minute_length = icon_size * 0.35
                minute_end_x = center[0] + math.cos(minute_angle) * minute_length
                minute_end_y = center[1] + math.sin(minute_angle) * minute_length
                pygame.draw.line(
                    icon_surface,
                    (*color, 220),
                    center,
                    (minute_end_x, minute_end_y),
                    max(1, int(icon_size // 12))
                )
                
                # Central dot
                pygame.draw.circle(
                    icon_surface,
                    color,
                    center,
                    max(1, int(icon_size // 10))
                )
                
            elif powerup_name == PowerupType.MEGA_BLAST.name:
                # Starburst pattern
                center = (icon_size // 2, icon_size // 2)
                
                # Draw star rays
                num_rays = 8
                for i in range(num_rays):
                    angle = math.radians(i * (360 / num_rays) + rotation)
                    length = icon_size * 0.4 * pulse
                    
                    # Main ray points
                    inner_x = center[0] + math.cos(angle) * (length * 0.3)
                    inner_y = center[1] + math.sin(angle) * (length * 0.3)
                    outer_x = center[0] + math.cos(angle) * length
                    outer_y = center[1] + math.sin(angle) * length
                    
                    # Draw with thickness gradient
                    for w in range(3, 0, -1):
                        pygame.draw.line(
                            icon_surface,
                            (*color, 200 - (w * 30)),
                            (inner_x, inner_y),
                            (outer_x, outer_y),
                            max(1, w)
                        )
                    
                    # Add glow at the tip
                    pygame.draw.circle(
                        icon_surface,
                        (*color, 150),
                        (int(outer_x), int(outer_y)),
                        max(1, int(icon_size // 10))
                    )
                
                # Central glow
                pygame.draw.circle(
                    icon_surface,
                    (*color, 200),
                    center,
                    int(icon_size // 5)
                )
                
            else:
                # Generic powerup glow for any other types
                center = (icon_size // 2, icon_size // 2)
                
                # Draw concentric circles with decreasing alpha
                for radius in range(int(icon_size // 2), 0, -2):
                    alpha = int(200 * (radius / (icon_size // 2)))
                    pygame.draw.circle(
                        icon_surface,
                        (*color, alpha),
                        center,
                        radius
                    )
                
                # Add highlight
                highlight_pos = (center[0] - icon_size//6, center[1] - icon_size//6)
                pygame.draw.circle(
                    icon_surface,
                    (255, 255, 255, 150),
                    highlight_pos,
                    max(1, int(icon_size // 6))
                )
            
            # Position for the icon
            icon_rect = icon_surface.get_rect(midleft=(
                effects_panel_x, 
                icon_y
            ))
            
            # Draw the special effect icon
            surface.blit(icon_surface, icon_rect)
            
            # Get full display name
            display_name = display_names.get(powerup_name, powerup_name)
            
            # Draw powerup name with a small shadow for readability
            name_text = name_font.render(display_name, True, (255, 255, 255))
            name_shadow = name_font.render(display_name, True, (0, 0, 0))
            
            # Position name to the right of the icon
            name_x = effects_panel_x + icon_size + 5
            name_y = icon_y - 10  # Vertically center with icon
            
            # Draw name with shadow
            surface.blit(name_shadow, (name_x + 1, name_y + 1))
            surface.blit(name_text, (name_x, name_y))
            
            # Determine time remaining or charges from state
            time_remaining_str = None
            charges_str = None

            expiry_time = powerup_state.get("expiry_time")
            if expiry_time is not None:
                time_left_ms = max(0, expiry_time - current_time)
                # Ensure integer division for seconds display
                time_remaining_str = f"{time_left_ms // 1000}s"
            
            charges = powerup_state.get("charges")
            if charges is not None:
                charges_str = f"{charges}"

            # Display charges for scatter bomb, time for others
            if powerup_name == PowerupType.SCATTER_BOMB.name and charges_str is not None:
                status_text = time_font.render(charges_str, True, (255, 220, 150))
                # Position directly under the name
                status_x = name_x
                status_y = name_y + name_text.get_height() + 2
            elif time_remaining_str is not None:
                status_text = time_font.render(time_remaining_str, True, (200, 200, 200))
                # Position directly under the name
                status_x = name_x
                status_y = name_y + name_text.get_height() + 2
            else:
                # For powerups without time or charges (like Power Restore, though it shouldn't persist)
                status_text = time_font.render("Active", True, (200, 200, 200))
                # Position directly under the name
                status_x = name_x
                status_y = name_y + name_text.get_height() + 2
            
            # Draw status text
            surface.blit(status_text, (status_x, status_y))

    def _shoot_triple(self) -> None:
        """Shoots three bullets in a spread pattern (triple shot powerup)."""
        now = pygame.time.get_ticks()
        # Use rapid fire delay if active (check state dict, use Enum name)
        shoot_delay = self.active_powerups_state.get(PowerupType.RAPID_FIRE.name, {}).get("delay", PLAYER_SHOOT_DELAY)
        
        if now - self.last_shot_time > shoot_delay:
            self.last_shot_time = now
            
            # Get first sprite group (usually all_sprites)
            all_sprites_group = self.groups()[0] if self.groups() else None
            
            if all_sprites_group:
                # Create three bullets: one straight ahead, one angled up, one angled down
                bullets = [
                    Bullet(self.rect.right, self.rect.centery, all_sprites_group, self.bullets),  # Center
                    Bullet(self.rect.right, self.rect.centery - 5, all_sprites_group, self.bullets),  # Top
                    Bullet(self.rect.right, self.rect.centery + 5, all_sprites_group, self.bullets)   # Bottom
                ]
                
                # Add vertical velocity component to the upper and lower bullets
                bullets[1].velocity_y = -2.0  # Upward
                bullets[2].velocity_y = 2.0   # Downward
                
                # Apply homing to all bullets if that powerup is also active (check state dict, use Enum name)
                if PowerupType.HOMING_MISSILES.name in self.active_powerups_state and self.game_ref:
                    # Find closest enemy
                    closest_enemy = None
                    closest_dist = float('inf')
                    
                    # Safely get the enemies group
                    enemies = getattr(self.game_ref, 'enemies', None)
                    
                    # Make sure enemies is iterable before trying to iterate
                    if enemies and hasattr(enemies, '__iter__'):
                        # Find closest enemy
                        for enemy in enemies:
                            if hasattr(enemy, 'rect') and enemy.alive():
                                dist = ((enemy.rect.centerx - self.rect.centerx)**2 + 
                                       (enemy.rect.centery - self.rect.centery)**2)**0.5
                                if dist < closest_dist:
                                    closest_dist = dist
                                    closest_enemy = enemy
                                    
                        # If we found an enemy, make all bullets home in on it
                        if closest_enemy:
                            for bullet in bullets:
                                bullet.make_homing(closest_enemy)
                                
                logger.debug(f"Player fired triple shot at {self.rect.right}, {self.rect.centery}")
                
    def _update_invincibility(self) -> None:
        """Updates invincibility status."""
        current_time = pygame.time.get_ticks()
        if self.is_invincible:
            if current_time - self.invincibility_timer > INVINCIBILITY_DURATION:
                self.is_invincible = False
                self.visible = True  # Ensure player is visible when invincibility ends
                
                # Reset alpha to full opacity for current image and all frames
                if hasattr(self.image, 'set_alpha'):
                    self.image.set_alpha(255)
                
                # Also reset all animation frames to full opacity
                for frame in self.frames:
                    if hasattr(frame, 'set_alpha'):
                        frame.set_alpha(255)
            else:
                # Calculate fade effect - smooth sine wave between 40 and 220 alpha
                # The frequency is slow enough to make it a smooth fade
                elapsed = current_time - self.invincibility_timer
                # 1.5 second cycle for fade in/out
                cycle_position = (elapsed % 1500) / 1500.0
                # Sine wave oscillation from 0 to 1
                fade_factor = 0.5 + 0.5 * math.sin(cycle_position * 2 * math.pi)
                # Map to alpha range 40-220 (never completely invisible or fully visible)
                alpha = int(40 + 180 * fade_factor)
                
                # Apply alpha to the image
                if hasattr(self.image, 'set_alpha'):
                    self.image.set_alpha(alpha)
                
                # Always keep visible flag true so image is drawn (with varying alpha)
                self.visible = True

    def _check_powerup_expirations(self) -> None:
        """Checks and handles powerup expirations based on active_powerups_state."""
        current_time = pygame.time.get_ticks()
        expired_powerups = []

        # Make a copy of keys to iterate over, as we might modify the dict
        powerup_names = list(self.active_powerups_state.keys())

        for powerup_name in powerup_names:
            state = self.active_powerups_state.get(powerup_name)
            if not state: continue # Should not happen if iterating keys, but safe check

            expiry_time = state.get("expiry_time")
            if expiry_time is not None and current_time > expiry_time:
                expired_powerups.append(powerup_name)
        
        for powerup_name in expired_powerups:
            logger.info(f"{powerup_name} powerup expired")
            # Remove the expired powerup from the state dictionary
            if powerup_name in self.active_powerups_state:
                 # Get the state again safely before potentially deleting the key
                 state_to_cleanup = self.active_powerups_state.get(powerup_name)
                 del self.active_powerups_state[powerup_name]
                 
                 # Specific cleanup if needed (e.g., reset rapid fire delay)
                 if powerup_name == "RAPID_FIRE":
                     # Shoot delay will default back to PLAYER_SHOOT_DELAY in shoot() 
                     # when "RAPID_FIRE" key is not found in dict.
                     pass 
                 # LASER_BEAM Removed
                 # elif powerup_name == PowerupType.LASER_BEAM.name and state_to_cleanup:
                 #     # Ensure charging stops if expired mid-charge
                 #     if state_to_cleanup.get("is_charging", False):
                 #          state_to_cleanup["is_charging"] = False
                 #          state_to_cleanup["charge_level"] = 0

            # Note: Time Warp effect removal is handled in game_loop update based on player state

    def add_powerup(self, powerup_name: str, powerup_idx: int, 
                    duration_ms: Optional[int] = POWERUP_DURATION, 
                    charges: Optional[int] = None,
                    extra_state: Optional[Dict[str, Any]] = None) -> None:
        """Adds or refreshes a powerup in the active state dictionary.

        Args:
            powerup_name: The unique string identifier (e.g., "SHIELD").
            powerup_idx: The index corresponding to the icon/sprite (0-8).
            duration_ms: Duration in milliseconds (for timed powerups).
            charges: Number of uses (for charge-based powerups).
            extra_state: Dictionary with any additional state (e.g., rapid fire delay).
        """
        current_time = pygame.time.get_ticks()
        # Check if this powerup has a dedicated display slot, which ensures consistent display
        # Try to find its slot based on its name in the POWERUP_SLOTS dictionary
        slot = POWERUP_SLOTS.get(powerup_name, None)
        
        # Create the state dictionary with the index and slot (if available)
        state = {"index": powerup_idx}
        if slot is not None:
            state["slot"] = slot
            
        is_refresh = powerup_name in self.active_powerups_state

        if duration_ms is not None:
            state["expiry_time"] = current_time + duration_ms
            state["duration"] = duration_ms # Store original duration for UI

        if charges is not None:
            # If refreshing, add charges; otherwise, set initial charges.
            current_charges = self.active_powerups_state.get(powerup_name, {}).get("charges", 0)
            state["charges"] = current_charges + charges if is_refresh else charges

        if extra_state:
            state.update(extra_state)
            
        # Specific handling for Shield state - Use Enum name
        if powerup_name == PowerupType.SHIELD.name:
             state.setdefault("color", (0, 100, 255)) # type: ignore
             state.setdefault("radius", 35)

        self.active_powerups_state[powerup_name] = state

        if is_refresh:
            if charges is not None:
                logger.info(f"Added {charges} charges to {powerup_name}, now {state['charges']}")
            else:
                logger.info(f"Refreshed duration for {powerup_name}")
        else:
            logger.info(f"Activated new powerup: {powerup_name}")

        # Ensure powerups that provide abilities but don't have inherent state
        # (like Homing Missiles, Triple Shot) are still added to the dict
        # even if duration_ms and charges are None.
        if duration_ms is None and charges is None:
            if powerup_name not in self.active_powerups_state:
                 self.active_powerups_state[powerup_name] = state
                 logger.info(f"Activated passive powerup: {powerup_name}")

    # Clean up old powerup tracking list method (no longer needed)
    # def add_powerup_old(self, powerup_name: str, powerup_idx: int) -> None:
    #     """Add a powerup to the active powerups list, preventing duplicates."""
    # ... (old implementation removed)
