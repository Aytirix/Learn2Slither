"""Fond spatial : trois couches d'etoiles en parallaxe lente."""

import math
import random

import pygame

from . import gfx, theme

LAYERS = (
    {"count": 120, "speed": 3.0, "bright": 0.30, "size": 1},
    {"count": 70, "speed": 7.0, "bright": 0.60, "size": 1},
    {"count": 28, "speed": 13.0, "bright": 1.00, "size": 2},
)


class Starfield:
    """Etoiles qui derivent et scintillent derriere le plateau."""

    def __init__(self, width, height, rng=None):
        self.width = width
        self.height = height
        self.rng = rng or random.Random(42)
        self.stars = []
        for layer in LAYERS:
            for _ in range(layer["count"]):
                self.stars.append(
                    [
                        self.rng.uniform(0, width),
                        self.rng.uniform(0, height),
                        layer["speed"],
                        layer["bright"],
                        layer["size"],
                        self.rng.uniform(0, math.tau),
                    ]
                )

    def update(self, dt):
        """Deplace les etoiles, avec rebouclage sur les bords."""
        for star in self.stars:
            star[0] -= star[2] * dt * 0.6
            star[1] += star[2] * dt
            if star[1] > self.height:
                star[1] -= self.height
                star[0] = self.rng.uniform(0, self.width)
            if star[0] < 0:
                star[0] += self.width

    def draw(self, surface, time_s):
        """Dessine les etoiles avec un leger scintillement."""
        for x, y, _, bright, size, phase in self.stars:
            twinkle = 0.65 + 0.35 * math.sin(time_s * 2.0 + phase)
            color = gfx.scale_color(theme.STAR, bright * twinkle)
            if size == 1:
                surface.set_at((int(x), int(y)), color)
            else:
                pygame.draw.circle(surface, color, (int(x), int(y)), size)
