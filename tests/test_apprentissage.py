"""Etapes 7 a 10 : apprendre, alpha, rejeu inverse, epsilon."""

import random
import unittest

from src.agent import interpreter as it
from src.agent.agent import Agent, EPSILON_MIN, GAMMA, PAS_CIBLE
from src.agent.qtable import QTable
from src.environment import board as bd
from src.environment.rewards import recompense

A = (("W", 3), ("G", 2), ("W", 3))
B = (("R", 2), ("W", 3), ("W", 3))
C = (("W", 1), ("S", 1), ("W", 3))


def agent_neuf(**options):
    return Agent(rng=random.Random(0), **options)


class TestBellman(unittest.TestCase):
    """Etape 7 : la cible, et la correction vers la cible."""

    def test_mort_pas_de_futur(self):
        agent = agent_neuf()
        agent.mettre_a_jour(A, it.TOUT_DROIT, -50, None, True)
        self.assertEqual(agent.q.valeurs(A)[it.TOUT_DROIT], -50)

    def test_pas_normal_bootstrappe(self):
        """-1 + 0.95 * max(Q(B)) = -1 + 0.95 * 1.0 = -0.05."""
        agent = agent_neuf()
        agent.mettre_a_jour(A, it.GAUCHE, -1, B, False)
        self.assertAlmostEqual(agent.q.valeurs(A)[it.GAUCHE], -0.05)

    def test_bootstrap_sur_la_meilleure_action_suivante(self):
        agent = agent_neuf()
        agent.q.valeurs(B)[:] = [-10.0, 4.0, -3.0]
        agent.mettre_a_jour(A, it.GAUCHE, 20, B, False)
        self.assertAlmostEqual(agent.q.valeurs(A)[it.GAUCHE], 20 + 0.95 * 4.0)

    def test_bootstrap_sur_valeur_initiale_reglee(self):
        agent = Agent(rng=random.Random(0), qtable=QTable(0.5))
        agent.mettre_a_jour(A, it.GAUCHE, -1, B, False)
        self.assertAlmostEqual(agent.q.valeurs(A)[it.GAUCHE], -1 + 0.95 * 0.5)

    def test_l_etat_suivant_n_est_pas_ajoute_a_la_table(self):
        """Le bootstrap lit l'etat suivant, il ne l'ecrit pas."""
        agent = agent_neuf()
        agent.mettre_a_jour(A, it.GAUCHE, -1, B, False)
        self.assertIn(A, agent.q)
        self.assertNotIn(B, agent.q)

    def test_seule_l_action_jouee_change(self):
        agent = agent_neuf()
        agent.mettre_a_jour(A, it.DROITE, -50, None, True)
        self.assertEqual(agent.q.valeurs(A)[it.TOUT_DROIT], 1.0)
        self.assertEqual(agent.q.valeurs(A)[it.GAUCHE], 1.0)


class TestAlpha(unittest.TestCase):
    """Etape 8 : corriger de moins en moins fort."""

    def test_valeurs_du_tableau_de_ia_md(self):
        self.assertAlmostEqual(Agent.alpha(1), 1.0)
        self.assertAlmostEqual(Agent.alpha(10), 0.1995, places=4)
        self.assertAlmostEqual(Agent.alpha(100), 0.0398, places=4)
        self.assertAlmostEqual(Agent.alpha(1000), 0.0079, places=4)

    def test_deuxieme_mise_a_jour_moins_forte(self):
        """1re : -50 pris en entier. 2e : on ne fait que 61,6 % du chemin."""
        agent = agent_neuf()
        agent.mettre_a_jour(A, it.TOUT_DROIT, -50, None, True)
        agent.mettre_a_jour(A, it.TOUT_DROIT, -10, None, True)
        attendu = -50 + Agent.alpha(2) * (-10 - (-50))
        self.assertAlmostEqual(agent.q.valeurs(A)[it.TOUT_DROIT], attendu)

    def test_alpha_compte_par_couple_et_non_par_etat(self):
        """3 mises a jour de DROITE ne ralentissent pas la 1re de GAUCHE."""
        agent = agent_neuf()
        for _ in range(3):
            agent.mettre_a_jour(A, it.DROITE, -1, B, False)
        agent.mettre_a_jour(A, it.GAUCHE, -50, None, True)
        self.assertEqual(agent.q.valeurs(A)[it.GAUCHE], -50)

    def test_visites_comptees_par_couple(self):
        agent = agent_neuf()
        agent.mettre_a_jour(A, it.GAUCHE, -1, B, False)
        agent.mettre_a_jour(A, it.GAUCHE, -1, B, False)
        agent.mettre_a_jour(A, it.DROITE, -1, B, False)
        self.assertEqual(agent.q.nb_visites(A, it.GAUCHE), 2)
        self.assertEqual(agent.q.nb_visites(A, it.DROITE), 1)
        self.assertEqual(agent.q.nb_visites(A, it.TOUT_DROIT), 0)


