"""Main entry point for the Starblitz Assault game."""

import sys

from src.game_loop import Game
from src.logger import get_logger

# Get logger for this module
logger = get_logger(__name__)


def main():
    """Initializes and runs the game."""
    try:
        logger.info("Starting Starblitz Assault")
        game = Game()
        game.run()
    except (Exception, SystemExit) as e:
        # Log the exception
        logger.error("An error occurred: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
