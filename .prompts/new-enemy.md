You are an experienced game systems developer. Your goal is to:

1. Read and understand the complete enemy system in this project.  Identify how enemies are defined, how behaviors and attributes are managed, and how combat interactions are implemented. Understand the structure, conventions, and logic patterns.

2. Add a new enemy to the system.
Insert a new, fully functional enemy into the game that fits naturally into the existing system but brings novelty. Do not request confirmation—perform the code changes directly and completely.

Your enemy must:

    Introduce a unique behavior or mechanic not already present

    Be integrated into spawning logic and AI behavior trees

    Follow code organization and naming conventions

    Include any necessary updates to animation, sound, or effects hooks

    Be immediately usable/testable within the existing framework

Constraints:

    Do not modify or refactor existing enemies unless necessary to support the new one

    Do not create placeholder functions—fully implement all new logic

    Be creative and make design decisions autonomously; treat this as a solo design assignment

Execution Order:

    Parse the enemy system files

    Identify integration points for new enemies

    Define and implement a new enemy class/file

    Register it in the spawning logic

    Ensure behavior is fully implemented (AI, attacks, damage, death, etc.)

    Save and validate all code changes

Begin by scanning for files or modules related to Enemy, AI, Spawner, and EnemyManager. Create a new enemy named Wraithbound Strider with unique phasing movement and terrain-ignoring pathfinding.