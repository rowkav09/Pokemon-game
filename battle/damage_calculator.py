"""
battle/damage_calculator.py — Pokémon damage formula (Gen I style, adapted).

Formula:
    damage = ( (2*level/5 + 2) * power * A/D / 50 + 2 )
             * STAB * type_effectiveness * random * critical
"""

from __future__ import annotations

import math
import random

from battle.type_chart import get_dual_multiplier, effectiveness_label
from battle.move import Move


# ---------------------------------------------------------------------------
# Stat stage multiplier table  (−6 to +6)
# ---------------------------------------------------------------------------
_STAGE_MULT = {
    -6: 2/8, -5: 2/7, -4: 2/6, -3: 2/5, -2: 2/4, -1: 2/3,
     0: 1.0,
     1: 3/2,  2: 4/2,  3: 5/2,  4: 6/2,  5: 7/2,  6: 8/2,
}
_ACC_EVA_MULT = {
    -6: 3/9, -5: 3/8, -4: 3/7, -3: 3/6, -2: 3/5, -1: 3/4,
     0: 1.0,
     1: 4/3,  2: 5/3,  3: 6/3,  4: 7/3,  5: 8/3,  6: 9/3,
}


def stat_stage_mult(stage: int) -> float:
    return _STAGE_MULT.get(max(-6, min(6, stage)), 1.0)


def acc_eva_mult(stage: int) -> float:
    return _ACC_EVA_MULT.get(max(-6, min(6, stage)), 1.0)


# ---------------------------------------------------------------------------
# Accuracy check
# ---------------------------------------------------------------------------
def accuracy_check(move: Move, attacker_acc_stage: int = 0,
                   defender_eva_stage: int = 0) -> bool:
    """Return True if the move hits."""
    if move.accuracy == 0:
        return True
    acc = move.accuracy * acc_eva_mult(attacker_acc_stage) / acc_eva_mult(defender_eva_stage)
    return random.randint(1, 100) <= int(acc)


# ---------------------------------------------------------------------------
# Critical hit
# ---------------------------------------------------------------------------
CRIT_STAGE_CHANCES = [1/16, 1/8, 1/4, 1/3, 1/2]

def is_critical(crit_stage: int = 0) -> bool:
    idx = min(crit_stage, len(CRIT_STAGE_CHANCES) - 1)
    return random.random() < CRIT_STAGE_CHANCES[idx]


# ---------------------------------------------------------------------------
# Main damage calculation
# ---------------------------------------------------------------------------
def calculate_damage(
    *,
    move: Move,
    attacker_level: int,
    attacker_attack: int,       # effective stat (base * stage mult)
    attacker_sp_attack: int,
    defender_defense: int,
    defender_sp_defense: int,
    attacker_types: list[str],
    defender_types: list[str],
    attacker_atk_stage: int  = 0,
    attacker_spa_stage: int  = 0,
    defender_def_stage: int  = 0,
    defender_spd_stage: int  = 0,
    crit_stage: int = 0,
) -> tuple[int, float, bool]:
    """
    Returns (damage, type_multiplier, is_crit).
    damage = 0 if the move is status or has 0 effectiveness.
    """
    if move.category == "status" or move.power == 0:
        return 0, 1.0, False

    # Choose which stats to use
    if move.category == "physical":
        A = max(1, int(attacker_attack  * stat_stage_mult(attacker_atk_stage)))
        D = max(1, int(defender_defense * stat_stage_mult(defender_def_stage)))
    else:
        A = max(1, int(attacker_sp_attack   * stat_stage_mult(attacker_spa_stage)))
        D = max(1, int(defender_sp_defense  * stat_stage_mult(defender_spd_stage)))

    crit = is_critical(crit_stage)
    crit_mult = 2.0 if crit else 1.0
    # Critical ignores negative attacker stages / positive defender stages
    if crit:
        A = max(1, int(attacker_attack  if move.category == "physical" else attacker_sp_attack))
        D = max(1, int(defender_defense if move.category == "physical" else defender_sp_defense))

    # Type effectiveness
    def_t1 = defender_types[0] if defender_types else "normal"
    def_t2 = defender_types[1] if len(defender_types) > 1 else None
    type_mult = get_dual_multiplier(move.type, def_t1, def_t2)

    if type_mult == 0.0:
        return 0, 0.0, False

    # STAB (Same Type Attack Bonus)
    stab = 1.5 if move.type in attacker_types else 1.0

    # Base damage formula
    base = math.floor(
        (math.floor(2 * attacker_level / 5 + 2) * move.power * A / D) / 50
    ) + 2

    # Apply modifiers
    damage = math.floor(base * stab * type_mult * crit_mult)

    # Random factor: 85-100 % of damage
    damage = math.floor(damage * random.randint(85, 100) / 100)

    return max(1, damage), type_mult, crit


# ---------------------------------------------------------------------------
# Status effect application
# ---------------------------------------------------------------------------
def apply_move_effect(effect: dict | None, target) -> list[str]:
    """
    Apply secondary effect to *target* (a PokemonInstance).
    Returns a list of message strings to display.
    """
    messages: list[str] = []
    if not effect:
        return messages

    chance = effect.get("chance", 100)
    if random.randint(1, 100) > chance:
        return messages

    etype = effect.get("type", "")

    if etype == "burn" and not target.status:
        target.status = "burn"
        messages.append(f"{target.name} was burned!")
    elif etype == "poison" and not target.status:
        target.status = "poison"
        messages.append(f"{target.name} was poisoned!")
    elif etype == "paralysis" and not target.status:
        target.status = "paralysis"
        messages.append(f"{target.name} is paralyzed!")
    elif etype == "sleep" and not target.status:
        target.status = "sleep"
        target.sleep_counter = random.randint(1, 3)
        messages.append(f"{target.name} fell asleep!")
    elif etype == "confusion" and not target.confused:
        target.confused = True
        messages.append(f"{target.name} became confused!")
    elif etype in ("lower_attack", "lower_defense", "lower_speed",
                   "lower_accuracy", "lower_sp_defense"):
        stat_map = {
            "lower_attack":     "atk_stage",
            "lower_defense":    "def_stage",
            "lower_speed":      "spe_stage",   # speed stage (not sp_defense)
            "lower_accuracy":   "acc_stage",
            "lower_sp_defense": "spd_stage",   # special-defense stage
        }
        attr = stat_map[etype]
        stages = effect.get("stages", 1)
        old = getattr(target, attr, 0)
        setattr(target, attr, max(-6, old - stages))
        stat_name = etype.replace("lower_", "").replace("_", " ").title()
        messages.append(f"{target.name}'s {stat_name} fell!")
    elif etype in ("raise_defense", "raise_speed"):
        stat_map = {
            "raise_defense": "def_stage",
            "raise_speed":   "spe_stage",   # speed stage
        }
        attr = stat_map[etype]
        stages = effect.get("stages", 1)
        old = getattr(target, attr, 0)
        setattr(target, attr, min(6, old + stages))
        stat_name = etype.replace("raise_", "").replace("_", " ").title()
        messages.append(f"{target.name}'s {stat_name} rose!")
    elif etype == "half_hp":
        dmg = max(1, target.current_hp // 2)
        target.current_hp -= dmg
    elif etype == "leech_seed":
        target.leech_seeded = True
        messages.append(f"{target.name} was seeded!")

    return messages
