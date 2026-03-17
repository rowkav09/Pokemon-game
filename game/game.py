"""
game/game.py — Main Game class.

Owns the Pygame window, clock, and top-level update/draw dispatch.
Delegates all logic to the active game state handler inside the loop.
"""

from __future__ import annotations

import json
import math
import os
import random
import sys

import pygame

import settings
from game.state_manager import StateManager, GameState
from game.asset_loader   import loader
from entities.player     import Player
from entities.npc        import load_npcs, TrainerNPC
from entities.pokemon    import PokemonRegistry, PokemonInstance
from world.tilemap       import TileMap
from world.map_loader    import load_map_json, build_tilemap
from world.collision     import npc_player_interaction, pokemon_encounter_check
from battle.battle_system import BattleSystem, BattlePhase, BattleAction
from battle.battle_ui    import BattleUI
from battle.move         import MoveRegistry
from ui.catch_minigame   import CatchMinigame
from ui.dialogue_box     import DialogueBox
from ui.menus            import (MainMenu, PauseMenu, BattleActionMenu,
                                  MoveSelectMenu, InventoryMenu, PartyMenu)
from ui.pokedex_ui       import PokedexUI


class Game:
    """
    Central game object.  One instance for the entire session.

    Game States
    -----------
    MAIN_MENU  → handled by MainMenu
    WORLD      → player roams the overworld
    DIALOGUE   → dialogue box is shown
    BATTLE     → BattleSystem + BattleUI
    INVENTORY  → InventoryMenu
    PAUSE      → PauseMenu overlay
    GAME_OVER  → "blacked out" screen
    """

    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error:
            pass

        self.screen = pygame.display.set_mode(
            (settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
        pygame.display.set_caption(settings.TITLE)
        self.clock  = pygame.time.Clock()

        # Registries (singletons, loaded once)
        self._pokemon_reg = PokemonRegistry.instance()
        self._move_reg    = MoveRegistry.instance()

        # State machine
        self.states  = StateManager(GameState.MAIN_MENU)

        # Shared objects (created fresh per session)
        self.player:        Player | None   = None
        self.tilemap:       TileMap | None  = None
        self.npcs:          list           = []
        self.wild_pokemon:  list[dict]      = []
        self._zones:        list[dict]      = []
        self._current_zone_name: str = "Meadow"
        self._encounter_cooldown = 0.0

        # Battle (trainer battles only — wild encounters use direct-catch)
        self._battle:       BattleSystem | None = None
        self._battle_ui:    BattleUI             = BattleUI()
        self._battle_results: list              = []
        self._battle_result_idx: int            = 0
        self._battle_phase_label: str           = ""
        self._caught_pokemon: PokemonInstance | None = None
        self._trainer_npc: TrainerNPC | None    = None

        # Direct wild-Pokémon catch (no battle)
        self._wild_encounter: dict | None = None  # the overworld entry being caught

        # UI widgets
        self._main_menu      = MainMenu()
        self._pause_menu     = PauseMenu()
        self._battle_menu    = BattleActionMenu()
        self._move_menu      = MoveSelectMenu()
        self._inventory_menu = InventoryMenu()
        self._party_menu     = PartyMenu()
        self._pokedex_ui     = PokedexUI()
        self._dialogue       = DialogueBox()
        self._dialogue_cb    = None   # callable called when dialogue closes
        self._catch_minigame: CatchMinigame | None = None
        self._pending_catch_item: dict | None = None

        # Game over overlay
        self._game_over_timer = 0.0

    # ==================================================================
    # Main loop
    # ==================================================================
    def run(self) -> None:
        while True:
            dt = self.clock.tick(settings.FPS) / 1000.0
            dt = min(dt, 0.05)  # cap at 50 ms to avoid spiral-of-death

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self._quit()
                self._handle_event(event)

            self._update(dt)
            self._draw()
            pygame.display.flip()

    # ==================================================================
    # Event dispatch
    # ==================================================================
    def _handle_event(self, event: pygame.event.Event) -> None:
        state = self.states.state

        if state == GameState.MAIN_MENU:
            result = self._main_menu.handle_event(event)
            if result == "New Game":
                self._new_game()
            elif result == "Continue":
                if not self._load_game():
                    self._new_game()
            elif result == "Quit":
                self._quit()

        elif state == GameState.PAUSE:
            result = self._pause_menu.handle_event(event)
            if result == "Resume":
                self.states.pop()
            elif result == "Pokémon":
                self.states.push(GameState.PARTY)
            elif result == "Bag":
                self._open_inventory()
            elif result == "Pokédex":
                self._open_pokedex()
            elif result == "Save":
                self._save_game()
                self._show_dialogue(["Game saved!"])
            elif result == "Quit to Title":
                self.states.change(GameState.MAIN_MENU)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.states.pop()

        elif state == GameState.WORLD:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.states.push(GameState.PAUSE)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_e:
                    self._try_interact()
                elif event.key == pygame.K_i or event.key == pygame.K_TAB:
                    self._open_inventory()
                elif event.key == pygame.K_p:
                    self._open_pokedex()

        elif state == GameState.DIALOGUE:
            if event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
                done = self._dialogue.advance()
                if done:
                    self.states.pop()
                    if callable(self._dialogue_cb):
                        cb = self._dialogue_cb
                        self._dialogue_cb = None
                        cb()

        elif state == GameState.BATTLE:
            self._handle_battle_event(event)

        elif state == GameState.CATCH_MINIGAME:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if self._catch_minigame:
                        self._catch_minigame.throw()

        elif state == GameState.INVENTORY:
            result = self._inventory_menu.handle_event(event)
            if result == "CLOSE":
                self.states.pop()
            elif isinstance(result, dict):
                self._use_inventory_item(result)

        elif state == GameState.POKEDEX:
            total = len(self._pokemon_reg.all_pokemon())
            result = self._pokedex_ui.handle_event(event, total)
            if result == "CLOSE":
                self.states.pop()

        elif state == GameState.PARTY:
            result = self._party_menu.handle_event(event, len(self.player.team))
            if result == "CLOSE":
                self.states.pop()

        elif state == GameState.GAME_OVER:
            if event.type == pygame.KEYDOWN:
                self.states.change(GameState.MAIN_MENU)

    def _handle_battle_event(self, event: pygame.event.Event) -> None:
        if self._battle is None:
            return

        phase = self._battle.phase

        # During ANIMATING: advance messages on key press
        if phase in (BattlePhase.ANIMATING, BattlePhase.INTRO,
                     BattlePhase.LEVEL_UP, BattlePhase.WIN, BattlePhase.LOSE):
            if event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
                self._advance_battle_message()
            return

        if phase == BattlePhase.PLAYER_ACTION:
            result = self._battle_menu.handle_event(event)
            if result == "FIGHT":
                self._battle.phase = BattlePhase.MOVE_SELECT
                self._move_menu.set_moves(self._battle.player_pokemon.moves)
            elif result == "BAG":
                self._open_bag_in_battle()
            elif result == "POKÉMON":
                pass  # TODO: team switch menu
            elif result == "RUN":
                self._submit_battle_action(BattleAction(kind="run"))

        elif phase == BattlePhase.MOVE_SELECT:
            result = self._move_menu.handle_event(event)
            if result == "BACK":
                self._battle.phase = BattlePhase.PLAYER_ACTION
            elif result is not None:
                self._submit_battle_action(BattleAction(kind="move", move=result))

    # ==================================================================
    # Update dispatch
    # ==================================================================
    def _update(self, dt: float) -> None:
        state = self.states.state

        if state == GameState.WORLD:
            self._update_world(dt)

        elif state == GameState.DIALOGUE:
            self._dialogue.update(dt)

        elif state == GameState.BATTLE:
            self._update_battle(dt)

        elif state == GameState.CATCH_MINIGAME and self._catch_minigame:
            self._catch_minigame.update(dt)
            if self._catch_minigame.finished:
                self._resolve_catch_minigame()

        elif state == GameState.GAME_OVER:
            self._game_over_timer += dt

    def _update_world(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys, self.tilemap.world_rect)
        self.tilemap.update(self.player.rect)
        self._encounter_cooldown = max(0.0, self._encounter_cooldown - dt)
        zone = self._zone_for_point(self.player.rect.centerx, self.player.rect.centery)
        if zone:
            self._current_zone_name = zone.get("name", "Unknown")
            if self._encounter_cooldown <= 0 and self.player._moving:
                if random.random() < zone.get("encounter_rate", 0.0009):
                    self._encounter_cooldown = 2.0
                    wild = self._make_zone_wild_entry(zone, self.player.rect.centerx, self.player.rect.centery)
                    self._start_wild_catch(wild)
                    return

        # Move wild Pokémon
        for p in self.wild_pokemon:
            if p.get("moving", True):
                p["x"] += p["dx"] * dt * 60
                p["y"] += p["dy"] * dt * 60
                # Bounce off world boundaries
                if p["x"] < 80 or p["x"] > self.tilemap.world_width - 80:
                    p["dx"] *= -1
                if p["y"] < 80 or p["y"] > self.tilemap.world_height - 80:
                    p["dy"] *= -1
                # Random direction changes
                if random.random() < 0.005:
                    angle = random.uniform(0, 2 * math.pi)
                    speed = random.uniform(settings.WILD_POKEMON_SPEED_MIN,
                                          settings.WILD_POKEMON_SPEED_MAX)
                    p["dx"] = math.cos(angle) * speed
                    p["dy"] = math.sin(angle) * speed

    def _update_battle(self, dt: float) -> None:
        if self._battle is None:
            return
        self._battle_ui.update(
            dt,
            self._battle.player_pokemon,
            self._battle.active_enemy,
        )

    # ==================================================================
    # Draw dispatch
    # ==================================================================
    def _draw(self) -> None:
        state = self.states.state

        if state == GameState.MAIN_MENU:
            self._main_menu.draw(self.screen)

        elif state in (GameState.WORLD, GameState.DIALOGUE, GameState.PAUSE,
                       GameState.INVENTORY, GameState.POKEDEX, GameState.PARTY):
            self._draw_world()
            if state == GameState.DIALOGUE:
                self._dialogue.draw(self.screen)
            elif state == GameState.PAUSE:
                self._pause_menu.draw(self.screen)
            elif state == GameState.INVENTORY:
                self._inventory_menu.draw(self.screen)
            elif state == GameState.POKEDEX:
                self._draw_pokedex()
            elif state == GameState.PARTY:
                self._party_menu.draw(self.screen, self.player.team)
            self._draw_world_hud()

        elif state in (GameState.BATTLE, GameState.CATCH_MINIGAME):
            if self._battle is not None:
                self._draw_battle()
            else:
                # Direct catch from the overworld — show world as background
                self._draw_world()
                self._draw_world_hud()
            if state == GameState.CATCH_MINIGAME and self._catch_minigame:
                if self._wild_encounter is not None:
                    pokemon_name   = self._wild_encounter["instance"].name
                    pokemon_surface = self._wild_encounter.get("frame")
                elif self._battle is not None:
                    pokemon_name   = self._battle.active_enemy.name
                    pokemon_surface = None
                else:
                    pokemon_name   = "Pokémon"
                    pokemon_surface = None
                ball_name = (self._pending_catch_item or {}).get("name", "Poké Ball")
                self._catch_minigame.draw(
                    self.screen, pokemon_name, ball_name, pokemon_surface)

        elif state == GameState.GAME_OVER:
            self._draw_game_over()

    def _draw_world(self) -> None:
        self.tilemap.draw(self.screen)

        cam = self.tilemap.camera.offset

        # Draw wild Pokémon
        for p in self.wild_pokemon:
            sx, sy = (p["x"] - cam[0], p["y"] - cam[1])
            frame: pygame.Surface = p["frame"]
            self.screen.blit(frame, (round(sx), round(sy)))

        # Draw NPCs
        for npc in self.npcs:
            npc.draw(self.screen, cam)

        # Draw player
        self.player.draw(self.screen, cam)

    def _draw_world_hud(self) -> None:
        fnt = loader.font("couriernew", 16, bold=True)
        # Pokéball count
        pb_count = self.player.item_count("pokeball")
        txt = fnt.render(f"Poké Balls: {pb_count}", True, settings.WHITE)
        pill = pygame.Surface((txt.get_width() + 12, txt.get_height() + 6), pygame.SRCALPHA)
        pill.fill((0, 0, 0, 150))
        self.screen.blit(pill, (8, 8))
        self.screen.blit(txt, (14, 11))

        zone_txt = fnt.render(f"Zone: {self._current_zone_name}", True, settings.WHITE)
        zpill = pygame.Surface((zone_txt.get_width() + 12, zone_txt.get_height() + 6), pygame.SRCALPHA)
        zpill.fill((0, 0, 0, 150))
        self.screen.blit(zpill, (8, 38))
        self.screen.blit(zone_txt, (14, 41))

        trainer_txt = fnt.render(f"Trainer Lv.{self.player.trainer_level}", True, settings.WHITE)
        tpill = pygame.Surface((trainer_txt.get_width() + 12, trainer_txt.get_height() + 6), pygame.SRCALPHA)
        tpill.fill((0, 0, 0, 150))
        self.screen.blit(tpill, (8, 68))
        self.screen.blit(trainer_txt, (14, 71))

        # Controls hint
        hint_fnt = loader.font("couriernew", 13)
        hints = [
            "ARROWS/WASD: Move",
            "E/ENTER: Throw Ball at nearby Pokémon",
            "I/TAB: Bag",
            "P: Pokédex",
            "ESC: Pause",
        ]
        for i, h in enumerate(hints):
            hs = hint_fnt.render(h, True, settings.LIGHT_GRAY)
            self.screen.blit(hs, (settings.SCREEN_WIDTH - hs.get_width() - 8,
                                   settings.SCREEN_HEIGHT - 18 - i * 16))

    def _draw_battle(self) -> None:
        if self._battle is None:
            return
        phase_label = self._battle.phase.name
        self._battle_ui.draw(
            self.screen,
            self._battle.player_pokemon,
            self._battle.active_enemy,
            phase=phase_label,
            move_menu=self._move_menu if self._battle.phase == BattlePhase.MOVE_SELECT else None,
        )
        # Action menu
        if self._battle.phase == BattlePhase.PLAYER_ACTION:
            self._battle_menu.draw(self.screen)
        # Advance hint
        if self._battle.phase in (BattlePhase.ANIMATING, BattlePhase.WIN,
                                   BattlePhase.LOSE, BattlePhase.INTRO):
            if self._battle_ui.dialogue_finished:
                hint = loader.font("couriernew", 16).render(
                    "Press SPACE to continue", True, settings.LIGHT_GRAY)
                self.screen.blit(hint, (
                    settings.SCREEN_WIDTH // 2 - hint.get_width() // 2,
                    settings.SCREEN_HEIGHT - 28))

    def _draw_game_over(self) -> None:
        self.screen.fill((0, 0, 0))
        fnt  = loader.font("couriernew", 48, bold=True)
        txt  = fnt.render("YOU BLACKED OUT!", True, settings.RED)
        self.screen.blit(txt, (settings.SCREEN_WIDTH // 2 - txt.get_width() // 2,
                                settings.SCREEN_HEIGHT // 2 - txt.get_height() // 2))
        hint = loader.font("couriernew", 20).render(
            "Press any key to return to title", True, settings.GRAY)
        self.screen.blit(hint, (settings.SCREEN_WIDTH // 2 - hint.get_width() // 2,
                                 settings.SCREEN_HEIGHT // 2 + 60))

    # ==================================================================
    # Game lifecycle
    # ==================================================================
    def _new_game(self) -> None:
        """Initialise a fresh save and enter the world."""
        self.player  = Player()
        self._load_world_map()

        # Give the player a starter Pokémon (Bulbasaur, id=1)
        starter = self._pokemon_reg.make_instance(1, level=5)
        self.player.team = [starter]

        self.npcs        = load_npcs()
        self.wild_pokemon = self._spawn_wild_pokemon()

        self.states.change(GameState.WORLD)

        # Intro dialogue
        self._show_dialogue([
            "Welcome to Pokémon Adventure!",
            "Use arrow keys or WASD to move.",
            "Walk up to a wild Pokémon and press",
            "ENTER or E to throw a Poké Ball!",
            "Open your Bag (I) to pick which ball to use.",
            "Good luck catching them all!",
        ])

    def _load_game(self) -> bool:
        if not os.path.isfile(settings.SAVE_FILE):
            return False
        try:
            with open(settings.SAVE_FILE, encoding="utf-8") as f:
                data = json.load(f)
            self.player      = Player.from_dict(data["player"])
            self._load_world_map()
            self.npcs        = load_npcs()
            # Restore defeated trainers
            for npc_state in data.get("npcs", []):
                for npc in self.npcs:
                    if npc.id == npc_state["id"] and hasattr(npc, "defeated"):
                        npc.defeated = npc_state.get("defeated", False)
            self.wild_pokemon = self._spawn_wild_pokemon()
            self.states.change(GameState.WORLD)
            self._show_dialogue(["Welcome back, Trainer!"])
            return True
        except Exception:  # noqa: BLE001
            return False

    def _save_game(self) -> None:
        npc_states = [npc.to_dict() for npc in self.npcs]
        data = {
            "player": self.player.to_dict(),
            "npcs":   npc_states,
        }
        with open(settings.SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load_world_map(self) -> None:
        map_path = os.path.join("data", "map.json")
        map_data = load_map_json(map_path)
        self.tilemap = build_tilemap(map_data)
        self._zones = self._load_zone_data(map_path)
        self._current_zone_name = self._zones[0]["name"] if self._zones else map_data.name

    @staticmethod
    def _load_zone_data(map_path: str) -> list[dict]:
        if not os.path.isfile(map_path):
            return []
        with open(map_path, encoding="utf-8") as f:
            raw = json.load(f)
        zones = []
        for z in raw.get("zones", []):
            zones.append({
                "id": z.get("id", "meadow"),
                "name": z.get("name", "Meadow"),
                "rect": pygame.Rect(*z.get("rect", [0, 0, 0, 0])),
                "pokemon_ids": z.get("pokemon_ids", []),
                "level_min": z.get("level_min", 3),
                "level_max": z.get("level_max", 8),
                "encounter_rate": z.get("encounter_rate", 0.001),
            })
        return zones

    # ==================================================================
    # Wild Pokémon spawning
    # ==================================================================
    def _spawn_wild_pokemon(self) -> list[dict]:
        sheet_path = os.path.join(settings.IMAGES_DIR, "3d_starter_sheet.png")

        pokemon_list: list[dict] = []
        for _ in range(settings.WILD_POKEMON_COUNT):
            zone = random.choice(self._zones) if self._zones else None
            if zone and zone["pokemon_ids"]:
                pid = random.choice(zone["pokemon_ids"])
                level = random.randint(zone["level_min"], zone["level_max"])
                pdata = self._pokemon_reg.get_by_id(pid)
            else:
                pdata = random.choice(self._pokemon_reg.all_pokemon())
                level = random.randint(3, 8)
            inst    = self._pokemon_reg.make_wild(pdata.id, level)

            idx  = pdata.sprite_index
            col  = idx % 6
            row  = idx // 6
            rect = pygame.Rect(
                col * settings.POKEMON_FRAME_WIDTH,
                row * settings.POKEMON_FRAME_HEIGHT,
                settings.POKEMON_FRAME_WIDTH,
                settings.POKEMON_FRAME_HEIGHT,
            )
            frame = loader.sub_image(
                sheet_path, rect,
                scale=(settings.POKEMON_DISPLAY_WIDTH,
                       settings.POKEMON_DISPLAY_HEIGHT),
            )
            if random.randint(0, 1):
                frame = pygame.transform.flip(frame, True, False)

            angle  = random.uniform(0, 2 * math.pi)
            speed  = random.uniform(settings.WILD_POKEMON_SPEED_MIN,
                                    settings.WILD_POKEMON_SPEED_MAX)
            if zone:
                zr = zone["rect"]
                wx = random.randint(zr.left + 20, max(zr.left + 21, zr.right - 20))
                wy = random.randint(zr.top + 20, max(zr.top + 21, zr.bottom - 20))
            else:
                wx = random.randint(120, self.tilemap.world_width - 120)
                wy = random.randint(120, self.tilemap.world_height - 120)
            pokemon_list.append({
                "instance": inst,
                "x":  wx, "y":  wy,
                "dx": math.cos(angle) * speed,
                "dy": math.sin(angle) * speed,
                "frame": frame,
                "moving": True,
            })
        return pokemon_list

    # ==================================================================
    # Interaction
    # ==================================================================
    def _try_interact(self) -> None:
        if self.player is None:
            return
        ir = self.player.interaction_rect

        # Check NPC interaction
        npc = npc_player_interaction(self.player.rect, ir, self.npcs)
        if npc:
            lines = npc.interact(self.player)
            if isinstance(npc, TrainerNPC) and not npc.defeated:
                self._show_dialogue(lines, speaker=npc.name,
                                    callback=lambda: self._start_trainer_battle(npc))
            else:
                self._show_dialogue(lines, speaker=npc.name)
            return

        # Check wild Pokémon encounter — throw a Poké Ball directly (no battle)
        enc = pokemon_encounter_check(self.player.rect, self.wild_pokemon, radius=80)
        if enc:
            self._start_wild_catch(enc)

    # ==================================================================
    # Battle: start
    # ==================================================================
    def _start_wild_battle(self, wild_entry: dict) -> None:
        if not self.player.has_usable_pokemon:
            self._show_dialogue(["You have no Pokémon to battle with!"])
            return

        wild_inst: PokemonInstance = wild_entry["instance"]
        wild_inst.reset_battle_state()
        self.player.see_pokemon(wild_inst.data.id)

        self._battle    = BattleSystem(
            player_team   = self.player.team,
            enemy_pokemon = wild_inst,
            is_wild       = True,
        )
        self._caught_pokemon = None
        self._trainer_npc    = None

        self.states.push(GameState.BATTLE)
        msgs = self._battle.start()
        self._battle_ui.show_messages(msgs)
        self._battle_ui.update_hp_instant(
            self._battle.player_pokemon, self._battle.active_enemy)
        self._wild_entry_in_battle = wild_entry

    def _start_trainer_battle(self, npc: TrainerNPC) -> None:
        if not self.player.has_usable_pokemon:
            self._show_dialogue(["You have no Pokémon to battle with!"])
            return

        trainer_team = npc.build_team(self._pokemon_reg)
        for tp in trainer_team:
            self.player.see_pokemon(tp.data.id)
        self._battle = BattleSystem(
            player_team   = self.player.team,
            enemy_pokemon = trainer_team[0],
            is_wild       = False,
            trainer       = npc,
            trainer_team  = trainer_team,
        )
        self._trainer_npc = npc
        self.player.see_pokemon(self._battle.active_enemy.data.id)

        self.states.push(GameState.BATTLE)
        msgs = self._battle.start()
        self._battle_ui.show_messages(msgs)
        self._battle_ui.update_hp_instant(
            self._battle.player_pokemon, self._battle.active_enemy)

    # ==================================================================
    # Wild catch: direct Poké Ball throw (no battle)
    # ==================================================================
    def _start_wild_catch(self, wild_entry: dict) -> None:
        """Begin a direct Poké Ball throw at a wild Pokémon (no battle)."""
        wild_inst = wild_entry["instance"]
        self.player.see_pokemon(wild_inst.data.id)

        if len(self.player.team) >= 6:
            self._show_dialogue([
                f"A wild {wild_inst.name} appeared!",
                "Your party is full — release a Pokémon first!",
            ])
            return

        ball = self._get_best_available_ball()
        if ball is None:
            self._show_dialogue([
                f"A wild {wild_inst.name} appeared!",
                "You have no Poké Balls!",
                "Visit a shop to stock up.",
            ])
            return

        if not self.player.use_item(ball["id"]):
            self._show_dialogue([
                f"A wild {wild_inst.name} appeared!",
                "You have no Poké Balls left!",
            ])
            return

        self._wild_encounter   = wild_entry
        self._pending_catch_item = dict(ball)
        self._catch_minigame   = CatchMinigame()
        self.states.push(GameState.CATCH_MINIGAME)

    def _get_best_available_ball(self) -> dict | None:
        """Return the best Poké Ball the player currently has, or None."""
        try:
            with open(os.path.join("data", "items.json"), encoding="utf-8") as f:
                all_items: list[dict] = json.load(f)
        except Exception:  # noqa: BLE001
            return None
        for bid in ("ultra_ball", "great_ball", "pokeball"):
            if bid in self.player.unlocked_balls and self.player.item_count(bid) > 0:
                for item in all_items:
                    if item["id"] == bid:
                        entry = dict(item)
                        entry["quantity"] = self.player.item_count(bid)
                        return entry
        return None

    def _resolve_direct_catch(self, ball: dict) -> None:
        """Handle the outcome of a direct (no-battle) catch attempt."""
        wild_entry = self._wild_encounter
        self._wild_encounter = None
        if wild_entry is None:
            return

        wild_inst = wild_entry["instance"]
        catch_p = self._compute_catch_probability(wild_inst, ball)
        shakes   = max(0, min(3, int(catch_p * 4)))
        msgs = [f"You threw a {ball.get('name', 'Poké Ball')} at {wild_inst.name}!"]
        msgs.extend(["...shake...", "...shake...", "...shake..."][:shakes])

        if random.random() < catch_p:
            msgs.append(f"Gotcha!  {wild_inst.name} was caught!")
            if len(self.player.team) < 6:
                self.player.team.append(wild_inst)
                self.player.catch_pokemon(wild_inst.data.id)
                msgs.append(f"{wild_inst.name} joined your party!")
            else:
                msgs.append("But your party is full!")
            try:
                self.wild_pokemon.remove(wild_entry)
            except ValueError:
                pass
            msgs.extend(self.player.gain_trainer_exp(35))
        else:
            msgs.append(f"{wild_inst.name} broke free and fled!")
            try:
                self.wild_pokemon.remove(wild_entry)
            except ValueError:
                pass

        self._show_dialogue(msgs)

    @staticmethod
    def _compute_catch_probability(wild_inst: "PokemonInstance", ball: dict) -> float:
        """Calculate catch probability for a direct Poké Ball throw.

        Because the wild Pokémon is at full HP (no damage dealt before throwing),
        the HP factor is fixed below 1.0 to keep catches balanced yet achievable.
        """
        base_rate  = wild_inst.data.catch_rate / 255.0
        # Wild Pokémon hasn't been weakened — use a moderate factor
        # (same formula as BattleSystem but capped at full-health value ≈ 0.33;
        #  we use 0.55 to keep direct catches reasonably fair)
        hp_factor  = 0.55
        skill_bonus = ball.get("catch_skill_bonus", 1.0)
        chance = (base_rate * hp_factor
                  * ball.get("catch_multiplier", 1.0)
                  * settings.BASE_CATCH_RATE
                  * skill_bonus)
        return max(0.05, min(0.90, chance))

    # ==================================================================
    # Battle: action submission & message draining
    # ==================================================================
    def _submit_battle_action(self, action: BattleAction) -> None:
        self._battle.submit_player_action(action)
        self._battle_results    = self._battle.execute_turn()
        self._battle_result_idx = 0
        self._show_next_battle_result()

    def _show_next_battle_result(self) -> None:
        if self._battle_result_idx >= len(self._battle_results):
            # All results consumed — check final phase
            self._finish_battle_results()
            return
        result = self._battle_results[self._battle_result_idx]
        if result.messages:
            self._battle_ui.show_messages(result.messages)
        if result.shake_target:
            self._battle_ui.shake(result.shake_target)
        if result.flash_target:
            self._battle_ui.flash(result.flash_target)

    def _advance_battle_message(self) -> None:
        if not self._battle_ui.dialogue_finished:
            self._battle_ui.advance_dialogue()
            return
        self._battle_result_idx += 1
        if self._battle_result_idx < len(self._battle_results):
            self._show_next_battle_result()
        else:
            self._finish_battle_results()

    def _finish_battle_results(self) -> None:
        """Called when all pending battle results have been displayed."""
        if self._battle is None:
            return

        phase = self._battle.phase

        if phase == BattlePhase.WIN:
            extra_messages: list[str] = []
            # Pokémon was caught
            enemy = self._battle.active_enemy
            if self._battle.is_wild and self._battle.last_catch_success:
                caught = enemy
                # Add to team if room
                if len(self.player.team) < 6:
                    self.player.team.append(caught)
                    self.player.catch_pokemon(caught.data.id)
                    extra_messages.append(f"{caught.name} joined your party!")
                # Remove from overworld
                if hasattr(self, "_wild_entry_in_battle"):
                    try:
                        self.wild_pokemon.remove(self._wild_entry_in_battle)
                    except ValueError:
                        pass
                extra_messages.extend(self.player.gain_trainer_exp(35))
            # Trainer defeated
            if self._trainer_npc:
                self._trainer_npc.defeated = True
                extra_messages.extend(self.player.gain_trainer_exp(60))
                self._trainer_npc = None

            if not extra_messages:
                extra_messages.append("Battle ended!")
            self._end_battle(extra_messages)

        elif phase == BattlePhase.LOSE:
            # Heal all Pokémon to half HP
            for p in self.player.team:
                p.fainted    = False
                p.current_hp = max(1, p.max_hp // 2)
                p.status     = None
            self._end_battle(None)
            self.states.change(GameState.GAME_OVER)

    def _end_battle(self, extra_messages: list[str] | None) -> None:
        self._battle = None
        self.states.pop()   # return to WORLD
        if extra_messages:
            self._show_dialogue(extra_messages)

    # ==================================================================
    # Bag in battle
    # ==================================================================
    def _open_bag_in_battle(self) -> None:
        """Build item list and open inventory while in battle."""
        items = self._build_item_list(battle=True)
        self._inventory_menu.set_items(items)
        self.states.push(GameState.INVENTORY)
        # After returning, handle item use via _use_inventory_item
        self._inventory_is_battle = True

    def _open_inventory(self) -> None:
        items = self._build_item_list(battle=False)
        self._inventory_menu.set_items(items)
        self._inventory_is_battle = False
        self.states.push(GameState.INVENTORY)

    def _build_item_list(self, battle: bool) -> list[dict]:
        import json as _json
        path = os.path.join("data", "items.json")
        with open(path, encoding="utf-8") as f:
            all_items: list[dict] = _json.load(f)

        result = []
        for item in all_items:
            qty = self.player.item_count(item["id"])
            if battle and item.get("type") == "pokeball" and item["id"] not in self.player.unlocked_balls:
                continue
            if qty > 0:
                entry = dict(item)
                entry["quantity"] = qty
                if battle and item.get("type") == "pokeball" and self._battle:
                    chance = self._battle.get_catch_probability(entry)
                    entry["description"] = f"{entry.get('description', '')} (Catch ~{int(chance * 100)}%)"
                result.append(entry)
        return result

    def _open_pokedex(self) -> None:
        self.states.push(GameState.POKEDEX)

    def _draw_pokedex(self) -> None:
        entries = []
        for pdata in sorted(self._pokemon_reg.all_pokemon(), key=lambda p: p.id):
            seen = pdata.id in self.player.pokedex_seen
            caught = pdata.id in self.player.pokedex
            entries.append({
                "id": pdata.id,
                "name": pdata.name,
                "types": list(pdata.types),
                "stats": dict(pdata.base_stats),
                "seen": seen,
                "caught": caught,
                "flavor": f"A {', '.join(pdata.types).title()}-type Pokémon species.",
            })
        self._pokedex_ui.draw(
            self.screen,
            entries,
            seen_count=len(self.player.pokedex_seen),
            caught_count=len(self.player.pokedex),
        )

    def _start_catch_minigame(self, item: dict) -> None:
        self._pending_catch_item = dict(item)
        self._catch_minigame = CatchMinigame()
        self.states.push(GameState.CATCH_MINIGAME)

    def _resolve_catch_minigame(self) -> None:
        if not self._catch_minigame or not self._pending_catch_item:
            return
        item = dict(self._pending_catch_item)
        item["catch_skill_bonus"] = self._catch_minigame.skill_multiplier
        self._pending_catch_item = None
        self._catch_minigame     = None
        self.states.pop()

        if self._battle is not None:
            # In-battle catch (trainer battles use bag mid-fight)
            self._submit_battle_action(BattleAction(kind="item", item=item))
        elif self._wild_encounter is not None:
            # Direct overworld catch
            self._resolve_direct_catch(item)
        else:
            self._show_dialogue(["The throw missed!"])

    def _zone_for_point(self, x: int, y: int) -> dict | None:
        for zone in self._zones:
            if zone["id"] not in self.player.unlocked_zones:
                continue
            if zone["rect"].collidepoint(x, y):
                return zone
        return None

    def _make_zone_wild_entry(self, zone: dict, x: int, y: int) -> dict:
        options = zone.get("pokemon_ids") or [1]
        pid = random.choice(options)
        level = random.randint(zone.get("level_min", 3), zone.get("level_max", 8))
        inst = self._pokemon_reg.make_wild(pid, level)
        idx = inst.data.sprite_index
        col = idx % 6
        row = idx // 6
        frame = loader.sub_image(
            os.path.join(settings.IMAGES_DIR, "3d_starter_sheet.png"),
            pygame.Rect(
                col * settings.POKEMON_FRAME_WIDTH,
                row * settings.POKEMON_FRAME_HEIGHT,
                settings.POKEMON_FRAME_WIDTH,
                settings.POKEMON_FRAME_HEIGHT,
            ),
            scale=(settings.POKEMON_DISPLAY_WIDTH, settings.POKEMON_DISPLAY_HEIGHT),
        )
        return {
            "instance": inst,
            "x": float(x),
            "y": float(y),
            "dx": 0.0,
            "dy": 0.0,
            "frame": frame,
            "moving": False,
        }

    def _use_inventory_item(self, item: dict) -> None:
        iid = item["id"]
        if not self.player.use_item(iid):
            return

        if getattr(self, "_inventory_is_battle", False) and self._battle:
            self.states.pop()   # close inventory first
            if item.get("type") == "pokeball":
                self._start_catch_minigame(item)
            else:
                action = BattleAction(kind="item", item=item)
                self._submit_battle_action(action)
        else:
            self.states.pop()  # close inventory
            self._show_dialogue([f"Used {item['name']}."])

    # ==================================================================
    # Dialogue helpers
    # ==================================================================
    def _show_dialogue(self, lines: list[str],
                        speaker: str | None = None,
                        callback=None) -> None:
        self._dialogue.show(lines, speaker=speaker)
        self._dialogue_cb = callback
        if self.states.state != GameState.DIALOGUE:
            self.states.push(GameState.DIALOGUE)

    # ==================================================================
    # Utility
    # ==================================================================
    @staticmethod
    def _quit() -> None:
        pygame.quit()
        sys.exit()
