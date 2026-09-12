"""Boucle de jeu : contrat d'apprentissage, statistiques, baselines."""

import contextlib
import io
import itertools
import random
import statistics
import unittest

from src import baselines, session as ss
from src.environment import board as bd
from tests.helpers import (Barometre, Espion, plateau_nu, pose,
                           tour_du_plateau)


def partie_tronquee():
    """Plateau et chemin qui atteignent la limite de pas sans pomme."""
    board = plateau_nu(size=5, idle_factor=1)
    chemin = list(itertools.islice(tour_du_plateau(board), 40))
    return board, chemin


class TestAgentPiloteLePlateau(unittest.TestCase):
    """Sans ca, tous les tests d'agent seraient decoratifs."""

    def test_l_action_choisie_deplace_vraiment_le_serpent(self):
        board = pose(plateau_nu(size=5), (2, 2), bd.RIGHT)
        espion = Espion([bd.DOWN, bd.DOWN, bd.DOWN])
        ss.play_session(board, espion, Barometre())
        # Si l'agent etait ignore, le serpent aurait garde son cap RIGHT et
        # serait mort contre le mur de droite en (4, 2).
        self.assertEqual(board.snake[0], (2, 4))
        self.assertEqual(board.end_cause, bd.WALL)
        self.assertEqual(espion.choisies, [bd.DOWN, bd.DOWN, bd.DOWN])

    def test_l_action_transmise_a_learn_est_celle_choisie(self):
        board = pose(plateau_nu(size=5), (2, 2), bd.RIGHT)
        espion = Espion([bd.DOWN, bd.DOWN, bd.DOWN])
        ss.play_session(board, espion, Barometre())
        self.assertEqual(
            [recu["action"] for recu in espion.recu], espion.choisies
        )

    def test_sans_agent_le_serpent_garde_son_cap(self):
        board = pose(plateau_nu(size=5), (2, 2), bd.RIGHT)
        ss.play_session(board)
        self.assertEqual(board.snake[0], (4, 2))


class TestContratLearn(unittest.TestCase):
    """L'invariant central : mort et troncature n'ont pas le meme contrat."""

    def test_troncature_bootstrappe(self):
        board, chemin = partie_tronquee()
        espion = Espion(chemin)
        ss.play_session(board, espion, Barometre())
        dernier = espion.recu[-1]
        self.assertFalse(
            dernier["done"],
            "le serpent etait vivant : son etat suivant a une valeur",
        )
        self.assertEqual(
            dernier["next_state"], board.vision_chars(),
            "l'etat suivant doit etre la vision d'APRES le pas",
        )
        self.assertNotEqual(dernier["next_state"], dernier["state"])

    def test_troncature_garde_le_cout_du_pas(self):
        """Sinon atteindre la limite rapporte +1 de plus que tout le reste."""
        board, chemin = partie_tronquee()
        barometre = Barometre()
        espion = Espion(chemin)
        ss.play_session(board, espion, barometre)
        self.assertEqual(
            barometre.vus[-1], bd.MOVE,
            "la recompense se calcule sur l'evenement du pas, pas sur la "
            "cause de fin",
        )
        self.assertEqual(espion.recu[-1]["reward"], -1)
        self.assertEqual({r["reward"] for r in espion.recu}, {-1})

    def test_mort_penalisee_et_sans_futur(self):
        board = pose(plateau_nu(size=10), (5, 5), bd.RIGHT)
        espion = Espion([bd.LEFT])
        ss.play_session(board, espion, Barometre())
        dernier = espion.recu[-1]
        self.assertEqual(dernier["reward"], -50)
        self.assertTrue(dernier["done"])

    def test_mort_ne_transmet_pas_d_etat_suivant(self):
        """Sur une mort il n'y a pas d'apres : on renvoie l'etat courant."""
        board = pose(plateau_nu(size=10), (5, 5), bd.RIGHT)
        espion = Espion([bd.LEFT])
        ss.play_session(board, espion, Barometre())
        dernier = espion.recu[-1]
        self.assertEqual(dernier["next_state"], dernier["state"])
        self.assertNotEqual(dernier["next_state"], board.vision_chars())

    def test_un_appel_par_pas(self):
        board, chemin = partie_tronquee()
        espion = Espion(chemin)
        ss.play_session(board, espion, Barometre())
        self.assertEqual(len(espion.recu), board.steps)
        self.assertEqual(len(espion.recu), 25)

    def test_agent_sans_learn_ne_casse_rien(self):
        board = pose(plateau_nu(size=5), (2, 2), bd.RIGHT)
        agent = baselines.RandomAgent(random.Random(0))
        cause = ss.play_session(board, agent, Barometre())
        self.assertIn(cause, bd.DEATH_EVENTS)
        self.assertEqual(cause, board.end_cause)

    def test_valeur_de_retour_est_la_cause_de_fin(self):
        board = pose(plateau_nu(size=5), (0, 2), bd.LEFT)
        self.assertEqual(ss.play_session(board), bd.WALL)
        board, chemin = partie_tronquee()
        self.assertEqual(
            ss.play_session(board, Espion(chemin), Barometre()), bd.TIMEOUT
        )

    def test_plafond_de_securite_de_la_boucle(self):
        """Un plateau qui ne meurt jamais ne doit pas figer l'entrainement.

        Et la partie doit rester coherente : une partie finie sans cause de
        fin casserait les statistiques.
        """
        class PlateauSansFin:
            """Plateau volontairement casse : il ne meurt jamais seul."""

            def __init__(self):
                self.alive = True
                self.truncated = False
                self.steps = 0
                self.direction = bd.RIGHT
                self.end_cause = None

            def vision_chars(self):
                return {}

            def step(self, direction):
                self.steps += 1
                return bd.MOVE

            def truncate(self):
                self.alive = False
                self.truncated = True
                self.end_cause = bd.TIMEOUT

        ancien = ss.MAX_STEPS_PER_SESSION
        ss.MAX_STEPS_PER_SESSION = 10
        try:
            board = PlateauSansFin()
            cause = ss.play_session(board)
            self.assertEqual(board.steps, 10)
            self.assertEqual(cause, bd.TIMEOUT)
            self.assertFalse(board.alive)
            self.assertIn(
                cause, bd.END_CAUSES,
                "sinon les statistiques comptent une cause None",
            )
        finally:
            ss.MAX_STEPS_PER_SESSION = ancien


