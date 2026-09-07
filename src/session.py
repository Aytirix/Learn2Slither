"""Enchainement de sessions sans affichage (-visual off).

L'agent est optionnel : tant qu'il n'existe pas, le serpent conserve
sa direction. Interface attendue cote agent :

    agent.choose(vision)                     -> direction (tuple)
    agent.learn(vision, action, reward,
                next_vision, done)           -> None      (optionnel)
    agent.save(path) / agent.load(path)      -> None      (optionnel)

`vision` est le dictionnaire renvoye par Board.vision_chars().
"""

import random

from .environment import board as bd


class SessionStats:
    """Bilan d'une serie de sessions."""

    def __init__(self):
        self.games = 0
        self.max_length = 0
        self.max_steps = 0
        self.total_steps = 0

    def record(self, board):
        self.games += 1
        self.max_length = max(self.max_length, board.max_length)
        self.max_steps = max(self.max_steps, board.steps)
        self.total_steps += board.steps

    def summary(self):
        mean = self.total_steps / self.games if self.games else 0.0
        return (
            "{} sessions — longueur maximale = {}, duree maximale = {}, "
            "duree moyenne = {:.1f}".format(
                self.games, self.max_length, self.max_steps, mean
            )
        )


def play_session(board, agent=None, reward_fn=None, trace=False,
                 max_idle=None):
    """Joue une partie complete et retourne l'evenement de fin."""
    idle = 0
    limit = max_idle or board.size * board.size * 4
    event = None
    while board.alive:
        vision = board.vision_chars()
        action = agent.choose(vision) if agent else board.direction
        event = board.step(action)

        if agent is not None and reward_fn is not None:
            learn = getattr(agent, "learn", None)
            if learn is not None:
                done = not board.alive
                after = board.vision_chars() if board.alive else vision
                learn(vision, action, reward_fn(event), after, done)

        idle = 0 if event in (bd.GREEN, bd.RED) else idle + 1
        if trace:
            for line in board.vision_lines():
                print(line)
            print("Action : {}".format(bd.ACTION_NAMES.get(action, "?")))
        if idle >= limit:
            board.alive = False
            board.last_event = bd.STARVE
            event = bd.STARVE
    return event


def run_sessions(config, agent=None, reward_fn=None):
    """Enchaine config.sessions parties sans ouvrir de fenetre."""
    rng = random.Random(config.seed)
    board = bd.Board(size=config.size, rng=rng)
    stats = SessionStats()

    for index in range(config.sessions):
        if index:
            board.reset()
        play_session(board, agent, reward_fn, trace=config.trace)
        stats.record(board)
        print(
            "Fin de la partie, longueur maximale = {}, "
            "duree maximale = {}".format(board.max_length, board.steps)
        )

    print(stats.summary())
    if config.save_path:
        save = getattr(agent, "save", None)
        if save is None:
            print(
                "Aucun agent a sauvegarder : {} n'a pas ete ecrit".format(
                    config.save_path
                )
            )
        else:
            save(config.save_path)
            print(
                "Sauvegarde de l'etat d'apprentissage dans {}".format(
                    config.save_path
                )
            )
    return stats
