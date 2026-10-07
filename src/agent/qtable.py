"""La table Q : pour chaque etat, une valeur par action.

C'est la memoire de l'agent. Chaque valeur repond a la question : "dans
cette situation, a quel point cette action est-elle bonne ?"

    (('R', 2), ('G', 2), ('W', 3))  ->  [-0.8, 4.2, -12.5]
                                        tout   gauche droite
                                        droit

La table retient aussi, pour chaque couple (etat, action), combien de fois
il a ete appris : c'est ce compteur qui regle la force des corrections
(etape 8, IA.md section 8.1).
"""

from .interpreter import ACTIONS

# Valeur donnee aux actions d'un etat jamais vu (IA.md section 8.4).
VALEUR_INITIALE = 1.0


class QTable:
    """Memoire de l'agent : etat -> [tout droit, gauche, droite]."""

    def __init__(self, valeur_initiale=VALEUR_INITIALE):
        self.valeur_initiale = valeur_initiale
        # etat -> [valeur tout droit, valeur gauche, valeur droite]
        self.table = {}
        # etat -> [nb de mises a jour de chacune des 3 actions]
        self.visites = {}

    def __len__(self):
        """Nombre d'etats deja rencontres : len(q)."""
        return len(self.table)

    def __contains__(self, etat):
        """Cet etat a-t-il deja ete rencontre : etat in q."""
        return etat in self.table

    def valeurs(self, etat):
        """Les valeurs des actions dans `etat`, dans l'ordre de ACTIONS.

        Un etat jamais vu est cree a la volee, avec `valeur_initiale` pour
        chacune des actions. Un etat deja connu est renvoye tel quel.

        Renvoie la liste STOCKEE dans la table, pas une copie : modifier la
        liste renvoyee modifie la table. C'est ce que fera l'apprentissage.
        """
        # Seul un etat inconnu recoit une liste neuve : un etat connu garde
        # ce qu'il a appris (piege 1), et chaque etat a SA propre liste,
        # fabriquee ici, au moment ou il apparait (piege 2).
        if etat not in self.table:
            self.table[etat] = [self.valeur_initiale] * len(ACTIONS)
        return self.table[etat]

    def lire(self, etat):
        """Les valeurs des actions dans `etat`, en LECTURE SEULE.

        Contrairement a valeurs(), un etat inconnu n'est pas cree : on
        renvoie seulement ce qu'il vaudrait, sans l'ajouter a la table. Et
        on renvoie une copie : la modifier ne change rien.

        Indispensable pour -dontlearn : un agent fige qui decouvre une
        situation nouvelle ne doit pas, en la regardant, l'ajouter a la table
        et donc modifier le modele qu'on evalue.
        """
        if etat in self.table:
            return list(self.table[etat])
        return [self.valeur_initiale] * len(ACTIONS)

    def compter_visite(self, etat, action):
        """Ajoute une mise a jour au couple (etat, action) et renvoie le total.

        Premier appel pour ce couple -> 1, deuxieme -> 2, etc.
        """
        if etat not in self.visites:
            self.visites[etat] = [0] * len(ACTIONS)
        self.visites[etat][action] += 1
        return self.visites[etat][action]

    def nb_visites(self, etat, action):
        """Nombre de mises a jour deja faites sur (etat, action)."""
        if etat not in self.visites:
            return 0
        return self.visites[etat][action]
