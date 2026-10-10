"""Boucle principale : menu, lobby, partie, entrainement, evaluation."""

import random
import sys

import pygame

from .. import baselines
from ..agent.fabrique import creer_agent
from ..agent.modele import ErreurModele
from ..config import GameConfig
from ..environment import board as bd
from .. import models
from . import theme
from .evaluation_view import EvaluationGame, ResultsScreen
from .evaluation_view import RETOUR_MENU as RESULTS_RETOUR
from .game import Game
from .lobby import CHOISIR_MODELE, Lobby, QUIT, START
from .menu import ENTRAINEMENT, EVALUATION, JOUER, QUITTER, MainMenu
from .model_picker import ANNULER as PICKER_ANNULER
from .model_picker import OK as PICKER_OK
from .model_picker import ModelPicker
from .renderer import Renderer
from .starfield import Starfield
from .training_view import RETOUR_MENU as TRAINING_RETOUR
from .training_view import TrainingScreen

KEY_DIRECTIONS = {
    pygame.K_UP: bd.UP,
    pygame.K_z: bd.UP,
    pygame.K_w: bd.UP,
    pygame.K_DOWN: bd.DOWN,
    pygame.K_s: bd.DOWN,
    pygame.K_LEFT: bd.LEFT,
    pygame.K_q: bd.LEFT,
    pygame.K_a: bd.LEFT,
    pygame.K_RIGHT: bd.RIGHT,
    pygame.K_d: bd.RIGHT,
}

FLECHES_PAS = (pygame.K_LEFT, pygame.K_RIGHT)

SPEED_UP_KEYS = (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS)
SPEED_DOWN_KEYS = (pygame.K_MINUS, pygame.K_KP_MINUS)

SCREEN_MENU = "menu"
SCREEN_LOBBY = "lobby"
SCREEN_PICKER = "picker"
SCREEN_GAME = "game"
SCREEN_TRAINING = "training"
SCREEN_EVAL_SETUP = "eval_setup"
SCREEN_EVAL = "eval"
SCREEN_RESULTS = "results"

# Ecrans ou une touche maintenue se repete (listes, reglages, rejeu). Pas en
# partie : maintenir ESPACE y ferait clignoter la pause.
REPETITION = (250, 40)
ECRANS_SANS_REPETITION = (SCREEN_GAME, SCREEN_EVAL)


def run(configuration=None, skip_lobby=False, agent=None):
    """Ouvre la fenetre : menu principal, ou directement la partie.

    Renvoie False si la sauvegarde demandee par -save a echoue.
    """
    pygame.init()
    pygame.display.set_caption("Learn2Slither — Galaxie Serpentine")
    screen = pygame.display.set_mode((theme.WIN_W, theme.WIN_H))
    clock = pygame.time.Clock()
    app = Application(screen, configuration or GameConfig(), skip_lobby,
                      agent)
    try:
        while app.running:
            dt = clock.tick(theme.FPS) / 1000.0
            app.repetition()
            for event in pygame.event.get():
                app.handle_event(event)
            app.update(dt)
            app.render()
            pygame.display.flip()
    except KeyboardInterrupt:
        # Ctrl+C dans le terminal : on ferme proprement, comme la croix de
        # la fenetre, pour ne pas perdre ce que l'agent a appris.
        print("\nInterruption : fermeture et sauvegarde")

    app.fermer()
    pygame.quit()
    return _terminer(app.game, app.config, app.pilote)


