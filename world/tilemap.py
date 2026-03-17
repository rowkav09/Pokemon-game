"""
world/tilemap.py — Tile-based map rendering with a smooth camera.

TileMap wraps a background surface (tiled or solid), exposes a camera that
follows the player, and provides helpers for converting between world and
screen space.
"""

from __future__ import annotations

import os

import pygame

import settings
from game.asset_loader import loader


class Camera:
    """Smooth camera that follows a target rect."""

    def __init__(self, screen_width: int, screen_height: int,
                 world_width: int, world_height: int):
        self.screen_w   = screen_width
        self.screen_h   = screen_height
        self.world_w    = world_width
        self.world_h    = world_height
        self._offset_x  = 0.0
        self._offset_y  = 0.0

    @property
    def offset(self) -> tuple[float, float]:
        return self._offset_x, self._offset_y

    def update(self, target_rect: pygame.Rect) -> None:
        """Smoothly move camera to centre on *target_rect*."""
        target_x = target_rect.centerx - self.screen_w / 2
        target_y = target_rect.centery - self.screen_h / 2

        # Clamp to world bounds
        target_x = max(0, min(self.world_w  - self.screen_w,  target_x))
        target_y = max(0, min(self.world_h  - self.screen_h, target_y))

        # Lerp for smooth follow
        lerp = settings.CAMERA_LERP
        self._offset_x += (target_x - self._offset_x) * lerp
        self._offset_y += (target_y - self._offset_y) * lerp

    def world_to_screen(self, x: float, y: float) -> tuple[int, int]:
        return (round(x - self._offset_x), round(y - self._offset_y))

    def screen_to_world(self, sx: int, sy: int) -> tuple[float, float]:
        return (sx + self._offset_x, sy + self._offset_y)


class TileMap:
    """
    Renders a tiled background and holds world dimensions.

    If a background image path is provided, the image is tiled to fill
    *world_width* × *world_height*.  Otherwise a solid colour is used.
    """

    def __init__(
        self,
        world_width:  int = settings.SCREEN_WIDTH  * 2,
        world_height: int = settings.SCREEN_HEIGHT * 2,
        bg_image_path: str | None = None,
        bg_colour: tuple = (40, 80, 40),
    ):
        self.world_width  = world_width
        self.world_height = world_height
        self.bg_colour    = bg_colour

        # Build a static pre-rendered surface for the world background
        self._bg_surface = pygame.Surface((world_width, world_height))
        self._bg_surface.fill(bg_colour)

        if bg_image_path and os.path.isfile(bg_image_path):
            tile = loader.scaled_image(
                bg_image_path,
                (world_width // 2, world_height // 2),
                convert_alpha=False,
            )
            tw, th = tile.get_size()
            for row in range(0, world_height, th):
                for col in range(0, world_width, tw):
                    self._bg_surface.blit(tile, (col, row))

        self.camera = Camera(
            screen_width  = settings.SCREEN_WIDTH,
            screen_height = settings.SCREEN_HEIGHT,
            world_width   = world_width,
            world_height  = world_height,
        )

    @property
    def world_rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, self.world_width, self.world_height)

    def update(self, player_rect: pygame.Rect) -> None:
        self.camera.update(player_rect)

    def draw(self, surface: pygame.Surface) -> None:
        ox, oy = self.camera.offset
        # Only blit the visible portion of the world
        visible = pygame.Rect(int(ox), int(oy),
                              settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT)
        surface.blit(self._bg_surface, (0, 0), visible)
