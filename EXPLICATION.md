# Learn2Slither — tout ce qui a été fait, et comment marche le code

Ce document est le récapitulatif complet du projet : ce que fait l'IA, comment le code est organisé, pourquoi chaque choix a été fait, ce qui a été mesuré, et les questions qu'un correcteur peut poser en soutenance, avec leurs réponses.

Le cours théorique complet est dans `IA.md`. Ce document-ci suit le **code réel**.

---

## 1. En une page

**Le projet.** Un serpent sur un plateau 10×10 apprend à jouer tout seul, par essais et erreurs, avec du **Q-learning tabulaire**. Il ne voit que les quatre lignes qui partent de sa tête (la « croix ») ; lui donner plus d'informations coûterait −42.

**Comment il apprend, en trois phrases.** À chaque pas, il résume ce qu'il voit en un **état** (ce qu'il y a devant, à sa gauche et à sa droite). Une **table Q** associe à chaque état une note pour chacune de ses trois actions (tout droit, gauche, droite). Après chaque partie, il corrige ces notes d'après ce qui s'est réellement passé (formule de Bellman).

**Les résultats** (modèle figé avec `-dontlearn`, longueur moyenne) :

| Modèle | Parties d'entraînement | Longueur moyenne | Longueur max |
|---|---|---|---|
| jouer au hasard | — | 3,05 | 4 |
| `models/1sess.txt` | 1 | 3,3 | 5 |
| `models/10sess.txt` | 10 | 3,4 | 7 |
| `models/100sess.txt` | 100 | 4,3 | 8 |
| `models/1000sess.txt` | 1 000 | 23,2 | 41 |
| `models/10000sess.txt` | 10 000 | 26,6 | 51 |
| **`models/infini.txt`** | **3 429 783** | **28,4** | **50** |

Le sujet demande 10 de longueur ; les bonus vont jusqu'à 35. Le meilleur modèle fait 28 de moyenne et a atteint 66 pendant l'entraînement.

**La limite.** Tout converge vers environ **29,5** : à ce niveau, 97 à 100 % des morts sont contre son propre corps. Il s'enferme parce qu'il ne voit pas la forme de son corps, seulement une ligne et une colonne. Douze idées ont été testées pour dépasser ce plafond, aucune n'y arrive (section 5).

**Les commandes du sujet :**

```bash
./snake -sessions 10 -save models/10sess.txt -visual off
./snake -visual on -load models/100sess.txt -sessions 10 -dontlearn -step-by-step
./snake -visual on -load models/1000sess.txt
```

**Pour montrer le meilleur modèle :**

```bash
./snake -visual on -load models/infini.txt -dontlearn
```

---

## 2. Le trajet d'une partie, fichier par fichier

On suit ce qui se passe quand on tape une commande, jusqu'au modèle sauvegardé. Chaque fichier arrive au moment où il sert.

```
./snake (lanceur)
  └─ main.py ─────────────── lit la ligne de commande, vérifie -save
       ├─ cli.py / config.py   traduit les options en réglages
       ├─ agent/fabrique.py    crée l'agent (neuf, rechargé, figé, ou de référence)
       │     └─ agent/modele.py   relit le fichier de -load
       └─ session.py (sans affichage)  ou  interface/loop.py + game.py (fenêtre)
             └─ pour chaque partie :
                  environment/board.py     le plateau, les règles
                  agent/agent.py           choisit, note, apprend
                    ├─ agent/interpreter.py   vision → état, action relative → direction
                    └─ agent/qtable.py        la mémoire : les notes
                  environment/rewards.py   le barème
             └─ à la fin : agent/modele.py écrit le modèle (-save)
```

### 2.1 Le lancement — `main.py`, `cli.py`, `config.py`, `agent/fabrique.py`

`./snake` est un petit script qui lance `main.py` avec le Python du projet (`.venv`).

`main.py` fait trois choses, dans cet ordre :

