"""Implementation of powerup type behaviors."""

import math
import random
from enum import auto
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, ClassVar, Union

import pygame

from config.config import PLAYER_SHOOT_DELAY, DRONE_DURATION, FLAMETHROWER_DURATION, FLAME_PARTICLE_DAMAGE, FLAME_PARTICLE_LIFETIME, FLAME_SPRAY_ANGLE
from src.logger import get_logger
from src.powerup import POWERUP_DURATION, Powerup, PowerupParticle, PowerupType
from src.projectile import Bullet, LaserBeam, ScatterProjectile
from src.drone import Drone
from src.particle import FlameParticle

# Get a logger for this module
logger = get_logger(__name__)

# Global registry to store powerup classes by type
POWERUP_REGISTRY: Dict[PowerupType, Type[Powerup]] = {}

# Global collection to track all active drones
# This ensures we can find and remove all drones even if state management fails
ACTIVE_DRONES = []

def register_powerup(powerup_type: PowerupType) -> Callable:
    """Decorator to register a powerup class with its type.
    
    Args:
        powerup_type: The PowerupType enum value for this powerup
        
    Returns:
        A decorator function that registers the decorated class
    """
    def decorator(cls):
        POWERUP_REGISTRY[powerup_type] = cls
        # Store the type directly on the class
        cls.powerup_type_enum = powerup_type
        return cls
    return decorator

# Classification of powerups by effect type
# For future usage when filtering/displaying powerups
DURATION_POWERUPS = [
    PowerupType.TRIPLE_SHOT,
    PowerupType.RAPID_FIRE,
    PowerupType.SHIELD,
    PowerupType.HOMING_MISSILES,
    PowerupType.TIME_WARP,
    PowerupType.LASER_BEAM,
    PowerupType.DRONE,
    PowerupType.FLAMETHROWER,
]

CHARGE_POWERUPS = [
    PowerupType.SCATTER_BOMB,
]

INSTANT_POWERUPS = [
    PowerupType.POWER_RESTORE,
    PowerupType.MEGA_BLAST,
]

# Create a base class for our registry-compatible powerups
class PowerupBase(Powerup):
    """Base class for all powerups that use the registry system."""
    
    # This will be set by the decorator
    powerup_type_enum: ClassVar[PowerupType]
    
    def __init__(
        self,
        x: float,
        y: float,
        *groups,
        particles_group: Optional[pygame.sprite.Group] = None,
        game_ref=None,
    ) -> None:
        """Initialize the powerup with the type stored in the class attribute."""
        # Pass the type from the class attribute to the Powerup constructor
        super().__init__(self.__class__.powerup_type_enum, x, y, *groups, particles_group=particles_group)
        self.game_ref = game_ref
    
    @classmethod
    def create(
        cls,
        x: float,
        y: float,
        *groups,
        particles_group: Optional[pygame.sprite.Group] = None,
        game_ref=None,
    ) -> 'PowerupBase':
        """Class method to create a powerup instance without type confusion."""
        return cls(x, y, *groups, particles_group=particles_group, game_ref=game_ref)

@register_powerup(PowerupType.TRIPLE_SHOT)
class TripleShotPowerup(PowerupBase):
    """Triple shot powerup - player fires 3 bullets at once."""
    
    # Explicitly define as class variable with correct type
    powerup_type_enum: ClassVar[PowerupType] = PowerupType.TRIPLE_SHOT

    def apply_effect(self, player) -> None:
        """Apply the triple shot effect to the player."""
        super().apply_effect(player)  # Call base implementation

        # Use the centralized state management method
        player.add_powerup(
            powerup_name=PowerupType.TRIPLE_SHOT.name,
            powerup_idx=PowerupType.TRIPLE_SHOT.value,
            duration_ms=POWERUP_DURATION,
        )

        # Create collection effect
        self._create_collection_effect(player.rect.center)

        logger.info("Triple Shot activated for 10 seconds")

