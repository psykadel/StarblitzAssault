"""Main entry point for the Starblitz Assault game."""

import sys
import os
import pygame

# Ensure the src directory is in the Python path
# This allows for absolute imports like 'from src.game_loop import Game'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Import logger first to ensure it's set up
from src.logger import get_logger
logger = get_logger(__name__)

from src.game_loop import Game

def main():
    """Initializes and runs the game."""
    try:
        logger.info("Starting Starblitz Assault")
        game = Game()
        game.run()
    except (pygame.error, SystemExit) as e:
        # Log the exception
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
