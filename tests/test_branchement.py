"""Etape 12 : l'agent branche dans la ligne de commande et les boucles."""

import contextlib
import io
import itertools
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from src import baselines, session as ss  # noqa: E402
from src.agent import modele  # noqa: E402
from src.agent.agent import Agent  # noqa: E402
from src.agent.fabrique import creer_agent  # noqa: E402
from src.config import GameConfig  # noqa: E402
from src.environment import board as bd  # noqa: E402
from src.environment.rewards import recompense  # noqa: E402
from src.interface import loop  # noqa: E402
from src.interface.game import Game  # noqa: E402
from tests.helpers import (Espion, plateau_nu, pose,  # noqa: E402
                           tour_du_plateau)

import pygame  # noqa: E402

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def silence():
    return contextlib.redirect_stdout(io.StringIO())


class Cfg:
    """Configuration minimale pour run_sessions."""

    def __init__(self, sessions, seed=1, save_path=None):
        self.size = 10
        self.seed = seed
        self.sessions = sessions
        self.save_path = save_path
        self.trace = False


class TestFabrique(unittest.TestCase):
    def test_agent_neuf_par_defaut(self):
        agent = creer_agent(GameConfig(), random.Random(0))
        self.assertIsInstance(agent, Agent)
        self.assertTrue(agent.apprend)
        self.assertEqual(len(agent.q), 0)

    def test_baseline(self):
        agent = creer_agent(GameConfig(baseline="random"), random.Random(0))
        self.assertIsInstance(agent, baselines.RandomAgent)

    def test_dontlearn_fige(self):
        agent = creer_agent(GameConfig(learn=False), random.Random(0))
        self.assertFalse(agent.apprend)
        self.assertEqual(agent.epsilon, 0.0)

    def test_load_recharge(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "m.txt")
            source = Agent(rng=random.Random(0))
            source.parties = 7
            source.save(chemin)
            with silence():
                agent = creer_agent(GameConfig(model=chemin))
            self.assertEqual(agent.parties, 7)

    def test_load_absent(self):
        with self.assertRaises(modele.ErreurModele):
            creer_agent(GameConfig(model="/nulle/part/m.txt"))


class TestBoucleSansAffichage(unittest.TestCase):
    def test_crochets_de_debut_et_de_fin(self):
        """debut_partie recoit le cap, fin_partie est appelee une fois."""
        appels = []

        class Temoin(Agent):
            def debut_partie(self, cap):
                appels.append(("debut", cap))
                super().debut_partie(cap)

            def fin_partie(self):
                appels.append(("fin",))
                super().fin_partie()

        board = bd.Board(size=10, rng=random.Random(2))
        cap = board.direction
        ss.play_session(board, Temoin(rng=random.Random(0)), recompense)
        self.assertEqual(appels[0], ("debut", cap))
        self.assertEqual(appels[1:], [("fin",)])

    def test_l_agent_apprend_pendant_les_sessions(self):
        agent = Agent(rng=random.Random(0))
        with silence():
            ss.run_sessions(Cfg(sessions=20), agent, recompense)
        self.assertEqual(agent.parties, 20)
        self.assertGreater(len(agent.q), 0)
        self.assertGreater(agent.pas_total, 0)

    def test_save_ecrit_un_modele_rechargeable(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "m.txt")
            agent = Agent(rng=random.Random(0))
            with silence():
                ss.run_sessions(Cfg(sessions=5, save_path=chemin), agent,
                                recompense)
            self.assertEqual(modele.charger(chemin).parties, 5)


class TestIlApprendVraiment(unittest.TestCase):
    """La preuve : entraine, il fait nettement mieux que le hasard."""

    def evaluer(self, agent):
        if hasattr(agent, "figer"):
            agent.figer()
        with silence():
            return ss.run_sessions(Cfg(sessions=100, seed=99), agent,
                                   recompense).mean_length

    def test_mieux_que_le_hasard_apres_mille_parties(self):
        agent = Agent(rng=random.Random(0))
        with silence():
            ss.run_sessions(Cfg(sessions=1000, seed=7), agent, recompense)
        hasard = self.evaluer(baselines.RandomAgent(random.Random(0)))
        appris = self.evaluer(agent)
        self.assertLess(hasard, 3.5)
        self.assertGreater(appris, hasard + 1.5)


