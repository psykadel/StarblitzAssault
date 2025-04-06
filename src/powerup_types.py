"""Specialized powerup types for Starblitz Assault."""

import pygame
import math
import random
from typing import Optional, Tuple, List, Dict, Any

from src.powerup import Powerup, POWERUP_DURATION, POWERUP_TYPES, PowerupParticle
from src.projectile import Bullet, ScatterProjectile
from src.logger import get_logger
from config.game_config import PLAYER_SHOOT_DELAY

logger = get_logger(__name__)

class TripleShotPowerup(Powerup):
    """Triple shot powerup - player fires 3 bullets at once."""
    
    def __init__(self, x: float, y: float, *groups, 
                 particles_group: Optional[pygame.sprite.Group] = None,
                 game_ref = None) -> None:
        super().__init__(0, x, y, *groups, particles_group=particles_group)
        
    def apply_effect(self, player) -> None:
        """Apply the triple shot effect to the player."""
        super().apply_effect(player)  # Call base implementation for power
        
        # Store original shoot method
        player.original_shoot = player.shoot
        
        # Replace with triple shot
        def triple_shot():
            now = pygame.time.get_ticks()
            if now - player.last_shot_time > PLAYER_SHOOT_DELAY:
                player.last_shot_time = now
                
                # Get sprite groups
                all_sprites_group = player.groups()[0] if player.groups() else None
                if all_sprites_group:
                    # Center bullet
                    Bullet(player.rect.right, player.rect.centery, 
                          all_sprites_group, player.bullets)
                    
                    # Bullet above
                    Bullet(player.rect.right, player.rect.centery - 15, 
                          all_sprites_group, player.bullets)
                    
                    # Bullet below
                    Bullet(player.rect.right, player.rect.centery + 15,
                          all_sprites_group, player.bullets)
                    
                    logger.debug("Player fired triple shot")
        
        # Set expiry time
        player.triple_shot_expiry = pygame.time.get_ticks() + POWERUP_DURATION
        player.has_triple_shot = True
        
        # Replace shoot method
        player.shoot = triple_shot
        
        # Create collection effect
        self._create_collection_effect(player.rect.center)
        
        logger.info("Triple Shot activated for 10 seconds")

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
        
        # Create a larger burst of particles
        for _ in range(40):  # Increased from 20 to 40 particles
            # Random angle and speed
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2.0, 5.0)  # Increased from 1.0-3.0 to 2.0-5.0
            
            vel_x = math.cos(angle) * speed
            vel_y = math.sin(angle) * speed
            
            # Random size and lifetime
            size = random.randint(4, 12)  # Increased from 3-8 to 4-12
            lifetime = random.randint(40, 80)  # Increased from 30-60 to 40-80
            
            # Create particle
            PowerupParticle(
                position, (vel_x, vel_y), color,
                size, lifetime, 0.03, 0.96,
                self.particles_group
            )


class RapidFirePowerup(Powerup):
    """Rapid fire powerup - player shoots more frequently."""
    
    def __init__(self, x: float, y: float, *groups, 
                 particles_group: Optional[pygame.sprite.Group] = None,
                 game_ref = None) -> None:
        super().__init__(1, x, y, *groups, particles_group=particles_group)
        
    def apply_effect(self, player) -> None:
        """Apply the rapid fire effect to the player."""
        super().apply_effect(player)  # Call base implementation for power
        
        # Store normal shoot delay if not yet stored
        if not hasattr(player, 'normal_shoot_delay'):
            player.normal_shoot_delay = PLAYER_SHOOT_DELAY
        
        # Set the new rapid fire delay (1/3 of normal)
        player.rapid_fire_delay = player.normal_shoot_delay // 3
        
        # Set expiry time
        player.rapid_fire_expiry = pygame.time.get_ticks() + POWERUP_DURATION
        player.has_rapid_fire = True
        
        # Create collection effect
        self._create_collection_effect(player.rect.center)
        
        logger.info("Rapid Fire activated for 10 seconds")


