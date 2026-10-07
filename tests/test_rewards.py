"""Etape 1 : le bareme de recompenses.

Ces tests ne verifient pas les VALEURS exactes, mais les RAPPORTS entre elles
(IA.md section 7.3) : les valeurs seront reglees plus tard par le sweep, les
rapports, eux, doivent toujours tenir.
"""

import itertools
import unittest

from src import session as ss
from src.environment import board as bd
from src.environment.rewards import BAREME, recompense
from tests.helpers import Espion, plateau_nu, tour_du_plateau

MORTS = (bd.WALL, bd.BODY, bd.STARVE)


class TestSignes(unittest.TestCase):
    def test_pomme_verte_positive(self):
        self.assertGreater(recompense(bd.GREEN), 0)

    def test_pomme_rouge_negative(self):
        self.assertLess(recompense(bd.RED), 0)

    def test_deplacement_negatif(self):
        """Sinon tourner en rond sans manger ne coute rien."""
        self.assertLess(recompense(bd.MOVE), 0)

    def test_morts_negatives(self):
        for mort in MORTS:
            with self.subTest(mort=mort):
                self.assertLess(recompense(mort), 0)


class TestRapports(unittest.TestCase):
    """IA.md section 7.3 : ce ne sont pas les valeurs qui comptent."""

    def test_la_mort_est_le_pire(self):
        """Si une rouge coute plus cher que la mort, il prefere le mur."""
        for mort in MORTS:
            with self.subTest(mort=mort):
                self.assertLess(recompense(mort), recompense(bd.RED))
                self.assertLess(recompense(mort), recompense(bd.MOVE))

    def test_les_trois_morts_se_valent(self):
        """Le sujet les regroupe : game over, quelle qu'en soit la cause."""
        self.assertEqual(len({recompense(mort) for mort in MORTS}), 1)

    def test_la_rouge_coute_plus_qu_un_pas(self):
        """Sinon manger une rouge ne serait qu'un pas comme un autre."""
        self.assertLess(recompense(bd.RED), recompense(bd.MOVE))

    def test_manger_compense_plus_qu_un_pas(self):
        """Sinon aller chercher une pomme ne vaut jamais le deplacement."""
        self.assertGreater(recompense(bd.GREEN), -recompense(bd.MOVE))


class TestTroncature(unittest.TestCase):
    """Le piege qu'on a mis trois audits a eliminer."""

    def test_timeout_absent_du_bareme(self):
        self.assertNotIn(bd.TIMEOUT, BAREME)
        with self.assertRaises(KeyError):
            recompense(bd.TIMEOUT)

    def test_evenement_inconnu(self):
        with self.assertRaises(KeyError):
            recompense("banane")

    def test_partie_tronquee_de_bout_en_bout(self):
        """Avec le vrai plateau, la troncature n'atteint jamais le bareme."""
        board = plateau_nu(size=5, idle_factor=1)
        chemin = list(itertools.islice(tour_du_plateau(board), 40))
        espion = Espion(chemin)
        ss.play_session(board, espion, recompense)
        self.assertTrue(board.truncated)
        self.assertEqual(espion.recu[-1]["reward"], recompense(bd.MOVE))
        self.assertFalse(espion.recu[-1]["done"])


class TestComplet(unittest.TestCase):
    def test_tout_evenement_du_pas_a_une_recompense(self):
        """board.step() ne doit jamais renvoyer un evenement sans prix."""
        for event in (bd.MOVE, bd.GREEN, bd.RED) + MORTS:
            with self.subTest(event=event):
                self.assertIsInstance(recompense(event), (int, float))


if __name__ == "__main__":
    unittest.main()
