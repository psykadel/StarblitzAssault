"""Defines the player character (Starblitz fighter)."""

import math
import os
import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import pygame

# Import config variables
from config.config import (
    BULLET_SPEED,
    GREEN,
    PLAYER_ANIMATION_SPEED_MS,
    PLAYER_SCALE_FACTOR,
    PLAYER_SHOOT_DELAY,
    PLAYER_SPEED,
    PLAYFIELD_BOTTOM_Y,
    PLAYFIELD_TOP_Y,
    POWERUP_DISPLAY_START_Y,
    POWERUP_ICON_SIZE,
    POWERUP_ICON_SPACING,
    POWERUP_SLOTS,
    RED,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SPRITES_DIR,
    WHITE,
    YELLOW,
    FLAME_PARTICLE_DAMAGE,
    FLAME_PARTICLE_LIFETIME,
    FLAME_SPAWN_DELAY,
    FLAME_SPRAY_ANGLE,
)

# Import base animated sprite
from src.animated_sprite import AnimatedSprite

# Import logger
from src.logger import get_logger

# Import the new constants
# Import powerup constants
from src.powerup import POWERUP_DURATION, PowerupType
from src.powerup_types import ACTIVE_DRONES

# Import the Bullet class
from src.projectile import Bullet, LaserBeam, ScatterProjectile

# Import the sprite loading utility
from src.sprite_loader import load_sprite_sheet

