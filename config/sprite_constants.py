from enum import IntEnum, auto

class PowerupType(IntEnum):
    """Maps powerup names to their sprite index in powerups.png (0-based)."""
    TRIPLE_SHOT = 0
    RAPID_FIRE = 1
    SHIELD = 2
    HOMING_MISSILES = 3
    POWER_RESTORE = 4 # Index shift: was 5
    SCATTER_BOMB = 5  # Index shift: was 6
    TIME_WARP = 6     # Index shift: was 7
    MEGA_BLAST = 7    # Index shift: was 8

# Create a list of active powerup types for easy iteration/random selection
ACTIVE_POWERUP_TYPES = list(PowerupType)

# Example for other potential mappings (if needed later)
# class EnemySpriteIndex(IntEnum):
#     ENEMY_TYPE_1 = 0
#     ENEMY_SHOOTER = 1
#     # ... etc 