def partie_graphique(agent, board=None):
    """Game dont le plateau est controle : la partie dure plus d'un pas.

    Le serpent part du centre d'un plateau sans pomme, cap a droite : avec
    3 actions relatives (jamais de demi-tour), il survit au moins 2 pas.
    """
    game = Game(GameConfig(seed=3, trace=False), agent)
    if board is None:
        board = pose(plateau_nu(size=10), (5, 5), bd.RIGHT)
    game.board = board
    game.prev_snake = list(board.snake)
    game.agent_en_partie = False
    game._debut_partie_agent()
    return game


def jouer(game, pas_max=5000):
    for _ in range(pas_max):
        if not game.board.alive:
            break
        game._tick()


class TestBoucleGraphique(unittest.TestCase):
    """Meme contrat que la boucle sans affichage (sans ouvrir de fenetre)."""

    def test_l_agent_pilote_et_apprend(self):
        agent = Agent(rng=random.Random(0))
        game = partie_graphique(agent)
        with silence():
            jouer(game)
        self.assertGreater(game.board.steps, 2, "partie trop courte")
        self.assertEqual(agent.parties, 1)
        self.assertEqual(agent.pas_total, game.board.steps)
        appris = sum(sum(v) for v in agent.q.visites.values())
        self.assertEqual(appris, game.board.steps)

    def test_fin_de_partie_apprise_une_seule_fois(self):
        agent = Agent(rng=random.Random(0))
        game = partie_graphique(agent)
        with silence():
            jouer(game)
            game.close()
            game.close()
        self.assertEqual(agent.parties, 1)

    def test_partie_abandonnee_apprise_au_restart(self):
        agent = Agent(rng=random.Random(0))
        game = partie_graphique(agent)
        with silence():
            game._tick()
            game._tick()
            self.assertTrue(game.board.alive, "doit etre en cours")
            game.restart()
        self.assertEqual(agent.parties, 1)
        self.assertEqual(sum(sum(v) for v in agent.q.visites.values()), 2)
        self.assertEqual(agent.cap, game.board.direction)

    def test_troncature_bootstrappe_et_garde_son_cout(self):
        board = plateau_nu(size=5, idle_factor=1)
        chemin = list(itertools.islice(tour_du_plateau(board), 40))
        espion = Espion(chemin)
        game = partie_graphique(espion, board)
        with silence():
            jouer(game)
        self.assertTrue(game.board.truncated)
        dernier = espion.recu[-1]
        self.assertEqual(dernier["reward"], recompense(bd.MOVE))
        self.assertFalse(dernier["done"])
        self.assertEqual(dernier["next_state"], game.board.vision_chars())
        self.assertNotEqual(dernier["next_state"], dernier["state"])

    def test_mort_sans_etat_suivant(self):
        board = pose(plateau_nu(size=5), (0, 2), bd.LEFT)
        espion = Espion([bd.LEFT])
        game = partie_graphique(espion, board)
        with silence():
            jouer(game)
        dernier = espion.recu[-1]
        self.assertTrue(dernier["done"])
        self.assertEqual(dernier["reward"], recompense(bd.WALL))
        self.assertEqual(dernier["next_state"], dernier["state"])

    def test_pilote_humain_l_agent_ne_joue_pas(self):
        agent = Agent(rng=random.Random(0))
        game = Game(GameConfig(pilot="joueur", seed=3, trace=False), agent)
        with silence():
            game._tick()
        self.assertEqual(agent.pas_total, 0)