class ShieldPowerup(Powerup):
    """Shield powerup - temporary invulnerability."""
    
    def __init__(self, x: float, y: float, *groups, 
                 particles_group: Optional[pygame.sprite.Group] = None,
                 game_ref = None) -> None:
        super().__init__(2, x, y, *groups, particles_group=particles_group)
        
    def apply_effect(self, player) -> None:
        """Apply the shield effect to the player."""
        super().apply_effect(player)  # Call base implementation for power
        
        # Make player invincible
        player.is_invincible = True
        
        # Set expiry time longer than normal invincibility
        player.shield_expiry = pygame.time.get_ticks() + POWERUP_DURATION
        player.has_shield = True
        
        # Create collection effect
        self._create_collection_effect(player.rect.center)
        
        # Create shield visual
        # This could be implemented in the player's draw method
        # For now we just log that we got it
        logger.info("Shield activated for 10 seconds")


class HomingMissilesPowerup(Powerup):
    """Homing missiles powerup - bullets track nearest enemy."""
    
    def __init__(self, x: float, y: float, *groups, 
                 particles_group: Optional[pygame.sprite.Group] = None,
                 game_ref = None) -> None:
        super().__init__(3, x, y, *groups, particles_group=particles_group, game_ref=game_ref)
        
    def apply_effect(self, player) -> None:
        """Apply the homing missiles effect to the player."""
        super().apply_effect(player)  # Call base implementation for power
        
        # Store original shoot method if not already stored
        if not hasattr(player, 'original_shoot'):
            player.original_shoot = player.shoot
        
        # Set the game reference if one is available
        if self.game_ref and not player.game_ref:
            player.game_ref = self.game_ref
            logger.info("Set game reference on player from powerup")
        
        # Set expiry time
        player.homing_missiles_expiry = pygame.time.get_ticks() + POWERUP_DURATION
        player.has_homing_missiles = True
        
        # Create collection effect
        self._create_collection_effect(player.rect.center)
        
        logger.info("Homing Missiles activated for 10 seconds")
        # Note: The actual homing behavior would be implemented in the Bullet class
        # or a new HomingMissile class, and player.update would check for expiry


class PulseBeamPowerup(Powerup):
    """Pulse beam powerup - charge and release a powerful beam."""
    
    def __init__(self, x: float, y: float, *groups, 
                 particles_group: Optional[pygame.sprite.Group] = None,
                 game_ref = None) -> None:
        super().__init__(4, x, y, *groups, particles_group=particles_group)
        
    def apply_effect(self, player) -> None:
        """Apply the pulse beam effect to the player."""
        super().apply_effect(player)  # Call base implementation for power
        
        # Give player the ability to charge a pulse beam
        player.has_pulse_beam = True
        
        # Initialize pulse beam variables
        player.pulse_beam_charge = 0
        player.max_pulse_beam_charge = 100
        player.is_charging = False
        
        # Set expiry time
        player.pulse_beam_expiry = pygame.time.get_ticks() + POWERUP_DURATION
        
        # Create collection effect
        self._create_collection_effect(player.rect.center)
        
        logger.info("Pulse Beam activated for 10 seconds")
        # Note: The pulse beam firing would be implemented in 
        # additional methods on the Player class


class PowerRestorePowerup(Powerup):
    """Power restore powerup - instantly restores player's power to max."""
    
    def __init__(self, x: float, y: float, *groups, 
                 particles_group: Optional[pygame.sprite.Group] = None,
                 game_ref = None) -> None:
        super().__init__(5, x, y, *groups, particles_group=particles_group)
        
    def apply_effect(self, player) -> None:
        """Apply the power restore effect to the player."""
        # Don't call base implementation since we're doing a custom power restoration
        
        # Restore power to maximum
        old_power = player.power_level
        player.power_level = 5  # MAX_POWER_LEVEL
        
        # Create healing effect particles
        self._create_collection_effect(player.rect.center)
        
        # Log the power increase
        logger.info(f"Power fully restored from {old_power} to {player.power_level}")


