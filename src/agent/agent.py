"""Agent Q-learning : choisit les actions et apprend de leurs consequences.

Deroulement d'une partie vu par l'agent :

    debut_partie(cap)          sens de depart du serpent
    |
    |  a chaque pas :
    |    choose(vision)        regarde, choisit, renvoie UP/LEFT/DOWN/RIGHT
    |    learn(...)            recoit la recompense du pas et la garde de
    |                          cote dans la trajectoire
    |
    fin_partie()               reprend la trajectoire et met la table a jour

Les choix de parametres sont expliques plus en detail dans IA.md.
"""

import random

from . import interpreter as it
from .interpreter import ACTIONS
from .qtable import QTable

# Facteur d'actualisation : le poids du futur dans la valeur d'un coup.
# Avec 0.95, l'agent voit a peu pres 1 / (1 - 0.95) = 20 coups devant lui.
GAMMA = 0.95

# alpha = 1 / n ** 0.7, ou n est le nombre de mises a jour du couple.
EXPOSANT_ALPHA = 0.7

# Exploration minimale : meme bien entraine, 1 coup sur 100 au hasard.
EPSILON_MIN = 0.01

# Nombre de pas apres lequel epsilon arrive a son minimum (environ 200
# parties). Resultats obtenus sur 1 000 parties d'entrainement, 4 graines,
# puis 100 parties sans apprentissage :
#
#     pas_cible     2 000   5 000   10 000   20 000   50 000
#     moyenne       22,7    21,7    20,1     18,0     7,1
#
# Une exploration courte suffit : la table demarre a +1, donc chaque
# situation nouvelle est deja essayee, et les parties jouees au hasard sont
# trop courtes pour apprendre grand-chose. 2 000 donne parfois un peu mieux
# mais varie plus selon la graine, j'ai garde 5 000 pour la stabilite.
PAS_CIBLE = 5_000