class TestBoucleDuLobby(unittest.TestCase):
    """src/interface/loop.py : lobby, Echap, fermeture et sauvegarde."""

    class LobbyFactice:
        def handle_key(self, key):
            return loop.START

    def demarrer(self, config, pilote):
        evenement = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        with silence(), contextlib.redirect_stderr(io.StringIO()):
            return loop._lobby_event(evenement, self.LobbyFactice(), config,
                                     None, True, pilote)

    def test_fermeture_apprend_la_partie_en_cours_puis_sauve(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "m.txt")
            agent = Agent(rng=random.Random(0))
            game = partie_graphique(agent)
            game._tick()
            config = GameConfig(save_path=chemin)
            with silence():
                loop._terminer(game, config, loop.PiloteAgent(config, agent))
            self.assertEqual(modele.charger(chemin).parties, 1)

    def test_fermeture_chemin_impossible_ne_plante_pas(self):
        with tempfile.TemporaryDirectory() as dossier:
            config = GameConfig(save_path=dossier)
            agent = Agent(rng=random.Random(0))
            erreurs, sortie = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(sortie), \
                    contextlib.redirect_stderr(erreurs):
                reussi = loop._terminer(partie_graphique(agent), config,
                                        loop.PiloteAgent(config, agent))
            self.assertFalse(reussi)
            self.assertIn("Erreur", erreurs.getvalue())
            self.assertNotIn("Sauvegarde", sortie.getvalue())

    def test_agent_de_la_ligne_de_commande_reutilise(self):
        """Sans lobby au depart : Echap puis relance garde l'agent fourni."""
        config = GameConfig()
        agent = Agent(rng=random.Random(0))
        _, game, _ = self.demarrer(config, loop.PiloteAgent(config, agent))
        self.assertIs(game.agent, agent)

    def test_sauve_l_agent_du_pilote_apres_une_partie_au_clavier(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "m.txt")
            agent = Agent(rng=random.Random(0))
            agent.parties = 5
            config = GameConfig(save_path=chemin, pilot="joueur")
            manuel = Game(config, None)
            with silence():
                loop._terminer(manuel, config,
                               loop.PiloteAgent(config, agent))
            self.assertEqual(modele.charger(chemin).parties, 5)

    def test_echap_apprend_la_partie_en_cours(self):
        agent = Agent(rng=random.Random(0))
        game = partie_graphique(agent)
        game._tick()
        etat, _ = loop._game_event(pygame.K_ESCAPE, game, True)
        self.assertEqual(etat, loop.SCREEN_LOBBY)
        self.assertEqual(agent.parties, 1)

    def test_relance_garde_le_meme_agent(self):
        """Echap puis relance : l'apprentissage n'est pas perdu."""
        config = GameConfig()
        pilote = loop.PiloteAgent(config)
        _, premier, _ = self.demarrer(config, pilote)
        _, second, _ = self.demarrer(config, pilote)
        self.assertIs(second.agent, premier.agent)

    def test_autre_modele_choisi_autre_agent(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "m.txt")
            source = Agent(rng=random.Random(0))
            source.parties = 9
            source.save(chemin)
            config = GameConfig()
            pilote = loop.PiloteAgent(config, Agent(rng=random.Random(1)))
            config.model = chemin
            _, game, _ = self.demarrer(config, pilote)
            self.assertEqual(game.agent.parties, 9)
            self.assertIs(pilote.agent, game.agent)

    def test_modele_invalide_reste_dans_le_lobby(self):
        ancien = Agent(rng=random.Random(1))
        config = GameConfig()
        pilote = loop.PiloteAgent(config, ancien)
        config.model = "/nulle/part/m.txt"
        etat, game, _ = self.demarrer(config, pilote)
        self.assertEqual(etat, loop.SCREEN_LOBBY)
        self.assertIsNone(game)
        self.assertIs(pilote.agent, ancien)

    def test_pilote_humain_sans_agent(self):
        config = GameConfig(pilot="joueur")
        etat, game, _ = self.demarrer(config, loop.PiloteAgent(config))
        self.assertEqual(etat, loop.SCREEN_GAME)
        self.assertIsNone(game.agent)


