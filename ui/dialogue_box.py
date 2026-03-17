"""
ui/dialogue_box.py — Scrolling dialogue box with typing effect.

Usage:
    box = DialogueBox()
    box.show(["Hello, Trainer!", "Welcome to the world of Pokémon!"])

    # In update loop:
    box.update(dt)

    # In draw loop:
    box.draw(surface)

    # Check completion:
    if box.is_finished:
        ...
"""

from __future__ import annotations

import pygame
import settings
from game.asset_loader import loader


class DialogueBox:
    """
    Renders a multi-line dialogue box at the bottom of the screen.

    The text is revealed character-by-character (typing effect).
    Pressing SPACE / RETURN advances to the next line.
    """

    BOX_RECT   = pygame.Rect(20, 510, 760, 160)
    PADDING    = 16
    FONT_SIZE  = 22
    LINE_SPACING = 30

    def __init__(self):
        self._lines:   list[str] = []
        self._line_idx: int      = 0
        self._char_idx: float    = 0.0
        self._visible: bool      = False
        self._speaker: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def show(self, lines: list[str], speaker: str | None = None) -> None:
        """Queue *lines* for display and make the box visible."""
        self._lines    = list(lines)
        self._line_idx = 0
        self._char_idx = 0.0
        self._visible  = True
        self._speaker  = speaker

    def hide(self) -> None:
        self._visible = False
        self._lines   = []

    @property
    def is_visible(self) -> bool:
        return self._visible

    @property
    def is_finished(self) -> bool:
        """True when the last line has been fully displayed."""
        if not self._visible or not self._lines:
            return True
        return (self._line_idx >= len(self._lines) - 1
                and self._char_idx >= len(self._lines[-1]))

    @property
    def current_line_complete(self) -> bool:
        if not self._lines:
            return True
        line = self._lines[self._line_idx]
        return self._char_idx >= len(line)

    # ------------------------------------------------------------------
    # Update / Advance
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if not self._visible or not self._lines:
            return
        line = self._lines[self._line_idx]
        if self._char_idx < len(line):
            self._char_idx += settings.DIALOGUE_SPEED * dt

    def advance(self) -> bool:
        """
        Advance to the next line or complete the current line.
        Returns True when all lines are exhausted (dialogue finished).
        """
        if not self._visible or not self._lines:
            return True

        line = self._lines[self._line_idx]
        if self._char_idx < len(line):
            # Snap current line to completion instantly
            self._char_idx = len(line)
            return False

        self._line_idx += 1
        if self._line_idx >= len(self._lines):
            self.hide()
            return True

        self._char_idx = 0.0
        return False

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        if not self._visible or not self._lines:
            return

        r = self.BOX_RECT

        # Background
        box_surf = pygame.Surface(r.size, pygame.SRCALPHA)
        box_surf.fill((*settings.DIALOGUE_BG, 230))
        surface.blit(box_surf, r.topleft)

        # Border
        pygame.draw.rect(surface, settings.DIALOGUE_BORDER, r, 2, border_radius=8)

        fnt = loader.font("couriernew", self.FONT_SIZE, bold=False)

        # Speaker name
        ty = r.top + self.PADDING
        if self._speaker:
            name_fnt = loader.font("couriernew", self.FONT_SIZE, bold=True)
            name_surf = name_fnt.render(self._speaker + ":", True, settings.UI_HIGHLIGHT)
            surface.blit(name_surf, (r.left + self.PADDING, ty))
            ty += self.LINE_SPACING

        # Visible lines: current and up to 1 previous (for multi-line feel)
        line = self._lines[self._line_idx]
        visible_text = line[:max(0, int(self._char_idx))]
        txt_surf = fnt.render(visible_text, True, settings.DIALOGUE_TEXT)
        surface.blit(txt_surf, (r.left + self.PADDING, ty))

        # "▼" advance indicator when line is complete
        if self.current_line_complete and not self.is_finished:
            ind_fnt = loader.font("couriernew", 18)
            ind = ind_fnt.render("▼", True, settings.UI_HIGHLIGHT)
            surface.blit(ind, (r.right - self.PADDING - ind.get_width(),
                                r.bottom - self.PADDING - ind.get_height()))
