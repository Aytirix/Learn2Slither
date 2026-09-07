"""Boucle principale : enchaine le lobby et la partie."""

import pygame

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
    """Ouvre la fenetre et enchaine lobby puis parties."""
    pygame.init()
    pygame.display.set_caption("Learn2Slither — Galaxie Serpentine")
    screen = pygame.display.set_mode((theme.WIN_W, theme.WIN_H))
    clock = pygame.time.Clock()
    fonts = theme.load_fonts()

    config = configuration or GameConfig()
    starfield = Starfield(theme.WIN_W, theme.WIN_H)
    lobby = Lobby(fonts, config, starfield)
    renderer = Renderer(screen, fonts, starfield)

    game = Game(config, agent) if skip_lobby else None
    state = SCREEN_GAME if skip_lobby else SCREEN_LOBBY

    running = True
    while running:
        dt = clock.tick(theme.FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif state == SCREEN_LOBBY:
                state, game, running = _lobby_event(
                    event, lobby, config, game, running, agent
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

    pygame.quit()


def _lobby_event(event, lobby, config, game, running, agent=None):
    """Traite un evenement du lobby et retourne le nouvel etat."""
    action = None
    if event.type == pygame.KEYDOWN:
        action = lobby.handle_key(event.key)
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        action = lobby.handle_click(event.pos)

    if action == QUIT:
        return SCREEN_LOBBY, game, False
    if action == START:
        return SCREEN_GAME, Game(config, agent), running
    return SCREEN_LOBBY, game, running


def _game_event(key, game, running):
    """Traite une touche en partie ; ECHAP ramene au lobby."""
    if key == pygame.K_ESCAPE:
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
