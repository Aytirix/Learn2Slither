"""Boucle principale : enchaine le lobby et la partie."""

import random
import sys

import pygame

from .. import baselines
from ..agent.fabrique import creer_agent
from ..agent.modele import ErreurModele
from ..config import GameConfig
from ..environment import board as bd
from . import theme
from .game import Game
from .lobby import Lobby, QUIT, START
from .renderer import Renderer
from .starfield import Starfield

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

SPEED_UP_KEYS = (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS)
SPEED_DOWN_KEYS = (pygame.K_MINUS, pygame.K_KP_MINUS)

SCREEN_LOBBY = "lobby"
SCREEN_GAME = "game"


def run(configuration=None, skip_lobby=False, agent=None):
    """Ouvre la fenetre et enchaine lobby puis parties.

    Renvoie False si la sauvegarde demandee par -save a echoue.
    """
    pygame.init()
    pygame.display.set_caption("Learn2Slither — Galaxie Serpentine")
    screen = pygame.display.set_mode((theme.WIN_W, theme.WIN_H))
    clock = pygame.time.Clock()
    fonts = theme.load_fonts()

    config = configuration or GameConfig()
    starfield = Starfield(theme.WIN_W, theme.WIN_H)
    lobby = Lobby(fonts, config, starfield)
    renderer = Renderer(screen, fonts, starfield)

    pilote = PiloteAgent(config, agent)
    game = Game(config, pilote.agent) if skip_lobby else None
    state = SCREEN_GAME if skip_lobby else SCREEN_LOBBY

    running = True
    try:
        while running:
            dt = clock.tick(theme.FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif state == SCREEN_LOBBY:
                    state, game, running = _lobby_event(
                        event, lobby, config, game, running, pilote
                    )
                elif event.type == pygame.KEYDOWN:
                    state, running = _game_event(event.key, game, running)

            if state == SCREEN_LOBBY:
                lobby.update(dt)
                lobby.render(screen)
            else:
                starfield.update(dt)
                game.update(dt)
                renderer.draw(game)
            pygame.display.flip()
    except KeyboardInterrupt:
        # Ctrl+C dans le terminal : on ferme proprement, comme la croix de
        # la fenetre, pour ne pas perdre ce que l'agent a appris.
        print("\nInterruption : fermeture et sauvegarde")

    pygame.quit()
    return _terminer(game, config, pilote)


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
        return SCREEN_LOBBY, game, False
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
    if key in KEY_DIRECTIONS:
        game.queue_direction(KEY_DIRECTIONS[key])
    elif key == pygame.K_SPACE:
        if game.board.alive:
            game.paused = not game.paused
        else:
            game.restart()
    elif key == pygame.K_r:
        game.restart()
    elif key == pygame.K_n:
        game.request_step()
    elif key == pygame.K_p:
        game.toggle_step_mode()
    elif key == pygame.K_v:
        game.show_vision = not game.show_vision
    elif key == pygame.K_t:
        game.trace = not game.trace
    elif key in SPEED_UP_KEYS:
        game.change_speed(1.25)
    elif key in SPEED_DOWN_KEYS:
        game.change_speed(0.8)
