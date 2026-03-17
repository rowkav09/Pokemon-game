from __future__ import annotations

import math

import pygame

import settings
from game.asset_loader import loader


class CatchMinigame:
    def __init__(self):
        self.elapsed = 0.0
        self.duration = 4.0
        self._resolved = False
        self._accuracy = 0.0
        self._result_text = "Press SPACE to throw!"
        self._result_timer = 0.0

    def update(self, dt: float) -> None:
        if self._resolved:
            self._result_timer += dt
            return
        self.elapsed = min(self.duration, self.elapsed + dt)
        if self.elapsed >= self.duration:
            self._resolved = True
            self._accuracy = 0.0
            self._result_text = "Too slow! The throw was weak."

    def throw(self) -> bool:
        if self._resolved:
            return False
        radius = self.current_radius
        perfect = self.perfect_radius
        max_delta = 82.0
        delta = abs(radius - perfect)
        self._accuracy = max(0.0, 1.0 - (delta / max_delta))
        self._resolved = True
        if self._accuracy > 0.85:
            self._result_text = "Excellent throw!"
        elif self._accuracy > 0.55:
            self._result_text = "Nice throw!"
        elif self._accuracy > 0.25:
            self._result_text = "Okay throw..."
        else:
            self._result_text = "Poor throw!"
        return True

    @property
    def finished(self) -> bool:
        return self._resolved and self._result_timer >= 0.6

    @property
    def skill_multiplier(self) -> float:
        return 0.6 + self._accuracy * 0.8

    @property
    def current_radius(self) -> float:
        pulse = math.sin(self.elapsed * 5.0)
        return 24.0 + (pulse + 1.0) * 44.0

    @property
    def perfect_radius(self) -> float:
        return 32.0

    def draw(self, surface: pygame.Surface, pokemon_name: str, ball_name: str) -> None:
        overlay = pygame.Surface((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        cx, cy = settings.SCREEN_WIDTH // 2, settings.SCREEN_HEIGHT // 2 - 20
        pygame.draw.circle(surface, (220, 80, 80), (cx, cy), 76, 2)
        pygame.draw.circle(surface, (90, 230, 90), (cx, cy), int(self.perfect_radius), 2)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), int(self.current_radius), 3)
        pygame.draw.circle(surface, settings.WHITE, (cx, cy), 10)
        pygame.draw.circle(surface, settings.RED, (cx, cy), 10, 2)

        f1 = loader.font("couriernew", 24, bold=True)
        f2 = loader.font("couriernew", 16)
        title = f1.render(f"Catch {pokemon_name}", True, settings.UI_HIGHLIGHT)
        tip = f2.render(f"Time your throw with {ball_name}", True, settings.WHITE)
        result = f1.render(self._result_text, True, settings.WHITE)
        surface.blit(title, (cx - title.get_width() // 2, 80))
        surface.blit(tip, (cx - tip.get_width() // 2, 118))
        surface.blit(result, (cx - result.get_width() // 2, settings.SCREEN_HEIGHT - 120))
