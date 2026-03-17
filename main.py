"""
main.py — Entry point for Pokémon Adventure.

Run with:
    python main.py
"""

import pygame
from game.game import Game


def main() -> None:
    """Initialise Pygame and hand off to the Game loop."""
    pygame.init()
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
