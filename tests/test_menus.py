"""Menu principal, choix du modele, entrainement et evaluation en fenetre."""

import contextlib
import io
import os
import random
import shutil
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from src import config as cfg  # noqa: E402
from src import models  # noqa: E402
from src.agent import modele  # noqa: E402
from src.agent.agent import Agent  # noqa: E402
from src.config import GameConfig  # noqa: E402
from src.environment import board as bd  # noqa: E402
from src.evaluation import Bilan, Photo  # noqa: E402
from src.interface import loop, theme, widgets  # noqa: E402
from src.interface.evaluation_view import EvaluationGame  # noqa: E402
from src.interface.panel_view import recadrer  # noqa: E402
from src.training import Entrainement  # noqa: E402

import pygame  # noqa: E402


def silence():
    """Coupe stdout et stderr (traces de partie, messages de chargement)."""
    pile = contextlib.ExitStack()
    pile.enter_context(contextlib.redirect_stdout(io.StringIO()))
    pile.enter_context(contextlib.redirect_stderr(io.StringIO()))
    return pile


def modele_sur_disque(dossier, nom, parties):
    agent = Agent(rng=random.Random(0))
    agent.parties = parties
    chemin = os.path.join(dossier, nom + ".txt")
    agent.save(chemin)
    return chemin


class DossierModeles(unittest.TestCase):
    """Chaque test travaille dans un dossier temporaire avec models/."""

    def setUp(self):
        self.ancien = os.getcwd()
        self.racine = tempfile.mkdtemp()
        os.chdir(self.racine)
        os.mkdir(models.MODELS_DIR)

    def tearDown(self):
        os.chdir(self.ancien)
        shutil.rmtree(self.racine)


# -- Bornes -------------------------------------------------------------------

class TestBornes(unittest.TestCase):
    def test_plateau_jusqu_a_50(self):
        config = GameConfig(size=10)
        for _ in range(100):
            config.change_size(1)
        self.assertEqual(config.size, 50)
        self.assertEqual(GameConfig(size=999).size, 50)

    def test_plateau_de_5_en_5(self):
        config = GameConfig(size=5)
        vues = [config.size]
        for _ in range(12):
            config.change_size(1)
            vues.append(config.size)
        self.assertEqual(vues[:10], list(range(5, 51, 5)))
        self.assertEqual(vues[-1], 50)
        # Taille hors liste (-size 12) : cran voisin, sans en sauter un.
        config = GameConfig(size=12)
        config.change_size(1)
        self.assertEqual(config.size, 15)
        config = GameConfig(size=12)
        config.change_size(-1)
        self.assertEqual(config.size, 10)

    def test_crans_de_vitesse(self):
        config = GameConfig(speed=1)
        vues = [config.speed]
        for _ in range(15):
            config.change_speed(1)
            vues.append(config.speed)
        self.assertEqual(vues[:11], [1, 5, 10, 15, 20, 30, 40, 50, 75, 100,
                                     cfg.VITESSE_MAX])
        self.assertEqual(vues[-1], cfg.VITESSE_MAX)
        self.assertEqual(GameConfig(speed=1e9).speed, 100.0)
        self.assertEqual(GameConfig(speed=float("inf")).speed,
                         cfg.VITESSE_MAX)
        self.assertEqual(GameConfig(speed=float("nan")).speed,
                         cfg.DEFAULT_SPEED)
        self.assertEqual(cfg.libelle_vitesse(cfg.VITESSE_MAX), "MAX")
        self.assertEqual(cfg.libelle_vitesse(15.0), "15 / s")

    def test_jeu_memes_crans_que_le_lobby(self):
        from src.interface.game import Game
        game = Game(GameConfig(pilot=cfg.PILOT_HUMAN, speed=6,
                               trace=False))
        game.change_speed(1)
        self.assertEqual(game.speed, 10)
        game.change_speed(-1)
        self.assertEqual(game.speed, 5)
        for _ in range(20):
            game.change_speed(1)
        self.assertEqual(game.speed, cfg.VITESSE_MAX)

    def test_vitesse_max_avance_sans_boucle_infinie(self):
        from src.interface.game import Game
        game = Game(GameConfig(pilot=cfg.PILOT_HUMAN, speed=float("inf"),
                               size=50, trace=False, seed=1))
        self.assertEqual(game.progress(), 1.0)
        game.update(1 / 60)
        self.assertGreater(game.board.steps, 1)

    def test_parties_jusqu_a_dix_millions(self):
        from src.interface.training_view import AJOUTS
        self.assertEqual(AJOUTS[-1], 10_000_000)
        apres = AJOUTS[AJOUTS.index(1_000_000):]
        self.assertEqual(list(apres),
                         [n * 1_000_000 for n in range(1, 11)])
        self.assertEqual(list(AJOUTS), sorted(set(AJOUTS)))