class TestApprendreEnFinDePartie(unittest.TestCase):
    """Etape 9 : noter pendant la partie, apprendre a la fin, dans l'ordre."""

    def partie_notee(self, agent):
        agent.trajectoire = [
            (A, it.TOUT_DROIT, -1, B, False),
            (B, it.TOUT_DROIT, -1, C, False),
            (C, it.TOUT_DROIT, -50, None, True),
        ]

    def jouer_une_partie(self, agent, graine=4):
        """Vraie partie, avec les vrais appels choose/learn."""
        board = bd.Board(size=10, rng=random.Random(graine))
        agent.debut_partie(board.direction)
        while board.alive:
            vision = board.vision_chars()
            direction = agent.choose(vision)
            event = board.step(direction)
            apres = vision if board.dead else board.vision_chars()
            agent.learn(vision, direction, recompense(event), apres,
                        board.dead)
        return board

    def test_rien_n_est_appris_pendant_la_partie(self):
        """learn() note seulement : sinon chaque pas serait appris 2 fois."""
        agent = agent_neuf()
        board = self.jouer_une_partie(agent)
        self.assertEqual(len(agent.trajectoire), board.steps)
        self.assertEqual(len(agent.q), 0)
        self.assertEqual(agent.q.visites, {})

    def test_chaque_pas_appris_exactement_une_fois(self):
        agent = agent_neuf()
        board = self.jouer_une_partie(agent)
        agent.fin_partie()
        total = sum(sum(v) for v in agent.q.visites.values())
        self.assertEqual(total, board.steps)

    def test_ordre_chronologique(self):
        ordre = []

        class Temoin(Agent):
            def mettre_a_jour(self, etat, *reste):
                ordre.append(etat)

        agent = Temoin(rng=random.Random(0))
        self.partie_notee(agent)
        agent.fin_partie()
        self.assertEqual(ordre, [A, B, C])

    def test_la_mort_ne_remonte_pas_seule(self):
        """Ce que fait vraiment Q-learning (IA.md 4.7).

        L'avant-dernier pas regarde la MEILLEURE action de l'etat suivant :
        les autres actions de C valent encore +1, le -50 ne passe pas.
        """
        agent = agent_neuf()
        self.partie_notee(agent)
        agent.fin_partie()
        self.assertEqual(agent.q.valeurs(C)[it.TOUT_DROIT], -50)
        self.assertAlmostEqual(
            agent.q.valeurs(B)[it.TOUT_DROIT], -1 + 0.95 * 1.0
        )

    def test_trajectoire_videe_et_partie_comptee(self):
        agent = agent_neuf()
        self.partie_notee(agent)
        agent.fin_partie()
        self.assertEqual(agent.trajectoire, [])
        self.assertEqual(agent.parties, 1)

    def test_partie_vide_non_comptee(self):
        agent = agent_neuf()
        agent.fin_partie()
        self.assertEqual(agent.parties, 0)

    def test_debut_partie_efface_une_trajectoire_orpheline(self):
        agent = agent_neuf()
        self.partie_notee(agent)
        agent.debut_partie(bd.UP)
        self.assertEqual(agent.trajectoire, [])


class TestCeQueLearnNote(unittest.TestCase):
    """Le drapeau de mort et l'etat suivant, tels que learn() les note."""

    def un_pas(self, mort):
        board = bd.Board(size=10, rng=random.Random(5))
        agent = agent_neuf()
        agent.debut_partie(board.direction)
        vision = board.vision_chars()
        direction = agent.choose(vision)
        board.step(direction)
        apres = board.vision_chars()
        agent.learn(vision, direction, -1, apres, mort)
        return agent, apres, direction

    def test_troncature_note_un_etat_suivant_reel(self):
        """mort = False : on bootstrappera sur ce que le serpent voit apres."""
        agent, apres, direction = self.un_pas(mort=False)
        _, _, recompense_notee, suivant, mort = agent.trajectoire[-1]
        self.assertEqual(recompense_notee, -1)
        self.assertFalse(mort)
        self.assertEqual(suivant, it.encode(apres, direction))

    def test_mort_note_pas_d_etat_suivant(self):
        agent, _, _ = self.un_pas(mort=True)
        _, _, _, suivant, mort = agent.trajectoire[-1]
        self.assertTrue(mort)
        self.assertIsNone(suivant)

    def test_troncature_apprise_avec_bootstrap(self):
        """De bout en bout : une troncature ne vaut pas -1 sec."""
        agent, _, _ = self.un_pas(mort=False)
        etat, action = agent.trajectoire[-1][:2]
        agent.fin_partie()
        self.assertAlmostEqual(agent.q.valeurs(etat)[action], -1 + 0.95)


