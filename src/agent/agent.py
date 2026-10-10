"""L'agent : il choisit les actions et apprend de leurs consequences.

Vue d'ensemble d'une partie, du point de vue de l'agent :

    debut_partie(cap)          on lui dit dans quel sens part le serpent
    |
    |  a chaque pas :
    |    choose(vision)        il regarde, choisit, renvoie UP/LEFT/DOWN/RIGHT
    |    learn(...)            on lui dit ce que ce pas a rapporte ;
    |                          il le NOTE dans sa trajectoire (sans apprendre)
    |
    fin_partie()               il rejoue la partie et apprend

Le cours complet est dans IA.md ; chaque section ci-dessous renvoie a la
partie correspondante.
"""

import random

from . import interpreter as it
from .interpreter import ACTIONS
from .qtable import QTable

# Facteur d'actualisation : combien compte le futur (IA.md section 2.3).
# 0.95 -> l'agent raisonne a peu pres sur 1 / (1 - 0.95) = 20 coups.
GAMMA = 0.95

# Exposant de la decroissance de alpha : alpha = 1 / n ** 0.7 (section 8.1).
EXPOSANT_ALPHA = 0.7

# Plancher de l'exploration : meme entraine, 1 coup sur 100 au hasard.
EPSILON_MIN = 0.01

# Nombre de pas cumules au bout duquel epsilon atteint son plancher
# (section 5.2). Valeur MESUREE (IA.md section 5.3) : 1 000 parties
# d'entrainement, 4 graines, evaluation figee sur 100 parties :
#
#     pas_cible     2 000   5 000   10 000   20 000   50 000
#     moyenne       22,7    21,7    20,1     18,0     7,1
#
# Ici, sortir vite de l'exploration paie : l'initialisation optimiste
# (+1) fait deja explorer chaque situation nouvelle, et des parties jouees
# au hasard sont courtes, donc apprennent peu. 2 000 a fait aussi bien ou
# mieux (un audit independant l'a mesure a 28 contre 23), mais en variant
# davantage d'une graine a l'autre : 5 000 a ete garde pour sa stabilite,
# et reste un candidat pour le sweep (IA.md section 8.5). Epsilon atteint
# son plancher apres environ 200 parties.
PAS_CIBLE = 5_000


