"""Etape 4 : assembler l'etat que la table Q va utiliser."""

import unittest

from src.agent import interpreter as it
from src.environment import board as bd
from tests.helpers import plateau_nu, pose

SYMBOLES = {bd.WALL_CHAR, bd.BODY_CHAR, bd.GREEN_CHAR, bd.RED_CHAR}


def plateau_exemple():
    """Le plateau 5x5 de l'explication : le serpent va a droite."""
    board = bd.Board(size=5, greens=0, reds=0)
    pose(board, (2, 2), bd.RIGHT)
    board.greens = [(2, 0)]
    board.reds = [(4, 2)]
    return board


class TestExemple(unittest.TestCase):
    def test_etat_du_plateau_exemple(self):
        board = plateau_exemple()
        etat = it.encode(board.vision_chars(), bd.RIGHT)
        self.assertEqual(etat, (("R", 2), ("G", 2), ("W", 3)))

    def test_ordre_devant_gauche_droite(self):
        board = plateau_exemple()
        devant, gauche, droite = it.encode(board.vision_chars(), bd.RIGHT)
        self.assertEqual(devant, ("R", 2), "devant = le rayon DROITE")
        self.assertEqual(gauche, ("G", 2), "gauche en allant a droite : HAUT")
        self.assertEqual(droite, ("W", 3), "a droite en allant a droite : BAS")

    def test_le_rayon_de_derriere_est_ignore(self):
        """Derriere, c'est le rayon GAUCHE, 'SSW' : il n'apparait pas."""
        board = plateau_exemple()
        etat = it.encode(board.vision_chars(), bd.RIGHT)
        self.assertEqual(len(etat), 3)
        self.assertNotIn(("S", 1), etat)

    def test_le_cap_change_l_etat(self):
        """Meme vision, autre cap : le serpent regarde ailleurs."""
        vision = plateau_exemple().vision_chars()
        self.assertNotEqual(
            it.encode(vision, bd.RIGHT), it.encode(vision, bd.UP)
        )


class TestLeGainDuRepereEgocentrique(unittest.TestCase):
    """La preuve de l'etape 3 : 4 orientations, un seul etat."""

    def situation(self, cap, cote):
        """Serpent au centre d'un 10x10, pomme verte a 2 cases du `cote`."""
        board = plateau_nu(size=10)
        pose(board, (5, 5), cap)
        direction = it.tourner(cap, cote)
        board.greens = [(5 + 2 * direction[0], 5 + 2 * direction[1])]
        return board

    def test_pomme_devant_les_quatre_orientations(self):
        visions = []
        etats = set()
        for cap in bd.DIRECTIONS:
            board = self.situation(cap, it.TOUT_DROIT)
            visions.append(board.vision_chars())
            etats.add(it.encode(board.vision_chars(), cap))
        self.assertEqual(len({frozenset(v.items()) for v in visions}), 4,
                         "en brut : 4 visions differentes")
        self.assertEqual(etats, {(("G", 2), ("W", 3), ("W", 3))},
                         "encode : un seul et meme etat")

    def test_pomme_a_gauche_les_quatre_orientations(self):
        """Detecte une confusion entre gauche et droite."""
        etats = {
            it.encode(self.situation(cap, it.GAUCHE).vision_chars(), cap)
            for cap in bd.DIRECTIONS
        }
        self.assertEqual(etats, {(("W", 3), ("G", 2), ("W", 3))})

    def test_pomme_a_droite_les_quatre_orientations(self):
        etats = {
            it.encode(self.situation(cap, it.DROITE).vision_chars(), cap)
            for cap in bd.DIRECTIONS
        }
        self.assertEqual(etats, {(("W", 3), ("W", 3), ("G", 2))})


class TestUtilisableCommeCle(unittest.TestCase):
    """La table Q sera un dictionnaire : l'etat doit pouvoir en etre la cle."""

    def test_etat_est_un_tuple(self):
        board = plateau_exemple()
        etat = it.encode(board.vision_chars(), bd.RIGHT)
        self.assertIsInstance(etat, tuple)
        for couple in etat:
            self.assertIsInstance(couple, tuple)

    def test_etat_sert_de_cle_de_dictionnaire(self):
        board = plateau_exemple()
        table = {it.encode(board.vision_chars(), bd.RIGHT): [0.0, 0.0, 0.0]}
        meme_etat = it.encode(plateau_exemple().vision_chars(), bd.RIGHT)
        self.assertIn(meme_etat, table)


class TestSurDeVraisPlateaux(unittest.TestCase):
    def test_tout_plateau_reel_s_encode(self):
        board = bd.Board(size=10)
        for _ in range(300):
            board.reset()
            etat = it.encode(board.vision_chars(), board.direction)
            self.assertEqual(len(etat), 3)
            for symbole, distance in etat:
                self.assertIn(symbole, SYMBOLES)
                self.assertIn(distance, range(1, it.DISTANCE_MAX + 1))

    def test_nombre_d_etats_borne(self):
        """Jamais plus de 12 x 12 x 12 = 1728 etats differents."""
        board = bd.Board(size=10)
        etats = set()
        for _ in range(2000):
            board.reset()
            etats.add(it.encode(board.vision_chars(), board.direction))
        self.assertLessEqual(len(etats), 12 ** 3)


if __name__ == "__main__":
    unittest.main()