@register_powerup(PowerupType.RAPID_FIRE)
class RapidFirePowerup(PowerupBase):
    """Rapid fire powerup - player shoots more frequently."""
    
    # Explicitly define as class variable with correct type
    powerup_type_enum: ClassVar[PowerupType] = PowerupType.RAPID_FIRE

    def apply_effect(self, player) -> None:
        """Apply the rapid fire effect to the player."""
        super().apply_effect(player)  # Call base implementation

        # Calculate the rapid fire delay
        # Use PLAYER_SHOOT_DELAY directly from config
        rapid_fire_delay = PLAYER_SHOOT_DELAY // 3

        # Use the centralized state management method
        player.add_powerup(
            powerup_name=PowerupType.RAPID_FIRE.name,
            powerup_idx=PowerupType.RAPID_FIRE.value,
            duration_ms=POWERUP_DURATION,
            extra_state={"delay": rapid_fire_delay},  # Store the calculated delay
        )

        # Create collection effect
        self._create_collection_effect(player.rect.center)

        logger.info("Rapid Fire activated for 10 seconds")

@register_powerup(PowerupType.SHIELD)
class ShieldPowerup(PowerupBase):
    """Shield powerup - temporary invulnerability."""
    
    # Explicitly define as class variable with correct type
    powerup_type_enum: ClassVar[PowerupType] = PowerupType.SHIELD

    def apply_effect(self, player) -> None:
        """Apply the shield effect to the player."""
        super().apply_effect(player)  # Call base implementation

        # Use the centralized state management method
        player.add_powerup(
            powerup_name=PowerupType.SHIELD.name,
            powerup_idx=PowerupType.SHIELD.value,
            duration_ms=POWERUP_DURATION,
        )

        # Create collection effect
        self._create_collection_effect(player.rect.center)

        # Create shield visual
        # This could be implemented in the player's draw method
        # For now we just log that we got it
        logger.info("Shield activated for 10 seconds")

@register_powerup(PowerupType.HOMING_MISSILES)
class HomingMissilesPowerup(PowerupBase):
    """Homing missiles powerup - bullets track nearest enemy."""
    
    # Explicitly define as class variable with correct type
    powerup_type_enum: ClassVar[PowerupType] = PowerupType.HOMING_MISSILES

    def apply_effect(self, player) -> None:
        """Apply the homing missiles effect to the player."""
        super().apply_effect(player)  # Call base implementation

        # Set the game reference if one is available and player doesn't have one
        if self.game_ref and not hasattr(player, "game_ref") or not player.game_ref:
            player.game_ref = self.game_ref
            logger.info("Set game reference on player from homing missile powerup")

        # Use the centralized state management method
        player.add_powerup(
            powerup_name=PowerupType.HOMING_MISSILES.name,
            powerup_idx=PowerupType.HOMING_MISSILES.value,
            duration_ms=POWERUP_DURATION,
            # No extra state needed; homing logic checks if key exists in dict
        )

        # Create collection effect
        self._create_collection_effect(player.rect.center)

        logger.info("Homing Missiles activated for 10 seconds")
        # Note: The actual homing behavior would be implemented in the Bullet class
        # or a new HomingMissile class, and player.update would check for expiry

@register_powerup(PowerupType.POWER_RESTORE)
class PowerRestorePowerup(PowerupBase):
    """Power restore powerup - instantly restores player's power to max."""
    
    # Explicitly define as class variable with correct type
    powerup_type_enum: ClassVar[PowerupType] = PowerupType.POWER_RESTORE

    def apply_effect(self, player) -> None:
        """Apply the power restore effect to the player."""
        # Don't call base implementation since we're doing a custom power restoration

        # Import MAX_POWER_LEVEL here to avoid dependency cycle at module level
        from src.player import MAX_POWER_LEVEL

        # Skip if player already has max power
        if player.power_level >= MAX_POWER_LEVEL:
            logger.info("Power already at maximum level, no restoration needed")
            return

        # Restore power to maximum (directly modify player attribute)
        old_power = player.power_level
        player.power_level = MAX_POWER_LEVEL

        # Create healing effect particles
        self._create_collection_effect(player.rect.center)

        # Log the power increase
        logger.info(f"Power fully restored from {old_power} to {player.power_level}")

        # Note: Power Restore does not add itself to the active_powerups_state
        # as it's an instant effect with no duration or charges.

