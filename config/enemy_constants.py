"""Enemy types and spawn frequency configuration."""

from typing import Dict, List, Tuple

# Enemy type identifiers - used to reference enemy types consistently across the codebase
ENEMY_TYPES = {
    "BASIC": 0,       # Basic enemy (EnemyType1)
    "SHOOTER": 1,     # Enemy that shoots bullets at player (EnemyShooter) 
    "WAVE": 2,        # Enemy that moves in wave pattern and fires wave projectiles (EnemyType3)
    "SPIRAL": 3,      # Enemy with erratic movement and spiral projectiles (EnemyType4)
    "SEEKER": 4,      # Enemy that tracks player and fires homing projectiles (EnemyType5)
    "TELEPORTER": 5,  # Enemy that teleports and fires bouncing projectiles (EnemyType6)
    "ORBITER": 6,     # Enemy that orbits around points and fires in patterns (EnemyType7)
    "SHIELDED": 7,    # Enemy with shield that absorbs damage (EnemyType8)
}

# Enemy type names for logging and UI display
ENEMY_TYPE_NAMES = {
    ENEMY_TYPES["BASIC"]: "Basic",
    ENEMY_TYPES["SHOOTER"]: "Shooter",
    ENEMY_TYPES["WAVE"]: "Wave",
    ENEMY_TYPES["SPIRAL"]: "Spiral", 
    ENEMY_TYPES["SEEKER"]: "Seeker",
    ENEMY_TYPES["TELEPORTER"]: "Teleporter",
    ENEMY_TYPES["ORBITER"]: "Orbiter",
    ENEMY_TYPES["SHIELDED"]: "Shielded",
}

# Base frequencies for each enemy type at difficulty level 1
# Values are percentages (should sum to 100)
BASE_ENEMY_FREQUENCIES = {
    ENEMY_TYPES["BASIC"]: 40,       # 40% chance at difficulty 1
    ENEMY_TYPES["SHOOTER"]: 30,     # 30% chance at difficulty 1
    ENEMY_TYPES["WAVE"]: 10,        # 10% chance at difficulty 1
    ENEMY_TYPES["SPIRAL"]: 10,      # 10% chance at difficulty 1
    ENEMY_TYPES["SEEKER"]: 10,      # 10% chance at difficulty 1
    ENEMY_TYPES["TELEPORTER"]: 0,   # 0% at difficulty 1 (unlocks at difficulty 2)
    ENEMY_TYPES["ORBITER"]: 0,      # 0% at difficulty 1 (unlocks at difficulty 3) 
    ENEMY_TYPES["SHIELDED"]: 0,     # 0% at difficulty 1 (unlocks at difficulty 4)
}

# Difficulty thresholds for when each enemy type starts to appear
ENEMY_UNLOCK_THRESHOLDS = {
    ENEMY_TYPES["BASIC"]: 1.0,      # Available from start
    ENEMY_TYPES["SHOOTER"]: 1.0,    # Available from start
    ENEMY_TYPES["WAVE"]: 1.0,       # Available from start
    ENEMY_TYPES["SPIRAL"]: 1.0,     # Available from start
    ENEMY_TYPES["SEEKER"]: 1.0,     # Available from start
    ENEMY_TYPES["TELEPORTER"]: 2.0, # Unlocks at difficulty 2.0
    ENEMY_TYPES["ORBITER"]: 3.0,    # Unlocks at difficulty 3.0
    ENEMY_TYPES["SHIELDED"]: 4.0,   # Unlocks at difficulty 4.0
}

# Frequency scaling per difficulty level
# Defines how frequencies change with difficulty level
# Positive values mean the frequency increases with difficulty
# Negative values mean the frequency decreases with difficulty
FREQUENCY_SCALING = {
    ENEMY_TYPES["BASIC"]: -3.5,      # Decreases by 3.5% per difficulty level
    ENEMY_TYPES["SHOOTER"]: 1.5,     # Increases by 1.5% per difficulty level
    ENEMY_TYPES["WAVE"]: 1.0,        # Increases by 1.0% per difficulty level
    ENEMY_TYPES["SPIRAL"]: 1.0,      # Increases by 1.0% per difficulty level
    ENEMY_TYPES["SEEKER"]: 1.5,      # Increases by 1.5% per difficulty level
    ENEMY_TYPES["TELEPORTER"]: 2.0,  # Increases by 2.0% per difficulty level once unlocked
    ENEMY_TYPES["ORBITER"]: 2.2,     # Increases by 2.2% per difficulty level once unlocked
    ENEMY_TYPES["SHIELDED"]: 2.5,    # Increases by 2.5% per difficulty level once unlocked
}

