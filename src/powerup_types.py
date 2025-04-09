"""Implementation of powerup type behaviors."""

import math
import random
from typing import Any, Dict, List, Optional, Tuple

import pygame

from config.config import PLAYER_SHOOT_DELAY
from src.logger import get_logger
from src.powerup import POWERUP_DURATION, Powerup, PowerupParticle, PowerupType
from src.projectile import Bullet, ScatterProjectile

# Get a logger for this module
logger = get_logger(__name__)


class TripleShotPowerup(Powerup):
    """Triple shot powerup - player fires 3 bullets at once."""

    def __init__(
        self,
        x: float,
        y: float,
        *groups,
        particles_group: Optional[pygame.sprite.Group] = None,
        game_ref=None,
    ) -> None:
        super().__init__(PowerupType.TRIPLE_SHOT, x, y, *groups, particles_group=particles_group)

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


class RapidFirePowerup(Powerup):
    """Rapid fire powerup - player shoots more frequently."""

    def __init__(
        self,
        x: float,
        y: float,
        *groups,
        particles_group: Optional[pygame.sprite.Group] = None,
        game_ref=None,
    ) -> None:
        super().__init__(PowerupType.RAPID_FIRE, x, y, *groups, particles_group=particles_group)

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


class ShieldPowerup(Powerup):
    """Shield powerup - temporary invulnerability."""

    def __init__(
        self,
        x: float,
        y: float,
        *groups,
        particles_group: Optional[pygame.sprite.Group] = None,
        game_ref=None,
    ) -> None:
        super().__init__(PowerupType.SHIELD, x, y, *groups, particles_group=particles_group)

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


class HomingMissilesPowerup(Powerup):
    """Homing missiles powerup - bullets track nearest enemy."""

    def __init__(
        self,
        x: float,
        y: float,
        *groups,
        particles_group: Optional[pygame.sprite.Group] = None,
        game_ref=None,
    ) -> None:
        super().__init__(
            PowerupType.HOMING_MISSILES,
            x,
            y,
            *groups,
            particles_group=particles_group,
            game_ref=game_ref,
        )

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


class PowerRestorePowerup(Powerup):
    """Power restore powerup - instantly restores player's power to max."""

    def __init__(
        self,
        x: float,
        y: float,
        *groups,
        particles_group: Optional[pygame.sprite.Group] = None,
        game_ref=None,
    ) -> None:
        super().__init__(PowerupType.POWER_RESTORE, x, y, *groups, particles_group=particles_group)

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


class ScatterBombPowerup(Powerup):
    """Scatter bomb powerup - releases burst of projectiles in all directions."""

    def __init__(
        self,
        x: float,
        y: float,
        *groups,
        particles_group: Optional[pygame.sprite.Group] = None,
        game_ref=None,
    ) -> None:
        super().__init__(PowerupType.SCATTER_BOMB, x, y, *groups, particles_group=particles_group)

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


class TimeWarpPowerup(Powerup):
    """Time warp powerup - slows down enemies and enemy bullets."""

    def __init__(
        self,
        x: float,
        y: float,
        *groups,
        particles_group: Optional[pygame.sprite.Group] = None,
        game_ref=None,
    ) -> None:
        super().__init__(PowerupType.TIME_WARP, x, y, *groups, particles_group=particles_group)

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


class MegaBlastPowerup(Powerup):
    """Mega blast powerup - screen-clearing explosion."""

    def __init__(
        self,
        x: float,
        y: float,
        *groups,
        particles_group: Optional[pygame.sprite.Group] = None,
        game_ref=None,
    ) -> None:
        super().__init__(PowerupType.MEGA_BLAST, x, y, *groups, particles_group=particles_group)

    def apply_effect(self, player) -> None:
        """Apply the mega blast effect - immediately destroy all enemies."""
        super().apply_effect(player)  # Call base implementation

        # We'll need access to game objects, so ensure player has game_ref
        game_ref = getattr(player, "game_ref", None)
        if not game_ref and self.game_ref:
            game_ref = self.game_ref  # Fallback to powerup's game_ref if player's is missing
            logger.warning("Used powerup's game_ref for Mega Blast")

        if game_ref:
            # Get all active enemies
            enemies = list(game_ref.enemies.sprites())

            # Count how many enemies were destroyed
            enemy_count = len(enemies)

            # Create explosion for each enemy
            for enemy in enemies:
                # Add points
                game_ref.score += 100

                # Create explosion at enemy position
                explosion_size = (50, 50)
                from src.explosion import Explosion  # Import here to avoid circular imports

                Explosion(
                    enemy.rect.center,
                    explosion_size,
                    "enemy",
                    game_ref.explosions,
                    particles_group=game_ref.particles,
                )

                # Remove the enemy
                enemy.kill()

            # Create mega blast effect around the player
            self._create_collection_effect(player.rect.center)

            # Play sound
            if hasattr(game_ref, "sound_manager"):
                game_ref.sound_manager.play("explosion1", "player")

            logger.info(f"Mega Blast destroyed {enemy_count} enemies!")
        else:
            logger.warning("Mega Blast couldn't access game reference")

        # Note: Mega Blast does not add itself to the active_powerups_state
        # as it's an instant effect with no duration or charges.


# Factory function to create a powerup of a specific type
def create_powerup(
    powerup_type: int,
    x: float,
    y: float,
    *groups,
    particles_group: Optional[pygame.sprite.Group] = None,
    game_ref=None,
) -> Powerup:
    """Create a powerup of the specified type.

    Args:
        powerup_type: Index (integer value) of the powerup type (0-7)
        x: Initial x position
        y: Initial y position
        groups: Sprite groups to add to
        particles_group: Optional group for particle effects
        game_ref: Reference to the game instance

    Returns:
        A new powerup instance of the appropriate type
    """
    powerup_class_map = {
        PowerupType.TRIPLE_SHOT: TripleShotPowerup,
        PowerupType.RAPID_FIRE: RapidFirePowerup,
        PowerupType.SHIELD: ShieldPowerup,
        PowerupType.HOMING_MISSILES: HomingMissilesPowerup,
        PowerupType.POWER_RESTORE: PowerRestorePowerup,
        PowerupType.SCATTER_BOMB: ScatterBombPowerup,
        PowerupType.TIME_WARP: TimeWarpPowerup,
        PowerupType.MEGA_BLAST: MegaBlastPowerup,
    }

    # Try to get the corresponding Enum member from the integer value
    try:
        powerup_enum_member = PowerupType(powerup_type)
    except ValueError:
        logger.error(f"Invalid powerup type integer: {powerup_type}")
        # Default to Triple Shot as a fallback
        powerup_enum_member = PowerupType.TRIPLE_SHOT

    # Get the correct class from the mapping using the Enum member
    powerup_class = powerup_class_map.get(powerup_enum_member)

    if not powerup_class:
        logger.error(f"No class mapped for powerup type: {powerup_enum_member.name}")
        # Fallback to Triple Shot class
        powerup_class = TripleShotPowerup
        powerup_enum_member = PowerupType.TRIPLE_SHOT  # Ensure enum member matches class

    # Create the powerup instance, passing the Enum member to the constructor
    return powerup_class(
        x,
        y,
        *groups,
        particles_group=particles_group,
        game_ref=game_ref,
        # Note: The __init__ of the specific powerup class now takes the Enum member
    )
