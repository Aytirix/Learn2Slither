"""Rendu du plateau : grille, faisceau de vision, pommes, serpent."""

import math

import pygame

from ..environment import board as bd
from . import gfx, theme

PAD = 16
FIN_HINT = "[ESPACE] ou [R] pour rejouer"

# Libelles d'affichage derives de la source unique de `board`. Le nom evite
# "DEATH" a dessein : une troncature n'est pas une mort.
END_CAUSE_LABELS = {
    cause: label.upper()
    for cause, label in bd.END_CAUSE_LABELS.items()
}


def cell_size(board_size):
    """Cote d'une case, en pixels."""
    return (theme.BOARD_PX - 2 * PAD) / board_size


def cell_center(board_size, cell):
    """Centre d'une case, en coordonnees du plateau."""
    cs = cell_size(board_size)
    return (PAD + (cell[0] + 0.5) * cs, PAD + (cell[1] + 0.5) * cs)


class BoardView:
    """Dessine le plateau sur sa propre surface, effets compris."""

    def __init__(self, fonts):
        self.fonts = fonts
        size = (theme.BOARD_PX, theme.BOARD_PX)
        self.surf = pygame.Surface(size, pygame.SRCALPHA)
        self.light = pygame.Surface(size, pygame.SRCALPHA)
        self.spark = pygame.Surface(size, pygame.SRCALPHA)
        self.beam = pygame.Surface(size, pygame.SRCALPHA)
        self.mask = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(
            self.mask,
            (255, 255, 255, 255),
            self.mask.get_rect(),
            border_radius=20,
        )
        self.halos = {}

    def halo(self, radius, color):
        """Halo mis en cache par rayon et couleur."""
        key = (radius, color)
        if key not in self.halos:
            self.halos[key] = gfx.make_halo(radius, color)
        return self.halos[key]

    def center(self, board, cell):
        return cell_center(board.size, cell)

    # -- frame --------------------------------------------------------
    def render(self, game):
        """Compose la frame du plateau et retourne la surface."""
        board = game.board
        self.surf.fill((0, 0, 0, 0))
        self.light.fill((0, 0, 0, 0))
        self.spark.fill((0, 0, 0, 0))
        self.beam.fill((0, 0, 0, 0))

        gfx.card(
            self.surf, self.surf.get_rect(), theme.BG_CARD, theme.BORDER, 20
        )
        self._grid(board)

        if game.show_vision and board.snake:
            self._vision(board)
            self.surf.blit(self.beam, (0, 0))

        self._apples(board, game.time_s)
        if board.snake:
            self._snake(game)

        game.particles.draw(self.spark)
        gfx.additive(self.surf, gfx.blur(self.light, 6), (0, 0))
        gfx.additive(self.surf, self.spark, (0, 0))
        self.surf.blit(
            self.mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT
        )

        if not board.alive:
            self._game_over(game)
        return self.surf

    def _grid(self, board):
        cs = cell_size(board.size)
        end = PAD + cs * board.size
        for i in range(board.size + 1):
            p = PAD + i * cs
            pygame.draw.line(self.surf, theme.GRID, (p, PAD), (p, end))
            pygame.draw.line(self.surf, theme.GRID, (PAD, p), (end, p))

    def _vision(self, board):
        """Faisceau case par case, degressif avec la distance."""
        cs = cell_size(board.size)
        head = board.snake[0]
        side = int(cs * 0.84)
        radius = int(cs * 0.26)
        for cells in board.vision_rays().values():
            visible = [c for c in cells if board.inside(c)]
            if not visible:
                continue
            for i, cell in enumerate(visible):
                fade = 1.0 - i / (len(visible) + 1.5)
                cx, cy = self.center(board, cell)
                rect = pygame.Rect(0, 0, side, side)
                rect.center = (int(cx), int(cy))
                pygame.draw.rect(
                    self.beam,
                    theme.ACCENT + (int(10 + 30 * fade),),
                    rect,
                    border_radius=radius,
                )
            pygame.draw.line(
                self.light,
                gfx.scale_color(theme.ACCENT, 0.10),
                self.center(board, head),
                self.center(board, visible[-1]),
                max(2, int(cs * 0.16)),
            )

    def _apples(self, board, time_s):
        cs = cell_size(board.size)
        radius = int(cs * 0.27)
        halo_r = int(cs * 1.25)
        for cell in board.greens:
            self._apple(
                cell, board, theme.GREEN_APPLE, radius, halo_r, time_s, 0.0
            )
        for cell in board.reds:
            self._apple(
                cell, board, theme.RED_APPLE, radius, halo_r, time_s, 1.7
            )

    def _apple(self, cell, board, color, radius, halo_r, time_s, phase):
        cx, cy = self.center(board, cell)
        bob = math.sin(time_s * 2.4 + phase + cell[0] * 0.7) * radius * 0.16
        pulse = 0.75 + 0.25 * math.sin(time_s * 3.1 + phase)
        halo = self.halo(halo_r, gfx.scale_color(color, 0.55 * pulse))
        gfx.additive(self.light, halo, (cx - halo_r, cy + bob - halo_r))
        pygame.draw.circle(
            self.surf, color, (int(cx), int(cy + bob)), radius
        )
        pygame.draw.circle(
            self.surf,
            gfx.lerp_color(color, (255, 255, 255), 0.55),
            (int(cx - radius * 0.3), int(cy + bob - radius * 0.35)),
            max(1, int(radius * 0.28)),
        )

    def _snake(self, game):
        points = game.snake_points()
        width = max(4, int(cell_size(game.board.size) * 0.72))
        n = max(1, len(points) - 1)

        for i in range(len(points) - 1, -1, -1):
            t = i / n
            color = gfx.lerp_color(theme.SNAKE_HEAD, theme.SNAKE_TAIL, t)
            core = gfx.lerp_color(color, (255, 255, 255), 0.22)
            w = max(3, int(width * (1.0 - 0.46 * t ** 1.2)))
            cw = max(2, int(w * 0.42))
            pos = (int(points[i][0]), int(points[i][1]))
            if i > 0:
                nxt = (int(points[i - 1][0]), int(points[i - 1][1]))
                pygame.draw.line(self.surf, color, pos, nxt, w)
                pygame.draw.line(self.surf, core, pos, nxt, cw)
                pygame.draw.line(
                    self.light,
                    gfx.scale_color(color, 0.30),
                    pos,
                    nxt,
                    int(w * 1.7),
                )
            pygame.draw.circle(self.surf, color, pos, w // 2)
            pygame.draw.circle(self.surf, core, pos, cw // 2)

        self._head(game, points[0], width)

    def _head(self, game, head_pos, width):
        hx, hy = head_pos
        radius = int(width * 0.58)
        pygame.draw.circle(
            self.surf, theme.SNAKE_HEAD, (int(hx), int(hy)), radius
        )
        halo_r = int(width * 1.6)
        halo = self.halo(halo_r, gfx.scale_color(theme.SNAKE_HEAD, 0.5))
        gfx.additive(self.light, halo, (hx - halo_r, hy - halo_r))

        dx, dy = game.board.direction
        px, py = -dy, dx
        eye_r = max(2, int(radius * 0.26))
        for side in (-1, 1):
            ex = hx + dx * radius * 0.38 + px * side * radius * 0.42
            ey = hy + dy * radius * 0.38 + py * side * radius * 0.42
            pygame.draw.circle(
                self.surf, theme.SNAKE_EYE, (int(ex), int(ey)), eye_r
            )

    def _game_over(self, game):
        board = game.board
        overlay = pygame.Surface(self.surf.get_size(), pygame.SRCALPHA)
        overlay.fill((6, 8, 18, 190))
        self.surf.blit(overlay, (0, 0))
        cx = theme.BOARD_PX // 2
        label = END_CAUSE_LABELS.get(board.end_cause, "FIN DE PARTIE")
        # Une interruption n'est pas une mort : pas de rouge.
        label_color = theme.ACCENT if board.truncated else theme.RED_APPLE
        rows = (
            (self.fonts["big"].render(
                "FIN DE PARTIE", True, theme.TEXT), 250),
            (self.fonts["mono"].render(label, True, label_color), 310),
            (self.fonts["mono"].render(
                "longueur max = {}   duree max = {}".format(
                    board.max_length, board.steps
                ),
                True,
                theme.TEXT_DIM,
            ), 340),
            (self.fonts["label"].render(
                getattr(game, "fin_hint", FIN_HINT), True, theme.ACCENT),
             390),
        )
        for surf, y in rows:
            self.surf.blit(surf, (cx - surf.get_width() // 2, y))
