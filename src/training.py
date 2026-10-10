"""Entrainement lance depuis la fenetre (menu ENTRAINEMENT).

Meme boucle que `-visual off` (session.play_session), mais decoupee en
tranches : la fenetre joue quelques parties a chaque image, puis se
redessine. Elle reste ainsi reactive (barre de progression, bouton
ARRETER) sans fil d'execution parallele.
"""

import random
import statistics
import time
from collections import deque

from . import graine as gr
from .agent import modele
from .environment import board as bd
from .environment.rewards import recompense
from .session import play_session

# Les dernieres parties servent a afficher la moyenne courante : sur toutes
# les parties, les premieres (jouees au hasard) tireraient la moyenne vers
# le bas pendant longtemps.
FENETRE_MOYENNE = 100


class Entrainement:
    """Entraine `agent` jusqu'a `objectif` parties, puis le sauvegarde."""

    def __init__(self, agent, chemin, objectif, taille=10, seed=None,
                 horloge=time.perf_counter):
        self.agent = agent
        self.chemin = chemin
        self.depart = agent.parties
        self.objectif = max(objectif, self.depart)
        self.board = bd.Board(size=taille, rng=random.Random())
        # Une graine par partie (src/graine.py) : avec la meme graine de
        # depart, tout l'entrainement se rejoue a l'identique.
        self.graine_depart = gr.graine_de_depart(seed)
        self.horloge = horloge
        self.jouees = 0
        self.recentes = deque(maxlen=FENETRE_MOYENNE)
        # Moyenne des FENETRE_MOYENNE dernieres parties, relevee toutes les
        # FENETRE_MOYENNE parties : la courbe d'apprentissage affichee.
        self.courbe = []
        self.record = 0
        self.fini = False
        self.erreur = None
        self.debut = horloge()

    @property
    def a_jouer(self):
        return self.objectif - self.depart

    @property
    def progression(self):
        """Avancement 0 -> 1."""
        if self.a_jouer <= 0:
            return 1.0
        return min(1.0, self.jouees / self.a_jouer)

    @property
    def moyenne_recente(self):
        return statistics.fmean(self.recentes) if self.recentes else 0.0

    @property
    def parties_par_seconde(self):
        duree = self.horloge() - self.debut
        return self.jouees / duree if duree > 0 else 0.0

    def avancer(self, budget_s):
        """Joue des parties pendant environ `budget_s` secondes.

        Le compte se fait sur les parties jouees ici, et non sur
        agent.parties : la boucle s'arrete meme si un agent ne comptait pas
        ses parties.
        """
        fin = self.horloge() + budget_s
        while not self.fini and self.jouees < self.a_jouer:
            gr.nouvelle_partie(self.board, self.agent, gr.graine_partie(
                self.graine_depart, self.jouees + 1))
            play_session(self.board, self.agent, recompense)
            self.jouees += 1
            self.recentes.append(self.board.max_length)
            self.record = max(self.record, self.board.max_length)
            if self.jouees % FENETRE_MOYENNE == 0:
                self.courbe.append(self.moyenne_recente)
            if self.horloge() >= fin:
                break
        if self.jouees >= self.a_jouer:
            self.terminer()

    def terminer(self):
        """Arrete et sauvegarde ; renvoie False si l'ecriture a echoue.

        Appelee aussi par ARRETER, la fermeture de la fenetre et Ctrl+C :
        les parties deja jouees ne sont jamais perdues.
        """
        if self.fini:
            return self.erreur is None
        self.fini = True
        try:
            modele.sauvegarder(self.agent, self.chemin)
        except modele.ErreurModele as erreur:
            self.erreur = str(erreur)
            return False
        return True
