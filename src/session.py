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

# Plafond de securite de la boucle de jeu. `Board` tronque deja les parties
# qui tournent en rond ; ce garde-fou-la protege contre un bug qui laisserait
# `alive` a vrai, cas ou la boucle ne rendrait jamais la main (et ou la suite
# de tests se figerait au lieu d'echouer).
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

        Ce n'est pas la longueur moyenne instantanee : c'est la moyenne des
        records de chaque partie. C'est la vraie mesure de progression, le
        maximum global etant surtout de la chance.
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

    Deux notions distinctes circulent ici, et les confondre est le bug que
    tout ce decoupage sert a eviter :

    - `event` est l'evenement de jeu du pas (deplacement, pomme, mort). Il
      determine la RECOMPENSE. Une troncature ne le modifie pas : le pas qui
      atteint la limite est un deplacement ordinaire et garde son cout.
    - `board.dead` dit s'il existe un apres. Il determine le BOOTSTRAP. Il
      est faux sur une troncature, car le serpent etait vivant.
    """
    debut = getattr(agent, "debut_partie", None)
    if debut is not None:
        # L'agent raisonne dans le repere du serpent : il doit savoir dans
        # quel sens celui-ci part (IA.md section 6.6).
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
        # Plafond atteint : le plateau n'a pas termine la partie lui-meme.
        # On la termine proprement, sinon `end_cause` resterait a None et une
        # partie finie sans cause casserait les statistiques.
        board.truncate()

    fin = getattr(agent, "fin_partie", None)
    if fin is not None:
        # C'est ici que l'agent apprend : il rejoue la partie, dans l'ordre.
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
            # Ctrl+C sur un long entrainement : on garde ce qui est appris.
            # Les parties terminees sont gardees ; celle qui etait en cours
            # n'est en general pas apprise.
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
