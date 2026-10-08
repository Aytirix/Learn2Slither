# Learn2Slither

Un serpent qui apprend à survivre par essais et erreurs, sur un plateau 10×10,
en ne voyant que les quatre directions depuis sa tête.

> **Le cours de référence est `IA.md`.**
>
> Toute la partie apprentissage par renforcement de ce fichier — **§4 à §15,
> glossaire compris** — est une version antérieure, **obsolète dans son
> ensemble**. Ne t'y fie sur aucun point : elle diverge de `IA.md` sur
> l'espace d'actions, l'encodage de l'état, la troncature, le barème de
> récompenses, le reward shaping, la décroissance d'epsilon, le taux
> d'apprentissage, l'initialisation de la table, le format de modèle, la
> priorité des variantes, et elle ignore le rejeu inverse.
>
> Aucune énumération ne sera tenue à jour ici : en cas de désaccord, même
> sur un détail, **`IA.md` fait foi**. Ces sections seront supprimées.

Ce README sert deux publics : celui qui veut **lancer le projet** (§1 à §3) et
celui qui veut **comprendre et écrire l'agent** (§4 et au-delà — voir
l'avertissement ci-dessus : cette partie est obsolète, `IA.md` la remplace).
La partie apprentissage par renforcement y est détaillée pas à pas : elle
contient les formules, leur explication terme par terme, les variantes, et un
plan d'implémentation. Le code de l'agent n'y est pas écrit — c'est le travail
à faire.

---

## Sommaire

