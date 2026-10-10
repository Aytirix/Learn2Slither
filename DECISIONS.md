# Learn2Slither — le code et ses décisions

Ce document décrit le code tel qu'il est : ce que fait chaque partie, et pourquoi elle est faite ainsi. Les chemins sont relatifs à la racine du dépôt.

---

## 1. Vue d'ensemble

```
main.py                 point d'entrée (./snake le lance avec le bon Python)
src/
  cli.py                options de la ligne de commande
  config.py             GameConfig : réglages partagés par le CLI, le lobby, le jeu
  graine.py             une graine par partie
  session.py            boucle sans affichage (-visual off) + statistiques
  training.py           entraînement par tranches (menu ENTRAINEMENT)
  evaluation.py         bilan d'évaluation + photos pour le rejeu
  models.py             liste des modèles du dossier models/
  baselines.py          agent aléatoire de référence
  environment/
    board.py            plateau, pommes, collisions, vision
    rewards.py          barème des récompenses
  agent/
    interpreter.py      vision brute -> état compact
    qtable.py           la table Q
    agent.py            choix des actions et apprentissage
    modele.py           sauvegarde / chargement d'un modèle
    fabrique.py         crée l'agent demandé par la configuration
  interface/            tout l'affichage pygame (menus, partie, panneau…)
models/                 modèles entraînés (1, 10, 100, 1000 parties, infini)
tests/                  tests unittest
```

### Un pas de jeu, du début à la fin

```
board.vision_chars()          la croix vue depuis la tête (4 chaînes)
   -> agent.choose(vision)    encode l'état, choisit, renvoie UP/LEFT/DOWN/RIGHT
   -> board.step(direction)   déplace le serpent, renvoie l'événement
   -> recompense(event)       l'environnement donne la récompense
   -> agent.learn(...)        l'agent NOTE le pas
fin de partie -> agent.fin_partie()   l'agent apprend toute la partie
```

Le même contrat sert partout : boucle sans affichage (`session.py`), entraînement en fenêtre (`training.py`) et partie affichée (`interface/game.py`).

---

## 2. L'environnement (`src/environment/board.py`)

### Le plateau
- 10×10 par défaut, 2 pommes vertes, 1 rouge, serpent de 3 cases. C'est ce qu'impose le sujet.
- La taille est réglable de 5 à 50 (bonus). En dessous de 3, `Board` refuse, sinon `_spawn_snake` chercherait sans fin 3 cases alignées.
- **Départ :** le serpent est posé au hasard, 3 cases contiguës et alignées, entièrement sur le plateau. Sa direction de départ est celle du cou vers la tête.
- **Pommes :** chacune apparaît sur une case libre tirée au hasard. Une pomme mangée est remplacée tout de suite.

### Ce qui se passe à chaque pas (`step`)
| Cas | Effet | Événement |
|---|---|---|
| sortie du plateau | mort | `WALL` |
| pomme verte | +1 case | `GREEN` |
| pomme rouge | −1 case ; à 0 case, mort | `RED` / `STARVE` |
| case vide | le serpent avance | `MOVE` |
| tête sur le corps | mort | `BODY` |

### La troncature : arrêter sans tuer
- Une partie qui tourne en rond est arrêtée après `IDLE_FACTOR × aire` pas sans pomme, soit 4 × 100 = 400 pas sur un plateau 10×10.
- **Limite proportionnelle à l'aire**, et non à la longueur : c'est l'aire qui fixe le temps nécessaire pour trouver une pomme, puisque le serpent ne voit une pomme que sur sa ligne ou sa colonne.
- **Une troncature n'est pas une mort.** `truncate()` met `alive = False` et `truncated = True`, avec la cause `TIMEOUT`. Deux conséquences :
  - `board.dead` reste faux : l'agent continue d'estimer la suite (bootstrap). Sinon il apprendrait que vivre longtemps tue.
  - L'événement du pas n'est pas modifié : le dernier pas reste un `MOVE` qui coûte −1. Sinon la limite deviendrait une récompense.