class TestPasAPas(unittest.TestCase):
    def _game(self, speed=5):
        from src.interface.game import Game
        return Game(GameConfig(pilot=cfg.PILOT_HUMAN, speed=speed,
                               trace=False))

    def test_n_passe_en_pas_a_pas_et_avance(self):
        game = self._game()
        self.assertFalse(game.step_by_step)
        game.request_step()
        self.assertTrue(game.step_by_step)
        for _ in range(60):
            game.update(1 / 60)
        self.assertEqual(game.board.steps, 1)

    def test_corps_fini_d_animer_apres_un_pas(self):
        """Bug : apres N, le corps restait a l'ancienne place."""
        game = self._game()
        game.request_step()
        for _ in range(60):
            game.update(1 / 60)
        self.assertEqual(game.board.steps, 1)
        self.assertEqual(game.progress(), 1.0)
        from src.interface.board_view import cell_center
        attendus = [cell_center(game.board.size, c)
                    for c in game.board.snake]
        for point, attendu in zip(game.snake_points(), attendus):
            self.assertAlmostEqual(point[0], attendu[0])
            self.assertAlmostEqual(point[1], attendu[1])

    def test_pas_a_pas_a_vitesse_max(self):
        game = self._game(speed=float("inf"))
        game.request_step()
        game.update(1 / 60)
        game.update(1 / 60)
        self.assertEqual(game.board.steps, 1)

    def test_aide_coloree_selon_l_etat(self):
        from src.interface import theme
        from src.interface.panel_view import hints_for
        game = self._game()
        lignes = dict((t.split()[0], c) for t, c in hints_for(game))
        self.assertEqual(lignes["P"], theme.ORANGE)
        self.assertEqual(lignes["V"], theme.GREEN_APPLE)
        game.toggle_step_mode()
        game.show_vision = False
        lignes = dict((t.split()[0], c) for t, c in hints_for(game))
        self.assertEqual(lignes["P"], theme.GREEN_APPLE)
        self.assertEqual(lignes["V"], theme.ORANGE)
        textes = [t for t, _ in hints_for(game)]
        self.assertTrue(any(t.startswith("R ") for t in textes))
        self.assertFalse(any("/ P" in t or "V / T" in t for t in textes))


class TestBornesSuite(unittest.TestCase):
    def test_100_cases_par_seconde_plusieurs_pas_par_image(self):
        from src.interface.game import Game
        game = Game(GameConfig(pilot=cfg.PILOT_HUMAN, speed=100, size=50,
                               trace=False))
        game.update(1 / 60)
        self.assertGreaterEqual(game.board.steps, 1)


# -- Modeles sur le disque ----------------------------------------------------

