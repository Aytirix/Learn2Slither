"""Etape 11 : sauvegarder et recharger un agent (IA.md section 11.5).

Le sujet demande qu'un modele tienne dans UN fichier qu'on peut recharger
pour reprendre l'apprentissage, ou pour l'evaluer avec -dontlearn. Le format
est du JSON, lisible a l'oeil :

    {
      "format": "learn2slither-qtable",
      "version_encodage": 1,
      "distance_max": 3,
      "regle": "qlearning",
      "hyperparametres": {"gamma": 0.95, ...},
      "parties": 100,
      "pas_total": 2417,
      "qtable": {
        "R2|G2|W3": {"valeurs": [-0.8, 4.2, -12.5], "visites": [3, 7, 1]},
        ...
      }
    }

Seule contrainte : JSON n'accepte pas un tuple comme cle, seulement du texte.
L'etat (('R', 2), ('G', 2), ('W', 3)) devient donc la cle "R2|G2|W3" a
l'ecriture, et redevient un tuple a la lecture.
"""

import json
import math
import os

from . import interpreter as it
from .agent import Agent
from .qtable import QTable

FORMAT = "learn2slither-qtable"
REGLE = "qlearning"

# Plus grand compteur accepte (visites, parties, pas). Bien au-dela de tout
# entrainement reel, mais assez petit pour que les calculs qui l'utilisent
# (alpha = 1/n^0.7, epsilon = pas/pas_cible) ne debordent jamais.
COMPTEUR_MAX = 10 ** 15


class ErreurModele(ValueError):
    """Fichier de modele absent, illisible, incompatible ou non inscriptible.

    Toute erreur liee a un fichier de modele devient une ErreurModele, avec
    un message lisible : le programme l'affiche et s'arrete proprement, au
    lieu de planter sur une trace Python (le sujet note 0 un programme qui
    quitte de facon inattendue).
    """


# -- Les cles : tuple <-> texte ----------------------------------------------

def etat_vers_texte(etat):
    """(('R', 2), ('G', 2), ('W', 3))  ->  "R2|G2|W3"."""
    return "|".join(symbole + str(distance) for symbole, distance in etat)


def texte_vers_etat(texte):
    """"R2|G2|W3"  ->  (('R', 2), ('G', 2), ('W', 3)).

    Le symbole est toujours un seul caractere ; tout ce qui suit est la
    distance, ce qui marcherait aussi si DISTANCE_MAX depassait 9.
    """
    return tuple(
        (morceau[0], int(morceau[1:])) for morceau in texte.split("|")
    )


# -- Ecriture ----------------------------------------------------------------

def verifier_chemin_sauvegarde(chemin):
    """Verifie qu'on pourra ecrire dans `chemin`, AVANT d'entrainer.

    Sans cette verification, une faute de frappe dans -save ne se verrait
    qu'a la toute fin, apres des minutes d'entrainement perdues.
    """
    if os.path.isdir(chemin):
        raise ErreurModele(
            "-save {} : c'est un dossier, pas un fichier".format(chemin))
    if not os.path.basename(chemin):
        raise ErreurModele(
            "-save {} : il manque le nom du fichier".format(chemin))
    dossier = os.path.dirname(os.path.abspath(chemin))
    # Remonte jusqu'au premier dossier qui existe deja : c'est lui qui doit
    # etre inscriptible pour qu'on puisse creer le reste.
    existant = dossier
    while not os.path.exists(existant):
        existant = os.path.dirname(existant)
    if not os.path.isdir(existant):
        raise ErreurModele(
            "-save {} : {} est un fichier, pas un dossier".format(
                chemin, existant))
    if not os.access(existant, os.W_OK | os.X_OK):
        raise ErreurModele(
            "-save {} : pas le droit d'ecrire dans {}".format(
                chemin, existant))
    if os.path.exists(chemin) and not os.access(chemin, os.W_OK):
        raise ErreurModele(
            "-save {} : fichier protege en ecriture".format(chemin))