@register_powerup(PowerupType.SCATTER_BOMB)
class ScatterBombPowerup(PowerupBase):
    """Scatter bomb powerup - releases burst of projectiles in all directions."""
    
    # Explicitly define as class variable with correct type
    powerup_type_enum: ClassVar[PowerupType] = PowerupType.SCATTER_BOMB

    def apply_effect(self, player) -> None:
        """Apply the scatter bomb effect to the player."""
        super().apply_effect(player)  # Call base implementation

        # Use the centralized state management method
        # Add 3 charges initially, subsequent pickups will add more via add_powerup logic
        player.add_powerup(
            powerup_name=PowerupType.SCATTER_BOMB.name,
            powerup_idx=PowerupType.SCATTER_BOMB.value,
            charges=3,
        )

        # Create collection effect
        self._create_collection_effect(player.rect.center)

        # Log message handled by add_powerup
        # logger.info(f"Scatter Bomb activated with {player.scatter_bomb_charges} charges")

        # Note: The actual scatter bombing would be handled in the player's update
        # or a new method triggered by a key press

@register_powerup(PowerupType.TIME_WARP)
class TimeWarpPowerup(PowerupBase):
    """Time warp powerup - slows down enemies and enemy bullets."""
    
    # Explicitly define as class variable with correct type
    powerup_type_enum: ClassVar[PowerupType] = PowerupType.TIME_WARP

    def apply_effect(self, player) -> None:
        """Apply the time warp effect."""
        super().apply_effect(player)  # Call base implementation

        # Set the game reference if one is available and player doesn't have one
        if self.game_ref and not hasattr(player, "game_ref") or not player.game_ref:
            player.game_ref = self.game_ref
            logger.info("Set game reference on player from time warp powerup")

        # Use the centralized state management method
        player.add_powerup(
            powerup_name=PowerupType.TIME_WARP.name,
            powerup_idx=PowerupType.TIME_WARP.value,
            duration_ms=POWERUP_DURATION,
        )

        # Create collection effect
        self._create_collection_effect(player.rect.center)

        logger.info("Time Warp activated for 10 seconds")
        # Note: The actual time warping would be implemented in the
        # game's update method, slowing down enemies and bullets

@register_powerup(PowerupType.MEGA_BLAST)
class MegaBlastPowerup(PowerupBase):
    """Mega blast powerup - screen-clearing explosion."""
    
    # Explicitly define as class variable with correct type
    powerup_type_enum: ClassVar[PowerupType] = PowerupType.MEGA_BLAST

    def apply_effect(self, player) -> None:
        """Apply the mega blast effect.
        
        This is an instant powerup that creates a shockwave that destroys enemies.
        """
        # Don't call super().apply_effect for instant powerups
        # Log the effect directly instead
        logger.info("Mega Blast activated")

        # Create collection effect
        self._create_collection_effect(player.rect.center)

        # Create a mega blast effect if the game reference is available
        if self.game_ref:
            # Try to access the mega blast method
            if hasattr(self.game_ref, "_create_mega_blast"):
                try:
                    # Call the mega blast method
                    self.game_ref._create_mega_blast(player.rect.center)
                except Exception as e:
                    logger.error(f"Error creating mega blast: {e}")
            else:
                logger.warning("Game instance does not have _create_mega_blast method")
        else:
            logger.warning("No game reference available for Mega Blast powerup")

        # Note: Mega Blast does not add itself to the active_powerups_state
        # as it's an instant effect with no duration or charges.
        
        # Explicitly remove MEGA_BLAST from player's active powerups state to prevent artifacts
        # if hasattr(player, "active_powerups_state"):
        #     # Check both string literal and enum name format
        #     if "MEGA_BLAST" in player.active_powerups_state:
        #         del player.active_powerups_state["MEGA_BLAST"]
        #         logger.debug("Removed MEGA_BLAST from active powerups state after effect was applied")
            
        #     if PowerupType.MEGA_BLAST.name in player.active_powerups_state:
        #         del player.active_powerups_state[PowerupType.MEGA_BLAST.name]
        #         logger.debug("Removed PowerupType.MEGA_BLAST.name from active powerups state after effect was applied")

