"""Affichage : la logique qui distingue une mort d'une interruption.

Seules les parties sans pygame actif sont testees ici : les libelles derives
et le libelle d'etat. Le rendu lui-meme demande une surface video.
"""

import unittest

from src.environment import board as bd
from src.interface import board_view, panel_view, theme
from tests.helpers import plateau_nu


class PlateauFactice:
    """Juste les trois champs que lit l'affichage."""

    def __init__(self, alive, truncated):
        self.alive = alive
        self.truncated = truncated


class TestLibellesDerives(unittest.TestCase):
    def test_source_unique(self):
        """L'affichage derive de board, il ne redefinit pas sa propre table."""
        self.assertEqual(
            set(board_view.END_CAUSE_LABELS), set(bd.END_CAUSE_LABELS)
        )
        for cause, label in bd.END_CAUSE_LABELS.items():
            self.assertEqual(
                board_view.END_CAUSE_LABELS[cause], label.upper()
            )

    def test_toute_cause_a_un_libelle(self):
        for cause in bd.END_CAUSES:
            self.assertIn(cause, board_view.END_CAUSE_LABELS)


class TestEtatDePartie(unittest.TestCase):
    def test_en_vie(self):
        etat, couleur = panel_view.etat_de_partie(PlateauFactice(True, False))
        self.assertEqual(etat, "EN VIE")
        self.assertEqual(couleur, theme.GREEN_APPLE)

    def test_mort(self):
        etat, couleur = panel_view.etat_de_partie(PlateauFactice(False, False))
        self.assertEqual(etat, "MORT")
        self.assertEqual(couleur, theme.RED_APPLE)

    def test_troncature_n_est_pas_une_mort(self):
        """Afficher MORT sur une troncature contredit tout le decoupage."""
        etat, couleur = panel_view.etat_de_partie(PlateauFactice(False, True))
        self.assertEqual(etat, "INTERROMPU")
        self.assertNotEqual(couleur, theme.RED_APPLE)

    def test_sur_un_vrai_plateau_tronque(self):
        board = plateau_nu(size=5, idle_factor=1)
        board.truncate()
        self.assertEqual(
            panel_view.etat_de_partie(board)[0], "INTERROMPU"
        )


if __name__ == "__main__":
    unittest.main()