class Agent:
    """Agent Q-learning sur l'etat egocentrique de l'interpreteur."""

    def __init__(self, epsilon=1.0, rng=None, qtable=None, gamma=GAMMA,
                 epsilon_min=EPSILON_MIN, pas_cible=PAS_CIBLE, apprend=True):
        # Probabilite de jouer au hasard plutot que la meilleure action.
        self.epsilon = epsilon
        # Valeur d'epsilon au tout debut, avant qu'il commence a baisser.
        self.epsilon_depart = epsilon
        self.epsilon_min = epsilon_min
        self.pas_cible = pas_cible
        # L'agent a son propre generateur : avec une graine fixee, une
        # partie se rejoue exactement pareil.
        self.rng = rng or random.Random()
        self.q = qtable if qtable is not None else QTable()
        self.gamma = gamma
        # Faux avec -dontlearn : l'agent joue mais n'apprend rien.
        self.apprend = apprend

        # Partie en cours.
        self.cap = None              # direction actuelle du serpent
        self.dernier_choix = None    # (etat, action relative, direction)
        self.trajectoire = []        # pas de la partie, appris a la fin

        # Totaux depuis la creation de l'agent, enregistres dans le modele.
        self.pas_total = 0           # pas joues en apprenant (pour epsilon)
        self.parties = 0             # parties terminees en apprenant

    # -- choix de l'action (epsilon-greedy) ----------------------------------

    def choisir_action(self, etat):
        """Action relative a jouer dans `etat` : TOUT_DROIT, GAUCHE ou DROITE.

        - avec la probabilite `epsilon` : une action au hasard parmi les 3
          (exploration) ;
        - sinon : l'action de plus grande valeur dans la table
          (exploitation), en tirant au hasard parmi les ex-aequo.

        Par exemple avec epsilon = 0.1 : 9 fois sur 10 il prend la meilleure
        action, 1 fois sur 10 il tire au hasard. Comme le tirage peut
        retomber sur la meilleure, il la joue en fait 90 % + 10 % / 3, soit
        environ 93 % du temps.
        """
        # Exploration : rng.random() est entre 0 et 1, il passe sous epsilon
        # avec une probabilite egale a epsilon.
        if self.rng.random() < self.epsilon:
            return self.rng.choice(ACTIONS)

        # Exploitation. Pas de `valeurs.index(max(valeurs))` ici : sur un
        # etat neuf [1, 1, 1], ca renverrait toujours la premiere action et
        # le serpent irait toujours tout droit. On tire parmi les ex-aequo.
        # lire() plutot que valeurs() pour ne pas toucher a la table.
        valeurs = self.q.lire(etat)
        meilleure = max(valeurs)
        candidates = [a for a in ACTIONS if valeurs[a] == meilleure]
        return self.rng.choice(candidates)

    # -- appels faits par la boucle de jeu -----------------------------------

    def debut_partie(self, cap):
        """Nouvelle partie : le serpent part dans la direction `cap`.

        C'est la seule fois ou l'agent recoit sa direction (elle se voit
        aussi dans la vision : le cou est colle a la tete). Ensuite il la
        tient a jour lui-meme, a partir du coup qu'il vient de jouer.
        """
        self.cap = cap
        self.dernier_choix = None
        self.trajectoire = []

    def choose(self, vision):
        """Choisit le prochain pas et renvoie UP, LEFT, DOWN ou RIGHT.

        1. resume la vision dans le repere du serpent (interpreter.encode) ;
        2. choisit tout droit, gauche ou droite ;
        3. traduit ce choix en direction du plateau (interpreter.tourner).
        """
        if self.cap is None:
            raise RuntimeError(
                "debut_partie(cap) doit etre appele avant le premier pas"
            )
        etat = it.encode(vision, self.cap)
        action = self.choisir_action(etat)
        direction = it.tourner(self.cap, action)

        # Garde pour learn(), qui doit savoir quel etat et quelle action
        # enregistrer.
        self.dernier_choix = (etat, action, direction)
        self.cap = direction

        if self.apprend:
            self.pas_total += 1
            self.mettre_a_jour_epsilon()
        return direction

    def learn(self, vision, direction, recompense, vision_suivante, mort):
        """Enregistre le resultat du dernier pas, pour l'apprendre a la fin.

        `mort` vient de board.dead : il reste faux quand la partie est
        tronquee, puisque le serpent etait encore vivant. Sur une vraie
        mort, il n'y a pas d'etat suivant.

        La table n'est mise a jour qu'en fin de partie (voir fin_partie).
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
        # Apres le pas, le serpent regarde dans la direction jouee : on
        # encode la nouvelle vision dans ce repere-la.
        etat_suivant = (None if mort
                        else it.encode(vision_suivante, direction))
        self.trajectoire.append(
            (etat, action, recompense, etat_suivant, mort)
        )

    # -- mise a jour de Bellman ----------------------------------------------

    def mettre_a_jour(self, etat, action, recompense, etat_suivant, mort):
        """Corrige Q(etat, action) d'apres ce qui s'est vraiment passe.

        La cible est la recompense du pas, plus la valeur de la situation
        ou il mene :

            mort  : cible = recompense            (il n'y a pas de suite)
            sinon : cible = recompense + gamma * max Q(etat_suivant)

        On rapproche ensuite l'ancienne valeur de la cible, d'une fraction
        alpha de l'ecart :

            Q <- Q + alpha * (cible - Q)

        Exemple : Q = 1.0, le pas coute -1 et mene a un etat dont la
        meilleure valeur est 1.0. Cible = -1 + 0.95 * 1.0 = -0.05. Avec
        alpha = 1 (premiere visite), Q passe a -0.05.
        """
        valeurs = self.q.valeurs(etat)
        if mort:
            cible = recompense
        else:
            meilleure_suite = max(self.q.lire(etat_suivant))
            cible = recompense + self.gamma * meilleure_suite
        alpha = self.alpha(self.q.compter_visite(etat, action))
        valeurs[action] += alpha * (cible - valeurs[action])

    # -- taux d'apprentissage -----------------------------------------------

    @staticmethod
    def alpha(n):
        """Poids de la correction a la n-ieme mise a jour d'un couple.

            n = 1     -> 1.00  la premiere observation compte en entier
            n = 10    -> 0.20
            n = 100   -> 0.04
            n = 1000  -> 0.008 la valeur ne bouge presque plus

        Les pommes tombent au hasard, donc une valeur vue souvent doit se
        comporter comme une moyenne, et pas suivre la derniere partie.
        """
        return 1.0 / n ** EXPOSANT_ALPHA

    # -- apprentissage en fin de partie --------------------------------------

    def fin_partie(self):
        """Apprend la partie terminee, pas par pas, du premier au dernier.

        Pendant la partie, learn() a seulement mis chaque pas de cote : toute
        la partie est donc jouee avec la meme table, puis apprise d'un coup.

        J'ai aussi essaye d'apprendre a l'envers, en partant de la mort, pour
        que le -50 remonte plus vite. Ca ne marche pas vraiment :
        l'avant-dernier pas regarde la meilleure action de l'etat suivant, pas
        celle qui a tue, et les autres actions valent encore +1. Resultats
        sur 8 graines, 2 000 parties, puis 100 parties sans apprentissage
        (ecart-type d'environ 3) :

            dans l'ordre  27,2    a l'envers  25,4    a chaque pas  25,5

        L'ordre normal est un peu devant, sans grosse difference.
        """
        if self.apprend:
            for transition in self.trajectoire:
                self.mettre_a_jour(*transition)
            if self.trajectoire:
                self.parties += 1
        self.trajectoire = []
        self.dernier_choix = None

    # -- baisse d'epsilon ----------------------------------------------------

    def mettre_a_jour_epsilon(self):
        """Fait baisser epsilon en ligne droite, en fonction des pas joues.

            pas_total = 0              -> epsilon = epsilon_depart (1.0)
            pas_total = pas_cible / 2  -> 0.5
            pas_total >= pas_cible     -> epsilon_min (0.01)

        On compte les pas plutot que les parties : au debut une partie dure
        5 pas, a la fin plusieurs centaines. En comptant les parties, toute
        l'exploration passerait dans les premieres, qui sont les plus courtes.
        """
        restant = 1.0 - self.pas_total / self.pas_cible
        self.epsilon = max(self.epsilon_min, self.epsilon_depart * restant)

    # -- -dontlearn ----------------------------------------------------------

    def figer(self):
        """Mode evaluation (-dontlearn) : ni exploration ni apprentissage.

        Sert a voir ce que vaut un modele sans le modifier et sans coups
        joues au hasard.
        """
        self.apprend = False
        self.epsilon = 0.0
        self.epsilon_depart = 0.0

    # -- sauvegarde ----------------------------------------------------------

    def save(self, chemin):
        """Ecrit l'etat d'apprentissage dans un fichier (voir modele.py)."""
        from .modele import sauvegarder
        sauvegarder(self, chemin)
