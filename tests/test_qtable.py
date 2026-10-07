"""Etape 5 : la table Q et son initialisation."""

import unittest

from src.agent import interpreter as it
from src.agent import qtable as qt
from src.environment import board as bd

ETAT_A = (("R", 2), ("G", 2), ("W", 3))
ETAT_B = (("W", 1), ("S", 2), ("W", 3))


class TestDepart(unittest.TestCase):
    def test_table_vide_au_depart(self):
        self.assertEqual(len(qt.QTable()), 0)

    def test_valeur_initiale_par_defaut(self):
        self.assertEqual(qt.VALEUR_INITIALE, 1.0)


class TestEtatInconnu(unittest.TestCase):
    def test_une_valeur_par_action(self):
        valeurs = qt.QTable().valeurs(ETAT_A)
        self.assertEqual(len(valeurs), len(it.ACTIONS))

    def test_initialise_a_la_valeur_initiale(self):
        self.assertEqual(qt.QTable().valeurs(ETAT_A), [1.0, 1.0, 1.0])

    def test_valeur_initiale_reglable(self):
        """Elle sera reglee par le sweep : elle ne doit pas etre en dur."""
        self.assertEqual(qt.QTable(0.0).valeurs(ETAT_A), [0.0, 0.0, 0.0])
        self.assertEqual(qt.QTable(5.0).valeurs(ETAT_A), [5.0, 5.0, 5.0])

    def test_l_etat_est_memorise(self):
        q = qt.QTable()
        q.valeurs(ETAT_A)
        self.assertEqual(len(q), 1)
        self.assertIn(ETAT_A, q)
        self.assertNotIn(ETAT_B, q)


class TestEtatConnu(unittest.TestCase):
    def test_relire_ne_cree_pas_de_doublon(self):
        q = qt.QTable()
        q.valeurs(ETAT_A)
        q.valeurs(ETAT_A)
        self.assertEqual(len(q), 1)

    def test_modifier_la_liste_modifie_la_table(self):
        """L'apprentissage ecrira dans la liste renvoyee."""
        q = qt.QTable()
        q.valeurs(ETAT_A)[it.GAUCHE] = 4.2
        self.assertEqual(q.valeurs(ETAT_A), [1.0, 4.2, 1.0])

    def test_relire_n_efface_pas_ce_qui_a_ete_appris(self):
        """Piege : recreer la liste a chaque lecture efface l'apprentissage."""
        q = qt.QTable()
        q.valeurs(ETAT_A)[it.TOUT_DROIT] = -50.0
        q.valeurs(ETAT_A)
        q.valeurs(ETAT_A)
        self.assertEqual(q.valeurs(ETAT_A)[it.TOUT_DROIT], -50.0)


class TestEtatsIndependants(unittest.TestCase):
    """Piege Python classique : deux etats qui partagent la meme liste."""

    def test_deux_etats_ont_deux_listes_distinctes(self):
        q = qt.QTable()
        self.assertIsNot(q.valeurs(ETAT_A), q.valeurs(ETAT_B))

    def test_apprendre_sur_un_etat_ne_touche_pas_l_autre(self):
        q = qt.QTable()
        q.valeurs(ETAT_B)
        q.valeurs(ETAT_A)[it.DROITE] = -12.5
        self.assertEqual(q.valeurs(ETAT_B), [1.0, 1.0, 1.0])


class TestLectureSeule(unittest.TestCase):
    """lire() : regarder un etat sans jamais modifier la table."""

    def test_etat_inconnu_non_cree(self):
        q = qt.QTable()
        self.assertEqual(q.lire(ETAT_A), [1.0, 1.0, 1.0])
        self.assertEqual(len(q), 0)
        self.assertNotIn(ETAT_A, q)

    def test_etat_connu_lu_tel_quel(self):
        q = qt.QTable()
        q.valeurs(ETAT_A)[it.GAUCHE] = 4.2
        self.assertEqual(q.lire(ETAT_A), [1.0, 4.2, 1.0])

    def test_etat_inconnu_lu_a_la_valeur_initiale_reglee(self):
        self.assertEqual(qt.QTable(0.5).lire(ETAT_A), [0.5, 0.5, 0.5])

    def test_modifier_la_lecture_ne_change_pas_la_table(self):
        q = qt.QTable()
        q.valeurs(ETAT_A)
        q.lire(ETAT_A)[it.GAUCHE] = 99.0
        self.assertEqual(q.valeurs(ETAT_A), [1.0, 1.0, 1.0])


class TestAvecDeVraisEtats(unittest.TestCase):
    def test_compte_les_etats_rencontres(self):
        """len(q) mesurera combien de situations le serpent a vues."""
        q = qt.QTable()
        board = bd.Board(size=10)
        vus = set()
        for _ in range(100):
            board.reset()
            etat = it.encode(board.vision_chars(), board.direction)
            q.valeurs(etat)
            vus.add(etat)
        self.assertEqual(len(q), len(vus))


if __name__ == "__main__":
    unittest.main()