- **Il y a donc deux notions séparées :**
  - `event` (ce qui est arrivé) détermine la **récompense** ;
  - `board.dead` (y a-t-il un après ?) détermine le **bootstrap**.

### La vision
- `vision_chars()` renvoie, pour chacune des 4 directions, la chaîne des cases vues depuis la tête jusqu'au mur compris. Exemple : `{UP: "0GW", LEFT: "SSW", …}`.
- Symboles : `W` mur, `H` tête, `S` corps, `G` vert, `R` rouge, `0` vide.
- **C'est la seule information transmise à l'agent.** Le sujet sanctionne toute autre information.
- `vision_lines()` dessine la même croix pour le terminal.

---

## 3. Les récompenses (`src/environment/rewards.py`)

| Événement | Récompense | Pourquoi |
|---|---|---|
| `MOVE` | −1 | chaque pas coûte : tourner en rond n'est pas gratuit |
| `GREEN` | +20 | l'objectif |
| `RED` | −10 | à éviter, sans être aussi grave qu'une mort |
| `WALL`, `BODY`, `STARVE` | −50 | la fin de partie, le pire |

- C'est l'environnement qui récompense, comme le demande le sujet (« rewards granted by the environment »).
- Un événement absent du barème lève `KeyError` : une erreur visible vaut mieux qu'une récompense inventée sans rien dire.

---

## 4. L'IA

### 4.1 L'état : compresser la vision (`src/agent/interpreter.py`)
La vision brute a beaucoup trop de combinaisons pour une table. Chaque rayon est donc réduit à **deux informations** : la première chose vue, et sa distance.

```
"S0W"       -> ('S', 1)   corps collé à la tête
"0R0W"      -> ('R', 2)   pomme rouge à 2 cases
"000000GW"  -> ('G', 3)   pomme verte à 7 cases, plafonnée à 3
```

- **`DISTANCE_MAX = 3` :** au-delà, « 3 » veut dire « 3 ou plus ». C'est le réglage qui fixe la richesse de l'état.
- **Repère égocentrique :** l'agent ne pense pas en HAUT/BAS/GAUCHE/DROITE, mais par rapport à son cap. Il a trois actions : `TOUT_DROIT`, `GAUCHE`, `DROITE`.
  - Pas de demi-tour : à 3 cases, il tue immédiatement contre le cou.
  - La même situation vue dans une autre orientation devient le même état : l'agent n'a pas à la réapprendre pour chaque direction.
- **L'état** = (devant, gauche, droite), par exemple `(('R', 2), ('G', 2), ('W', 3))`. Le rayon de derrière n'est pas lu : dès que le serpent a 2 cases, il commence par le cou, donc il n'apprend rien à l'agent.
- **Nombre d'états :** 4 symboles × 3 distances = 12 par rayon, donc au plus 12³ = **1 728 états**. Le modèle `infini.txt` en connaît 1 368.
- `tourner(cap, action)` traduit une action relative en direction absolue pour le plateau.
- **`VERSION_ENCODAGE = 1` :** à incrémenter à chaque changement d'encodage. Un modèle sauvegardé avec un autre encodage est alors refusé au chargement au lieu d'être faux sans rien dire.

### 4.2 La table Q (`src/agent/qtable.py`)
- C'est un dictionnaire `état -> [valeur tout droit, valeur gauche, valeur droite]`, plus un compteur de mises à jour par couple (état, action), qui sert à alpha.
- **`VALEUR_INITIALE = 1.0` (optimiste) :** une action jamais essayée vaut +1, plus que n'importe quel pas déjà payé (−1). L'agent essaie donc spontanément ce qu'il ne connaît pas.
- Deux façons de lire :
  - `valeurs(etat)` crée l'état s'il est inconnu et renvoie la liste stockée (pour apprendre) ;
  - `lire(etat)` ne crée rien et renvoie une copie (pour choisir). **Choisir ne modifie jamais la table :** un agent figé qui découvre une situation ne change pas le modèle qu'on évalue.

