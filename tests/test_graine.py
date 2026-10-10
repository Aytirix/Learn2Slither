"""Une graine par partie : la partie n se rejoue seule (src/graine.py)."""

import contextlib
import io
import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from src import graine as gr  # noqa: E402
from src.agent.agent import Agent  # noqa: E402
from src.config import GameConfig  # noqa: E402
from src.environment import board as bd  # noqa: E402
from src.interface.evaluation_view import EvaluationGame  # noqa: E402
from src.session import play_session, run_sessions  # noqa: E402


def silence():
    return contextlib.redirect_stdout(io.StringIO())


def agent_fige():
    """Agent qui n'apprend pas mais tire encore au hasard (epsilon 0.3) :
    le generateur de l'agent compte donc dans la partie."""
    agent = Agent(rng=random.Random(123))
    agent.figer()
    agent.epsilon = 0.3
    return agent


def fin(board):
    """Ce qui resume une partie finie."""
    return (list(board.snake), list(board.greens), list(board.reds),
            board.steps, board.max_length, board.end_cause)


def parties_sans_affichage(depart, nombre):
    """Joue `nombre` parties d'affilee comme src/session.py."""
    agent = agent_fige()
    board = bd.Board(rng=random.Random())
    fins = []
    with silence():
        for numero in range(1, nombre + 1):
            gr.nouvelle_partie(board, agent, gr.graine_partie(depart, numero))
            play_session(board, agent)
            fins.append(fin(board))
    return fins


class TestGraine(unittest.TestCase):
    def test_graine_de_la_partie_n(self):
        self.assertEqual(gr.graine_partie(1000, 1), 1000)
        self.assertEqual(gr.graine_partie(1000, 847), 1846)

    def test_graine_de_depart(self):
        self.assertEqual(gr.graine_de_depart(42), 42)
        tiree = gr.graine_de_depart(None)
        self.assertTrue(0 <= tiree < gr.GRAINE_MAX)

    def test_partie_n_rejouee_seule(self):
        """Partie 7 avec la graine 500 = partie 1 avec la graine 506."""
        suite = parties_sans_affichage(500, 7)
        seule = parties_sans_affichage(506, 1)
        self.assertEqual(suite[6], seule[0])

    def test_parties_differentes_entre_elles(self):
        fins = parties_sans_affichage(500, 5)
        self.assertGreater(len({repr(f) for f in fins}), 1)

    def test_board_reset_garde_la_graine(self):
        board = bd.Board(rng=random.Random())
        board.reset(77)
        premier = (list(board.snake), list(board.greens), list(board.reds))
        board.reset(77)
        self.assertEqual(board.graine, 77)
        self.assertEqual(
            (list(board.snake), list(board.greens), list(board.reds)),
            premier)

    def test_run_sessions_annonce_la_graine(self):
        sortie = io.StringIO()
        with contextlib.redirect_stdout(sortie):
            run_sessions(GameConfig(sessions=2, seed=31, visual=False,
                                    trace=False), agent_fige())
        self.assertIn("Graine de depart : 31", sortie.getvalue())


class TestGraineEnFenetre(unittest.TestCase):
    def evaluation(self, depart, nombre):
        """Joue `nombre` parties dans la fenetre d'evaluation."""
        config = GameConfig(learn=False, trace=False, speed=100,
                            seed=depart)
        game = EvaluationGame(config, agent_fige(), seuil=10_000)
        fins, graines = [], []
        with silence():
            while game.bilan.stats.games < nombre:
                avant = game.bilan.stats.games
                graine = game.graine
                # Pas de temps irreguliers : le rythme des images ne doit
                # plus changer les pommes (les particules ont leur
                # propre generateur).
                game.update(random.choice((0.01, 0.03, 0.2)))
                if game.bilan.stats.games > avant:
                    photo = game.bilan.derniere[-1]
                    fins.append((photo.snake, photo.greens, photo.reds,
                                 photo.steps, photo.max_length,
                                 photo.end_cause))
                    graines.append((graine, photo.graine))
        return fins, graines

    def test_fenetre_identique_au_mode_sans_affichage(self):
        fins, graines = self.evaluation(300, 4)
        self.assertEqual(fins, parties_sans_affichage(300, 4))
        self.assertEqual(graines, [(g, g) for g in range(300, 304)])

    def test_partie_n_en_fenetre_rejouee_seule(self):
        suite, _ = self.evaluation(300, 4)
        seule, _ = self.evaluation(303, 1)
        self.assertEqual(suite[3], seule[0])

    def test_graine_du_record(self):
        """Le record affiche la graine de la partie qui l'a fait."""
        config = GameConfig(learn=False, trace=False, speed=100, seed=300)
        game = EvaluationGame(config, agent_fige(), seuil=10_000)
        meilleure = (0, None)
        with silence():
            while game.bilan.stats.games < 6:
                avant = game.bilan.stats.games
                game.update(0.05)
                if game.bilan.stats.games > avant:
                    photo = game.bilan.derniere[-1]
                    if photo.max_length > meilleure[0]:
                        meilleure = (photo.max_length, photo.graine)
        self.assertEqual(game.best_length, meilleure[0])
        self.assertEqual(game.graine_record, meilleure[1])
        self.assertEqual(game.bilan.meilleure[0].graine, meilleure[1])

    def test_pas_de_graine_si_l_agent_apprend(self):
        from src.interface.game import Game
        agent = Agent(rng=random.Random(0))   # apprend
        with silence():
            game = Game(GameConfig(trace=False, speed=100, seed=1), agent)
            for _ in range(200):
                game.update(0.05)
        self.assertFalse(game.graine_rejouable)
        self.assertIsNone(game.graine_record)

    def test_pas_de_graine_au_clavier(self):
        from src.interface.game import Game
        game = Game(GameConfig(pilot="joueur", trace=False, seed=1), None)
        self.assertFalse(game.graine_rejouable)
        self.assertIsNone(game.graine_record)

    def test_graine_si_agent_fige(self):
        from src.interface.game import Game
        game = Game(GameConfig(trace=False, seed=1), agent_fige())
        self.assertTrue(game.graine_rejouable)
        self.assertEqual(game.graine_record, 1)


if __name__ == "__main__":
    unittest.main()