def sauvegarder(agent, chemin):
    """Ecrit tout l'etat d'apprentissage de `agent` dans `chemin`.

    L'ecriture passe par un fichier temporaire, renomme a la fin : si
    l'ecriture echoue en cours de route, l'ancien modele reste intact.
    Leve ErreurModele si le fichier ne peut pas etre ecrit.
    """
    q = agent.q
    donnees = {
        "format": FORMAT,
        "version_encodage": it.VERSION_ENCODAGE,
        "distance_max": it.DISTANCE_MAX,
        "regle": REGLE,
        "hyperparametres": {
            "gamma": agent.gamma,
            "alpha": "1/n^0.7",
            "valeur_initiale": q.valeur_initiale,
            "epsilon_min": agent.epsilon_min,
            "pas_cible": agent.pas_cible,
        },
        "parties": agent.parties,
        "pas_total": agent.pas_total,
        "qtable": {
            etat_vers_texte(etat): {
                "valeurs": valeurs,
                "visites": q.visites.get(etat, [0] * len(it.ACTIONS)),
            }
            for etat, valeurs in sorted(q.table.items())
        },
    }
    verifier_chemin_sauvegarde(chemin)
    temporaire = chemin + ".tmp"
    try:
        dossier = os.path.dirname(chemin)
        if dossier:
            os.makedirs(dossier, exist_ok=True)
        with open(temporaire, "w", encoding="utf-8") as fichier:
            json.dump(donnees, fichier, indent=1)
            fichier.write("\n")
        os.replace(temporaire, chemin)
    except OSError as erreur:
        if os.path.isfile(temporaire):
            os.remove(temporaire)
        raise ErreurModele("ecriture impossible de {} : {}".format(
            chemin, erreur.strerror or erreur))


# -- Lecture -----------------------------------------------------------------

def charger(chemin, rng=None):
    """Recree un agent a partir d'un fichier ecrit par sauvegarder().

    Leve ErreurModele, avec un message clair, plutot que de planter ou,
    pire, de charger un modele incompatible sans rien dire.
    """
    donnees = _lire_json(chemin)
    _verifier_compatibilite(donnees, chemin)
    try:
        hyper, q = _lire_contenu(donnees)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError,
            OverflowError) as erreur:
        raise ErreurModele("{} est corrompu : {}".format(chemin, erreur))

    agent = Agent(
        rng=rng,
        qtable=q,
        gamma=hyper["gamma"],
        epsilon_min=hyper["epsilon_min"],
        pas_cible=hyper["pas_cible"],
    )
    agent.parties = donnees["parties"]
    agent.pas_total = donnees["pas_total"]
    # On reprend l'exploration la ou elle s'etait arretee, sinon un modele
    # deja entraine se remettrait a jouer au hasard.
    agent.mettre_a_jour_epsilon()
    return agent


def _lire_contenu(donnees):
    """Valide TOUT le contenu et reconstruit la table.

    Chaque valeur est controlee ici, au chargement : un modele corrompu doit
    etre refuse tout de suite, pas planter au milieu d'une partie le jour
    ou l'etat abime est enfin rencontre.
    """
    hyper = donnees["hyperparametres"]
    _nombre(hyper["gamma"], "gamma", 0.0, 1.0)
    _nombre(hyper["valeur_initiale"], "valeur_initiale")
    _nombre(hyper["epsilon_min"], "epsilon_min", 0.0, 1.0)
    if _nombre(hyper["pas_cible"], "pas_cible") <= 0:
        raise ValueError("pas_cible doit etre positif")
    _compteur(hyper["pas_cible"], "pas_cible")
    for champ in ("parties", "pas_total"):
        _compteur(donnees[champ], champ)

    q = QTable(valeur_initiale=hyper["valeur_initiale"])
    for texte, ligne in donnees["qtable"].items():
        etat = _etat_valide(texte)
        valeurs = [_nombre(v, "valeur") for v in ligne["valeurs"]]
        visites = ligne["visites"]
        if len(valeurs) != len(it.ACTIONS) or len(visites) != len(it.ACTIONS):
            raise ValueError("{} : il faut {} valeurs et {} visites".format(
                texte, len(it.ACTIONS), len(it.ACTIONS)))
        for n in visites:
            _compteur(n, "visites de " + texte)
        q.table[etat] = valeurs
        q.visites[etat] = list(visites)
    return hyper, q


