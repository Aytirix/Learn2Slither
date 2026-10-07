"""Etape 3 : le repere egocentrique, tourner a gauche et a droite.

Rappel des coordonnees du plateau : x augmente vers la droite, y augmente
vers le BAS de l'ecran. UP vaut donc (0, -1).
"""

import unittest

from src.agent import interpreter as it
from src.environment import board as bd
from tests.helpers import plateau_nu, pose

OPPOSE = {bd.UP: bd.DOWN, bd.DOWN: bd.UP, bd.LEFT: bd.RIGHT, bd.RIGHT: bd.LEFT}


class TestToutDroit(unittest.TestCase):
    def test_garde_le_cap(self):
        for cap in bd.DIRECTIONS:
            with self.subTest(cap=bd.ACTION_NAMES[cap]):
                self.assertEqual(it.tourner(cap, it.TOUT_DROIT), cap)


class TestGauche(unittest.TestCase):
    """Imagine-toi a la place du serpent, sur l'ecran."""

    def test_les_quatre_caps(self):
        attendu = {
            bd.UP: bd.LEFT,       # je monte, a ma gauche : l'ouest
            bd.LEFT: bd.DOWN,     # je vais a gauche, a ma gauche : le bas
            bd.DOWN: bd.RIGHT,    # je descends, a ma gauche : l'est
            bd.RIGHT: bd.UP,      # je vais a droite, a ma gauche : le haut
        }
        for cap, nouveau in attendu.items():
            with self.subTest(cap=bd.ACTION_NAMES[cap]):
                self.assertEqual(it.tourner(cap, it.GAUCHE), nouveau)


class TestDroite(unittest.TestCase):
    def test_les_quatre_caps(self):
        attendu = {
            bd.UP: bd.RIGHT,
            bd.RIGHT: bd.DOWN,
            bd.DOWN: bd.LEFT,
            bd.LEFT: bd.UP,
        }
        for cap, nouveau in attendu.items():
            with self.subTest(cap=bd.ACTION_NAMES[cap]):
                self.assertEqual(it.tourner(cap, it.DROITE), nouveau)


class TestProprietes(unittest.TestCase):
    def test_quatre_fois_a_gauche_font_un_tour(self):
        for cap in bd.DIRECTIONS:
            nouveau = cap
            for _ in range(4):
                nouveau = it.tourner(nouveau, it.GAUCHE)
            self.assertEqual(nouveau, cap)

    def test_gauche_puis_droite_revient_au_cap(self):
        for cap in bd.DIRECTIONS:
            aller = it.tourner(cap, it.GAUCHE)
            self.assertEqual(it.tourner(aller, it.DROITE), cap)

    def test_jamais_de_demi_tour(self):
        """La seule direction mortelle a coup sur n'est jamais produite."""
        for cap in bd.DIRECTIONS:
            for action in it.ACTIONS:
                with self.subTest(cap=bd.ACTION_NAMES[cap], action=action):
                    self.assertNotEqual(it.tourner(cap, action), OPPOSE[cap])

    def test_toujours_une_direction_du_sujet(self):
        for cap in bd.DIRECTIONS:
            for action in it.ACTIONS:
                self.assertIn(it.tourner(cap, action), bd.DIRECTIONS)

    def test_action_inconnue(self):
        with self.assertRaises(ValueError):
            it.tourner(bd.UP, 7)


class TestDirectionsRelatives(unittest.TestCase):
    def test_ordre_devant_gauche_droite(self):
        self.assertEqual(
            it.directions_relatives(bd.UP), (bd.UP, bd.LEFT, bd.RIGHT)
        )

    def test_coherent_avec_tourner(self):
        for cap in bd.DIRECTIONS:
            self.assertEqual(
                it.directions_relatives(cap),
                tuple(it.tourner(cap, action) for action in it.ACTIONS),
            )


class TestSurLeVraiPlateau(unittest.TestCase):
    """La geometrie doit correspondre a ce qu'on voit a l'ecran."""

    def test_tourner_a_gauche_en_allant_a_droite_fait_monter(self):
        board = pose(plateau_nu(size=10), (5, 5), bd.RIGHT)
        board.step(it.tourner(bd.RIGHT, it.GAUCHE))
        self.assertEqual(board.snake[0], (5, 4), "y diminue : on monte")

    def test_tourner_a_droite_en_allant_a_droite_fait_descendre(self):
        board = pose(plateau_nu(size=10), (5, 5), bd.RIGHT)
        board.step(it.tourner(bd.RIGHT, it.DROITE))
        self.assertEqual(board.snake[0], (5, 6), "y augmente : on descend")

    def test_aucune_action_ne_tue_contre_le_cou(self):
        for cap in bd.DIRECTIONS:
            for action in it.ACTIONS:
                with self.subTest(cap=bd.ACTION_NAMES[cap], action=action):
                    board = pose(plateau_nu(size=10), (5, 5), cap)
                    board.step(it.tourner(cap, action))
                    self.assertNotEqual(board.end_cause, bd.BODY)


if __name__ == "__main__":
    unittest.main()
