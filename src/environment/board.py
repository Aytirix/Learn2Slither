"""Environnement du serpent : plateau, pommes, collisions et vision."""

import random

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
DIRECTIONS = (UP, LEFT, DOWN, RIGHT)

ACTION_NAMES = {
    UP: "HAUT",
    LEFT: "GAUCHE",
    DOWN: "BAS",
    RIGHT: "DROITE",
}

MOVE = "move"
GREEN = "green"
RED = "red"
WALL = "wall"
BODY = "body"
STARVE = "starve"
TIMEOUT = "timeout"

# Vrais terminaux du MDP : il n'y a pas d'apres, l'agent ne bootstrappe pas.
DEATH_EVENTS = (WALL, BODY, STARVE)
# Causes de fin de partie, troncature comprise. Affichage et boucles de jeu.
END_CAUSES = DEATH_EVENTS + (TIMEOUT,)

# Libelles des causes de fin. Source unique : l'affichage et les statistiques
# lisent cette table, personne ne la redefinit.
END_CAUSE_LABELS = {
    WALL: "collision avec un mur",
    BODY: "collision avec la queue",
    STARVE: "longueur nulle",
    TIMEOUT: "trop de pas sans pomme",
}

# Pas sans pomme toleres avant troncature, par case du plateau.
#
# Proportionnel a l'AIRE et non a la longueur du serpent : c'est l'aire qui
# donne le temps de recherche, puisque le serpent ne detecte une pomme que si
# elle partage sa ligne ou sa colonne.
#
# Mesure : 300 parties par cellule, graine fixe, agent aleatoire ecartant les
# directions immediatement mortelles. Pourcentage de parties tronquees :
#
#     regle              10x10     20x20     30x30
#     4 x aire             2 %       5 %       6 %
#     100 x longueur      14 %      76 %      97 %
#     300 (constante)      8 %      86 %      98 %
#
# Une limite qui ignore la taille transforme le comportement normal en
# troncature des que le plateau grandit. Celle-ci garde un taux stable.
IDLE_FACTOR = 4

# Longueur du serpent au depart, imposee par le sujet.
SNAKE_LENGTH = 3

WALL_CHAR = "W"
HEAD_CHAR = "H"
BODY_CHAR = "S"
GREEN_CHAR = "G"
RED_CHAR = "R"
EMPTY_CHAR = "0"


