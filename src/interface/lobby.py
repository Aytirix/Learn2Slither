"""Lobby : configuration d'une partie (JOUER) ou d'une evaluation."""

import pygame

from .. import config as cfg
from .. import models
from . import widgets
from .model_card import parties
from .widgets import QUIT, START  # noqa: F401  (reexportes pour loop.py)

PILOT_LABELS = {cfg.PILOT_AI: "IA", cfg.PILOT_HUMAN: "JOUEUR"}

# Action renvoyee quand on veut changer de modele : la boucle ouvre alors
# l'ecran de choix du modele.
CHOISIR_MODELE = "choisir_modele"

HINTS = (
    "HAUT / BAS      choisir un reglage",
    "GAUCHE / DROITE modifier la valeur",
    "ENTREE          lancer  ·  choisir le modele",
    "ECHAP           menu principal",
)


def libelle_modele(chemin):
    """Nom du modele et nombre de parties d'entrainement."""
    if not chemin:
        return models.BLANK_LABEL
    infos = models.infos(chemin)
    if not infos.lisible:
        return "{}  (illisible)".format(infos.nom)
    return "{}  ·  {}".format(infos.nom, parties(infos.parties))


class Lobby:
    """Ecran de configuration : reglages, puis LANCER."""

    def __init__(self, fonts, configuration, starfield, avec_pilote=True,
                 sous_titre="JOUER  ·  CONFIGURATION DE LA PARTIE",
                 bouton="LANCER", avec_objectif=False):
        self.fonts = fonts
        self.config = configuration
        self.fond = widgets.Fond(starfield)
        self.sous_titre = sous_titre
        self.time_s = 0.0
        self.formulaire = widgets.Formulaire(
            fonts, self._champs(avec_pilote, avec_objectif), bouton, y=215
        )

    def _champs(self, avec_pilote, avec_objectif):
        conf = self.config
        champs = []
        if avec_pilote:
            champs.append(widgets.Pilules(
                "PILOTE",
                [(p, PILOT_LABELS[p]) for p in cfg.PILOTS],
                lambda: conf.pilot,
                self._choisir_pilote,
            ))
        champs += [
            widgets.Lien(
                "MODELE",
                lambda: libelle_modele(conf.model),
                CHOISIR_MODELE,
                actif=lambda: conf.ai_driven,
            ),
            widgets.Reglage(
                "PLATEAU",
                lambda: "{0} x {0}".format(conf.size),
                conf.change_size,
            ),
            widgets.Reglage(
                "VITESSE",
                lambda: cfg.libelle_vitesse(conf.speed),
                conf.change_speed,
            ),
        ]
        if avec_objectif:
            champs.append(widgets.Reglage(
                "OBJECTIF",
                lambda: str(conf.objectif),
                conf.change_objectif,
                aide="longueur a atteindre, sinon on rejoue",
            ))
        return champs

    def _choisir_pilote(self, pilote):
        self.config.pilot = pilote

    # -- entrees ------------------------------------------------------
    def handle_key(self, key):
        """Retourne START, QUIT, CHOISIR_MODELE ou None selon la touche."""
        if key == pygame.K_ESCAPE:
            return QUIT
        return self.formulaire.handle_key(key)

    def handle_click(self, pos):
        return self.formulaire.handle_click(pos)

    def update(self, dt):
        self.time_s += dt
        self.fond.update(dt)

    # -- rendu --------------------------------------------------------
    def render(self, screen):
        self.fond.render(screen, self.time_s)
        widgets.titre(screen, self.fonts, "LEARN2SLITHER", self.sous_titre,
                      y=70)
        self.formulaire.render(screen, self.time_s)
        widgets.aide(screen, self.fonts["label"], HINTS,
                     self.formulaire.bas + 26)