class Agent:
    """Agent Q-learning sur l'etat egocentrique de l'interpreteur."""

    def __init__(self, epsilon=1.0, rng=None, qtable=None, gamma=GAMMA,
                 epsilon_min=EPSILON_MIN, pas_cible=PAS_CIBLE, apprend=True,
                 vision=it.VISION_CROIX):
        # Probabilite de jouer au hasard plutot que la meilleure action.
        self.epsilon = epsilon
        # Valeur de depart d'epsilon, avant toute decroissance (etape 10).
        self.epsilon_depart = epsilon
        self.epsilon_min = epsilon_min
        self.pas_cible = pas_cible
        # Generateur aleatoire propre a l'agent, pour qu'une graine fixe
        # rende une partie entierement reproductible.
        self.rng = rng or random.Random()
        self.q = qtable if qtable is not None else QTable()
        self.gamma = gamma
        # Faux avec -dontlearn : l'agent joue mais n'apprend rien.
        self.apprend = apprend
        # "croix" (le sujet) ou "plateau" (option HORS SUJET : l'agent
        # recoit aussi des informations de tout le plateau, voir
        # src/environment/plateau_complet.py).
        if vision not in it.VISIONS:
            raise ValueError("vision inconnue : {!r}".format(vision))
        self.vision = vision

        # Etat de la partie en cours.
        self.cap = None              # direction actuelle du serpent
        self.dernier_choix = None    # (etat, action relative, direction)
        self.trajectoire = []        # transitions notees, rejouees a la fin

        # Compteurs cumules sur toute la vie de l'agent, sauvegardes.
        self.pas_total = 0           # pas joues en apprenant (etape 10)
        self.parties = 0             # parties terminees en apprenant

    # -- Etape 6 : choisir une action (IA.md section 5) ----------------------

    def choisir_action(self, etat):
        """Action relative a jouer dans `etat` : TOUT_DROIT, GAUCHE ou DROITE.

        - avec la probabilite `epsilon` : une action au hasard parmi les 3
          (exploration) ;
        - sinon : l'action de plus grande valeur dans la table
          (exploitation), en tirant au hasard parmi les ex-aequo.

        Exemple avec epsilon = 0.1 : 9 fois sur 10 il exploite, 1 fois sur
        10 il tire au hasard. Le tirage pouvant retomber sur la meilleure
        action, il la joue en tout 90 % + 10 % / 3 = environ 93 % du temps.
        """
        # Exploration. self.rng.random() tire un nombre entre 0 et 1 : il
        # tombe sous epsilon avec une probabilite exactement egale a epsilon.
        if self.rng.random() < self.epsilon:
            return self.rng.choice(ACTIONS)

        # Exploitation. On ne fait PAS `valeurs.index(max(valeurs))` : sur un
        # etat neuf [1, 1, 1], index() renverrait toujours la premiere action
        # et le serpent irait toujours tout droit (IA.md section 5.2).
        # lire() et non valeurs() : choisir ne doit jamais modifier la table.
        valeurs = self.q.lire(etat)
        meilleure = max(valeurs)
        candidates = [a for a in ACTIONS if valeurs[a] == meilleure]
        return self.rng.choice(candidates)

    # -- Le pas de jeu : interface avec la boucle (IA.md section 11) ---------

    def debut_partie(self, cap):
        """Nouvelle partie : le serpent part dans la direction `cap`.

        L'environnement maintient cette direction (board.direction) ; l'agent
        la lit ici une seule fois, puis la met a jour lui-meme a chaque pas.
        """
        self.cap = cap
        self.dernier_choix = None
        self.trajectoire = []

    def choose(self, vision):
        """Choisit le prochain pas et renvoie une direction ABSOLUE du sujet.

        1. encode la vision dans le repere du serpent (etapes 2 a 4) ;
        2. choisit une action relative (etape 6) ;
        3. la traduit en UP / LEFT / DOWN / RIGHT (etape 3).
        """
        if self.cap is None:
            raise RuntimeError(
                "debut_partie(cap) doit etre appele avant le premier pas"
            )
        etat = self.encoder(vision, self.cap)
        action = self.choisir_action(etat)
        direction = it.tourner(self.cap, action)

        # Retenu pour learn() : il saura quel etat et quelle action noter.
        self.dernier_choix = (etat, action, direction)
        self.cap = direction

        if self.apprend:
            self.pas_total += 1
            self.mettre_a_jour_epsilon()
        return direction

    def learn(self, vision, direction, recompense, vision_suivante, mort):
        """Note la consequence du dernier pas, sans apprendre tout de suite.

        `mort` vient de board.dead : il est FAUX sur une troncature (le
        serpent etait vivant, IA.md section 4.5). Sur une vraie mort, il n'y
        a pas d'etat suivant.

        L'apprentissage a lieu en fin de partie (etape 9).
        """
        if not self.apprend:
            return
        if self.dernier_choix is None:
            raise RuntimeError("learn() appele sans choose() juste avant")
        etat, action, direction_jouee = self.dernier_choix
        if direction != direction_jouee:
            raise ValueError(
                "learn() recoit {} alors que l'agent a joue {}".format(
                    direction, direction_jouee
                )
            )
        # Apres le pas, le cap du serpent est la direction jouee : c'est
        # dans ce repere qu'on encode ce qu'il voit maintenant.
        etat_suivant = (None if mort
                        else self.encoder(vision_suivante, direction))
        self.trajectoire.append(
            (etat, action, recompense, etat_suivant, mort)
        )

    @property
    def vision_complete(self):
        """Vrai si l'agent doit recevoir tout le plateau (hors sujet)."""
        return self.vision == it.VISION_PLATEAU

    def encoder(self, vision, cap):
        """Etat de la table : la croix, plus le plateau si vision_complete."""
        if self.vision_complete:
            return it.encode_complet(vision, cap)
        return it.encode(vision, cap)

    # -- Etape 7 : la mise a jour de Bellman (IA.md section 4) ---------------

    def mettre_a_jour(self, etat, action, recompense, etat_suivant, mort):
        """Corrige Q(etat, action) d'apres ce qui s'est vraiment passe.

        La cible, c'est ce que le pas a rapporte, plus ce que vaut la
        situation d'arrivee :

            mort  : cible = recompense            (pas d'apres, section 4.4)
            sinon : cible = recompense + gamma * max Q(etat_suivant)

        Puis on deplace l'ancienne valeur vers la cible, d'une fraction alpha
        de l'ecart :

            Q <- Q + alpha * (cible - Q)

        Exemple : Q = 1.0, le pas coute -1 et mene a un etat dont la
        meilleure valeur est 1.0. Cible = -1 + 0.95 * 1.0 = -0.05. Avec
        alpha = 1 (premiere fois), Q devient -0.05.
        """
        valeurs = self.q.valeurs(etat)
        if mort:
            cible = recompense
        else:
            meilleure_suite = max(self.q.lire(etat_suivant))
            cible = recompense + self.gamma * meilleure_suite
        alpha = self.alpha(self.q.compter_visite(etat, action))
        valeurs[action] += alpha * (cible - valeurs[action])

    # -- Etape 8 : alpha decroit avec les visites (IA.md section 8.1) --------

    @staticmethod
    def alpha(n):
        """Force de la correction a la n-ieme mise a jour d'un couple.

            n = 1     -> 1.00  la premiere observation est prise en entier
            n = 10    -> 0.20
            n = 100   -> 0.04
            n = 1000  -> 0.008 la valeur est etablie, elle bouge a peine

        Les pommes apparaissent au hasard : une valeur souvent visitee doit
        etre une moyenne stable, pas suivre la derniere partie.
        """
        return 1.0 / n ** EXPOSANT_ALPHA

    # -- Etape 9 : apprendre en fin de partie (IA.md section 4.7) ------------

    def fin_partie(self):
        """Apprend de la partie terminee, en rejouant ses pas DANS L'ORDRE.

        Pendant la partie, learn() a seulement note chaque pas. On les
        apprend maintenant, du premier au dernier : la partie entiere est
        jouee avec la meme table, et apprise d'un seul bloc.

        Pourquoi pas a l'envers ? On l'esperait plus rapide : en apprenant
        la mort d'abord, l'avant-dernier pas aurait du "voir" le -50. En
        general, il ne le voit pas : l'avant-dernier pas regarde la
        MEILLEURE action de l'etat suivant, pas celle qui a tue. Or les
        autres actions de cet etat valent encore +1 (jamais essayees) :
        le -50 reste bloque sur le
        dernier pas (IA.md section 4.7). Mesure sur 8 graines, 2 000 parties,
        evaluation figee sur 100 parties (ecart-type d'environ 3) :

            dans l'ordre  27,2    a l'envers  25,4    a chaque pas  25,5

        A l'envers n'apporte rien ; dans l'ordre est un peu devant, sans
        ecart decisif.
        """
        if self.apprend:
            for transition in self.trajectoire:
                self.mettre_a_jour(*transition)
            if self.trajectoire:
                self.parties += 1
        self.trajectoire = []
        self.dernier_choix = None

    # -- Etape 10 : epsilon decroit sur les pas (IA.md section 5.2) ----------

    def mettre_a_jour_epsilon(self):
        """Fait descendre epsilon en ligne droite, sur les pas cumules.

            pas_total = 0              -> epsilon = epsilon_depart (1.0)
            pas_total = pas_cible / 2  -> 0.5
            pas_total >= pas_cible     -> epsilon_min (0.01)

        Sur les pas et non sur les parties : une partie dure 5 pas au debut
        et des centaines a la fin. Compter les parties epuiserait
        l'exploration sur les toutes premieres, les plus courtes.
        """
        restant = 1.0 - self.pas_total / self.pas_cible
        self.epsilon = max(self.epsilon_min, self.epsilon_depart * restant)

    # -- -dontlearn ----------------------------------------------------------

    def figer(self):
        """Mode evaluation : plus d'exploration, plus d'apprentissage.

        C'est l'option -dontlearn du sujet : on mesure ce que le modele
        sait, sans le modifier et sans bruit aleatoire.
        """
        self.apprend = False
        self.epsilon = 0.0
        self.epsilon_depart = 0.0

    # -- Etape 11 : sauvegarde (voir modele.py) ------------------------------

    def save(self, chemin):
        """Ecrit l'etat d'apprentissage dans un fichier (voir modele.py)."""
        from .modele import sauvegarder
        sauvegarder(self, chemin)
