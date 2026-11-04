"""Interpreteur : transforme la vision du serpent en un etat compact.

La vision recue est un dictionnaire de 4 chaines, une par direction :

    {UP: "0GW", LEFT: "SSW", DOWN: "00W", RIGHT: "0RW"}

Telle quelle, elle donne beaucoup trop d'etats differents pour une table Q.
Chaque rayon est donc resume en deux informations : la premiere chose vue,
et a quelle distance.
"""

from ..environment import board as bd

VIDE = bd.EMPTY_CHAR

# Au-dela de cette distance on ne fait plus la difference : "3" veut dire
# "3 ou plus". Plus la valeur est grande, plus il y a d'etats a apprendre.
DISTANCE_MAX = 3

# A changer des que la facon d'encoder un etat change. Un ancien modele
# aurait des cles qui ne correspondent plus aux etats calcules, et il
# jouerait n'importe comment sans erreur : modele.py refuse donc de le
# charger.
VERSION_ENCODAGE = 1


def lire_rayon(rayon):
    """Premiere chose vue sur un rayon, et sa distance plafonnee.

    La distance compte en cases depuis la tete : la case collee a la tete
    est a distance 1, pas 0.

        "S0W"       ->  ('S', 1)    corps colle a la tete
        "0R0W"      ->  ('R', 2)    pomme rouge a deux cases
        "000000GW"  ->  ('G', 3)    pomme verte a 7 cases, plafonnee a 3

    Leve ValueError si le rayon ne contient que du vide.
    """
    for i, char in enumerate(rayon):
        if char != VIDE:
            return char, min(i + 1, DISTANCE_MAX)
    raise ValueError("rayon ne contient que du vide")


# -- repere du serpent -------------------------------------------------------
#
# L'agent ne pense pas en HAUT / BAS / GAUCHE / DROITE, mais par rapport a la
# direction ou il va (son "cap") : tout droit, a gauche ou a droite.

TOUT_DROIT = 0
GAUCHE = 1
DROITE = 2
ACTIONS = (TOUT_DROIT, GAUCHE, DROITE)


def tourner(cap, action):
    """Direction absolue obtenue en appliquant une action relative au cap.

    `cap` est une direction de board.DIRECTIONS, `action` un element de
    ACTIONS. Leve ValueError si l'action est inconnue.

        tourner(bd.UP, TOUT_DROIT)  ->  bd.UP
        tourner(bd.UP, GAUCHE)      ->  bd.LEFT
        tourner(bd.UP, DROITE)      ->  bd.RIGHT
        tourner(bd.LEFT, TOUT_DROIT)    ->  bd.LEFT
        tourner(bd.LEFT, GAUCHE)    ->  bd.DOWN
        tourner(bd.LEFT, DROITE)     ->  bd.UP
        tourner(bd.DOWN, TOUT_DROIT)  ->  bd.DOWN
        tourner(bd.DOWN, GAUCHE)    ->  bd.RIGHT
    """

    if action == TOUT_DROIT:
        decalage = 0
    elif action == GAUCHE:
        decalage = 1
    elif action == DROITE:
        decalage = -1
    else:
        raise ValueError("action inconnue : {}".format(action))
    return bd.DIRECTIONS[(bd.DIRECTIONS.index(cap) + decalage) % 4]


def directions_relatives(cap):
    """Les trois directions absolues vues depuis le cap : (devant, gauche,
    droite).

        directions_relatives(bd.UP)  ->  (bd.UP, bd.LEFT, bd.RIGHT)
    """
    return (cap, tourner(cap, GAUCHE), tourner(cap, DROITE))


# -- l'etat complet ----------------------------------------------------------


def encode(vision, cap):
    """Etat compact du serpent : ce qu'il voit devant, a gauche, a droite.

    `vision` est le dictionnaire de board.vision_chars(), `cap` la direction
    ou va le serpent. Le rayon de derriere n'est pas lu.

    Renvoie un tuple de trois couples (symbole, distance), dans l'ordre
    (devant, gauche, droite) :

        (('R', 2), ('G', 2), ('W', 3))
    """
    etat = []
    for direction in directions_relatives(cap):
        rayon = vision[direction]
        etat.append(lire_rayon(rayon))
    return tuple(etat)
