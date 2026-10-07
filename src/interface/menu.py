"""Menu principal : JOUER, ENTRAINEMENT, EVALUATION, QUITTER."""

import pygame

from . import theme, widgets

JOUER = "jouer"
ENTRAINEMENT = "entrainement"
EVALUATION = "evaluation"
QUITTER = "quitter"

ENTREES = (
    (JOUER, "JOUER", "l'IA joue au mieux, ou toi au clavier"),
    (ENTRAINEMENT, "ENTRAINEMENT",
     "creer un modele, continuer son entrainement"),
    (EVALUATION, "EVALUATION",
     "parties en boucle jusqu'a une longueur de 35, puis rejeu"),
    (QUITTER, "QUITTER", ""),
)

LARGEUR = 520
HAUTEUR = 78
ECART = 16
HAUT = 240

HINTS = ("HAUT / BAS  choisir   ·   ENTREE  valider   ·   ECHAP  quitter",)


class MainMenu:
    """Ecran d'accueil quand le programme est lance sans argument."""

    def __init__(self, fonts, starfield):
        self.fonts = fonts
        self.fond = widgets.Fond(starfield)
        self.time_s = 0.0
        self.index = 0
        self.rects = [
            pygame.Rect(theme.WIN_W // 2 - LARGEUR // 2,
                        HAUT + i * (HAUTEUR + ECART), LARGEUR, HAUTEUR)
            for i in range(len(ENTREES))
        ]

    def handle_event(self, event):
        """Renvoie l'entree choisie (JOUER...) ou None."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return QUITTER
            if event.key in widgets.TOUCHES_VALIDER + (pygame.K_SPACE,):
                return ENTREES[self.index][0]
            if event.key in widgets.TOUCHES_BAS:
                self.index = (self.index + 1) % len(ENTREES)
            elif event.key in widgets.TOUCHES_HAUT:
                self.index = (self.index - 1) % len(ENTREES)
        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.rects):
                if rect.collidepoint(event.pos):
                    self.index = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.rects):
                if rect.collidepoint(event.pos):
                    return ENTREES[i][0]
        return None

    def update(self, dt):
        self.time_s += dt
        self.fond.update(dt)

    def render(self, screen):
        self.fond.render(screen, self.time_s)
        widgets.titre(screen, self.fonts, "LEARN2SLITHER",
                      "GALAXIE SERPENTINE  ·  MENU PRINCIPAL", y=70)
        for i, ((_, libelle, detail), rect) in enumerate(
                zip(ENTREES, self.rects)):
            focus = i == self.index
            widgets.bouton(screen, self.fonts["value"], rect, "",
                           focus=focus,
                           time_s=self.time_s if focus else None)
            y = rect.centery - (11 if detail else 0)
            widgets.texte(screen, self.fonts["value"], libelle,
                          (rect.centerx, y), theme.TEXT, centre=True)
            if detail:
                widgets.texte(screen, self.fonts["label"], detail,
                              (rect.centerx, rect.centery + 17),
                              theme.ACCENT if focus else theme.TEXT_MUTED,
                              centre=True)
        widgets.aide(screen, self.fonts["label"], HINTS,
                     self.rects[-1].bottom + 30)