class TestModeles(DossierModeles):
    def test_infos_lues_dans_le_fichier(self):
        chemin = modele_sur_disque(models.MODELS_DIR, "m", 42)
        infos = models.infos(chemin)
        self.assertTrue(infos.lisible)
        self.assertEqual((infos.nom, infos.parties), ("m", 42))
        self.assertEqual(infos.gamma, 0.95)

    def test_fichier_illisible_ne_plante_pas(self):
        chemin = os.path.join(models.MODELS_DIR, "casse.txt")
        with open(chemin, "w") as fichier:
            fichier.write("pas du json")
        infos = models.infos(chemin)
        self.assertFalse(infos.lisible)
        self.assertTrue(infos.erreur)

    def test_infos_relues_si_le_fichier_change(self):
        chemin = modele_sur_disque(models.MODELS_DIR, "m", 1)
        self.assertEqual(models.infos(chemin).parties, 1)
        agent = modele.charger(chemin)
        agent.parties = 7
        agent.save(chemin)
        os.utime(chemin, ns=(1, 10 ** 18))
        self.assertEqual(models.infos(chemin).parties, 7)

    def test_meilleur_modele_le_plus_entraine(self):
        modele_sur_disque(models.MODELS_DIR, "petit", 10)
        grand = modele_sur_disque(models.MODELS_DIR, "grand", 500)
        self.assertEqual(models.meilleur_modele(), grand)

    def test_meilleur_modele_aucun(self):
        self.assertIsNone(models.meilleur_modele())

    def test_tries_du_moins_au_plus_entraine(self):
        modele_sur_disque(models.MODELS_DIR, "b", 500)
        modele_sur_disque(models.MODELS_DIR, "a", 10)
        self.assertEqual([i.nom for i in models.modeles()], ["a", "b"])

    def test_nom_de_nouveau_modele(self):
        modele_sur_disque(models.MODELS_DIR, "pris", 1)
        self.assertIsNone(models.probleme_de_nom("mon-modele_2"))
        for mauvais in ("", "pris", "../evasion", "a/b", "a b",
                        "x" * (models.NOM_MAX + 1)):
            with self.subTest(nom=mauvais):
                self.assertIsNotNone(models.probleme_de_nom(mauvais))


# -- Entrainement -------------------------------------------------------------

class TestEntrainement(DossierModeles):
    def test_va_jusqu_a_l_objectif_puis_sauve(self):
        chemin = os.path.join(models.MODELS_DIR, "neuf.txt")
        run = Entrainement(Agent(rng=random.Random(0)), chemin, 30,
                           seed=1)
        while not run.fini:
            run.avancer(1.0)
        self.assertEqual(run.jouees, 30)
        self.assertEqual(run.progression, 1.0)
        self.assertEqual(modele.charger(chemin).parties, 30)

    def test_continuer_ajoute_des_parties(self):
        chemin = modele_sur_disque(models.MODELS_DIR, "m", 20)
        agent = modele.charger(chemin)
        run = Entrainement(agent, chemin, 25, seed=1)
        while not run.fini:
            run.avancer(1.0)
        self.assertEqual(run.jouees, 5)
        self.assertEqual(modele.charger(chemin).parties, 25)

    def test_par_tranches(self):
        """Budget nul : une seule partie par appel, la fenetre reste
        fluide."""
        run = Entrainement(Agent(rng=random.Random(0)),
                           os.path.join(models.MODELS_DIR, "t.txt"), 10)
        run.avancer(0.0)
        self.assertEqual(run.jouees, 1)
        self.assertFalse(run.fini)

    def test_arret_sauve_les_parties_jouees(self):
        chemin = os.path.join(models.MODELS_DIR, "stop.txt")
        run = Entrainement(Agent(rng=random.Random(0)), chemin, 1000)
        run.avancer(0.0)
        run.avancer(0.0)
        self.assertTrue(run.terminer())
        self.assertEqual(modele.charger(chemin).parties, 2)
        self.assertTrue(run.terminer())   # deuxieme appel sans effet

    def test_echec_d_ecriture_signale(self):
        run = Entrainement(Agent(rng=random.Random(0)),
                           models.MODELS_DIR, 1)
        run.avancer(1.0)
        self.assertTrue(run.fini)
        self.assertIsNotNone(run.erreur)

    def test_objectif_deja_atteint(self):
        agent = Agent(rng=random.Random(0))
        agent.parties = 50
        run = Entrainement(agent, os.path.join(models.MODELS_DIR, "x.txt"),
                           10)
        run.avancer(1.0)
        self.assertEqual(run.jouees, 0)
        self.assertTrue(run.fini)


# -- Evaluation ---------------------------------------------------------------

