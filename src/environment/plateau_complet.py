"""Option HORS SUJET : l'agent recoit des informations de TOUT le plateau.

Le sujet limite la vision aux 4 rayons de la croix et sanctionne (-42) toute
information en plus. Cette option existe pour comparer, et n'est jamais
active par defaut : elle se choisit a la creation d'un modele (ecran
ENTRAINEMENT), est enregistree dans le fichier du modele, et chaque ecran
qui utilise un tel modele l'affiche en avertissement.

En plus de la croix, l'environnement calcule deux faits sur tout le
plateau, en coordonnees absolues (l'agent les remet dans son repere) :

- piege : pour chaque direction, la case voisine est-elle un piege ?
  On "colorie" depuis cette case toutes les cases libres atteignables
  (remplissage par diffusion, comme le pot de peinture d'un logiciel de
  dessin). S'il y en a moins que la longueur du serpent, il ne pourra pas
  y tenir : c'est un piege. Une case occupee (mur, corps) est un piege.
- pomme : ecart (dx, dy) entre la tete et la pomme verte la plus proche,
  ou None s'il n'y en a pas.
"""

from collections import deque

from . import board as bd


class VueComplete(dict):
    """La croix habituelle (dict direction -> rayon) + le plateau resume."""

    def __init__(self, croix, pieges, pomme):
        super().__init__(croix)
        self.pieges = pieges      # direction -> True si piege
        self.pomme = pomme        # (dx, dy) ou None


def observer(board, complete=False):
    """Ce que l'agent recoit : la croix seule, ou la croix + le plateau."""
    croix = board.vision_chars()
    if not complete or not board.snake:
        return croix
    return VueComplete(croix, pieges(board), pomme_proche(board))


def pieges(board):
    """direction -> True si s'y engager mene a un espace trop petit."""
    tete = board.snake[0]
    # La queue avance au prochain pas : sa case sera libre.
    corps = set(board.snake[:-1])
    besoin = len(board.snake)
    return {
        d: _espace(board, (tete[0] + d[0], tete[1] + d[1]), corps,
                   besoin) < besoin
        for d in bd.DIRECTIONS
    }


def _espace(board, depart, corps, besoin):
    """Cases libres atteignables depuis `depart`, compte arrete a `besoin`
    (au-dela, la reponse ne change plus : inutile de tout colorier)."""
    if not board.inside(depart) or depart in corps:
        return 0
    vues = {depart}
    file = deque([depart])
    while file and len(vues) < besoin:
        x, y = file.popleft()
        for dx, dy in bd.DIRECTIONS:
            case = (x + dx, y + dy)
            if (case not in vues and board.inside(case)
                    and case not in corps):
                vues.add(case)
                file.append(case)
    return len(vues)


def pomme_proche(board):
    """(dx, dy) de la tete vers la pomme verte la plus proche, ou None."""
    if not board.greens:
        return None
    hx, hy = board.snake[0]
    gx, gy = min(board.greens,
                 key=lambda p: abs(p[0] - hx) + abs(p[1] - hy))
    return gx - hx, gy - hy
