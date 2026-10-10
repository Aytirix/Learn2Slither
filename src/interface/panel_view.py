"""Panneau lateral : titre, statistiques, vision et aide."""

import pygame

from .. import config as cfg
from ..environment import board as bd
from . import gfx, theme
from .model_card import AVERTISSEMENT

CHAR_COLORS = {
    bd.WALL_CHAR: theme.TEXT_MUTED,
    bd.HEAD_CHAR: theme.SNAKE_HEAD,
    bd.BODY_CHAR: (129, 140, 248),
    bd.GREEN_CHAR: theme.GREEN_APPLE,
    bd.RED_CHAR: theme.RED_APPLE,
    bd.EMPTY_CHAR: (48, 60, 88),
}

MANUAL_HINT = "FLECHES / ZQSD   diriger le serpent"


def ligne_etat(touche, libelle, actif):
    """Ligne d'aide d'un interrupteur : verte s'il est actif, orange sinon."""
    texte = "{:<17}{}  ·  {}".format(
        touche, libelle, "ACTIF" if actif else "INACTIF")
    return texte, theme.GREEN_APPLE if actif else theme.ORANGE


def hints_for(game):
    """Aide clavier, une touche par ligne : liste de (texte, couleur).

    Les interrupteurs (P, V, T) montrent leur etat en couleur. Une partie
    peut retirer ESPACE et R (`aide_complete`) et changer la ligne d'ECHAP
    (`aide_sortie`), comme le fait l'evaluation.
    """
    neutre = theme.TEXT_MUTED
    complete = getattr(game, "aide_complete", True)
    lignes = []
    if game.manual:
        lignes.append((MANUAL_HINT, neutre))
    if complete:
        lignes.append(("ESPACE           pause  ·  rejouer", neutre))
    if game.manual:
        lignes.append(("N                pas suivant", neutre))
    else:
        lignes += [
            ("N / DROITE       pas suivant", neutre),
            ("GAUCHE           pas precedent  (en pas a pas)", neutre),
        ]
    lignes += [
        ligne_etat("P", "mode pas a pas", game.step_by_step),
        ligne_etat("V", "vision", game.show_vision),
        ligne_etat("T", "trace terminal", game.trace),
        ("+ / -            vitesse", neutre),
    ]
    if complete:
        lignes.append(("R                nouvelle partie", neutre))
    lignes.append(("ECHAP            " + getattr(
        game, "aide_sortie", "retour au lobby"), neutre))
    return lignes


def etat_de_partie(board):
    """Libelle et couleur de l'etat du plateau.

    Trois etats et non deux : une partie tronquee n'est pas une mort, le
    serpent etait vivant quand on a coupe le chrono.
    """
    if board.alive:
        return "EN VIE", theme.GREEN_APPLE
    if board.truncated:
        return "INTERROMPU", theme.ACCENT
    return "MORT", theme.RED_APPLE


def recadrer(lines, max_lignes, max_colonnes):
    """Centre de la croix autour de la tete, si elle est trop grande.

    Renvoie (lignes, recadree). La tete reste au milieu ; on coupe a
    egale distance de chaque cote.
    """
    if len(lines) <= max_lignes and all(
            len(line) <= max_colonnes for line in lines):
        return lines, False
    ligne_tete = next(
        (i for i, line in enumerate(lines) if bd.HEAD_CHAR in line), 0)
    colonne_tete = lines[ligne_tete].find(bd.HEAD_CHAR) if lines else 0
    demi_h = (max_lignes - 1) // 2
    demi_l = (max_colonnes - 1) // 2
    haut = max(0, min(ligne_tete - demi_h, len(lines) - max_lignes))
    gauche = max(0, colonne_tete - demi_l)
    return [line[gauche:gauche + max_colonnes]
            for line in lines[haut:haut + max_lignes]], True


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
        recul = getattr(game, "recul", 0)
        if recul:
            caption += "  ·  RETOUR {} PAS EN ARRIERE".format(recul)
        sub = self.fonts["sub"].render(
            caption, True, theme.ORANGE if recul else theme.ACCENT)
        self.screen.blit(title, (x, y))
        self.screen.blit(sub, (x, y + 38))
        if getattr(game, "vision_complete", False):
            # Modele hors sujet : rappele en permanence pendant la partie.
            alerte = self.fonts["label"].render(AVERTISSEMENT, True,
                                                theme.RED_APPLE)
            self.screen.blit(alerte, (x, y + 56))
        return y + 74

    def _stats(self, game, x, y):
        stats = (
            ("LONGUEUR", str(len(game.board.snake))),
            ("RECORD", str(game.best_length)),
            ("DUREE", str(game.board.steps)),
            ("VITESSE", cfg.libelle_vitesse(game.speed).replace(" ", "")),
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
        font = self.fonts["vision"]
        line_h = font.get_height() + 1
        cw = font.size("0")[0]
        # Sur un grand plateau, la croix complete ne tient pas dans le
        # panneau : on n'en montre que le centre, autour de la tete.
        bas = theme.WIN_H - 20 - 62 - 18 * len(hints_for(game))
        lines, recadree = recadrer(
            game.board.vision_lines(),
            max(3, (bas - y - 56 - 12) // line_h),
            max(3, (theme.PANEL_W - 32) // cw),
        )
        height = 44 + line_h * max(1, len(lines)) + 12
        rect = pygame.Rect(x, y, theme.PANEL_W, height)
        gfx.card(self.screen, rect, theme.BG_CARD, theme.BORDER, 14)
        head = self.fonts["label"].render(
            "VISION DU SERPENT  (centre de la croix)" if recadree
            else "VISION DU SERPENT  (terminal)", True, theme.TEXT_MUTED
        )
        self.screen.blit(head, (x + 16, y + 14))

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
        board = game.board
        etat, couleur = etat_de_partie(board)
        rows = (
            (
                "DERNIERE ACTION",
                bd.ACTION_NAMES.get(game.board.direction, "-"),
                theme.ACCENT,
            ),
            ("ETAT", etat, couleur),
        )
        for label, value, color in rows:
            lab = self.fonts["label"].render(label, True, theme.TEXT_MUTED)
            val = self.fonts["mono"].render(value, True, color)
            self.screen.blit(lab, (x, y))
            self.screen.blit(val, (x + 180, y - 2))
            y += 26

        y += 10
        for hint, couleur in hints_for(game):
            surf = self.fonts["label"].render(hint, True, couleur)
            self.screen.blit(surf, (x, y))
            y += 18
