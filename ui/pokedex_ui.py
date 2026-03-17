from __future__ import annotations

import pygame

import settings
from game.asset_loader import loader


class PokedexUI:
    def __init__(self):
        self._selected = 0
        self._scroll = 0
        self._rows = 10
        self._list_rect = pygame.Rect(30, 70, 360, 560)
        self._detail_rect = pygame.Rect(410, 70, 360, 560)

    def handle_event(self, event: pygame.event.Event, total: int) -> str | None:
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in (pygame.K_ESCAPE, pygame.K_p, pygame.K_TAB):
            return "CLOSE"
        if event.key in (pygame.K_UP, pygame.K_w):
            self._selected = max(0, self._selected - 1)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._selected = min(max(0, total - 1), self._selected + 1)
        elif event.key in (pygame.K_PAGEUP,):
            self._selected = max(0, self._selected - self._rows)
        elif event.key in (pygame.K_PAGEDOWN,):
            self._selected = min(max(0, total - 1), self._selected + self._rows)
        self._scroll = min(self._scroll, self._selected)
        if self._selected >= self._scroll + self._rows:
            self._scroll = self._selected - self._rows + 1
        return None

    def draw(self, surface: pygame.Surface, entries: list[dict], seen_count: int, caught_count: int) -> None:
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 14, 24, 235))
        surface.blit(overlay, (0, 0))

        title_fnt = loader.font("couriernew", 28, bold=True)
        txt_fnt = loader.font("couriernew", 18)
        small_fnt = loader.font("couriernew", 14)
        title = title_fnt.render("POKÉDEX", True, settings.UI_HIGHLIGHT)
        surface.blit(title, (32, 24))

        total = max(1, len(entries))
        completion = int((caught_count / total) * 100)
        summary = txt_fnt.render(
            f"Seen: {seen_count}/{total}  Caught: {caught_count}/{total}  Completion: {completion}%",
            True, settings.WHITE,
        )
        surface.blit(summary, (210, 32))

        pygame.draw.rect(surface, settings.UI_BORDER, self._list_rect, 2, border_radius=8)
        pygame.draw.rect(surface, settings.UI_BORDER, self._detail_rect, 2, border_radius=8)

        visible = entries[self._scroll:self._scroll + self._rows]
        for i, entry in enumerate(visible):
            idx = self._scroll + i
            y = self._list_rect.top + 12 + i * 52
            row = pygame.Rect(self._list_rect.left + 8, y, self._list_rect.width - 16, 46)
            if idx == self._selected:
                pygame.draw.rect(surface, (54, 64, 100), row, border_radius=6)
            seen = entry["seen"]
            caught = entry["caught"]
            status = "CAUGHT" if caught else ("SEEN" if seen else "---")
            name = entry["name"] if seen else "???"
            text = txt_fnt.render(f"#{entry['id']:03d} {name}", True, settings.WHITE)
            stat = small_fnt.render(status, True, settings.LIGHT_GRAY)
            surface.blit(text, (row.left + 10, row.top + 10))
            surface.blit(stat, (row.right - stat.get_width() - 10, row.top + 15))

        if entries:
            e = entries[self._selected]
            name = e["name"] if e["seen"] else "???"
            type_line = "/".join(e["types"]) if e["seen"] else "Unknown"
            stats = e["stats"] if e["seen"] else None
            flavor = e["flavor"] if e["seen"] else "Encounter this Pokémon to register details."
            name_t = title_fnt.render(f"#{e['id']:03d} {name}", True, settings.WHITE)
            type_t = txt_fnt.render(f"Type: {type_line}", True, settings.LIGHT_GRAY)
            surface.blit(name_t, (self._detail_rect.left + 14, self._detail_rect.top + 14))
            surface.blit(type_t, (self._detail_rect.left + 14, self._detail_rect.top + 54))
            if stats:
                lines = [
                    f"HP {stats['hp']}  ATK {stats['attack']}  DEF {stats['defense']}",
                    f"SPA {stats['sp_attack']}  SPD {stats['sp_defense']}  SPE {stats['speed']}",
                ]
                for i, line in enumerate(lines):
                    ls = txt_fnt.render(line, True, settings.WHITE)
                    surface.blit(ls, (self._detail_rect.left + 14, self._detail_rect.top + 96 + i * 26))
            flavor_lines = _wrap_text(flavor, small_fnt, self._detail_rect.width - 28)
            for i, line in enumerate(flavor_lines[:6]):
                ls = small_fnt.render(line, True, settings.LIGHT_GRAY)
                surface.blit(ls, (self._detail_rect.left + 14, self._detail_rect.bottom - 140 + i * 20))

        hint = small_fnt.render("↑↓ select  PgUp/PgDn scroll  P/ESC close", True, settings.GRAY)
        surface.blit(hint, (32, settings.SCREEN_HEIGHT - 26))


def _wrap_text(text: str, font: pygame.font.Font, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        nxt = (cur + " " + w).strip()
        if font.size(nxt)[0] <= width:
            cur = nxt
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines
