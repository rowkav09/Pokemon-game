"""
battle/battle_ui.py — Renders the battle screen.

BattleUI owns all display logic; BattleSystem owns all game logic.
"""

from __future__ import annotations

import math
import os

import pygame

import settings
from game.asset_loader import loader
from ui.health_bar import HealthBar, ExpBar
from ui.dialogue_box import DialogueBox


# Type-colour palette for badge labels
TYPE_COLOURS: dict[str, tuple[int, int, int]] = {
    "normal":   (168, 167, 122),
    "fire":     (238, 129,  48),
    "water":    ( 99, 144, 240),
    "grass":    (122, 199,  76),
    "electric": (247, 208,  44),
    "ice":      (150, 217, 214),
    "fighting": (194,  46,  40),
    "poison":   (163,  62, 161),
    "ground":   (226, 191,  10),
    "flying":   (169, 143, 243),
    "psychic":  (249,  85, 135),
    "bug":      (166, 185,  26),
    "rock":     (182, 161,  54),
    "ghost":    (115,  87, 151),
    "dragon":   (111,  53, 252),
    "dark":     ( 74,  69,  85),
    "steel":    (183, 183, 206),
    "fairy":    (214, 133, 173),
}


class PokemonHUD:
    """
    Draws one Pokémon's info card (name, level, HP bar, EXP bar).

    Parameters
    ----------
    is_player   : controls which side of the screen (left / right)
    show_exp    : show EXP bar (only for player's Pokémon)
    """

    CARD_W = 340
    CARD_H = 90

    def __init__(self, is_player: bool, show_exp: bool = False):
        self.is_player = is_player
        self.show_exp  = show_exp
        if is_player:
            self._rect = pygame.Rect(*settings.BATTLE_PLAYER_HUD_POS,
                                     self.CARD_W, self.CARD_H)
        else:
            self._rect = pygame.Rect(*settings.BATTLE_ENEMY_HUD_POS,
                                     self.CARD_W, self.CARD_H)

        bar_x = self._rect.x + 120
        bar_y = self._rect.y + 48
        self._hp_bar  = HealthBar(bar_x, bar_y, width=200, height=14)
        self._exp_bar = ExpBar(bar_x, bar_y + 20, width=200, height=6) if show_exp else None

    def update_pokemon(self, pokemon, instant: bool = False) -> None:
        self._hp_bar.set_value(pokemon.hp_fraction, instant=instant)
        if self._exp_bar:
            self._exp_bar.set_value(pokemon.exp_fraction)

    def update(self, dt: float) -> None:
        self._hp_bar.update(dt)

    def draw(self, surface: pygame.Surface, pokemon) -> None:
        r = self._rect

        # Card background
        card = pygame.Surface(r.size, pygame.SRCALPHA)
        card.fill((240, 240, 240, 230))
        surface.blit(card, r.topleft)
        pygame.draw.rect(surface, settings.DARK_GRAY, r, 2, border_radius=8)

        # Name
        name_fnt = loader.font("couriernew", 20, bold=True)
        name_txt = name_fnt.render(pokemon.name, True, settings.BLACK)
        surface.blit(name_txt, (r.left + 10, r.top + 8))

        # Level
        lvl_fnt = loader.font("couriernew", 16)
        lvl_txt = lvl_fnt.render(f"Lv.{pokemon.level}", True, settings.DARK_GRAY)
        surface.blit(lvl_txt, (r.right - lvl_txt.get_width() - 10, r.top + 10))

        # Type badge(s)
        bfnt = loader.font("couriernew", 12, bold=True)
        bx = r.left + 10
        for t in pokemon.types[:2]:
            colour = TYPE_COLOURS.get(t.lower(), settings.GRAY)
            badge = pygame.Rect(bx, r.top + 32, 50, 14)
            pygame.draw.rect(surface, colour, badge, border_radius=3)
            bt = bfnt.render(t.upper(), True, settings.WHITE)
            surface.blit(bt, (badge.x + badge.w // 2 - bt.get_width() // 2,
                               badge.y + badge.h // 2 - bt.get_height() // 2))
            bx += 56

        # Status
        if pokemon.status:
            sfnt = loader.font("couriernew", 12, bold=True)
            sc = {"burn": (220, 100, 50), "poison": (160, 50, 160),
                  "paralysis": (200, 200, 50), "sleep": (100, 100, 180),
                  "freeze": (100, 200, 220)}.get(pokemon.status, settings.GRAY)
            st = sfnt.render(pokemon.status[:3].upper(), True, settings.WHITE)
            sr = pygame.Rect(r.right - 42, r.top + 30, 38, 14)
            pygame.draw.rect(surface, sc, sr, border_radius=3)
            surface.blit(st, (sr.centerx - st.get_width() // 2,
                               sr.centery - st.get_height() // 2))

        # "HP" label
        hp_fnt = loader.font("couriernew", 14, bold=True)
        hp_lbl = hp_fnt.render("HP", True, settings.DARK_GRAY)
        surface.blit(hp_lbl, (r.left + 10, r.top + 50))

        # HP bar
        self._hp_bar.draw(surface,
                          show_numbers=self.is_player,
                          current=pokemon.current_hp,
                          maximum=pokemon.max_hp)
        if self._exp_bar:
            self._exp_bar.draw(surface)


class BattleUI:
    """
    Full battle screen renderer.

    Call update(dt) and draw(screen, battle_state) every frame.
    """

    # Background grass strips
    _BATTLE_BG_TOP    = (100, 150, 80)
    _BATTLE_BG_BOT    = (180, 220, 120)
    _PLATFORM_COLOUR  = (200, 170, 120)

    def __init__(self):
        self._player_hud = PokemonHUD(is_player=True,  show_exp=True)
        self._enemy_hud  = PokemonHUD(is_player=False, show_exp=False)
        self._dialogue   = DialogueBox()

        # Pokémon sprite cache: id -> scaled Surface
        self._sprite_cache: dict[int, pygame.Surface] = {}
        self._pokemon_sheet_path = os.path.join(settings.IMAGES_DIR,
                                                 "3d_starter_sheet.png")

        # Flash / shake animation
        self._flash_timer = 0.0
        self._flash_target: str | None = None   # "player" or "enemy"
        self._shake_timer  = 0.0
        self._shake_target: str | None = None
        self._t = 0.0  # global time for animations

    # ------------------------------------------------------------------
    # Pokémon sprites
    # ------------------------------------------------------------------
    def _get_sprite(self, pokemon, flip: bool = False) -> pygame.Surface | None:
        key = (pokemon.data.sprite_index, flip)
        if key not in self._sprite_cache:
            if not os.path.isfile(self._pokemon_sheet_path):
                return None
            idx = pokemon.data.sprite_index
            col = idx % 6
            row = idx // 6
            rect = pygame.Rect(
                col * settings.POKEMON_FRAME_WIDTH,
                row * settings.POKEMON_FRAME_HEIGHT,
                settings.POKEMON_FRAME_WIDTH,
                settings.POKEMON_FRAME_HEIGHT,
            )
            surf = loader.sub_image(
                self._pokemon_sheet_path, rect,
                scale=(150, 165),
            )
            if flip:
                surf = pygame.transform.flip(surf, True, False)
            self._sprite_cache[key] = surf
        return self._sprite_cache[key]

    # ------------------------------------------------------------------
    # Animation helpers
    # ------------------------------------------------------------------
    def flash(self, target: str) -> None:
        self._flash_timer  = 0.3
        self._flash_target = target

    def shake(self, target: str) -> None:
        self._shake_timer  = 0.4
        self._shake_target = target

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt: float, player_pokemon, enemy_pokemon) -> None:
        self._t += dt
        self._flash_timer  = max(0.0, self._flash_timer  - dt)
        self._shake_timer  = max(0.0, self._shake_timer  - dt)
        self._player_hud.update_pokemon(player_pokemon)
        self._enemy_hud.update_pokemon(enemy_pokemon)
        self._player_hud.update(dt)
        self._enemy_hud.update(dt)
        self._dialogue.update(dt)

    def update_hp_instant(self, player_pokemon, enemy_pokemon) -> None:
        self._player_hud.update_pokemon(player_pokemon, instant=True)
        self._enemy_hud.update_pokemon(enemy_pokemon,  instant=True)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, player_pokemon,
             enemy_pokemon, phase: str, *, move_menu=None) -> None:
        self._draw_background(surface)
        self._draw_pokemon_sprites(surface, player_pokemon, enemy_pokemon)
        self._player_hud.draw(surface, player_pokemon)
        self._enemy_hud.draw(surface, enemy_pokemon)
        self._dialogue.draw(surface)

        if phase == "MOVE_SELECT" and move_menu:
            move_menu.draw(surface)

    # ------------------------------------------------------------------
    # Background
    # ------------------------------------------------------------------
    def _draw_background(self, surface: pygame.Surface) -> None:
        # Sky / grass split
        surface.fill(self._BATTLE_BG_TOP)
        pygame.draw.rect(surface, self._BATTLE_BG_BOT,
                         pygame.Rect(0, settings.SCREEN_HEIGHT // 2,
                                     settings.SCREEN_WIDTH,
                                     settings.SCREEN_HEIGHT // 2))
        # Platforms
        # Enemy platform
        ep = pygame.Rect(430, 230, 200, 24)
        pygame.draw.ellipse(surface, self._PLATFORM_COLOUR, ep)
        # Player platform
        pp = pygame.Rect(50, 390, 200, 24)
        pygame.draw.ellipse(surface, self._PLATFORM_COLOUR, pp)

    # ------------------------------------------------------------------
    # Pokémon sprites
    # ------------------------------------------------------------------
    def _draw_pokemon_sprites(self, surface: pygame.Surface,
                               player_pokemon, enemy_pokemon) -> None:
        # --- enemy ---
        e_sprite = self._get_sprite(enemy_pokemon, flip=False)
        ex, ey   = settings.BATTLE_ENEMY_SPRITE_POS
        if self._shake_timer > 0 and self._shake_target == "enemy":
            ex += int(8 * math.sin(self._t * 40))

        if e_sprite:
            if self._flash_timer > 0 and self._flash_target == "enemy":
                fs = e_sprite.copy()
                fs.fill((255, 255, 255, 180), special_flags=pygame.BLEND_RGBA_ADD)
                surface.blit(fs, (ex, ey))
            else:
                surface.blit(e_sprite, (ex, ey))
        else:
            self._draw_placeholder(surface, (ex, ey), enemy_pokemon.name)

        # --- player ---
        p_sprite = self._get_sprite(player_pokemon, flip=True)
        px, py   = settings.BATTLE_PLAYER_SPRITE_POS
        if self._shake_timer > 0 and self._shake_target == "player":
            px += int(8 * math.sin(self._t * 40))

        if p_sprite:
            if self._flash_timer > 0 and self._flash_target == "player":
                fs = p_sprite.copy()
                fs.fill((255, 255, 255, 180), special_flags=pygame.BLEND_RGBA_ADD)
                surface.blit(fs, (px, py))
            else:
                surface.blit(p_sprite, (px, py))
        else:
            self._draw_placeholder(surface, (px, py), player_pokemon.name)

    @staticmethod
    def _draw_placeholder(surface, pos, name) -> None:
        r = pygame.Rect(pos[0], pos[1], 120, 120)
        pygame.draw.ellipse(surface, settings.GRAY, r)
        fnt  = loader.font("couriernew", 14)
        txt  = fnt.render(name, True, settings.WHITE)
        surface.blit(txt, (r.centerx - txt.get_width() // 2,
                            r.centery - txt.get_height() // 2))

    # ------------------------------------------------------------------
    # Dialogue passthrough
    # ------------------------------------------------------------------
    @property
    def dialogue(self) -> DialogueBox:
        return self._dialogue

    def show_message(self, text: str) -> None:
        self._dialogue.show([text])

    def show_messages(self, lines: list[str]) -> None:
        self._dialogue.show(lines)

    def advance_dialogue(self) -> bool:
        return self._dialogue.advance()

    @property
    def dialogue_finished(self) -> bool:
        return self._dialogue.is_finished
