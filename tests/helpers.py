"""Utilitaires partages par les modules de test."""

from src.environment import board as bd


def plateau_nu(size=10, idle_factor=bd.IDLE_FACTOR, rng=None):
    """Plateau sans pomme : rien ne peut remettre le compteur a zero."""
    return bd.Board(size=size, greens=0, reds=0,
                    idle_factor=idle_factor, rng=rng)


def pose(board, head, direction, longueur=3):
    """Place un serpent aligne, tete en `head`, cap sur `direction`."""
    board.snake = [
        (head[0] - direction[0] * i, head[1] - direction[1] * i)
        for i in range(longueur)
    ]
    board.direction = direction
    board.idle = 0
    board.max_length = longueur
    return board


def tour_du_plateau(board):
    """Directions qui longent le bord indefiniment, sans auto-collision.

    Le bord compte `4 * (size - 1)` cases, tres au-dela de la longueur du
    serpent : la queue a toujours quitte la case avant que la tete y revienne.
    Sert a produire autant de pas sans pomme qu'on veut.
    """
    n = board.size
    pose(board, (2, 0), bd.RIGHT)
    for _ in range(n - 3):
        yield bd.RIGHT
    while True:
        for direction in (bd.DOWN, bd.LEFT, bd.UP, bd.RIGHT):
            for _ in range(n - 1):
                yield direction


def joue(board, directions, limite=10000):
    """Joue les directions donnees jusqu'a la fin de partie."""
    evenements = []
    for direction in directions:
        if not board.alive or len(evenements) >= limite:
            break
        evenements.append(board.step(direction))
    return evenements


class Espion:
    """Agent qui joue un chemin impose et note tout ce qu'il recoit.

    Contrairement a un simple compteur, il enregistre les etats et l'action
    transmis a `learn`, ce qui permet de verifier le bootstrap et le fait que
    l'action jouee est bien celle que l'agent a choisie.
    """

    def __init__(self, chemin=()):
        self.chemin = list(chemin)
        self.choisies = []
        self.recu = []

    def choose(self, vision):
        action = self.chemin.pop(0) if self.chemin else bd.RIGHT
        self.choisies.append(action)
        return action

    def learn(self, state, action, reward, next_state, done):
        self.recu.append({
            "state": state,
            "action": action,
            "reward": reward,
            "next_state": next_state,
            "done": done,
        })


class Barometre:
    """Fonction de recompense qui note les evenements qu'on lui soumet."""

    TABLE = {
        bd.MOVE: -1,
        bd.GREEN: 20,
        bd.RED: -10,
        bd.WALL: -50,
        bd.BODY: -50,
        bd.STARVE: -50,
        bd.TIMEOUT: 0,
    }

    def __init__(self):
        self.vus = []

    def __call__(self, event):
        self.vus.append(event)
        return self.TABLE[event]
