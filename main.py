"""Point d'entree de Learn2Slither."""

import random
import sys

from src import baselines
from src.agent.fabrique import creer_agent
from src.agent.modele import ErreurModele, verifier_chemin_sauvegarde
from src.cli import build_config, parse_args, wants_lobby
from src.environment.rewards import recompense
from src.session import run_sessions


def construire_agent(config):
    """Agent demande par la ligne de commande ; quitte proprement si le
    modele passe a -load ne peut pas etre charge."""
    rng = random.Random(baselines.derive_seed(config.seed))
    try:
        return creer_agent(config, rng)
    except ErreurModele as probleme:
        erreur(probleme)


def erreur(message):
    """Affiche une erreur lisible et quitte, sans trace Python."""
    print("Erreur : {}".format(message), file=sys.stderr)
    sys.exit(1)


def main():
    args = parse_args()
    config = build_config(args)
    skip_lobby = not wants_lobby(args)

    if config.save_path is not None and not config.save_path:
        erreur("-save : nom de fichier vide")
    if config.save_path:
        # Verifie -save AVANT d'entrainer : une faute de frappe ne doit pas
        # faire perdre tout l'entrainement a la fin.
        try:
            verifier_chemin_sauvegarde(config.save_path)
        except ErreurModele as probleme:
            erreur(probleme)

    if not config.visual:
        agent = construire_agent(config)
        try:
            run_sessions(config, agent, reward_fn=recompense)
        except ErreurModele as probleme:
            erreur(probleme)
        return

    from src.interface.loop import run

    # Avec le lobby, l'agent est cree au lancement de la partie, une fois
    # le modele choisi (voir loop.agent_pour).
    agent = construire_agent(config) if skip_lobby else None
    if not run(config, skip_lobby=skip_lobby, agent=agent):
        sys.exit(1)


if __name__ == "__main__":
    main()
