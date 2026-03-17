"""
entities/pokemon.py — Pokémon data and instance classes.

PokemonData     — immutable species data loaded from data/pokemon.json.
PokemonInstance — mutable in-battle/overworld Pokémon with current stats.
PokemonRegistry — loads and indexes all species from JSON.
"""

from __future__ import annotations

import json
import math
import os
import random
from dataclasses import dataclass, field
from typing import Any

from battle.move import MoveInstance, MoveRegistry


# ---------------------------------------------------------------------------
# Species data (immutable)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PokemonData:
    id:           int
    name:         str
    types:        tuple[str, ...]
    base_stats:   dict[str, int]   # hp, attack, defense, sp_attack, sp_defense, speed
    base_exp:     int
    catch_rate:   int              # 0-255; higher = easier to catch
    evolves_to:   int | None       # pokédex id of next form, or None
    evolve_level: int | None
    sprite_index: int              # column offset in the sprite sheet
    default_moves: tuple[str, ...]


# ---------------------------------------------------------------------------
# Instance (mutable, one per Pokémon in a team/battle)
# ---------------------------------------------------------------------------
@dataclass
class PokemonInstance:
    data:       PokemonData
    level:      int
    moves:      list[MoveInstance] = field(default_factory=list)

    # Current stats (calculated at construction / on level-up)
    max_hp:     int = field(init=False)
    current_hp: int = field(init=False)
    attack:     int = field(init=False)
    defense:    int = field(init=False)
    sp_attack:  int = field(init=False)
    sp_defense: int = field(init=False)
    speed:      int = field(init=False)

    # Battle state
    exp:        int = 0
    status:     str | None = None      # "burn","poison","paralysis","sleep","freeze"
    sleep_counter: int = 0
    confused:   bool = False
    leech_seeded: bool = False
    fainted:    bool = False

    # Stat stages (−6 to +6)
    atk_stage:  int = 0
    def_stage:  int = 0
    spa_stage:  int = 0
    spd_stage:  int = 0
    spe_stage:  int = 0
    acc_stage:  int = 0
    eva_stage:  int = 0

    def __post_init__(self):
        self._calculate_stats()
        self.current_hp = self.max_hp
        # Apply EXP for current level
        self.exp = exp_for_level(self.level)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def name(self) -> str:
        return self.data.name

    @property
    def types(self) -> list[str]:
        return list(self.data.types)

    @property
    def hp_fraction(self) -> float:
        return self.current_hp / self.max_hp if self.max_hp > 0 else 0.0

    @property
    def exp_to_next_level(self) -> int:
        return exp_for_level(self.level + 1) - self.exp

    @property
    def exp_in_current_level(self) -> int:
        return self.exp - exp_for_level(self.level)

    @property
    def exp_span(self) -> int:
        return exp_for_level(self.level + 1) - exp_for_level(self.level)

    @property
    def exp_fraction(self) -> float:
        span = self.exp_span
        return self.exp_in_current_level / span if span > 0 else 0.0

    # ------------------------------------------------------------------
    # Stat calculation  (Simplified Gen-III formula without EVs/IVs)
    # ------------------------------------------------------------------
    def _calculate_stats(self):
        bs = self.data.base_stats
        lv = self.level
        self.max_hp    = math.floor(((2 * bs["hp"]       ) * lv) / 100) + lv + 10
        self.attack    = math.floor(((2 * bs["attack"]   ) * lv) / 100) + 5
        self.defense   = math.floor(((2 * bs["defense"]  ) * lv) / 100) + 5
        self.sp_attack = math.floor(((2 * bs["sp_attack"]) * lv) / 100) + 5
        self.sp_defense= math.floor(((2 * bs["sp_defense"]) * lv) / 100) + 5
        self.speed     = math.floor(((2 * bs["speed"]    ) * lv) / 100) + 5

    # ------------------------------------------------------------------
    # Battle helpers
    # ------------------------------------------------------------------
    def take_damage(self, amount: int) -> None:
        self.current_hp = max(0, self.current_hp - amount)
        if self.current_hp == 0:
            self.fainted = True

    def heal(self, amount: int) -> int:
        before = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp - before

    def gain_exp(self, amount: int) -> list[str]:
        """Add EXP and handle level-ups.  Returns list of message strings."""
        messages: list[str] = []
        self.exp += amount
        messages.append(f"{self.name} gained {amount} EXP!")
        while self.exp >= exp_for_level(self.level + 1):
            self.level += 1
            hp_before = self.max_hp
            self._calculate_stats()
            hp_gained = self.max_hp - hp_before
            self.current_hp = min(self.max_hp, self.current_hp + hp_gained)
            messages.append(f"{self.name} grew to level {self.level}!")
            # Check evolution
            if (self.data.evolves_to and self.data.evolve_level
                    and self.level >= self.data.evolve_level):
                messages.append(f"What? {self.name} is evolving!")
        return messages

    def reset_battle_state(self) -> None:
        """Clear temporary battle modifications."""
        self.status = None
        self.confused = False
        self.leech_seeded = False
        self.fainted = self.current_hp == 0
        self.atk_stage = self.def_stage = self.spa_stage = 0
        self.spd_stage = self.spe_stage = self.acc_stage = self.eva_stage = 0

    def apply_end_of_turn(self) -> list[str]:
        """Burn/poison/leech-seed tick.  Returns messages."""
        messages: list[str] = []
        if self.fainted:
            return messages
        if self.status == "burn":
            dmg = max(1, self.max_hp // 8)
            self.take_damage(dmg)
            messages.append(f"{self.name} is hurt by its burn!")
        elif self.status == "poison":
            dmg = max(1, self.max_hp // 8)
            self.take_damage(dmg)
            messages.append(f"{self.name} is hurt by poison!")
        if self.leech_seeded:
            dmg = max(1, self.max_hp // 8)
            self.take_damage(dmg)
            messages.append(f"{self.name} had its energy drained!")
        return messages

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "id":         self.data.id,
            "level":      self.level,
            "exp":        self.exp,
            "current_hp": self.current_hp,
            "status":     self.status,
            "moves":      [{"name": m.name, "pp": m.current_pp} for m in self.moves],
        }

    @classmethod
    def from_dict(cls, d: dict, registry: "PokemonRegistry") -> "PokemonInstance":
        data = registry.get_by_id(d["id"])
        move_reg = MoveRegistry.instance()
        inst = cls(data=data, level=d["level"])
        inst.exp = d.get("exp", exp_for_level(inst.level))
        inst.current_hp = d.get("current_hp", inst.max_hp)
        inst.status = d.get("status")
        inst.fainted = inst.current_hp == 0
        # Restore moves
        saved_moves = d.get("moves", [])
        if saved_moves:
            inst.moves = []
            for sm in saved_moves:
                mi = move_reg.make_instance(sm["name"])
                if mi:
                    mi.current_pp = sm.get("pp", mi.move.pp)
                    inst.moves.append(mi)
        return inst


# ---------------------------------------------------------------------------
# EXP curve (Medium Fast / cubic)
# ---------------------------------------------------------------------------
def exp_for_level(level: int) -> int:
    return level ** 3


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class PokemonRegistry:
    _instance: PokemonRegistry | None = None

    def __init__(self):
        self._by_id:   dict[int, PokemonData] = {}
        self._by_name: dict[str, PokemonData] = {}
        self._load()

    @classmethod
    def instance(cls) -> "PokemonRegistry":
        if cls._instance is None:
            cls._instance = PokemonRegistry()
        return cls._instance

    def _load(self) -> None:
        path = os.path.join("data", "pokemon.json")
        move_reg = MoveRegistry.instance()
        with open(path, encoding="utf-8") as f:
            raw: list[dict[str, Any]] = json.load(f)
        for entry in raw:
            d = PokemonData(
                id           = entry["id"],
                name         = entry["name"],
                types        = tuple(entry["types"]),
                base_stats   = entry["base_stats"],
                base_exp     = entry.get("base_exp", 50),
                catch_rate   = entry.get("catch_rate", 45),
                evolves_to   = entry.get("evolves_to"),
                evolve_level = entry.get("evolve_level"),
                sprite_index = entry.get("sprite_index", 0),
                default_moves= tuple(entry.get("moves", [])),
            )
            self._by_id[d.id] = d
            self._by_name[d.name.lower()] = d

    def get_by_id(self, pid: int) -> PokemonData | None:
        return self._by_id.get(pid)

    def get_by_name(self, name: str) -> PokemonData | None:
        return self._by_name.get(name.lower())

    def all_pokemon(self) -> list[PokemonData]:
        return list(self._by_id.values())

    def make_instance(self, pokemon_id: int, level: int,
                      move_names: list[str] | None = None) -> PokemonInstance:
        """Create a PokemonInstance with moves."""
        data = self.get_by_id(pokemon_id)
        if data is None:
            raise ValueError(f"Unknown Pokémon id: {pokemon_id}")
        inst = PokemonInstance(data=data, level=level)
        move_reg = MoveRegistry.instance()
        names = move_names if move_names is not None else list(data.default_moves)
        for name in names[:4]:
            mi = move_reg.make_instance(name)
            if mi:
                inst.moves.append(mi)
        return inst

    def make_wild(self, pokemon_id: int, level: int) -> PokemonInstance:
        return self.make_instance(pokemon_id, level)
