"""Etat d'une partie : tempo, effets visuels et trace terminal."""

import random

from ..config import GameConfig
from ..environment import board as bd
from . import gfx, theme
from .board_view import cell_center
from .particles import ParticleSystem

MIN_SPEED = 1.0
MAX_SPEED = 30.0


class Game:
    """Relie le plateau, les effets et le rythme d'affichage."""

    def __init__(self, configuration=None, agent=None):
        self.config = configuration or GameConfig()
        self.agent = agent
        self.rng = random.Random(self.config.seed)
        self.board = bd.Board(size=self.config.size, rng=self.rng)
        self.particles = ParticleSystem(self.rng)
        self.speed = self.config.speed
        self.paused = False
        self.show_vision = True
        self.trace = self.config.trace
        self.time_s = 0.0
        self.shake = (0, 0)
        self.shake_amp = 0.0
        self.best_length = len(self.board.snake)
        self.prev_snake = list(self.board.snake)
        self.acc = 0.0
        self.pending = []
        self.step_by_step = self.config.step_by_step
        self.steps_left = 0
        self.session = 1
        self.sessions = self.config.sessions
        self.death_timer = 0.0

    @property
    def manual(self):
        """Vrai si le joueur dirige le serpent au clavier."""
        return not self.config.ai_driven

    @property
    def pilot_label(self):
        """Libelle du pilote, affiche dans le panneau."""
        if not self.config.ai_driven:
            return "PILOTAGE MANUEL"
        if self.agent is None:
            return "PILOTE IA  ·  AGENT NON BRANCHE"
        return "PILOTE IA"

    # -- geometrie ----------------------------------------------------
    @property
    def interval(self):
        return 1.0 / self.speed

    def progress(self):
        """Avancement 0->1 entre deux cases, adouci."""
        if not self.board.alive:
            return 1.0
        return gfx.ease_out_cubic(min(1.0, self.acc / self.interval))

    def snake_points(self):
        """Positions pixel interpolees, de la tete vers la queue."""
        t = self.progress()
        size = self.board.size
        prev = self.prev_snake or self.board.snake
        points = []
        for i, cell in enumerate(self.board.snake):
            old = prev[i] if i < len(prev) else prev[-1]
            a = cell_center(size, old)
            b = cell_center(size, cell)
            points.append((gfx.lerp(a[0], b[0], t), gfx.lerp(a[1], b[1], t)))
        return points

    def head_pixel(self):
        return cell_center(self.board.size, self.board.snake[0])

    # -- commandes ----------------------------------------------------
    def queue_direction(self, direction):
        """Ignore les demi-tours immediats, met en file les virages.

        Sans effet lorsque la partie est pilotee par l'IA.
        """
        if not self.manual:
            return
        last = self.pending[-1] if self.pending else self.board.direction
        if direction == last:
            return
        if (direction[0] + last[0], direction[1] + last[1]) == (0, 0):
            return
        if len(self.pending) < 2:
            self.pending.append(direction)

    def request_step(self):
        """Autorise un pas supplementaire en mode pas a pas."""
        self.steps_left += 1

    def toggle_step_mode(self):
        self.step_by_step = not self.step_by_step
        self.steps_left = 0

    def next_session(self):
        """Passe a la session suivante si le quota n'est pas atteint."""
        if self.session >= self.sessions:
            return False
        self.session += 1
        self.restart()
        return True

    def restart(self):
        """Nouvelle partie, effets remis a zero."""
        self.board.reset()
        self.particles.clear()
        self.prev_snake = list(self.board.snake)
        self.pending.clear()
        self.acc = 0.0
        self.steps_left = 0
        self.death_timer = 0.0
        self.shake_amp = 0.0
        self.best_length = max(self.best_length, len(self.board.snake))

    def change_speed(self, factor):
        self.speed = max(MIN_SPEED, min(MAX_SPEED, self.speed * factor))

    # -- simulation ---------------------------------------------------
    def update(self, dt):
        """Avance le temps, declenche les pas de jeu et les effets."""
        self.time_s += dt
        self.particles.update(dt)
        self._update_shake(dt)

        if not self.board.alive:
            self.death_timer += dt
            if self.death_timer > 1.2:
                self.next_session()
            return
        if self.paused:
            return
        if self.step_by_step and self.steps_left <= 0:
            return

        self.acc += dt
        while self.acc >= self.interval:
            self.acc -= self.interval
            if self.step_by_step:
                if self.steps_left <= 0:
                    self.acc = 0.0
                    break
                self.steps_left -= 1
            self._tick()
            if not self.board.alive:
                self.acc = 0.0
                break

        if self.board.alive and self.rng.random() < dt * 30:
            self.particles.trail(self.head_pixel(), theme.SNAKE_HEAD, 1)

    def _update_shake(self, dt):
        self.shake_amp *= 0.86 ** (dt * 60)
        if self.shake_amp < 0.4:
            self.shake_amp = 0.0
            self.shake = (0, 0)
        else:
            self.shake = (
                self.rng.uniform(-self.shake_amp, self.shake_amp),
                self.rng.uniform(-self.shake_amp, self.shake_amp),
            )

    def _tick(self):
        direction = self._next_direction()
        self.prev_snake = list(self.board.snake)
        event = self.board.step(direction)
        self._on_event(event, direction)

    def _next_direction(self):
        """Direction du prochain pas : agent, file clavier, ou statu quo."""
        if self.agent is not None and not self.manual:
            return self.agent.choose(self.board.vision_chars())
        if self.pending:
            return self.pending.pop(0)
        return self.board.direction

    def _on_event(self, event, direction):
        if self.board.snake:
            head = self.head_pixel()
        else:
            head = (theme.BOARD_PX / 2, theme.BOARD_PX / 2)

        if event == bd.GREEN:
            self.particles.burst(head, theme.GREEN_APPLE, 30, 210)
            self.shake_amp = max(self.shake_amp, 3.0)
        elif event == bd.RED:
            self.particles.burst(head, theme.RED_APPLE, 26, 190)
            self.shake_amp = max(self.shake_amp, 6.0)
        elif event in bd.DEATH_EVENTS:
            self.particles.burst(head, theme.RED_APPLE, 70, 320, 5.0, 0.9)
            self.particles.burst(head, theme.SNAKE_HEAD, 40, 240, 4.0, 0.7)
            self.shake_amp = 16.0

        self.best_length = max(self.best_length, self.board.max_length)
        if self.trace:
            self._print_state(direction, event)
        if event in bd.DEATH_EVENTS:
            print(
                "Fin de la partie, longueur maximale = {}, "
                "duree maximale = {}".format(
                    self.board.max_length, self.board.steps
                )
            )

    def _print_state(self, direction, event):
        for line in self.board.vision_lines():
            print(line)
        print("Action : {}  (evenement : {})\n".format(
            bd.ACTION_NAMES.get(direction, "?"), event
        ))