class TestBilan(unittest.TestCase):
    def finir(self, bilan, longueur):
        board = bd.Board(rng=random.Random(0))
        bilan.debut_partie(board)
        board.max_length = longueur
        bilan.apres_pas(board)
        return bilan.fin_partie(board)

    def test_continue_sous_le_seuil(self):
        bilan = Bilan(seuil=35)
        self.assertFalse(self.finir(bilan, 34))
        self.assertFalse(bilan.atteint)

    def test_s_arrete_a_la_fin_de_la_partie_qui_atteint_le_seuil(self):
        bilan = Bilan(seuil=35)
        self.finir(bilan, 10)
        self.assertTrue(self.finir(bilan, 41))
        numero, photos = bilan.a_rejouer()
        self.assertEqual(numero, 2)
        self.assertEqual(photos[-1].max_length, 41)
        self.assertEqual(bilan.stats.games, 2)
        self.assertEqual(bilan.stats.max_length, 41)

    def test_arretee_avant_rejoue_la_meilleure(self):
        bilan = Bilan(seuil=35)
        self.finir(bilan, 20)
        self.finir(bilan, 12)
        numero, photos = bilan.a_rejouer()
        self.assertEqual((numero, photos[-1].max_length), (1, 20))

    def test_arretee_en_pleine_meilleure_partie(self):
        bilan = Bilan(seuil=35)
        self.finir(bilan, 5)
        board = bd.Board(rng=random.Random(0))
        bilan.debut_partie(board)
        board.max_length = 30
        bilan.apres_pas(board)
        numero, photos = bilan.a_rejouer()
        self.assertEqual((numero, photos[-1].max_length), (2, 30))

    def test_photo_restauree_a_l_identique(self):
        board = bd.Board(rng=random.Random(3))
        for _ in range(5):
            board.step(board.direction)
            if not board.alive:
                break
        photo = Photo(board)
        autre = bd.Board(rng=random.Random(99))
        photo.restaurer(autre)
        self.assertEqual(autre.snake, board.snake)
        self.assertEqual(autre.greens, board.greens)
        self.assertEqual(autre.vision_chars(), board.vision_chars())
        self.assertEqual(autre.end_cause, board.end_cause)


class TestPartieEvaluation(unittest.TestCase):
    def partie(self, seuil):
        agent = Agent(rng=random.Random(0))
        agent.figer()
        config = GameConfig(learn=False, trace=False, speed=100, seed=4)
        return EvaluationGame(config, agent, seuil=seuil), agent

    def jouer(self, game, limite=200_000):
        with silence():
            for _ in range(limite):
                if game.fini:
                    return
                game.update(0.5)

    def test_enchaine_jusqu_au_seuil_sans_apprendre(self):
        game, agent = self.partie(seuil=4)
        self.jouer(game)
        self.assertTrue(game.fini)
        self.assertTrue(game.bilan.atteint)
        self.assertGreaterEqual(game.bilan.stats.max_length, 4)
        self.assertEqual((agent.parties, agent.pas_total, len(agent.q)),
                         (0, 0, 0))

    def test_une_photo_par_pas(self):
        game, _ = self.partie(seuil=4)
        self.jouer(game)
        _, photos = game.bilan.a_rejouer()
        self.assertEqual(len(photos), photos[-1].steps + 1)

    def test_espace_sur_la_derniere_partie_donne_les_resultats(self):
        game, _ = self.partie(seuil=4)
        with silence():
            while not game.termine:
                game.update(0.05)
        game.restart()
        self.assertTrue(game.fini)

    def test_pause_courte_si_objectif_rate(self):
        game, _ = self.partie(seuil=4)
        for vitesse in (1.0, 10.0, 100.0, float("inf")):
            game.speed = vitesse
            game.termine = False
            rate = game.pause_fin
            game.termine = True
            self.assertLessEqual(rate, 0.4)
            self.assertLessEqual(rate, game.pause_fin)
            if vitesse >= 40:
                self.assertEqual(rate, 0.0)

    def test_pas_d_ecran_de_fin_a_grande_vitesse(self):
        game, _ = self.partie(seuil=10_000)
        game.speed = 40.0
        with silence():
            for _ in range(5_000):
                game.update(0.05)
                self.assertTrue(game.board.alive)
        self.assertGreater(game.bilan.stats.games, 1)


