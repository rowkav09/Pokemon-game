"""
game/state_manager.py — Enum-based game state machine.

States:
    MAIN_MENU   — title screen
    WORLD       — overworld exploration
    DIALOGUE    — NPC / item text
    BATTLE      — turn-based Pokémon battle
    INVENTORY   — bag / items screen
    PAUSE       — in-game pause menu
    GAME_OVER   — player blacked out
"""

from enum import Enum, auto


class GameState(Enum):
    MAIN_MENU = auto()
    WORLD     = auto()
    DIALOGUE  = auto()
    BATTLE    = auto()
    CATCH_MINIGAME = auto()
    INVENTORY = auto()
    POKEDEX   = auto()
    PARTY     = auto()
    PAUSE     = auto()
    GAME_OVER = auto()


class StateManager:
    """Tracks the active game state and maintains a small history stack."""

    def __init__(self, initial: GameState = GameState.MAIN_MENU):
        self._state   = initial
        self._history = []           # previous states (for overlay-style states)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def state(self) -> GameState:
        return self._state

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------
    def change(self, new_state: GameState) -> None:
        """Hard-switch to a new state, clearing history."""
        self._history.clear()
        self._state = new_state

    def push(self, new_state: GameState) -> None:
        """Push current state onto the history stack, overlay a new one."""
        self._history.append(self._state)
        self._state = new_state

    def pop(self) -> GameState:
        """Return to the previously pushed state.  No-op at stack bottom."""
        if self._history:
            self._state = self._history.pop()
        return self._state

    # ------------------------------------------------------------------
    # Convenience checks
    # ------------------------------------------------------------------
    def is_state(self, *states: GameState) -> bool:
        return self._state in states

    def __repr__(self) -> str:  # pragma: no cover
        return f"StateManager(state={self._state.name}, history={[s.name for s in self._history]})"