### 4.3 Choisir une action (`Agent.choisir_action`)
- **ε-greedy :**
  - avec la probabilité ε, une action au hasard (exploration) ;
  - sinon, la meilleure action de la table (exploitation).
- **Égalités tirées au hasard :** `index(max(...))` prendrait toujours la première action. Sur un état neuf `[1, 1, 1]`, le serpent irait toujours tout droit.
- **`self.rng` propre à l'agent :** il est resemé à chaque partie (voir §7).

### 4.4 Apprendre : la mise à jour de Bellman (`Agent.mettre_a_jour`)
```
mort  : cible = récompense
sinon : cible = récompense + γ × max Q(état suivant)
Q <- Q + α × (cible − Q)
```
Exemple : Q = 1,0, le pas coûte −1 et mène à un état dont la meilleure valeur est 1,0. La cible vaut −1 + 0,95 × 1,0 = −0,05. Avec α = 1, Q devient −0,05.

- **`GAMMA = 0.95` :** le poids du futur. L'agent raisonne sur environ 1 / (1 − 0,95) = 20 coups.
- **Sur une vraie mort,** il n'y a pas d'après : on ne regarde pas l'état suivant. Sur une troncature, on le regarde (voir §2).

### 4.5 α décroît avec les visites (`Agent.alpha`)
`α = 1 / n^0.7`, où n est le nombre de mises à jour du couple (état, action).

| n | 1 | 10 | 100 | 1000 |
|---|---|---|---|---|
| α | 1,00 | 0,20 | 0,04 | 0,008 |

Les pommes tombent au hasard : une valeur souvent vue doit devenir une **moyenne stable**, au lieu de suivre la dernière partie. La première observation est prise en entier.

### 4.6 Apprendre en fin de partie (`learn` puis `fin_partie`)
- Pendant la partie, `learn()` **note** seulement chaque pas dans `trajectoire` : (état, action, récompense, état suivant, mort).
- À la fin, `fin_partie()` rejoue ces pas **dans l'ordre** et met la table à jour. Toute la partie est donc jouée avec la même table, puis apprise d'un bloc.
- `learn()` vérifie qu'on lui donne bien la direction que l'agent vient de jouer. Un décalage entre la boucle et l'agent lève une erreur au lieu de fausser l'apprentissage.

### 4.7 ε décroît sur les pas (`mettre_a_jour_epsilon`)
```
ε = max(EPSILON_MIN, 1 × (1 − pas_total / PAS_CIBLE))
```
- ε part de 1 (tout au hasard) et descend **en ligne droite** jusqu'à `EPSILON_MIN = 0.01` en `PAS_CIBLE = 5 000` pas. Il atteint son plancher après environ 200 parties.
- **Compté sur les pas, pas sur les parties :** une partie dure 5 pas au début et des centaines à la fin. Compter les parties épuiserait l'exploration sur les toutes premières, les plus courtes.
- **Plancher à 0,01 :** même entraîné, l'agent joue 1 coup sur 100 au hasard pendant l'apprentissage.
- Un modèle rechargé reprend ε là où il en était, à partir de `pas_total`. Sinon il se remettrait à jouer au hasard.

### 4.8 L'agent figé (`figer`, option `-dontlearn`)
`apprend = False`, ε = 0 : l'agent joue au mieux, ne note rien et ne modifie pas sa table. C'est ce qui sert à évaluer un modèle, et c'est le mode par défaut du menu JOUER.

### 4.9 Créer l'agent (`src/agent/fabrique.py`)
| Configuration | Agent |
|---|---|
| `-baseline random` | `RandomAgent`, tire une direction au hasard : le plancher à battre |
| `-load FICHIER` | agent rechargé depuis le modèle |
| rien | agent neuf |
| `-dontlearn` | l'agent ci-dessus, figé |

---

## 5. Les modèles (`src/agent/modele.py`, `src/models.py`)