class TestRetourEnArriere(unittest.TestCase):
    """Pas a pas avec l'IA : GAUCHE recule, DROITE avance."""

    def partie(self):
        from src.interface.game import Game
        agent = Agent(rng=random.Random(0))
        config = GameConfig(trace=False, speed=100, seed=0, size=20)
        game = Game(config, agent)
        game.toggle_step_mode()
        return game, agent

    def pas(self, game, n):
        for _ in range(n):
            loop.handle_key(game, pygame.K_RIGHT)
            game.update(0.05)

    def test_gauche_puis_droite_revient_au_meme_present(self):
        game, agent = self.partie()
        self.pas(game, 5)
        self.assertEqual(game.board.steps, 5)
        present = (list(game.board.snake), list(game.board.greens),
                   game.board.idle, game.board.direction)
        appris = agent.pas_total
        for attendu in (4, 3, 2):
            loop.handle_key(game, pygame.K_LEFT)
            game.update(0.05)
            self.assertEqual(game.board.steps, attendu)
        self.assertEqual(game.recul, 3)
        # On regarde le passe : rien n'est joue ni appris.
        for _ in range(30):
            game.update(0.05)
        self.assertEqual(game.board.steps, 2)
        self.assertEqual(agent.pas_total, appris)
        self.pas(game, 3)
        self.assertEqual(game.recul, 0)
        self.assertEqual(agent.pas_total, appris)
        self.assertEqual((list(game.board.snake), list(game.board.greens),
                          game.board.idle, game.board.direction), present)
        # Au present, DROITE joue de nouveau un vrai pas.
        self.pas(game, 1)
        self.assertEqual(game.board.steps, 6)
        self.assertEqual(agent.pas_total, appris + 1)

    def test_gauche_s_arrete_au_debut(self):
        game, _ = self.partie()
        self.pas(game, 2)
        for _ in range(10):
            loop.handle_key(game, pygame.K_LEFT)
        self.assertEqual(game.board.steps, 0)
        self.assertEqual(game.recul, 2)

    def test_quitter_le_pas_a_pas_revient_au_present(self):
        game, _ = self.partie()
        self.pas(game, 3)
        loop.handle_key(game, pygame.K_LEFT)
        loop.handle_key(game, pygame.K_p)
        self.assertEqual((game.recul, game.board.steps), (0, 3))

    def test_gauche_sans_effet_hors_pas_a_pas(self):
        game, _ = self.partie()
        self.pas(game, 2)
        game.toggle_step_mode()
        loop.handle_key(game, pygame.K_LEFT)
        self.assertEqual(game.recul, 0)

    def test_au_clavier_les_fleches_dirigent_toujours(self):
        from src.interface.game import Game
        game = Game(GameConfig(pilot=cfg.PILOT_HUMAN, trace=False, seed=1))
        game.toggle_step_mode()
        cap = game.board.direction
        fleche = pygame.K_UP if cap in (bd.LEFT, bd.RIGHT) else \
            pygame.K_LEFT
        loop.handle_key(game, fleche)
        self.assertEqual(game.recul, 0)
        self.assertEqual(len(game.pending), 1)

    def test_en_pas_a_pas_la_fin_attend_n(self):
        from src.interface.game import Game
        game = Game(GameConfig(pilot=cfg.PILOT_HUMAN, trace=False, seed=1,
                               speed=100), None)
        game.config.sessions = game.sessions = 3
        game.toggle_step_mode()
        with silence():
            while game.board.alive:
                game.pas_suivant()
                game.update(0.05)
        for _ in range(100):
            game.update(0.05)
        self.assertEqual(game.session, 1)
        self.assertIn("[N]", game.fin_hint)
        game.pas_suivant()
        game.update(0.05)
        self.assertEqual(game.session, 2)


class TestObjectifEvaluation(unittest.TestCase):
    def test_reglage_de_5_en_5_defaut_35(self):
        config = GameConfig()
        self.assertEqual(config.objectif, 35)
        config.change_objectif(1)
        self.assertEqual(config.objectif, 40)
        for _ in range(50):
            config.change_objectif(-1)
        self.assertEqual(config.objectif, 5)

    def test_l_evaluation_utilise_l_objectif_choisi(self):
        pygame.init()
        app = loop.Application(
            pygame.display.set_mode((1, 1)), GameConfig(trace=False))
        app.eval_config.objectif = 10
        app.eval_config.model = None
        app._lancer_evaluation()
        self.assertEqual(app.eval_game.bilan.seuil, 10)
        champs = [c.label for c in app.eval_setup.formulaire.champs]
        self.assertIn("OBJECTIF", champs)
        self.assertNotIn("OBJECTIF",
                         [c.label for c in app.lobby.formulaire.champs])


