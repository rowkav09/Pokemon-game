"""
entities/player.py — Player character with movement, animations, team and inventory.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import pygame

import settings
from game.asset_loader import loader

if TYPE_CHECKING:
    from entities.pokemon import PokemonInstance


# ---------------------------------------------------------------------------
# Direction constants
# ---------------------------------------------------------------------------
DIRECTION_ROWS = {0: "down", 1: "left", 2: "right", 3: "up"}
DIRS = ("down", "left", "right", "up")


class Player:
    """
    Handles player input, movement, animation and game-state inventory.

    Attributes
    ----------
    x, y        : float  — world-space pixel position (top-left of sprite)
    facing      : str    — current direction ("up"|"down"|"left"|"right")
    team        : list[PokemonInstance]
    inventory   : dict[str, int]  — item_id -> quantity
    pokedex     : set[int]        — pokédex ids caught
    money       : int
    """

    def __init__(self, x: float = 375.0, y: float = 300.0):
        self.x: float = x
        self.y: float = y
        self.facing: str = "down"
        self._frame_index: float = 0.0
        self._moving: bool = False

        # Game state
        self.team: list[PokemonInstance] = []
        self.inventory: dict[str, int] = {
            "pokeball":  5,
            "potion":    3,
            "revive":    1,
            "antidote":  2,
            "awakening": 1,
        }
        self.pokedex: set[int] = set()
        self.money: int = 3000
        self.name: str = "RED"
        self.badges: int = 0

        # Sprite
        self._animations: dict[str, list[pygame.Surface]] = {}
        self._load_sprites()

    # ------------------------------------------------------------------
    # Sprite loading
    # ------------------------------------------------------------------
    def _load_sprites(self) -> None:
        path = os.path.join(settings.IMAGES_DIR, "trainer_sheet.png")
        if not os.path.isfile(path):
            self._animations = {d: [_placeholder_surface()] for d in DIRS}
            return

        self._animations = {d: [] for d in DIRS}
        for row_idx, direction in DIRECTION_ROWS.items():
            for col in range(4):
                rect = pygame.Rect(
                    settings.PLAYER_FRAME_OFFSET_X + col * settings.PLAYER_FRAME_WIDTH,
                    settings.PLAYER_FRAME_OFFSET_Y + row_idx * settings.PLAYER_FRAME_HEIGHT,
                    settings.PLAYER_FRAME_WIDTH,
                    settings.PLAYER_FRAME_HEIGHT,
                )
                frame = loader.sub_image(
                    path, rect,
                    scale=(settings.PLAYER_WIDTH, settings.PLAYER_HEIGHT),
                )
                self._animations[direction].append(frame)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt: float, keys: pygame.key.ScancodeWrapper,
               world_rect: pygame.Rect) -> None:
        """Move player based on held keys; dt is seconds elapsed."""
        dx = dy = 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]:  dx = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:  dx =  1
        if keys[pygame.K_UP]    or keys[pygame.K_w]:  dy = -1
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]:  dy =  1

        # Diagonal normalisation
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        spd = settings.PLAYER_SPEED * dt
        new_x = self.x + dx * spd
        new_y = self.y + dy * spd

        # Clamp to world bounds
        new_x = max(world_rect.left, min(world_rect.right  - settings.PLAYER_WIDTH,  new_x))
        new_y = max(world_rect.top,  min(world_rect.bottom - settings.PLAYER_HEIGHT, new_y))

        self._moving = dx != 0 or dy != 0

        if dx < 0:  self.facing = "left"
        elif dx > 0: self.facing = "right"
        elif dy < 0: self.facing = "up"
        elif dy > 0: self.facing = "down"

        self.x = new_x
        self.y = new_y

        # Animation
        if self._moving:
            self._frame_index = (self._frame_index + settings.PLAYER_ANIM_SPEED * dt) % 4
        else:
            self._frame_index = 0.0

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera_offset: tuple[float, float]) -> None:
        frames = self._animations.get(self.facing, [])
        if not frames:
            return
        frame = frames[int(self._frame_index)]
        surface.blit(frame, (round(self.x - camera_offset[0]),
                              round(self.y - camera_offset[1])))

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------
    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y),
                           settings.PLAYER_WIDTH, settings.PLAYER_HEIGHT)

    @property
    def interaction_rect(self) -> pygame.Rect:
        """Small rect in front of the player for interaction checks."""
        r = self.rect.inflate(-40, -40)
        offsets = {
            "up":    (0,  -settings.PLAYER_HEIGHT // 2),
            "down":  (0,   settings.PLAYER_HEIGHT // 2),
            "left":  (-settings.PLAYER_WIDTH // 2, 0),
            "right": ( settings.PLAYER_WIDTH // 2, 0),
        }
        dx, dy = offsets.get(self.facing, (0, 0))
        r.x += dx
        r.y += dy
        return r

    @property
    def first_alive_pokemon(self) -> PokemonInstance | None:
        for p in self.team:
            if not p.fainted:
                return p
        return None

    @property
    def has_usable_pokemon(self) -> bool:
        return self.first_alive_pokemon is not None

    # ------------------------------------------------------------------
    # Inventory helpers
    # ------------------------------------------------------------------
    def item_count(self, item_id: str) -> int:
        return self.inventory.get(item_id, 0)

    def use_item(self, item_id: str) -> bool:
        count = self.inventory.get(item_id, 0)
        if count <= 0:
            return False
        self.inventory[item_id] = count - 1
        return True

    def add_item(self, item_id: str, qty: int = 1) -> None:
        self.inventory[item_id] = self.inventory.get(item_id, 0) + qty

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "x":         self.x,
            "y":         self.y,
            "facing":    self.facing,
            "name":      self.name,
            "money":     self.money,
            "badges":    self.badges,
            "inventory": self.inventory,
            "pokedex":   list(self.pokedex),
            "team":      [p.to_dict() for p in self.team],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Player":
        from entities.pokemon import PokemonRegistry
        p = cls(x=d.get("x", 375.0), y=d.get("y", 300.0))
        p.facing    = d.get("facing", "down")
        p.name      = d.get("name", "RED")
        p.money     = d.get("money", 3000)
        p.badges    = d.get("badges", 0)
        p.inventory = d.get("inventory", p.inventory)
        p.pokedex   = set(d.get("pokedex", []))
        registry = PokemonRegistry.instance()
        p.team = [
            __import__("entities.pokemon", fromlist=["PokemonInstance"]).PokemonInstance.from_dict(td, registry)
            for td in d.get("team", [])
        ]
        return p


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _placeholder_surface() -> pygame.Surface:
    surf = pygame.Surface((settings.PLAYER_WIDTH, settings.PLAYER_HEIGHT), pygame.SRCALPHA)
    surf.fill((200, 100, 100))
    return surf