class Application:
    """Tous les ecrans de la fenetre et le passage de l'un a l'autre.

        MENU --JOUER--------> LOBBY --LANCER--> GAME
          |                     `--MODELE--> PICKER (retour au LOBBY)
          |--ENTRAINEMENT-----> TRAINING
          `--EVALUATION-------> EVAL_SETUP --EVALUER--> EVAL --> RESULTS
                                  `--MODELE--> PICKER (retour a EVAL_SETUP)

    ECHAP remonte d'un cran ; depuis le menu, il quitte.
    """

    def __init__(self, screen, config, skip_lobby=False, agent=None):
        self.screen = screen
        self.config = config
        fonts = theme.load_fonts()
        self.fonts = fonts
        self.starfield = Starfield(theme.WIN_W, theme.WIN_H)
        self.renderer = Renderer(screen, fonts, self.starfield)
        self.menu = MainMenu(fonts, self.starfield)
        self.lobby = Lobby(fonts, config, self.starfield)
        self.picker = ModelPicker(fonts, self.starfield)
        self.picker_config = config
        self.picker_retour = SCREEN_LOBBY
        self.training = TrainingScreen(fonts, self.starfield)
        self.eval_config = GameConfig(learn=False, trace=False)
        self.eval_setup = Lobby(
            fonts, self.eval_config, self.starfield, avec_pilote=False,
            sous_titre="EVALUATION  ·  PARTIES EN BOUCLE JUSQU'A ATTEINDRE "
                       "L'OBJECTIF",
            bouton="EVALUER", avec_objectif=True)
        self.results = None
        self.eval_game = None

        self.pilote = PiloteAgent(config, agent)
        self.game = Game(config, self.pilote.agent) if skip_lobby else None
        self.state = SCREEN_GAME if skip_lobby else SCREEN_MENU
        self.running = True
        self._repetition = None

    def repetition(self):
        """Active la repetition des touches hors partie."""
        voulue = self.state not in ECRANS_SANS_REPETITION
        if voulue != self._repetition:
            pygame.key.set_repeat(*(REPETITION if voulue else (0, 0)))
            self._repetition = voulue

    # -- evenements ---------------------------------------------------
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        handler = getattr(self, "_event_" + self.state)
        handler(event)

    def _event_menu(self, event):
        choix = self.menu.handle_event(event)
        if choix == QUITTER:
            self.running = False
        elif choix == JOUER:
            self.ouvrir_jouer()
        elif choix == ENTRAINEMENT:
            self.training.ouvrir()
            self.state = SCREEN_TRAINING
        elif choix == EVALUATION:
            if self.eval_config.model is None:
                self.eval_config.model = models.meilleur_modele()
            self.state = SCREEN_EVAL_SETUP

    def ouvrir_jouer(self):
        """JOUER : l'IA joue au mieux, avec un agent fige.

        Sauf si la ligne de commande a demande -save : l'agent qu'elle a
        lance doit alors continuer d'apprendre, sinon on sauvegarderait un
        agent fige a la place de ce qu'il a appris.
        """
        if not self.config.save_path:
            self.config.learn = False
        if self.config.model is None:
            self.config.model = models.meilleur_modele()
        self.state = SCREEN_LOBBY

    def _event_lobby(self, event):
        self.state, self.game, running = _lobby_event(
            event, self.lobby, self.config, self.game, self.running,
            self.pilote)
        if not running:
            self.state = SCREEN_MENU
        elif self.state == SCREEN_PICKER:
            self._ouvrir_picker(self.config, SCREEN_LOBBY)

    def _ouvrir_picker(self, config, retour):
        self.picker.ouvrir(config.model)
        self.picker_config = config
        self.picker_retour = retour
        self.state = SCREEN_PICKER

    def _event_picker(self, event):
        action = self.picker.handle_event(event)
        if action == PICKER_OK:
            self.picker_config.model = self.picker.selection
        if action in (PICKER_OK, PICKER_ANNULER):
            self.state = self.picker_retour

    def _event_game(self, event):
        if event.type == pygame.KEYDOWN:
            self.state, _ = _game_event(event.key, self.game, self.running)

    def _event_training(self, event):
        if self.training.handle_event(event) == TRAINING_RETOUR:
            self.state = SCREEN_MENU

    def _event_eval_setup(self, event):
        action = None
        if event.type == pygame.KEYDOWN:
            action = self.eval_setup.handle_key(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = self.eval_setup.handle_click(event.pos)
        if action == QUIT:
            self.state = SCREEN_MENU
        elif action == CHOISIR_MODELE:
            self._ouvrir_picker(self.eval_config, SCREEN_EVAL_SETUP)
        elif action == START:
            self._lancer_evaluation()

    def _lancer_evaluation(self):
        agent = agent_pour(self.eval_config)
        if agent is None:
            self.eval_setup.formulaire.message = \
                "modele illisible : voir le terminal"
            return
        self.eval_setup.formulaire.message = ""
        self.eval_game = EvaluationGame(self.eval_config, agent,
                                        seuil=self.eval_config.objectif)
        self.state = SCREEN_EVAL

    def _event_eval(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self._resultats()
        else:
            handle_key(self.eval_game, event.key)

    def _resultats(self):
        self.results = ResultsScreen(
            self.fonts, self.starfield, self.eval_game.bilan,
            models.label_for(self.eval_config.model),
            self.eval_config.size)
        self.eval_game = None
        self.state = SCREEN_RESULTS

    def _event_results(self, event):
        if self.results.handle_event(event) == RESULTS_RETOUR:
            self.results = None
            self.state = SCREEN_MENU

    # -- boucle -------------------------------------------------------
    def update(self, dt):
        if self.state == SCREEN_GAME:
            self.starfield.update(dt)
            self.game.update(dt)
        elif self.state == SCREEN_EVAL:
            self.starfield.update(dt)
            self.eval_game.update(dt)
            if self.eval_game.fini:
                self._resultats()
        else:
            self._ecran().update(dt)

    def render(self):
        if self.state == SCREEN_GAME:
            self.renderer.draw(self.game)
        elif self.state == SCREEN_EVAL:
            self.renderer.draw(self.eval_game)
        else:
            self._ecran().render(self.screen)

    def _ecran(self):
        return {
            SCREEN_MENU: self.menu,
            SCREEN_LOBBY: self.lobby,
            SCREEN_PICKER: self.picker,
            SCREEN_TRAINING: self.training,
            SCREEN_EVAL_SETUP: self.eval_setup,
            SCREEN_RESULTS: self.results,
        }[self.state]

    def fermer(self):
        """Fermeture de la fenetre : un entrainement en cours est sauve."""
        self.training.arreter()


def _terminer(game, config, pilote):
    """Fin du programme : apprendre la partie en cours, puis sauvegarder.

    On sauvegarde l'agent du pilote, et non celui de la derniere partie :
    si la derniere partie etait jouee au clavier, c'est quand meme l'agent
    entraine plus tot qu'on veut garder.
    """
    if game is not None:
        game.close()
    if not config.save_path:
        return True
    save = getattr(pilote.agent, "save", None)
    if save is None:
        print("Aucun agent a sauvegarder : {} n'a pas ete ecrit".format(
            config.save_path))
        return True
    try:
        save(config.save_path)
    except ErreurModele as erreur:
        print("Erreur : {}".format(erreur), file=sys.stderr)
        return False
    print("Sauvegarde de l'etat d'apprentissage dans {}".format(
        config.save_path))
    return True


def _cle_agent(config):
    """Reglages qui definissent l'agent : s'ils changent, on en recree un."""
    return (config.model, config.learn, config.baseline)


class PiloteAgent:
    """Garde le MEME agent d'une partie a l'autre.

    Sans lui, chaque retour au lobby puis nouveau lancement recreerait un
    agent depuis le fichier, et tout ce qu'il a appris entre-temps serait
    perdu. On ne recree l'agent que si l'on a change, dans le lobby, un
    reglage qui le definit (le modele choisi, par exemple).
    """

    def __init__(self, config, agent=None):
        self.agent = agent
        self.cle = _cle_agent(config) if agent is not None else None

    def pour(self, config):
        """Agent pour une nouvelle partie ; None si le chargement echoue."""
        cle = _cle_agent(config)
        if self.agent is not None and cle == self.cle:
            return self.agent
        nouvel = agent_pour(config)
        if nouvel is not None:
            self.agent, self.cle = nouvel, cle
        return nouvel


def agent_pour(config):
    """Agent du pilote IA, cree au moment ou la partie demarre.

    Cree ici et non au lancement du programme, parce que le lobby permet de
    changer de modele entre-temps. Renvoie None si le modele choisi ne peut
    pas etre charge : le message est affiche et on reste dans le lobby.
    """
    if not config.ai_driven:
        return None
    rng = random.Random(baselines.derive_seed(config.seed))
    try:
        return creer_agent(config, rng)
    except ErreurModele as erreur:
        print("Erreur : {}".format(erreur), file=sys.stderr)
        return None


def _lobby_event(event, lobby, config, game, running, pilote):
    """Traite un evenement du lobby et retourne le nouvel etat."""
    action = None
    if event.type == pygame.KEYDOWN:
        action = lobby.handle_key(event.key)
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        action = lobby.handle_click(event.pos)

    if action == QUIT:
        # Le lobby se ferme : l'appelant revient au menu principal.
        return SCREEN_LOBBY, game, False
    if action == CHOISIR_MODELE:
        return SCREEN_PICKER, game, running
    if action == START:
        if not config.ai_driven:
            return SCREEN_GAME, Game(config, None), running
        agent = pilote.pour(config)
        if agent is None:
            return SCREEN_LOBBY, game, running
        return SCREEN_GAME, Game(config, agent), running
    return SCREEN_LOBBY, game, running


def _game_event(key, game, running):
    """Traite une touche en partie ; ECHAP ramene au lobby."""
    if key == pygame.K_ESCAPE:
        # Retour au lobby : la partie en cours est apprise, pas jetee.
        game.close()
        return SCREEN_LOBBY, running
    handle_key(game, key)
    return SCREEN_GAME, running


def handle_key(game, key):
    """Applique une touche de jeu a la partie en cours."""
    if game.step_by_step and not game.manual and key in FLECHES_PAS:
        # Pas a pas avec l'IA : les fleches ne dirigent rien, elles font
        # reculer ou avancer d'un pas. Au clavier, elles dirigent toujours.
        if key == pygame.K_LEFT:
            game.pas_precedent()
        else:
            game.pas_suivant()
    elif key in KEY_DIRECTIONS:
        game.queue_direction(KEY_DIRECTIONS[key])
    elif key == pygame.K_SPACE:
        if game.board.alive:
            game.paused = not game.paused
        else:
            game.restart()
    elif key == pygame.K_r:
        game.restart()
    elif key == pygame.K_n:
        game.pas_suivant()
    elif key == pygame.K_p:
        game.toggle_step_mode()
    elif key == pygame.K_v:
        game.show_vision = not game.show_vision
    elif key == pygame.K_t:
        game.trace = not game.trace
    elif key in SPEED_UP_KEYS:
        game.change_speed(1)
    elif key in SPEED_DOWN_KEYS:
        game.change_speed(-1)