class ScatterBombPowerup(Powerup):
    """Scatter bomb powerup - releases burst of projectiles in all directions."""
    
    def __init__(self, x: float, y: float, *groups, 
                 particles_group: Optional[pygame.sprite.Group] = None,
                 game_ref = None) -> None:
        super().__init__(6, x, y, *groups, particles_group=particles_group)
        
    def apply_effect(self, player) -> None:
        """Apply the scatter bomb effect to the player."""
        super().apply_effect(player)  # Call base implementation for power
        
        # Store original shoot method if not already stored
        if not hasattr(player, 'original_shoot'):
            player.original_shoot = player.shoot
        
        # Add scatter bomb ability
        player.has_scatter_bomb = True
        
        # Add charges of scatter bombs (3 uses)
        player.scatter_bomb_charges = 3
        
        # Create collection effect
        self._create_collection_effect(player.rect.center)
        
        logger.info(f"Scatter Bomb activated with {player.scatter_bomb_charges} charges")
        
        # Note: The actual scatter bombing would be handled in the player's update
        # or a new method triggered by a key press


class TimeWarpPowerup(Powerup):
    """Time warp powerup - slows down enemies and enemy bullets."""
    
    def __init__(self, x: float, y: float, *groups, 
                 particles_group: Optional[pygame.sprite.Group] = None,
                 game_ref = None) -> None:
        super().__init__(7, x, y, *groups, particles_group=particles_group)
        
    def apply_effect(self, player) -> None:
        """Apply the time warp effect."""
        super().apply_effect(player)  # Call base implementation for power
        
        # We'll need access to game objects, so store game reference
        # This should be passed when applying the powerup
        player.game_ref = getattr(player, 'game_ref', None)
        
        # Set time warp active
        player.has_time_warp = True
        
        # Set expiry time
        player.time_warp_expiry = pygame.time.get_ticks() + POWERUP_DURATION
        
        # Create collection effect
        self._create_collection_effect(player.rect.center)
        
        logger.info("Time Warp activated for 10 seconds")
        # Note: The actual time warping would be implemented in the 
        # game's update method, slowing down enemies and bullets


class MegaBlastPowerup(Powerup):
    """Mega blast powerup - screen-clearing explosion."""
    
    def __init__(self, x: float, y: float, *groups, 
                 particles_group: Optional[pygame.sprite.Group] = None,
                 game_ref = None) -> None:
        super().__init__(8, x, y, *groups, particles_group=particles_group)
        
    def apply_effect(self, player) -> None:
        """Apply the mega blast effect - immediately destroy all enemies."""
        super().apply_effect(player)  # Call base implementation for power
        
        # We'll need access to game objects, so store game reference
        game_ref = getattr(player, 'game_ref', None)
        
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
                Explosion(enemy.rect.center, explosion_size, "enemy", 
                         game_ref.explosions, particles_group=game_ref.particles)
                
                # Remove the enemy
                enemy.kill()
            
            # Create mega blast effect around the player
            self._create_collection_effect(player.rect.center)
            
            # Play sound
            if hasattr(game_ref, 'sound_manager'):
                game_ref.sound_manager.play("explosion1", "player")
            
            logger.info(f"Mega Blast destroyed {enemy_count} enemies!")
        else:
            logger.warning("Mega Blast couldn't access game reference")


# Factory function to create a powerup of a specific type
def create_powerup(powerup_type: int, x: float, y: float, *groups, 
                  particles_group: Optional[pygame.sprite.Group] = None,
                  game_ref = None) -> Powerup:
    """Create a powerup of the specified type.
    
    Args:
        powerup_type: Index of the powerup type (0-8)
        x: Initial x position
        y: Initial y position
        groups: Sprite groups to add to
        particles_group: Optional group for particle effects
        game_ref: Reference to the game instance
        
    Returns:
        A new powerup instance of the appropriate type
    """
    powerup_classes = [
        TripleShotPowerup,
        RapidFirePowerup,
        ShieldPowerup,
        HomingMissilesPowerup,
        PulseBeamPowerup,
        PowerRestorePowerup,
        ScatterBombPowerup,
        TimeWarpPowerup,
        MegaBlastPowerup
    ]
    
    if powerup_type < 0 or powerup_type >= len(powerup_classes):
        logger.error(f"Invalid powerup type: {powerup_type}")
        # Default to Triple Shot as a fallback
        powerup_type = 0
        
    # Create the powerup instance with the game reference
    return powerup_classes[powerup_type](
        x, y, *groups, 
        particles_group=particles_group,
        game_ref=game_ref
    ) 