class TestAidesDesParametres(unittest.TestCase):
    def test_gamma(self):
        from src.interface.training_view import aide_gamma
        self.assertIn("~20 coups", aide_gamma(0.95))
        self.assertIn("~5 coups", aide_gamma(0.8))
        self.assertIn("~100 coups", aide_gamma(0.99))
        self.assertIn("coup present", aide_gamma(0.0))

    def test_epsilon_min(self):
        from src.interface.training_view import aide_epsilon_min
        self.assertIn("1 coup sur 100", aide_epsilon_min(0.01))
        self.assertIn("1 coup sur 20", aide_epsilon_min(0.05))
        self.assertIn("50 %", aide_epsilon_min(0.5))
        self.assertIn("aucun hasard", aide_epsilon_min(0.0))
        self.assertIn("toujours", aide_epsilon_min(1.0))

    def test_gamma_jamais_a_1(self):
        from src.interface.training_view import GAMMAS
        self.assertLess(max(GAMMAS), 1.0)


# -- Panneau ------------------------------------------------------------------

class TestRecadrage(unittest.TestCase):
    def test_petit_plateau_intact(self):
        lignes = bd.Board(size=10, rng=random.Random(0)).vision_lines()
        self.assertEqual(recadrer(lignes, 20, 40), (lignes, False))

    def test_grand_plateau_centre_sur_la_tete(self):
        board = bd.Board(size=50, rng=random.Random(0))
        lignes, recadree = recadrer(board.vision_lines(), 15, 40)
        self.assertTrue(recadree)
        self.assertLessEqual(len(lignes), 15)
        self.assertTrue(all(len(ligne) <= 40 for ligne in lignes))
        self.assertTrue(any(bd.HEAD_CHAR in ligne for ligne in lignes))


# -- Formulaire ---------------------------------------------------------------

class TestFormulaire(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.valeur = [0]
        self.actif = [True]
        self.saisie = widgets.Saisie("NOM")
        self.form = widgets.Formulaire(theme.load_fonts(), [
            self.saisie,
            widgets.Reglage("X", lambda: str(self.valeur[0]),
                            self._changer, actif=lambda: self.actif[0]),
            widgets.Lien("L", lambda: "-", "ouvrir"),
        ], "OK", y=100)

    def _changer(self, delta):
        self.valeur[0] += delta

    def test_les_lettres_ecrivent_sans_deplacer(self):
        for touche in (pygame.K_s, pygame.K_z, pygame.K_q, pygame.K_d):
            self.assertIsNone(self.form.handle_key(touche))
        self.form.handle_text("sdz")
        self.assertEqual((self.form.index, self.saisie.valeur), (0, "sdz"))
        self.form.handle_key(pygame.K_BACKSPACE)
        self.assertEqual(self.saisie.valeur, "sd")

    def test_espace_dans_un_nom_ne_lance_pas(self):
        self.assertIsNone(self.form.handle_key(pygame.K_SPACE))

    def test_reglage_et_lien(self):
        self.form.handle_key(pygame.K_DOWN)
        self.form.handle_key(pygame.K_RIGHT)
        self.assertEqual(self.valeur[0], 1)
        self.form.handle_key(pygame.K_DOWN)
        self.assertEqual(self.form.handle_key(pygame.K_RETURN), "ouvrir")

    def test_champ_inactif_saute(self):
        self.actif[0] = False
        self.form.handle_key(pygame.K_DOWN)
        self.assertEqual(self.form.index, 2)

    def test_entree_lance(self):
        self.assertEqual(self.form.handle_key(pygame.K_RETURN),
                         widgets.START)


# -- Navigation entre les ecrans ----------------------------------------------

def touche(app, key, fois=1):
    for _ in range(fois):
        app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key))


