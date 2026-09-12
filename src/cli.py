"""Ligne de commande, au format attendu par le sujet.

Exemples du sujet :
    ./snake -sessions 10 -save models/10sess.txt -visual off
    ./snake -visual on -load models/100sess.txt -sessions 10 \
            -dontlearn -step-by-step
"""

import argparse

from . import baselines
from . import config as cfg

ON = "on"
OFF = "off"


def build_parser():
    """Construit le parseur ; les options longues sont en simple tiret."""
    parser = argparse.ArgumentParser(
        prog="snake",
        description="Learn2Slither — plateau, agent et affichage",
        allow_abbrev=False,
    )
    parser.add_argument(
        "-sessions", type=int, default=1,
        help="nombre de sessions d'entrainement a enchainer",
    )
    parser.add_argument(
        "-save", metavar="FICHIER", default=None,
        help="fichier ou sauvegarder l'etat d'apprentissage",
    )
    parser.add_argument(
        "-load", metavar="FICHIER", default=None,
        help="fichier de modele a charger avant de commencer",
    )
    parser.add_argument(
        "-visual", choices=(ON, OFF), default=ON,
        help="affichage graphique (off = entrainement rapide)",
    )
    parser.add_argument(
        "-dontlearn", action="store_true",
        help="fige la fonction Q : les recompenses sont ignorees",
    )
    parser.add_argument(
        "-step-by-step", action="store_true",
        help="avance d'un pas a chaque appui sur N",
    )
    parser.add_argument(
        "-verbose", action="store_true",
        help="garde la trace terminal meme avec -visual off",
    )

    extra = parser.add_argument_group("options supplementaires")
    extra.add_argument(
        "-size", type=int, default=10, help="taille du plateau (defaut : 10)"
    )
    extra.add_argument(
        "-speed", type=float, default=6.0, help="cases par seconde"
    )
    extra.add_argument("-seed", type=int, default=None, help="graine")
    extra.add_argument(
        "-pilot", choices=cfg.PILOTS, default=cfg.PILOT_AI,
        help="pilote par defaut (defaut : ia)",
    )
    extra.add_argument(
        "-lobby", choices=(ON, OFF), default=None,
        help="forcer ou non le passage par le lobby",
    )
    extra.add_argument(
        "-baseline", choices=tuple(baselines.BASELINES), default=None,
        help="agent de reference sans apprentissage, pour comparer",
    )
    return parser


def parse_args(argv=None):
    return build_parser().parse_args(argv)


def build_config(args):
    """Traduit les arguments en configuration de session."""
    visual = args.visual == ON
    return cfg.GameConfig(
        pilot=args.pilot,
        model=args.load,
        size=args.size,
        speed=args.speed,
        seed=args.seed,
        sessions=args.sessions,
        save_path=args.save,
        visual=visual,
        learn=not args.dontlearn,
        step_by_step=args.step_by_step,
        trace=args.verbose if not visual else True,
        baseline=args.baseline,
    )


def wants_lobby(args):
    """Le lobby s'ouvre sauf si la ligne de commande decrit deja la run."""
    if args.lobby is not None:
        return args.lobby == ON
    if args.visual == OFF:
        return False
    return not (
        args.sessions != 1
        or args.load
        or args.save
        or args.dontlearn
        or args.step_by_step
        or args.baseline
    )