**Le projet**
1. [Installation et lancement](#1-installation-et-lancement)
2. [Ligne de commande](#2-ligne-de-commande)
3. [Structure du dépôt](#3-structure-du-dépôt)

**Comprendre l'apprentissage par renforcement**
4. [Le vocabulaire de base](#4-le-vocabulaire-de-base)
5. [La fonction Q et l'équation de Bellman](#5-la-fonction-q-et-léquation-de-bellman)
6. [Le Q-learning, ligne par ligne](#6-le-q-learning-ligne-par-ligne)
7. [Modéliser Snake : état, actions, récompenses](#7-modéliser-snake--état-actions-récompenses)
8. [Exploration contre exploitation](#8-exploration-contre-exploitation)
9. [Les hyperparamètres](#9-les-hyperparamètres)
10. [Les variantes de mise à jour](#10-les-variantes-de-mise-à-jour)
11. [Les réseaux de neurones](#11-les-réseaux-de-neurones)

**Passer à la pratique**
12. [Plan d'implémentation](#12-plan-dimplémentation)
13. [Diagnostiquer un agent qui n'apprend pas](#13-diagnostiquer-un-agent-qui-napprend-pas)
14. [Pièges du sujet et checklist de soutenance](#14-pièges-du-sujet-et-checklist-de-soutenance)
15. [Glossaire](#15-glossaire)

---

# LE PROJET

## 1. Installation et lancement

```bash
python3 -m venv .venv
.venv/bin/pip install pygame-ce flake8
./snake                      # ouvre le menu principal
```

`./snake` détecte automatiquement `.venv/bin/python` s'il existe, sinon il
utilise `python3`.

Vérification de la norme (le sujet impose flake8 pour un projet Python) :

```bash
.venv/bin/flake8 main.py src/ tests/
```

Suite de tests — `unittest` de la bibliothèque standard, rien à installer :

```bash
.venv/bin/python -m unittest discover -s tests -t .
```

### Le menu principal

Lancé sans argument, `./snake` ouvre le menu principal :

| Entrée | Rôle |
|---|---|
| **JOUER** | le lobby : l'IA joue au mieux (agent **figé**, rien n'est sauvegardé), ou toi au clavier |
| **ENTRAINEMENT** | liste des modèles et leur détail ; créer un modèle (nom, vision, γ, ε minimal, pas cible, valeur initiale, plateau, parties) ; continuer l'entraînement d'un modèle jusqu'à N parties |
| **EVALUATION** | parties en boucle avec l'agent figé jusqu'à une partie de longueur ≥ OBJECTIF (réglable de 5 en 5, 35 par défaut), menée jusqu'à sa fin ; puis statistiques et rejeu coup par coup |
| **QUITTER** | ferme le programme |

`ÉCHAP` remonte d'un écran ; depuis le menu principal, il quitte.

**Option VISION = PLATEAU (hors sujet).** À la création d'un modèle, on peut
lui donner, en plus de sa croix, deux informations calculées sur **tout** le
plateau : pour chaque coup, si la case mène à un piège (espace libre plus
petit que le serpent), et de quel côté est la pomme verte la plus proche.
Le sujet l'interdit (−42) : c'est une option de comparaison, jamais active
par défaut, enregistrée dans le fichier du modèle (`"vision": "plateau"`).
Partout où un tel modèle est utilisé (liste, fiche, lobby, partie,
résultats, et `-load` en ligne de commande), un avertissement rouge
« ATTENTION : VOIT TOUT LE PLATEAU (HORS SUJET) » s'affiche. Les modèles
rendus dans `models/` voient tous seulement la croix.

**Lobby (JOUER) et réglages de l'évaluation :**

| Réglage | Valeurs | Défaut |
|---|---|---|
| PILOTE (JOUER seulement) | `IA` / `JOUEUR` | **IA** |
| MODÈLE | `CHOISIR` ouvre la liste des modèles avec leur détail, validée par `OK` | le plus entraîné |
| PLATEAU | 5×5 → 50×50 | **10×10** |
| VITESSE | 1 → 100 cases/s | 6 |

Navigation : `↑`/`↓` choisir, `←`/`→` modifier, `ENTRÉE` lancer (ou ouvrir
le choix du modèle sur la ligne MODÈLE). La souris fonctionne partout.

**Entraînement en fenêtre :** les parties sont jouées par tranches entre deux
images (barre de progression, moyenne des 100 dernières parties, courbe).
`ARRETER`, `ÉCHAP`, la croix de la fenêtre ou Ctrl+C arrêtent et
**sauvegardent** les parties déjà jouées.

**Résultats de l'évaluation :** parties jouées, longueur moyenne, médiane,
maximale, causes de fin ; rejeu de la partie qui a atteint 35 (ou de la
meilleure si l'évaluation a été arrêtée) : `←` coup précédent, `→` coup
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
| `T` | trace terminal |
| `+` / `-` | vitesse : 1, 5, 10, 15, 20, 30, 40, 50, 75, 100 cases/s, puis MAX |
| `R` | nouvelle partie |
| `ÉCHAP` | retour au lobby (en évaluation : arrêter et voir les résultats) |

---

## 2. Ligne de commande

Les options suivent le format du sujet (simple tiret, nom complet).

```bash
./snake -sessions 10 -save models/10sess.txt -visual off
./snake -visual on -load models/100sess.txt -sessions 10 -dontlearn -step-by-step
```

| Option | Rôle |
|---|---|
| `-sessions N` | nombre de parties à enchaîner (défaut 1) |
| `-save FICHIER` | écrit l'état d'apprentissage à la fin |
| `-load FICHIER` | charge un modèle avant de commencer |
| `-visual on\|off` | `off` = aucune fenêtre, aucun rendu, entraînement rapide |
| `-dontlearn` | fige la fonction Q : les récompenses sont ignorées |
| `-step-by-step` | avance d'un pas à chaque appui sur `N` |
| `-verbose` | garde la trace terminal même avec `-visual off` |
| `-size N` | taille du plateau (bonus) |
| `-speed F` | cases par seconde (`inf` = vitesse maximale) |
| `-seed N` | graine aléatoire, pour des runs reproductibles |
| `-pilot ia\|joueur` | pilote présélectionné |
| `-lobby on\|off` | force ou non le passage par le lobby |
| `-baseline random` | agent de référence sans apprentissage, pour comparer |

Le lobby s'ouvre par défaut, **sauf** si la ligne de commande décrit déjà
la run : `-sessions` avec une valeur autre que 1, `-load`, `-save`,
`-dontlearn`, `-step-by-step`, `-baseline`, ou `-visual off`.

**Le mode `-visual off` n'importe pas pygame du tout.** Il enchaîne les
parties en pur Python, ce qui rend l'entraînement massif praticable (l'ordre
de grandeur mesuré est de plusieurs milliers de sessions par seconde sur des
parties courtes ; des parties plus longues coûtent proportionnellement plus).

---

## 3. Structure du dépôt

```
snake                      lanceur shell (./snake -sessions ...)
main.py                    point d'entrée : dispatch headless / graphique
sujet/                     énoncé du projet (PDF, fr et en)
models/                    modèles entraînés : 1, 10, 100, 1000, 10000 sessions
src/
├── cli.py                 arguments du sujet
├── config.py              GameConfig : réglages d'une session
├── models.py              recensement des fichiers de models/
├── baselines.py           agents de référence sans apprentissage
├── session.py             enchaînement des parties, statistiques
├── training.py            entraînement par tranches (menu ENTRAINEMENT)
├── evaluation.py          seuil (35 par défaut), statistiques, photos pour le rejeu
├── environment/
│   └── board.py           plateau, règles, vision
├── agent/
│   ├── interpreter.py     vision → état égocentrique, actions relatives
│   ├── qtable.py          la table Q et ses compteurs de visites
│   ├── agent.py           choisir, apprendre, rejeu inverse, epsilon
│   ├── modele.py          sauvegarde / chargement JSON versionné
│   └── fabrique.py        agent demandé par la ligne de commande
└── interface/
    ├── theme.py           palette, dimensions, polices
    ├── gfx.py             bloom, halos, vignette, interpolations
    ├── starfield.py       fond spatial
    ├── particles.py       particules
    ├── board_view.py      rendu du plateau
    ├── panel_view.py      panneau latéral
    ├── renderer.py        composition d'une frame
    ├── widgets.py         fond, boutons, formulaires communs aux menus
    ├── menu.py            menu principal
    ├── lobby.py           écran de configuration (JOUER, EVALUATION)
    ├── model_picker.py    choix du modèle
    ├── model_card.py      liste et fiche détaillée d'un modèle
    ├── training_view.py   écran ENTRAINEMENT
    ├── evaluation_view.py partie d'évaluation, résultats et rejeu
    ├── game.py            état d'une partie, tempo, effets
    └── loop.py            boucle pygame, machine à états entre les écrans
tests/                     suite unittest (bibliothèque standard)
├── helpers.py             plateaux de test, agent espion, barème
├── test_board.py          vision, collisions, pommes, mort, troncature
├── test_session.py        contrat d'apprentissage, statistiques, baselines
└── test_cli.py            traduction des arguments en configuration
```

### Les points d'accroche de l'agent

L'agent est écrit (`src/agent/`) et branché dans les deux boucles :
`-load`, `-dontlearn` et `-save` fonctionnent en mode graphique comme sans
affichage. Le barème de récompenses est dans `src/environment/rewards.py`.

```python
# ce que l'environnement fournit
board.vision_chars()   # {direction: "SS0G0W", ...} — LE seul état autorisé
board.step(direction)  # évènement du PAS : "move" | "green" | "red"
                       #                  | "wall" | "body" | "starve"
                       # hors board.DIRECTIONS -> ValueError (si alive)

# la fin de partie ne se lit PAS dans la valeur de retour de step()
board.alive            # False dès que la partie est finie
board.end_cause        # None, ou "wall"|"body"|"starve"|"timeout"
board.dead             # True seulement pour une VRAIE mort
board.truncated        # True si la partie a été coupée (trop de pas sans pomme)

board.max_length       # longueur maximale atteinte
board.steps            # durée de la partie
```

**`board.dead` est ce qu'il faut passer à `learn()`, jamais `not board.alive`.**
Une partie tronquée n'est pas une mort : le serpent était vivant, donc son état
suivant a une valeur et l'agent doit continuer à bootstrapper. Et le pas qui a
déclenché la troncature reste un `"move"`, avec son coût normal. `IA.md` §4.5
et §7.2 détaillent le piège.

```python
# ce que les boucles appellent sur l'agent (src/agent/agent.py)
agent.debut_partie(board.direction)          # cap de départ du serpent
agent.choose(vision) -> direction            # à chaque pas, obligatoire
agent.learn(vision, action, reward, next_vision, board.dead)  # à chaque pas
agent.fin_partie()                           # rejeu inverse : il apprend ici
agent.save(path)                             # -save ; -load : agent/modele.py
```

`direction` est l'un des quatre tuples exportés par `src/environment/board.py` :
`UP`, `DOWN`, `LEFT`, `RIGHT`.

Une fois l'agent écrit, il se branche à deux endroits :

```python
run_sessions(config, agent=mon_agent, reward_fn=ma_fonction)  # headless
Game(config, agent=mon_agent)                                 # graphique
```

---

# COMPRENDRE L'APPRENTISSAGE PAR RENFORCEMENT

## 4. Le vocabulaire de base

L'apprentissage par renforcement, c'est une boucle entre deux entités.

```
        ┌──────────────────────────────────────┐
        │                                      │
        ▼                                      │
   ┌─────────┐   action a          ┌──────────────────┐
   │  AGENT  │ ──────────────────► │  ENVIRONNEMENT   │
   │         │ ◄────────────────── │    (plateau)     │
   └─────────┘  état s', récompense r └──────────────┘
```

À chaque pas de temps :

1. l'agent observe un **état** `s` (ici : la vision du serpent) ;
2. il choisit une **action** `a` parmi 4 (HAUT, BAS, GAUCHE, DROITE) ;
3. l'environnement applique l'action, produit un nouvel état `s'` et une
   **récompense** `r` (un nombre) ;
4. on recommence, jusqu'à la fin de l'**épisode** (ici : la mort du serpent).

Quelques termes qui reviendront :

| Terme | Définition |
|---|---|
| **Épisode** (ou session) | une partie complète, du placement du serpent à sa mort |
| **Politique** π | la règle qui décide de l'action à partir de l'état |
| **Retour** `G` | somme des récompenses futures à partir d'un instant |
| **Facteur d'escompte** γ | poids donné au futur, entre 0 et 1 |
| **Épisodique** | le problème a une fin (contrairement à une tâche continue) |

### Pourquoi une simple somme de récompenses ne suffit pas

Si l'agent maximisait uniquement la récompense immédiate, il serait
myope : il éviterait un détour de deux cases même si ce détour mène à une
pomme. On veut qu'il maximise le **retour**, c'est-à-dire tout ce qu'il
gagnera *ensuite* :

```
G_t = r_{t+1} + γ·r_{t+2} + γ²·r_{t+3} + γ³·r_{t+4} + ...
```

γ (gamma) pondère l'avenir :

- **γ = 0** → agent totalement myope, ne regarde que le pas suivant ;
- **γ = 0.9** → une récompense dans 10 pas compte pour `0.9¹⁰ ≈ 0.35` ;
- **γ = 0.99** → l'agent planifie très loin, mais apprend plus lentement ;
- **γ = 1** → pas d'escompte ; possible seulement parce que les épisodes
  se terminent, mais rend l'apprentissage instable.

Pour Snake, `γ` entre **0.9 et 0.95** est le bon compromis : assez pour viser
une pomme à cinq cases, pas assez pour se noyer dans du bruit lointain.

---

## 5. La fonction Q et l'équation de Bellman

### Définition

`Q(s, a)` = « quelle est la qualité de faire l'action `a` quand je suis dans
l'état `s`, si ensuite je joue au mieux ? »

Formellement, c'est l'espérance du retour :

```
Q(s, a) = E[ G_t | s_t = s, a_t = a ]
```

Si on connaissait `Q` parfaitement, jouer optimalement serait trivial : dans
chaque état, prendre l'action de plus grande valeur.

```
π*(s) = argmax_a Q*(s, a)
```

**Tout le projet consiste à estimer cette fonction Q.**

### L'équation de Bellman

La valeur optimale d'un couple `(s, a)` se décompose en deux morceaux : ce
qu'on gagne tout de suite, plus la valeur escomptée du meilleur coup depuis
l'état suivant.

```
Q*(s, a) = E[ r + γ · max_{a'} Q*(s', a') ]
             └─┬─┘   └──────────┬────────┘
          immédiat        meilleur futur
```

C'est une équation **récursive** : la valeur d'un état dépend de celle des
états suivants. On ne peut pas la résoudre directement (on ne connaît ni les
probabilités de transition, ni les récompenses à l'avance), mais on peut
l'approcher par itérations successives — c'est exactement ce que fait le
Q-learning.

### Pourquoi une table

`Q` est une fonction de deux arguments. Si le nombre d'états est fini et
raisonnable, on peut simplement la **tabuler** : un dictionnaire
`état -> [q_haut, q_gauche, q_bas, q_droite]`.

```python
qtable = {
    ("W1", "0>3", "G2", "S1"): [-12.4,  3.1,  18.7, -85.0],
    ...
}
```

C'est la solution retenue ici, et elle est parfaitement légitime : le sujet
autorise explicitement « des valeurs Q dans une table Q ». Ses avantages sont
énormes en contexte 42 : c'est exact (pas d'approximation), rapide, lisible
dans un fichier texte, débogable à la main, et défendable en trente secondes
en soutenance.

---

## 6. Le Q-learning, ligne par ligne

### La règle de mise à jour

C'est **la** formule à savoir par cœur :

```
Q(s, a) ← Q(s, a) + α · [ r + γ · max_{a'} Q(s', a') − Q(s, a) ]
                          └──────────┬──────────┘   └───┬───┘
                              cible (ce qu'on           estimation
                              pense maintenant)          actuelle
```

Décortiquons chaque morceau.

| Symbole | Nom | Rôle |
|---|---|---|
| `Q(s,a)` | estimation actuelle | ce que l'agent croyait jusqu'ici |
| `r` | récompense observée | le retour immédiat du plateau |
| `max_a' Q(s',a')` | valeur du meilleur coup suivant | la promesse du futur |
| `r + γ·max…` | **cible** | une meilleure estimation, car elle contient une vraie observation `r` |
| `cible − Q(s,a)` | **erreur de différence temporelle** (TD error, notée δ) | de combien on s'était trompé |
| `α` | taux d'apprentissage | quelle fraction de l'erreur on corrige |

En français : *« j'avais estimé la valeur de ce coup ; en le jouant j'ai
observé une récompense réelle et j'ai vu où j'atterrissais ; je corrige mon
estimation d'une fraction α de mon erreur. »*

### Pourquoi ça converge

La cible `r + γ·max Q(s',a')` est *partiellement vraie* : elle contient une
observation réelle (`r`) et une estimation (`max Q(s',·)`). À chaque mise à
jour, un peu de vérité s'infiltre. Cette vérité se propage ensuite **à
rebours** : d'abord les états juste avant une pomme, puis ceux d'avant, etc.

C'est pour cela qu'au début de l'entraînement le serpent semble ne rien
apprendre pendant des centaines d'épisodes, puis progresse brusquement :
l'information doit d'abord remonter la chaîne des états.

### Off-policy

Le `max` porte sur **la meilleure action possible**, pas sur celle qu'on a
réellement jouée. C'est ce qui rend le Q-learning **off-policy** : il apprend
la politique optimale même quand il explore au hasard. Conséquence pratique :
on peut explorer agressivement sans polluer ce qu'on apprend.

### Pseudo-code d'un épisode

```
initialiser la table Q (vide, valeurs à 0)
pour chaque session :
    réinitialiser le plateau
    s = encoder(vision)
    tant que le serpent est vivant :
        a = choisir_action(s)              # ε-greedy, cf. §8
        evenement = plateau.step(a)
        r = recompense(evenement)
        s' = encoder(nouvelle vision)
        fini = (le serpent est mort)

        si apprentissage activé :
            cible = r  si fini
                    r + γ · max(Q[s'])  sinon
            Q[s][a] += α · (cible − Q[s][a])

        s = s'
    faire décroître ε
```

Trois détails qui font la différence entre un agent qui apprend et un qui
stagne :

1. **`cible = r` quand l'épisode se termine.** Il n'y a pas d'état suivant ;
   ajouter `γ·max Q(s')` reviendrait à créditer une valeur imaginaire à un
   serpent mort. C'est le bug numéro un.
2. **Un état inconnu vaut 0 sur les 4 actions**, pas une valeur aléatoire.
3. **Les égalités se tranchent au hasard.** Une table vide donne quatre zéros ;
   un `max` naïf renverrait toujours la première action et le serpent
   partirait éternellement vers le haut. Tirez au sort parmi les ex æquo.

---

## 7. Modéliser Snake : état, actions, récompenses

C'est ici que se joue la réussite du projet. Le Q-learning est une recette de
dix lignes ; la modélisation, elle, décide de tout.

### 7.1 Les actions

Quatre, imposées : HAUT, GAUCHE, BAS, DROITE, dans cet ordre dans
`board.DIRECTIONS`. L'indice dans ce tuple sert d'indice dans le vecteur de
valeurs Q. Rien de plus à décider.

Note : le demi-tour immédiat n'est pas interdit par le sujet — il provoque une
collision avec le cou, donc la mort. L'agent doit l'apprendre, et il
l'apprendra vite (grosse pénalité, état très reconnaissable). L'interdire en
dur simplifierait, mais retire une partie de l'apprentissage.

### 7.2 L'état : le choix décisif

L'agent reçoit `board.vision_chars()`, soit quatre chaînes de symboles :

```
W = mur    H = tête    S = corps    G = pomme verte    R = pomme rouge    0 = vide
```

Par exemple, une vision `{HAUT: "00G00W", DROITE: "S0W", ...}` signifie :
au-dessus, deux cases vides puis une pomme verte ; à droite, mon propre corps
juste à côté.

**Interdiction absolue** : ne transmettez rien d'autre à l'agent. Pas la
taille du plateau, pas la longueur du serpent, pas sa position absolue, pas
le nombre de pas écoulés. Le sujet sanctionne d'un `-42`.

#### Option A — la vision brute

Utiliser la concaténation des quatre chaînes comme clé.

- Nombre d'états : la croix de vision compte **18 cases** au total sur un
  plateau 10×10 — les quatre rayons se partagent une ligne et une colonne, ils
  ne peuvent pas faire 9 cases chacun simultanément. Chacune peut valoir
  4 symboles utiles (`S`, `G`, `R`, `0` — `W` n'apparaît qu'au bout du rayon,
  `H` seulement au centre), soit une borne de `4¹⁸ ≈ 6,9·10¹⁰` (et non `5³⁶`,
  qui surestime d'un facteur supérieur à 10¹⁴). Voir `IA.md` §6.2.
- Verdict : **inutilisable**. La table ne se remplira jamais ; l'agent
  rencontrera presque toujours un état inédit. Et une table entraînée en
  10×10 serait inexploitable en 20×20.

#### Option B — symbole le plus proche + distance (recommandée)

Pour chaque direction, on retient deux informations : le **premier symbole
non vide** rencontré, et sa **distance plafonnée**.

```
HAUT   : "00G00W"  ->  ('G', 3)
DROITE : "S0W"     ->  ('S', 1)
BAS    : "000W"    ->  ('W', 3+)   # plafonné
GAUCHE : "0R0W"    ->  ('R', 2)
```

- Symboles possibles en première position : `W`, `S`, `G`, `R` — 4 valeurs
  (`0` est exclu par construction, `H` est la tête elle-même).
- Distances : `1`, `2`, `3 ou plus` — 3 valeurs.
- Par direction : `4 × 3 = 12` combinaisons. Sur quatre directions :
  **12⁴ = 20 736 états au maximum**, et en pratique beaucoup moins, car
  toutes les combinaisons ne se produisent pas.

C'est le bon équilibre : assez riche pour distinguer « pomme à une case » de
« pomme à cinq cases », assez compact pour être appris en quelques milliers de
sessions. **Et il ne dépend pas de la taille du plateau** — le même modèle
fonctionne en 10×10 comme en 20×20, ce qui valide le bonus « taille variable ».

Limite connue : si une pomme rouge est devant une pomme verte sur le même
rayon, seule la rouge est vue. On peut enrichir avec un booléen « une verte
existe-t-elle plus loin sur ce rayon ? » — la table passe alors à `24⁴`,
toujours praticable.

#### Option C — encodage binaire

Trois booléens par direction : `danger immédiat ?`, `pomme verte visible ?`,
`pomme rouge immédiate ?` → `2¹² = 4 096` états.

Apprend très vite (la table se remplit en quelques centaines de sessions),
mais l'agent est aveugle aux distances : il ne sait pas choisir entre une
pomme à deux cases et une à sept. Excellent choix pour un **premier
prototype qui marche en une soirée**, à raffiner ensuite.

#### Récapitulatif

| Option | États | Vitesse d'apprentissage | Plafond de performance |
|---|---|---|---|
| A — vision brute | ~7·10¹⁰ | jamais | nul |
| B — symbole + distance | ~2·10⁴ | quelques milliers de sessions | élevé |
| C — binaire | 4 096 | quelques centaines | moyen |

**Stratégie conseillée** : implémentez C d'abord pour valider toute la chaîne
(récompenses, boucle, sauvegarde), puis passez à B en ne changeant *que* la
fonction d'encodage. C'est une fonction pure de quelques lignes ; tout le
reste du code est inchangé.

### 7.3 Les récompenses

Le sujet les laisse libres. Une base saine :

| Événement | Récompense | Pourquoi |
|---|---|---|
| pomme verte | **+20** | l'objectif principal |
| pomme rouge | **−20** | perdre une case est coûteux |
| mort (mur, queue, longueur nulle) | **−100** | doit dominer tout le reste |
| pas ordinaire | **−1** | pousse à ne pas tourner en rond |

Trois principes :

1. **La mort doit être la pire issue, de loin.** Si mourir coûte −10 et qu'une
   pomme rapporte +20, un agent peut trouver rentable de foncer dans le mur
   pour « recommencer » une partie plus favorable.
2. **Le petit coût par pas est essentiel.** Sans lui, faire des ronds
   indéfiniment a un retour nul, ce qui est mieux que de risquer une mort :
   l'agent apprend à ne rien faire.
3. **Les ordres de grandeur comptent plus que les valeurs exactes.** `+20/−100`
   ou `+10/−50` donnent des comportements très proches. Ne passez pas trois
   jours à peaufiner ; passez-les sur l'encodage de l'état.

#### Le reward shaping

Technique optionnelle mais efficace : donner un petit bonus quand la distance
à la pomme verte visible diminue, un petit malus quand elle augmente
(typiquement ±1). L'agent reçoit alors un signal à *chaque* pas au lieu
d'attendre la pomme, et apprend nettement plus vite.

C'est **légal** ici : l'information (la distance sur un rayon) fait partie de
la vision. Attention toutefois — si le bonus de rapprochement dépasse la
valeur de la pomme elle-même, l'agent peut apprendre à osciller devant la
pomme sans jamais la manger, pour encaisser le bonus en boucle. Gardez le
shaping petit devant la récompense terminale.

#### La boucle infinie

Un agent peut apprendre à survivre sans jamais manger — c'est un optimum
local parfaitement rationnel si mourir coûte très cher. Un compteur de pas
depuis la dernière pomme arrête la partie au-delà d'une limite.

Ce garde-fou est implémenté dans **`src/environment/board.py`** (`IDLE_FACTOR`,
`idle_limit`, `_truncate`), et la valeur retenue est **`4 × taille²`** — voir
`IA.md` §7.5 pour la mesure qui justifie de la lier à l'aire du plateau et non
à la longueur du serpent.

---

## 8. Exploration contre exploitation

Un agent qui joue toujours son meilleur coup connu ne découvre jamais mieux.
Un agent qui joue toujours au hasard n'exploite jamais ce qu'il sait. Il faut
doser.

### ε-greedy

```
avec probabilité ε   : action au hasard parmi les 4
sinon                : argmax_a Q(s, a)
```

### La décroissance de ε

C'est le réglage qui change le plus visiblement les résultats.

```
ε = 1.0                    au tout début : exploration pure
ε ← max(ε_min, ε × 0.995)  après chaque session
ε_min = 0.01               un fond d'exploration permanent
```

Avec `0.995`, ε passe de 1.0 à 0.01 en environ 900 sessions — l'agent explore
massivement au début, puis exploite. Décroissance trop rapide : il se fige sur
une stratégie médiocre. Trop lente : il joue au hasard pendant des dizaines de
milliers de sessions.

**En mode `-dontlearn`, forcez ε = 0** : on évalue un modèle, on ne veut aucun
bruit.

### Alternatives

| Méthode | Idée | Quand |
|---|---|---|
| **ε-greedy décroissant** | ci-dessus | par défaut, toujours |
| **Softmax / Boltzmann** | probabilité ∝ `exp(Q(s,a)/τ)` | explore proportionnellement à la qualité, plus fin mais un paramètre de plus |
| **Initialisation optimiste** | initialiser Q à `+5` au lieu de `0` | tout état non testé paraît attirant : l'exploration devient automatique, sans ε |
| **UCB** | bonus aux actions peu essayées | élégant, rarement nécessaire ici |

---

## 9. Les hyperparamètres

| Paramètre | Symbole | Plage utile | Effet si trop grand | Effet si trop petit |
|---|---|---|---|---|
| Taux d'apprentissage | α | 0.05 – 0.3 | oscille, ne converge pas | apprend au ralenti |
| Facteur d'escompte | γ | 0.9 – 0.95 | myopie inversée : bruit lointain | agent myope, ignore les pommes éloignées |
| Exploration | ε | 1.0 → 0.01 | joue au hasard indéfiniment | se fige sur une stratégie médiocre |
| Décroissance de ε | — | 0.995 – 0.9995 | — | — |

**Point de départ conseillé** : `α = 0.1`, `γ = 0.9`, `ε₀ = 1.0`,
`ε_decay = 0.995`, `ε_min = 0.01`.

Changez **un seul paramètre à la fois** et comparez sur le même nombre de
sessions avec la même graine (`-seed`). Sinon vous ne saurez jamais ce qui a
produit l'amélioration.

Astuce : un α décroissant (`α = 1/(1+visites(s,a))`) donne une convergence
théoriquement garantie, mais un α constant s'adapte mieux à un environnement
où le plateau change à chaque partie.

---

## 10. Les variantes de mise à jour

Le sujet dit explicitement : *« Vous pouvez entraîner plusieurs modèles en
utilisant différentes méthodes de mise à jour de la fonction Q. »* C'est une
invitation directe à en implémenter plusieurs — et c'est un excellent sujet de
discussion en soutenance.

### 10.1 Q-learning (la base, off-policy)

```
Q(s,a) ← Q(s,a) + α [ r + γ · max_{a'} Q(s',a') − Q(s,a) ]
```

Apprend la politique optimale indépendamment de la façon dont il explore.
Tendance à **surestimer** les valeurs (le `max` sur des estimations bruitées
sélectionne systématiquement le bruit favorable).

### 10.2 SARSA (on-policy)

```
Q(s,a) ← Q(s,a) + α [ r + γ · Q(s',a') − Q(s,a) ]
```

Une seule différence : `a'` est **l'action réellement choisie** au pas suivant
(y compris si c'était un coup d'exploration), au lieu du meilleur coup
théorique. Il faut donc choisir `a'` *avant* de faire la mise à jour — d'où le
nom : **S**tate, **A**ction, **R**eward, **S**tate, **A**ction.

Conséquence concrète : SARSA apprend une politique **prudente**. Comme il
intègre le risque de ses propres coups d'exploration, il se tient à distance
des murs. Q-learning apprend le chemin optimal en supposant qu'il ne fera
jamais d'erreur, et longe donc les parois.

**Coût d'implémentation : trois lignes.** C'est la deuxième méthode à faire, sans
discussion.

### 10.3 Expected SARSA

```
Q(s,a) ← Q(s,a) + α [ r + γ · Σ_{a'} π(a'|s')·Q(s',a') − Q(s,a) ]
```

Au lieu de tirer une action et d'utiliser sa valeur, on prend l'**espérance**
sur toutes les actions selon la politique ε-greedy. Moins de variance que
SARSA, souvent un peu meilleur, pour un coût de quelques lignes de plus.

### 10.4 Double Q-learning

Deux tables `Q₁` et `Q₂`. À chaque pas, on en tire une au hasard :

```
si Q1 est tirée :
    a* = argmax_{a'} Q1(s', a')
    Q1(s,a) ← Q1(s,a) + α [ r + γ · Q2(s', a*) − Q1(s,a) ]
sinon : symétrique
```

L'une **choisit** la meilleure action, l'autre **l'évalue**. Cela découple la
sélection de l'évaluation et supprime le biais de surestimation. Décision :
`argmax` sur `Q₁ + Q₂`. Sauvegarde : les deux tables dans le même fichier.

**Coût : une dizaine de lignes.** Bon rapport bénéfice/effort, et impressionne
en soutenance parce que peu de gens le font.

### 10.5 Monte-Carlo

On ne met rien à jour pendant la partie. À la fin, on recalcule le retour réel
de chaque couple visité et on corrige :

```
G = 0
pour chaque (s, a, r) de l'épisode, parcouru À L'ENVERS :
    G = r + γ · G
    Q(s,a) ← Q(s,a) + α · (G − Q(s,a))
```

Avantage : la cible est le **vrai** retour observé, sans estimation
intermédiaire — aucun biais. Inconvénient : **variance énorme**, et aucun
apprentissage avant la fin de l'épisode. Sur Snake, où les épisodes peuvent
durer des centaines de pas et où le hasard des pommes est fort, Monte-Carlo
converge nettement plus lentement que le Q-learning.

**Verdict : à faire pour la comparaison pédagogique, pas pour produire votre
meilleur modèle.**

### 10.6 Q(λ) — traces d'éligibilité

Le pont entre Monte-Carlo (λ = 1) et le Q-learning (λ = 0). On garde une
« trace » `e(s,a)` de chaque couple récemment visité, et on propage l'erreur
TD à *tous* les couples récents d'un coup :

```
δ = r + γ · max_{a'} Q(s',a') − Q(s,a)
e(s,a) += 1
pour tous les couples (x, u) avec une trace :
    Q(x,u) += α · δ · e(x,u)
    e(x,u) *= γ · λ
```

L'information remonte la chaîne des états **en un seul pas** au lieu d'attendre
autant d'épisodes qu'il y a d'états. C'est mesurablement plus rapide.

Prix à payer : c'est la variante la plus délicate à écrire correctement
(quand remettre les traces à zéro après un coup exploratoire ? traces
« accumulantes » ou « remplaçantes » ?), et un bug y est difficile à
diagnostiquer.

**Verdict : en dernier, si tout le reste marche.**

### 10.7 Que choisir

| Méthode | Effort | Bénéfice | Priorité |
|---|---|---|---|
| **Q-learning** | — | la base | **1 — obligatoire** |
| **SARSA** | 3 lignes | politique prudente, contraste on/off-policy | **2 — à faire** |
| **Double Q-learning** | ~10 lignes | supprime la surestimation | **3 — recommandé** |
| Expected SARSA | ~5 lignes | variance réduite | 4 — optionnel |
| Monte-Carlo | ~15 lignes | comparaison pédagogique | 5 — optionnel |
| Q(λ) | ~30 lignes délicates | convergence plus rapide | 6 — si temps |

**Le plan de bataille** : faites marcher Q-learning seul jusqu'à ce que le
serpent dépasse une longueur de 10. Ne touchez à rien d'autre avant. Ensuite,
ajoutez SARSA et Double Q — ils partagent tout sauf trois lignes, donc
factorisez : une classe de base qui gère la table, le choix d'action, la
sauvegarde, et une méthode `update()` redéfinie par chaque variante.

Vous rendrez alors des modèles du type `models/1000sess_qlearning.txt`,
`models/1000sess_sarsa.txt`, `models/1000sess_doubleq.txt` — et vous pourrez
comparer leurs statistiques, ce qui est exactement ce que le sujet attend.

---

## 11. Les réseaux de neurones

Le sujet autorise de remplacer la table par un réseau. Voici de quoi le
comprendre, et pourquoi ce n'est probablement pas ce que vous devriez faire.

### 11.1 Le problème que ça résout

Une table Q ne sait rien généraliser. Si elle a appris que
`('G', 2)` en haut est bon, elle n'en déduit **rien** pour `('G', 3)` en haut :
c'est une autre clé, apprise indépendamment. Avec 20 000 états c'est
acceptable. Avec des millions — ou avec des états continus, comme des pixels —
c'est impossible.

Un réseau de neurones est un **approximateur de fonction** : il apprend une
fonction lisse `Q(s, a; θ)` paramétrée par des poids `θ`. Des états proches
donnent des sorties proches — donc il généralise.

### 11.2 Ce qu'est un réseau, en trois phrases

Un neurone calcule une somme pondérée de ses entrées, ajoute un biais, et
passe le résultat dans une fonction non linéaire :

```
sortie = f( w₁·x₁ + w₂·x₂ + ... + wₙ·xₙ + b )     avec f = ReLU, tanh, ...
```

Une **couche** est un paquet de neurones en parallèle ; un **réseau** est un
empilement de couches. Pour Snake, l'architecture typique serait :

```
entrée : vecteur binaire de la vision (par ex. 12 valeurs)
   ↓  couche dense 128 neurones + ReLU
   ↓  couche dense 128 neurones + ReLU
sortie : 4 valeurs = Q(s, HAUT), Q(s, GAUCHE), Q(s, BAS), Q(s, DROITE)
```

L'apprentissage se fait par **descente de gradient** : on définit une erreur
(ici, l'écart au carré entre la prédiction et la cible du Q-learning), on
calcule sa dérivée par rapport à chaque poids (rétropropagation), et on
déplace chaque poids un peu dans la direction qui réduit l'erreur.

### 11.3 DQN

Remplacer naïvement la table par un réseau **diverge**. Deux astuces l'ont
rendu viable (DeepMind, 2015) :

1. **Replay buffer** — on stocke les transitions `(s, a, r, s', fini)` dans une
   mémoire de quelques dizaines de milliers d'entrées, et on entraîne sur des
   mini-lots tirés au hasard. Cela casse la corrélation entre échantillons
   successifs, qui déstabilise la descente de gradient.
2. **Réseau cible** — on garde une copie figée `θ⁻` du réseau pour calculer la
   cible, copiée depuis le réseau principal toutes les N étapes. Sans cela, la
   cible bouge à chaque mise à jour et le réseau « court après sa propre
   queue ».

La perte minimisée :

```
L(θ) = E[ ( r + γ · max_{a'} Q(s', a'; θ⁻) − Q(s, a; θ) )² ]
```

### 11.4 Pourquoi ne pas le faire ici

| Critère | Table Q | DQN |
|---|---|---|
| Dépendances | aucune | PyTorch ou TensorFlow |
| Temps d'entraînement | secondes à minutes | dizaines de minutes à heures |
| Stabilité | déterministe | sensible à l'initialisation, aux seeds |
| Fichier modèle | texte lisible, inspectable | poids binaires opaques |
| Débogage | on lit la table | on regarde des courbes en priant |
| Défense en soutenance | on montre les valeurs Q d'un état | il faut expliquer la rétropropagation |
| Suffisant pour longueur 10+ | **oui** | oui |

L'espace d'états de ce projet, correctement encodé, fait quelques dizaines de
milliers d'entrées. **Une table le couvre entièrement.** Le réseau résout un
problème que vous n'avez pas.

Faites-le seulement si votre objectif personnel est d'apprendre le deep RL —
auquel cas gardez la table comme référence pour comparer, et documentez les
deux. Sinon, le temps est bien mieux investi dans l'encodage de l'état et le
reward shaping.

---

# PASSER À LA PRATIQUE

## 12. Plan d'implémentation

Étape par étape, chaque étape étant vérifiable avant de passer à la suivante.

### Étape 1 — l'encodage de l'état

Créez `src/agent/state.py` avec une unique fonction pure :

```
encode(vision) -> clé hashable
```

Commencez par l'option C (binaire), ou directement B si vous êtes à l'aise.

**Vérification** : affichez l'état encodé à chaque pas à côté de la croix de
vision affichée par le jeu, et confrontez-les à la main sur une dizaine de
pas. Un encodage faux est invisible plus tard — il donne juste un agent qui
n'apprend pas, sans message d'erreur.

### Étape 2 — les récompenses

Une fonction `reward(evenement) -> float` avec le barème du §7.3. Le mapping
des événements (`"green"`, `"red"`, `"wall"`, `"body"`, `"starve"`, `"move"`)
est déjà fourni par `board.step()`.

### Étape 3 — l'agent

`src/agent/qlearning.py` avec :

- `qtable` : un `dict` de clé d'état vers liste de 4 flottants ;
- `choose(vision)` : ε-greedy, égalités tranchées au hasard ;
- `learn(vision, action, reward, next_vision, done)` : la règle du §6, avec le
  cas `done` traité à part ;
- `save(path)` / `load(path)` ;
- un attribut `learning` que `-dontlearn` met à `False` (et qui force ε = 0).

**Vérification** : après 100 sessions, `len(agent.qtable)` doit être de l'ordre
de plusieurs centaines. Si c'est 3, votre encodage écrase tout. Si c'est
50 000 après 100 sessions, il est trop fin.

### Étape 4 — le format du fichier modèle

Un seul fichier, comme l'exige le sujet. Suggestion de format texte lisible :

```
# learn2slither v1
# method=qlearning alpha=0.1 gamma=0.9 epsilon=0.01 sessions=1000
W1,S2,G3,03|-85.231000,12.400000,3.100000,-1.220000
...
```

Un en-tête commenté avec les hyperparamètres et le nombre de sessions, puis
une ligne par état. Le `.txt` est explicitement cité par le sujet, et un
fichier lisible vous sauvera en debug comme en soutenance.

**Vérification** : `save` puis `load` puis `save` à nouveau doit produire deux
fichiers **identiques** (`diff` doit être vide).

### Étape 5 — l'entraînement

```bash
./snake -sessions 1     -save models/1sess.txt    -visual off
./snake -sessions 10    -save models/10sess.txt   -visual off
./snake -sessions 100   -save models/100sess.txt  -visual off
./snake -sessions 10000 -save models/10000sess.txt -visual off
```

Les trois premiers sont exigés par le sujet. Le quatrième est celui que vous
montrerez.

Deux façons de produire les modèles intermédiaires : soit quatre runs
indépendantes, soit une run longue qui sauvegarde à des paliers — la seconde
est plus cohérente pédagogiquement, car elle montre *le même* agent qui
progresse.

### Étape 6 — l'évaluation

```bash
./snake -visual on -load models/10000sess.txt -sessions 10 -dontlearn
```

C'est exactement la commande que l'examinateur tapera. Vérifiez qu'elle
fonctionne, que ε vaut bien 0, que la table n'est pas modifiée, et que la
longueur atteinte dépasse 10.

### Étape 7 — les variantes

Factorisez : une classe de base qui gère table, choix d'action et
persistance ; une méthode `update()` redéfinie par Q-learning, SARSA et
Double Q. Entraînez un modèle par méthode avec le **même nombre de sessions et
la même graine**, et comparez.

---

## 13. Diagnostiquer un agent qui n'apprend pas

Instrumentez d'abord. Sans ces chiffres, vous devinez.

À logger toutes les 100 sessions : longueur maximale, longueur moyenne, durée
moyenne, valeur de ε, **taille de la table Q**, et la répartition des causes de
mort (mur / queue / longueur nulle / boucle).

| Symptôme | Cause probable | Correctif |
|---|---|---|
| Le serpent va toujours dans la même direction | égalités du `max` non tranchées au hasard | tirer au sort parmi les ex æquo |
| La table a 3 entrées après 1000 sessions | encodage qui écrase tout | vérifier `encode()` à la main |
| La table a 500 000 entrées | encodage trop fin | plafonner les distances, réduire les symboles |
| Progresse puis s'effondre | α trop grand, ou `γ·max Q(s')` ajouté sur un état terminal | α → 0.05 ; traiter `done` |
| Bloqué à une longueur de 4-5 | γ trop bas, ou pas de récompense de rapprochement | γ → 0.95, ajouter du shaping |
| Tourne en rond sans manger | pas de coût par pas | ajouter `−1` par pas |
| Meurt toujours contre le mur | pénalité de mort trop faible | mort à `−100` |
| Bon pendant l'entraînement, nul en `-dontlearn` | ε non remis à 0, ou modèle mal rechargé | vérifier `load` avec un `diff` |
| Aucune amélioration, ε déjà à 0.01 | décroissance trop rapide | `ε_decay = 0.999` |

**Le test qui tranche** : entraînez avec `-seed 42`, deux fois. Vous devez
obtenir exactement les mêmes chiffres. Sinon, une source d'aléa non contrôlée
traîne dans votre code, et toutes vos comparaisons sont sans valeur.

---

## 14. Pièges du sujet et checklist de soutenance

### Les pièges

1. **Le `-42`.** Vérifiez ligne par ligne que votre fonction `encode()` ne
   reçoit que `board.vision_chars()`. Pas de `board.size`, pas de
   `len(board.snake)`, pas de position absolue. Un examinateur lira cette
   fonction en priorité.
2. **Le crash = 0.** Le programme ne doit jamais planter : fichier de modèle
   absent ou corrompu, `-sessions 0`, plateau minuscule, fermeture de fenêtre
   en pleine partie. Testez ces cas.
3. **Le mode pas à pas et la vitesse lisible sont obligatoires**, pas des
   bonus.
4. **La sortie terminal est obligatoire** : la croix de vision et l'action à
   chaque pas, comme dans la figure du sujet.
5. **Trois modèles minimum** : 1, 10 et 100 sessions. Ils doivent montrer une
   progression.
6. **Le dépôt doit être clonable et fonctionner** dans un répertoire vide.
   `.venv/` est ignoré par git : documentez la commande d'installation.

### La checklist

- [ ] `flake8 main.py src/ tests/` sans erreur
- [ ] `python -m unittest discover -s tests -t .` — tous les tests passent
- [ ] `git clone` dans un dossier vide, installation, lancement — ça marche
- [ ] plateau 10×10, 2 pommes vertes, 1 rouge, serpent de 3 cases
- [ ] mort : mur, queue, longueur nulle
- [ ] vision affichée dans le terminal à chaque pas
- [ ] les 4 actions, décidées uniquement à partir de la vision
- [ ] fonction Q sous forme de table (ou de réseau)
- [ ] `-sessions`, `-save`, `-load`, `-visual on|off`, `-dontlearn`, `-step-by-step`
- [ ] `models/` contient au moins 1, 10 et 100 sessions
- [ ] un modèle atteint une longueur ≥ 10 en `-dontlearn`
- [ ] vitesse d'affichage configurable, dont une lisible par un humain
- [ ] mode pas à pas fonctionnel
- [ ] **bonus** : lobby, panneau de configuration, statistiques
- [ ] **bonus** : taille de plateau variable, avec le *même* modèle entraîné

---

## 15. Glossaire

| Terme | Définition |
|---|---|
| **Action** | l'un des 4 déplacements possibles |
| **Agent** | l'entité qui décide de l'action |
| **α (alpha)** | taux d'apprentissage : fraction de l'erreur corrigée à chaque mise à jour |
| **Bellman (équation de)** | relation récursive entre la valeur d'un état et celle de ses successeurs |
| **Épisode** | une partie complète, du début à la mort |
| **ε (epsilon)** | probabilité de jouer au hasard plutôt qu'au mieux |
| **État** | ce que l'agent perçoit — ici, la vision sur 4 directions |
| **γ (gamma)** | facteur d'escompte : poids accordé aux récompenses futures |
| **Greedy** | qui choisit systématiquement la valeur maximale |
| **Off-policy** | apprend la politique optimale même en explorant (Q-learning) |
| **On-policy** | apprend la politique effectivement suivie (SARSA) |
| **Politique (π)** | la règle qui associe une action à un état |
| **Q(s,a)** | qualité estimée de l'action `a` dans l'état `s` |
| **Récompense** | le nombre renvoyé par l'environnement après une action |
| **Retour (G)** | somme escomptée des récompenses futures |
| **Reward shaping** | récompenses intermédiaires ajoutées pour guider l'apprentissage |
| **TD error (δ)** | `cible − estimation` : de combien l'agent s'était trompé |
| **Trace d'éligibilité** | mémoire des couples récemment visités, pour propager δ en arrière |

---

## Références

- Sutton & Barto, *Reinforcement Learning: An Introduction* (2ᵉ édition) —
  la référence du domaine, librement disponible en ligne. Chapitre 6 pour le
  Q-learning et SARSA, chapitre 12 pour les traces d'éligibilité.
- Mnih et al., *Human-level control through deep reinforcement learning*,
  Nature 2015 — l'article fondateur de DQN.
- `sujet/fr.subject.pdf` — le sujet officiel, qui prime sur ce document en cas
  de désaccord.
