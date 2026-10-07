"""Recensement des fichiers de modeles presents sur le disque."""

import os
import re

from .agent import modele

MODELS_DIR = "models"
EXTENSIONS = (".txt", ".json", ".qtable")
EXTENSION_NOUVEAU = ".txt"
BLANK_LABEL = "Aucun (agent neuf)"

# Nom d'un nouveau modele : il devient un nom de fichier, on n'accepte donc
# ni chemin (/, ..) ni caractere exotique.
NOM_MAX = 32
NOM_VALIDE = re.compile(r"^[A-Za-z0-9_-]{1,%d}$" % NOM_MAX)


def list_models(directory=MODELS_DIR):
    """Liste (libelle, chemin) ; l'entree vide est toujours en tete."""
    entries = [(BLANK_LABEL, None)]
    if not os.path.isdir(directory):
        return entries
    names = sorted(
        name
        for name in os.listdir(directory)
        if name.lower().endswith(EXTENSIONS)
        and os.path.isfile(os.path.join(directory, name))
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


class Infos:
    """Ce qu'un fichier de modele contient, pour l'afficher."""

    def __init__(self, chemin, agent=None, erreur=None):
        self.chemin = chemin
        self.nom = os.path.splitext(os.path.basename(chemin))[0]
        self.erreur = erreur
        self.parties = agent.parties if agent else 0
        self.pas_total = agent.pas_total if agent else 0
        self.etats = len(agent.q) if agent else 0
        self.epsilon = agent.epsilon if agent else 0.0
        self.gamma = agent.gamma if agent else 0.0
        self.epsilon_min = agent.epsilon_min if agent else 0.0
        self.pas_cible = agent.pas_cible if agent else 0
        self.valeur_initiale = agent.q.valeur_initiale if agent else 0.0
        try:
            self.octets = os.path.getsize(chemin)
        except OSError:
            self.octets = 0

    @property
    def lisible(self):
        return self.erreur is None


# Cache (chemin) -> (date de modification, taille, Infos) : la liste des
# modeles est redessinee a chaque image, on ne relit un fichier que s'il a
# change sur le disque.
_cache = {}


def infos(chemin):
    """Infos d'un modele ; un fichier illisible donne erreur != None."""
    try:
        stat = os.stat(chemin)
        cle = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        cle = None
    memo = _cache.get(chemin)
    if memo is not None and cle is not None and memo[0] == cle:
        return memo[1]
    try:
        resultat = Infos(chemin, agent=modele.charger(chemin))
    except modele.ErreurModele as erreur:
        resultat = Infos(chemin, erreur=str(erreur))
    if cle is not None:
        _cache[chemin] = (cle, resultat)
    return resultat


def modeles(directory=MODELS_DIR):
    """Infos de tous les modeles, du moins au plus entraine."""
    liste = [infos(path) for _, path in list_models(directory) if path]
    return sorted(liste, key=lambda i: (not i.lisible, i.parties, i.nom))


def meilleur_modele(directory=MODELS_DIR):
    """Chemin du modele le plus entraine, None s'il n'y en a aucun."""
    lisibles = [i for i in modeles(directory) if i.lisible]
    if not lisibles:
        return None
    return max(lisibles, key=lambda i: i.parties).chemin


def chemin_nouveau(nom, directory=MODELS_DIR):
    """Chemin du fichier d'un nouveau modele appele `nom`."""
    return os.path.join(directory, nom + EXTENSION_NOUVEAU)


def probleme_de_nom(nom, directory=MODELS_DIR):
    """Pourquoi `nom` ne convient pas a un nouveau modele ; None si ok."""
    if not nom:
        return "donne un nom au modele"
    if not NOM_VALIDE.match(nom):
        return "lettres, chiffres, - et _ seulement ({} max)".format(
            NOM_MAX)
    for _, path in list_models(directory):
        if path and os.path.splitext(os.path.basename(path))[0] == nom:
            return "un modele porte deja ce nom"
    return None
