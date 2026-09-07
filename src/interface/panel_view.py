"""Panneau lateral : titre, statistiques, vision et aide."""

import pygame

from ..environment import board as bd
from . import gfx, theme

CHAR_COLORS = {
    bd.WALL_CHAR: theme.TEXT_MUTED,
    bd.HEAD_CHAR: theme.SNAKE_HEAD,
    bd.BODY_CHAR: (129, 140, 248),
    bd.GREEN_CHAR: theme.GREEN_APPLE,
    bd.RED_CHAR: theme.RED_APPLE,
    bd.EMPTY_CHAR: (48, 60, 88),
}

MANUAL_HINT = "FLECHES / ZQSD   diriger le serpent"

HINTS = (
    "ESPACE           pause  ·  rejouer",
    "N / P            pas suivant  ·  mode pas a pas",
    "V / T            vision  ·  trace terminal",
    "+ / -  ·  R      vitesse  ·  nouvelle partie",
    "ECHAP            retour au lobby",
)


def hints_for(game):
    """Aide clavier : les directions n'existent qu'en pilotage manuel."""
    if game.manual:
        return (MANUAL_HINT,) + HINTS
    return HINTS


class PanelView:
    """Colonne de droite, dessinee directement sur l'ecran."""

    def __init__(self, screen, fonts):
        self.screen = screen
        self.fonts = fonts

    def render(self, game):
        """Dessine le panneau complet."""
        x = theme.PANEL_X
        y = self._header(game, x, theme.BOARD_Y)
        y = self._stats(game, x, y)
        y = self._vision(game, x, y)
        self._footer(game, x, y)

    def _header(self, game, x, y):
        title = self.fonts["title"].render("LEARN2SLITHER", True, theme.TEXT)
        caption = game.pilot_label
        if game.sessions > 1:
            caption += "  ·  SESSION {}/{}".format(
                game.session, game.sessions
            )
        sub = self.fonts["sub"].render(caption, True, theme.ACCENT)
        self.screen.blit(title, (x, y))
        self.screen.blit(sub, (x, y + 38))
        return y + 74

    def _stats(self, game, x, y):
        stats = (
            ("LONGUEUR", str(len(game.board.snake))),
            ("RECORD", str(game.best_length)),
            ("DUREE", str(game.board.steps)),
            ("VITESSE", "{:.1f}/s".format(game.speed)),
        )
        cw = (theme.PANEL_W - 12) // 2
        for i, (label, value) in enumerate(stats):
            rect = pygame.Rect(
                x + (i % 2) * (cw + 12), y + (i // 2) * 74, cw, 64
            )
            self._stat_card(rect, label, value)
        return y + 2 * 74 + 8

    def _stat_card(self, rect, label, value):
        gfx.card(self.screen, rect, theme.BG_CARD, theme.BORDER, 14)
        lab = self.fonts["label"].render(label, True, theme.TEXT_MUTED)
        val = self.fonts["value"].render(value, True, theme.TEXT)
        self.screen.blit(lab, (rect.x + 16, rect.y + 12))
        self.screen.blit(val, (rect.x + 16, rect.y + 30))

    def _vision(self, game, x, y):
        lines = game.board.vision_lines()
        font = self.fonts["vision"]
        line_h = font.get_height() + 1
        height = 44 + line_h * max(1, len(lines)) + 12
        rect = pygame.Rect(x, y, theme.PANEL_W, height)
        gfx.card(self.screen, rect, theme.BG_CARD, theme.BORDER, 14)
        head = self.fonts["label"].render(
            "VISION DU SERPENT  (terminal)", True, theme.TEXT_MUTED
        )
        self.screen.blit(head, (x + 16, y + 14))

        cw = font.size("0")[0]
        for row, line in enumerate(lines):
            for col, char in enumerate(line):
                if char == " ":
                    continue
                glyph = font.render(
                    char, True, CHAR_COLORS.get(char, theme.TEXT_DIM)
                )
                self.screen.blit(
                    glyph, (x + 16 + col * cw, y + 38 + row * line_h)
                )
        return y + height + 12

    def _footer(self, game, x, y):
        alive = game.board.alive
        rows = (
            (
                "DERNIERE ACTION",
                bd.ACTION_NAMES.get(game.board.direction, "-"),
                theme.ACCENT,
            ),
            (
                "ETAT",
                "EN VIE" if alive else "MORT",
                theme.GREEN_APPLE if alive else theme.RED_APPLE,
            ),
        )
        for label, value, color in rows:
            lab = self.fonts["label"].render(label, True, theme.TEXT_MUTED)
            val = self.fonts["mono"].render(value, True, color)
            self.screen.blit(lab, (x, y))
            self.screen.blit(val, (x + 180, y - 2))
            y += 26

        y += 10
        for hint in hints_for(game):
            surf = self.fonts["label"].render(hint, True, theme.TEXT_MUTED)
            self.screen.blit(surf, (x, y))
            y += 18
