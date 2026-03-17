"""
entities/npc.py — NPC base class, dialogue NPCs and Trainer NPCs.

NPC         — static character that shows dialogue when interacted with.
TrainerNPC  — NPC that triggers a battle when the player approaches or presses interact.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import pygame

import settings
from game.asset_loader import loader

if TYPE_CHECKING:
    from entities.pokemon import PokemonInstance, PokemonRegistry


# ---------------------------------------------------------------------------
# NPC base
# ---------------------------------------------------------------------------
class NPC:
    """Non-player character with position, direction and dialogue."""

    WIDTH  = 60
    HEIGHT = 80

    def __init__(self, npc_id: str, name: str, x: float, y: float,
                 direction: str = "down", dialogue: list[str] | None = None,
                 colour: tuple = (100, 150, 250)):
        self.id        = npc_id
        self.name      = name
        self.x         = x
        self.y         = y
        self.direction = direction
        self.dialogue  = dialogue or ["..."]
        self._colour   = colour
        self.interacted = False    # flag for one-shot dialogue

    # ------------------------------------------------------------------
    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.WIDTH, self.HEIGHT)

    def draw(self, surface: pygame.Surface, camera_offset: tuple[float, float]) -> None:
        r = self.rect.move(-int(camera_offset[0]), -int(camera_offset[1]))
        pygame.draw.rect(surface, self._colour, r, border_radius=6)
        # Name label
        fnt = loader.font("couriernew", 12, bold=True)
        lbl = fnt.render(self.name, True, settings.WHITE)
        surface.blit(lbl, (r.centerx - lbl.get_width() // 2, r.top - 14))

    def interact(self, player) -> list[str]:
        """Return dialogue lines when player interacts."""
        return list(self.dialogue)

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "interacted":  self.interacted,
        }


# ---------------------------------------------------------------------------
# Trainer NPC
# ---------------------------------------------------------------------------
class TrainerNPC(NPC):
    """
    An NPC that triggers a battle when faced / interacted with.

    trainer_data format (from trainers.json):
        id, name, dialogue_before, dialogue_after,
        battle_team: [{pokemon_id, level, moves}]
    """

    def __init__(self, npc_id: str, name: str, x: float, y: float,
                 direction: str, dialogue_before: list[str],
                 dialogue_after: list[str], battle_team: list[dict],
                 defeated: bool = False):
        super().__init__(npc_id, name, x, y, direction,
                         dialogue=dialogue_before, colour=(250, 100, 100))
        self.dialogue_before = list(dialogue_before)
        self.dialogue_after  = list(dialogue_after)
        self.battle_team_data = battle_team
        self.defeated         = defeated
        self._built_team: list[PokemonInstance] | None = None

    def build_team(self, registry: "PokemonRegistry") -> list["PokemonInstance"]:
        if self._built_team is not None:
            return self._built_team
        team = []
        for entry in self.battle_team_data:
            poke = registry.make_instance(
                pokemon_id  = entry["pokemon_id"],
                level       = entry["level"],
                move_names  = entry.get("moves"),
            )
            team.append(poke)
        self._built_team = team
        return team

    def interact(self, player) -> list[str]:
        if self.defeated:
            return self.dialogue_after
        return self.dialogue_before

    def draw(self, surface: pygame.Surface, camera_offset: tuple[float, float]) -> None:
        super().draw(surface, camera_offset)
        if not self.defeated:
            r = self.rect.move(-int(camera_offset[0]), -int(camera_offset[1]))
            fnt = loader.font("couriernew", 10)
            lbl = fnt.render("!", True, settings.YELLOW)
            surface.blit(lbl, (r.centerx - lbl.get_width() // 2, r.top - 28))

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["defeated"] = self.defeated
        return d


# ---------------------------------------------------------------------------
# Factory: load all NPCs from trainers.json
# ---------------------------------------------------------------------------
def load_npcs(path: str | None = None) -> list[NPC]:
    path = path or os.path.join("data", "trainers.json")
    with open(path, encoding="utf-8") as f:
        entries = json.load(f)

    npcs: list[NPC] = []
    for e in entries:
        npc_id    = e["id"]
        name      = e["name"]
        x         = float(e.get("x", 200))
        y         = float(e.get("y", 200))
        direction = e.get("direction", "down")

        if e.get("is_trainer") is False:
            # Pure dialogue NPC
            npcs.append(NPC(
                npc_id    = npc_id,
                name      = name,
                x         = x,
                y         = y,
                direction = direction,
                dialogue  = e.get("dialogue", ["..."]),
            ))
        else:
            npcs.append(TrainerNPC(
                npc_id          = npc_id,
                name            = name,
                x               = x,
                y               = y,
                direction       = direction,
                dialogue_before = e.get("dialogue_before", ["Battle me!"]),
                dialogue_after  = e.get("dialogue_after",  ["Good battle..."]),
                battle_team     = e.get("battle_team", []),
                defeated        = e.get("defeated", False),
            ))
    return npcs