@register_powerup(PowerupType.LASER_BEAM)
class LaserBeamPowerup(PowerupBase):
    """Laser beam powerup - player fires a powerful growing green laser beam."""
    
    # Explicitly define as class variable with correct type
    powerup_type_enum: ClassVar[PowerupType] = PowerupType.LASER_BEAM

    def apply_effect(self, player) -> None:
        """Apply the laser beam effect to the player."""
        super().apply_effect(player)  # Call base implementation

        # Use the centralized state management method
        player.add_powerup(
            powerup_name=PowerupType.LASER_BEAM.name,
            powerup_idx=PowerupType.LASER_BEAM.value,
            duration_ms=POWERUP_DURATION,
            charges=5,  # Add 5 laser beam charges
        )

        # Create collection effect
        self._create_collection_effect(player.rect.center)

        logger.info("Laser Beam activated for 10 seconds with 5 charges")

@register_powerup(PowerupType.DRONE)
class DronePowerup(PowerupBase):
    """Drone powerup - spawns a drone that orbits the player and shoots enemies."""
    
    # Explicitly define as class variable with correct type
    powerup_type_enum: ClassVar[PowerupType] = PowerupType.DRONE

    def apply_effect(self, player) -> None:
        """Apply the drone effect to the player."""
        super().apply_effect(player)  # Call base implementation

        # Check if we have a valid game reference
        if not self.game_ref:
            logger.warning("No game reference available, drone powerup might not work correctly")
            return

        # Create a drone instance
        drone = Drone(
            player, 
            self.game_ref.enemies, 
            player.bullets,
            self.game_ref.all_sprites
        )
        
        # Keep track of drone globally
        global ACTIVE_DRONES
        ACTIVE_DRONES.append(drone)
        
        # Use the centralized state management method
        player.add_powerup(
            powerup_name=PowerupType.DRONE.name,
            powerup_idx=PowerupType.DRONE.value,
            duration_ms=DRONE_DURATION,
            extra_state={"drone_instance": drone},
        )

        # Create collection effect
        self._create_collection_effect(player.rect.center)

        logger.info(f"Drone activated for 15 seconds")

@register_powerup(PowerupType.FLAMETHROWER)
class FlamethrowerPowerup(PowerupBase):
    """Flamethrower powerup - player sprays flames up and down in a fiery effect."""
    
    # Explicitly define as class variable with correct type
    powerup_type_enum: ClassVar[PowerupType] = PowerupType.FLAMETHROWER

    def apply_effect(self, player) -> None:
        """Apply the flamethrower effect to the player."""
        super().apply_effect(player)  # Call base implementation

        # Import required modules and constants
        from config.config import FLAMETHROWER_DURATION, FLAME_PARTICLE_DAMAGE, FLAME_PARTICLE_LIFETIME, FLAME_SPRAY_ANGLE
        from src.particle import FlameParticle
        import random
        import math

        # Use the centralized state management method
        player.add_powerup(
            powerup_name=PowerupType.FLAMETHROWER.name,
            powerup_idx=PowerupType.FLAMETHROWER.value,
            duration_ms=FLAMETHROWER_DURATION,
        )

        # Create collection effect
        self._create_collection_effect(player.rect.center)
        
        # ===== DIRECT FLAME PARTICLE CREATION =====
        # Instead of relying on Player's _shoot_flamethrower, we'll create particles directly
        
        # 1. Reset flame timer to allow future particle creation
        if hasattr(player, 'flame_timer'):
            player.flame_timer = 0
        
        # Get necessary references
        game = self.game_ref
        if not game or not hasattr(game, 'all_sprites'):
            logger.warning("Cannot create immediate flame particles: no game reference or sprite groups")
        else:
            # Get sprite groups for particles
            all_sprites_group = game.all_sprites
            bullets_group = player.bullets if hasattr(player, 'bullets') else None
            
            if all_sprites_group and bullets_group:
                # Base position slightly in front of player
                base_x = player.rect.right
                base_y = player.rect.centery
                
                # Create an initial burst of flames (more than usual for dramatic effect)
                for _ in range(10):  # Create 10 particles for a big initial burst
                    # Calculate random vertical angle for spray effect
                    angle = random.uniform(-FLAME_SPRAY_ANGLE, FLAME_SPRAY_ANGLE)
                    
                    # Random velocity with forward momentum
                    speed = random.uniform(6.0, 10.0)  # Faster than normal for dramatic effect
                    vel_x = speed * math.cos(angle)
                    vel_y = speed * math.sin(angle)
                    
                    # Add position variation
                    pos_x = base_x + random.uniform(-10, 10)
                    pos_y = base_y + random.uniform(-10, 10)
                    
                    # Random size and lifetime
                    size = random.randint(6, 12)  # Slightly larger than normal
                    lifetime = random.randint(
                        int(FLAME_PARTICLE_LIFETIME * 0.8),
                        int(FLAME_PARTICLE_LIFETIME * 1.5)  # Longer lifetimes for initial burst
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
                        bullets_group  # Add to bullets group for collision detection
                    )
                
                logger.info("Created immediate flame particles on powerup collection")
        
        # 3. Activate sound immediately
        if hasattr(player, '_manage_flamethrower_sound'):
            player._manage_flamethrower_sound(True)
        
        # Also try the player's method (as a backup)
        if hasattr(player, '_shoot_flamethrower'):
            try:
                player._shoot_flamethrower(force=True)
            except Exception as e:
                logger.warning(f"Failed to call player's _shoot_flamethrower: {e}")

        # Log activation
        logger.info(f"Flamethrower activated for {FLAMETHROWER_DURATION/1000} seconds with immediate effect")