### Format : un seul fichier JSON lisible
```json
{
  "format": "learn2slither-qtable",
  "version_encodage": 1,
  "distance_max": 3,
  "regle": "qlearning",
  "hyperparametres": {"gamma": 0.95, "alpha": "1/n^0.7", "valeur_initiale": 1.0,
                      "epsilon_min": 0.01, "pas_cible": 5000},
  "parties": 1000,
  "pas_total": 123456,
  "qtable": {"R2|G2|W3": {"valeurs": [-0.8, 4.2, -12.5], "visites": [3, 7, 1]}}
}
```
- **Clés en texte :** JSON n'accepte pas un tuple comme clé. `(('R',2),('G',2),('W',3))` devient `"R2|G2|W3"`, puis redevient un tuple à la lecture.
- **Écriture atomique :** on écrit dans `fichier.tmp`, puis on le renomme. Si l'écriture échoue, l'ancien modèle reste intact.
- **`-save` est vérifié avant d'entraîner** (`verifier_chemin_sauvegarde`) : une faute de frappe ne fait pas perdre l'entraînement à la fin.

### Chargement strict
- Tout est vérifié **au chargement** : format, version d'encodage, `DISTANCE_MAX`, champs présents, nombres finis et dans leurs bornes, compteurs entiers, clés valides et écrites d'une seule façon (`R02` est refusé).
- Un modèle abîmé est refusé tout de suite, au lieu de planter le jour où l'état abîmé est rencontré.
- Toute erreur devient une `ErreurModele` avec un message lisible : le programme l'affiche et s'arrête proprement, sans trace Python (le sujet note 0 un programme qui quitte de façon inattendue).

### Le dossier `models/`
- `models.py` liste les fichiers `.txt`, `.json` et `.qtable`, et en lit les métadonnées.
- Les métadonnées sont gardées en cache selon (date de modification, taille) : la liste est redessinée à chaque image, et un fichier n'est relu que s'il a changé.
- Nom d'un nouveau modèle : `[A-Za-z0-9_-]{1,32}`, enregistré dans `models/<nom>.txt`.
- **Modèle par défaut** dans JOUER et ÉVALUATION : le modèle lisible qui a le plus de parties.

| Fichier | Parties |
|---|---|
| `1sess.txt`, `10sess.txt`, `100sess.txt`, `1000sess.txt` | 1 / 10 / 100 / 1 000 |
| `infini.txt` | environ 4,1 millions |

---

## 6. Les boucles de jeu

### 6.1 Sans affichage (`src/session.py`, `-visual off`)
- `run_sessions` enchaîne `-sessions N` parties. Chaque partie est jouée par `play_session`, puis l'agent est sauvegardé si `-save` est donné.
- **Contrat avec l'agent :** seul `choose()` est obligatoire ; `debut_partie`, `learn`, `fin_partie` et `save` sont facultatifs. Les agents de référence passent donc par la même boucle.
- **Garde-fou** `MAX_STEPS_PER_SESSION = 1 000 000` : si un bug laissait `alive` à vrai, la boucle s'arrêterait quand même (et les tests échoueraient au lieu de se figer). La partie est alors terminée par `truncate()`, pour que `end_cause` ne reste jamais vide.
- **Ctrl+C :** on s'arrête après les parties terminées, et ce qui est appris est gardé et sauvegardé.
- **Statistiques** (`SessionStats`) :
  - longueur moyenne, médiane et maximale, durée, causes de fin ;
  - la moyenne porte sur le record de chaque partie : c'est la vraie mesure de progression, le maximum global relevant surtout de la chance ;
  - la répartition des causes de fin dit quoi corriger en priorité.
- Chaque partie affiche `Fin de la partie, longueur maximale = …, duree maximale = …`.

### 6.2 Entraînement en fenêtre (`src/training.py`)
- C'est la même boucle `play_session`, **découpée en tranches** de 25 ms par image (`BUDGET_S`), sans thread : la fenêtre reste fluide pendant l'entraînement.
- Le compte se fait sur les parties jouées dans cette session, pas sur `agent.parties` : la boucle s'arrête même avec un agent qui ne compte pas ses parties.
- **Moyenne glissante sur 100 parties :** sur toutes les parties, les premières (jouées au hasard) tireraient la moyenne vers le bas pendant longtemps.
- **Courbe :** un point toutes les 100 parties.
- **Sauvegarde dans tous les cas :** fin normale, bouton ARRETER, fermeture de la fenêtre, Ctrl+C. Les parties jouées ne sont jamais perdues.

