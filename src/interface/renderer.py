"""Assemble le fond, le plateau et le panneau en une frame."""

from . import gfx, theme
from .board_view import BoardView
from .panel_view import PanelView


class Renderer:
    """Chef d'orchestre du rendu : fond, plateau, panneau."""

    def __init__(self, screen, fonts, starfield):
        self.screen = screen
        self.fonts = fonts
        self.starfield = starfield
        self.vignette = gfx.make_vignette(theme.WIN_W, theme.WIN_H)
        self.board_view = BoardView(fonts)
        self.panel_view = PanelView(screen, fonts)

    def draw(self, game):
        """Dessine une frame complete a partir de l'etat du jeu."""
        self.screen.fill(theme.BG_DEEP)
        self.starfield.draw(self.screen, game.time_s)
        self.screen.blit(self.vignette, (0, 0))
        board_surf = self.board_view.render(game)
        self.screen.blit(
            board_surf,
            (theme.BOARD_X + game.shake[0], theme.BOARD_Y + game.shake[1]),
        )
        self.panel_view.render(game)