# Import the necessary modules for flamethrower
from src.particle import FlameParticle

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
            (255, 0, 0),  # Red (critical)
            (255, 128, 0),  # Orange (low)
            (255, 255, 0),  # Yellow (medium)
            (128, 255, 0),  # Yellow-Green (good)
            (0, 255, 0),  # Green (full)
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

        # Key state tracking
        self.key_states = {
            "up": False,
            "down": False,
            "left": False,
            "right": False,
            "key_fire": False,
            "key_beam": False,
            "key_bomb": False,
        }
        self.prev_key_states = {}

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

        # Flamethrower sound control
        self.flamethrower_sound_active = False
        self.flamethrower_sound_start_time = 0
        self.flamethrower_sound_duration = 5000  # 5 seconds loop duration
        self.flamethrower_sound_fadeout_start = 4000  # Start fadeout at 4 seconds (1 second before end)
        self.flamethrower_next_sound_instance = None  # For smooth transition

        # Laser beam sound control - Using crossfade logic now
        self.laserbeam_sound_active = False
        self.laserbeam_sound_start_time = 0
        self.laserbeam_sound_duration = 0 # Will be fetched from SoundManager
        self.laserbeam_sound_fadeout_start = 0 # Calculated from duration
        self.laserbeam_next_sound_instance = None

    def load_sprites(self) -> None:
        """Loads animation frames using the utility function."""
        # Player sprite likely benefits from right-alignment for consistency
        self.frames = load_sprite_sheet(
            filename="main-character.png",
            sprite_dir=SPRITES_DIR,
            scale_factor=PLAYER_SCALE_FACTOR,
            # crop_border=5 # No longer used
            alignment="right",  # Explicitly state right alignment
            align_margin=5,  # Keep a small margin from the right edge
        )
        # Error handling is done within load_sprite_sheet, which raises SystemExit

    def update(self) -> None:
        """Update the player's position and state."""
        # Call the parent class update
        super().update()

        # FIRST, check for flamethrower activation - must happen early in the update cycle
        flamethrower_active = PowerupType.FLAMETHROWER.name in self.active_powerups_state
        if flamethrower_active:
            self._shoot_flamethrower()  # Create flame particles
            self._manage_flamethrower_sound(True)  # Play sound
        else:
            self._manage_flamethrower_sound(False)

        # Timing variables
        current_time = pygame.time.get_ticks()

        # Skip update if player is dead
        if not self.is_alive:
            # Ensure sound stops if player dies
            self._manage_laserbeam_sound(False)
            return

        # Update hit animation if active
        if self.is_hit_animating:
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
                    if (
                        self.is_invincible
                        and hasattr(self.image, "get_alpha")
                        and self.image.get_alpha() is not None
                    ):
                        self.image.set_alpha(self.image.get_alpha())
            else:
                # End animation
                self.is_hit_animating = False
                self.image = self.frames[self.frame_index]
                self.mask = pygame.mask.from_surface(self.image)

                # Maintain invincibility fade effect after animation ends
                if self.is_invincible and hasattr(self.image, "set_alpha"):
                    # Get the current alpha from our fade calculation
                    elapsed = current_time - self.invincibility_timer
                    cycle_position = (elapsed % 1500) / 1500.0
                    fade_factor = 0.5 + 0.5 * math.sin(cycle_position * 2 * math.pi)
                    alpha = int(40 + 180 * fade_factor)
                    self.image.set_alpha(alpha)

        # Check if power level has changed
        if self.power_level != self.previous_power_level:
            # Record the time of power change for particle effects
            self.power_change_time = current_time
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

        # --- Manage Laser Beam Sound --- 
        # Check if the player is firing AND has the laser beam powerup
        laser_beam_powerup_active = PowerupType.LASER_BEAM.name in self.active_powerups_state
        should_laser_sound_be_active = self.is_firing and laser_beam_powerup_active
        self._manage_laserbeam_sound(should_laser_sound_be_active)
        # --- End Laser Beam Sound --- 

        # Check for continuous shooting (handle weapon firing AFTER sound check)
        if self.is_firing:
            # Use triple shot if active, otherwise normal shot
            if PowerupType.TRIPLE_SHOT.name in self.active_powerups_state:
                self._shoot_triple()
            elif laser_beam_powerup_active: # Use the variable we just checked
                self._fire_laser_beam()
            else:
                self.shoot()  # shoot() already handles the cooldown based on powerup state

        # Update shield meter if shield is active (derived from state)
        # shield_value is calculated in draw method
        # if "SHIELD" in self.active_powerups_state:
        #     current_time = pygame.time.get_ticks()
        #     expiry = self.active_powerups_state["SHIELD"].get("expiry_time", 0)
        #     time_remaining = max(0, expiry - current_time)
        #     self.shield_value = time_remaining
        # else:
        #     self.shield_value = 0

        # Handle continuous firing if key is held down
        if self.key_states["key_fire"]:
            self.shoot()

    def start_firing(self) -> None:
        """Begins continuous firing."""
        self.is_firing = True
        # REMOVED: Start laser beam loop if powerup is active
        # if PowerupType.LASER_BEAM.name in self.active_powerups_state:
        #     self._manage_laserbeam_sound(True)

    def stop_firing(self) -> None:
        """Stops continuous firing."""
        self.is_firing = False
        # REMOVED: Stop laser beam loop regardless of powerup status (only active when firing)
        # self._manage_laserbeam_sound(False)

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
                    self.speed_x = -PLAYER_SPEED / 2  # Slower horizontal?
                elif event.key == pygame.K_RIGHT:
                    self.speed_x = PLAYER_SPEED / 2

                # Special powerup controls
                # Check state dict for scatter bomb availability and charges
                scatter_state = self.active_powerups_state.get("SCATTER_BOMB")
                if (
                    event.key == pygame.K_b
                    and scatter_state
                    and scatter_state.get("charges", 0) > 0
                ):
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
        """Fire a bullet if the shoot delay has elapsed."""
        try:
            # Check if shoot delay has elapsed
            current_time = pygame.time.get_ticks()
            
            # Get rapid fire state if exists
            rapid_fire_state = self.active_powerups_state.get(PowerupType.RAPID_FIRE.name, {})
            
            # Use rapid fire delay if available, otherwise use standard delay
            shoot_delay = rapid_fire_state.get("delay", PLAYER_SHOOT_DELAY)
            
            if current_time - self.last_shot_time > shoot_delay:
                self.last_shot_time = current_time
                
                # If we have triple shot active, fire triple bullets
                if PowerupType.TRIPLE_SHOT.name in self.active_powerups_state:
                    self._shoot_triple()
                else:
                    # Default single bullet
                    self._shoot_single_bullet()
                
                # Always try to fire flamethrower if active (has its own cooldown)
                self._shoot_flamethrower()
                
                # Play sound effect
                if self.game_ref and hasattr(self.game_ref, "sound_manager"):
                    try:
                        self.game_ref.sound_manager.play("laser", "player")
                    except Exception as e:
                        logger.warning(f"Failed to play laser sound: {e}")
                
                # Reset the shoot flag since we've handled the shot
                self.key_states["key_fire"] = False
                
        except Exception as e:
            logger.error(f"Error in shoot method: {e}")

    def _handle_special_attacks(self) -> None:
        """Handle special attacks like homing missiles or laser beam."""
        # Check if we have the scatter bomb powerup active
        if PowerupType.SCATTER_BOMB.name in self.active_powerups_state:
            # See if we can shoot a scatter bomb (check current charge and charge time)
            scatter_state = self.active_powerups_state[PowerupType.SCATTER_BOMB.name]

            # If we don't have charge info, set it up
            if "charges" not in scatter_state:
                scatter_state["charges"] = 3  # Maximum 3 scatter bomb charges
                scatter_state["last_charge_time"] = self.timing_func()
                scatter_state["charge_interval"] = 3000  # 3 seconds to recharge one bomb

            # If we have charges and the scatter key is pressed for the first time
            if (
                scatter_state["charges"] > 0
                and self.key_states["key_bomb"]
                and not self.prev_key_states.get("key_bomb", False)
            ):
                self._fire_scatter_bomb(scatter_state)

            # Recharge scatter bombs over time
            current_time = self.timing_func()
            if scatter_state["charges"] < 3:  # Don't recharge if we're at max
                time_since_last_charge = current_time - scatter_state["last_charge_time"]
                if time_since_last_charge >= scatter_state["charge_interval"]:
                    # Recharge one bomb
                    scatter_state["charges"] += 1
                    scatter_state["last_charge_time"] = current_time
                    logger.debug(
                        f"Recharged scatter bomb. Now have {scatter_state['charges']} bombs."
                    )
        
        # Check if we have the laser beam powerup active
        elif PowerupType.LASER_BEAM.name in self.active_powerups_state:
            # See if we can fire a laser beam (check current charge and charge time)
            laser_state = self.active_powerups_state[PowerupType.LASER_BEAM.name]

            # If we don't have charge info, set it up
            if "charges" not in laser_state:
                laser_state["charges"] = 5  # Maximum 5 laser beam charges
                laser_state["last_charge_time"] = self.timing_func()
                laser_state["charge_interval"] = 2000  # 2 seconds to recharge one beam

            # If we have charges and the bomb key is pressed for the first time
            if (
                laser_state["charges"] > 0
                and self.key_states["key_bomb"]
                and not self.prev_key_states.get("key_bomb", False)
            ):
                self._fire_laser_beam(laser_state)

            # Recharge laser beams over time
            current_time = self.timing_func()
            if laser_state["charges"] < 5:  # Don't recharge if we're at max
                time_since_last_charge = current_time - laser_state["last_charge_time"]
                if time_since_last_charge >= laser_state["charge_interval"]:
                    # Recharge one beam
                    laser_state["charges"] += 1
                    laser_state["last_charge_time"] = current_time
                    logger.debug(
                        f"Recharged laser beam. Now have {laser_state['charges']} beams."
                    )

    def timing_func(self) -> int:
        """Return the current time in milliseconds. Used for timing-based effects."""
        return pygame.time.get_ticks()

    def _fire_scatter_bomb(self, scatter_state=None) -> None:
        """Fire a scatter bomb that creates projectiles in all directions.

        Args:
            scatter_state: Optional scatter bomb state dictionary. If None, will attempt
                          to retrieve from active_powerups_state.
        """
        # If no state provided, try to get it from active powerups
        if scatter_state is None:
            scatter_state = self.active_powerups_state.get(PowerupType.SCATTER_BOMB.name)

        if not scatter_state or scatter_state.get("charges", 0) <= 0:
            return  # Not active or no charges

        # Reduce available charges in state
        scatter_state["charges"] -= 1
        charges_remaining = scatter_state["charges"]

        # Get sprite groups
        all_sprites_group = self.groups()[0] if self.groups() else None
        if all_sprites_group:
            # Create scatter projectiles in all directions
            num_projectiles = 16  # Spread in 16 directions
            for i in range(num_projectiles):
                angle = (i / num_projectiles) * 2 * math.pi

                # Create scatter projectile
                ScatterProjectile(
                    self.rect.centerx,
                    self.rect.centery,
                    angle,
                    BULLET_SPEED * 0.75,
                    all_sprites_group,
                    self.bullets,
                )

            # Play sound
            if self.game_ref and hasattr(self.game_ref, "sound_manager"):
                try:
                    self.game_ref.sound_manager.play("explosion1", "player")
                except Exception as e:
                    logger.warning(f"Failed to play explosion sound: {e}")

            logger.info(f"Fired scatter bomb. {charges_remaining} charges remaining")

    def _fire_laser_beam(self, laser_state=None) -> None:
        """Fire a growing green laser beam.

        Args:
            laser_state: Optional laser beam state dictionary. If None, will attempt
                       to retrieve from active_powerups_state.
        """
        # Get sprite groups
        all_sprites_group = self.groups()[0] if self.groups() else None
        if all_sprites_group:
            # Create a laser beam from the player's position
            # Use a constant charge level for consistent visuals
            charge_level = 0.8
            
            LaserBeam(
                self.rect.center,
                charge_level,
                all_sprites_group,
                self.bullets,
                sound_manager=self.game_ref.sound_manager if self.game_ref else None
            )

            # Play initial sound effect (one-shot) in addition to the looping sound
            if self.game_ref and hasattr(self.game_ref, "sound_manager"):
                try:
                    self.game_ref.sound_manager.play("laser", "player")
                except Exception as e:
                    logger.warning(f"Failed to play laser sound: {e}")

            logger.debug("Fired laser beam")

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
        return (
            current_time - self.power_change_time < 1000
            and (current_time - self.power_change_time) % self.particle_cooldown < 50
        )

    def get_power_bar_particles_position(self) -> tuple:
        """Get the position for power bar particles."""
        # Calculate the current width of the filled power bar
        filled_width = (
            (self.power_bar_width - self.power_bar_border * 2) * self.power_level / MAX_POWER_LEVEL
        )

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
                if not hasattr(self, "shield_pulse"):
                    self.shield_pulse = 0
                    self.shield_particles = []
                    self.last_shield_particle_time = 0

                # Update shield pulse value
                self.shield_pulse = (self.shield_pulse + 0.1) % (2 * math.pi)
                pulse_value = 0.7 + 0.3 * math.sin(self.shield_pulse)

                # Calculate shield color with pulse
                shield_base_color = shield_state.get("color", (0, 100, 255))  # Default blue

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
                    0,  # Filled
                )

                # Middle layer
                pygame.draw.circle(
                    shield_surface,
                    (*shield_base_color, 80),  # Semi-transparent
                    center,
                    int(shield_size * 0.85),
                    0,  # Filled
                )

                # Inner layer
                pygame.draw.circle(
                    shield_surface,
                    (*shield_base_color, 40),  # Semi-transparent
                    center,
                    int(shield_size * 0.7),
                    0,  # Filled
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
                            max(1, int(3 * pulse_value)),  # Thickness
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
                            max(1, int(2 * pulse_value)),  # Thickness
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
                        max(1, int(1 * pulse_value)),  # Thickness
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
                            current_size,
                        )

                # Position shield around player
                shield_rect = shield_surface.get_rect(center=self.rect.center)
                surface.blit(shield_surface, shield_rect)

                # Create shield particles occasionally
                current_time = pygame.time.get_ticks()
                if (
                    current_time - getattr(self, "last_shield_particle_time", 0) > 100
                ):  # Every 100ms
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
                            "pos": [particle_x, particle_y],
                            "vel": [
                                math.cos(rad_angle) * random.uniform(0.5, 1.5),
                                math.sin(rad_angle) * random.uniform(0.5, 1.5),
                            ],
                            "size": random.randint(2, 5),
                            "life": random.randint(10, 30),
                            "age": 0,
                            "color": shield_base_color,
                        }

                        # Store in shield particles list
                        if not hasattr(self, "shield_particles"):
                            self.shield_particles = []
                        self.shield_particles.append(particle)

                # Update and draw existing shield particles
                if hasattr(self, "shield_particles"):
                    new_particles = []
                    for p in self.shield_particles:
                        # Update position
                        p["pos"][0] += p["vel"][0]
                        p["pos"][1] += p["vel"][1]

                        # Update age
                        p["age"] += 1

                        # Skip if too old
                        if p["age"] >= p["life"]:
                            continue

                        # Calculate fade
                        fade = 1 - (p["age"] / p["life"])
                        particle_alpha = int(200 * fade)
                        particle_size = max(1, int(p["size"] * fade))

                        # Draw particle
                        pygame.draw.circle(
                            surface,
                            (*p["color"], particle_alpha),
                            (int(p["pos"][0]), int(p["pos"][1])),
                            particle_size,
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

        # Debug the state dictionary
        logger.debug(f"Active powerups state: {self.active_powerups_state.keys()}")

        # Set icon size from config
        icon_size = POWERUP_ICON_SIZE
        spacing = POWERUP_ICON_SPACING

        # Track time for animation effects
        animation_time = current_time / 1000  # Convert to seconds for easier math

        # Define the powerup colors - match the ones in powerup.py
        powerup_colors = {
            PowerupType.TRIPLE_SHOT.value: (255, 220, 0),  # Golden
            PowerupType.RAPID_FIRE.value: (0, 255, 255),  # Cyan
            PowerupType.SHIELD.value: (0, 100, 255),  # Blue
            PowerupType.HOMING_MISSILES.value: (255, 0, 255),  # Magenta
            PowerupType.POWER_RESTORE.value: (0, 255, 0),  # Green
            PowerupType.SCATTER_BOMB.value: (255, 128, 0),  # Orange
            PowerupType.TIME_WARP.value: (128, 0, 255),  # Purple
            PowerupType.MEGA_BLAST.value: (255, 0, 128),  # Pink
            PowerupType.LASER_BEAM.value: (20, 255, 100),  # Bright Green for Laser
            PowerupType.DRONE.value: (180, 180, 180),  # Light Gray for Drone
            PowerupType.FLAMETHROWER.value: (255, 60, 0),  # Fiery Orange-Red for Flamethrower
        }

        # Powerup full names for display
        display_names = {
            PowerupType.TRIPLE_SHOT.name: "TRIPLE SHOT",
            PowerupType.RAPID_FIRE.name: "RAPID FIRE",
            PowerupType.SHIELD.name: "SHIELD",
            PowerupType.HOMING_MISSILES.name: "HOMING MISSILES",
            PowerupType.POWER_RESTORE.name: "POWER RESTORE",
            PowerupType.SCATTER_BOMB.name: "SCATTER BOMB",
            PowerupType.TIME_WARP.name: "TIME WARP",
            PowerupType.MEGA_BLAST.name: "MEGA BLAST",
            PowerupType.LASER_BEAM.name: "LASER BEAM",
            PowerupType.DRONE.name: "DRONE",
            PowerupType.FLAMETHROWER.name: "FLAMETHROWER",
        }

        # Map enum values directly to Y positions - this is the key fix
        # This guarantees consistent positions regardless of anything else
        absolute_positions = {
            PowerupType.TRIPLE_SHOT.value: start_y + (POWERUP_SLOTS["TRIPLE_SHOT"] * spacing),
            PowerupType.RAPID_FIRE.value: start_y + (POWERUP_SLOTS["RAPID_FIRE"] * spacing),
            PowerupType.SHIELD.value: start_y + (POWERUP_SLOTS["SHIELD"] * spacing),
            PowerupType.HOMING_MISSILES.value: start_y
            + (POWERUP_SLOTS["HOMING_MISSILES"] * spacing),
            PowerupType.SCATTER_BOMB.value: start_y + (POWERUP_SLOTS["SCATTER_BOMB"] * spacing),
            PowerupType.TIME_WARP.value: start_y + (POWERUP_SLOTS["TIME_WARP"] * spacing),
            PowerupType.LASER_BEAM.value: start_y + (POWERUP_SLOTS["LASER_BEAM"] * spacing),
            PowerupType.DRONE.value: start_y + (POWERUP_SLOTS["DRONE"] * spacing),
            PowerupType.FLAMETHROWER.value: start_y + (POWERUP_SLOTS["FLAMETHROWER"] * spacing),
        }

        # Fonts for names and time
        name_font = pygame.font.SysFont(None, 18)
        time_font = pygame.font.SysFont(None, 16)

        # Track which powerup indices were actually drawn
        drawn_indices = set()

        # Draw each active powerup in its dedicated position
        for name, state in self.active_powerups_state.items():
            powerup_idx = state.get("index", 999)

            # Skip if we've already drawn this powerup index
            if powerup_idx in drawn_indices:
                logger.warning(f"Skipping duplicate powerup index {powerup_idx} for {name}")
                continue

            # Get the absolute position directly from the index, regardless of name
            icon_y = absolute_positions.get(powerup_idx, start_y + (999 * spacing))

            drawn_indices.add(powerup_idx)
            logger.debug(f"Drawing powerup {name} (idx={powerup_idx}) at fixed position y={icon_y}")

            # Create a special effect surface for this powerup
            icon_surface = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)

            # Get color for this powerup
            color = powerup_colors.get(powerup_idx, (128, 128, 128))  # Default to gray if not found

            # Create animation values - use consistent seed for each powerup type
            pulse = 0.7 + 0.3 * math.sin(
                animation_time * 2 + powerup_idx
            )  # Unique phase for each powerup
            rotation = (
                animation_time * 15 + powerup_idx * 45
            ) % 360  # Different rotation for each powerup

            # Draw special effect icon based on powerup type
            if name == PowerupType.TRIPLE_SHOT.name:
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
                        icon_surface, color, center, (end_x, end_y), max(1, int(icon_size // 8))
                    )
                # Add central glow
                pygame.draw.circle(icon_surface, color, center, int(icon_size // 4))
                pygame.draw.circle(
                    icon_surface,
                    (255, 255, 255, 150),
                    (center[0] - 2, center[1] - 2),
                    int(icon_size // 8),
                )

            elif name == PowerupType.RAPID_FIRE.name:
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
                        pygame.draw.lines(
                            icon_surface, color, False, points, max(1, icon_size // 12)
                        )

                # Add central glow
                pygame.draw.circle(icon_surface, (*color, 180), center, int(icon_size // 4))

            elif name == PowerupType.SHIELD.name:
                # Shield bubble effect
                center = (icon_size // 2, icon_size // 2)
                shield_radius = int(icon_size // 2 * pulse)

                # Draw shield circle
                pygame.draw.circle(
                    icon_surface, (*color, 180), center, shield_radius, max(1, int(icon_size // 10))
                )

                # Add inner glow
                pygame.draw.circle(icon_surface, (*color, 100), center, max(1, shield_radius - 2))

                # Add highlight
                highlight_pos = (center[0] - shield_radius // 3, center[1] - shield_radius // 3)
                pygame.draw.circle(
                    icon_surface, (255, 255, 255, 150), highlight_pos, max(1, shield_radius // 4)
                )

            elif name == PowerupType.HOMING_MISSILES.name:
                # Target-like icon
                center = (icon_size // 2, icon_size // 2)

                # Draw concentric circles (target)
                circle_sizes = [icon_size // 2, icon_size // 3, icon_size // 5]
                for r in circle_sizes:
                    pygame.draw.circle(
                        icon_surface, (*color, 150), center, r, max(1, int(icon_size // 12))
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
                        max(1, int(icon_size // 12)),
                    )

            elif name == PowerupType.POWER_RESTORE.name:
                # Health/power cross
                center = (icon_size // 2, icon_size // 2)
                width = max(2, int(icon_size // 6))
                length = int(icon_size * 0.7 * pulse)

                # Vertical line
                pygame.draw.rect(
                    icon_surface,
                    (*color, 220),
                    (center[0] - width // 2, center[1] - length // 2, width, length),
                )
                # Horizontal line
                pygame.draw.rect(
                    icon_surface,
                    (*color, 220),
                    (center[0] - length // 2, center[1] - width // 2, length, width),
                )

                # Add glow
                pygame.draw.circle(icon_surface, (*color, 100), center, int(icon_size // 3))

            elif name == PowerupType.SCATTER_BOMB.name:
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
                        icon_surface, color, center, (end_x, end_y), max(1, int(icon_size // 8))
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
                        max(1, int(icon_size // 10)),
                    )

                # Add central glow
                pygame.draw.circle(icon_surface, (*color, 200), center, int(icon_size // 4))

            elif name == PowerupType.TIME_WARP.name:
                # Clock-like pattern
                center = (icon_size // 2, icon_size // 2)

                # Draw clock face
                pygame.draw.circle(
                    icon_surface,
                    (*color, 150),
                    center,
                    int(icon_size // 2 * 0.8 * pulse),
                    max(1, int(icon_size // 10)),
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
                    max(1, int(icon_size // 8)),
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
                    max(1, int(icon_size // 12)),
                )

                # Central dot
                pygame.draw.circle(icon_surface, color, center, max(1, int(icon_size // 10)))

            elif name == PowerupType.LASER_BEAM.name:
                # Laser beam effect
                center = (icon_size // 2, icon_size // 2)
                
                # Draw a horizontal beam from left to right
                beam_width = max(2, int(icon_size // 4))
                beam_length = int(icon_size * 0.9 * pulse)
                
                # Draw beam glow (wider, semi-transparent)
                pygame.draw.rect(
                    icon_surface,
                    (*color, 80),
                    (center[0] - beam_length//2, center[1] - beam_width, beam_length, beam_width * 2),
                )
                
                # Draw main beam (thinner, brighter)
                pygame.draw.rect(
                    icon_surface,
                    (*color, 220),
                    (center[0] - beam_length//2, center[1] - beam_width//2, beam_length, beam_width),
                )
                
                # Add source point glow
                source_x = center[0] - beam_length//2
                pygame.draw.circle(
                    icon_surface,
                    (*color, 150),
                    (source_x, center[1]),
                    max(3, int(icon_size // 6))
                )
                
                # Add energy particles along beam
                for i in range(3):
                    particle_x = source_x + (beam_length * (i+1) // 4)
                    particle_y = center[1] + random.randint(-1, 1)
                    particle_size = random.randint(1, 2)
                    pygame.draw.circle(
                        icon_surface,
                        (255, 255, 255, 200),
                        (particle_x, particle_y),
                        particle_size
                    )

            elif name == PowerupType.DRONE.name:
                # Drone icon
                center = (icon_size // 2, icon_size // 2)
                
                # Draw drone body (triangle)
                drone_body_points = [
                    (center[0] + int(icon_size * 0.3), center[1]),  # Nose
                    (center[0] - int(icon_size * 0.2), center[1] - int(icon_size * 0.2)),  # Top left
                    (center[0] - int(icon_size * 0.2), center[1] + int(icon_size * 0.2)),  # Bottom left
                ]
                pygame.draw.polygon(icon_surface, color, drone_body_points)
                
                # Draw engine glow
                engine_glow_points = [
                    (center[0] - int(icon_size * 0.2), center[1] - int(icon_size * 0.1)),  # Top
                    (center[0] - int(icon_size * 0.2), center[1] + int(icon_size * 0.1)),  # Bottom
                    (center[0] - int(icon_size * 0.4), center[1]),  # Tip
                ]
                pygame.draw.polygon(icon_surface, (50, 150, 255, 200), engine_glow_points)
                
                # Draw weapon indicator
                pygame.draw.circle(
                    icon_surface,
                    (255, 50, 50),  # Red
                    (center[0] + int(icon_size * 0.2), center[1]),
                    max(1, int(icon_size * 0.06))
                )
                
                # Add orbit path
                orbit_radius = int(icon_size * 0.35 * pulse)
                pygame.draw.circle(
                    icon_surface,
                    (*color, 80),  # Semi-transparent
                    center,
                    orbit_radius,
                    max(1, int(icon_size * 0.02))
                )

            elif name == PowerupType.FLAMETHROWER.name:
                # Flamethrower effect
                center = (icon_size // 2, icon_size // 2)
                
                # Draw a flame-like pattern
                flame_width = max(2, int(icon_size // 4))
                flame_length = int(icon_size * 0.9 * pulse)
                
                # Draw flame glow (wider, semi-transparent)
                pygame.draw.rect(
                    icon_surface,
                    (*color, 80),
                    (center[0] - flame_length//2, center[1] - flame_width, flame_length, flame_width * 2),
                )
                
                # Draw main flame (thinner, brighter)
                pygame.draw.rect(
                    icon_surface,
                    (*color, 220),
                    (center[0] - flame_length//2, center[1] - flame_width//2, flame_length, flame_width),
                )
                
                # Add source point glow
                source_x = center[0] - flame_length//2
                pygame.draw.circle(
                    icon_surface,
                    (*color, 150),
                    (source_x, center[1]),
                    max(3, int(icon_size // 6))
                )
                
                # Add energy particles along flame
                for i in range(3):
                    particle_x = source_x + (flame_length * (i+1) // 4)
                    particle_y = center[1] + random.randint(-1, 1)
                    particle_size = random.randint(1, 2)
                    pygame.draw.circle(
                        icon_surface,
                        (255, 255, 255, 200),
                        (particle_x, particle_y),
                        particle_size
                    )

            else:
                # Generic powerup glow for any other types
                center = (icon_size // 2, icon_size // 2)

                # Draw concentric circles with decreasing alpha
                for radius in range(int(icon_size // 2), 0, -2):
                    alpha = int(200 * (radius / (icon_size // 2)))
                    pygame.draw.circle(icon_surface, (*color, alpha), center, radius)

                # Add highlight
                highlight_pos = (center[0] - icon_size // 6, center[1] - icon_size // 6)
                pygame.draw.circle(
                    icon_surface, (255, 255, 255, 150), highlight_pos, max(1, int(icon_size // 6))
                )

            # Position for the icon
            icon_rect = icon_surface.get_rect(midleft=(effects_panel_x, icon_y))

            # Draw the special effect icon
            surface.blit(icon_surface, icon_rect)

            # Get full display name
            display_name = display_names.get(name, name)

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

            expiry_time = state.get("expiry_time")
            if expiry_time is not None:
                time_left_ms = max(0, expiry_time - current_time)
                # Ensure integer division for seconds display
                time_remaining_str = f"{time_left_ms // 1000}s"

            charges = state.get("charges")
            if charges is not None:
                charges_str = f"{charges}"

            # Display charges for scatter bomb, time for others
            if name == PowerupType.SCATTER_BOMB.name and charges_str is not None:
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
        shoot_delay = self.active_powerups_state.get(PowerupType.RAPID_FIRE.name, {}).get(
            "delay", PLAYER_SHOOT_DELAY
        )

        if now - self.last_shot_time > shoot_delay:
            self.last_shot_time = now

            # Get first sprite group (usually all_sprites)
            all_sprites_group = self.groups()[0] if self.groups() else None

            if all_sprites_group:
                # Create three bullets: one straight ahead, one angled up, one angled down
                bullets = [
                    Bullet(
                        self.rect.right, self.rect.centery, all_sprites_group, self.bullets
                    ),  # Center
                    Bullet(
                        self.rect.right, self.rect.centery - 5, all_sprites_group, self.bullets
                    ),  # Top
                    Bullet(
                        self.rect.right, self.rect.centery + 5, all_sprites_group, self.bullets
                    ),  # Bottom
                ]

                # Add vertical velocity component to the upper and lower bullets
                bullets[1].velocity_y = -2.0  # Upward
                bullets[2].velocity_y = 2.0  # Downward

                # Apply homing to all bullets if that powerup is also active (check state dict, use Enum name)
                if PowerupType.HOMING_MISSILES.name in self.active_powerups_state and self.game_ref:
                    # Find closest enemy
                    closest_enemy = None
                    closest_dist = float("inf")

                    # Safely get the enemies group
                    enemies = getattr(self.game_ref, "enemies", None)

                    # Make sure enemies is iterable before trying to iterate
                    if enemies and hasattr(enemies, "__iter__"):
                        # Find closest enemy
                        for enemy in enemies:
                            if hasattr(enemy, "rect") and enemy.alive():
                                dist = (
                                    (enemy.rect.centerx - self.rect.centerx) ** 2
                                    + (enemy.rect.centery - self.rect.centery) ** 2
                                ) ** 0.5
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
                if hasattr(self.image, "set_alpha"):
                    self.image.set_alpha(255)

                # Also reset all animation frames to full opacity
                for frame in self.frames:
                    if hasattr(frame, "set_alpha"):
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
                if hasattr(self.image, "set_alpha"):
                    self.image.set_alpha(alpha)

                # Always keep visible flag true so image is drawn (with varying alpha)
                self.visible = True

    def _check_powerup_expirations(self) -> None:
        """Check and remove expired powerups."""
        current_time = pygame.time.get_ticks()
        expired_powerups = []

        # Iterate through all active powerups and check expiry times
        for powerup_name, state in self.active_powerups_state.items():
            expiry_time = state.get("expiry_time")
            if expiry_time is None:
                continue  # Skip if no expiry (permanent powerup)

            # Check if expired
            if current_time >= expiry_time:
                # Special case for scatter bomb - keep if has charges
                if powerup_name == PowerupType.SCATTER_BOMB.name and state.get("charges", 0) > 0:
                    continue
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
                # Handle drone cleanup
                elif powerup_name == PowerupType.DRONE.name:
                    # Find and remove ALL drone instances from ALL drone powerups
                    # This ensures all drones are removed when any drone powerup expires
                    all_drones_removed = False
                    
                    # First, make a copy of active_powerups_state keys to avoid modification during iteration
                    active_powerup_names = list(self.active_powerups_state.keys())
                    
                    # Loop through all active powerups looking for DRONE types
                    for name in active_powerup_names:
                        if name == PowerupType.DRONE.name:
                            drone_state = self.active_powerups_state.get(name)
                            if drone_state:
                                # Get the drone instance from each drone powerup state
                                drone_instance = drone_state.get("drone_instance")
                                if drone_instance:
                                    # Kill this drone
                                    drone_instance.kill()
                                    all_drones_removed = True
                                    
                                # Remove this drone powerup from active powerups
                                if name in self.active_powerups_state and name != powerup_name:
                                    del self.active_powerups_state[name]
                    
                    # Also clean up using the global drone list to ensure all drones are removed
                    if ACTIVE_DRONES:
                        for drone in ACTIVE_DRONES[:]:  # Use a copy of the list to safely modify while iterating
                            if drone:
                                drone.kill()
                                if drone in ACTIVE_DRONES:
                                    ACTIVE_DRONES.remove(drone)
                        logger.info(f"Removed {len(ACTIVE_DRONES)} drones from global tracking")
                        ACTIVE_DRONES.clear()  # Clear any remaining references
                    
                    if all_drones_removed:
                        logger.info("All drone powerups and drones removed")

            # Note: Time Warp effect removal is handled in game_loop update based on player state

    def add_powerup(
        self,
        powerup_name: str,
        powerup_idx: int,
        duration_ms: Optional[int] = POWERUP_DURATION,
        charges: Optional[int] = None,
        extra_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Adds or refreshes a powerup in the active state dictionary.

        Args:
            powerup_name: The unique string identifier (e.g., "SHIELD").
            powerup_idx: The index corresponding to the icon/sprite (0-8).
            duration_ms: Duration in milliseconds (for timed powerups).
            charges: Number of uses (for charge-based powerups).
            extra_state: Dictionary with any additional state (e.g., rapid fire delay).
        """
        current_time = pygame.time.get_ticks()

        # Create the state dictionary with mandatory index (the enum value is key to positioning)
        # No need to calculate slot - the drawer will use the index directly
        state = {"index": powerup_idx}

        is_refresh = powerup_name in self.active_powerups_state

        if duration_ms is not None:
            state["expiry_time"] = current_time + duration_ms
            state["duration"] = duration_ms  # Store original duration for UI

        if charges is not None:
            # If refreshing, add charges; otherwise, set initial charges.
            current_charges = self.active_powerups_state.get(powerup_name, {}).get("charges", 0)
            state["charges"] = current_charges + charges if is_refresh else charges

        if extra_state:
            state.update(extra_state)

        # Specific handling for Shield state - Use Enum name
        if powerup_name == PowerupType.SHIELD.name:
            state.setdefault("color", (0, 100, 255))  # type: ignore
            state.setdefault("radius", 35)

        # Store in the active powerups dictionary
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

    def _shoot_flamethrower(self, force=False) -> None:
        """Create flame particles when the flamethrower powerup is active.
        
        Args:
            force: If True, bypasses cooldown check for immediate activation
        """
        # Check if powerup is active
        if PowerupType.FLAMETHROWER.name not in self.active_powerups_state:
            return

        # Get current time for cooldown check
        current_time = pygame.time.get_ticks()
        
        # Initialize flame_timer if it doesn't exist
        if not hasattr(self, 'flame_timer'):
            self.flame_timer = 0
        
        # Check cooldown (unless force=True)
        if not force and current_time - self.flame_timer < FLAME_SPAWN_DELAY:
            return
        
        # Update timer
        self.flame_timer = current_time
        
        # Get sprite groups
        all_sprites_group = self.groups()[0] if self.groups() else None
        if not all_sprites_group or not self.bullets:
            return
        
        # Base position slightly in front of player
        base_x = self.rect.right
        base_y = self.rect.centery
        
        # Base velocity with forward movement
        base_vx = 8.0  # Forward speed
        
        # Create multiple flame particles with random spread for a fuller effect
        num_flames = random.randint(2, 4)  # Random number of flames per burst
        
        for _ in range(num_flames):
            # Calculate random vertical angle for spray effect
            angle = random.uniform(-FLAME_SPRAY_ANGLE, FLAME_SPRAY_ANGLE)
            
            # Calculate velocity components with spray angle
            vel_x = base_vx * math.cos(angle)
            vel_y = base_vx * math.sin(angle)
            
            # Add small position variation
            pos_x = base_x + random.uniform(-5, 5)
            pos_y = base_y + random.uniform(-5, 5)
            
            # Random size variation for the flames
            size = random.randint(6, 10)
            
            # Random lifetime variation
            lifetime = random.randint(
                int(FLAME_PARTICLE_LIFETIME * 0.8),
                int(FLAME_PARTICLE_LIFETIME * 1.2)
            )
            
            # Create flame particle
            FlameParticle(
                (pos_x, pos_y),
                (vel_x, vel_y),
                (255, 60, 0),  # Fiery orange-red color
                size,
                lifetime,
                FLAME_PARTICLE_DAMAGE,
                all_sprites_group,
                self.bullets  # Add to bullets group for collision detection
            )
        
        # Sound is now handled by _manage_flamethrower_sound method

    def _shoot_single_bullet(self) -> None:
        """Create a single bullet projectile."""
        # Bullet starts at the front-center of the player
        all_sprites_group = self.groups()[0] if self.groups() else None
        if all_sprites_group:
            # Create the bullet
            bullet = Bullet(self.rect.right, self.rect.centery, all_sprites_group, self.bullets)

            # Make bullet home in on enemies if that powerup is active
            if PowerupType.HOMING_MISSILES.name in self.active_powerups_state and self.game_ref:
                # Find closest enemy
                closest_enemy = None
                closest_dist = float("inf")

                # Safely get the enemies group
                enemies = getattr(self.game_ref, "enemies", None)

                # Make sure enemies is iterable before trying to iterate
                if enemies and hasattr(enemies, "__iter__"):
                    for enemy in enemies:
                        if hasattr(enemy, "rect") and enemy.alive():
                            dist = (
                                (enemy.rect.centerx - self.rect.centerx) ** 2
                                + (enemy.rect.centery - self.rect.centery) ** 2
                            ) ** 0.5
                            if dist < closest_dist:
                                closest_dist = dist
                                closest_enemy = enemy

                if closest_enemy:
                    bullet.make_homing(closest_enemy)

            logger.debug(
                f"Player fired bullet at position {self.rect.right}, {self.rect.centery}"
            )

    def _manage_flamethrower_sound(self, is_active: bool) -> None:
        """Manage the continuous flamethrower sound loop with smooth transitions.
        
        Args:
            is_active: Whether the flamethrower is currently active
        """
        # No sound manager available
        if not self.game_ref or not hasattr(self.game_ref, "sound_manager"):
            return
        
        current_time = pygame.time.get_ticks()
        
        # Flamethrower was just activated
        if is_active and not self.flamethrower_sound_active:
            try:
                # Start the sound immediately
                self.game_ref.sound_manager.play("flamethrower1", "player")
                self.flamethrower_sound_active = True
                self.flamethrower_sound_start_time = current_time
                logger.debug("Started flamethrower sound loop")
            except Exception as e:
                logger.warning(f"Failed to start flamethrower sound: {e}")
                return
        
        # Flamethrower is active and sound is playing - check if we need to loop
        elif is_active and self.flamethrower_sound_active:
            elapsed = current_time - self.flamethrower_sound_start_time
            
            # Start fadeout/fadein transition in the last second
            if elapsed >= self.flamethrower_sound_fadeout_start and self.flamethrower_next_sound_instance is None:
                try:
                    # Calculate fadeout time (remaining time until end of sound)
                    fadeout_ms = self.flamethrower_sound_duration - elapsed
                    
                    # Start the next instance with fadeout of current instance
                    # This creates the smooth transition effect
                    self.game_ref.sound_manager.play("flamethrower1", "player", fadeout_ms=int(fadeout_ms))
                    self.flamethrower_next_sound_instance = current_time
                    logger.debug(f"Starting next flamethrower sound iteration with {fadeout_ms}ms fadeout")
                except Exception as e:
                    logger.warning(f"Failed to start next flamethrower sound: {e}")
            
            # Check if we've completed a full loop
            if elapsed >= self.flamethrower_sound_duration:
                # Reset timers for the next loop
                self.flamethrower_sound_start_time = self.flamethrower_next_sound_instance or current_time
                self.flamethrower_next_sound_instance = None
                logger.debug("Flamethrower sound loop restarted")
        
        # Flamethrower was just deactivated
        elif not is_active and self.flamethrower_sound_active:
            try:
                # Stop the sound with a short fadeout
                if hasattr(self.game_ref.sound_manager, 'sounds') and 'player' in self.game_ref.sound_manager.sounds:
                    if 'flamethrower1' in self.game_ref.sound_manager.sounds['player']:
                        # Use fadeout for a smoother stop
                        self.game_ref.sound_manager.sounds['player']['flamethrower1'].fadeout(300)
                
                self.flamethrower_sound_active = False
                self.flamethrower_next_sound_instance = None
                logger.debug("Stopped flamethrower sound loop")
            except Exception as e:
                logger.warning(f"Failed to stop flamethrower sound: {e}")

    def _manage_laserbeam_sound(self, is_active: bool) -> None:
        """Manage the continuous laser beam sound loop using crossfading.
        
        Args:
            is_active: Whether the laser beam should be making sound.
        """
        # No sound manager available
        if not self.game_ref or not hasattr(self.game_ref, "sound_manager"):
            return
            
        sound_manager = self.game_ref.sound_manager
        current_time = pygame.time.get_ticks()

        # Fetch duration if not already set
        if self.laserbeam_sound_duration == 0:
            duration = sound_manager.get_sound_duration("laserbeam", "player")
            if duration and duration > 1000: # Ensure duration is valid and long enough
                self.laserbeam_sound_duration = duration
                # Start fadeout 1 second before the end, ensure it's not negative
                self.laserbeam_sound_fadeout_start = max(0, duration - 1000) 
            else:
                logger.warning("Could not get valid laserbeam duration, crossfade disabled.")
                # Fallback to simple play/stop if duration invalid
                if is_active and not self.laserbeam_sound_active:
                    try:
                        sound_manager.play("laserbeam", "player", volume=0.7, loops=-1) # Simple loop
                        self.laserbeam_sound_active = True
                    except Exception as e:
                        logger.error(f"Failed to start simple laserbeam loop: {e}")
                elif not is_active and self.laserbeam_sound_active:
                    try:
                        # Need to find the sound object to stop it directly if using simple loop
                        if 'laserbeam' in sound_manager.sounds['player']:
                            sound_manager.sounds['player']['laserbeam'].stop()
                        self.laserbeam_sound_active = False
                    except Exception as e:
                        logger.error(f"Failed to stop simple laserbeam loop: {e}")
                return # Exit after handling fallback

        # --- Crossfade Logic --- 
        
        # Laser beam was just activated
        if is_active and not self.laserbeam_sound_active:
            try:
                # Start the sound immediately using standard play (no loops)
                sound_manager.play("laserbeam", "player", volume=0.7)
                self.laserbeam_sound_active = True
                self.laserbeam_sound_start_time = current_time
                self.laserbeam_next_sound_instance = None # Reset crossfade tracking
                logger.debug("Started laser beam sound (crossfade mode)")
            except Exception as e:
                logger.warning(f"Failed to start laser beam sound: {e}")
                return

        # Laser beam is active and sound is playing - check if we need to crossfade
        elif is_active and self.laserbeam_sound_active:
            elapsed = current_time - self.laserbeam_sound_start_time
            
            # Check if it's time to start the next instance for crossfading
            if elapsed >= self.laserbeam_sound_fadeout_start and self.laserbeam_next_sound_instance is None:
                try:
                    # Calculate fadeout time (remaining time until end of sound)
                    fadeout_ms = self.laserbeam_sound_duration - elapsed
                    # Ensure fadeout is not negative and reasonably short
                    fadeout_ms = max(100, min(fadeout_ms, 1000)) 
                    
                    # Start the next instance with fadeout of current instance
                    sound_manager.play("laserbeam", "player", volume=0.7, fadeout_ms=int(fadeout_ms))
                    self.laserbeam_next_sound_instance = current_time # Mark when next instance started
                    logger.debug(f"Starting next laser beam sound iteration with {fadeout_ms}ms fadeout")
                except Exception as e:
                    logger.warning(f"Failed to start next laser beam sound instance: {e}")
            
            # Check if we've completed a full loop cycle (based on duration)
            if elapsed >= self.laserbeam_sound_duration:
                # Reset timers using the start time of the *next* instance if crossfading occurred
                self.laserbeam_sound_start_time = self.laserbeam_next_sound_instance or current_time
                self.laserbeam_next_sound_instance = None # Reset for next cycle
                logger.debug("Laser beam sound loop cycle completed")

        # Laser beam was just deactivated
        elif not is_active and self.laserbeam_sound_active:
            try:
                # Stop the sound with a short fadeout
                # Find the specific sound object to apply fadeout
                if 'laserbeam' in sound_manager.sounds['player']:
                     sound_manager.sounds['player']['laserbeam'].fadeout(150) # Slightly longer fadeout
                else:
                    # If somehow the sound isn't found, log it but still mark as inactive
                     logger.warning("Could not find 'laserbeam' sound object to fade out.")

                self.laserbeam_sound_active = False
                self.laserbeam_next_sound_instance = None # Ensure reset
                logger.debug("Stopped laser beam sound (crossfade mode)")
            except Exception as e:
                logger.warning(f"Failed to stop laser beam sound with fadeout: {e}")
                # Fallback stop
                try:
                    if 'laserbeam' in sound_manager.sounds['player']:
                         sound_manager.sounds['player']['laserbeam'].stop()
                    self.laserbeam_sound_active = False
                    self.laserbeam_next_sound_instance = None
                except Exception as e2:
                     logger.error(f"Failed even fallback stop for laser beam sound: {e2}")
