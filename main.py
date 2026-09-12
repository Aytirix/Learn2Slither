"""Point d'entree de Learn2Slither."""

import random

from src import baselines
from src.cli import build_config, parse_args, wants_lobby
from src.session import run_sessions


def main():
    args = parse_args()
    config = build_config(args)
    seed = baselines.derive_seed(config.seed)
    agent = baselines.make(config.baseline, random.Random(seed))

    if not config.visual:
        run_sessions(config, agent)
        return

    from src.interface.loop import run

    run(config, skip_lobby=not wants_lobby(args), agent=agent)


if __name__ == "__main__":
    main()
