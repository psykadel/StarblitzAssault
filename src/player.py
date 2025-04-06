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
        self.powerup_icon_base_y = 45  # Position below power bar

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
            
        # Call parent update for animation and movement
        super().update()
        
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
            # Use triple shot if active
            if self.has_triple_shot:
                self._shoot_triple()
            else:
                self.shoot() # shoot() already handles the cooldown

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
                elif event.key == pygame.K_SPACE and self.has_scatter_bomb and self.scatter_bomb_charges > 0:
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
            # Create the pulse beam
            beam = PulseBeam(self.rect.center, charge_percent, 
                           all_sprites_group, self.bullets)
            
            # Play sound
            if hasattr(self.game_ref, 'sound_manager'):
                try:
                    self.game_ref.sound_manager.play("laser", "player")
                except Exception as e:
                    logger.warning(f"Failed to play laser sound: {e}")
            
            logger.info(f"Fired pulse beam with charge {charge_percent:.2f}")
            
        # Reset charge
        self.pulse_beam_charge = 0
    
    def _fire_scatter_bomb(self) -> None:
        """Fire a scatter bomb that creates projectiles in all directions."""
        if not self.has_scatter_bomb or self.scatter_bomb_charges <= 0:
            return
            
        # Reduce available charges
        self.scatter_bomb_charges -= 1
        
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
    
    def draw_powerup_icons(self, surface: pygame.Surface) -> None:
        """Draw icons for active powerups."""
        if not self.active_powerups:
            return
            
        # Colors for each powerup type
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
        
        # Icons for each type
        for i, (powerup_name, powerup_idx) in enumerate(self.active_powerups):
            # Position
            icon_x = self.power_bar_position[0] + i * (self.powerup_icon_size + self.powerup_icon_spacing)
            icon_y = self.powerup_icon_base_y
            
            # Create icon
            color = colors[powerup_idx]
            
            # Draw icon background
            pygame.draw.rect(
                surface,
                (50, 50, 50),
                (icon_x, icon_y, self.powerup_icon_size, self.powerup_icon_size)
            )
            
            # Draw icon inner
            pygame.draw.rect(
                surface,
                color,
                (icon_x + 2, icon_y + 2, self.powerup_icon_size - 4, self.powerup_icon_size - 4)
            )
            
            # Draw count for scatter bomb
            if powerup_name == "SCATTER_BOMB":
                font = pygame.font.SysFont(None, 14)
                count_text = font.render(str(self.scatter_bomb_charges), True, (0, 0, 0))
                text_rect = count_text.get_rect(center=(
                    icon_x + self.powerup_icon_size // 2, 
                    icon_y + self.powerup_icon_size // 2
                ))
                surface.blit(count_text, text_rect)

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
            else:
                # Make player blink by toggling visibility every few frames
                self.blink_counter += 1
                if self.blink_counter >= 4:  # Toggle every 4 frames
                    self.visible = not self.visible
                    self.blink_counter = 0

    def _check_powerup_expirations(self) -> None:
        """Checks and handles powerup expirations."""
        current_time = pygame.time.get_ticks()
        
        # Handle rapid fire expiry
        if self.has_rapid_fire and current_time > self.rapid_fire_expiry:
            self.has_rapid_fire = False
            logger.info("Rapid Fire powerup expired")
            # Remove from active powerups
            if "RAPID_FIRE" in self.active_powerups:
                self.active_powerups.remove("RAPID_FIRE")
        
        # Handle triple shot expiry
        if self.has_triple_shot and current_time > self.triple_shot_expiry:
            self.has_triple_shot = False
            logger.info("Triple Shot powerup expired")
            # Remove from active powerups
            if "TRIPLE_SHOT" in self.active_powerups:
                self.active_powerups.remove("TRIPLE_SHOT")
        
        # Handle shield expiry
        if self.has_shield and current_time > self.shield_expiry:
            self.has_shield = False
            logger.info("Shield powerup expired")
            # Remove from active powerups
            if "SHIELD" in self.active_powerups:
                self.active_powerups.remove("SHIELD")
        
        # Handle homing missiles expiry
        if self.has_homing_missiles and current_time > self.homing_missiles_expiry:
            self.has_homing_missiles = False
            logger.info("Homing Missiles powerup expired")
            # Remove from active powerups
            if "HOMING_MISSILES" in self.active_powerups:
                self.active_powerups.remove("HOMING_MISSILES")
        
        # Handle time warp expiry
        if self.has_time_warp and current_time > self.time_warp_expiry:
            self.has_time_warp = False
            logger.info("Time Warp powerup expired")
            # Remove from active powerups
            if "TIME_WARP" in self.active_powerups:
                self.active_powerups.remove("TIME_WARP")
        
        # Handle pulse beam expiry
        if self.has_pulse_beam and current_time > self.pulse_beam_expiry:
            self.has_pulse_beam = False
            logger.info("Pulse Beam powerup expired")
            # Remove from active powerups
            if "PULSE_BEAM" in self.active_powerups:
                self.active_powerups.remove("PULSE_BEAM")
                
        # Check if charging pulse beam
        if self.is_charging and self.has_pulse_beam:
            self._charge_pulse_beam()
