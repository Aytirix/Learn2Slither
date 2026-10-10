"""Evaluation d'un modele (menu EVALUATION), sans affichage.

Regle demandee : on enchaine des parties avec l'agent FIGE (il joue au
mieux, n'apprend rien) jusqu'a ce qu'une partie atteigne la longueur
SEUIL. Cette partie-la n'est pas coupee en plein milieu : on la laisse aller
jusqu'a sa fin, puis l'evaluation s'arrete.

Chaque pas est photographie, pour pouvoir ensuite rejouer la partie coup
par coup, en avant et en arriere.
"""

from .config import OBJECTIF_DEFAUT
from .session import SessionStats

# Longueur visee par defaut ; reglable dans l'ecran EVALUATION (OBJECTIF).
SEUIL = OBJECTIF_DEFAUT


class Photo:
    """Etat du plateau a un instant : de quoi le redessiner a l'identique."""

    __slots__ = ("snake", "greens", "reds", "direction", "steps", "idle",
                 "max_length", "alive", "truncated", "end_cause", "event",
                 "graine")

    def __init__(self, board):
        self.snake = list(board.snake)
        self.greens = list(board.greens)
        self.reds = list(board.reds)
        self.direction = board.direction
        self.steps = board.steps
        # Pas depuis la derniere pomme : sans lui, revenir au present apres
        # un retour en arriere (mode pas a pas) fausserait la troncature.
        self.idle = board.idle
        self.max_length = board.max_length
        self.alive = board.alive
        self.truncated = board.truncated
        self.end_cause = board.end_cause
        self.event = board.last_event
        # Graine de la partie : -seed <graine> la rejoue (src/graine.py).
        self.graine = board.graine

    def restaurer(self, board):
        """Remet `board` dans l'etat photographie (pour l'affichage)."""
        board.snake = list(self.snake)
        board.greens = list(self.greens)
        board.reds = list(self.reds)
        board.direction = self.direction
        board.steps = self.steps
        board.idle = self.idle
        board.max_length = self.max_length
        board.alive = self.alive
        board.truncated = self.truncated
        board.end_cause = self.end_cause
        board.last_event = self.event
        board.graine = self.graine


class Bilan:
    """Statistiques et rejeu d'une evaluation, partie apres partie."""

    def __init__(self, seuil=SEUIL):
        self.seuil = seuil
        self.stats = SessionStats()
        self.photos = []           # partie en cours
        self.meilleure = []        # photos de la meilleure partie finie
        self.numero_meilleure = 0
        self.derniere = []         # photos de la derniere partie finie
        self.atteint = False

    @property
    def numero(self):
        """Numero de la partie en cours (a partir de 1)."""
        return self.stats.games + 1

    def debut_partie(self, board):
        self.photos = [Photo(board)]

    def apres_pas(self, board):
        self.photos.append(Photo(board))

    def fin_partie(self, board):
        """Enregistre la partie finie ; renvoie True si l'evaluation est
        terminee (la partie a atteint le seuil)."""
        self.stats.record(board)
        self.derniere = self.photos
        if not self.meilleure or board.max_length > self.meilleure_longueur:
            self.meilleure = self.photos
            self.numero_meilleure = self.stats.games
        self.photos = []
        if board.max_length >= self.seuil:
            self.atteint = True
        return self.atteint

    @property
    def meilleure_longueur(self):
        return self.meilleure[-1].max_length if self.meilleure else 0

    def a_rejouer(self):
        """(numero, photos) de la partie a rejouer.

        Si le seuil est atteint, c'est la derniere partie, celle qui l'a
        atteint. Si l'evaluation a ete arretee avant, c'est la meilleure
        partie, y compris celle qu'on vient d'interrompre.
        """
        if self.atteint:
            return self.stats.games, self.derniere
        en_cours = self.photos[-1].max_length if self.photos else 0
        if self.meilleure and self.meilleure_longueur >= en_cours:
            return self.numero_meilleure, self.meilleure
        return self.numero, self.photos