### 6.3 Évaluation (`src/evaluation.py`, `src/interface/evaluation_view.py`)
- **Règle :** l'agent figé enchaîne des parties jusqu'à ce qu'une partie atteigne l'**OBJECTIF** (longueur, 35 par défaut, réglable de 5 à 100 par pas de 5). 35 est le palier de bonus le plus haut du sujet.
- La partie qui atteint l'objectif n'est pas coupée : elle va jusqu'à sa fin, puis l'évaluation s'arrête.
- **Chaque pas est photographié** (`Photo`) pour le rejeu. Une photo contient le serpent, les pommes, la direction, les compteurs (dont `idle`, sans lequel la troncature serait faussée au retour au présent) et la graine.
- **Enchaînement après un objectif raté :**
  - pause de `min(0,4 ; 4 / vitesse)` secondes ;
  - à partir de la vitesse 40 (MAX compris), pas d'écran de fin du tout : la partie suivante démarre au pas même de la mort ;
  - la partie qui atteint l'objectif garde une pause de 0,3 à 1,2 s, pour qu'on la voie.
- R ou ESPACE pendant une partie : la partie abandonnée n'est pas comptée. ECHAP : arrêt et résultats.
- **Résultats :**
  - parties jouées, objectif atteint ou non, longueur moyenne, médiane et maximale (avec la graine du record), durée moyenne, causes de fin ;
  - puis le **rejeu** coup par coup (← →, ORIGINE, FIN) de la partie qui a atteint l'objectif, ou sinon de la meilleure partie.

---

## 7. Une graine par partie (`src/graine.py`)

**But :** pouvoir rejouer **n'importe quelle partie** à l'identique, par exemple la partie 847, sans rejouer les 846 d'avant.

```
graine de départ G = -seed N, ou un nombre tiré au hasard entre 0 et 999 999
graine de la partie n = G + n − 1
```
Exemple avec `-seed 1000` : la partie 1 a la graine 1000, la partie 847 a la graine 1846.

- **Au début de chaque partie**, `nouvelle_partie()` resème :
  - le plateau avec la graine (position du serpent, pommes) ;
  - l'agent avec `"agent-<graine>"` (exploration, égalités).

  Les deux flux sont différents : sinon les tirages de l'agent seraient corrélés aux apparitions de pommes.
- Une partie ne dépend donc plus des précédentes. **`-seed 1846` rejoue la partie 847** : elle devient la partie 1.
- **Graine tirée par `SystemRandom` :** elle ne dépend pas du module `random`, qu'une autre partie du programme aurait pu semer. Elle est courte, donc facile à recopier depuis l'écran.
- **Les effets visuels** (particules, secousse) ont leur propre générateur. Ils tirent au rythme des images : partager le générateur du plateau ferait dépendre les pommes de la fluidité de l'affichage. La fenêtre donne ainsi exactement les mêmes parties que `-visual off`.
- **Condition :** le même modèle, figé. Un agent qui apprend change de table à chaque partie ; un entraînement se rejoue seulement en entier, depuis la même graine de départ.
- **Affichée seulement quand elle rejoue vraiment la partie,** c'est-à-dire avec un agent qui n'apprend pas (modèle figé ou agent aléatoire). Elle est masquée quand l'agent apprend et au pilotage clavier (`Game.graine_rejouable`). Le menu ENTRAINEMENT ne l'affiche pas non plus.
- **Où voir la graine :**
  - le panneau de jeu (`GRAINE G · -seed G la rejoue`) ;
  - la carte RECORD (graine de la partie record) ;
  - les résultats d'évaluation (record et rejeu) ;
  - le terminal en `-visual off` (`Graine de depart : G`).

---

## 8. L'interface (`src/interface/`)

