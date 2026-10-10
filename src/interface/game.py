"""Etat d'une partie : tempo, effets visuels et trace terminal."""

import random
import time
from collections import deque

from .. import config as cfg
from .. import graine as gr
from ..config import GameConfig
from ..environment import board as bd
from ..environment.rewards import recompense
from ..evaluation import Photo
from . import gfx, theme
from .board_view import FIN_HINT, cell_center
from .particles import ParticleSystem

# Vitesse MAX : on enchaine les pas sans attente, mais pas plus de ce temps
# de calcul par image, pour que la fenetre reste fluide (60 images / s, soit
# environ 16 ms par image ; on en garde pour le dessin).
BUDGET_MAX_S = 0.010

# Pas que l'on peut revoir en arriere en mode pas a pas (fleche GAUCHE).
HISTORIQUE_MAX = 1000

FIN_HINT_SUIVANTE = "[N] partie suivante"


class Game:
    """Relie le plateau, les effets et le rythme d'affichage."""

    def __init__(self, configuration=None, agent=None):
        self.config = configuration or GameConfig()
        self.agent = agent
        # Generateur des effets (particules, secousse) seulement : il tire
        # au rythme des images, il ne doit pas deplacer les pommes.
        self.rng = random.Random()
        self.board = bd.Board(size=self.config.size, rng=random.Random())
        # Une graine par partie (src/graine.py) : chaque partie se rejoue
        # seule avec -seed <graine affichee dans le panneau>.
        self.graine_depart = gr.graine_de_depart(self.config.seed)
        self.numero_partie = 1
        gr.nouvelle_partie(self.board, self.agent, self.graine)
        self.particles = ParticleSystem(self.rng)
        self.speed = self.config.speed
        self.paused = False
        self.show_vision = True
        self.trace = self.config.trace
        self.time_s = 0.0
        self.shake = (0, 0)
        self.shake_amp = 0.0
        self.best_length = len(self.board.snake)
        # Graine de la partie qui detient le record : -seed <graine> la
        # rejoue (src/graine.py). None si cette partie n'est pas rejouable.
        self.graine_record = self.graine if self.graine_rejouable else None
        self.prev_snake = list(self.board.snake)
        self.acc = 0.0
        self.pending = []
        self.step_by_step = self.config.step_by_step
        self.steps_left = 0
        self.session = 1
        self.sessions = self.config.sessions
        self.death_timer = 0.0
        self.agent_en_partie = False
        # Photos des derniers pas ; historique[-1] est toujours le present.
        # `recul` = combien de pas en arriere on regarde (0 = le present).
        self.historique = deque(maxlen=HISTORIQUE_MAX)
        self.recul = 0
        self._photographier()
        self._debut_partie_agent()

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

    @property
    def fin_hint(self):
        """Texte de l'ecran de fin."""
        if not self.step_by_step:
            return FIN_HINT
        texte = (FIN_HINT_SUIVANTE if self.session < self.sessions
                 else FIN_HINT)
        return self.avec_revoir(texte)

    def avec_revoir(self, texte):
        """Ajoute [GAUCHE] revoir quand la fleche sert a reculer."""
        if self.step_by_step and not self.manual:
            return texte + "  ·  [GAUCHE] revoir"
        return texte

    @property
    def pause_fin(self):
        """Secondes d'ecran de fin avant la session suivante."""
        return 1.2

    @property
    def graine(self):
        """Graine de la partie en cours : -seed <graine> la rejoue."""
        return gr.graine_partie(self.graine_depart, self.numero_partie)

    @property
    def graine_rejouable(self):
        """Vrai si -seed <graine> rejoue vraiment la partie.

        Il faut un agent qui n'apprend pas : un agent qui apprend change
        de table Q d'une partie a l'autre, et au clavier les coups viennent
        du joueur. Dans ces deux cas, la graine n'est pas affichee.
        """
        return self.agent_pilote and not getattr(self.agent, "apprend",
                                                 False)

    # -- geometrie ----------------------------------------------------
    @property
    def vitesse_max(self):
        return self.speed == cfg.VITESSE_MAX

    @property
    def interval(self):
        """Secondes entre deux pas ; 0 a la vitesse MAX."""
        return 0.0 if self.vitesse_max else 1.0 / self.speed

    def progress(self):
        """Avancement 0->1 entre deux cases, adouci."""
        if not self.board.alive or self.interval <= 0:
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
        """N : joue un pas, et passe en mode pas a pas s'il ne l'etait pas.

        Hors mode pas a pas, N passait inapercu (le serpent avancait deja
        tout seul) : appuyer sur N fige donc le jeu et avance d'un pas.
        """
        if not self.step_by_step:
            self.toggle_step_mode()
        self.steps_left += 1

    def toggle_step_mode(self):
        self.step_by_step = not self.step_by_step
        self.steps_left = 0
        if not self.step_by_step:
            # On reprend le jeu la ou il en etait, pas dans le passe.
            self.revenir_au_present()

    # -- retour en arriere (mode pas a pas) ---------------------------
    # On ne fait que MONTRER le passe : la partie, le hasard des pommes et
    # ce que l'agent a appris ne sont jamais rejoues ni annules. Revenir en
    # avant reaffiche les photos jusqu'au present ; c'est seulement depuis
    # le present qu'un nouveau pas est vraiment joue.
    def pas_suivant(self):
        """N ou DROITE : avance dans l'historique, sinon joue un pas."""
        if self.recul == 0:
            self.request_step()
            return
        self.recul -= 1
        self._montrer(self.historique[-1 - self.recul])

    def pas_precedent(self):
        """GAUCHE : montre le pas d'avant (en mode pas a pas seulement)."""
        if not self.step_by_step:
            return
        if self.recul + 1 >= len(self.historique):
            return
        self.recul += 1
        self.steps_left = 0
        self._montrer(self.historique[-1 - self.recul])

    def revenir_au_present(self):
        if self.recul:
            self.recul = 0
            self._montrer(self.historique[-1])

    def _montrer(self, photo):
        """Affiche une photo, avec l'animation depuis ce qui etait montre."""
        self.prev_snake = list(self.board.snake)
        photo.restaurer(self.board)
        self.acc = 0.0

    def _photographier(self):
        self.historique.append(Photo(self.board))

    def next_session(self):
        """Passe a la session suivante si le quota n'est pas atteint."""
        if self.session >= self.sessions:
            return False
        self.session += 1
        self.restart()
        return True

    def restart(self):
        """Nouvelle partie, effets remis a zero."""
        # Une partie abandonnee en cours (touche R) est quand meme apprise.
        self.revenir_au_present()
        self._fin_partie_agent()
        self.numero_partie += 1
        gr.nouvelle_partie(self.board, self.agent, self.graine)
        self.recul = 0
        self.historique.clear()
        self._photographier()
        self.particles.clear()
        self.prev_snake = list(self.board.snake)
        self.pending.clear()
        self.acc = 0.0
        self.steps_left = 0
        self.death_timer = 0.0
        self.shake_amp = 0.0
        self.best_length = max(self.best_length, len(self.board.snake))
        self._debut_partie_agent()

    # -- agent --------------------------------------------------------
    @property
    def agent_pilote(self):
        """Vrai si c'est l'agent, et non le clavier, qui dirige."""
        return self.agent is not None and not self.manual

    def _debut_partie_agent(self):
        debut = getattr(self.agent, "debut_partie", None)
        if self.agent_pilote and debut is not None:
            debut(self.board.direction)
            self.agent_en_partie = True

    def _fin_partie_agent(self):
        """Fait apprendre la partie a l'agent, une seule fois par partie."""
        fin = getattr(self.agent, "fin_partie", None)
        if self.agent_en_partie and fin is not None:
            fin()
        self.agent_en_partie = False

    def close(self):
        """A la fermeture : ne pas perdre la partie en cours."""
        self._fin_partie_agent()

    def change_speed(self, delta):
        """+ / - : cran suivant ou precedent de cfg.SPEEDS, comme au lobby."""
        self.speed = cfg.valeur_voisine(cfg.SPEEDS, self.speed, delta)

    # -- simulation ---------------------------------------------------
    def update(self, dt):
        """Avance le temps, declenche les pas de jeu et les effets."""
        self.time_s += dt
        self.particles.update(dt)
        self._update_shake(dt)

        if self.recul:
            # On regarde le passe : rien n'est joue, on finit l'animation.
            self.acc = min(self.acc + dt, self.interval)
            return
        if not self.board.alive:
            self._apres_la_fin(dt)
            return
        if self.paused:
            return
        if self.step_by_step and self.steps_left <= 0:
            # En attente du prochain N : on laisse quand meme l'animation
            # du dernier pas aller a son terme. Sans cela, `acc` restait a 0
            # juste apres le pas : la tete etait deja sur sa nouvelle case
            # mais le corps, interpole, restait dessine a l'ancienne place
            # jusqu'au N suivant.
            self.acc = min(self.acc + dt, self.interval)
            return

        if self.vitesse_max:
            self._avancer_au_maximum()
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

    def _apres_la_fin(self, dt):
        """Ecran de fin, puis partie suivante.

        En mode pas a pas, on attend N ou DROITE : on peut ainsi revoir
        les derniers pas (GAUCHE) avant que la partie suivante ne parte.
        """
        if self.step_by_step:
            if self.steps_left > 0:
                self.steps_left = 0
                self.next_session()
            return
        self.death_timer += dt
        if self.death_timer > self.pause_fin:
            self.next_session()

    def _avancer_au_maximum(self):
        """Vitesse MAX : autant de pas que le budget de l'image le permet."""
        fin = time.perf_counter() + BUDGET_MAX_S
        while self.board.alive and time.perf_counter() < fin:
            if self.step_by_step:
                if self.steps_left <= 0:
                    break
                self.steps_left -= 1
            self._tick()
        self.acc = 0.0

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
        vision = self.board.vision_chars()
        direction = self._next_direction(vision)
        self.prev_snake = list(self.board.snake)
        event = self.board.step(direction)
        self._photographier()
        self._apprendre(vision, direction, event)
        self._on_event(event, direction)

    def _apprendre(self, vision, direction, event):
        """Meme contrat que la boucle sans affichage (src/session.py)."""
        if not self.agent_pilote:
            return
        learn = getattr(self.agent, "learn", None)
        if learn is not None:
            # board.dead et non `not alive` : une troncature bootstrappe.
            apres = (vision if self.board.dead
                     else self.board.vision_chars())
            learn(vision, direction, recompense(event), apres,
                  self.board.dead)
        if not self.board.alive:
            self._fin_partie_agent()

    def _next_direction(self, vision):
        """Direction du prochain pas : agent, file clavier, ou statu quo."""
        if self.agent_pilote:
            return self.agent.choose(vision)
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

        if self.board.max_length > self.best_length:
            self.best_length = self.board.max_length
            self.graine_record = (self.board.graine if self.graine_rejouable
                                  else None)
        if self.trace:
            self._print_state(direction, event)
        if self.board.end_cause is not None:
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