class TestBoucleComplete(unittest.TestCase):
    """loop.run de bout en bout, fenetre factice (SDL_VIDEODRIVER=dummy)."""

    def lancer_puis_ctrl_c(self, chemin):
        agent = Agent(rng=random.Random(0))
        appels = {"n": 0}
        mise_a_jour = Game.update

        def puis_interrompre(game, dt):
            appels["n"] += 1
            if appels["n"] > 20:
                raise KeyboardInterrupt
            mise_a_jour(game, dt)

        config = GameConfig(save_path=chemin, speed=30, trace=False)
        with mock.patch.object(Game, "update", puis_interrompre), \
                silence(), contextlib.redirect_stderr(io.StringIO()):
            reussi = loop.run(config, skip_lobby=True, agent=agent)
        return reussi, agent

    def test_ctrl_c_ferme_proprement_et_sauve(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "m.txt")
            reussi, agent = self.lancer_puis_ctrl_c(chemin)
            self.assertTrue(reussi)
            self.assertEqual(modele.charger(chemin).pas_total,
                             agent.pas_total)

    def test_sauvegarde_impossible_signalee(self):
        with tempfile.TemporaryDirectory() as dossier:
            reussi, _ = self.lancer_puis_ctrl_c(dossier)
            self.assertFalse(reussi)


class TestPointDEntree(unittest.TestCase):
    """main.py appele dans le meme processus, pour pouvoir le piloter."""

    def lancer_main(self, *arguments):
        import main
        erreurs = io.StringIO()
        with mock.patch.object(sys, "argv", ["main.py", *arguments]), \
                silence(), contextlib.redirect_stderr(erreurs):
            try:
                main.main()
                code = 0
            except SystemExit as sortie:
                code = sortie.code
        return code, erreurs.getvalue()

    def test_echec_de_sauvegarde_apres_l_entrainement(self):
        """Le chemin devient invalide pendant l'entrainement : pas de trace."""
        import main
        panne = modele.ErreurModele("disque plein")
        with mock.patch.object(main, "run_sessions", side_effect=panne):
            code, erreurs = self.lancer_main("-visual", "off")
        self.assertEqual(code, 1)
        self.assertIn("Erreur : disque plein", erreurs)

    def test_save_vide_refuse(self):
        code, erreurs = self.lancer_main("-visual", "off", "-save", "")
        self.assertEqual(code, 1)
        self.assertIn("vide", erreurs)


class TestInterruption(unittest.TestCase):
    def test_ctrl_c_arrete_vraiment_l_entrainement(self):
        """Une seule interruption doit arreter, pas sauter une partie."""

        class InterrompuUneFois(Agent):
            deja = False

            def debut_partie(self, cap):
                if self.parties == 2 and not self.deja:
                    self.deja = True
                    raise KeyboardInterrupt
                super().debut_partie(cap)

        agent = InterrompuUneFois(rng=random.Random(0))
        with silence():
            stats = ss.run_sessions(Cfg(sessions=10), agent, recompense)
        self.assertEqual(stats.games, 2)
        self.assertEqual(agent.parties, 2)

    def test_ctrl_c_garde_les_parties_terminees(self):
        """Ctrl+C pendant la 3e partie : les 2 premieres sont sauvees."""

        class Interrompu(Agent):
            def debut_partie(self, cap):
                if self.parties == 2:
                    raise KeyboardInterrupt
                super().debut_partie(cap)

        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "m.txt")
            agent = Interrompu(rng=random.Random(0))
            with silence():
                stats = ss.run_sessions(
                    Cfg(sessions=10, save_path=chemin), agent, recompense)
            self.assertEqual(stats.games, 2)
            self.assertEqual(modele.charger(chemin).parties, 2)


