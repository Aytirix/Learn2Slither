"""Ligne de commande : traduction des arguments en configuration."""

import contextlib
import io
import random
import unittest

from src import baselines, cli


def config(argv):
    return cli.build_config(cli.parse_args(argv))


class TestBaselineCablee(unittest.TestCase):
    def test_flag_absent(self):
        self.assertIsNone(config([]).baseline)

    def test_flag_transmis(self):
        self.assertEqual(config(["-baseline", "random"]).baseline, "random")

    def test_choix_limites_aux_baselines_connues(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                config(["-baseline", "inexistante"])

    def test_bout_en_bout_jusqu_a_l_agent(self):
        agent = baselines.make(
            config(["-baseline", "random"]).baseline, random.Random(0)
        )
        self.assertIsInstance(agent, baselines.RandomAgent)


class TestWantsLobby(unittest.TestCase):
    def test_sans_argument_le_lobby_s_ouvre(self):
        self.assertTrue(cli.wants_lobby(cli.parse_args([])))

    def test_headless_saute_le_lobby(self):
        self.assertFalse(cli.wants_lobby(cli.parse_args(["-visual", "off"])))

    def test_baseline_decrit_la_run(self):
        """Comme -sessions ou -load : la run est deja decrite."""
        self.assertFalse(
            cli.wants_lobby(cli.parse_args(["-baseline", "random"]))
        )

    def test_flag_lobby_explicite_prime(self):
        args = cli.parse_args(["-baseline", "random", "-lobby", "on"])
        self.assertTrue(cli.wants_lobby(args))


class TestTraductionDesArguments(unittest.TestCase):
    def test_dontlearn(self):
        self.assertFalse(config(["-dontlearn"]).learn)
        self.assertTrue(config([]).learn)

    def test_visual(self):
        self.assertFalse(config(["-visual", "off"]).visual)
        self.assertTrue(config([]).visual)

    def test_vitesse_bornee(self):
        """0 ou infini faisaient diviser par zero dans la boucle graphique."""
        self.assertEqual(config(["-speed", "0"]).speed, 1.0)
        self.assertEqual(config(["-speed", "1000"]).speed, 30.0)
        self.assertEqual(config(["-speed", "inf"]).speed, 6.0)
        self.assertEqual(config(["-speed", "nan"]).speed, 6.0)

    def test_taille_bornee(self):
        self.assertEqual(config(["-size", "1"]).size, 5)
        self.assertEqual(config(["-size", "999"]).size, 30)


if __name__ == "__main__":
    unittest.main()
