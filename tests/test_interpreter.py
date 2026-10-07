"""Etape 2 : lire un rayon de vision."""

import unittest

from src.agent import interpreter as it
from src.environment import board as bd
from tests.helpers import pose


class TestPremierSymbole(unittest.TestCase):
    def test_corps_colle_a_la_tete(self):
        self.assertEqual(it.lire_rayon("S0W"), ("S", 1))

    def test_mur_colle_a_la_tete(self):
        """Un rayon de longueur 1 : la tete est contre le bord."""
        self.assertEqual(it.lire_rayon("W"), ("W", 1))

    def test_pomme_rouge_a_deux_cases(self):
        self.assertEqual(it.lire_rayon("0R0W"), ("R", 2))

    def test_la_premiere_chose_vue_cache_le_reste(self):
        """Trou connu de l'encodage (IA.md 6.7) : la rouge cache la verte."""
        self.assertEqual(it.lire_rayon("0RGW"), ("R", 2))


class TestDistance(unittest.TestCase):
    def test_la_case_adjacente_est_a_distance_un(self):
        """Le piege de l'etape : l'indice 0 de la chaine est la distance 1."""
        self.assertEqual(it.lire_rayon("GW")[1], 1)

    def test_exactement_au_plafond(self):
        self.assertEqual(it.lire_rayon("00GW"), ("G", 3))

    def test_au_dela_du_plafond(self):
        self.assertEqual(it.lire_rayon("000000GW"), ("G", 3))

    def test_couloir_libre_jusqu_au_mur(self):
        self.assertEqual(it.lire_rayon("000000000W"), ("W", 3))

    def test_jamais_au_dela_du_plafond(self):
        for longueur in range(30):
            with self.subTest(longueur=longueur):
                rayon = it.VIDE * longueur + bd.WALL_CHAR
                self.assertLessEqual(it.lire_rayon(rayon)[1], it.DISTANCE_MAX)


class TestIndependanceDeLaTaille(unittest.TestCase):
    def test_meme_lecture_sur_un_grand_plateau(self):
        """Le plafond rend le modele utilisable en 10x10 comme en 30x30."""
        petit = "0000G0000W"
        grand = "0000G" + "0" * 24 + "W"
        self.assertEqual(it.lire_rayon(petit), it.lire_rayon(grand))


class TestRayonInvalide(unittest.TestCase):
    def test_que_du_vide(self):
        with self.assertRaises(ValueError):
            it.lire_rayon("000")

    def test_rayon_vide(self):
        with self.assertRaises(ValueError):
            it.lire_rayon("")


class TestSurLeVraiPlateau(unittest.TestCase):
    def test_vision_d_un_plateau_connu(self):
        board = bd.Board(size=5, greens=0, reds=0)
        pose(board, (2, 2), bd.RIGHT)
        board.greens = [(2, 0)]
        board.reds = [(4, 2)]
        vision = board.vision_chars()
        self.assertEqual(it.lire_rayon(vision[bd.UP]), ("G", 2))
        self.assertEqual(it.lire_rayon(vision[bd.LEFT]), ("S", 1))
        self.assertEqual(it.lire_rayon(vision[bd.DOWN]), ("W", 3))
        self.assertEqual(it.lire_rayon(vision[bd.RIGHT]), ("R", 2))

    def test_tout_rayon_reel_se_lit(self):
        """Sur 200 plateaux aleatoires, aucun rayon ne fait lever d'erreur."""
        symboles = {bd.WALL_CHAR, bd.BODY_CHAR, bd.GREEN_CHAR, bd.RED_CHAR}
        board = bd.Board(size=10)
        for _ in range(200):
            board.reset()
            for rayon in board.vision_chars().values():
                symbole, distance = it.lire_rayon(rayon)
                self.assertIn(symbole, symboles)
                self.assertIn(distance, range(1, it.DISTANCE_MAX + 1))


if __name__ == "__main__":
    unittest.main()
