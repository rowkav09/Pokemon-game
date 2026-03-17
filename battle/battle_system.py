"""
battle/battle_system.py — Turn-based Pokémon battle state machine.

Phases
------
INTRO          show battle start text
PLAYER_ACTION  action menu: FIGHT / BAG / POKÉMON / RUN
MOVE_SELECT    move list
BAG_SELECT     item selection (delegates back to game)
ANIMATING      executing the chosen moves (with messages)
LEVEL_UP       show level-up / evolution text
WIN            player won
LOSE           player lost (blacked out)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

import settings
from battle.damage_calculator import (
    calculate_damage, accuracy_check, apply_move_effect
)
from battle.type_chart import effectiveness_label

if TYPE_CHECKING:
    from entities.pokemon import PokemonInstance
    from entities.npc import TrainerNPC
    from battle.move import MoveInstance


# ---------------------------------------------------------------------------
# Battle phase enum
# ---------------------------------------------------------------------------
class BattlePhase(Enum):
    INTRO         = auto()
    PLAYER_ACTION = auto()
    MOVE_SELECT   = auto()
    BAG_SELECT    = auto()
    ANIMATING     = auto()
    LEVEL_UP      = auto()
    WIN           = auto()
    LOSE          = auto()


# ---------------------------------------------------------------------------
# Pending action
# ---------------------------------------------------------------------------
@dataclass
class BattleAction:
    kind:  str            # "move" | "item" | "switch" | "run"
    move:  MoveInstance | None = None
    item:  dict | None = None
    switch_to: int | None = None   # team index


# ---------------------------------------------------------------------------
# Result messages queue
# ---------------------------------------------------------------------------
@dataclass
class BattleResult:
    """Returned by BattleSystem.tick() each frame."""
    phase:    BattlePhase
    messages: list[str] = field(default_factory=list)
    # animaton hints
    flash_target: str | None = None   # "player" or "enemy"
    shake_target: str | None = None


# ---------------------------------------------------------------------------
# BattleSystem
# ---------------------------------------------------------------------------
class BattleSystem:
    """
    Pure-logic battle controller.

    Usage
    -----
    1. Construct with player_pokemon, enemy_pokemon, is_wild.
    2. Call start() to get intro messages.
    3. During PLAYER_ACTION: call submit_player_action().
    4. Call execute_turn() once both sides have a pending action.
    5. Read .phase and .pending_messages.
    """

    def __init__(
        self,
        player_team:   list["PokemonInstance"],
        enemy_pokemon: "PokemonInstance",
        is_wild:       bool = True,
        trainer:       "TrainerNPC | None" = None,
        trainer_team:  list["PokemonInstance"] | None = None,
    ):
        self.player_team    = player_team
        self.player_idx     = 0          # index into player_team
        self.enemy_pokemon  = enemy_pokemon
        self.is_wild        = is_wild
        self.trainer        = trainer
        self.trainer_team   = trainer_team or []
        self.trainer_idx    = 0

        self.phase          = BattlePhase.INTRO
        self._messages:  list[str] = []
        self._pending_player_action: BattleAction | None = None
        self._turn_count = 0

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------
    @property
    def player_pokemon(self) -> "PokemonInstance":
        return self.player_team[self.player_idx]

    @property
    def active_enemy(self) -> "PokemonInstance":
        return self.enemy_pokemon

    def _player_goes_first(self) -> bool:
        """Return True if the player's Pokémon acts before the enemy this turn."""
        ps = self.player_pokemon.speed
        es = self.enemy_pokemon.speed
        if ps != es:
            return ps > es
        # Speed tie: coin flip
        return random.random() < 0.5

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self) -> list[str]:
        """Return intro messages and advance to PLAYER_ACTION."""
        if self.is_wild:
            msgs = [f"A wild {self.enemy_pokemon.name} appeared!",
                    f"Go! {self.player_pokemon.name}!"]
        else:
            name = self.trainer.name if self.trainer else "Trainer"
            msgs = [f"{name} wants to battle!",
                    f"{name} sent out {self.enemy_pokemon.name}!",
                    f"Go! {self.player_pokemon.name}!"]
        self.phase = BattlePhase.PLAYER_ACTION
        return msgs

    def submit_player_action(self, action: BattleAction) -> None:
        """Called when the player confirms their action in the UI."""
        self._pending_player_action = action
        if action.kind == "run":
            self.phase = BattlePhase.ANIMATING
        elif action.kind == "move":
            self.phase = BattlePhase.ANIMATING
        elif action.kind == "item":
            self.phase = BattlePhase.ANIMATING
        elif action.kind == "switch":
            self.phase = BattlePhase.ANIMATING

    def execute_turn(self) -> list[BattleResult]:
        """
        Execute the full turn (player + enemy) and return ordered results.
        Each BattleResult contains messages plus animation hints.
        """
        results: list[BattleResult] = []
        action = self._pending_player_action
        self._pending_player_action = None

        if action is None:
            return results

        # ---------- RUN ----------
        if action.kind == "run":
            if self.is_wild:
                results.append(BattleResult(
                    phase=BattlePhase.WIN,
                    messages=["Got away safely!"],
                ))
                self.phase = BattlePhase.WIN
            else:
                results.append(BattleResult(
                    phase=BattlePhase.PLAYER_ACTION,
                    messages=["Can't run from a trainer battle!"],
                ))
                self.phase = BattlePhase.PLAYER_ACTION
            return results

        # ---------- ITEM ----------
        if action.kind == "item":
            item = action.item
            msg  = self._use_item(item)
            results.append(BattleResult(phase=BattlePhase.ANIMATING, messages=[msg]))
            # Enemy retaliates
            enemy_result = self._execute_enemy_move()
            results.extend(enemy_result)
            self._advance_phase_after_turn(results)
            return results

        # ---------- SWITCH ----------
        if action.kind == "switch":
            new_idx = action.switch_to
            if new_idx is not None and 0 <= new_idx < len(self.player_team):
                self.player_idx = new_idx
                msg = f"Go! {self.player_pokemon.name}!"
                results.append(BattleResult(phase=BattlePhase.ANIMATING, messages=[msg]))
            enemy_result = self._execute_enemy_move()
            results.extend(enemy_result)
            self._advance_phase_after_turn(results)
            return results

        # ---------- MOVE ----------
        player_move  = action.move
        player_first = self._player_goes_first()

        if player_first:
            results.extend(self._execute_player_move(player_move))
            if not self.enemy_pokemon.fainted:
                results.extend(self._execute_enemy_move())
        else:
            results.extend(self._execute_enemy_move())
            if not self.player_pokemon.fainted:
                results.extend(self._execute_player_move(player_move))

        # End-of-turn effects (burn/poison)
        eot_msgs: list[str] = []
        if not self.player_pokemon.fainted:
            eot_msgs.extend(self.player_pokemon.apply_end_of_turn())
        if not self.enemy_pokemon.fainted:
            eot_msgs.extend(self.enemy_pokemon.apply_end_of_turn())
        if eot_msgs:
            results.append(BattleResult(phase=BattlePhase.ANIMATING, messages=eot_msgs))

        self._advance_phase_after_turn(results)
        self._turn_count += 1
        return results

    # ------------------------------------------------------------------
    # Internal: move execution
    # ------------------------------------------------------------------
    def _execute_player_move(self, mi: "MoveInstance") -> list[BattleResult]:
        results: list[BattleResult] = []
        poke   = self.player_pokemon
        target = self.enemy_pokemon

        # Paralysis check
        if poke.status == "paralysis" and random.random() < 0.25:
            results.append(BattleResult(phase=BattlePhase.ANIMATING,
                           messages=[f"{poke.name} is paralyzed and can't move!"]))
            return results

        # Sleep check
        if poke.status == "sleep":
            poke.sleep_counter -= 1
            if poke.sleep_counter <= 0:
                poke.status = None
                results.append(BattleResult(phase=BattlePhase.ANIMATING,
                               messages=[f"{poke.name} woke up!"]))
            else:
                results.append(BattleResult(phase=BattlePhase.ANIMATING,
                               messages=[f"{poke.name} is fast asleep!"]))
            return results

        # Use PP
        mi.use()
        msgs = [f"{poke.name} used {mi.display_name()}!"]

        # Accuracy check
        if not accuracy_check(mi.move, poke.acc_stage, target.eva_stage):
            msgs.append(f"{poke.name}'s attack missed!")
            results.append(BattleResult(phase=BattlePhase.ANIMATING, messages=msgs))
            return results

        # Damage
        dmg, type_mult, crit = calculate_damage(
            move            = mi.move,
            attacker_level  = poke.level,
            attacker_attack = poke.attack,
            attacker_sp_attack = poke.sp_attack,
            defender_defense   = target.defense,
            defender_sp_defense= target.sp_defense,
            attacker_types  = poke.types,
            defender_types  = target.types,
            attacker_atk_stage = poke.atk_stage,
            attacker_spa_stage = poke.spa_stage,
            defender_def_stage = target.def_stage,
            defender_spd_stage = target.spd_stage,
        )

        eff_label = effectiveness_label(type_mult)
        if eff_label:
            msgs.append(eff_label)
        if crit:
            msgs.append("A critical hit!")

        shake_target = None
        if dmg > 0:
            target.take_damage(dmg)
            shake_target = "enemy"

        # Secondary effect
        effect_msgs = apply_move_effect(mi.move.effect, target)
        msgs.extend(effect_msgs)

        results.append(BattleResult(phase=BattlePhase.ANIMATING,
                                    messages=msgs,
                                    shake_target=shake_target))

        if target.fainted:
            results.append(BattleResult(phase=BattlePhase.ANIMATING,
                           messages=[f"{target.name} fainted!"]))
            # Exp gain
            exp = self._calc_exp(target)
            level_msgs = poke.gain_exp(exp)
            results.append(BattleResult(phase=BattlePhase.ANIMATING,
                           messages=level_msgs))

        return results

    def _execute_enemy_move(self) -> list[BattleResult]:
        results: list[BattleResult] = []
        target = self.player_pokemon
        enemy  = self.enemy_pokemon

        if enemy.fainted:
            return results

        # Simple AI: pick highest-power usable move
        usable = [m for m in enemy.moves if m.current_pp > 0]
        if not usable:
            results.append(BattleResult(phase=BattlePhase.ANIMATING,
                           messages=[f"{enemy.name} has no moves left!"]))
            return results

        # Prefer moves that are super-effective
        def move_priority(mi):
            from battle.type_chart import get_dual_multiplier
            mult = get_dual_multiplier(mi.move.type,
                                       target.types[0],
                                       target.types[1] if len(target.types) > 1 else None)
            return mi.move.power * mult

        mi = max(usable, key=move_priority)

        # Paralysis
        if enemy.status == "paralysis" and random.random() < 0.25:
            results.append(BattleResult(phase=BattlePhase.ANIMATING,
                           messages=[f"{enemy.name} is paralyzed and can't move!"]))
            return results

        # Sleep
        if enemy.status == "sleep":
            enemy.sleep_counter -= 1
            if enemy.sleep_counter <= 0:
                enemy.status = None
                results.append(BattleResult(phase=BattlePhase.ANIMATING,
                               messages=[f"{enemy.name} woke up!"]))
            else:
                results.append(BattleResult(phase=BattlePhase.ANIMATING,
                               messages=[f"{enemy.name} is fast asleep!"]))
            return results

        mi.use()
        msgs = [f"Enemy {enemy.name} used {mi.display_name()}!"]

        if not accuracy_check(mi.move, enemy.acc_stage, target.eva_stage):
            msgs.append("But it missed!")
            results.append(BattleResult(phase=BattlePhase.ANIMATING, messages=msgs))
            return results

        dmg, type_mult, crit = calculate_damage(
            move            = mi.move,
            attacker_level  = enemy.level,
            attacker_attack = enemy.attack,
            attacker_sp_attack = enemy.sp_attack,
            defender_defense   = target.defense,
            defender_sp_defense= target.sp_defense,
            attacker_types  = enemy.types,
            defender_types  = target.types,
        )

        eff_label = effectiveness_label(type_mult)
        if eff_label:
            msgs.append(eff_label)
        if crit:
            msgs.append("A critical hit!")

        shake_target = None
        if dmg > 0:
            target.take_damage(dmg)
            shake_target = "player"

        effect_msgs = apply_move_effect(mi.move.effect, target)
        msgs.extend(effect_msgs)

        results.append(BattleResult(phase=BattlePhase.ANIMATING,
                                    messages=msgs,
                                    shake_target=shake_target))

        if target.fainted:
            results.append(BattleResult(phase=BattlePhase.ANIMATING,
                           messages=[f"{target.name} fainted!"]))

        return results

    # ------------------------------------------------------------------
    # Internal: items
    # ------------------------------------------------------------------
    def _use_item(self, item: dict) -> str:
        poke = self.player_pokemon
        itype = item.get("type", "")
        if itype == "heal":
            healed = poke.heal(item.get("heal_amount", 20))
            return f"You used {item['name']}. {poke.name} restored {healed} HP!"
        if itype == "pokeball":
            return self._attempt_catch(item)
        if itype == "revive":
            frac = item.get("heal_fraction", 0.5)
            if poke.fainted:
                poke.fainted = False
                poke.current_hp = max(1, int(poke.max_hp * frac))
                return f"{poke.name} was revived!"
            return f"{poke.name} is not fainted!"
        if itype == "status_cure":
            cures = item.get("cures", [])
            if poke.status in cures:
                poke.status = None
                return f"{poke.name} was cured!"
            return "It had no effect."
        return f"Used {item.get('name', 'item')}."

    def _attempt_catch(self, ball: dict) -> str:
        """Simplified catch formula."""
        if not self.is_wild:
            return "You can't catch a trainer's Pokémon!"
        rate    = self.enemy_pokemon.data.catch_rate / 255.0
        hp_mod  = (3 * self.enemy_pokemon.max_hp - 2 * self.enemy_pokemon.current_hp)
        hp_mod  = max(1, hp_mod) / max(1, 3 * self.enemy_pokemon.max_hp)
        catch_p = rate * hp_mod * ball.get("catch_multiplier", 1.0) * settings.BASE_CATCH_RATE
        if random.random() < catch_p:
            self.enemy_pokemon.fainted = True  # treat as "caught" = remove
            self.phase = BattlePhase.WIN
            return f"You caught {self.enemy_pokemon.name}!"
        return f"{self.enemy_pokemon.name} broke free!"

    # ------------------------------------------------------------------
    # Internal: EXP calculation
    # ------------------------------------------------------------------
    def _calc_exp(self, fainted: "PokemonInstance") -> int:
        base  = fainted.data.base_exp
        level = fainted.level
        return max(1, int((base * level) / 7))

    # ------------------------------------------------------------------
    # Phase transition helpers
    # ------------------------------------------------------------------
    def _advance_phase_after_turn(self, results: list[BattleResult]) -> None:
        # Check if any Pokémon fainted and decide next phase
        if self.player_pokemon.fainted:
            # Try to send in next alive Pokémon
            next_idx = self._next_alive_player()
            if next_idx is None:
                results.append(BattleResult(phase=BattlePhase.LOSE,
                               messages=["You have no Pokémon left!",
                                         "You blacked out!"]))
                self.phase = BattlePhase.LOSE
            else:
                self.player_idx = next_idx
                results.append(BattleResult(
                    phase=BattlePhase.PLAYER_ACTION,
                    messages=[f"Go! {self.player_pokemon.name}!"],
                ))
                self.phase = BattlePhase.PLAYER_ACTION
            return

        if self.enemy_pokemon.fainted:
            if not self.is_wild:
                next_enemy = self._next_trainer_pokemon()
                if next_enemy:
                    self.enemy_pokemon = next_enemy
                    name = self.trainer.name if self.trainer else "Trainer"
                    results.append(BattleResult(
                        phase=BattlePhase.PLAYER_ACTION,
                        messages=[f"{name} sent out {next_enemy.name}!"],
                    ))
                    self.phase = BattlePhase.PLAYER_ACTION
                    return
            # Battle won
            results.append(BattleResult(phase=BattlePhase.WIN,
                           messages=self._win_messages()))
            self.phase = BattlePhase.WIN
            return

        self.phase = BattlePhase.PLAYER_ACTION

    def _next_alive_player(self) -> int | None:
        for i, p in enumerate(self.player_team):
            if not p.fainted and i != self.player_idx:
                return i
        return None

    def _next_trainer_pokemon(self) -> "PokemonInstance | None":
        self.trainer_idx += 1
        if self.trainer_idx < len(self.trainer_team):
            return self.trainer_team[self.trainer_idx]
        return None

    def _win_messages(self) -> list[str]:
        if self.is_wild:
            return [f"Wild {self.enemy_pokemon.name} was defeated!"]
        name = self.trainer.name if self.trainer else "Trainer"
        return [f"You defeated {name}!"]
