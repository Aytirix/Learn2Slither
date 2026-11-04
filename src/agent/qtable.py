"""La table Q : pour chaque etat, une valeur par action.

C'est la memoire de l'agent. Chaque valeur repond a la question : "dans
cette situation, a quel point cette action est-elle bonne ?"

    (('R', 2), ('G', 2), ('W', 3))  ->  [-0.8, 4.2, -12.5]
                                        tout   gauche droite
                                        droit

La table compte aussi, pour chaque couple (etat, action), le nombre de mises
a jour deja faites : c'est ce compteur qui fixe alpha (voir Agent.alpha).
"""

from .interpreter import ACTIONS

# Valeur de depart des actions d'un etat jamais vu. Un peu au-dessus de ce
# que rapporte un pas (-1), pour que les actions pas encore essayees soient
# tentees en premier.
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

        Renvoie la liste qui est dans la table, pas une copie : la modifier
        modifie la table, et c'est justement ce que fait l'apprentissage.
        """
        # On ne cree une liste que pour un etat inconnu, sinon on effacerait
        # ce qu'il a appris. Et chaque etat a bien sa propre liste, creee
        # ici : deux etats ne doivent jamais partager la meme.
        if etat not in self.table:
            self.table[etat] = [self.valeur_initiale] * len(ACTIONS)
        return self.table[etat]

    def lire(self, etat):
        """Les valeurs des actions dans `etat`, sans rien modifier.

        Contrairement a valeurs(), un etat inconnu n'est pas ajoute : on
        renvoie juste ce qu'il vaudrait. Et c'est une copie, la modifier ne
        change pas la table.

        C'est ce qui garantit -dontlearn : un agent fige qui tombe sur une
        situation nouvelle ne doit pas l'ajouter a la table, sinon le modele
        evalue changerait.
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
