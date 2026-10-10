"""Une graine par partie : n'importe quelle partie se rejoue a l'identique.

Principe
--------
Au lancement, on fixe une GRAINE DE DEPART (celle de -seed, ou un nombre
tire au hasard si -seed n'est pas donne). La partie numero n recoit ensuite
sa propre graine :

    graine de la partie n = graine de depart + n - 1

Exemple avec -seed 1000 : partie 1 -> 1000, partie 2 -> 1001, ...,
partie 847 -> 1846.

Au debut de CHAQUE partie, on resème le generateur du plateau (position du
serpent, pommes) et celui de l'agent (hasard d'exploration, egalites) avec
cette graine. Une partie ne depend donc plus de celles d'avant : pour revoir
la partie 847, il suffit de relancer avec -seed 1846, et c'est la partie 1.

Condition : le meme modele, fige. Un agent qui apprend change de table Q
d'une partie a l'autre ; il ne rejouerait pas les memes coups.
"""

import random

# Graine de depart tiree au hasard quand -seed n'est pas donne : un nombre
# court, facile a recopier depuis l'ecran.
GRAINE_MAX = 1_000_000


def graine_de_depart(seed=None):
    """La graine de -seed, ou une graine tiree au hasard si elle manque."""
    if seed is not None:
        return seed
    # SystemRandom : independant du module random, qu'une autre partie du
    # programme aurait pu semer.
    return random.SystemRandom().randrange(GRAINE_MAX)


def graine_partie(depart, numero):
    """Graine de la partie `numero` (la premiere partie a le numero 1)."""
    return depart + numero - 1


def semer_agent(agent, graine):
    """Resème le generateur de l'agent pour la partie de graine `graine`.

    La chaine "agent-<graine>" donne un flux different de celui du plateau
    (seme avec le nombre seul) : sinon les tirages de l'agent seraient
    correles aux apparitions de pommes. Un agent sans generateur (pilotage
    clavier, agent de test) est laisse tel quel.
    """
    rng = getattr(agent, "rng", None)
    if isinstance(rng, random.Random):
        rng.seed("agent-{}".format(graine))


def nouvelle_partie(board, agent, graine):
    """Remet le plateau a zero et seme plateau + agent avec `graine`."""
    board.reset(graine)
    semer_agent(agent, graine)