class Board:
    """Plateau de jeu conforme au sujet : 10x10, 2 pommes vertes, 1 rouge."""

    def __init__(self, size=10, greens=2, reds=1, rng=None,
                 idle_factor=IDLE_FACTOR):
        # Sous 3 cases de cote, _spawn_snake ne trouverait jamais 3 cases
        # alignees et tournerait indefiniment.
        if size < SNAKE_LENGTH:
            raise ValueError(
                "taille de plateau trop petite : {}, minimum {}".format(
                    size, SNAKE_LENGTH
                )
            )
        self.size = size
        self.n_greens = greens
        self.n_reds = reds
        self.rng = rng or random.Random()
        # Un facteur nul ou negatif tronquerait des le premier pas.
        self.idle_factor = max(1, idle_factor)
        self.reset()

    # -- cycle de vie -------------------------------------------------
    def reset(self, graine=None):
        """Replace serpent et pommes, remet les compteurs a zero.

        Avec `graine`, le generateur est d'abord reseme : la partie ne
        depend alors que de cette graine (voir src/graine.py).
        """
        if graine is not None:
            self.rng.seed(graine)
        self.graine = graine
        self.snake = self._spawn_snake()
        self.greens = []
        self.reds = []
        for _ in range(self.n_greens):
            self._spawn_apple(self.greens)
        for _ in range(self.n_reds):
            self._spawn_apple(self.reds)
        self.alive = True
        self.truncated = False
        self.steps = 0
        self.idle = 0
        self.max_length = len(self.snake)
        self.last_event = None
        self.end_cause = None
        self.direction = self._initial_direction()

    @property
    def dead(self):
        """Vrai terminal : une partie tronquee n'est pas une mort."""
        return not self.alive and not self.truncated

    @property
    def idle_limit(self):
        """Pas sans pomme avant troncature ; proportionnel a l'aire."""
        return self.idle_factor * self.size * self.size

    def _initial_direction(self):
        head, neck = self.snake[0], self.snake[1]
        return (head[0] - neck[0], head[1] - neck[1])

    def _spawn_snake(self):
        """Trois cases contigues, alignees, entierement sur le plateau."""
        while True:
            head = (
                self.rng.randrange(self.size),
                self.rng.randrange(self.size),
            )
            step = self.rng.choice(DIRECTIONS)
            cells = [
                (head[0] - step[0] * i, head[1] - step[1] * i)
                for i in range(SNAKE_LENGTH)
            ]
            if all(self.inside(c) for c in cells):
                return cells

    def inside(self, cell):
        x, y = cell
        return 0 <= x < self.size and 0 <= y < self.size

    def _occupied(self):
        return set(self.snake) | set(self.greens) | set(self.reds)

    def _spawn_apple(self, bucket):
        taken = self._occupied()
        free = [
            (x, y)
            for x in range(self.size)
            for y in range(self.size)
            if (x, y) not in taken
        ]
        if free:
            bucket.append(self.rng.choice(free))

    # -- simulation ---------------------------------------------------
    def step(self, direction):
        """Avance d'une case et retourne l'evenement de jeu du pas.

        La valeur rendue decrit ce qui est arrive au serpent : deplacement,
        pomme, ou mort. Elle ne dit PAS si la partie s'arrete : une troncature
        laisse l'evenement du pas intact (un deplacement reste un
        deplacement, et garde son cout) et se lit sur `end_cause`,
        `truncated` et `alive`.
        """
        if not self.alive:
            return self.last_event

        if direction not in DIRECTIONS:
            raise ValueError(
                "direction invalide : {!r}, attendu un element de "
                "DIRECTIONS".format(direction)
            )

        self.direction = direction
        head = self.snake[0]
        new_head = (head[0] + direction[0], head[1] + direction[1])
        self.steps += 1

        if not self.inside(new_head):
            return self._die(WALL)

        if new_head in self.greens:
            self.greens.remove(new_head)
            self.snake.insert(0, new_head)
            self._spawn_apple(self.greens)
            event = GREEN
        elif new_head in self.reds:
            self.reds.remove(new_head)
            self.snake.insert(0, new_head)
            del self.snake[-1]
            if self.snake:
                del self.snake[-1]
            self._spawn_apple(self.reds)
            if not self.snake:
                return self._die(STARVE)
            event = RED
        else:
            self.snake.insert(0, new_head)
            del self.snake[-1]
            event = MOVE

        if new_head in self.snake[1:]:
            return self._die(BODY)

        self.max_length = max(self.max_length, len(self.snake))
        self.last_event = event

        if event in (GREEN, RED):
            self.idle = 0
        else:
            self.idle += 1
            if self.idle >= self.idle_limit:
                self.truncate()
        return event

    def _die(self, cause):
        self.alive = False
        self.last_event = cause
        self.end_cause = cause
        return cause

    def truncate(self):
        """Arret sans mort : le serpent etait vivant, on a coupe le chrono.

        Publique a dessein : la boucle de jeu possede son propre plafond de
        securite et doit pouvoir terminer une partie de facon coherente, sans
        laisser `end_cause` a None sur une partie finie.

        Deux consequences, et la seconde est le piege a eviter :

        - l'agent doit continuer a bootstrapper (d'ou `dead` qui reste faux),
          sinon il apprend que vivre longtemps tue ;
        - le pas qui a declenche la troncature est un deplacement ordinaire
          et garde son cout. On ne touche donc pas a `last_event` : sinon la
          recompense de ce pas deviendrait celle d'un evenement "timeout",
          c'est-a-dire une prime pour avoir atteint la limite.
        """
        self.alive = False
        self.truncated = True
        self.end_cause = TIMEOUT

    # -- vision -------------------------------------------------------
    def cell_char(self, cell):
        """Symbole du contenu d'une case."""
        if not self.inside(cell):
            return WALL_CHAR
        if self.snake and cell == self.snake[0]:
            return HEAD_CHAR
        if cell in self.snake:
            return BODY_CHAR
        if cell in self.greens:
            return GREEN_CHAR
        if cell in self.reds:
            return RED_CHAR
        return EMPTY_CHAR

    def vision_rays(self):
        """Cases vues depuis la tete, direction par direction."""
        rays = {}
        if not self.snake:
            return rays
        head = self.snake[0]
        for d in DIRECTIONS:
            cells = []
            cur = (head[0] + d[0], head[1] + d[1])
            while self.inside(cur):
                cells.append(cur)
                cur = (cur[0] + d[0], cur[1] + d[1])
            cells.append(cur)
            rays[d] = cells
        return rays

    def vision_lines(self):
        """Croix de vision, telle qu'affichee dans le terminal."""
        if not self.snake:
            return []
        hx, hy = self.snake[0]
        lines = []
        for y in range(-1, self.size + 1):
            row = []
            for x in range(-1, self.size + 1):
                if x != hx and y != hy:
                    row.append(" ")
                else:
                    row.append(self.cell_char((x, y)))
            lines.append("".join(row))
        return lines

    def vision_chars(self):
        """Etat transmis a l'agent : une chaine de symboles par direction.

        C'est la seule information que le serpent percoit ; y ajouter
        quoi que ce soit d'autre est sanctionne par le sujet.
        """
        return {
            d: "".join(self.cell_char(c) for c in cells)
            for d, cells in self.vision_rays().items()
        }
