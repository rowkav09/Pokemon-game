"""
world/collision.py — Axis-aligned collision detection helpers.
"""

from __future__ import annotations

import pygame


def check_rect_collisions(mover: pygame.Rect,
                          obstacles: list[pygame.Rect]) -> list[pygame.Rect]:
    """Return all rects in *obstacles* that overlap *mover*."""
    return [r for r in obstacles if mover.colliderect(r)]


def resolve_rect_collision(mover: pygame.Rect, obstacle: pygame.Rect,
                            dx: float, dy: float) -> pygame.Rect:
    """
    Push *mover* out of *obstacle* along the axis of least penetration.
    Returns the corrected rect.
    """
    r = mover.copy()

    # Overlap depths
    left_depth  = obstacle.right  - r.left
    right_depth = r.right  - obstacle.left
    top_depth   = obstacle.bottom - r.top
    bot_depth   = r.bottom  - obstacle.top

    # Choose smallest penetration
    min_x = left_depth if left_depth < right_depth else -right_depth
    min_y = top_depth  if top_depth  < bot_depth   else -bot_depth

    if abs(min_x) < abs(min_y):
        r.x += min_x
    else:
        r.y += min_y

    return r


def npc_player_interaction(player_rect: pygame.Rect,
                            interaction_rect: pygame.Rect,
                            npcs) -> object | None:
    """
    Return the first NPC whose rect intersects *interaction_rect*, or None.
    *npcs* is any iterable of objects with a `.rect` property.
    """
    for npc in npcs:
        if interaction_rect.colliderect(npc.rect):
            return npc
    return None


def pokemon_encounter_check(player_rect: pygame.Rect,
                             pokemon_list: list[dict],
                             radius: int = 60) -> dict | None:
    """
    Return the first wild Pokémon dict whose position is within *radius*
    pixels of the player centre, or None.
    """
    cx, cy = player_rect.centerx, player_rect.centery
    for p in pokemon_list:
        px, py = p.get("x", 0), p.get("y", 0)
        dist_sq = (cx - px) ** 2 + (cy - py) ** 2
        if dist_sq <= radius ** 2:
            return p
    return None
