"""Systeme de particules pour les retours visuels (bouffe, mort)."""

import math
import random

import pygame

from . import gfx


class Particle:
    """Etincelle lumineuse a duree de vie limitee."""

    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size")

    def __init__(self, x, y, vx, vy, life, color, size):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size


class ParticleSystem:
    """Conteneur : met a jour et dessine toutes les particules vivantes."""

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.particles = []

    def burst(self, pos, color, count=26, speed=190, size=4.0, life=0.55):
        """Explosion radiale a la position donnee."""
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            power = speed * self.rng.uniform(0.25, 1.0)
            self.particles.append(
                Particle(
                    pos[0],
                    pos[1],
                    math.cos(angle) * power,
                    math.sin(angle) * power,
                    life * self.rng.uniform(0.6, 1.3),
                    color,
                    size * self.rng.uniform(0.5, 1.4),
                )
            )

    def trail(self, pos, color, count=2):
        """Poussiere lente laissee derriere la tete."""
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            power = self.rng.uniform(6, 26)
            self.particles.append(
                Particle(
                    pos[0],
                    pos[1],
                    math.cos(angle) * power,
                    math.sin(angle) * power,
                    self.rng.uniform(0.25, 0.5),
                    color,
                    self.rng.uniform(1.2, 2.6),
                )
            )

    def update(self, dt):
        """Avance la simulation et retire les particules eteintes."""
        drag = 0.90 ** (dt * 60)
        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vx *= drag
            p.vy *= drag
            alive.append(p)
        self.particles = alive

    def draw(self, surface):
        """Rendu additif : les particules brillent sur le fond sombre."""
        for p in self.particles:
            t = max(0.0, p.life / p.max_life)
            radius = max(1, int(p.size * t))
            color = gfx.scale_color(p.color, t * t)
            pygame.draw.circle(
                surface, color, (int(p.x), int(p.y)), radius
            )

    def clear(self):
        """Vide le systeme (nouvelle partie)."""
        self.particles.clear()
