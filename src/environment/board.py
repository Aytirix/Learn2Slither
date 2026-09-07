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

DEATH_EVENTS = (WALL, BODY, STARVE)

WALL_CHAR = "W"
HEAD_CHAR = "H"
BODY_CHAR = "S"
GREEN_CHAR = "G"
RED_CHAR = "R"
EMPTY_CHAR = "0"


class Board:
    """Plateau de jeu conforme au sujet : 10x10, 2 pommes vertes, 1 rouge."""

    def __init__(self, size=10, greens=2, reds=1, rng=None):
        self.size = size
        self.n_greens = greens
        self.n_reds = reds
        self.rng = rng or random.Random()
        self.reset()

    # -- cycle de vie -------------------------------------------------
    def reset(self):
        """Replace serpent et pommes, remet les compteurs a zero."""
        self.snake = self._spawn_snake()
        self.greens = []
        self.reds = []
        for _ in range(self.n_greens):
            self._spawn_apple(self.greens)
        for _ in range(self.n_reds):
            self._spawn_apple(self.reds)
        self.alive = True
        self.steps = 0
        self.max_length = len(self.snake)
        self.last_event = None
        self.direction = self._initial_direction()

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
                for i in range(3)
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
        """Avance d'une case et retourne l'evenement resultant."""
        if not self.alive:
            return self.last_event

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
        return event

    def _die(self, cause):
        self.alive = False
        self.last_event = cause
        return cause

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