### 8.1 Navigation (`loop.py`)
```
MENU --JOUER--------> LOBBY --LANCER--> PARTIE
  |                     `--MODELE--> CHOIX DU MODELE
  |--ENTRAINEMENT-----> LISTE / NOUVEAU / CONTINUER / EN COURS
  `--EVALUATION-------> RÉGLAGES --EVALUER--> PARTIES --> RÉSULTATS
```
- ECHAP remonte d'un cran ; depuis le menu principal, il quitte.
- Si la ligne de commande décrit déjà la run (`-sessions`, `-load`, `-save`, `-dontlearn`, `-step-by-step`, `-baseline`), on va directement à la partie. `-lobby on|off` force le choix.
- **Fenêtre :** 1180×760 à 60 images/s, plateau à gauche, panneau à droite.
- **Fermeture** (croix ou Ctrl+C dans le terminal) : la partie en cours est apprise, l'entraînement en cours et `-save` sont sauvegardés.
- **`PiloteAgent` garde le même agent d'une partie à l'autre.** Revenir au lobby ne recharge pas le fichier, ce qui perdrait ce qu'il a appris entre-temps. L'agent n'est recréé que si le modèle, l'apprentissage ou la baseline changent.
- **L'agent est créé au lancement de la partie**, puisque le modèle peut changer dans le lobby. Si le modèle est illisible, le message va dans le terminal et on reste dans le lobby.

### 8.2 JOUER (`lobby.py`, `model_picker.py`, `model_card.py`)
- **Réglages :** PILOTE (IA / JOUEUR), MODELE, PLATEAU (5 à 50 par pas de 5), VITESSE.
- **L'IA est figée**, sauf si `-save` est donné : dans ce cas l'agent doit apprendre, sinon on sauvegarderait un agent figé.
- **Choix du modèle :**
  - la liste est relue à chaque ouverture ;
  - la carte de détails affiche parties, pas, situations connues (sur 1 728), ε actuel, hyperparamètres et taille du fichier.
- **Valeurs hors cran** venant du CLI (`-size 12`) : on passe au cran voisin sans en sauter (12 donne 15 ou 10).

### 8.3 ENTRAINEMENT (`training_view.py`)
- **LISTE :** les modèles, du moins au plus entraîné ; un modèle illisible ne peut pas être continué.
- **NOUVEAU :** NOM, GAMMA, EPSILON MINIMAL, PAS CIBLE, VALEUR INITIALE, PLATEAU, PARTIES A JOUER.
  - γ reste strictement sous 1 : à 1, le futur compterait sans fin et les valeurs pourraient grandir sans limite.
  - Sous chaque champ, une aide traduit la valeur (γ : « pense à ~1/(1−γ) coups » ; ε : « 1 coup sur N »).
- **CONTINUER :** « monter jusqu'à » N parties, de 10 à 10 millions.
- **EN COURS :** progression, longueur moyenne sur 100 parties, record, ε, parties par seconde, temps restant, courbe d'apprentissage (environ un point par pixel).

### 8.4 La partie (`game.py`, `panel_view.py`, `board_view.py`)
- **Vitesses :** 1, 5, 10, 15, 20, 30, 40, 50, 75, 100 cases/s et MAX. Défaut 5.
  - Toute vitesse est bornée : 0 ferait diviser par zéro, et NaN figerait le serpent.
  - **MAX** joue autant de pas que possible pendant 10 ms par image. Sur les 16 ms d'une image, il en reste pour le dessin.
- **Pas à pas** (P, ou N qui l'active et avance d'un pas) :
  - avec l'IA, ← et → reculent ou avancent dans l'historique (1 000 photos) ;
  - **on ne fait que montrer le passé** : la partie, les pommes et l'apprentissage ne sont jamais annulés, et un nouveau pas n'est joué que depuis le présent ;
  - en fin de partie, on attend N, ce qui laisse revoir les derniers pas.
