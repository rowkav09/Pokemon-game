"""
ui/menus.py — Reusable menu components.

Menu         — generic vertical option list
MainMenu     — title screen
PauseMenu    — in-game overlay
BattleActionMenu — Fight / Bag / Pokémon / Run
InventoryMenu    — browse and use items
"""

from __future__ import annotations

import pygame
import settings
from game.asset_loader import loader


# ---------------------------------------------------------------------------
# Generic vertical menu
# ---------------------------------------------------------------------------
class Menu:
    """
    Simple up/down selectable option list.

    Parameters
    ----------
    options   : list of option label strings
    rect      : bounding box on screen
    font_size : label font size
    """

    def __init__(self, options: list[str], rect: pygame.Rect,
                 font_size: int = 22):
        self.options    = list(options)
        self.rect       = rect
        self.font_size  = font_size
        self._selected  = 0
        self._padding   = 12
        self._row_h     = font_size + 10

    # ------------------------------------------------------------------
    @property
    def selected_index(self) -> int:
        return self._selected

    @property
    def selected_option(self) -> str:
        return self.options[self._selected] if self.options else ""

    def move_up(self) -> None:
        self._selected = (self._selected - 1) % len(self.options)

    def move_down(self) -> None:
        self._selected = (self._selected + 1) % len(self.options)

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Return selected option string on RETURN/SPACE, else None."""
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in (pygame.K_UP, pygame.K_w):
            self.move_up()
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.move_down()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            return self.selected_option
        return None

    def draw(self, surface: pygame.Surface) -> None:
        r = self.rect
        # Background
        bg = pygame.Surface(r.size, pygame.SRCALPHA)
        bg.fill((*settings.UI_BG, 220))
        surface.blit(bg, r.topleft)
        pygame.draw.rect(surface, settings.UI_BORDER, r, 2, border_radius=6)

        fnt = loader.font("couriernew", self.font_size, bold=True)
        for i, option in enumerate(self.options):
            y = r.top + self._padding + i * self._row_h
            colour = settings.UI_HIGHLIGHT if i == self._selected else settings.UI_TEXT
            # Cursor
            if i == self._selected:
                cur_surf = fnt.render("▶", True, settings.UI_HIGHLIGHT)
                surface.blit(cur_surf, (r.left + self._padding, y))
            txt = fnt.render(option, True, colour)
            surface.blit(txt, (r.left + self._padding + 20, y))


# ---------------------------------------------------------------------------
# Main Menu
# ---------------------------------------------------------------------------
class MainMenu:
    """Full-screen title screen with Start / Continue / Quit."""

    OPTIONS = ["New Game", "Continue", "Quit"]

    def __init__(self):
        self._menu = Menu(
            self.OPTIONS,
            rect      = pygame.Rect(settings.SCREEN_WIDTH  // 2 - 120,
                                    settings.SCREEN_HEIGHT // 2 + 20,
                                    240, 120),
            font_size = 24,
        )

    @property
    def selected_option(self) -> str:
        return self._menu.selected_option

    def handle_event(self, event: pygame.event.Event) -> str | None:
        return self._menu.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        # Background gradient
        surface.fill((20, 30, 60))

        # Title
        title_fnt = loader.font("couriernew", 56, bold=True)
        title     = title_fnt.render("POKÉMON", True, settings.YELLOW)
        subtitle_fnt = loader.font("couriernew", 28)
        subtitle  = subtitle_fnt.render("Adventure", True, settings.WHITE)

        surface.blit(title,    (settings.SCREEN_WIDTH  // 2 - title.get_width()    // 2, 120))
        surface.blit(subtitle, (settings.SCREEN_WIDTH  // 2 - subtitle.get_width() // 2, 190))

        # Pokéball decoration
        pygame.draw.circle(surface, settings.RED,    (settings.SCREEN_WIDTH // 2, 340), 60)
        pygame.draw.circle(surface, settings.WHITE,  (settings.SCREEN_WIDTH // 2, 340), 60, 3)
        pygame.draw.line(surface, settings.WHITE,
                         (settings.SCREEN_WIDTH // 2 - 60, 340),
                         (settings.SCREEN_WIDTH // 2 + 60, 340), 5)
        pygame.draw.circle(surface, settings.WHITE,  (settings.SCREEN_WIDTH // 2, 340), 15)
        pygame.draw.circle(surface, settings.DARK_GRAY, (settings.SCREEN_WIDTH // 2, 340), 10)

        self._menu.draw(surface)

        hint = loader.font("couriernew", 14).render(
            "↑↓ Move   ENTER Select", True, settings.GRAY)
        surface.blit(hint, (settings.SCREEN_WIDTH // 2 - hint.get_width() // 2,
                             settings.SCREEN_HEIGHT - 40))


# ---------------------------------------------------------------------------
# Pause Menu
# ---------------------------------------------------------------------------
class PauseMenu:
    OPTIONS = ["Resume", "Pokémon", "Bag", "Save", "Quit to Title"]

    def __init__(self):
        w, h = 280, 200
        self._menu = Menu(
            self.OPTIONS,
            rect = pygame.Rect((settings.SCREEN_WIDTH - w) // 2,
                               (settings.SCREEN_HEIGHT - h) // 2,
                               w, h),
            font_size = 22,
        )

    @property
    def selected_option(self) -> str:
        return self._menu.selected_option

    def handle_event(self, event: pygame.event.Event) -> str | None:
        return self._menu.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        # Dim overlay
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT),
                                  pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        fnt   = loader.font("couriernew", 28, bold=True)
        title = fnt.render("PAUSED", True, settings.WHITE)
        r     = self._menu.rect
        surface.blit(title, (r.centerx - title.get_width() // 2, r.top - 40))

        self._menu.draw(surface)


# ---------------------------------------------------------------------------
# Battle Action Menu
# ---------------------------------------------------------------------------
class BattleActionMenu:
    OPTIONS = ["FIGHT", "BAG", "POKÉMON", "RUN"]

    def __init__(self):
        w, h = 320, 100
        self._menu = Menu(
            self.OPTIONS,
            rect      = pygame.Rect(settings.SCREEN_WIDTH - w - 10,
                                    settings.SCREEN_HEIGHT - h - 10,
                                    w, h),
            font_size = 22,
        )

    @property
    def selected_option(self) -> str:
        return self._menu.selected_option

    def handle_event(self, event: pygame.event.Event) -> str | None:
        return self._menu.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        self._menu.draw(surface)


# ---------------------------------------------------------------------------
# Move Select Menu (in battle)
# ---------------------------------------------------------------------------
class MoveSelectMenu:
    def __init__(self):
        self._moves: list = []   # list of MoveInstance
        self._selected = 0
        self._rect = pygame.Rect(10, settings.SCREEN_HEIGHT - 115, 330, 105)

    def set_moves(self, moves: list) -> None:
        self._moves   = moves
        self._selected = 0

    @property
    def selected_move(self):
        if not self._moves:
            return None
        return self._moves[self._selected]

    def handle_event(self, event: pygame.event.Event):
        if event.type != pygame.KEYDOWN or not self._moves:
            return None
        n = len(self._moves)
        if event.key in (pygame.K_UP, pygame.K_w):
            self._selected = (self._selected - 1) % n
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._selected = (self._selected + 1) % n
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            return self.selected_move
        elif event.key == pygame.K_ESCAPE:
            return "BACK"
        return None

    def draw(self, surface: pygame.Surface) -> None:
        r = self._rect
        bg = pygame.Surface(r.size, pygame.SRCALPHA)
        bg.fill((*settings.UI_BG, 220))
        surface.blit(bg, r.topleft)
        pygame.draw.rect(surface, settings.UI_BORDER, r, 2, border_radius=6)

        fnt  = loader.font("couriernew", 20, bold=True)
        type_fnt = loader.font("couriernew", 14)
        pad  = 10
        row_h = 24

        for i, mi in enumerate(self._moves):
            y = r.top + pad + i * row_h
            colour = settings.UI_HIGHLIGHT if i == self._selected else settings.UI_TEXT
            # cursor
            if i == self._selected:
                pygame.draw.rect(surface, (60, 60, 90),
                                 pygame.Rect(r.left + 2, y - 2, r.width - 4, row_h),
                                 border_radius=4)
            move_txt = fnt.render(mi.display_name(), True, colour)
            surface.blit(move_txt, (r.left + pad + 18, y))
            # PP
            pp_txt = type_fnt.render(f"PP {mi.current_pp}/{mi.move.pp}", True, settings.LIGHT_GRAY)
            surface.blit(pp_txt, (r.right - pp_txt.get_width() - pad, y + 4))

        # ESC hint
        hint = loader.font("couriernew", 13).render("[ESC] Back", True, settings.GRAY)
        surface.blit(hint, (r.left + pad, r.bottom - hint.get_height() - 3))


# ---------------------------------------------------------------------------
# Inventory Menu
# ---------------------------------------------------------------------------
class InventoryMenu:
    def __init__(self):
        self._items: list[dict] = []
        self._selected  = 0
        self._scroll    = 0
        self._visible_rows = 8
        self._rect = pygame.Rect(50, 60, 700, 580)

    def set_items(self, items: list[dict]) -> None:
        self._items = items
        self._selected = 0
        self._scroll   = 0

    @property
    def selected_item(self) -> dict | None:
        if not self._items:
            return None
        return self._items[self._selected]

    def handle_event(self, event: pygame.event.Event) -> dict | str | None:
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in (pygame.K_UP, pygame.K_w):
            self._selected = max(0, self._selected - 1)
            if self._selected < self._scroll:
                self._scroll = self._selected
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._selected = min(len(self._items) - 1, self._selected + 1)
            if self._selected >= self._scroll + self._visible_rows:
                self._scroll = self._selected - self._visible_rows + 1
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            return self.selected_item
        elif event.key == pygame.K_ESCAPE:
            return "CLOSE"
        return None

    def draw(self, surface: pygame.Surface) -> None:
        r = self._rect
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT),
                                  pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        bg = pygame.Surface(r.size, pygame.SRCALPHA)
        bg.fill((*settings.UI_BG, 240))
        surface.blit(bg, r.topleft)
        pygame.draw.rect(surface, settings.UI_BORDER, r, 2, border_radius=8)

        title_fnt = loader.font("couriernew", 26, bold=True)
        title = title_fnt.render("BAG", True, settings.UI_HIGHLIGHT)
        surface.blit(title, (r.left + 20, r.top + 12))

        fnt = loader.font("couriernew", 20)
        row_h = 36
        pad   = 16

        visible = self._items[self._scroll: self._scroll + self._visible_rows]
        for i, item in enumerate(visible):
            actual_idx = self._scroll + i
            y = r.top + 56 + i * row_h
            if actual_idx == self._selected:
                pygame.draw.rect(surface, (60, 60, 100),
                                 pygame.Rect(r.left + 4, y - 2, r.width - 8, row_h - 4),
                                 border_radius=4)
            name_txt = fnt.render(item["name"], True, settings.UI_TEXT)
            qty_txt  = fnt.render(f"× {item['quantity']}", True, settings.LIGHT_GRAY)
            surface.blit(name_txt, (r.left + pad + 20, y))
            surface.blit(qty_txt,  (r.right - qty_txt.get_width() - pad, y))

        # Description of selected item
        if self._items:
            sel = self._items[self._selected]
            desc_fnt = loader.font("couriernew", 16)
            desc = desc_fnt.render(sel.get("description", ""), True, settings.LIGHT_GRAY)
            surface.blit(desc, (r.left + pad, r.bottom - 40))

        hint = loader.font("couriernew", 14).render(
            "↑↓ Navigate   ENTER Use   ESC Close", True, settings.GRAY)
        surface.blit(hint, (r.left + pad, r.bottom - 20))
