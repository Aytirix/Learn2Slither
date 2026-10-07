"""Recensement des fichiers de modeles presents sur le disque."""

import os

MODELS_DIR = "models"
EXTENSIONS = (".txt", ".json", ".qtable")
BLANK_LABEL = "Aucun (agent neuf)"


def list_models(directory=MODELS_DIR):
    """Liste (libelle, chemin) ; l'entree vide est toujours en tete."""
    entries = [(BLANK_LABEL, None)]
    if not os.path.isdir(directory):
        return entries
    names = sorted(
        name
        for name in os.listdir(directory)
        if name.lower().endswith(EXTENSIONS)
    )
    for name in names:
        entries.append(
            (os.path.splitext(name)[0], os.path.join(directory, name))
        )
    return entries


def label_for(path, directory=MODELS_DIR):
    """Libelle affichable pour un chemin de modele."""
    if not path:
        return BLANK_LABEL
    for label, candidate in list_models(directory):
        if candidate == path:
            return label
    return os.path.splitext(os.path.basename(path))[0]
