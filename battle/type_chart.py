"""
battle/type_chart.py — Pokémon type effectiveness chart (Gen VI / Gen VIII rules).

get_multiplier(attacking_type, defending_type) -> float
    Returns 0.0, 0.25, 0.5, 1.0, 2.0, or 4.0.

get_dual_multiplier(attacking_type, type1, type2) -> float
    Returns the combined effectiveness against a dual-type defender.
"""

# Effectiveness table: chart[ATK][DEF] = multiplier
# Only non-1.0 values are stored; missing keys default to 1.0.
_CHART: dict[str, dict[str, float]] = {
    "normal": {
        "rock": 0.5, "ghost": 0.0, "steel": 0.5
    },
    "fire": {
        "fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0,
        "bug": 2.0, "rock": 0.5, "dragon": 0.5, "steel": 2.0
    },
    "water": {
        "fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0,
        "rock": 2.0, "dragon": 0.5
    },
    "electric": {
        "water": 2.0, "electric": 0.5, "grass": 0.5, "ground": 0.0,
        "flying": 2.0, "dragon": 0.5
    },
    "grass": {
        "fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5,
        "ground": 2.0, "flying": 0.5, "bug": 0.5, "rock": 2.0,
        "dragon": 0.5, "steel": 0.5
    },
    "ice": {
        "fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 0.5,
        "ground": 2.0, "flying": 2.0, "dragon": 2.0, "steel": 0.5
    },
    "fighting": {
        "normal": 2.0, "ice": 2.0, "poison": 0.5, "flying": 0.5,
        "psychic": 0.5, "bug": 0.5, "rock": 2.0, "ghost": 0.0,
        "dark": 2.0, "steel": 2.0, "fairy": 0.5
    },
    "poison": {
        "grass": 2.0, "poison": 0.5, "ground": 0.5, "rock": 0.5,
        "ghost": 0.5, "steel": 0.0, "fairy": 2.0
    },
    "ground": {
        "fire": 2.0, "electric": 2.0, "grass": 0.5, "poison": 2.0,
        "flying": 0.0, "bug": 0.5, "rock": 2.0, "steel": 2.0
    },
    "flying": {
        "electric": 0.5, "grass": 2.0, "fighting": 2.0, "bug": 2.0,
        "rock": 0.5, "steel": 0.5
    },
    "psychic": {
        "fighting": 2.0, "poison": 2.0, "psychic": 0.5,
        "dark": 0.0, "steel": 0.5
    },
    "bug": {
        "fire": 0.5, "grass": 2.0, "fighting": 0.5, "poison": 0.5,
        "flying": 0.5, "psychic": 2.0, "ghost": 0.5, "dark": 2.0,
        "steel": 0.5, "fairy": 0.5
    },
    "rock": {
        "fire": 2.0, "ice": 2.0, "fighting": 0.5, "ground": 0.5,
        "flying": 2.0, "bug": 2.0, "steel": 0.5
    },
    "ghost": {
        "normal": 0.0, "psychic": 2.0, "ghost": 2.0, "dark": 0.5
    },
    "dragon": {
        "dragon": 2.0, "steel": 0.5, "fairy": 0.0
    },
    "dark": {
        "fighting": 0.5, "psychic": 2.0, "ghost": 2.0, "dark": 0.5, "fairy": 0.5
    },
    "steel": {
        "fire": 0.5, "water": 0.5, "electric": 0.5, "ice": 2.0,
        "rock": 2.0, "steel": 0.5, "fairy": 2.0
    },
    "fairy": {
        "fire": 0.5, "fighting": 2.0, "poison": 0.5, "dragon": 2.0,
        "dark": 2.0, "steel": 0.5
    },
}


def get_multiplier(attacking_type: str, defending_type: str) -> float:
    """Return the type effectiveness multiplier for a single type pair."""
    atk = attacking_type.lower()
    def_ = defending_type.lower()
    return _CHART.get(atk, {}).get(def_, 1.0)


def get_dual_multiplier(attacking_type: str,
                        type1: str, type2: str | None = None) -> float:
    """Return combined effectiveness against a one- or two-type defender."""
    m = get_multiplier(attacking_type, type1)
    if type2:
        m *= get_multiplier(attacking_type, type2)
    return m


def effectiveness_label(multiplier: float) -> str:
    """Human-readable effectiveness label."""
    if multiplier == 0.0:
        return "It had no effect!"
    if multiplier < 1.0:
        return "It's not very effective..."
    if multiplier > 1.0:
        return "It's super effective!"
    return ""
