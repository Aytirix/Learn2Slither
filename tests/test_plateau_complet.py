"""Option hors sujet : un modele qui voit tout le plateau."""

import contextlib
import io
import json
import os
import random
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from src import models  # noqa: E402
from src.agent import interpreter as it  # noqa: E402
from src.agent import modele  # noqa: E402
from src.agent.agent import Agent  # noqa: E402
from src.agent.fabrique import creer_agent  # noqa: E402
from src.config import GameConfig  # noqa: E402
from src.environment import board as bd  # noqa: E402
from src.environment import plateau_complet as pc  # noqa: E402
from src.environment.rewards import recompense  # noqa: E402
from src.interface.game import Game  # noqa: E402
from src.session import play_session  # noqa: E402
from tests.helpers import plateau_nu, pose  # noqa: E402


class TestEnvironnement(unittest.TestCase):
    def test_croix_seule_par_defaut(self):
        board = bd.Board(rng=random.Random(0))
        vue = pc.observer(board)
        self.assertNotIsInstance(vue, pc.VueComplete)
        self.assertEqual(vue, board.vision_chars())

    def test_vue_complete_contient_la_croix(self):
        board = bd.Board(rng=random.Random(0))
        vue = pc.observer(board, complete=True)
        self.assertIsInstance(vue, pc.VueComplete)
        self.assertEqual(dict(vue), board.vision_chars())

    def test_mur_et_corps_sont_des_pieges(self):
        board = pose(plateau_nu(), (0, 5), bd.UP)   # tete au bord gauche
        pieges = pc.pieges(board)
        self.assertTrue(pieges[bd.LEFT])            # mur
        self.assertTrue(pieges[bd.DOWN])            # cou
        self.assertFalse(pieges[bd.UP])
        self.assertFalse(pieges[bd.RIGHT])

    def test_cul_de_sac_trop_petit(self):
        """Une case libre, mais enfermee : moins de place que le serpent."""
        board = plateau_nu()
        # Serpent en U autour de la case (1, 0) : seule issue, sans sortie.
        board.snake = [(0, 1), (1, 1), (2, 1), (2, 0), (3, 0), (3, 1)]
        board.direction = bd.LEFT
        self.assertTrue(pc.pieges(board)[bd.UP])     # (0, 0) puis (1, 0)
        self.assertFalse(pc.pieges(board)[bd.DOWN])  # tout le bas du plateau

    def test_pomme_la_plus_proche(self):
        board = plateau_nu()
        pose(board, (5, 5), bd.UP)
        board.greens = [(9, 9), (5, 2)]
        self.assertEqual(pc.pomme_proche(board), (0, -3))
        board.greens = []
        self.assertIsNone(pc.pomme_proche(board))


class TestEncodage(unittest.TestCase):
    def vue(self, cap, pomme, pieges=None):
        board = pose(plateau_nu(), (5, 5), cap)
        board.greens = [pomme] if pomme else []
        vue = pc.observer(board, complete=True)
        if pieges is not None:
            vue.pieges = pieges
        return vue

    def test_pomme_dans_le_repere_du_serpent(self):
        # Cap HAUT, pomme en haut a gauche : devant (+1) et a gauche (+1).
        etat = it.encode_complet(self.vue(bd.UP, (3, 2)), bd.UP)
        self.assertEqual(etat[4], (1, 1))
        # Cap DROITE, meme pomme : derriere (-1) et a gauche (+1).
        etat = it.encode_complet(self.vue(bd.RIGHT, (3, 2)), bd.RIGHT)
        self.assertEqual(etat[4], (-1, 1))
        self.assertEqual(
            it.encode_complet(self.vue(bd.UP, None), bd.UP)[4], (0, 0))

    def test_pieges_dans_le_repere_du_serpent(self):
        pieges = {bd.UP: False, bd.LEFT: True, bd.DOWN: True,
                  bd.RIGHT: False}
        etat = it.encode_complet(self.vue(bd.UP, None, pieges), bd.UP)
        self.assertEqual(etat[3], (0, 1, 0))    # devant, gauche, droite
        etat = it.encode_complet(self.vue(bd.RIGHT, None, pieges), bd.RIGHT)
        self.assertEqual(etat[3], (0, 0, 1))    # droite d'un cap DROITE = BAS

    def test_la_croix_reste_la_meme(self):
        vue = self.vue(bd.UP, (5, 2))
        self.assertEqual(it.encode_complet(vue, bd.UP)[:3],
                         it.encode(vue, bd.UP))

    def test_sans_vue_complete_erreur_claire(self):
        board = bd.Board(rng=random.Random(0))
        with self.assertRaises(ValueError):
            it.encode_complet(board.vision_chars(), board.direction)


