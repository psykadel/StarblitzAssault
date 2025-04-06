"""Defines the player character (Starblitz fighter)."""

import pygame
import os
import random
import math
from typing import TYPE_CHECKING, Tuple, List, Optional, Dict, Any

# Import the Bullet class
from src.projectile import Bullet, LaserBeam, ScatterProjectile
# Import the sprite loading utility
from src.sprite_loader import load_sprite_sheet, DEFAULT_CROP_BORDER_PIXELS
# Import base animated sprite
from src.animated_sprite import AnimatedSprite
# Import logger
from src.logger import get_logger

# Import config variables
from config.game_config import (
    SPRITES_DIR, PLAYER_SPEED, PLAYER_SHOOT_DELAY, SCREEN_WIDTH,
    SCREEN_HEIGHT, PLAYFIELD_TOP_Y, PLAYFIELD_BOTTOM_Y,
    PLAYER_SCALE_FACTOR, PLAYER_ANIMATION_SPEED_MS, BULLET_SPEED
)

# Import powerup constants
from src.powerup import POWERUP_DURATION
# Import the new constants
from config.sprite_constants import PowerupType

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
        self.frames = load_sprite_sheet(
            filename="main-character.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=PLAYER_SCALE_FACTOR,
            crop_border=5 # Try a larger crop (was 4)
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
                if not hasattr(self, 'shield_pulse'): self.shield_pulse = 0
                self.shield_pulse = (self.shield_pulse + 0.1) % (2 * math.pi)
                pulse_value = 0.7 + 0.3 * math.sin(self.shield_pulse)
                
                # Calculate shield color with pulse
                shield_base_color = shield_state.get("color", (0, 100, 255)) # Default blue
                alpha = int(128 * pulse_value)
                shield_color = (
                    shield_base_color[0],
                    shield_base_color[1],
                    shield_base_color[2],
                    alpha
                )
                
                # Create shield surface
                shield_radius = shield_state.get("radius", 35)
                shield_size = int(shield_radius * 2 * pulse_value)
                shield_surface = pygame.Surface((shield_size, shield_size), pygame.SRCALPHA)
                
                # Draw shield
                pygame.draw.circle(
                    shield_surface,
                    shield_color,
                    (shield_size // 2, shield_size // 2),
                    shield_size // 2,
                    max(1, int(3 * pulse_value))  # Thickness
                )
                
                # Draw shield
                shield_rect = shield_surface.get_rect(center=self.rect.center)
                surface.blit(shield_surface, shield_rect)
            
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

        # Draw shield meter if shield is active (check state dict)
        shield_state = self.active_powerups_state.get(PowerupType.SHIELD.name)
        if shield_state:
            # Calculate shield percentage remaining from state
            current_time = pygame.time.get_ticks()
            expiry_time = shield_state.get("expiry_time", 0)
            duration = shield_state.get("duration", POWERUP_DURATION)
            time_remaining = max(0, expiry_time - current_time)
            shield_percent = time_remaining / duration if duration > 0 else 0
            
            # Draw shield meter background
            pygame.draw.rect(
                surface,
                (50, 50, 80),  # Dark blue-gray background
                (self.shield_meter_position[0], 
                 self.shield_meter_position[1], 
                 self.shield_meter_width, 
                 self.shield_meter_height)
            )
            
            # Draw shield meter fill
            filled_width = int(self.shield_meter_width * shield_percent)
            pygame.draw.rect(
                surface,
                (0, 140, 255),  # Shield blue
                (self.shield_meter_position[0], 
                 self.shield_meter_position[1], 
                 filled_width, 
                 self.shield_meter_height)
            )
            
            # Draw shield icon
            shield_icon_size = 12
            pygame.draw.circle(
                surface,
                (0, 100, 255),  # Shield color
                (self.shield_meter_position[0] - 10, 
                 self.shield_meter_position[1] + self.shield_meter_height // 2),
                shield_icon_size // 2,
                2  # Line width
            )

    def draw_powerup_icons(self, surface: pygame.Surface) -> None:
        """Draw icons for active powerups based on active_powerups_state."""
        # Check the state dictionary directly
        if not self.active_powerups_state:
            return
        
        current_time = pygame.time.get_ticks()
        
        # Position for effects panel - right side of power meter
        effects_panel_x = 10
        effects_panel_y = 110  # Below power meter
        
        # Font for powerup name and time - smaller text
        name_font = pygame.font.SysFont(None, 16)
        time_font = pygame.font.SysFont(None, 14)
        
        # Start position for the first powerup (directly at panel position since no header)
        start_y = effects_panel_y
        
        # Load powerup sprites if not already loaded
        if not hasattr(self, 'powerup_sprites'):
            self.powerup_sprites = []
            try:
                # Use the same function that powerups use to load their sprites
                from src.sprite_loader import load_sprite_sheet, DEFAULT_CROP_BORDER_PIXELS
                from src.powerup import POWERUP_SCALE_FACTOR, SPRITES_DIR
                
                self.powerup_sprites = load_sprite_sheet(
                    filename="powerups.png",
                    sprite_dir=SPRITES_DIR,
                    scale_factor=0.1,  # Smaller scale factor for icons
                    crop_border=DEFAULT_CROP_BORDER_PIXELS
                )
                
                # Resize all sprites to a consistent size for icons
                icon_size = 20
                for i, sprite in enumerate(self.powerup_sprites):
                    self.powerup_sprites[i] = pygame.transform.scale(sprite, (icon_size, icon_size))
                    
            except Exception as e:
                logger.error(f"Failed to load powerup sprites for icons: {e}")
                # Fallback to empty list, will use colors as fallback
                self.powerup_sprites = []
        
        # Powerup full names for display - use Enum names as keys
        display_names = {
            PowerupType.TRIPLE_SHOT.name: "TRIPLE SHOT",
            PowerupType.RAPID_FIRE.name: "RAPID FIRE",
            PowerupType.SHIELD.name: "SHIELD",
            PowerupType.HOMING_MISSILES.name: "HOMING MISSILES",
            # PowerupType.LASER_BEAM.name: "LASER BEAM", # Removed
            PowerupType.POWER_RESTORE.name: "POWER RESTORE", # Doesn't persist in state dict
            PowerupType.SCATTER_BOMB.name: "SCATTER BOMB",
            PowerupType.TIME_WARP.name: "TIME WARP",
            PowerupType.MEGA_BLAST.name: "MEGA BLAST" # Doesn't persist in state dict
        }
        
        # Colors as fallback - use Enum values for indexing
        colors = {
            PowerupType.TRIPLE_SHOT.value: (255, 220, 0),    # Golden
            PowerupType.RAPID_FIRE.value: (0, 255, 255),     # Cyan
            PowerupType.SHIELD.value: (0, 100, 255),     # Blue
            PowerupType.HOMING_MISSILES.value: (255, 0, 255),    # Magenta
            # PowerupType.LASER_BEAM.value: (0, 255, 0),      # Green (Removed)
            PowerupType.POWER_RESTORE.value: (255, 255, 255),  # White
            PowerupType.SCATTER_BOMB.value: (255, 128, 0),    # Orange
            PowerupType.TIME_WARP.value: (128, 0, 255),    # Purple
            PowerupType.MEGA_BLAST.value: (255, 0, 128),    # Pink
        }
        
        # Set a smaller icon size
        icon_size = 20
        spacing = 22
        
        # Draw each active powerup from the state dictionary
        # Iterate through a sorted list of powerup names for consistent order
        active_names_sorted = sorted(self.active_powerups_state.keys())

        for i, powerup_name in enumerate(active_names_sorted):
            powerup_state = self.active_powerups_state[powerup_name]
            powerup_idx = powerup_state.get("index", -1)

            if powerup_idx == -1:
                logger.warning(f"Powerup '{powerup_name}' in state dict missing index.")
                continue # Skip drawing this one

            # Calculate vertical position for this powerup
            icon_y = start_y + i * spacing
            
            # Use the actual powerup sprite if available
            if self.powerup_sprites and powerup_idx < len(self.powerup_sprites):
                # Get the correct sprite for this powerup type
                sprite = self.powerup_sprites[powerup_idx]
                
                # Position for the sprite icon
                icon_rect = sprite.get_rect(center=(
                    effects_panel_x + icon_size//2, 
                    icon_y + icon_size//2
                ))
                
                # Draw the sprite
                surface.blit(sprite, icon_rect)
            else:
                # Fallback to colored circle if sprites not available
                # Use Enum value to get color
                color = colors.get(powerup_idx, (128, 128, 128)) # Default grey
                
                # Create circular powerup icon
                pygame.draw.circle(
                    surface,
                    color,
                    (effects_panel_x + icon_size//2, icon_y + icon_size//2),
                    icon_size//2
                )
                
                # Inner highlight
                pygame.draw.circle(
                    surface,
                    (255, 255, 255),
                    (effects_panel_x + icon_size//2 - 2, icon_y + icon_size//2 - 2),
                    icon_size//4
                )
            
            # Get full display name
            display_name = display_names.get(powerup_name, powerup_name)
            
            # Draw powerup name with a small shadow for readability
            name_text = name_font.render(display_name, True, (255, 255, 255))
            name_shadow = name_font.render(display_name, True, (0, 0, 0))
            
            # Position name to the right of the icon
            name_x = effects_panel_x + icon_size + 5
            name_y = icon_y + 2
            
            # Draw name with shadow
            surface.blit(name_shadow, (name_x + 1, name_y + 1))
            surface.blit(name_text, (name_x, name_y))
            
            # Determine time remaining or charges from state
            time_remaining_str = None
            charges_str = None

            expiry_time = powerup_state.get("expiry_time")
            if expiry_time is not None:
                time_left_ms = max(0, expiry_time - current_time)
                time_remaining_str = f"{time_left_ms // 1000}s"
            
            charges = powerup_state.get("charges")
            if charges is not None:
                charges_str = f"{charges}"

            # Display charges for scatter bomb, time for others
            # Use Enum name for check
            if powerup_name == PowerupType.SCATTER_BOMB.name and charges_str is not None:
                status_text = time_font.render(charges_str, True, (255, 220, 150))
            elif time_remaining_str is not None:
                status_text = time_font.render(time_remaining_str, True, (200, 200, 200))
            else:
                # For powerups without time or charges (like Power Restore, though it shouldn't persist)
                status_text = time_font.render("Active", True, (200, 200, 200))
            
            # Position time/charge info below the name (on same line)
            status_x = name_x + name_text.get_width() + 5
            status_y = name_y
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
        state = {"index": powerup_idx}
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

        # Remove specific handling for Laser Beam
        # if powerup_name == PowerupType.LASER_BEAM.name:
        #      state["charge_level"] = 0
        #      state["max_charge"] = 100
        #      state["is_charging"] = False
        #      state.setdefault("color", (0, 255, 0)) # type: ignore
        
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
