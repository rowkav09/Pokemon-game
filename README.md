# Pokémon Adventure

A fully-featured, modular 2D top-down Pokémon-style game built with Python and Pygame.

## Features

- **Modular architecture** — separated into `game/`, `entities/`, `world/`, `battle/`, `ui/`, and `data/` packages
- **State machine** — Main Menu → World → Dialogue → Battle → Inventory → Pause
- **Delta-time game loop** — consistent speed at any framerate
- **Player system** — 4-direction movement, animated sprites, collision detection, interaction system
- **World system** — tile-based scrolling map with camera follow, NPC placement
- **Pokémon system** — 24 Pokémon loaded from JSON with full stat calculation (Gen III formula)
- **Turn-based battle system** — speed-based turn order, type effectiveness, critical hits, status effects, EXP/level-up
- **18-type chart** — full type effectiveness system (super-effective, not-very-effective, immune)
- **Move system** — 45+ moves loaded from JSON with PP tracking and secondary effects
- **NPC system** — dialogue NPCs and trainer NPCs that trigger battles
- **Inventory system** — Poké Balls, Potions, Revives, status cures
- **Catch minigame** — timing-based throw ring that boosts/reduces catch chance
- **Pokédex menu** — tracks Seen vs Caught with completion percentage and stat cards
- **Trainer progression** — trainer EXP/levels unlock stronger balls and tougher zones
- **Save / Load** — JSON save files storing player position, team, inventory, and progress
- **Battle UI** — HP bars, EXP bars, move menu, type badges, status indicators
- **Dialogue box** — typing-effect character-by-character text reveal

## Requirements

- Python 3.10+
- [Pygame](https://www.pygame.org/) (`pip install pygame`)

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/rowkav09/Pokemon-game.git
   cd Pokemon-game
   ```

2. Install dependencies:
   ```bash
   pip install pygame
   ```

3. Run the game:
   ```bash
   python main.py
   ```

## Controls

### Overworld

| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move |
| ENTER / E | Interact with NPC or start battle |
| SPACE | Advance dialogue |
| I / TAB | Open bag/inventory |
| P | Open Pokédex |
| ESC | Pause menu |

### Battle

| Key | Action |
|-----|--------|
| Arrow keys / WASD | Navigate menus |
| ENTER / SPACE | Confirm selection |
| ESC | Go back |
| SPACE (while throwing ball) | Trigger catch minigame throw |

## Project Structure

```
Pokemon-game/
├── main.py                     # Entry point
├── settings.py                 # Global constants and configuration
│
├── game/
│   ├── game.py                 # Main Game class (loop, state dispatch)
│   ├── state_manager.py        # Enum-based state machine
│   └── asset_loader.py         # Centralised asset caching
│
├── entities/
│   ├── player.py               # Player character
│   ├── pokemon.py              # PokemonData, PokemonInstance, PokemonRegistry
│   └── npc.py                  # NPC + TrainerNPC classes
│
├── world/
│   ├── tilemap.py              # TileMap + Camera
│   ├── map_loader.py           # JSON / TMX map loading
│   └── collision.py            # AABB collision helpers
│
├── battle/
│   ├── battle_system.py        # Turn-based battle logic (state machine)
│   ├── battle_ui.py            # Battle screen renderer
│   ├── damage_calculator.py    # Gen-III damage formula + status effects
│   ├── move.py                 # Move / MoveInstance / MoveRegistry
│   └── type_chart.py           # 18-type effectiveness chart
│
├── ui/
│   ├── dialogue_box.py         # Typing-effect dialogue box
│   ├── health_bar.py           # Animated HP and EXP bars
│   └── menus.py                # Main menu, pause, battle action, inventory menus
│
├── data/
│   ├── pokemon.json            # 24 Pokémon species definitions
│   ├── moves.json              # 45+ move definitions
│   ├── items.json              # Item definitions
│   ├── trainers.json           # NPC / trainer definitions
│   └── map.json                # Default world map data
│
├── assets/
│   ├── sprites/                # (place custom sprites here)
│   ├── tiles/                  # (place custom tile sheets here)
│   ├── sounds/                 # (place .wav / .ogg sound effects here)
│   └── music/                  # (place .mp3 / .ogg music tracks here)
│
└── images/                     # Existing sprite sheets (reused)
    ├── trainer_sheet.png
    ├── 3d_starter_sheet.png
    └── pokeball.png
```

## Adding Content

### New Pokémon
Edit `data/pokemon.json` — add an entry with `id`, `name`, `types`, `base_stats`, and a `sprite_index` pointing to the correct frame in `images/3d_starter_sheet.png`.

### New Moves
Edit `data/moves.json` — add a move with `name`, `type`, `power`, `accuracy`, `pp`, `category`, and optional `effect`.

### New Maps
Edit `data/map.json` or create a new JSON file.  Tiled `.tmx` maps are supported if `pytmx` is installed.

### Audio
Drop `.ogg` / `.mp3` / `.wav` files into `assets/sounds/` and `assets/music/`.  Play them via `loader.play_sound(path)` or `loader.play_music(path)`.

## Credits

Original project by [bubse](https://github.com/bubse).  
Restructured and expanded by the contributors to this repository.
