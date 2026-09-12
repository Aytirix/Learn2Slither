"""Agents de reference, sans aucun apprentissage.

Ils servent de barre a battre : si l'agent Q-learning ne les depasse pas
clairement, le probleme est dans l'encodage de l'etat ou les recompenses,
pas dans les hyperparametres.
"""

import random

from .environment import board as bd


class RandomAgent:
    """Tire une direction au hasard : le plancher de performance."""

    def __init__(self, rng=None):
        self.rng = rng or random.Random()

    def choose(self, vision):
        return self.rng.choice(bd.DIRECTIONS)


BASELINES = {
    "random": RandomAgent,
}


def derive_seed(seed):
    """Graine de l'agent, distincte de celle du plateau.

    Semer les deux avec la meme valeur donne deux flux identiques, consommes
    differemment : les tirages de l'agent seraient correles aux apparitions
    de pommes. `None` reste `None` : on ne force pas le determinisme.
    """
    return None if seed is None else seed + 1


def make(name, rng=None):
    """Instancie une baseline par son nom ; None si aucun nom n'est donne."""
    if not name:
        return None
    if name not in BASELINES:
        raise ValueError(
            "baseline inconnue : {!r}, choix possibles : {}".format(
                name, ", ".join(sorted(BASELINES))
            )
        )
    return BASELINES[name](rng)