# Maximum frequency for each enemy type (percentage)
MAX_FREQUENCIES = {
    ENEMY_TYPES["BASIC"]: 40,       # Never higher than initial value
    ENEMY_TYPES["SHOOTER"]: 45,     # Max 45%
    ENEMY_TYPES["WAVE"]: 20,        # Max 20%
    ENEMY_TYPES["SPIRAL"]: 20,      # Max 20%
    ENEMY_TYPES["SEEKER"]: 25,      # Max 25%
    ENEMY_TYPES["TELEPORTER"]: 20,  # Max 20%
    ENEMY_TYPES["ORBITER"]: 22,     # Max 22%
    ENEMY_TYPES["SHIELDED"]: 25,    # Max 25%
}

# Minimum frequency for each enemy type once unlocked (percentage)
MIN_FREQUENCIES = {
    ENEMY_TYPES["BASIC"]: 5,        # Min 5% (always some chance)
    ENEMY_TYPES["SHOOTER"]: 10,     # Min 10%
    ENEMY_TYPES["WAVE"]: 5,         # Min 5%
    ENEMY_TYPES["SPIRAL"]: 5,       # Min 5%
    ENEMY_TYPES["SEEKER"]: 5,       # Min 5%
    ENEMY_TYPES["TELEPORTER"]: 2,   # Min 2%
    ENEMY_TYPES["ORBITER"]: 2,      # Min 2%
    ENEMY_TYPES["SHIELDED"]: 1,     # Min 1%
}

# Enemy sprite sheet filenames
ENEMY_SPRITE_FILES = {
    ENEMY_TYPES["BASIC"]: "enemy1.png",
    ENEMY_TYPES["SHOOTER"]: "enemy2.png",
    ENEMY_TYPES["WAVE"]: "enemy3.png",
    ENEMY_TYPES["SPIRAL"]: "enemy4.png",
    ENEMY_TYPES["SEEKER"]: "enemy5.png",
    ENEMY_TYPES["TELEPORTER"]: "enemy6.png",
    ENEMY_TYPES["ORBITER"]: "enemy7.png",
    ENEMY_TYPES["SHIELDED"]: "enemy8.png",
}

def get_enemy_weights(difficulty_level: float) -> List[int]:
    """Calculate enemy spawn weights based on current difficulty level.
    
    Args:
        difficulty_level: Current game difficulty level
        
    Returns:
        List of weights for each enemy type (index corresponds to enemy type)
    """
    weights = [0] * 8  # Initialize weights for all 8 enemy types
    
    for enemy_type, base_freq in BASE_ENEMY_FREQUENCIES.items():
        # Skip if enemy type is not yet unlocked at this difficulty
        if difficulty_level < ENEMY_UNLOCK_THRESHOLDS.get(enemy_type, 1.0):
            weights[enemy_type] = 0
            continue
            
        # Calculate weight based on difficulty scaling
        difficulty_factor = difficulty_level - 1  # Difficulty 1 is baseline (factor = 0)
        scaled_frequency = base_freq + (FREQUENCY_SCALING[enemy_type] * difficulty_factor)
        
        # Apply min/max constraints
        scaled_frequency = max(MIN_FREQUENCIES[enemy_type], scaled_frequency)
        scaled_frequency = min(MAX_FREQUENCIES[enemy_type], scaled_frequency)
        
        weights[enemy_type] = int(scaled_frequency)  # Cast to int to fix linter error
        
    # Normalize to ensure sum is 100
    weight_sum = sum(weights)
    if weight_sum > 0:  # Avoid division by zero
        weights = [int(w * 100 / weight_sum) for w in weights]
        
    # Ensure minimum weight for all unlocked enemy types
    for enemy_type in ENEMY_TYPES.values():
        if difficulty_level >= ENEMY_UNLOCK_THRESHOLDS.get(enemy_type, 1.0) and weights[enemy_type] < MIN_FREQUENCIES[enemy_type]:
            weights[enemy_type] = MIN_FREQUENCIES[enemy_type]
    
    # Ensure weights sum to 100 (adjust highest weight if needed)
    weight_sum = sum(weights)
    if weight_sum != 100:
        # Find the enemy type with highest frequency and adjust it
        max_idx = weights.index(max(weights))
        weights[max_idx] += (100 - weight_sum)
    
    return weights 