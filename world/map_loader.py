"""
world/map_loader.py — Map data loading and world initialisation.

Supports a simple JSON map format and a thin Tiled (.tmx) adapter.
For projects without pytmx installed, TMX loading is silently skipped and
the JSON path is used instead.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import pygame

import settings
from world.tilemap import TileMap


@dataclass
class MapData:
    """Holds everything needed to construct a world TileMap."""
    name:         str
    world_width:  int
    world_height: int
    bg_image:     str | None
    bg_colour:    tuple = (40, 80, 40)
    collision_rects: list[pygame.Rect] = field(default_factory=list)
    spawn_x:      float = 375.0
    spawn_y:      float = 300.0
    # Named exit triggers: {name: pygame.Rect}
    exits:        dict[str, pygame.Rect] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# JSON map loader (default format)
# ---------------------------------------------------------------------------
_DEFAULT_MAP: dict = {
    "name":         "Pallet Town Outskirts",
    "world_width":  1600,
    "world_height": 1400,
    "bg_image":     "maps/grassy.jpg",
    "bg_colour":    [40, 80, 40],
    "spawn_x":      750.0,
    "spawn_y":      650.0,
    "collision_rects": [],
    "exits": {}
}


def load_map_json(path: str) -> MapData:
    """Load a map from a JSON file.  Falls back to default if missing."""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    else:
        raw = _DEFAULT_MAP

    collision = [pygame.Rect(*r) for r in raw.get("collision_rects", [])]
    exits = {k: pygame.Rect(*v) for k, v in raw.get("exits", {}).items()}

    return MapData(
        name          = raw.get("name", "Unknown"),
        world_width   = raw.get("world_width",  settings.SCREEN_WIDTH  * 2),
        world_height  = raw.get("world_height", settings.SCREEN_HEIGHT * 2),
        bg_image      = raw.get("bg_image"),
        bg_colour     = tuple(raw.get("bg_colour", [40, 80, 40])),
        collision_rects = collision,
        spawn_x       = raw.get("spawn_x", 375.0),
        spawn_y       = raw.get("spawn_y", 300.0),
        exits         = exits,
    )


# ---------------------------------------------------------------------------
# Thin Tiled (.tmx) adapter — optional
# ---------------------------------------------------------------------------
def load_map_tmx(path: str) -> MapData | None:
    """
    Try to load a Tiled .tmx file using pytmx.
    Returns None if pytmx is not available or the file is missing.
    """
    try:
        import pytmx  # type: ignore
    except ImportError:
        return None

    if not os.path.isfile(path):
        return None

    tmx = pytmx.load_pygame(path)
    w   = tmx.width  * tmx.tilewidth
    h   = tmx.height * tmx.tileheight

    collision_rects: list[pygame.Rect] = []
    for obj in tmx.objects:
        if getattr(obj, "name", "").lower() == "collision":
            collision_rects.append(pygame.Rect(obj.x, obj.y, obj.width, obj.height))

    return MapData(
        name          = os.path.splitext(os.path.basename(path))[0],
        world_width   = w,
        world_height  = h,
        bg_image      = None,   # TMX tiles rendered separately
        collision_rects = collision_rects,
    )


# ---------------------------------------------------------------------------
# High-level helper
# ---------------------------------------------------------------------------
def build_tilemap(map_data: MapData) -> TileMap:
    return TileMap(
        world_width   = map_data.world_width,
        world_height  = map_data.world_height,
        bg_image_path = map_data.bg_image,
        bg_colour     = map_data.bg_colour,
    )
