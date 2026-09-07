"""Primitives graphiques : glow, halos, vignette, interpolations."""

import math

import pygame


def lerp(a, b, t):
    """Interpolation lineaire entre deux scalaires."""
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    """Interpolation lineaire entre deux couleurs RVB."""
    t = max(0.0, min(1.0, t))
    return (
        int(lerp(c1[0], c2[0], t)),
        int(lerp(c1[1], c2[1], t)),
        int(lerp(c1[2], c2[2], t)),
    )


def scale_color(color, factor):
    """Multiplie une couleur par un facteur, borne a 255."""
    return tuple(min(255, int(c * factor)) for c in color)


def ease_out_cubic(t):
    """Adoucit une progression 0->1."""
    return 1.0 - (1.0 - t) ** 3


def blur(surface, factor=8):
    """Flou approxime : reduction forte puis remontee en deux paliers."""
    w, h = surface.get_size()
    small = pygame.transform.smoothscale(
        surface, (max(1, w // factor), max(1, h // factor))
    )
    mid = pygame.transform.smoothscale(
        small, (max(1, w // 2), max(1, h // 2))
    )
    return pygame.transform.smoothscale(mid, (w, h))


def make_halo(radius, color, steps=28):
    """Halo radial pret pour un blit additif (RVB degrade vers noir)."""
    size = radius * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    for i in range(steps, 0, -1):
        t = i / steps
        r = int(radius * t)
        if r <= 0:
            continue
        fade = (1.0 - t) ** 2
        pygame.draw.circle(
            surf, scale_color(color, fade), (radius, radius), r
        )
    return surf


def make_vignette(width, height, strength=190):
    """Assombrissement progressif des bords de la fenetre."""
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    max_r = int(math.hypot(width, height) / 2)
    cx, cy = width // 2, height // 2
    steps = 60
    for i in range(steps):
        t = i / steps
        alpha = int(strength * (t ** 2.2))
        radius = int(max_r * (1.0 - t))
        pygame.draw.circle(surf, (0, 0, 0, alpha), (cx, cy), radius)
    return surf


def card(surface, rect, fill, border, radius=18, width=1):
    """Panneau arrondi avec liseré."""
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(
        surface, border, rect, width=width, border_radius=radius
    )


def additive(target, source, pos):
    """Blit additif : ne rend visible que la lumiere."""
    target.blit(source, pos, special_flags=pygame.BLEND_RGB_ADD)
