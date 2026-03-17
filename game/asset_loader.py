"""
game/asset_loader.py — Centralised asset loading with an in-memory cache.

All surfaces, fonts and sounds pass through here so they are loaded exactly
once even if requested from multiple modules.  Missing audio files are
silently skipped so the game can run in headless / no-audio environments.
"""

import os
import pygame

import settings


class AssetLoader:
    """Singleton-style loader; import the module-level ``loader`` instance."""

    def __init__(self):
        self._image_cache: dict[str, pygame.Surface]     = {}
        self._font_cache:  dict[tuple, pygame.font.Font] = {}
        self._sound_cache: dict[str, pygame.mixer.Sound] = {}
        self._music_cache: dict[str, str]                = {}   # path only, pygame streams music

    # ------------------------------------------------------------------
    # Images / Surfaces
    # ------------------------------------------------------------------
    def image(self, path: str, convert_alpha: bool = True) -> pygame.Surface:
        """Return a cached surface, loading from *path* on first access."""
        if path not in self._image_cache:
            surf = pygame.image.load(path)
            # convert_alpha / convert require a display mode to be set;
            # gracefully fall back to the raw surface when it isn't.
            try:
                self._image_cache[path] = (
                    surf.convert_alpha() if convert_alpha else surf.convert()
                )
            except pygame.error:
                self._image_cache[path] = surf
        return self._image_cache[path]

    def scaled_image(self, path: str, size: tuple[int, int],
                     convert_alpha: bool = True) -> pygame.Surface:
        """Return a cached surface pre-scaled to *size*."""
        key = (path, size)
        if key not in self._image_cache:
            base = self.image(path, convert_alpha)
            self._image_cache[key] = pygame.transform.scale(base, size)
        return self._image_cache[key]

    def sub_image(self, path: str, rect: pygame.Rect,
                  scale: tuple[int, int] | None = None) -> pygame.Surface:
        """Extract and optionally scale a sub-surface from a sprite sheet."""
        sheet  = self.image(path)
        # subsurface shares pixel data — copy so scaling doesn't corrupt cache
        sub    = sheet.subsurface(rect).copy()
        if scale:
            sub = pygame.transform.scale(sub, scale)
        return sub

    def preload_images(self, paths: list[str]) -> None:
        """Eagerly load a list of image paths."""
        for p in paths:
            self.image(p)

    # ------------------------------------------------------------------
    # Fonts
    # ------------------------------------------------------------------
    def font(self, name: str | None, size: int,
             bold: bool = False, italic: bool = False) -> pygame.font.Font:
        key = (name, size, bold, italic)
        if key not in self._font_cache:
            if name and os.path.isfile(name):
                f = pygame.font.Font(name, size)
            else:
                f = pygame.font.SysFont(name or "couriernew", size,
                                        bold=bold, italic=italic)
            self._font_cache[key] = f
        return self._font_cache[key]

    # ------------------------------------------------------------------
    # Sound effects
    # ------------------------------------------------------------------
    def sound(self, path: str) -> pygame.mixer.Sound | None:
        if path in self._sound_cache:
            return self._sound_cache[path]
        if not os.path.isfile(path):
            return None
        try:
            snd = pygame.mixer.Sound(path)
            snd.set_volume(settings.SFX_VOLUME)
            self._sound_cache[path] = snd
            return snd
        except pygame.error:
            return None

    def play_sound(self, path: str) -> None:
        snd = self.sound(path)
        if snd:
            snd.play()

    # ------------------------------------------------------------------
    # Music (streaming)
    # ------------------------------------------------------------------
    def play_music(self, path: str, loops: int = -1) -> None:
        if not os.path.isfile(path):
            return
        try:
            if pygame.mixer.music.get_busy() and self._music_cache.get("current") == path:
                return  # already playing
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(settings.MUSIC_VOLUME)
            pygame.mixer.music.play(loops)
            self._music_cache["current"] = path
        except pygame.error:
            pass

    def stop_music(self) -> None:
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def clear_cache(self) -> None:
        self._image_cache.clear()


# Module-level singleton — import this from other modules.
loader = AssetLoader()