# Factory function to create a powerup of a specific type
def create_powerup(
    powerup_type: Union[int, PowerupType],
    x: float,
    y: float,
    *groups,
    particles_group: Optional[pygame.sprite.Group] = None,
    game_ref=None,
) -> Powerup:
    """Create a powerup of the specified type.

    Args:
        powerup_type: Index (integer value) or PowerupType enum member
        x: Initial x position
        y: Initial y position
        groups: Sprite groups to add to
        particles_group: Optional group for particle effects
        game_ref: Reference to the game instance

    Returns:
        A new powerup instance of the appropriate type
    """
    # Convert int to PowerupType if needed
    if isinstance(powerup_type, int):
        try:
            powerup_enum_member = PowerupType(powerup_type)
        except ValueError:
            logger.error(f"Invalid powerup type integer: {powerup_type}")
            # Default to Triple Shot as a fallback
            powerup_enum_member = PowerupType.TRIPLE_SHOT
    else:
        # Already a PowerupType
        powerup_enum_member = powerup_type

    # Get the correct class from the registry using the Enum member
    powerup_class = POWERUP_REGISTRY.get(powerup_enum_member)

    if not powerup_class:
        logger.error(f"No class registered for powerup type: {powerup_enum_member.name}")
        # Fallback to Triple Shot class
        powerup_class = POWERUP_REGISTRY[PowerupType.TRIPLE_SHOT]

    # Use a type cast to silence the linter error
    from typing import cast
    
    # Create powerup instance - the linter gets confused about parameter order
    # pylint: disable=no-member
    powerup = cast(Type[PowerupBase], powerup_class).create(
        x,
        y,
        *groups,
        particles_group=particles_group,
        game_ref=game_ref,
    )
    
    return powerup

# Helper function to get all registered powerup types
def get_all_powerup_types() -> List[PowerupType]:
    """Get a list of all registered powerup types.
    
    Returns:
        List of PowerupType enum values for all registered powerups
    """
    return list(POWERUP_REGISTRY.keys())

# Helper function to get powerups by category
def get_powerups_by_category(category: str) -> List[PowerupType]:
    """Get powerups by category.
    
    Args:
        category: The category to filter by ('duration', 'charge', or 'instant')
        
    Returns:
        List of PowerupType enum values in the requested category
    """
    if category == 'duration':
        return DURATION_POWERUPS
    elif category == 'charge':
        return CHARGE_POWERUPS
    elif category == 'instant':
        return INSTANT_POWERUPS
    else:
        logger.warning(f"Unknown powerup category: {category}")
        return []
