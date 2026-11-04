"""Enchainement de sessions sans affichage (-visual off).

Contrat avec l'agent (voir src/agent/agent.py), toutes les methodes sauf
choose() sont optionnelles, pour accepter aussi les agents de reference :

    agent.debut_partie(direction)             cap de depart du serpent
    agent.choose(vision)        -> direction  a chaque pas
    agent.learn(vision, action, reward,
                next_vision, done)            a chaque pas, done = board.dead
    agent.fin_partie()                        une fois, a la fin de la partie
    agent.save(path)                          avec -save

`vision` est le dictionnaire renvoye par Board.vision_chars().
"""

import random
import statistics
from collections import Counter

from . import graine as gr
from .environment import board as bd

# Limite de securite de la boucle de jeu. `Board` coupe deja les parties qui
# tournent en rond ; ceci evite seulement une boucle infinie si un bug
# laissait `alive` a vrai (les tests bloqueraient au lieu d'echouer).
MAX_STEPS_PER_SESSION = 1_000_000


class SessionStats:
    """Bilan d'une serie de sessions."""

    def __init__(self):
        self.games = 0
        self.max_length = 0
        self.max_steps = 0
        self.total_steps = 0
        self.lengths = []
        self.causes = Counter()

    def record(self, board):
        self.games += 1
        self.max_length = max(self.max_length, board.max_length)
        self.max_steps = max(self.max_steps, board.steps)
        self.total_steps += board.steps
        self.lengths.append(board.max_length)
        self.causes[board.end_cause] += 1

    @property
    def mean_length(self):
        """Moyenne des longueurs maximales atteintes, une par partie.

        C'est la moyenne du record de chaque partie. Elle montre mieux la
        progression que le maximum global, qui depend surtout de la chance.
        """
        return statistics.fmean(self.lengths) if self.lengths else 0.0

    @property
    def median_length(self):
        return statistics.median(self.lengths) if self.lengths else 0.0

    def summary(self):
        mean = self.total_steps / self.games if self.games else 0.0
        return (
            "{} sessions — longueur : moyenne = {:.2f}, mediane = {}, "
            "maximale = {} | duree : moyenne = {:.1f}, maximale = {}".format(
                self.games, self.mean_length, self.median_length,
                self.max_length, mean, self.max_steps
            )
        )

    def causes_summary(self):
        """Repartition des fins de partie : dit quoi corriger en priorite."""
        total = sum(self.causes.values())
        if not total:
            return "causes de fin : aucune partie enregistree"
        parts = [
            "{} = {} ({:.0f} %)".format(
                bd.END_CAUSE_LABELS.get(cause, cause), count,
                100.0 * count / total
            )
            for cause, count in self.causes.most_common()
        ]
        return "causes de fin : " + ", ".join(parts)


def play_session(board, agent=None, reward_fn=None, trace=False):
    """Joue une partie complete et retourne la cause de fin.

    Il faut bien distinguer deux choses :

    - `event`, ce qui s'est passe pendant le pas (deplacement, pomme, mort),
      donne la recompense. Si la partie est coupee, le dernier pas reste un
      deplacement normal, avec son cout ;
    - `board.dead` dit s'il y a une suite, et donc si la mise a jour tient
      compte de l'etat suivant. Il reste faux si la partie est coupee,
      puisque le serpent etait vivant.
    """
    debut = getattr(agent, "debut_partie", None)
    if debut is not None:
        # L'agent raisonne par rapport a sa direction : il doit savoir dans
        # quel sens le serpent part.
        debut(board.direction)

    while board.alive and board.steps < MAX_STEPS_PER_SESSION:
        vision = board.vision_chars()
        action = agent.choose(vision) if agent else board.direction
        event = board.step(action)

        if agent is not None and reward_fn is not None:
            learn = getattr(agent, "learn", None)
            if learn is not None:
                after = vision if board.dead else board.vision_chars()
                learn(vision, action, reward_fn(event), after, board.dead)

        if trace:
            for line in board.vision_lines():
                print(line)
            print("Action : {}".format(bd.ACTION_NAMES.get(action, "?")))

    if board.alive:
        # Limite de securite atteinte sans que le plateau ait fini la partie.
        # On la termine proprement : sans cause de fin, les statistiques
        # planteraient.
        board.truncate()

    fin = getattr(agent, "fin_partie", None)
    if fin is not None:
        # L'agent apprend la partie qui vient de se terminer.
        fin()
    return board.end_cause


def run_sessions(config, agent=None, reward_fn=None):
    """Enchaine config.sessions parties sans ouvrir de fenetre."""
    board = bd.Board(size=config.size, rng=random.Random())
    stats = SessionStats()
    # Une graine par partie (src/graine.py) : la partie n se rejoue seule
    # avec -seed <graine de depart + n - 1>.
    depart = gr.graine_de_depart(config.seed)
    print("Graine de depart : {} (partie n : graine {} + n - 1)".format(
        depart, depart))

    for index in range(config.sessions):
        gr.nouvelle_partie(board, agent, gr.graine_partie(depart, index + 1))
        try:
            play_session(board, agent, reward_fn, trace=config.trace)
        except KeyboardInterrupt:
            # Ctrl+C pendant un long entrainement : les parties terminees
            # sont gardees, celle qui etait en cours est en general perdue.
            print("\nInterruption : arret apres {} parties completes".format(
                stats.games))
            break
        stats.record(board)
        print(
            "Fin de la partie, longueur maximale = {}, "
            "duree maximale = {}".format(board.max_length, board.steps)
        )

    print(stats.summary())
    print(stats.causes_summary())
    if config.save_path:
        save = getattr(agent, "save", None)
        if save is None:
            print(
                "Aucun agent a sauvegarder : {} n'a pas ete ecrit".format(
                    config.save_path
                )
            )
        else:
            save(config.save_path)
            print(
                "Sauvegarde de l'etat d'apprentissage dans {}".format(
                    config.save_path
                )
            )
    return stats
