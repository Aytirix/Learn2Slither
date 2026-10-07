"""Choix du modele : liste des modeles, details du modele selectionne, OK."""

import pygame

from .. import models
from . import theme, widgets
from .model_card import ListeModeles, carte_details

OK = "ok"
ANNULER = "annuler"

HINTS = (
    "HAUT / BAS  ·  CLIC   selectionner un modele",
    "ENTREE  ·  OK         valider",
)


class ModelPicker:
    """Ecran ou l'on choisit le modele qui va jouer."""

    def __init__(self, fonts, starfield):
        self.fonts = fonts
        self.fond = widgets.Fond(starfield)
        self.time_s = 0.0
        self.liste = ListeModeles(fonts, pygame.Rect(44, 150, 470, 470))
        self.details = pygame.Rect(534, 150, theme.WIN_W - 534 - 44, 470)
        self.ok_rect = pygame.Rect(theme.WIN_W // 2 - 140, 640, 280, 58)

    def ouvrir(self, chemin_actuel):
        """Relit le dossier models/ : un modele vient peut-etre d'etre
        entraine ou cree."""
        self.liste.remplir(
            [i for i in models.modeles() if i.lisible], chemin_actuel)

    @property
    def selection(self):
        """Chemin du modele selectionne, None s'il n'y en a aucun."""
        choisi = self.liste.choisi
        return choisi.chemin if choisi else None

    def handle_event(self, event):
        """Renvoie OK, ANNULER ou None."""
        if event.type == pygame.KEYDOWN:
            if event.key in widgets.TOUCHES_VALIDER + (pygame.K_SPACE,):
                return OK
            if event.key == pygame.K_ESCAPE:
                return ANNULER
            if event.key in widgets.TOUCHES_BAS:
                self.liste.bouger(1)
            elif event.key in widgets.TOUCHES_HAUT:
                self.liste.bouger(-1)
        elif event.type == pygame.MOUSEWHEEL:
            self.liste.defiler(-event.y)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.ok_rect.collidepoint(event.pos):
                return OK
            self.liste.clic(event.pos)
        return None

    def update(self, dt):
        self.time_s += dt
        self.fond.update(dt)

    def render(self, screen):
        self.fond.render(screen, self.time_s)
        widgets.titre(screen, self.fonts, "CHOIX DU MODELE",
                      "LE MODELE SELECTIONNE JOUERA LA PARTIE", y=10)
        self.liste.render(screen)
        carte_details(screen, self.fonts, self.details, self.liste.choisi)
        widgets.bouton(screen, self.fonts["value"], self.ok_rect, "OK",
                       time_s=self.time_s)
        widgets.aide(screen, self.fonts["label"], HINTS, 712)