def _nombre(valeur, nom, minimum=None, maximum=None):
    """Un nombre fini (ni texte, ni NaN, ni infini), dans les bornes."""
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)):
        raise ValueError("{} n'est pas un nombre : {!r}".format(nom, valeur))
    try:
        fini = math.isfinite(valeur)
    except OverflowError:
        fini = False
    if not fini:
        raise ValueError("{} n'est pas fini : {!r}".format(
            nom, valeur if isinstance(valeur, float) else "entier geant"))
    if minimum is not None and not minimum <= valeur <= maximum:
        raise ValueError("{} hors de [{}, {}] : {}".format(
            nom, minimum, maximum, valeur))
    return float(valeur)


def _compteur(valeur, nom):
    """Un vrai entier (pas un booleen) entre 0 et COMPTEUR_MAX."""
    if type(valeur) is not int or not 0 <= valeur <= COMPTEUR_MAX:
        raise ValueError("{} doit etre un entier entre 0 et {}".format(
            nom, COMPTEUR_MAX))
    return valeur


def _etat_valide(texte):
    """Cle de table relue, verifiee : 3 couples (symbole connu, distance)."""
    etat = texte_vers_etat(texte)
    if etat_vers_texte(etat) != texte:
        # Refuse "R 2", "R+2", "R02"... : deux ecritures du meme etat
        # fusionneraient sans rien dire.
        raise ValueError("cle {!r} non canonique".format(texte))
    if len(etat) != 3:
        raise ValueError("cle {!r} : 3 directions attendues".format(texte))
    for symbole, distance in etat:
        if symbole not in "WSGR" or not 1 <= distance <= it.DISTANCE_MAX:
            raise ValueError("cle {!r} invalide".format(texte))
    return etat


def _lire_json(chemin):
    try:
        with open(chemin, encoding="utf-8") as fichier:
            return json.load(fichier)
    except FileNotFoundError:
        raise ErreurModele("fichier de modele introuvable : {}".format(chemin))
    except IsADirectoryError:
        raise ErreurModele("{} est un dossier, pas un modele".format(chemin))
    except (OSError, UnicodeDecodeError) as erreur:
        raise ErreurModele("lecture impossible de {} : {}".format(
            chemin, erreur))
    except (ValueError, RecursionError):
        # JSONDecodeError, mais aussi un entier de plus de 4 300 chiffres
        # (ValueError) ou des crochets imbriques a l'infini (RecursionError).
        raise ErreurModele("{} n'est pas un fichier JSON valide".format(
            chemin))


def _verifier_compatibilite(donnees, chemin):
    if not isinstance(donnees, dict) or donnees.get("format") != FORMAT:
        raise ErreurModele(
            "{} n'est pas un modele Learn2Slither".format(chemin)
        )
    if (type(donnees.get("version_encodage")) is not int
            or donnees["version_encodage"] != it.VERSION_ENCODAGE):
        raise ErreurModele(
            "{} a ete entraine avec l'encodage v{}, le code utilise la v{} :"
            " ses etats ne correspondent plus".format(
                chemin, donnees.get("version_encodage"), it.VERSION_ENCODAGE
            )
        )
    if (type(donnees.get("distance_max")) is not int
            or donnees["distance_max"] != it.DISTANCE_MAX):
        raise ErreurModele(
            "{} utilise DISTANCE_MAX = {}, le code utilise {}".format(
                chemin, donnees.get("distance_max"), it.DISTANCE_MAX
            )
        )
    manquants = {"hyperparametres", "parties", "pas_total", "qtable"}
    manquants -= set(donnees)
    if manquants:
        raise ErreurModele("{} est incomplet, il manque : {}".format(
            chemin, ", ".join(sorted(manquants))))
