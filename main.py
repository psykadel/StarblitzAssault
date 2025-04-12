"""Main entry point for the Starblitz Assault game."""

import sys
import argparse

from src.game_loop import Game
from src.intro import run_intro
from src.logger import get_logger

# Get logger for this module
logger = get_logger(__name__)


def main():
    """Initializes and runs the game."""
    try:
        # Parse command line args
        parser = argparse.ArgumentParser(description="Starblitz Assault")
        parser.add_argument("--skip-intro", action="store_true", help="Skip the intro sequence")
        parser.add_argument("--test-mode", action="store_true", help="Enable test mode")
        args = parser.parse_args()
        
        logger.info("Starting Starblitz Assault")
        
        # Create the game instance
        game = Game()
        
        # Run intro sequence if not skipped
        if not args.skip_intro:
            logger.info("Running intro sequence")
            # Pass the game's sound manager to the intro for smoother music transitions
            intro_result = run_intro(game.screen, game.sound_manager)
            
            # Quit if user closed the game during intro
            if not intro_result:
                logger.info("User quit during intro sequence")
                return
                
        # Run the game
        game.run()
        
    except (Exception, SystemExit) as e:
        # Log the exception
        logger.error("An error occurred: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