class TestEpsilon(unittest.TestCase):
    """Etape 10 : l'exploration diminue avec les pas joues."""

    def test_decroissance_lineaire(self):
        agent = agent_neuf(pas_cible=100)
        agent.pas_total = 50
        agent.mettre_a_jour_epsilon()
        self.assertAlmostEqual(agent.epsilon, 0.5)

    def test_plancher(self):
        agent = agent_neuf(pas_cible=100)
        agent.pas_total = 10_000
        agent.mettre_a_jour_epsilon()
        self.assertEqual(agent.epsilon, EPSILON_MIN)

    def test_chaque_pas_joue_fait_baisser_epsilon(self):
        agent = agent_neuf(pas_cible=1000)
        board = bd.Board(size=10, rng=random.Random(3))
        agent.debut_partie(board.direction)
        for _ in range(5):
            if board.alive:
                board.step(agent.choose(board.vision_chars()))
        self.assertEqual(agent.pas_total, board.steps)
        self.assertLess(agent.epsilon, 1.0)


class TestPasDeJeu(unittest.TestCase):
    """L'interface avec la boucle : debut_partie, choose, learn."""

    def test_choose_sans_debut_partie(self):
        with self.assertRaises(RuntimeError):
            agent_neuf().choose({})

    def test_choose_renvoie_une_direction_et_met_le_cap_a_jour(self):
        board = bd.Board(size=10, rng=random.Random(5))
        agent = agent_neuf()
        agent.debut_partie(board.direction)
        direction = agent.choose(board.vision_chars())
        self.assertIn(direction, bd.DIRECTIONS)
        self.assertEqual(agent.cap, direction)

    def test_jamais_de_demi_tour(self):
        oppose = {bd.UP: bd.DOWN, bd.DOWN: bd.UP,
                  bd.LEFT: bd.RIGHT, bd.RIGHT: bd.LEFT}
        board = bd.Board(size=10, rng=random.Random(6))
        agent = agent_neuf()
        for _ in range(50):
            board.reset()
            agent.debut_partie(board.direction)
            cap = board.direction
            direction = agent.choose(board.vision_chars())
            self.assertNotEqual(direction, oppose[cap])

    def test_learn_refuse_une_autre_direction(self):
        board = bd.Board(size=10, rng=random.Random(5))
        agent = agent_neuf()
        agent.debut_partie(board.direction)
        joue = agent.choose(board.vision_chars())
        autre = next(d for d in bd.DIRECTIONS if d != joue)
        with self.assertRaises(ValueError):
            agent.learn({}, autre, -1, {}, True)

    def test_mort_sans_etat_suivant(self):
        board = bd.Board(size=10, rng=random.Random(5))
        agent = agent_neuf()
        agent.debut_partie(board.direction)
        joue = agent.choose(board.vision_chars())
        agent.learn(board.vision_chars(), joue, -50, {}, True)
        self.assertIsNone(agent.trajectoire[-1][3])


class TestConstantes(unittest.TestCase):
    """Les valeurs livrees, mesurees et documentees dans IA.md."""

    def test_valeurs(self):
        self.assertEqual(GAMMA, 0.95)
        self.assertEqual(EPSILON_MIN, 0.01)
        self.assertEqual(PAS_CIBLE, 5_000)


class TestFiger(unittest.TestCase):
    """-dontlearn : jouer sans rien modifier."""

    def test_fige_n_explore_plus_et_n_apprend_plus(self):
        board = bd.Board(size=10, rng=random.Random(8))
        agent = agent_neuf()
        agent.figer()
        agent.debut_partie(board.direction)
        while board.alive:
            vision = board.vision_chars()
            direction = agent.choose(vision)
            event = board.step(direction)
            agent.learn(vision, direction, -1, vision, board.dead)
        agent.fin_partie()
        self.assertEqual(agent.epsilon, 0.0)
        self.assertEqual(agent.pas_total, 0)
        self.assertEqual(agent.parties, 0)
        self.assertEqual(agent.trajectoire, [])
        self.assertIsNotNone(event)


if __name__ == "__main__":
    unittest.main()