class TestStats(unittest.TestCase):
    """Mesure sur de vraies parties, pas sur des attributs fabriques."""

    class Cfg:
        size = 10
        seed = 7
        sessions = 12
        save_path = None
        trace = False
        baseline = None

    def stats_reelles(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return ss.run_sessions(self.Cfg())

    def test_agregats_coherents_avec_les_parties(self):
        stats = self.stats_reelles()
        self.assertEqual(stats.games, 12)
        self.assertEqual(len(stats.lengths), 12)
        self.assertEqual(stats.max_length, max(stats.lengths))
        self.assertAlmostEqual(
            stats.mean_length, statistics.fmean(stats.lengths)
        )
        self.assertEqual(
            stats.median_length, statistics.median(stats.lengths)
        )

    def test_compteurs_de_duree_alimentes(self):
        stats = self.stats_reelles()
        self.assertGreater(stats.max_steps, 0)
        self.assertGreater(stats.total_steps, 0)
        self.assertLessEqual(stats.max_steps, stats.total_steps)

    def test_causes_toutes_valides_et_comptees(self):
        stats = self.stats_reelles()
        self.assertEqual(sum(stats.causes.values()), 12)
        for cause in stats.causes:
            self.assertIn(cause, bd.END_CAUSES)

    def test_summary_affiche_les_vrais_chiffres(self):
        stats = self.stats_reelles()
        texte = stats.summary()
        self.assertIn("12 sessions", texte)
        self.assertIn("maximale = {}".format(stats.max_length), texte)
        self.assertIn("{:.2f}".format(stats.mean_length), texte)

    def test_causes_summary_libelle_et_pourcentage(self):
        stats = ss.SessionStats()
        for cause in (bd.WALL, bd.WALL, bd.BODY, bd.TIMEOUT):
            board = plateau_nu()
            board.end_cause = cause
            stats.record(board)
        texte = stats.causes_summary()
        self.assertIn("collision avec un mur = 2 (50 %)", texte)
        self.assertIn("trop de pas sans pomme = 1 (25 %)", texte)

    def test_stats_vides(self):
        stats = ss.SessionStats()
        self.assertEqual(stats.mean_length, 0.0)
        self.assertEqual(stats.median_length, 0.0)
        self.assertIn("aucune partie", stats.causes_summary())


class TestBaselines(unittest.TestCase):
    def test_make_sans_nom(self):
        self.assertIsNone(baselines.make(None))

    def test_make_nom_inconnu(self):
        with self.assertRaises(ValueError):
            baselines.make("greedy")

    def test_random_est_vraiment_aleatoire(self):
        """Un agent qui va toujours tout droit passerait les autres tests."""
        agent = baselines.make("random", random.Random(0))
        tirages = {agent.choose({}) for _ in range(200)}
        self.assertEqual(tirages, set(bd.DIRECTIONS))

    def test_random_est_reproductible(self):
        a = baselines.make("random", random.Random(42))
        b = baselines.make("random", random.Random(42))
        self.assertEqual(
            [a.choose({}) for _ in range(20)],
            [b.choose({}) for _ in range(20)],
        )

    def test_random_ne_sort_pas_des_directions(self):
        agent = baselines.make("random", random.Random(1))
        for _ in range(50):
            self.assertIn(agent.choose({}), bd.DIRECTIONS)

    def test_graine_de_l_agent_distincte_du_plateau(self):
        """Meme graine = flux identiques, donc agent correle aux pommes."""
        self.assertNotEqual(baselines.derive_seed(7), 7)
        self.assertIsNone(baselines.derive_seed(None))
        plateau = random.Random(7)
        agent = random.Random(baselines.derive_seed(7))
        self.assertNotEqual(
            [plateau.random() for _ in range(20)],
            [agent.random() for _ in range(20)],
        )


if __name__ == "__main__":
    unittest.main()
