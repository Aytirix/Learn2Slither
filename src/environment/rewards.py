"""Bareme de recompenses : evenement du pas -> nombre.

C'est l'environnement qui recompense l'agent, pas l'agent qui se recompense
lui-meme : le sujet parle de "rewards granted by the environment (or board)".
"""

from . import board as bd

BAREME = {
    bd.MOVE: -1,
    bd.GREEN: 20,
    bd.RED: -10,
    bd.WALL: -50,
    bd.BODY: -50,
    bd.STARVE: -50,
}


def recompense(event):
    """Recompense du pas qui a produit `event`.

    Un evenement absent du bareme doit lever KeyError : une erreur bruyante
    vaut mieux qu'une recompense inventee en silence.
    """
    if event in BAREME:
        return BAREME[event]
    raise KeyError(f"evenement {event!r} absent du bareme de recompenses")
