"""Main entry point for the Starblitz Assault game."""

import sys
import os

# Ensure the src directory is in the Python path
# This allows for absolute imports like 'from src.game_loop import Game'
# based on the project structure rule in python.mdc
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.game_loop import Game

def main():
    """Initializes and runs the game."""
    try:
        game = Game()
        game.run()
    except Exception as e:
        # Log the exception
        print(f"An error occurred: {e}") # Replace with proper logging
        # Optionally, save error details to a log file in .logs/
        sys.exit(1)

if __name__ == "__main__":
    main()
