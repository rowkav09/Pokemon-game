"""
ui/health_bar.py — Animated HP and EXP bars for battle and world UI.
"""

from __future__ import annotations

import pygame
import settings


def hp_colour(fraction: float) -> tuple[int, int, int]:
    """Return HP bar colour based on remaining fraction (0.0-1.0)."""
    if fraction > 0.5:
        return settings.HP_GREEN
    if fraction > 0.25:
        return settings.HP_YELLOW
    return settings.HP_RED


class HealthBar:
    """
    Animated HP bar that smoothly interpolates toward the real value.

    Parameters
    ----------
    x, y        : position on screen
    width, height: bar dimensions
    animated    : if True, bar animates toward target value
    """

    def __init__(self, x: int, y: int, width: int = 200, height: int = 12,
                 animated: bool = True):
        self.rect = pygame.Rect(x, y, width, height)
        self._displayed: float = 1.0   # fraction currently shown (0-1)
        self._target:    float = 1.0
        self.animated = animated
        self._anim_speed = 1.5         # fractions per second

    def set_value(self, fraction: float, instant: bool = False) -> None:
        """Set the target fraction; optionally jump instantly."""
        self._target = max(0.0, min(1.0, fraction))
        if instant or not self.animated:
            self._displayed = self._target

    def update(self, dt: float) -> None:
        if self._displayed != self._target:
            diff = self._target - self._displayed
            step = self._anim_speed * dt
            if abs(diff) <= step:
                self._displayed = self._target
            else:
                self._displayed += step * (1 if diff > 0 else -1)

    @property
    def is_animating(self) -> bool:
        return self._displayed != self._target

    def draw(self, surface: pygame.Surface,
             show_numbers: bool = False,
             current: int = 0, maximum: int = 0) -> None:
        r = self.rect

        # Background track
        pygame.draw.rect(surface, settings.DARK_GRAY, r, border_radius=4)

        # Filled portion
        fill_w = max(0, round(r.width * self._displayed))
        if fill_w > 0:
            fill_rect = pygame.Rect(r.x, r.y, fill_w, r.height)
            pygame.draw.rect(surface, hp_colour(self._displayed),
                             fill_rect, border_radius=4)

        # Border
        pygame.draw.rect(surface, settings.UI_BORDER, r, 1, border_radius=4)

        if show_numbers and maximum > 0:
            fnt = pygame.font.SysFont("couriernew", 12)
            txt = fnt.render(f"{current}/{maximum}", True, settings.WHITE)
            surface.blit(txt, (r.right + 6, r.centery - txt.get_height() // 2))


class ExpBar:
    """Thin EXP bar below the HP bar."""

    def __init__(self, x: int, y: int, width: int = 200, height: int = 5):
        self.rect = pygame.Rect(x, y, width, height)
        self._fraction: float = 0.0

    def set_value(self, fraction: float) -> None:
        self._fraction = max(0.0, min(1.0, fraction))

    def draw(self, surface: pygame.Surface) -> None:
        r = self.rect
        pygame.draw.rect(surface, settings.DARK_GRAY, r, border_radius=2)
        fill_w = max(0, round(r.width * self._fraction))
        if fill_w > 0:
            fill_rect = pygame.Rect(r.x, r.y, fill_w, r.height)
            pygame.draw.rect(surface, settings.EXP_BLUE, fill_rect, border_radius=2)
        pygame.draw.rect(surface, settings.UI_BORDER, r, 1, border_radius=2)
