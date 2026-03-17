"""
battle/move.py — Move data class.

Moves are loaded from data/moves.json via MoveRegistry.
A MoveInstance wraps a Move and tracks remaining PP.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Move:
    """Immutable move definition loaded from JSON."""
    name:     str
    type:     str
    power:    int          # 0 for status moves
    accuracy: int          # 0–100; 0 = always hits
    pp:       int
    category: str          # "physical" | "special" | "status"
    effect:   dict | None  # optional secondary-effect descriptor

    def display_name(self) -> str:
        return self.name.replace("_", " ").title()

    def __str__(self) -> str:
        return self.display_name()


@dataclass
class MoveInstance:
    """A move in a Pokémon's moveset — tracks current PP."""
    move:    Move
    current_pp: int = field(init=False)

    def __post_init__(self):
        self.current_pp = self.move.pp

    def use(self) -> bool:
        """Decrement PP and return True if the move could be used."""
        if self.current_pp <= 0:
            return False
        self.current_pp -= 1
        return True

    def restore_pp(self, amount: int | None = None) -> None:
        """Restore PP (fully if amount is None)."""
        self.current_pp = self.move.pp if amount is None else min(
            self.move.pp, self.current_pp + amount)

    @property
    def name(self) -> str:
        return self.move.name

    def display_name(self) -> str:
        return self.move.display_name()

    def __str__(self) -> str:
        return f"{self.display_name()} {self.current_pp}/{self.move.pp}"


class MoveRegistry:
    """Loads and indexes all moves from data/moves.json."""
    _instance: MoveRegistry | None = None

    def __init__(self):
        self._moves: dict[str, Move] = {}
        self._load()

    @classmethod
    def instance(cls) -> MoveRegistry:
        if cls._instance is None:
            cls._instance = MoveRegistry()
        return cls._instance

    def _load(self) -> None:
        path = os.path.join("data", "moves.json")
        with open(path, encoding="utf-8") as f:
            raw: list[dict[str, Any]] = json.load(f)
        for entry in raw:
            m = Move(
                name     = entry["name"],
                type     = entry["type"],
                power    = entry.get("power", 0),
                accuracy = entry.get("accuracy", 100),
                pp       = entry.get("pp", 10),
                category = entry.get("category", "physical"),
                effect   = entry.get("effect"),
            )
            self._moves[m.name] = m

    def get(self, name: str) -> Move | None:
        return self._moves.get(name)

    def all_moves(self) -> list[Move]:
        return list(self._moves.values())

    def make_instance(self, name: str) -> MoveInstance | None:
        m = self.get(name)
        if m is None:
            return None
        return MoveInstance(m)
