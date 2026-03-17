"""
settings.py — Global game constants and configuration.
All magic numbers live here; nothing else should hard-code them.
"""

# ---------------------------------------------------------------------------
# Window
# ---------------------------------------------------------------------------
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 700
FPS = 60
TITLE = "Pokémon Adventure"

# ---------------------------------------------------------------------------
# Tile / world
# ---------------------------------------------------------------------------
TILE_SIZE = 32          # logical tile size in pixels
CAMERA_LERP = 0.08      # camera smoothing (0 = instant, 1 = no movement)

# ---------------------------------------------------------------------------
# Player sprite-sheet layout
# ---------------------------------------------------------------------------
PLAYER_SPEED = 200      # pixels per second
PLAYER_WIDTH = 120
PLAYER_HEIGHT = 140
PLAYER_FRAME_WIDTH = 121
PLAYER_FRAME_HEIGHT = 126
PLAYER_FRAME_OFFSET_X = 177
PLAYER_FRAME_OFFSET_Y = 45
PLAYER_ANIM_SPEED = 8   # animation frames per second

# ---------------------------------------------------------------------------
# Wild Pokémon
# ---------------------------------------------------------------------------
POKEMON_FRAME_WIDTH = 210
POKEMON_FRAME_HEIGHT = 228
POKEMON_DISPLAY_WIDTH = 90
POKEMON_DISPLAY_HEIGHT = 100
WILD_POKEMON_COUNT = 5  # number on the overworld at once
WILD_POKEMON_SPEED_MIN = 0.05
WILD_POKEMON_SPEED_MAX = 0.20

# ---------------------------------------------------------------------------
# Battle
# ---------------------------------------------------------------------------
BATTLE_PLAYER_SPRITE_POS = (80, 350)    # position of player pokémon sprite
BATTLE_ENEMY_SPRITE_POS = (520, 120)    # position of enemy pokémon sprite
BATTLE_PLAYER_HUD_POS = (380, 320)      # player info box (bottom right)
BATTLE_ENEMY_HUD_POS = (30, 40)         # enemy info box (top left)
BATTLE_TEXT_BOX_RECT = (0, 480, 800, 220)
MOVES_PER_POKEMON = 4
BASE_CATCH_RATE = 0.45  # base probability to catch a wild Pokémon

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
WHITE       = (255, 255, 255)
BLACK       = (0,   0,   0  )
RED         = (220,  50,  50)
GREEN       = ( 50, 200,  50)
BLUE        = ( 50,  50, 220)
YELLOW      = (255, 220,  50)
GRAY        = (100, 100, 100)
DARK_GRAY   = ( 40,  40,  40)
LIGHT_GRAY  = (180, 180, 180)

# UI chrome
UI_BG        = ( 30,  30,  30)
UI_BORDER    = ( 80,  80,  80)
UI_TEXT      = (255, 255, 255)
UI_HIGHLIGHT = (255, 220,  50)

# HP bar colours (thresholds applied in health_bar.py)
HP_GREEN    = ( 50, 205,  50)
HP_YELLOW   = (220, 200,  50)
HP_RED      = (220,  50,  50)

# EXP bar
EXP_BLUE    = ( 60, 120, 255)

# Dialogue box
DIALOGUE_BG      = ( 20,  20,  20)
DIALOGUE_BORDER  = (200, 200, 200)
DIALOGUE_TEXT    = (255, 255, 255)
DIALOGUE_SPEED   = 40   # characters per second for typing effect

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
IMAGES_DIR = "images"
MAPS_DIR   = "maps"
DATA_DIR   = "data"
ASSETS_DIR = "assets"

SAVE_FILE  = "save_data.json"

# ---------------------------------------------------------------------------
# Audio (volume 0.0-1.0)
# ---------------------------------------------------------------------------
MUSIC_VOLUME = 0.5
SFX_VOLUME   = 0.7
