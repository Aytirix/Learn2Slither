"""Lobby : ecran de configuration affiche avant la partie."""

import math

import pygame

from .. import config as cfg
from .. import models
from . import gfx, theme

CARD_W = 640
CARD_X = (theme.WIN_W - CARD_W) // 2
CARD_Y = 215
ROW_H = 64
ROW_GAP = 8
ROW_PITCH = ROW_H + ROW_GAP
CARD_PAD = 24

ARROW_ZONE = 250
BUTTON_W = 280
BUTTON_H = 58
BUTTON_Y = 592

PILOT_LABELS = {cfg.PILOT_AI: "IA", cfg.PILOT_HUMAN: "JOUEUR"}

HINTS = (
    "HAUT / BAS      choisir un reglage",
    "GAUCHE / DROITE modifier la valeur",
    "ENTREE          lancer la partie",
    "ECHAP           quitter",
)

START = "start"
QUIT = "quit"


class Lobby:
    """Etat et rendu de l'ecran de configuration."""

    def __init__(self, fonts, configuration, starfield):
        self.fonts = fonts
        self.config = configuration
        self.starfield = starfield
        self.vignette = gfx.make_vignette(theme.WIN_W, theme.WIN_H)
        self.light = pygame.Surface(
            (theme.WIN_W, theme.WIN_H), pygame.SRCALPHA
        )
        self.models = models.list_models()
        self.index = 0
        self.time_s = 0.0
        self.hits = []

    # -- contenu ------------------------------------------------------
    def rows(self):
        """Reglages affiches, dans l'ordre, avec leur etat actif."""
        ai = self.config.ai_driven
        return (
            ("PILOTE", PILOT_LABELS[self.config.pilot], True),
            ("MODELE", models.label_for(self.config.model), ai),
            ("PLATEAU", "{0} x {0}".format(self.config.size), True),
            ("VITESSE", "{:.0f} / s".format(self.config.speed), True),
        )

    def enabled_indexes(self):
        return [i for i, row in enumerate(self.rows()) if row[2]]

    def move(self, delta):
        """Deplace le focus sur le reglage actif suivant."""
        available = self.enabled_indexes()
        if not available:
            return
        if self.index in available:
            position = available.index(self.index)
        else:
            position = 0
        self.index = available[(position + delta) % len(available)]

    def change(self, delta):
        """Modifie la valeur du reglage sous le focus."""
        if self.index == 0:
            self.config.toggle_pilot(delta)
            if not self.config.ai_driven:
                self.move(1)
        elif self.index == 1:
            self._change_model(delta)
        elif self.index == 2:
            self.config.change_size(delta)
        elif self.index == 3:
            self.config.change_speed(delta)

    def _change_model(self, delta):
        paths = [path for _, path in self.models]
        if self.config.model in paths:
            current = paths.index(self.config.model)
        else:
            current = 0
        self.config.model = paths[(current + delta) % len(paths)]

    # -- entrees ------------------------------------------------------
    def handle_key(self, key):
        """Retourne START, QUIT ou None selon la touche."""
        if key == pygame.K_ESCAPE:
            return QUIT
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            return START
        if key in (pygame.K_DOWN, pygame.K_s):
            self.move(1)
        elif key in (pygame.K_UP, pygame.K_z, pygame.K_w):
            self.move(-1)
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.change(1)
        elif key in (pygame.K_LEFT, pygame.K_q, pygame.K_a):
            self.change(-1)
        return None

    def handle_click(self, pos):
        """Applique l'action de la zone cliquee, si elle existe."""
        for rect, action in self.hits:
            if not rect.collidepoint(pos):
                continue
            if action == START:
                return START
            index, delta = action
            self.index = index
            self.change(delta)
            return None
        return None

    def update(self, dt):
        self.time_s += dt
        self.starfield.update(dt)

    # -- rendu --------------------------------------------------------
    def render(self, screen):
        """Dessine l'ecran complet du lobby."""
        self.hits = []
        self.light.fill((0, 0, 0, 0))
        screen.fill(theme.BG_DEEP)
        self.starfield.draw(screen, self.time_s)
        self._decor()
        screen.blit(self.vignette, (0, 0))
        gfx.additive(screen, gfx.blur(self.light, 10), (0, 0))
        self._title(screen)
        self._card(screen)
        self._button(screen)
        self._hints(screen)

    def _decor(self):
        """Serpent decoratif ondulant en arriere-plan."""
        base_y = theme.WIN_H * 0.80
        span = theme.WIN_W + 240
        points = []
        for i in range(60):
            t = i / 59
            x = -120 + span * t
            y = base_y + math.sin(t * 6.0 - self.time_s * 1.2) * 46
            points.append((x, y))
        for i in range(len(points) - 1):
            t = i / (len(points) - 1)
            color = gfx.lerp_color(theme.SNAKE_TAIL, theme.SNAKE_HEAD, t)
            pygame.draw.line(
                self.light,
                gfx.scale_color(color, 0.22),
                points[i],
                points[i + 1],
                int(34 * (0.35 + 0.65 * t)),
            )

    def _title(self, screen):
        title = self.fonts["hero"].render(
            "LEARN2SLITHER", True, theme.TEXT
        )
        sub = self.fonts["sub"].render(
            "GALAXIE SERPENTINE  ·  CONFIGURATION DE LA SESSION",
            True,
            theme.ACCENT,
        )
        screen.blit(title, (theme.WIN_W // 2 - title.get_width() // 2, 104))
        screen.blit(sub, (theme.WIN_W // 2 - sub.get_width() // 2, 168))

    def _card(self, screen):
        rows = self.rows()
        height = CARD_PAD * 2 + ROW_PITCH * len(rows) - ROW_GAP
        rect = pygame.Rect(CARD_X, CARD_Y, CARD_W, height)
        gfx.card(screen, rect, theme.BG_CARD, theme.BORDER, 18)
        for i, (label, value, enabled) in enumerate(rows):
            row = pygame.Rect(
                CARD_X + CARD_PAD,
                CARD_Y + CARD_PAD + i * ROW_PITCH,
                CARD_W - CARD_PAD * 2,
                ROW_H,
            )
            self._row(screen, row, i, label, value, enabled)

    def _row(self, screen, rect, index, label, value, enabled):
        focused = enabled and index == self.index
        fill = theme.BG_DEEP if focused else theme.BG_CARD
        border = theme.ACCENT if focused else theme.BORDER
        gfx.card(screen, rect, fill, border, 12, 2 if focused else 1)

        color = theme.TEXT_DIM if enabled else theme.TEXT_MUTED
        lab = self.fonts["label"].render(label, True, color)
        screen.blit(lab, (rect.x + 18, rect.centery - lab.get_height() // 2))

        if index == 0:
            self._pilot_pills(screen, rect)
            return

        left = rect.right - ARROW_ZONE
        right = rect.right - 30
        value_color = theme.TEXT if enabled else theme.TEXT_MUTED
        val = self.fonts["mono"].render(value, True, value_color)
        screen.blit(val, ((left + right) // 2 - val.get_width() // 2,
                          rect.centery - val.get_height() // 2))
        if enabled:
            self._chevrons(screen, rect, index, left, right)

    def _chevrons(self, screen, rect, index, left, right):
        """Fleches a position fixe, alignees d'une ligne a l'autre."""
        arrow = self.fonts["mono"]
        for delta, glyph, x in ((-1, "<", left), (1, ">", right)):
            surf = arrow.render(glyph, True, theme.ACCENT)
            pos = (x - surf.get_width() // 2,
                   rect.centery - surf.get_height() // 2)
            screen.blit(surf, pos)
            hit = pygame.Rect(pos[0] - 16, rect.y,
                              surf.get_width() + 32, rect.height)
            self.hits.append((hit, (index, delta)))

    def _pilot_pills(self, screen, rect):
        pill_w = 118
        pill_h = 38
        x = rect.right - 18 - pill_w * 2 - 10
        for i, pilot in enumerate(cfg.PILOTS):
            active = self.config.pilot == pilot
            pill = pygame.Rect(
                x + i * (pill_w + 10),
                rect.centery - pill_h // 2,
                pill_w,
                pill_h,
            )
            fill = theme.ACCENT if active else theme.BG_CARD
            border = theme.ACCENT if active else theme.BORDER
            gfx.card(screen, pill, fill, border, 10)
            text_color = theme.BG_DEEP if active else theme.TEXT_DIM
            text = self.fonts["mono"].render(
                PILOT_LABELS[pilot], True, text_color
            )
            screen.blit(
                text,
                (pill.centerx - text.get_width() // 2,
                 pill.centery - text.get_height() // 2),
            )
            delta = 1 if not active else 0
            self.hits.append((pill, (0, delta)))

    def _button(self, screen):
        rect = pygame.Rect(
            theme.WIN_W // 2 - BUTTON_W // 2, BUTTON_Y, BUTTON_W, BUTTON_H
        )
        pulse = 0.65 + 0.35 * math.sin(self.time_s * 2.6)
        gfx.card(
            screen,
            rect,
            gfx.scale_color(theme.ACCENT, 0.22 + 0.10 * pulse),
            theme.ACCENT,
            14,
            2,
        )
        text = self.fonts["value"].render("LANCER", True, theme.TEXT)
        screen.blit(
            text,
            (rect.centerx - text.get_width() // 2,
             rect.centery - text.get_height() // 2),
        )
        self.hits.append((rect, START))

    def _hints(self, screen):
        font = self.fonts["label"]
        surfaces = [font.render(h, True, theme.TEXT_MUTED) for h in HINTS]
        width = max(surf.get_width() for surf in surfaces)
        x = theme.WIN_W // 2 - width // 2
        y = BUTTON_Y + BUTTON_H + 26
        for surf in surfaces:
            screen.blit(surf, (x, y))
            y += 20
