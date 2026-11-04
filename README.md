# Learn2Slither

Un serpent qui apprend à survivre par essais et erreurs (apprentissage par
renforcement, Q-learning), sur un plateau 10×10, en ne voyant que les quatre
directions depuis sa tête.

| Document | Contenu |
|---|---|
| `README.md` | installation, utilisation, résumé de l'IA, structure |
| `IA.md` | le cours complet : formules, choix, mesures, pistes testées |
| `EXPLICATION.md` | le code fichier par fichier, et les questions de soutenance |
| `DECISIONS.md` | la documentation du code, module par module |
| `CORRECTION.md` | la fiche de soutenance, dans l'ordre du barème |

---

## Sommaire

1. [Installation](#1-installation)
2. [Ligne de commande](#2-ligne-de-commande)
3. [La fenêtre](#3-la-fenêtre)
4. [L'IA en bref](#4-lia-en-bref)
5. [Les modèles](#5-les-modèles)
6. [Structure du dépôt](#6-structure-du-dépôt)

---

## 1. Installation

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt     # pygame-ce, flake8
./snake                      # ouvre le menu principal
```

`./snake` utilise `.venv/bin/python` s'il existe, sinon `python3`.

Norme (le sujet impose flake8 ; `.flake8` exclut `.venv/`) :

```bash
.venv/bin/flake8 .
```

Tests (`unittest`, bibliothèque standard, rien à installer) :

```bash
.venv/bin/python -m unittest discover -s tests -t .
```

---

## 2. Ligne de commande

Les options suivent le format du sujet (simple tiret, nom complet).

```bash
# entraîner 10 parties sans fenêtre et sauvegarder
./snake -sessions 10 -save models/10sess.txt -visual off

# rejouer un modèle sans le modifier, pas à pas
./snake -visual on -load models/100sess.txt -sessions 10 -dontlearn -step-by-step

# continuer l'entraînement d'un modèle existant
./snake -load models/10sess.txt -sessions 90 -save models/100sess.txt -visual off
```

| Option | Rôle |
|---|---|
| `-sessions N` | nombre de parties à enchaîner (défaut 1, minimum 1) |
| `-save FICHIER` | écrit l'état d'apprentissage à la fin (chemin vérifié **avant** l'entraînement) |
| `-load FICHIER` | charge un modèle avant de commencer |
| `-visual on\|off` | `off` = ni fenêtre ni trace terminal, entraînement rapide |
| `-dontlearn` | fige l'agent : pas d'exploration, la table Q n'est jamais modifiée |
| `-step-by-step` | avance d'un pas à chaque appui sur `N` (ou `→`) |
| `-verbose` | garde la trace terminal même avec `-visual off` |
| `-size N` | taille du plateau, de 5 à 50 (bonus) |
| `-speed F` | cases par seconde, de 1 à 100 (`inf` = vitesse maximale) ; défaut 5 |
| `-seed N` | graine de départ : la partie n reçoit la graine N + n − 1 et se rejoue seule avec `-seed <sa graine>` |
| `-pilot ia\|joueur` | pilote présélectionné |
| `-lobby on\|off` | force ou non le passage par le lobby |
| `-baseline random` | agent de référence qui joue au hasard, pour comparer |

Le lobby s'ouvre par défaut, **sauf** si la ligne de commande décrit déjà
la partie : `-sessions` différent de 1, `-load`, `-save`, `-dontlearn`,
`-step-by-step`, `-baseline` ou `-visual off`.

À la fin de chaque partie, le terminal affiche
`Fin de la partie, longueur maximale = X, duree maximale = Y`, puis un bilan :
longueur moyenne, médiane et maximale, et causes de fin.

En cas d'erreur (modèle introuvable ou abîmé, dossier non accessible en écriture…),
le programme affiche `Erreur : …` et quitte avec le code 1, sans trace Python.
`Ctrl+C` pendant un entraînement l'arrête proprement et sauvegarde les parties
déjà terminées.

`-visual off` n'importe pas pygame : les parties s'enchaînent en Python pur,
plusieurs milliers par seconde quand elles sont courtes.

---

## 3. La fenêtre

### Le menu principal

| Entrée | Rôle |
|---|---|
| **JOUER** | le lobby : l'IA joue au mieux (agent **figé**, rien n'est sauvegardé), ou toi au clavier |
| **ENTRAINEMENT** | liste des modèles et leur détail ; créer un modèle (nom, γ, ε minimal, pas cible, valeur initiale, plateau, parties) ; continuer l'entraînement d'un modèle jusqu'à N parties |
| **EVALUATION** | parties en boucle avec l'agent figé jusqu'à une partie de longueur ≥ OBJECTIF (de 5 en 5, 35 par défaut) ; puis statistiques et rejeu coup par coup |
| **QUITTER** | ferme le programme |

`ÉCHAP` remonte d'un écran ; depuis le menu principal, il quitte.

**Lobby (JOUER) et réglages de l'évaluation :**

| Réglage | Valeurs | Défaut |
|---|---|---|
| PILOTE (JOUER seulement) | `IA` / `JOUEUR` | **IA** |
| MODÈLE | `CHOISIR` ouvre la liste des modèles avec leur détail, validée par `OK` | le plus entraîné |
| PLATEAU | 5×5 → 50×50 | **10×10** |
| VITESSE | 1 → 100 cases/s, puis MAX | 5 |

Navigation : `↑`/`↓` choisir, `←`/`→` modifier, `ENTRÉE` lancer (ou ouvrir
le choix du modèle sur la ligne MODÈLE). La souris fonctionne partout.

**Entraînement en fenêtre :** les parties sont jouées par tranches entre deux
images (barre de progression, moyenne des 100 dernières parties, courbe).
`ARRETER`, `ÉCHAP`, la croix de la fenêtre ou `Ctrl+C` arrêtent et
**sauvegardent** les parties déjà jouées.

**Résultats de l'évaluation :** parties jouées, longueur moyenne, médiane,
maximale, causes de fin ; rejeu de la partie qui a atteint l'objectif (ou de
la meilleure si l'évaluation a été arrêtée) : `←` coup précédent, `→` coup
suivant, `ORIGINE` / `FIN` début / présent.

### En partie

| Touche | Effet |
|---|---|
| `←` `→` `↑` `↓` / `ZQSD` | diriger le serpent — **inactif en mode IA** |
| `ESPACE` | pause, ou relancer après une mort |
| `N` / `→` | avancer d'un pas (active le mode pas à pas s'il ne l'est pas ; `→` seulement avec l'IA en pas à pas) |
| `←` | pas à pas avec l'IA : revoir le pas précédent (affichage seulement, la partie n'est pas rejouée) |
| `P` | activer/désactiver le mode pas à pas |
| `V` | surbrillance de la vision du serpent |
| `T` | trace terminal (vision + action à chaque pas) |
| `+` / `-` | vitesse : 1, 5, 10, 15, 20, 30, 40, 50, 75, 100 cases/s, puis MAX |
| `R` | nouvelle partie |
| `ÉCHAP` | retour au lobby (en évaluation : arrêter et voir les résultats) |

### La trace terminal

À chaque pas, le terminal affiche la vision du serpent (la croix vue depuis
la tête), puis l'action choisie :

```
    W
    0
W000HG00000W
    S
    W
Action : HAUT
```

`W` mur · `H` tête · `S` corps · `G` pomme verte · `R` pomme rouge · `0` vide.

---

## 4. L'IA en bref

Le détail, les formules et les mesures sont dans `IA.md`.

### Le plateau (`src/environment/board.py`)

10×10, deux pommes vertes, une rouge, serpent de 3 cases placé au hasard.
Mur, corps ou longueur 0 : fin de partie. Verte : +1 case. Rouge : −1 case.
Une partie qui dure trop sans pomme (4 × aire, soit 400 pas en 10×10) est
**tronquée** : ce n'est pas une mort, l'agent n'apprend pas qu'elle « tue ».

### Ce que voit l'agent

L'agent reçoit **uniquement** `board.vision_chars()` : quatre chaînes, une par
direction, de la tête jusqu'au mur. `src/agent/interpreter.py` résume chaque
rayon en (première chose vue, distance plafonnée à 3), lu dans le repère du
serpent : devant, à gauche, à droite. Cela donne au plus 1 728 états.

### Les actions

La table Q a trois colonnes : tout droit, tourner à gauche, tourner à droite.
`tourner()` les traduit en `UP`, `LEFT`, `DOWN` ou `RIGHT` : le plateau reçoit
toujours une des quatre actions du sujet. Le demi-tour n'est pas proposé, parce
qu'il tue tout de suite contre le cou.

### Les récompenses (`src/environment/rewards.py`)

| Évènement | Récompense |
|---|---|
| pas sans rien manger | −1 |
| pomme verte | +20 |
| pomme rouge | −10 |
| mur, corps, longueur 0 | −50 |

### Le Q-learning (`src/agent/agent.py`, `src/agent/qtable.py`)

```
cible = r                             si le serpent meurt
cible = r + γ · max Q(état suivant)   sinon (troncature comprise)
Q(s, a) ← Q(s, a) + α · (cible − Q(s, a))
```

| Paramètre | Valeur |
|---|---|
| γ | 0,95 |
| α | 1 / n^0,7, n = nombre de mises à jour du couple (état, action) |
| valeur initiale | +1 (optimiste : une action jamais essayée paraît meilleure) |
| ε (ε-greedy) | de 1 à 0,01, en ligne droite sur 5 000 pas |

Chaque pas est noté pendant la partie ; à la fin de la partie, chaque transition
reçoit sa mise à jour, dans l'ordre. Avec `-dontlearn`, ε vaut 0 et la table
n'est jamais modifiée.

---

## 5. Les modèles

Un modèle est un seul fichier JSON (extension `.txt`) : valeurs Q, compteurs
de visites, hyperparamètres, nombre de parties et version de l'encodage
(un modèle d'un autre encodage est refusé au chargement).

Mesuré avec `-dontlearn` sur 200 parties en 10×10 (longueur en fin de partie) :

| Modèle | Parties apprises | Longueur moyenne | Parties finies à ≥ 10 |
|---|---|---|---|
| `models/1sess.txt` | 1 | 3,1 | 0 % |
| `models/10sess.txt` | 10 | 3,4 | 0 % |
| `models/100sess.txt` | 100 | 4,2 | 0,5 % |
| `models/1000sess.txt` | 1 000 | 22,8 | 92 % |
| `models/infini.txt` | 4,1 millions | 27,8 | 99,5 % |

Le même modèle joue sur d'autres tailles sans réentraînement (l'état ne
contient ni coordonnée ni taille) : `infini.txt` fait 22 de moyenne en 8×8
et 55 en 20×20.

Le serpent plafonne vers 28-30 : il ne voit qu'une ligne et une colonne, pas
la forme de son corps, et finit par s'enfermer. Les pistes testées pour aller
plus loin sont dans `IA.md`.

---

## 6. Structure du dépôt

```
snake                      lanceur shell (./snake -sessions ...)
main.py                    point d'entrée : sans fenêtre / avec fenêtre
.flake8                    configuration de la norme (exclut .venv/)
requirements.txt           dépendances (pygame-ce, flake8)
sujet/                     énoncé du projet (PDF, fr et en)
models/                    modèles entraînés : 1, 10, 100, 1000 parties, infini
src/
├── cli.py                 arguments du sujet
├── config.py              GameConfig : réglages d'une session
├── graine.py              une graine par partie (-seed)
├── models.py              recensement des fichiers de models/
├── baselines.py           agents de référence sans apprentissage
├── session.py             enchaînement des parties sans fenêtre, statistiques
├── training.py            entraînement par tranches (menu ENTRAINEMENT)
├── evaluation.py          objectif, statistiques, photos pour le rejeu
├── environment/
│   ├── board.py           plateau, règles, vision
│   └── rewards.py         barème de récompenses
├── agent/
│   ├── interpreter.py     vision → état égocentrique, actions relatives
│   ├── qtable.py          la table Q et ses compteurs de visites
│   ├── agent.py           choisir, apprendre, epsilon, -dontlearn
│   ├── modele.py          sauvegarde / chargement JSON versionné
│   └── fabrique.py        agent demandé par la ligne de commande
└── interface/
    ├── theme.py           palette, dimensions, polices
    ├── gfx.py             halos, vignette, interpolations
    ├── starfield.py       fond spatial
    ├── particles.py       particules
    ├── board_view.py      rendu du plateau
    ├── panel_view.py      panneau latéral
    ├── renderer.py        composition d'une image
    ├── widgets.py         fond, boutons, formulaires communs aux menus
    ├── menu.py            menu principal
    ├── lobby.py           écran de configuration (JOUER, EVALUATION)
    ├── model_picker.py    choix du modèle
    ├── model_card.py      liste et fiche détaillée d'un modèle
    ├── training_view.py   écran ENTRAINEMENT
    ├── evaluation_view.py partie d'évaluation, résultats et rejeu
    ├── game.py            état d'une partie, tempo, effets
    └── loop.py            boucle pygame, passage d'un écran à l'autre
tests/                     suite unittest (343 tests)
```

### Le contrat entre le plateau et l'agent

Deux boucles appellent l'agent, avec le même contrat : `src/session.py`
(sans fenêtre) et `src/interface/game.py` (avec fenêtre).

```python
agent.debut_partie(board.direction)          # sens de départ du serpent
agent.choose(vision) -> direction            # à chaque pas
agent.learn(vision, action, reward, next_vision, board.dead)  # à chaque pas
agent.fin_partie()                           # apprentissage de la partie
agent.save(path)                             # -save ; -load : agent/modele.py
```

`vision` vient de `board.vision_chars()` : c'est la seule information que
l'agent reçoit sur le plateau. Le sens de départ se lit aussi dans la vision
(le cou `S` est collé à la tête) ; ensuite l'agent le tient à jour lui-même,
à partir de son propre coup.

`board.dead` est vrai seulement pour une vraie mort, pas pour une troncature :
une partie tronquée a encore un état suivant, qui compte dans la cible.
