"""Point d'entree de Learn2Slither."""

from src.cli import build_config, parse_args, wants_lobby
from src.session import run_sessions


def main():
    args = parse_args()
    config = build_config(args)

    if not config.visual:
        run_sessions(config)
        return

    from src.interface.loop import run

    run(config, skip_lobby=not wants_lobby(args))


if __name__ == "__main__":
    main()
