"""Etape 12 : fabriquer l'agent que demande la ligne de commande.

    -baseline random    -> agent de reference, sans apprentissage
    -load FICHIER       -> agent recharge depuis un modele (etape 11)
    (rien)              -> agent neuf, qui part de zero
    -dontlearn          -> l'agent ci-dessus, fige : il joue sans apprendre
"""

from .. import baselines
from . import modele
from .agent import Agent


def creer_agent(config, rng=None):
    """Agent correspondant a `config` (voir src/config.py).

    Peut lever modele.ErreurModele si le fichier passe a -load est absent
    ou incompatible : c'est a l'appelant d'afficher le message.
    """
    if config.baseline:
        return baselines.make(config.baseline, rng)

    if config.model:
        agent = modele.charger(config.model, rng=rng)
        print("Chargement du modele entraine depuis {} ({} parties)".format(
            config.model, agent.parties))
    else:
        agent = Agent(rng=rng)

    if not config.learn:
        agent.figer()
    return agent