class TestLigneDeCommande(unittest.TestCase):
    """Les commandes du sujet, lancees pour de vrai."""

    def lancer(self, *arguments):
        return subprocess.run(
            [sys.executable, "-B", "main.py", "-visual", "off", *arguments],
            cwd=RACINE, capture_output=True, text=True, timeout=120,
        )

    def test_entrainer_sauver_recharger_evaluer(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "10sess.txt")
            entrainement = self.lancer("-sessions", "10", "-save", chemin)
            self.assertEqual(entrainement.returncode, 0)
            self.assertIn("Sauvegarde", entrainement.stdout)
            with open(chemin, "rb") as fichier:
                avant = fichier.read()

            evaluation = self.lancer("-load", chemin, "-sessions", "3",
                                     "-dontlearn", "-save", chemin)
            self.assertEqual(evaluation.returncode, 0)
            self.assertIn("Chargement", evaluation.stdout)
            with open(chemin, "rb") as fichier:
                self.assertEqual(fichier.read(), avant,
                                 "-dontlearn ne doit rien modifier")

    def test_l_entrainement_apprend_vraiment(self):
        """Sans la fonction de recompense, -save ecrirait une table vide."""
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "m.txt")
            self.lancer("-sessions", "10", "-save", chemin)
            agent = modele.charger(chemin)
            self.assertEqual(agent.parties, 10)
            self.assertGreater(len(agent.q), 0)

    def test_meme_graine_meme_resultat(self):
        with tempfile.TemporaryDirectory() as dossier:
            sorties, fichiers = [], []
            for nom in ("a.txt", "b.txt"):
                chemin = os.path.join(dossier, nom)
                sorties.append(self.lancer("-sessions", "20", "-seed", "5",
                                           "-save", chemin).stdout)
                with open(chemin, "rb") as fichier:
                    fichiers.append(fichier.read())
            self.assertEqual(sorties[0].replace("b.txt", "a.txt"),
                             sorties[1].replace("b.txt", "a.txt"))
            self.assertEqual(fichiers[0], fichiers[1])

    def test_meme_graine_meme_resultat_avec_load(self):
        modele_livre = os.path.join("models", "10sess.txt")
        sorties = [
            self.lancer("-load", modele_livre, "-sessions", "5",
                        "-seed", "5").stdout
            for _ in range(2)
        ]
        self.assertEqual(sorties[0], sorties[1])

    def test_save_sans_nom_de_fichier_refuse(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "nouveau") + os.sep
            resultat = self.lancer("-sessions", "3", "-save", chemin)
        self.assertEqual(resultat.returncode, 1)
        self.assertNotIn("Fin de la partie", resultat.stdout)
        self.assertNotIn("Traceback", resultat.stderr)

    def test_save_impossible_refuse_avant_l_entrainement(self):
        with tempfile.TemporaryDirectory() as dossier:
            resultat = self.lancer("-sessions", "5", "-save", dossier)
        self.assertEqual(resultat.returncode, 1)
        self.assertIn("Erreur", resultat.stderr)
        self.assertNotIn("Fin de la partie", resultat.stdout)
        self.assertNotIn("Traceback", resultat.stderr)

    def test_modele_corrompu_message_clair(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "m.txt")
            Agent(rng=random.Random(0)).save(chemin)
            with open(chemin, encoding="utf-8") as fichier:
                donnees = json.load(fichier)
            donnees["hyperparametres"] = {}
            with open(chemin, "w", encoding="utf-8") as fichier:
                json.dump(donnees, fichier)
            resultat = self.lancer("-load", chemin)
        self.assertEqual(resultat.returncode, 1)
        self.assertIn("corrompu", resultat.stderr)
        self.assertNotIn("Traceback", resultat.stderr)

    def test_modele_absent_message_clair(self):
        resultat = self.lancer("-load", "/nulle/part/m.txt")
        self.assertEqual(resultat.returncode, 1)
        self.assertIn("introuvable", resultat.stderr)
        self.assertNotIn("Traceback", resultat.stderr)


if __name__ == "__main__":
    unittest.main()