class TestAgentEtModele(unittest.TestCase):
    def entraine(self, parties=30):
        agent = Agent(rng=random.Random(0), vision=it.VISION_PLATEAU)
        board = bd.Board(rng=random.Random(1))
        for i in range(parties):
            if i:
                board.reset()
            play_session(board, agent, recompense)
        return agent

    def test_par_defaut_la_croix(self):
        self.assertFalse(Agent().vision_complete)
        with self.assertRaises(ValueError):
            Agent(vision="tout")

    def test_apprend_avec_le_plateau(self):
        agent = self.entraine()
        self.assertEqual(agent.parties, 30)
        self.assertTrue(all(len(etat) == 5 for etat in agent.q.table))

    def test_sauver_recharger(self):
        agent = self.entraine()
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "p.txt")
            agent.save(chemin)
            with open(chemin) as f:
                donnees = json.load(f)
            copie = modele.charger(chemin)
        self.assertEqual(donnees["vision"], "plateau")
        self.assertTrue(any("|P" in cle for cle in donnees["qtable"]))
        self.assertTrue(copie.vision_complete)
        self.assertEqual(copie.q.table, agent.q.table)

    def test_ancien_modele_sans_champ_vision(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "a.txt")
            Agent(rng=random.Random(0)).save(chemin)
            with open(chemin) as f:
                donnees = json.load(f)
            del donnees["vision"]
            with open(chemin, "w") as f:
                json.dump(donnees, f)
            self.assertFalse(modele.charger(chemin).vision_complete)

    def test_fichiers_incoherents_refuses(self):
        cas = (
            ("croix", "R2|G2|W3|P010|A+-"),     # cle plateau, modele croix
            ("plateau", "R2|G2|W3"),            # l'inverse
            ("plateau", "R2|G2|W3|P012|A+-"),   # piege ni 0 ni 1
            ("plateau", "R2|G2|W3|P010|A+x"),   # signe inconnu
            ("tout", "R2|G2|W3"),               # vision inconnue
        )
        for vision, cle in cas:
            with self.subTest(vision=vision, cle=cle), \
                    tempfile.TemporaryDirectory() as dossier:
                chemin = os.path.join(dossier, "m.txt")
                Agent(rng=random.Random(0)).save(chemin)
                with open(chemin) as f:
                    donnees = json.load(f)
                donnees["vision"] = vision
                donnees["qtable"] = {cle: {"valeurs": [0, 0, 0],
                                           "visites": [0, 0, 0]}}
                with open(chemin, "w") as f:
                    json.dump(donnees, f)
                with self.assertRaises(modele.ErreurModele):
                    modele.charger(chemin)

    def test_dontlearn_ne_modifie_pas_le_fichier(self):
        agent = self.entraine()
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "p.txt")
            agent.save(chemin)
            with open(chemin, "rb") as f:
                avant = f.read()
            fige = modele.charger(chemin)
            fige.figer()
            board = bd.Board(rng=random.Random(5))
            for i in range(10):
                if i:
                    board.reset()
                play_session(board, fige, recompense)
            fige.save(chemin)
            with open(chemin, "rb") as f:
                self.assertEqual(f.read(), avant)

    def test_chargement_en_ligne_de_commande_previent(self):
        agent = self.entraine(5)
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "p.txt")
            agent.save(chemin)
            erreurs = io.StringIO()
            with contextlib.redirect_stderr(erreurs), \
                    contextlib.redirect_stdout(io.StringIO()):
                creer_agent(GameConfig(model=chemin), random.Random(0))
            self.assertIn("TOUT le plateau", erreurs.getvalue())

    def test_infos_et_partie_graphique(self):
        agent = self.entraine(5)
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "p.txt")
            agent.save(chemin)
            self.assertTrue(models.voit_tout(chemin))
            croix = os.path.join(dossier, "c.txt")
            Agent(rng=random.Random(0)).save(croix)
            self.assertFalse(models.voit_tout(croix))
        self.assertFalse(models.voit_tout(None))
        game = Game(GameConfig(trace=False), agent)
        self.assertTrue(game.vision_complete)
        for _ in range(20):
            if not game.board.alive:
                break
            game._tick()
        self.assertFalse(Game(GameConfig(trace=False),
                              Agent()).vision_complete)


if __name__ == "__main__":
    unittest.main()