1. **Vérifier `-save` avant tout** (`verifier_chemin_sauvegarde`). Si le chemin est impossible (un dossier, pas de droit d'écriture, nom vide), on s'arrête tout de suite avec un message clair. Sinon, une faute de frappe ne se verrait qu'après des minutes d'entraînement perdues.
2. **Créer l'agent** avec `creer_agent` (`agent/fabrique.py`) :

| Option | Agent créé |
|---|---|
| `-baseline random` | un agent qui joue au hasard, pour comparer |
| `-load FICHIER` | l'agent rechargé depuis le fichier |
| rien | un agent neuf, qui part de zéro |
| `-dontlearn` en plus | l'agent ci-dessus, **figé** : il joue sans apprendre |

3. **Lancer la boucle** : `session.py` avec `-visual off`, la fenêtre pygame sinon.

Toute erreur de modèle (fichier absent, abîmé, incompatible) devient un message `Erreur : …` et un code de sortie 1, jamais une trace Python : le sujet note 0 un programme qui quitte de façon inattendue.

`config.py` borne les réglages absurdes : la taille entre 5 et 30, la vitesse entre 1 et 30 cases par seconde (une vitesse de 0 faisait diviser par zéro).

### 2.2 Le plateau — `environment/board.py`

Les règles du sujet : 10×10, 2 pommes vertes, 1 rouge, serpent de 3 cases placé au hasard. Verte : +1 case. Rouge : −1 case. Mur, corps ou longueur 0 : partie perdue.

La méthode centrale est `step(direction)`. Elle avance d'une case et **renvoie l'évènement du pas** : `"move"`, `"green"`, `"red"`, `"wall"`, `"body"` ou `"starve"` (longueur tombée à 0).

**La distinction la plus importante du projet : mourir n'est pas être interrompu.**

Pour qu'un serpent entraîné ne tourne pas en rond à l'infini, la partie s'arrête après trop de pas sans pomme. Ce n'est **pas** une mort : c'est une **troncature**, une limite qu'on impose nous-mêmes.

| | Mort | Troncature |
|---|---|---|
| cause | mur, corps, longueur 0 | 400 pas sans pomme (sur 10×10) |
| `board.dead` | vrai | **faux** |
| `board.truncated` | faux | vrai |
| `board.end_cause` | `"wall"`, `"body"`, `"starve"` | `"timeout"` |
| ce que renvoie `step()` | l'évènement de la mort | **`"move"`** : le pas reste un déplacement ordinaire |

Pourquoi c'est si important : si la troncature était traitée comme une mort, l'agent apprendrait que « vivre longtemps finit mal », et il apprendrait à mourir plus tôt. Et si elle valait 0 au lieu du −1 d'un déplacement, atteindre la limite deviendrait le meilleur coup possible : il apprendrait à stagner. C'est le premier bug trouvé par l'audit, corrigé dans les deux sens.

**La limite de pas** vaut `4 × taille²` (`IDLE_FACTOR = 4`), soit 400 sur 10×10. Elle dépend de l'**aire** du plateau et non de la longueur du serpent : mesuré, une limite qui ignorait la taille tronquait 97 % des parties sur un 30×30.

**La vision.** `vision_chars()` renvoie la croix sous forme de 4 chaînes, une par direction, lues de la tête vers l'extérieur :

```
   W
   G         HAUT    '0GW'
   0         GAUCHE  'SSW'
WSSH0RW      BAS     '00W'
   0         DROITE  '0RW'
   0
   W
```

Chaque chaîne finit toujours par `W` : la case juste après le bord. Sur 10×10, la croix compte 18 cases en plus de la tête.

### 2.3 Le barème — `environment/rewards.py`

| Évènement du pas | Récompense |
|---|---|
| pomme verte | +20 |
| pomme rouge | −10 |
| déplacement simple | −1 |
| mort (mur, corps, longueur 0) | −50 |

Il n'y a **volontairement pas** de ligne pour la troncature : demander la récompense de `"timeout"` lève une erreur. Les rapports comptent plus que les valeurs : si un pas coûtait −10, survivre 5 pas coûterait autant que mourir, et le serpent apprendrait à se suicider.

C'est l'**environnement** qui note l'agent, pas l'agent qui se note lui-même : le fichier est donc dans `environment/`.

### 2.4 Ce que voit le serpent — `agent/interpreter.py`

La vision brute a des dizaines de milliards de combinaisons possibles : impossible à mettre dans une table. Il faut la **résumer**.

**`lire_rayon`** — de chaque rayon, on ne garde que **la première chose vue et sa distance**, plafonnée à 3 :

```
'0GW'       → ('G', 2)     pomme verte à 2 cases
'SSW'       → ('S', 1)     son corps, collé à la tête
'000000GW'  → ('G', 3)     pomme à 7 cases : "3 ou plus"
```

Le plafond à 3 garde la table petite, et rend le modèle utilisable sur un plateau de n'importe quelle taille : « 3 ou plus » veut dire la même chose partout. C'est ce qui valide le bonus « taille de plateau variable ».

**Le repère égocentrique.** Au lieu de « haut, bas, gauche, droite », le serpent raisonne **par rapport à là où il va** : devant, à sa gauche, à sa droite. « Pomme à 2 cases devant » est alors la même situation qu'il monte ou qu'il aille à droite : la même leçon ne s'apprend plus 4 fois.

**`tourner(cap, action)`** traduit une action relative en direction du sujet. Le piège : `board.DIRECTIONS = (UP, LEFT, DOWN, RIGHT)` tourne dans le sens **inverse** des aiguilles d'une montre. Donc gauche = indice +1, droite = indice −1.

```
cap HAUT    tout droit → HAUT    gauche → GAUCHE   droite → DROITE
cap DROITE  tout droit → DROITE  gauche → HAUT     droite → BAS
```

Les 3 actions sont `TOUT_DROIT = 0`, `GAUCHE = 1`, `DROITE = 2`. Le demi-tour n'existe pas : dès 3 cases de long, il envoie la tête sur le cou. L'agent envoie toujours au plateau une des 4 directions imposées par le sujet.

**`encode(vision, cap)`** fabrique l'état : 3 couples, devant puis gauche puis droite. Le rayon de derrière n'est jamais lu, puisque c'est toujours le cou.

```python
(('R', 2), ('G', 2), ('W', 3))
```

C'est un **tuple**, parce qu'il sert de clé dans un dictionnaire et qu'une liste ne peut pas en être une. Il y a au plus 12 × 12 × 12 = 1 728 états ; en pratique, environ 1 370 sont rencontrés.

**D'où vient le cap ?** L'environnement connaît la direction du serpent (`board.direction`) ; la boucle la donne à l'agent **une fois**, au début de la partie (`debut_partie`). Ensuite, l'agent la tient à jour lui-même, puisqu'il sait quel coup il vient de jouer.

### 2.5 La mémoire — `agent/qtable.py`

La Q-table est un dictionnaire : **état → 3 notes**, une par action.

```python
{ (('R', 2), ('G', 2), ('W', 3)): [-0.8,  4.2, -12.5], ... }
#                                  tout   gauche droite
```

- **`valeurs(etat)`** sert à **écrire**. Un état jamais vu est créé avec `[1.0, 1.0, 1.0]`. Elle renvoie la liste rangée dans la table, pas une copie : modifier cette liste modifie la table.
- **`lire(etat)`** sert à **regarder** : elle ne crée jamais rien et renvoie une copie. Sans elle, un agent figé (`-dontlearn`) ajoutait à la table chaque situation qu'il regardait, et le fichier du modèle changeait alors qu'il n'avait rien appris. Le correcteur vérifie justement ce point.
- **Pourquoi partir de +1 et pas de 0** (« initialisation optimiste ») : un pas coûte −1, donc une action essayée descend en général sous +1. Les actions jamais essayées paraissent alors meilleures, et le serpent explore de lui-même ce qu'il ne connaît pas.
- **`compter_visite`** compte combien de fois chaque couple (état, action) a été appris : ce compteur règle la force des corrections (α, voir 2.6).

Deux pièges évités et testés : recréer la liste à chaque lecture effacerait tout l'apprentissage ; donner la même liste à deux états ferait que corriger l'un corrigerait l'autre.

### 2.6 Le cerveau — `agent/agent.py`

Le déroulé d'une partie, vu par l'agent :

```
debut_partie(cap)       on lui dit dans quel sens part le serpent
  à chaque pas :
    choose(vision)      il regarde, choisit, renvoie UP/LEFT/DOWN/RIGHT
    learn(...)          il NOTE ce que ce pas a rapporté
fin_partie()            il apprend toute la partie
```

**Choisir — `choisir_action`** (ε-greedy) :
- avec la probabilité **ε**, une action au hasard : il **explore** ;
- sinon, l'action qui a la meilleure note : il **exploite** ce qu'il sait.

Si plusieurs actions sont à égalité, il tire au sort entre elles. Sinon Python prendrait toujours la première, et sur un état neuf `[1, 1, 1]` le serpent irait toujours tout droit.

**Apprendre — `mettre_a_jour`** : c'est la formule de Bellman, le cœur du projet.

```
si mort : cible = récompense                              (il n'y a pas d'après)
sinon   : cible = récompense + γ × meilleure note de la situation suivante
nouvelle note = ancienne note + α × (cible − ancienne note)
```

En clair : la valeur d'un coup, c'est ce qu'il a rapporté tout de suite, plus ce que vaut la situation où il mène. On déplace l'ancienne note vers cette cible, d'une fraction α de l'écart.

Exemple : note à 1,0 ; le pas coûte −1 et mène à une situation dont la meilleure note vaut 1,0. Cible = −1 + 0,95 × 1,0 = −0,05. À la première visite (α = 1), la note devient −0,05.

Sur une **troncature**, l'agent utilise bien la situation suivante (le serpent était vivant). Sur une **mort**, il ne l'utilise pas.

**Les trois réglages :**

| Réglage | Valeur | Rôle |
|---|---|---|
| γ (`GAMMA`) | 0,95 | importance du futur : il raisonne sur environ 1 / (1 − 0,95) = 20 coups |
| α | 1 / n^0,7 | force de la correction à la n-ième fois : 1 la première fois, 0,2 à la 10ᵉ, 0,008 à la 1 000ᵉ. Les pommes tombent au hasard, une note souvent vue doit devenir une moyenne stable |
| ε | de 1 à 0,01 | baisse en ligne droite sur les **pas** joués, et atteint 0,01 au bout de `PAS_CIBLE = 5 000` pas (environ 200 parties) |

**Apprendre en fin de partie, dans l'ordre — `fin_partie`.** Pendant la partie, `learn()` ne fait que **noter** chaque pas. À la fin, `fin_partie()` les apprend tous, du premier au dernier, une seule fois chacun.

On a d'abord essayé de les rejouer **à l'envers**, en espérant que la mort « remonte » d'un coup sur toute la partie. C'est faux en Q-learning : l'avant-dernier pas regarde la **meilleure** action de la situation suivante, et les actions encore jamais essayées y valent +1. Le −50 reste bloqué sur le dernier pas. Mesuré sur 8 graines : dans l'ordre 27,2 ; à l'envers 25,4 ; à chaque pas 25,5.

**Figer — `figer()`.** C'est `-dontlearn` : ε = 0, plus aucune note modifiée, plus aucun compteur qui bouge. On mesure ce que le modèle sait, sans bruit et sans l'abîmer.

### 2.7 La boucle de jeu — `session.py`, `interface/game.py`, `interface/loop.py`

**Sans affichage — `play_session`**, pour une partie :

```
agent.debut_partie(board.direction)
tant que la partie continue :
    vision = board.vision_chars()           ce qu'il voit avant
    action = agent.choose(vision)
    event  = board.step(action)
    agent.learn(vision, action, recompense(event), vision d'après, board.dead)
agent.fin_partie()
```

Trois détails qui comptent :
- c'est **`board.dead`** qui est donné à l'agent, pas « la partie est finie » : une troncature n'est pas une mort ;
- la récompense se calcule sur **l'évènement du pas**, pas sur la cause de fin ;
- un plafond de sécurité (`MAX_STEPS_PER_SESSION`) termine proprement une partie qui ne s'arrêterait jamais à cause d'un bug.

`run_sessions` enchaîne les parties, affiche les statistiques (longueur moyenne, médiane, maximum, causes de fin), puis sauvegarde avec `-save`. **Ctrl+C** pendant un long entraînement arrête proprement et sauvegarde les parties déjà terminées.

**Avec la fenêtre — `game.py` et `loop.py`.** Même contrat : `_tick` joue un pas exactement comme `play_session`. En plus :
- le pas-à-pas (touche N), la vitesse réglable, la vision et l'action affichées dans le terminal ;
- **`PiloteAgent`** garde le **même agent** d'une partie à l'autre. Sinon, revenir au lobby (Échap) puis relancer rechargeait l'agent depuis le fichier, et tout ce qu'il avait appris entre-temps était perdu ;
- Échap, la touche R et la fermeture font apprendre la partie en cours au lieu de la jeter ;
- à la fermeture (croix ou Ctrl+C), l'agent est sauvegardé avec `-save` ;
- le panneau affiche « INTERROMPU » et non « MORT » sur une troncature.

### 2.8 La sauvegarde — `agent/modele.py`

Un modèle est **un fichier JSON** (avec l'extension `.txt`, comme dans les exemples du sujet) :

```json
{
  "format": "learn2slither-qtable",
  "version_encodage": 1,
  "distance_max": 3,
  "regle": "qlearning",
  "hyperparametres": {"gamma": 0.95, "alpha": "1/n^0.7", "valeur_initiale": 1.0,
                      "epsilon_min": 0.01, "pas_cible": 5000},
  "parties": 1000,
  "pas_total": 125043,
  "qtable": {
    "R2|G2|W3": {"valeurs": [-0.8, 4.2, -12.5], "visites": [3, 7, 1]}
  }
}
```

- JSON n'accepte pas un tuple comme clé : l'état `(('R', 2), ('G', 2), ('W', 3))` devient le texte `"R2|G2|W3"`, et redevient un tuple au chargement.
- **`version_encodage`** : si on change un jour la façon de fabriquer les états, un ancien modèle est **refusé**. Sinon ses clés ne correspondraient plus à rien, sans aucun message d'erreur.
- **Au chargement, tout est vérifié** : types, bornes, valeurs infinies ou NaN, nombres géants, clés mal écrites. Un fichier abîmé donne un message clair, jamais une trace Python, ni un plantage plus tard au milieu d'une partie.
- **À l'écriture**, on écrit d'abord un fichier temporaire, puis on le renomme. Si l'écriture échoue en route, l'ancien modèle reste intact.
- Au rechargement, ε reprend là où il en était. Sinon un modèle entraîné se remettrait à jouer au hasard (c'était le cas de la 3ᵉ commande du sujet avant correction).

### 2.9 Les menus de la fenêtre — `interface/menu.py`, `training_view.py`, `evaluation_view.py`

Lancé sans argument, `./snake` ouvre un **menu principal** (les 3 commandes du sujet, elles, ne passent pas par lui) :

- **JOUER** : le lobby. En mode IA, l'agent est **figé** (`figer()`, ε = 0) : il joue au mieux, n'apprend rien et ne modifie aucun fichier. Le bouton CHOISIR ouvre la liste des modèles avec le détail de chacun (parties, pas, situations connues, γ, ε…), validée par OK. Par défaut, c'est le modèle le plus entraîné. Plateau jusqu'à 50×50, vitesse jusqu'à 100 cases/s.
- **ENTRAINEMENT** : la liste des modèles et leur détail ; créer un modèle (nom, γ, ε minimal, `PAS_CIBLE`, plateau, nombre de parties) ou continuer un modèle existant « de X jusqu'à Y parties ». `src/training.py` joue les parties **par tranches** de 25 ms entre deux images, avec la même `play_session` que `-visual off` : la fenêtre reste fluide sans thread. Arrêter, fermer ou Ctrl+C sauvegarde ce qui est déjà joué.
- **EVALUATION** : l'agent figé enchaîne les parties jusqu'à ce qu'une partie atteigne une longueur de 35 (le bonus le plus haut du sujet). Cette partie n'est pas coupée : elle va jusqu'à sa fin, puis on affiche les statistiques de toutes les parties. `src/evaluation.py` photographie chaque pas : sur l'écran des résultats, ← et → rejouent la partie coup par coup.

---

## 3. Les décisions importantes, et pourquoi

| Décision | Pourquoi | Preuve |
|---|---|---|
| Résumer chaque rayon en (première chose vue, distance ≤ 3) | la vision brute est impossible à apprendre | 18 cases → `4^18` ≈ 69 milliards d'états bruts, contre 1 728 |
| Repère égocentrique, 3 actions relatives | la même situation dans 4 orientations devient un seul état ; le demi-tour mortel disparaît | environ 4,7 fois plus d'exemples par case de la table |
| Troncature ≠ mort, et pas de récompense propre | sinon il apprend à mourir tôt, ou à stagner | bugs trouvés par l'audit, testés dans les deux sens |
| Limite de pas = 4 × aire | une limite fixe tronquait 97 % des parties à 30×30 | 2 % / 5 % / 6 % de troncatures à 10×10 / 20×20 / 30×30 |
| Initialisation à +1 | fait explorer ce qu'il ne connaît pas | — |
| α = 1 / n^0,7 | corriger fort au début, puis se stabiliser | — |
| Apprendre en fin de partie, dans l'ordre | rejouer à l'envers ne propage pas la mort en Q-learning | 27,2 contre 25,4 (8 graines) |
| ε sur les pas, `PAS_CIBLE = 5 000` | sortir vite de l'exploration paie ici | à 1 000 parties : 21,7 contre 7,1 avec 50 000 |
| `lire()` séparé de `valeurs()` | `-dontlearn` ne doit jamais modifier le modèle | fichier identique octet pour octet, testé |
| Aucune information hors de la croix, même dans la récompense | aucun risque de −42 | — |

---

## 4. Ce que les audits ont trouvé et fait corriger

Le projet est passé par plusieurs rondes d'audit (la BAA : Boucle d'Audit Adversarial). À chaque ronde, des auditeurs indépendants cherchaient à casser le code : ils le faisaient tourner, et introduisaient volontairement des bugs pour vérifier que les tests les attrapent (le « test de mutation »).

**Les bugs les plus importants, tous corrigés :**

| Bug | Conséquence | Correction |
|---|---|---|
| Le code de départ ne distinguait pas la mort de la troncature | il aurait appris à mourir tôt | `dead`, `truncated`, `end_cause` |
| La troncature valait 0 au lieu de −1 | prime pour stagner jusqu'à la limite | `step()` renvoie `"move"` sur une troncature |
| La limite de pas ignorait la taille du plateau | 97 % de parties tronquées à 30×30 | limite = 4 × aire |
| `-dontlearn` modifiait le fichier du modèle | évaluation faussée | `QTable.lire()` |
| Le calibrage de ε faisait jouer un modèle de 1 000 parties au hasard 2 coups sur 3 | 3ᵉ commande du sujet ratée en démo | `PAS_CIBLE` : de 50 000 à 5 000 |
| `-save` vers un mauvais chemin plantait **après** l'entraînement | tout l'entraînement perdu | chemin vérifié avant de commencer |
| Un modèle abîmé faisait planter le programme, même depuis le lobby | note 0 possible | tout le contenu vérifié au chargement |
| Revenir au lobby puis relancer perdait tout l'apprentissage | apprentissage perdu en silence | `PiloteAgent` garde le même agent |
| Ctrl+C perdait tout l'entraînement | entraînement perdu | arrêt propre et sauvegarde, dans les deux modes |
| `-speed 0` faisait planter la fenêtre | note 0 possible | vitesse bornée |

**Les tests.** Il y a 267 tests, qui passent en 5 secondes. Avec eux, la part des bugs introduits exprès qui sont détectés est passée de 56 % à **92 %**. Il reste 4 petits trous signalés au dernier audit : des cas déjà gérés par le code, mais qu'aucun test ne vérifie encore.

**Des erreurs dans le cours aussi.** L'audit a corrigé plusieurs affirmations fausses de `IA.md` : le comptage des états (36 cases au lieu de 18), la formule du « reward shaping » (il manquait γ), l'ordre des directions (gauche et droite inversées), « aucun algorithme ne franchit ce mur » (faux : il faudrait dire « aucune politique sans mémoire »), le rejeu à l'envers, et la règle de calibrage de ε.

---

## 5. Les pistes testées pour faire mieux

Tout est détaillé avec les chiffres dans `IA.md` §6.8. En résumé :

| Piste | Résultat |
|---|---|
| 3,4 millions de parties (`infini.txt`) | +7 % pour 340 fois plus d'entraînement |
| regarder plus loin dans le futur (γ = 0,97 ; 0,99) | moins bien |
| distances plus longues (4, 5) | pas mieux : plus d'états à apprendre |
| se souvenir de son dernier coup | pas mieux |
| voir l'obstacle caché derrière une pomme | pas mieux |
| faire remonter le malus sur 3, 6, 10 coups ou toute la partie | moins bien : il punit des coups qui étaient bons en général |
| rembobiner à la mort pour essayer d'autres coups | n'apporte rien à expérience égale |
| savoir qu'il s'enroule (tendance de virage) | rattrape, mais ne dépasse pas |
| connaître sa longueur (comptée depuis la croix) | rattrape à 60 000 parties (29,7 contre 29,6) |
| longueur + virages | rattrape (29,5) |
| rembobinage + longueur (+ virages) | atteint le plafond plus vite, sans le dépasser |
| bonus pour l'espace libre visible | aucun effet |
| Double Q-learning (deux tables pour corriger la surestimation) | moins bien : 23,9 contre 28,3 à 3 000 parties, 25,9 contre 27,6 à 20 000 |

**Conclusion :** tout converge vers environ 29,5. La limite vient de ce que le serpent voit, pas de la façon dont il apprend. Pour aller plus loin, il faudrait lui montrer la forme de son corps, ce que la règle de vision interdit.

**Une piste écartée volontairement :** une récompense calculée sur l'espace libre de **tout** le plateau. Défendable, puisque la récompense vient de l'environnement, mais elle aurait pu être lue comme une fuite d'information hors de la croix. On ne prend aucun risque sur le −42.

---

## 6. Ce qui a été fait, dans l'ordre

1. **Lecture critique du cours `IA.md`**, puis première BAA sur l'environnement : séparation de la mort et de la troncature, statistiques (moyenne, médiane, causes de fin), agent de référence aléatoire (`-baseline random`), premiers tests. Poussé sur GitHub.
2. **Étapes 1 à 5, écrites ensemble** : le barème, puis `lire_rayon`, `tourner`, `encode`, et la table Q. Poussé sur GitHub.
3. **Étapes 6 à 12, écrites par Claude** et commentées pour la soutenance : choisir, apprendre, α, l'apprentissage en fin de partie, ε, la sauvegarde, le branchement dans le programme.
4. **BAA en 3 itérations** sur ce code : les bugs de la section 4, 267 tests, 92 % des bugs introduits exprès détectés. Verdict final : GO.
5. **Modèles** : 1, 10, 100, 1 000 et 10 000 sessions, puis `infini.txt` (3 h d'entraînement, 3,4 millions de parties).
6. **Douze pistes d'amélioration** testées et mesurées (section 5), documentées dans `IA.md` §6.8.

**Les commits** (du plus ancien au plus récent) :

```
9bd78df  fix(env): distinguer la mort de la troncature            ┐
d595400  feat(baseline): ajouter un agent de reference aleatoire  │
1d1c59c  fix(session): calculer la recompense sur l'evenement     │ poussés
d7233c8  fix(ui): ne plus afficher une interruption comme une mort│
cca6f29  docs: reecrire le cours d'apprentissage dans IA.md       │
e5398d2  feat(env): ajouter le bareme de recompenses              │
791dcd2  feat(agent): encoder la vision en etat egocentrique      │
46a79ba  docs: preciser que le demi-tour n'est mortel qu'a 3 cases│
ddcfd18  chore: regler VS Code sur la norme flake8 pour Python    ┘
bb76216  feat(agent): ajouter la table Q                          ┐
72f9085  feat(agent): choisir une action et apprendre             │
c475bdc  feat(agent): sauvegarder et recharger un modele          │ locaux, pas encore
fa47e00  feat(models): ajouter les modeles entraines              │ poussés
3efddcf  feat: brancher l'agent dans le programme                 │
e3ea186  docs: corriger le cours d'apres les mesures de l'agent   ┘
```

---

## 7. Commandes utiles

```bash
# vérifier la norme (le sujet impose flake8)
.venv/bin/flake8 main.py src/ tests/

# lancer les 267 tests
.venv/bin/python -m unittest discover -s tests -t .

# entraîner un modèle
./snake -visual off -sessions 1000 -save models/1000sess.txt

# évaluer un modèle sans le modifier
./snake -visual off -sessions 100 -load models/infini.txt -dontlearn

# comparer avec le hasard
./snake -visual off -sessions 100 -baseline random
```

Touches en mode graphique : **N** un pas (en mode pas-à-pas), **P** active ou coupe le pas-à-pas, **Espace** pause, **R** recommencer, **V** afficher la vision, **T** trace dans le terminal, **+ / −** vitesse, **Échap** retour au lobby.

---

## 8. Ce qui reste à faire

1. **Commiter `IA.md`** (la section des douze pistes) et **ce document**.
2. **Pousser** les commits locaux sur GitHub : le sujet ne note que ce qui est dans le dépôt.
3. **Les 4 tests manquants** relevés par le dernier audit (non bloquants) : code de sortie après un échec de `-save` en mode graphique, valeur exacte de la borne des compteurs, dossier sans droit « x », fichier temporaire qui serait un dossier.

---

## 9. Questions de soutenance, avec les réponses

**Pourquoi ne pas donner toute la vision brute à la table ?**
La croix compte 18 cases, chacune peut valoir 4 symboles : environ 69 milliards de combinaisons. Le serpent ne verrait presque jamais deux fois la même, il n'apprendrait rien. On résume chaque rayon en (première chose vue, distance ≤ 3) : au plus 1 728 états.

**Le sujet impose 4 actions et votre agent n'en a que 3 ?**
L'agent choisit parmi tout droit, gauche, droite, puis `tourner` le traduit en UP, LEFT, DOWN ou RIGHT. Le plateau reçoit toujours une des 4 actions du sujet. Le demi-tour est retiré parce qu'il tue dès 3 cases de long.

**Qu'est-ce que le repère égocentrique vous apporte ?**
« Pomme devant » est la même situation quelle que soit l'orientation : 4 orientations deviennent 1 état. Le serpent apprend environ 4,7 fois plus vite. Il ne voit pas plus de choses ; son plafond est le même.

**Comment l'agent connaît-il sa direction ?**
L'environnement la lui donne au début de la partie ; ensuite il la tient à jour lui-même, puisqu'il sait quel coup il vient de jouer.

**Expliquez la formule de mise à jour.**
Cible = récompense du pas + γ × meilleure note de la situation suivante (juste la récompense s'il est mort). Nouvelle note = ancienne + α × (cible − ancienne). La valeur d'un coup, c'est ce qu'il rapporte tout de suite plus ce que vaut la situation où il mène.

**Pourquoi γ = 0,95 ?**
L'agent raisonne sur environ 1 / (1 − γ) = 20 coups : assez pour traverser le plateau jusqu'à une pomme. Des valeurs plus grandes ont été testées et ont donné moins bien.

**Quelle différence entre une mort et une troncature ?**
Une mort n'a pas d'après : la cible est la seule récompense. Une troncature est une limite qu'on impose ; le serpent était vivant, donc on utilise la valeur de la situation suivante, et le pas garde son −1. Sinon il apprendrait à mourir tôt, ou à stagner jusqu'à la limite.

**Pourquoi pas de récompense pour la troncature dans le barème ?**
Ce n'est pas un évènement du jeu. Lui donner 0 offrirait +1 par rapport à tout autre déplacement : atteindre la limite deviendrait le meilleur coup.

**Exploration et exploitation ?**
ε-greedy : avec la probabilité ε il joue au hasard pour découvrir, sinon il prend la meilleure note. ε passe de 1 à 0,01 en 5 000 pas. Avec `-dontlearn`, ε vaut 0.

**Pourquoi la table démarre à +1 ?**
Un pas coûte −1 : une action essayée descend sous +1, les actions jamais essayées paraissent meilleures, il les essaie. C'est une exploration automatique.

**Pourquoi α diminue ?**
La première fois, on prend l'observation en entier (α = 1). Plus un couple est vu, moins on le corrige : la note devient une moyenne stable, malgré les pommes qui tombent au hasard.

**C'est du Q-learning ou autre chose ?**
Du Q-learning tabulaire : la cible utilise la **meilleure** action suivante (`max`), même si le coup réellement joué ensuite était un coup d'exploration. C'est ce qu'on appelle « off-policy ». SARSA, lui, utiliserait le coup réellement joué.

**Pourquoi le serpent plafonne vers 29 ?**
Il ne voit qu'une ligne et une colonne, pas la forme de son corps. Deux positions différentes donnent la même croix : il joue pareil dans les deux, et s'enferme dans l'une. À 10 000 parties, 97 % des morts sont contre son corps. Douze pistes ont été testées : aucune ne passe ce plafond.

**`-dontlearn` modifie-t-il le modèle ?**
Non. L'agent figé ne note rien, ne corrige rien, et lit la table sans jamais y ajouter d'état. Le fichier reste identique octet pour octet, et un test le vérifie.

**Que se passe-t-il si on charge un fichier abîmé ?**
Un message `Erreur : …` et le code de sortie 1, jamais une trace Python. Un modèle entraîné avec un autre encodage est refusé grâce à `version_encodage`.

**Le modèle marche-t-il sur un autre plateau ?**
Oui : l'état ne contient ni coordonnée ni taille, et les distances sont plafonnées à « 3 ou plus ». Un modèle entraîné en 10×10 joue en 20×20 sans réentraînement.
