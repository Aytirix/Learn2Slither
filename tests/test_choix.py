"""Etape 6 : choisir une action, entre exploration et exploitation."""

import random
import unittest
from collections import Counter

from src.agent import interpreter as it
from src.agent.agent import Agent

ETAT = (("R", 2), ("G", 2), ("W", 3))


def agent_avec(valeurs, epsilon, graine=0):
    """Agent dont la table contient `valeurs` pour ETAT."""
    agent = Agent(epsilon=epsilon, rng=random.Random(graine))
    agent.q.valeurs(ETAT)[:] = valeurs
    return agent


def tirages(agent, n):
    return Counter(agent.choisir_action(ETAT) for _ in range(n))


class TestExploitation(unittest.TestCase):
    """epsilon = 0 : l'agent joue toujours ce qu'il croit le meilleur."""

    def test_choisit_la_meilleure_action(self):
        compte = tirages(agent_avec([1.0, 5.0, 2.0], epsilon=0), 200)
        self.assertEqual(compte, Counter({it.GAUCHE: 200}))

    def test_meilleure_action_meme_negative(self):
        """Le meilleur, c'est le moins mauvais."""
        compte = tirages(agent_avec([-9.0, -40.0, -0.5], epsilon=0), 200)
        self.assertEqual(compte, Counter({it.DROITE: 200}))

    def test_ne_modifie_pas_la_table(self):
        agent = agent_avec([1.0, 5.0, 2.0], epsilon=0)
        for _ in range(50):
            agent.choisir_action(ETAT)
        self.assertEqual(agent.q.valeurs(ETAT), [1.0, 5.0, 2.0])

    def test_un_etat_inconnu_n_est_pas_ajoute(self):
        """Regarder pour choisir ne doit pas faire grossir la table."""
        agent = Agent(epsilon=0, rng=random.Random(0))
        agent.choisir_action(ETAT)
        self.assertEqual(len(agent.q), 0)


class TestExAequo(unittest.TestCase):
    """Le piege de IA.md 5.2 : max() renvoie toujours le premier."""

    def test_tire_au_hasard_parmi_les_meilleurs(self):
        compte = tirages(agent_avec([5.0, 5.0, 2.0], epsilon=0), 400)
        self.assertEqual(set(compte), {it.TOUT_DROIT, it.GAUCHE})

    def test_etat_neuf_les_trois_actions_sortent(self):
        """Etat jamais vu : [1, 1, 1]. Sinon il irait toujours tout droit."""
        agent = Agent(epsilon=0, rng=random.Random(1))
        compte = Counter(agent.choisir_action(ETAT) for _ in range(300))
        self.assertEqual(set(compte), set(it.ACTIONS))


class TestExploration(unittest.TestCase):
    def test_epsilon_un_joue_tout_au_hasard(self):
        """Meme avec une action nettement meilleure."""
        compte = tirages(agent_avec([0.0, 100.0, 0.0], epsilon=1), 3000)
        self.assertEqual(set(compte), set(it.ACTIONS))
        for action in it.ACTIONS:
            self.assertGreater(compte[action] / 3000, 0.28)

    def test_epsilon_dix_pourcents(self):
        """90 % meilleure action + 10 % hasard dont 1/3 retombe dessus."""
        compte = tirages(agent_avec([0.0, 100.0, 0.0], epsilon=0.1), 5000)
        part = compte[it.GAUCHE] / 5000
        self.assertGreater(part, 0.91)
        self.assertLess(part, 0.955)


class TestRobustesse(unittest.TestCase):
    def test_renvoie_toujours_une_action_valide(self):
        for epsilon in (0, 0.3, 1):
            agent = agent_avec([3.0, -1.0, 3.0], epsilon=epsilon)
            for _ in range(100):
                self.assertIn(agent.choisir_action(ETAT), it.ACTIONS)

    def test_reproductible_avec_la_meme_graine(self):
        a = agent_avec([1.0, 1.0, 1.0], epsilon=0.5, graine=42)
        b = agent_avec([1.0, 1.0, 1.0], epsilon=0.5, graine=42)
        self.assertEqual(
            [a.choisir_action(ETAT) for _ in range(50)],
            [b.choisir_action(ETAT) for _ in range(50)],
        )


if __name__ == "__main__":
    unittest.main()