- **Pilotage clavier :** file de 2 virages au plus, demi-tour immédiat ignoré.
- **R** lance une nouvelle partie ; une partie abandonnée est quand même apprise.
- **Panneau :**
  - pilote, graine, cartes LONGUEUR / RECORD (avec graine) / DUREE / VITESSE ;
  - la croix de vision comme dans le terminal, recadrée autour de la tête sur un grand plateau ;
  - dernière action, et un état à 3 valeurs : EN VIE, INTERROMPU, MORT (une troncature n'est pas une mort) ;
  - l'aide clavier, une touche par ligne.
- **Effets :** particules et secousse sur les pommes et la mort. Ils sont purement visuels et ont leur propre générateur aléatoire.

---

## 9. La ligne de commande (`src/cli.py`)

Les options s'écrivent avec un seul tiret, comme dans le sujet. Les abréviations sont refusées.

| Option | Défaut | Rôle |
|---|---|---|
| `-sessions N` | 1 | nombre de parties |
| `-save FICHIER` | — | sauvegarde de l'agent à la fin |
| `-load FICHIER` | — | modèle à charger |
| `-visual on\|off` | on | affichage ; off = entraînement rapide |
| `-dontlearn` | — | agent figé |
| `-step-by-step` | — | un pas par appui sur N |
| `-verbose` | — | trace terminal même avec `-visual off` |
| `-size N` | 10 | taille du plateau (5 à 50) |
| `-speed X` | 5 | cases par seconde, `inf` = MAX |
| `-seed N` | tirée au hasard | graine de départ (voir §7) |
| `-pilot ia\|joueur` | ia | pilote présélectionné |
| `-lobby on\|off` | auto | forcer ou non le lobby |
| `-baseline random` | — | agent aléatoire de référence |

Exemples du sujet :
```
./snake -sessions 10 -save models/10sess.txt -visual off
./snake -visual on -load models/100sess.txt -sessions 10 -dontlearn -step-by-step
```

---

## 10. Les tests (`tests/`)

Lancement : `python -m unittest discover -s tests`. Les tests de l'interface tournent sans écran (`SDL_VIDEODRIVER=dummy`).

| Fichier | Ce qu'il vérifie |
|---|---|
| `test_board.py`, `test_rewards.py` | règles du plateau, troncature, barème |
| `test_interpreter.py`, `test_encode.py`, `test_directions.py` | encodage de l'état, repère égocentrique |
| `test_qtable.py`, `test_choix.py`, `test_apprentissage.py` | table Q, ε-greedy, Bellman, α, fin de partie |
| `test_modele.py` | sauvegarde, chargement, refus des fichiers abîmés |
| `test_session.py`, `test_branchement.py`, `test_cli.py` | boucles, options, reproductibilité |
| `test_graine.py` | partie n = partie 1 avec la graine G + n − 1, fenêtre identique au mode sans affichage, graine du record |
| `test_menus.py` | menus, entraînement, évaluation, pas à pas |
| `test_interface.py` | affichage : mort ou interruption |

---

## 11. Touches clavier

| Écran | Touche | Action |
|---|---|---|
| Menus et formulaires | ↑ ↓ (ZQSD / WASD), TAB | se déplacer |
| | ← → | changer la valeur |
| | ENTRÉE / ESPACE | valider |
| | ECHAP | revenir |
| Partie | ↑ ↓ ← → / ZQSD / WASD | diriger (pilote JOUEUR) |
| | ← → (IA en pas à pas) | pas précédent / suivant |
| | N | pas suivant (active le pas à pas) |
| | P | mode pas à pas |
| | ESPACE | pause ; partie finie : rejouer (évaluation : résultats) |
| | R | nouvelle partie |
| | V | afficher / masquer la vision |
| | T | trace terminal |
| | + / − | vitesse ± un cran |
| | ECHAP | lobby (évaluation : résultats) |
| Entraînement | N / ENTRÉE (C) | nouveau / continuer |
| | ECHAP / ESPACE | arrêter et sauvegarder |
| Résultats | ← → | coup précédent / suivant |
| | ORIGINE / FIN | début / fin de la partie |
| | ECHAP / ENTRÉE | menu |