class TestApplication(DossierModeles):
    def setUp(self):
        super().setUp()
        self.petit = modele_sur_disque(models.MODELS_DIR, "petit", 3)
        self.grand = modele_sur_disque(models.MODELS_DIR, "grand", 300)
        pygame.init()
        screen = pygame.display.set_mode((theme.WIN_W, theme.WIN_H))
        self.app = loop.Application(screen, GameConfig(trace=False))

    def image(self, n=1):
        with silence():
            for _ in range(n):
                self.app.update(1 / 60)
                self.app.render()

    def test_sans_argument_le_menu_s_ouvre(self):
        self.assertEqual(self.app.state, loop.SCREEN_MENU)
        self.image()

    def test_jouer_ia_fige_avec_le_meilleur_modele(self):
        touche(self.app, pygame.K_RETURN)
        self.assertEqual(self.app.state, loop.SCREEN_LOBBY)
        self.assertEqual(self.app.config.model, self.grand)
        touche(self.app, pygame.K_RETURN)
        with silence():
            self.image(5)
        self.assertEqual(self.app.state, loop.SCREEN_GAME)
        agent = self.app.game.agent
        self.assertFalse(agent.apprend)
        self.assertEqual(agent.epsilon, 0.0)

    def test_jouer_avec_save_garde_l_apprentissage(self):
        self.app.config.save_path = "models/sortie.txt"
        touche(self.app, pygame.K_RETURN)
        self.assertTrue(self.app.config.learn)

    def test_choisir_le_modele_puis_ok(self):
        touche(self.app, pygame.K_RETURN)       # JOUER
        touche(self.app, pygame.K_DOWN)         # MODELE
        touche(self.app, pygame.K_RETURN)       # ouvre le choix
        self.assertEqual(self.app.state, loop.SCREEN_PICKER)
        self.image()
        touche(self.app, pygame.K_UP)           # petit (moins entraine)
        touche(self.app, pygame.K_RETURN)       # OK
        self.assertEqual(self.app.state, loop.SCREEN_LOBBY)
        self.assertEqual(self.app.config.model, self.petit)

    def test_clic_sur_ok(self):
        touche(self.app, pygame.K_RETURN)
        touche(self.app, pygame.K_DOWN)
        touche(self.app, pygame.K_RETURN)
        self.image()
        self.app.handle_event(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1,
            pos=self.app.picker.ok_rect.center))
        self.assertEqual(self.app.state, loop.SCREEN_LOBBY)

    def test_echap_remonte_jusqu_a_quitter(self):
        touche(self.app, pygame.K_RETURN)
        touche(self.app, pygame.K_RETURN)
        self.image()
        with silence():
            touche(self.app, pygame.K_ESCAPE)
        self.assertEqual(self.app.state, loop.SCREEN_LOBBY)
        touche(self.app, pygame.K_ESCAPE)
        self.assertEqual(self.app.state, loop.SCREEN_MENU)
        touche(self.app, pygame.K_ESCAPE)
        self.assertFalse(self.app.running)

    def test_creer_un_modele_et_l_entrainer(self):
        touche(self.app, pygame.K_DOWN)
        touche(self.app, pygame.K_RETURN)
        self.assertEqual(self.app.state, loop.SCREEN_TRAINING)
        touche(self.app, pygame.K_n)
        self.app.handle_event(pygame.event.Event(pygame.TEXTINPUT,
                                                 text="neuf"))
        touche(self.app, pygame.K_DOWN, 6)          # PARTIES A JOUER
        touche(self.app, pygame.K_LEFT, 10)         # au minimum : 10
        touche(self.app, pygame.K_RETURN)
        self.assertEqual(self.app.training.vue, "en_cours")
        for _ in range(500):
            self.image()
            if self.app.training.vue != "en_cours":
                break
        self.assertEqual(modele.charger("models/neuf.txt").parties, 10)
        self.assertIn("sauvegarde", self.app.training.message)

    def test_hyperparametres_du_nouveau_modele(self):
        """GAMMA au plus bas, EPSILON MIN au plus haut, VALEUR INITIALE
        a 0 : le modele cree les garde dans son fichier."""
        touche(self.app, pygame.K_DOWN)
        touche(self.app, pygame.K_RETURN)
        touche(self.app, pygame.K_n)
        self.app.handle_event(pygame.event.Event(pygame.TEXTINPUT,
                                                 text="regle"))
        touche(self.app, pygame.K_DOWN)             # GAMMA
        touche(self.app, pygame.K_LEFT, 30)
        touche(self.app, pygame.K_DOWN)             # EPSILON MINIMAL
        touche(self.app, pygame.K_RIGHT, 30)
        touche(self.app, pygame.K_DOWN, 2)          # VALEUR INITIALE
        touche(self.app, pygame.K_LEFT, 2)          # 1 -> 0.5 -> 0
        touche(self.app, pygame.K_DOWN, 2)          # PARTIES A JOUER
        touche(self.app, pygame.K_LEFT, 10)
        self.image()
        touche(self.app, pygame.K_RETURN)
        for _ in range(500):
            self.image()
            if self.app.training.vue != "en_cours":
                break
        agent = modele.charger("models/regle.txt")
        self.assertEqual((agent.gamma, agent.epsilon_min,
                          agent.q.valeur_initiale), (0.0, 1.0, 0.0))
        self.assertEqual(models.infos("models/regle.txt").valeur_initiale,
                         0.0)

    def test_nom_deja_pris_refuse(self):
        touche(self.app, pygame.K_DOWN)
        touche(self.app, pygame.K_RETURN)
        touche(self.app, pygame.K_n)
        self.app.handle_event(pygame.event.Event(pygame.TEXTINPUT,
                                                 text="grand"))
        touche(self.app, pygame.K_RETURN)
        self.assertEqual(self.app.training.vue, "nouveau")
        self.assertTrue(self.app.training.formulaire.message)

    def test_continuer_un_modele(self):
        touche(self.app, pygame.K_DOWN)
        touche(self.app, pygame.K_RETURN)
        touche(self.app, pygame.K_UP, 5)            # petit
        touche(self.app, pygame.K_c)
        self.assertEqual(self.app.training.vue, "continuer")
        touche(self.app, pygame.K_LEFT, 10)         # +10
        touche(self.app, pygame.K_RETURN)
        for _ in range(500):
            self.image()
            if self.app.training.vue != "en_cours":
                break
        self.assertEqual(modele.charger(self.petit).parties, 13)

    def test_fermer_pendant_l_entrainement_sauve(self):
        touche(self.app, pygame.K_DOWN)
        touche(self.app, pygame.K_RETURN)
        touche(self.app, pygame.K_n)
        self.app.handle_event(pygame.event.Event(pygame.TEXTINPUT,
                                                 text="coupe"))
        touche(self.app, pygame.K_DOWN, 7)
        touche(self.app, pygame.K_RIGHT, 20)
        touche(self.app, pygame.K_RETURN)
        self.image(2)
        self.app.fermer()
        self.assertGreater(modele.charger("models/coupe.txt").parties, 0)

    def test_evaluation_jusqu_aux_resultats_puis_rejeu(self):
        touche(self.app, pygame.K_DOWN, 2)
        touche(self.app, pygame.K_RETURN)
        self.assertEqual(self.app.state, loop.SCREEN_EVAL_SETUP)
        self.assertEqual(self.app.eval_config.model, self.grand)
        touche(self.app, pygame.K_DOWN)             # PLATEAU
        touche(self.app, pygame.K_RETURN)           # EVALUER
        self.assertEqual(self.app.state, loop.SCREEN_EVAL)
        self.assertFalse(self.app.eval_game.agent.apprend)
        self.image(3)
        with silence():
            touche(self.app, pygame.K_ESCAPE)       # arreter
        self.assertEqual(self.app.state, loop.SCREEN_RESULTS)
        self.image()
        resultats = self.app.results
        fin = resultats.index
        touche(self.app, pygame.K_LEFT)
        self.assertEqual(resultats.index, max(0, fin - 1))
        touche(self.app, pygame.K_HOME)
        self.assertEqual(resultats.index, 0)
        touche(self.app, pygame.K_END)
        self.assertEqual(resultats.index, fin)
        touche(self.app, pygame.K_ESCAPE)
        self.assertEqual(self.app.state, loop.SCREEN_MENU)


if __name__ == "__main__":
    unittest.main()
