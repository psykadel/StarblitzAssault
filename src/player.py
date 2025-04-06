"""Defines the player character (Starblitz fighter)."""

import pygame
import os
import random
import math
from typing import TYPE_CHECKING, Tuple, List, Optional, Dict, Any

# Import the Bullet class
from src.projectile import Bullet, PulseBeam, ScatterProjectile
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
        
        # Shield meter
        self.shield_meter_width = 100
        self.shield_meter_height = 8
        self.shield_meter_position = (20, 90)  # Moved down from 70 to 90
        self.shield_max_value = POWERUP_DURATION  # Import this from powerup.py
        self.shield_value = 0
        
        # Powerup state
        self.original_shoot = self.shoot  # Store reference to original shoot method
        self.has_triple_shot = False
        self.triple_shot_expiry = 0
        
        self.normal_shoot_delay = PLAYER_SHOOT_DELAY
        self.has_rapid_fire = False
        self.rapid_fire_expiry = 0
        self.rapid_fire_delay = PLAYER_SHOOT_DELAY // 3
        
        self.has_shield = False
        self.shield_expiry = 0
        self.shield_color = (0, 100, 255, 128)  # Semi-transparent blue
        self.shield_radius = 35
        self.shield_pulse = 0
        
        self.has_homing_missiles = False
        self.homing_missiles_expiry = 0
        
        self.has_pulse_beam = False
        self.pulse_beam_expiry = 0
        self.pulse_beam_charge = 0
        self.max_pulse_beam_charge = 100
        self.is_charging = False
        
        self.has_scatter_bomb = False
        self.scatter_bomb_charges = 0
        
        self.has_time_warp = False
        self.time_warp_expiry = 0
        
        # Active powerup visual indicators
        self.active_powerups = []
        self.powerup_icon_size = 20
        self.powerup_icon_spacing = 5
        self.powerup_icon_base_y = 55  # Increased from 45 to 55 for more space below power bar

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
        
        # Check charging pulse beam if active
        if self.has_pulse_beam and self.is_charging:
            self._charge_pulse_beam()
        
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
            if self.has_triple_shot:
                self._shoot_triple()
            else:
                self.shoot() # shoot() already handles the cooldown

        # Update shield meter if shield is active
        if self.has_shield:
            current_time = pygame.time.get_ticks()
            time_remaining = max(0, self.shield_expiry - current_time)
            self.shield_value = time_remaining
        else:
            self.shield_value = 0

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
                elif event.key == pygame.K_b and self.has_scatter_bomb and self.scatter_bomb_charges > 0:
                    self._fire_scatter_bomb()
                elif event.key == pygame.K_LSHIFT and self.has_pulse_beam:
                    self.is_charging = True
                    self.pulse_beam_charge = 0

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
                    
                # Release charged beam
                elif event.key == pygame.K_LSHIFT and self.has_pulse_beam and self.is_charging:
                    self._fire_pulse_beam()
                    self.is_charging = False
        except Exception as e:
            logger.error(f"Error handling input: {e}")
            # Reset speeds to prevent getting stuck moving
            self.speed_x = 0
            self.speed_y = 0

    def shoot(self) -> None:
        """Creates a projectile sprite (bullet) firing forward."""
        now = pygame.time.get_ticks()
        # Use rapid fire delay if active
        shoot_delay = self.rapid_fire_delay if self.has_rapid_fire else self.normal_shoot_delay
        
        if now - self.last_shot_time > shoot_delay:
            self.last_shot_time = now
            # Bullet starts at the front-center of the player
            all_sprites_group = self.groups()[0] if self.groups() else None
            if all_sprites_group:
                # Create the bullet
                bullet = Bullet(self.rect.right, self.rect.centery, all_sprites_group, self.bullets)
                
                # Make bullet home in on enemies if that powerup is active
                if self.has_homing_missiles and self.game_ref:
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
        """Charge up the pulse beam while key is held."""
        if self.pulse_beam_charge < self.max_pulse_beam_charge:
            self.pulse_beam_charge += 2  # Charge rate
            
            # Create charging particles if we have a game reference
            if self.game_ref and hasattr(self.game_ref, 'particles'):
                particles_group = getattr(self.game_ref, 'particles', None)
                if particles_group:
                    # Only create particles every few frames
                    if self.pulse_beam_charge % 5 == 0:
                        charge_percent = self.pulse_beam_charge / self.max_pulse_beam_charge
                        
                        # Calculate color based on charge (blue to white)
                        r = min(255, int(100 + 155 * charge_percent))
                        g = min(255, int(200 + 55 * charge_percent))
                        b = 255
                        
                        from src.powerup import PowerupParticle
                        # Create particles around the front of the ship
                        for _ in range(2):
                            pos_x = self.rect.right + random.randint(-5, 5)
                            pos_y = self.rect.centery + random.randint(-10, 10)
                            
                            # Random velocity
                            vel_x = random.uniform(-0.5, 1.5)
                            vel_y = random.uniform(-1.0, 1.0)
                            
                            # Random size based on charge
                            size = random.randint(2, int(2 + 5 * charge_percent))
                            
                            try:
                                # Create particle
                                PowerupParticle(
                                    (pos_x, pos_y), (vel_x, vel_y),
                                    (r, g, b), size, 
                                    random.randint(10, 20),
                                    0.01, 0.9,
                                    particles_group
                                )
                            except Exception as e:
                                logger.warning(f"Failed to create pulse beam charging particle: {e}")
                                break
    
    def _fire_pulse_beam(self) -> None:
        """Fire the charged pulse beam."""
        if not self.has_pulse_beam or self.pulse_beam_charge < 10:
            return
            
        # Calculate charge percentage
        charge_percent = min(1.0, self.pulse_beam_charge / self.max_pulse_beam_charge)
        
        # Get sprite groups
        all_sprites_group = self.groups()[0] if self.groups() else None
        if all_sprites_group and self.game_ref:
            try:
                # Create the pulse beam and explicitly add to bullets group
                beam = PulseBeam(self.rect.center, charge_percent, all_sprites_group)
                # Ensure it's in the bullets group for collision detection
                self.bullets.add(beam)
                
                # Play sound
                if hasattr(self.game_ref, 'sound_manager'):
                    try:
                        self.game_ref.sound_manager.play("laser", "player")
                    except Exception as e:
                        logger.warning(f"Failed to play laser sound: {e}")
                
                logger.info(f"Fired pulse beam with charge {charge_percent:.2f}")
            except Exception as e:
                logger.error(f"Error creating pulse beam: {e}")
            
        # Reset charge
        self.pulse_beam_charge = 0
    
    def _fire_scatter_bomb(self) -> None:
        """Fire a scatter bomb that creates projectiles in all directions."""
        if not self.has_scatter_bomb or self.scatter_bomb_charges <= 0:
            return
            
        # Reduce available charges
        self.scatter_bomb_charges -= 1
        
        # If no charges left, remove from active powerups
        if self.scatter_bomb_charges <= 0:
            self.has_scatter_bomb = False
            if ("SCATTER_BOMB", 6) in self.active_powerups:
                self.active_powerups.remove(("SCATTER_BOMB", 6))
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
            
            logger.info(f"Fired scatter bomb. {self.scatter_bomb_charges} charges remaining")
            
    def take_damage(self) -> bool:
        """Reduces player's power level when hit.
        
        Returns:
            bool: True if player is still alive, False if game over
        """
        try:
            # Skip damage if player is invincible
            if self.is_invincible:
                logger.info("Hit ignored - player is invincible")
                return True
                
            # Skip damage if player has active shield
            if self.has_shield:
                logger.info("Hit ignored - player has active shield")
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
            
            # Draw shield if active
            if self.has_shield:
                self.shield_pulse = (self.shield_pulse + 0.1) % (2 * math.pi)
                pulse_value = 0.7 + 0.3 * math.sin(self.shield_pulse)
                
                # Calculate shield color with pulse
                alpha = int(128 * pulse_value)
                shield_color = (
                    self.shield_color[0],
                    self.shield_color[1],
                    self.shield_color[2],
                    alpha
                )
                
                # Create shield surface
                shield_size = int(self.shield_radius * 2 * pulse_value)
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
            
        # Draw pulse beam charge meter if charging
        if self.has_pulse_beam and self.is_charging and self.pulse_beam_charge > 0:
            charge_percent = self.pulse_beam_charge / self.max_pulse_beam_charge
            
            # Meter dimensions
            meter_width = 40
            meter_height = 8
            meter_x = self.rect.right + 5
            meter_y = self.rect.centery - meter_height // 2
            
            # Calculate color based on charge
            r = min(255, int(100 + 155 * charge_percent))
            g = min(255, int(100 + 155 * charge_percent))
            b = 255
            
            # Background
            pygame.draw.rect(
                surface,
                (50, 50, 50),
                (meter_x, meter_y, meter_width, meter_height)
            )
            
            # Filled portion
            filled_width = int(meter_width * charge_percent)
            pygame.draw.rect(
                surface,
                (r, g, b),
                (meter_x, meter_y, filled_width, meter_height)
            )

        # Draw shield meter if shield is active
        if self.has_shield:
            # Calculate shield percentage remaining
            shield_percent = self.shield_value / self.shield_max_value
            
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
        """Draw icons for active powerups."""
        if not self.active_powerups:
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
        
        # Powerup full names for display
        display_names = {
            "TRIPLE_SHOT": "TRIPLE SHOT",
            "RAPID_FIRE": "RAPID FIRE",
            "SHIELD": "SHIELD",
            "HOMING_MISSILES": "HOMING MISSILES",
            "PULSE_BEAM": "PULSE BEAM",
            "POWER_RESTORE": "POWER RESTORE",
            "SCATTER_BOMB": "SCATTER BOMB",
            "TIME_WARP": "TIME WARP",
            "MEGA_BLAST": "MEGA BLAST"
        }
        
        # Colors as fallback (same as before)
        colors = [
            (255, 220, 0),    # TRIPLE_SHOT: Golden
            (0, 255, 255),    # RAPID_FIRE: Cyan
            (0, 100, 255),    # SHIELD: Blue
            (255, 0, 255),    # HOMING_MISSILES: Magenta
            (255, 255, 255),  # PULSE_BEAM: White
            (0, 255, 0),      # POWER_RESTORE: Green (not shown)
            (255, 128, 0),    # SCATTER_BOMB: Orange
            (128, 0, 255),    # TIME_WARP: Purple
            (255, 0, 128),    # MEGA_BLAST: Pink (not shown)
        ]
        
        # Set a smaller icon size
        icon_size = 20
        spacing = 22
        
        # Draw each active powerup
        for i, (powerup_name, powerup_idx) in enumerate(self.active_powerups):
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
                color = colors[powerup_idx]
                
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
            
            # Determine time remaining for timed powerups
            time_remaining = None
            if powerup_name == "TRIPLE_SHOT" and self.has_triple_shot:
                time_remaining = max(0, (self.triple_shot_expiry - current_time) // 1000)
            elif powerup_name == "RAPID_FIRE" and self.has_rapid_fire:
                time_remaining = max(0, (self.rapid_fire_expiry - current_time) // 1000)
            elif powerup_name == "SHIELD" and self.has_shield:
                time_remaining = max(0, (self.shield_expiry - current_time) // 1000)
            elif powerup_name == "HOMING_MISSILES" and self.has_homing_missiles:
                time_remaining = max(0, (self.homing_missiles_expiry - current_time) // 1000)
            elif powerup_name == "PULSE_BEAM" and self.has_pulse_beam:
                time_remaining = max(0, (self.pulse_beam_expiry - current_time) // 1000)
            elif powerup_name == "TIME_WARP" and self.has_time_warp:
                time_remaining = max(0, (self.time_warp_expiry - current_time) // 1000)
            
            # For SCATTER_BOMB, show charges instead of time
            if powerup_name == "SCATTER_BOMB":
                time_text = time_font.render(f"{self.scatter_bomb_charges}", True, (255, 220, 150))
            elif time_remaining is not None:
                time_text = time_font.render(f"{time_remaining}s", True, (200, 200, 200))
            else:
                time_text = time_font.render("Active", True, (200, 200, 200))
            
            # Position time info below the name (on same line)
            time_x = name_x + name_text.get_width() + 5
            time_y = name_y
            surface.blit(time_text, (time_x, time_y))

    def _shoot_triple(self) -> None:
        """Shoots three bullets in a spread pattern (triple shot powerup)."""
        now = pygame.time.get_ticks()
        # Use rapid fire delay if active
        shoot_delay = self.rapid_fire_delay if self.has_rapid_fire else self.normal_shoot_delay
        
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
                
                # Apply homing to all bullets if that powerup is also active
                if self.has_homing_missiles and self.game_ref:
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
        """Checks and handles powerup expirations."""
        current_time = pygame.time.get_ticks()
        
        # Handle rapid fire expiry
        if self.has_rapid_fire and current_time > self.rapid_fire_expiry:
            self.has_rapid_fire = False
            logger.info("Rapid Fire powerup expired")
            # Remove from active powerups
            self.active_powerups = [p for p in self.active_powerups if p[0] != "RAPID_FIRE"]
        
        # Handle triple shot expiry
        if self.has_triple_shot and current_time > self.triple_shot_expiry:
            self.has_triple_shot = False
            logger.info("Triple Shot powerup expired")
            # Remove from active powerups
            self.active_powerups = [p for p in self.active_powerups if p[0] != "TRIPLE_SHOT"]
        
        # Handle shield expiry
        if self.has_shield and current_time > self.shield_expiry:
            self.has_shield = False
            logger.info("Shield powerup expired")
            # Remove from active powerups
            self.active_powerups = [p for p in self.active_powerups if p[0] != "SHIELD"]
        
        # Handle homing missiles expiry
        if self.has_homing_missiles and current_time > self.homing_missiles_expiry:
            self.has_homing_missiles = False
            logger.info("Homing Missiles powerup expired")
            # Remove from active powerups
            self.active_powerups = [p for p in self.active_powerups if p[0] != "HOMING_MISSILES"]
        
        # Handle time warp expiry
        if self.has_time_warp and current_time > self.time_warp_expiry:
            self.has_time_warp = False
            logger.info("Time Warp powerup expired")
            # Remove from active powerups
            self.active_powerups = [p for p in self.active_powerups if p[0] != "TIME_WARP"]
        
        # Handle pulse beam expiry
        if self.has_pulse_beam and current_time > self.pulse_beam_expiry:
            self.has_pulse_beam = False
            logger.info("Pulse Beam powerup expired")
            # Remove from active powerups
            self.active_powerups = [p for p in self.active_powerups if p[0] != "PULSE_BEAM"]
                
        # Check if charging pulse beam
        if self.is_charging and self.has_pulse_beam:
            self._charge_pulse_beam()

    def add_powerup(self, powerup_name: str, powerup_idx: int) -> None:
        """Add a powerup to the active powerups list, preventing duplicates."""
        # Check if this powerup is already active
        for existing in self.active_powerups:
            if existing[0] == powerup_name:
                # Update the existing powerup's expiry time instead of adding a duplicate
                if powerup_name == "TRIPLE_SHOT":
                    self.triple_shot_expiry = pygame.time.get_ticks() + POWERUP_DURATION
                elif powerup_name == "RAPID_FIRE":
                    self.rapid_fire_expiry = pygame.time.get_ticks() + POWERUP_DURATION
                elif powerup_name == "SHIELD":
                    self.shield_expiry = pygame.time.get_ticks() + POWERUP_DURATION
                elif powerup_name == "HOMING_MISSILES":
                    self.homing_missiles_expiry = pygame.time.get_ticks() + POWERUP_DURATION
                elif powerup_name == "PULSE_BEAM":
                    self.pulse_beam_expiry = pygame.time.get_ticks() + POWERUP_DURATION
                elif powerup_name == "TIME_WARP":
                    self.time_warp_expiry = pygame.time.get_ticks() + POWERUP_DURATION
                elif powerup_name == "SCATTER_BOMB":
                    # For scatter bomb, add more charges instead of extending time
                    self.scatter_bomb_charges += 3
                # Powerup already exists, don't add it again
                return
                
        # If we get here, the powerup isn't active yet, so add it
        self.active_powerups.append((powerup_name, powerup_idx))
