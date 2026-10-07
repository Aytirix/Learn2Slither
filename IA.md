# Reinforcement Learning — de zéro jusqu'à Learn2Slither

---

## Partie 1 — Le cadre général

### 1.1 Ce que le RL n'est pas

Avant de définir, écartons les confusions classiques.

En **apprentissage supervisé**, on te donne des paires (entrée, bonne réponse). Le modèle apprend à reproduire la bonne réponse. Exemple : 10 000 photos étiquetées "chat" ou "chien".

En **apprentissage non supervisé**, on te donne des données sans étiquettes et le modèle cherche une structure. Exemple : regrouper des clients en segments.

En **apprentissage par renforcement**, personne ne te dit jamais quelle était la bonne action. On te dit seulement, après coup, si ce que tu as fait s'est bien ou mal passé. Et parfois le retour arrive très en retard : tu meurs au coup 50 à cause d'une erreur commise au coup 12.

C'est ce décalage qui fait toute la difficulté et tout l'intérêt du RL.

### 1.2 La boucle fondamentale

Tout problème de RL se ramène à ce schéma :

```
        ┌──────────────────────────────┐
        │                              │
        ▼                              │
   ┌─────────┐    action a_t      ┌────┴────┐
   │  AGENT  │ ─────────────────► │  ENVIR. │
   └─────────┘                    └────┬────┘
        ▲                              │
        │   état s_{t+1}, récompense r_{t+1}
        └──────────────────────────────┘
```

À chaque pas de temps `t` :

1. L'agent observe l'état `s_t`
2. Il choisit une action `a_t`
3. L'environnement applique l'action, passe à l'état `s_{t+1}` et renvoie une récompense `r_{t+1}`
4. On recommence

C'est tout. Le reste du cours consiste à répondre à une seule question : **comment l'agent choisit-il `a_t` de mieux en mieux ?**

### 1.3 Vocabulaire

| Terme | Notation | Définition |
|---|---|---|
| État | `s` | Ce que l'agent perçoit du monde à un instant donné |
| Action | `a` | Un des choix possibles de l'agent |
| Récompense | `r` | Un nombre réel renvoyé par l'environnement après une action |
| Politique | `π` | La stratégie de l'agent : une fonction `état → action` |
| Épisode | | Une partie complète, du départ jusqu'à un état terminal |
| Pas de temps | `t` | Un tour de boucle |
| Transition | | Le quadruplet `(s, a, r, s')` : le matériau brut de l'apprentissage |

Le quadruplet `(s, a, r, s')` est la brique de base. Retiens-le : tout l'apprentissage se fait à partir de ces quatre valeurs.

### 1.4 Le processus de décision markovien (MDP)

Le RL suppose que le problème est un **MDP**. La propriété de Markov dit :

> L'état `s_t` contient toute l'information nécessaire pour prédire la suite. Le passé n'apporte rien de plus.

Autrement dit, si tu connais l'état actuel, savoir comment tu y es arrivé ne change rien à ce qu'il faut faire.

C'est une hypothèse forte et **elle sera partiellement fausse dans ton projet**. On y reviendra en partie 6, parce que c'est précisément ce qui limitera ton score.

---

## Partie 2 — Le retour et l'horizon

### 2.1 Ce que l'agent cherche à maximiser

Naïvement, on pourrait dire : l'agent maximise la récompense immédiate `r`. C'est faux et c'est même une catastrophe.

Un serpent qui maximise `r` immédiat va foncer sur la pomme la plus proche même si ça le coince contre un mur. Il faut maximiser la **somme des récompenses futures**.

On appelle ça le **retour** (return), noté `G_t` :

```
G_t = r_{t+1} + r_{t+2} + r_{t+3} + ...
```

### 2.2 Pourquoi il faut un facteur d'actualisation

Cette somme pose deux problèmes.

D'abord, si l'épisode ne se termine jamais, la somme peut être infinie. On ne peut pas comparer deux infinis.

Ensuite, une récompense dans 200 coups est beaucoup plus incertaine qu'une récompense au prochain coup. Le monde a le temps de changer.

On introduit donc **gamma** (`γ`), un nombre entre 0 et 1, qui déprécie le futur :

```
G_t = r_{t+1} + γ·r_{t+2} + γ²·r_{t+3} + γ³·r_{t+4} + ...
```

Ce qui s'écrit récursivement :

```
G_t = r_{t+1} + γ·G_{t+1}
```

Cette forme récursive est **la clé de tout ce qui suit**. Garde-la en tête.

### 2.3 Interprétation de gamma

| γ | Comportement |
|---|---|
| 0 | Agent myope : ne regarde que la récompense immédiate |
| 0.5 | Une récompense dans 10 coups compte pour 0.1 % de sa valeur |
| 0.9 | Une récompense dans 10 coups compte pour 35 % |
| 0.99 | Une récompense dans 10 coups compte pour 90 % |
| 1 | Toutes les récompenses comptent également (dangereux si pas d'état terminal) |

Une intuition utile : `1/(1-γ)` donne l'ordre de grandeur de l'horizon en nombre de coups. Avec `γ = 0.95`, l'agent raisonne sur environ 20 coups. Avec `γ = 0.9`, environ 10 coups.

Pour un serpent qui doit parfois traverser tout le plateau pour atteindre une pomme, un horizon de 10 coups est un peu court. C'est pour ça qu'on recommande 0.95 plutôt que 0.9.

---

## Partie 3 — Les fonctions de valeur

### 3.1 L'idée centrale

On ne sait pas directement quelle action est la meilleure. Mais si on savait, pour chaque situation, **combien elle vaut**, on pourrait simplement choisir l'action qui mène à la meilleure situation.

D'où l'idée : apprendre une fonction qui évalue les situations.

### 3.2 La fonction V

`V(s)` = le retour espéré si on part de l'état `s` et qu'on suit sa politique ensuite.

C'est une réponse à : « à quel point cette situation est-elle bonne ? »

Problème : `V` ne suffit pas pour décider. Savoir que la situation actuelle vaut 12 ne dit pas quelle action prendre. Il faudrait pouvoir simuler chaque action pour voir où elle mène, donc connaître le modèle de l'environnement.

### 3.3 La fonction Q

`Q(s, a)` = le retour espéré si on est dans l'état `s`, qu'on **prend l'action `a`**, puis qu'on suit sa politique.

C'est une réponse à : « à quel point ce choix-là, dans cette situation-là, est-il bon ? »

Q est ce qu'il nous faut, parce que la décision devient triviale :

```
meilleure_action = argmax_a Q(s, a)
```

Pas besoin de modèle de l'environnement. C'est ce qu'on appelle une méthode **model-free**, et c'est ce que ton sujet impose.

### 3.4 Représentation concrète : la Q-table

Si le nombre d'états est fini et raisonnable, on stocke Q dans un tableau :

```
        │ UP   │ DOWN │ LEFT │ RIGHT
────────┼──────┼──────┼──────┼───────
état 0  │ 2.3  │ -1.4 │ 0.8  │ 5.1
état 1  │ -8.0 │ 3.2  │ 3.1  │ -0.5
état 2  │ 0.0  │ 0.0  │ 0.0  │ 0.0     ← jamais visité
...
```

En Python, un `dict[état] -> list[floats]` fait très bien l'affaire — un flottant par action, donc 3 avec l'encodage égocentrique de §6.6. L'initialisation des états inconnus n'est pas anodine : zéro est le réflexe, une valeur légèrement positive est meilleure, voir §8.4.

**La taille de cette table est le paramètre le plus important de ton projet.** Trop petite : l'agent ne distingue pas des situations différentes. Trop grande : il n'aura jamais assez d'expérience pour remplir les cases.

---

## Partie 4 — L'équation de Bellman et le Q-learning

### 4.1 L'équation de Bellman

Reprenons la forme récursive du retour : `G_t = r_{t+1} + γ·G_{t+1}`.

Appliquée à Q, elle donne l'**équation d'optimalité de Bellman** :

```
Q*(s, a) = r + γ · max_{a'} Q*(s', a')
```

En français : la valeur d'une action, c'est la récompense immédiate plus la valeur actualisée du meilleur choix disponible ensuite.

C'est une équation de point fixe. La vraie fonction Q optimale la satisfait exactement. Toute fonction qui la satisfait est optimale.

### 4.2 Le passage à l'apprentissage

On ne connaît pas `Q*`. On a une estimation `Q` qui est fausse au départ. L'idée du Q-learning est simple :

> Regarde de combien ton estimation viole l'équation de Bellman, et corrige-la un peu dans cette direction.

Formalisons. Après avoir observé une transition `(s, a, r, s')` :

**Cible** (ce que Bellman dit que ça devrait valoir) :
```
cible = r + γ · max_{a'} Q(s', a')
```

**Erreur de différence temporelle** (TD error) :
```
δ = cible - Q(s, a)
```

**Mise à jour** :
```
Q(s, a) ← Q(s, a) + α · δ
```

Soit, tout en un :

```
Q(s, a) ← Q(s, a) + α · [ r + γ · max_{a'} Q(s', a') - Q(s, a) ]
```

**C'est l'intégralité de l'algorithme de Q-learning.** Une ligne.

### 4.3 Décomposition terme par terme

| Terme | Rôle |
|---|---|
| `Q(s, a)` | Mon estimation actuelle |
| `r` | Ce que j'ai réellement gagné, observé, non estimé |
| `max_a' Q(s', a')` | Ma meilleure estimation de ce qui m'attend après |
| `γ` | Combien je fais confiance au futur |
| `[...]` | De combien je me suis trompé |
| `α` | Quelle fraction de l'erreur je corrige |

Le point remarquable : on remplace une partie inconnue (`G_{t+1}`) par une estimation qu'on a déjà (`max Q(s', a')`). On apprend une estimation à partir d'une autre estimation. Ça s'appelle le **bootstrapping**, et c'est ce qui permet d'apprendre sans attendre la fin de l'épisode.

### 4.4 Le cas terminal

Quand `s'` est un état terminal (mort du serpent), il n'y a pas de futur. La cible est simplement :

```
cible = r
```

**Oublier ce cas est le bug numéro un des implémentations de Q-learning.** Si tu bootstrappes après la mort, tu ajoutes une valeur de futur qui n'existe pas, et les Q-valeurs des états dangereux ne descendent jamais assez.

### 4.5 Mourir n'est pas la même chose qu'être interrompu

Il existe un deuxième cas de fin de partie, et le confondre avec le premier est un bug aussi grave que d'oublier le cas terminal.

Pour éviter qu'un agent entraîné tourne en rond à l'infini, on arrête la partie au bout d'un certain nombre de pas sans pomme (voir §7.5). Ce n'est pas une mort : c'est une **troncature**, une limite technique qu'on impose de l'extérieur.

| Fin de partie | Réalité |
|---|---|
| Mur, corps, longueur nulle | Le serpent est mort. Il n'y a **plus d'avenir**. La valeur de la suite vaut 0. |
| Limite de pas atteinte | Le serpent était **vivant et en pleine forme**. Il y avait un avenir. C'est nous qui avons coupé. |

Si tu traites la troncature comme une mort, tu racontes à l'agent : « après plusieurs centaines de pas de jeu correct, le monde s'arrête et tu prends la pénalité de mort ». Il observe alors un gros malus systématiquement au bout de ses parties longues, il en déduit que **vivre longtemps est dangereux**, et il apprend à mourir plus tôt. Tu as fabriqué exactement le comportement que la troncature devait empêcher.

Deux règles, donc :

**Une troncature ne touche pas à la récompense.** Ni pénalité de mort, ni récompense propre : le pas qui a déclenché la troncature est un **déplacement ordinaire** et garde son coût habituel. Le détail compte, et §7.2 explique pourquoi lui donner `0` serait une erreur coûteuse.

**Une troncature bootstrappe.** Le serpent était vivant, donc la situation où il se trouvait avait bien une valeur. On l'utilise.

Autrement dit : **une troncature ne change que `done`.**

```
mort    = evenement est (mur, corps, longueur nulle)    → vrai terminal
tronque = limite de pas atteinte                        → on a coupé le chrono

r = recompense(evenement du pas)      # inchangee par la troncature

si mort:
    cible = r                                  # pas de futur
sinon:
    cible = r + gamma * max(Q[s_suivant])      # il y avait un futur, on l'utilise
```

La phrase à retenir : **le serpent était vivant à cet instant, donc la valeur de sa situation n'est pas zéro.**

Conséquence côté environnement : la troncature doit être un événement **distinct** des causes de mort, pas rangé avec elles. Si ton code met la fin par limite de pas dans la même liste que le mur et le corps, le piège se referme tout seul.

### 4.6 Comment l'information se propage

Prenons un serpent qui meurt contre un mur. La pénalité `-50` est appliquée à la dernière transition. Seule la case `Q(dernier_état, action_fatale)` baisse.

Mais au passage suivant dans l'état d'avant, `max Q(s', a')` est maintenant plus bas, donc la cible de l'état d'avant baisse aussi. Puis celui d'encore avant.

L'information remonte d'un pas par visite. C'est pourquoi il faut beaucoup d'épisodes : la récompense doit se diffuser en arrière à travers la chaîne d'états.

### 4.7 Rejouer la partie à l'envers

Le paragraphe précédent décrit le principal goulot d'étranglement du projet. Il se supprime en six lignes.

**Le problème, chiffré.** Le serpent joue 30 pas et meurt contre le mur. Les mises à jour se font au fil de l'eau :

```
pas 1  → mise à jour faite      (on ne sait pas encore qu'on va mourir)
pas 2  → mise à jour faite      (idem)
...
pas 29 → mise à jour faite      (idem)
pas 30 → MORT, pénalité         ← seule cette case apprend quelque chose
```

À la fin de la partie, **une seule case de la table** sait que ce mur est mauvais. Le pas 29 ne l'apprendra qu'à sa prochaine visite, le pas 28 à celle d'après. Pour qu'une chaîne de 30 pas comprenne le danger, il faut donc repasser des dizaines de fois par les mêmes états.

**Le correctif.** On garde les transitions de la partie dans une liste, et à la fin on **rejoue la liste à l'envers**.

```
trajectoire = []

# pendant la partie
trajectoire.ajouter((s, a, r, s_suivant, mort))

# à la fin de la partie
pour (s, a, r, s_suivant, mort) dans inverse(trajectoire):
    apprendre(s, a, r, s_suivant, mort)
```

**Pourquoi l'ordre inverse change tout.** Quand on met à jour le pas 29, le pas 30 a **déjà** encaissé la pénalité. Donc 29 la voit immédiatement. Puis 28 voit 29, puis 27 voit 28. Toute la chaîne apprend la mort **dans la même partie**, au lieu d'en 30 parties.

Gain constaté couramment : 3 à 10 fois moins d'épisodes pour la même performance. C'est le levier le plus rentable du projet après l'encodage de l'état, et c'est la version la plus simple de ce que font les traces d'éligibilité (§10.4).

Note : avec le rejeu inverse, la mise à jour « en direct » pendant la partie devient redondante. Choisis l'un ou l'autre, pas les deux, sinon chaque transition compte double et ton `α` effectif est faussé.

---

## Partie 5 — Exploration et exploitation

### 5.1 Le dilemme

Si l'agent choisit toujours `argmax Q(s, a)`, il ne testera jamais les actions dont il sous-estime la valeur. Or au départ, toutes les valeurs sont à zéro et donc arbitraires.

Un agent purement glouton se verrouille sur la première chose qui a marché par hasard.

Mais un agent purement aléatoire n'utilise jamais ce qu'il a appris et n'atteint jamais les états intéressants du jeu.

Il faut les deux, dans des proportions qui évoluent.

### 5.2 Epsilon-greedy

La stratégie standard :

```
avec probabilité ε   : action aléatoire uniforme
avec probabilité 1-ε : argmax_a Q(s, a)
```

Et on fait décroître `ε` au cours de l'entraînement : beaucoup d'exploration au début, presque plus à la fin.

#### Décroître sur les pas, pas sur les épisodes

Le schéma que l'on voit partout applique la décroissance **à chaque fin d'épisode** :

```
ε ← max(ε_min, ε · decay)     à chaque fin d'épisode     ← à éviter ici
```

Le problème est propre à ce projet : la durée d'un épisode passe de **5 pas** au début (l'agent meurt immédiatement) à **200 ou 300 pas** à la fin (il sait survivre). Or ce qui consomme de l'exploration, c'est le **pas**, pas l'épisode.

Conséquence : avec une décroissance par épisode, les premiers milliers d'épisodes — très courts — épuisent presque tout le budget d'`ε`, et les épisodes longs de la fin, qui contiennent l'essentiel des pas joués, se déroulent avec un `ε` déjà au plancher. Le budget d'exploration est écrasé sur le début de l'entraînement, là où l'agent n'a encore aucune structure à explorer.

**On décroît donc sur le compteur de pas cumulés.** Le plus simple et le plus facile à calibrer est une décroissance linéaire :

```
epsilon = max(epsilon_min, 1.0 - pas_total / pas_cible)
```

Un seul paramètre, `pas_cible` : le nombre de pas au bout duquel `ε` atteint son plancher. Aucun exponentiel à régler, et le comportement est exactement celui qu'on a écrit.

Si tu préfères la forme multiplicative, elle s'applique aussi par pas, et son facteur se calcule au lieu de se deviner :

```
decay = (epsilon_min / epsilon_depart) ** (1 / pas_cible)
```

#### Le piège de l'argmax : départager les ex-aequo

`argmax` a l'air inoffensif. Il ne l'est pas, parce qu'en Python il renvoie **le premier** maximum, pas un maximum au hasard.

```python
Q[s] = [0.0, 0.0, 0.0]
Q[s].index(max(Q[s]))       # → 0, toujours, indéfiniment
```

Or au départ **toute la table vaut zéro**. Donc :

- ton agent non entraîné n'est pas aléatoire, il est « toujours l'action n°0 ». Il rentre dans le mur de la même façon à chaque partie ;
- chaque fois qu'il découvre un état neuf, il rejoue cette même action par défaut. Seul `ε` le sauve, et `ε` diminue ;
- ton modèle « 1 session » aura l'air bizarrement rigide alors que le sujet attend qu'il soit visiblement mauvais.

Le correctif, trois lignes :

```python
best = max(Q[s])
candidats = [i for i, v in enumerate(Q[s]) if v == best]
a = random.choice(candidats)
```

Le tirage ne s'applique qu'**entre ex-aequo**. Si une action est seule en tête, elle est choisie comme avant : ça ne change rien au cas normal, ça ne répare que le cas dégénéré.

### 5.3 Calibrer la décroissance

Règle pratique : `ε` doit atteindre son plancher vers **50 à 70 % des pas de ton entraînement**. Ça laisse une phase finale où l'agent affine une politique déjà bonne au lieu de la bruiter.

Il faut donc une estimation du nombre total de pas. Elle est grossière et c'est suffisant : lance 200 épisodes, regarde la durée moyenne, multiplie par le nombre d'épisodes prévu.

| Pas totaux estimés | `pas_cible` (≈ 60 %) |
|---|---|
| 100 000 | 60 000 |
| 300 000 | 180 000 |
| 1 000 000 | 600 000 |

Diagnostic : si la performance stagne très tôt puis ne bouge plus jamais, `pas_cible` est trop petit. Si elle reste chaotique jusqu'à la fin, il est trop grand.

C'est un des paramètres que le sweep (§8.5) règle le mieux, parce que son effet est monotone et lisible sur la courbe.

### 5.4 Note sur l'évaluation

Pour mesurer la performance d'un modèle, il faut `ε = 0`. Sinon tu mesures un mélange de la politique et du bruit.

C'est ce que devra faire l'option `-dontlearn` du sujet : `ε = 0` et pas de mise à jour de Q. **Elle n'est pas encore câblée** : la ligne de commande la lit et la range dans `config.learn`, mais aucun module ne consulte ce champ aujourd'hui — il n'y a pas encore d'agent à figer. À brancher à l'étape 3, en même temps que `-load`.

---

## Partie 6 — Concevoir l'état (la partie qui décide de tout)

### 6.1 Pourquoi c'est le vrai sujet

L'algorithme de Q-learning tient en une ligne et tu ne le modifieras jamais. En revanche, la façon dont tu transformes le monde en `état` détermine :

- si l'agent peut distinguer les situations qui exigent des réponses différentes
- combien de cases la table contient
- combien d'épisodes il faut pour la remplir

C'est là que se joue la totalité de ta performance.

### 6.2 La malédiction de la dimension

Comptons ce que la vision brute représente vraiment. Sur un plateau 10×10, la croix centrée sur la tête contient la ligne (10 cases) plus la colonne (10 cases), moins la tête comptée deux fois : **18 cases visibles** en plus de la tête. Chacune de ces 18 cases peut valoir 4 symboles utiles (`S`, `G`, `R`, `0`) — `W` n'apparaît qu'au bout d'un rayon et `H` seulement au centre, donc ni l'un ni l'autre n'ajoute de combinaisons libres.

Ça donne une borne de `4^18 ≈ 69 milliards` d'états. La vraie valeur est plus basse (le corps du serpent est contigu, il n'y a que deux `G` et une `R` sur le plateau), mais l'ordre de grandeur suffit : c'est hors de portée.

Chaque état ne serait visité qu'une fois, jamais deux. Aucune généralisation, aucun apprentissage.

**Il faut compresser.** Et compresser signifie décider ce qui est pertinent et ce qui ne l'est pas.

### 6.3 Le compromis fondamental

```
état pauvre                                          état riche
    │                                                     │
    ├─ table petite                          table énorme ─┤
    ├─ converge vite                     converge jamais  ─┤
    ├─ plafonne bas                    plafond théorique  ─┤
    │                                        très haut     │
```

Tu cherches le point où l'agent a juste assez d'information pour bien décider, et pas une case de plus.

### 6.4 L'encodage retenu : premier symbole + distance plafonnée

Pour chaque direction, on lit le rayon depuis la tête vers l'extérieur et on en extrait **deux** informations :

**Le premier symbole non vide rencontré** → `W`, `S`, `G` ou `R`, soit **4 valeurs**.

**Sa distance, plafonnée** → `1`, `2`, `3 ou plus`, soit **3 valeurs**.

```
rayon "00G00W"  →  ('G', 3+)     première chose vue : pomme verte, loin
rayon "S0W"     →  ('S', 1)      corps collé à la tête
rayon "000W"    →  ('W', 3+)     couloir libre jusqu'au mur
rayon "0R0W"    →  ('R', 2)      pomme rouge à deux cases
```

Soit **4 × 3 = 12 valeurs par direction**.

#### Deux propriétés qui ne sont pas des hasards

**Le premier symbole est toujours défini.** `Board.vision_rays()` ajoute la case hors plateau au bout de chaque rayon, et `cell_char` la rend en `W` : toute chaîne de vision finit donc par un `W`. Il n'existe aucun cas « rien vu ». Pas de valeur fourre-tout, pas d'ambiguïté à l'encodage.

**Le danger immédiat est déjà dedans.** `('W', 1)` ou `('S', 1)` signifie exactement « la case adjacente me tue ». Inutile d'ajouter un booléen de danger : il serait redondant.

#### Ce que cet encodage donne, et que le réflexe naïf perd

Le réflexe classique est d'encoder un booléen de danger sur la case adjacente, plus « y a-t-il une pomme sur cette ligne ». Trois informations essentielles disparaissent alors, et ce ne sont pas des détails.

**La distance à la pomme.** Sans elle, « pomme verte devant à 1 case » et « pomme verte devant à 7 cases » sont le même état. L'agent ne peut ni arbitrer entre deux pommes visibles, ni savoir qu'il est sur le point d'en attraper une.

**La place disponible.** Un booléen de danger ne regarde que la case collée à la tête. À deux cases, un mur, un segment de corps et du vide deviennent indiscernables : l'agent ne voit la falaise que quand son pied est déjà dessus. Ici, `('S', 1)` contre `('S', 2)` contre `('W', 3+)` donne **une notion d'espace libre dans chaque direction**.

C'est la perte la plus coûteuse, parce que l'auto-piégeage est la cause de mort dominante d'un serpent long.

**Le mur et le corps comme premier symbole.** Avec seulement `{G, R, rien}`, un segment de corps à trois cases devant est encodé « rien » — et l'agent croit la voie libre. Ici il lit `('S', 3+)`.

#### Il est purement relatif

Aucune coordonnée absolue, aucune taille de plateau. Et c'est précisément le **plafonnement** de la distance qui le garantit : un modèle entraîné en 10×10 tourne en 20×20 sans réentraînement, parce que « 3 ou plus » veut dire la même chose partout. Le bonus « taille de plateau variable » du sujet est validé par construction.

Il respecte aussi la contrainte de vision : on ne lit que les 4 rayons, jamais le plateau. Pas de pénalité `-42`.

### 6.5 Le curseur de richesse : les paliers de distance

Le plafond à `3+` n'est pas sacré, c'est ton bouton de réglage, et son effet est chiffrable à l'avance. En comptant à partir de l'encodage égocentrique de §6.6 (3 directions, 3 actions) :

| Paliers de distance | Val./dir | États | Cellules | Visites / cellule |
|---|---|---|---|---|
| `{1, 2, 3+}` | 12 | 1 728 | 5 184 | ~58 |
| `{1, 2, 3-4, 5+}` | 16 | 4 096 | 12 288 | ~24 |
| `{1, 2, 3, 4, 5+}` | 20 | 8 000 | 24 000 | ~12,5 |

La dernière colonne suppose 5 000 épisodes à ~60 pas de moyenne, soit ~300 000 transitions.

**Commence à 3 paliers.** Si la courbe plafonne et que le sweep (§8.5) ne débloque rien, passe à 4. Un seul paramètre à changer, et tu sais d'avance ce que ça coûte en densité d'échantillons.

### 6.6 L'encodage égocentrique

Jusqu'ici on a décrit le monde dans le repère du plateau : haut, bas, gauche, droite. C'est le réflexe naturel, et c'est un gaspillage.

**Le problème.** Un serpent qui va vers la droite avec une pomme devant lui, et le même serpent qui va vers la gauche avec une pomme devant lui, sont deux états distincts dans une table absolue. Pourtant c'est le même problème. Il y a 4 rotations possibles de chaque situation, donc chaque leçon doit être réapprise 4 fois, chacune à partir de zéro.

**La solution.** Décrire le monde par rapport à la direction de déplacement du serpent : **devant, gauche relative, droite relative**. Les 4 rotations d'une situation fusionnent en un seul état.

Effet chiffré : table divisée par 4, et surtout expérience accumulée par état multipliée par 4. À nombre d'épisodes constant, chaque Q-valeur est estimée sur 4 fois plus d'échantillons. C'est le même gain que si tu quadruplais ton entraînement.

#### Le facteur 4, et son compte exact

Le « divisé par 4 » est le bon modèle mental, mais il faut savoir d'où il vient et où il n'est pas exact.

**Le modèle mental.** Une situation égocentrique `(devant, gauche, droite)` peut se présenter sous 4 caps. Chacun donne un état absolu différent, parce que l'emplacement du **cou** — toujours `('S', 1)` — change de case. Le repère égocentrique replie ces 4 rotations en un seul état : d'où le facteur 4.

**Le compte exact.** Ce facteur n'est pas tout à fait 4, et se tromper là-dessus est facile. On pourrait écrire « 4 emplacements possibles pour le cou × `12³` pour les trois autres = `6 912` états absolus ». **C'est faux** : ce calcul compte des couples (cap, situation) et non des états, donc il compte deux fois les situations où **plusieurs** directions valent `('S', 1)` — un serpent replié voit son corps ailleurs que derrière lui.

Le majorant correct s'obtient par inclusion-exclusion : les états absolus atteignables sont ceux dont au moins un emplacement porte le cou, soit tous les états moins ceux qui n'en portent aucun :

```
12⁴ − 11⁴  =  20 736 − 14 641  =  6 095 états     (et non 6 912 : 817 de trop)
```

Rapport réel : `6 095 / 1 728 = 3,53`. Le facteur est donc « **jusqu'à** 4 », exactement 4 sur les situations non ambiguës, un peu moins en moyenne.

Et supprimer la quatrième direction n'est possible *que* parce qu'on est égocentrique : en repère absolu, on ne sait pas laquelle jeter.

#### Le prix comparé, en cellules à remplir

C'est le seul chiffre qui compte vraiment : une Q-table, ce sont des cellules `(état, action)`, et chacune doit être visitée assez souvent pour valoir quelque chose.

Toutes les lignes sont en **nominal** (toutes les combinaisons), pour être comparables entre elles :

| Encodage | Repère | Dir. | Val./dir | États | Actions | **Cellules** |
|---|---|---|---|---|---|---|
| Danger booléen + pomme | absolu | 4 | 6 | 1 296 | 4 | **5 184** |
| §6.4 | absolu | 4 | 12 | 20 736 | 4 | **82 944** |
| **§6.4 + égocentrique** | égocentrique | 3 | 12 | 1 728 | 3 | **5 184** |

L'encodage retenu coûte **exactement le même nombre de cellules** que la version pauvre en repère absolu, tout en portant la distance, l'espace libre et la distinction mur/corps. Ce n'est pas une formule d'effet, c'est une égalité.

**En pratique**, une table en dictionnaire n'alloue que les états réellement rencontrés. Il faut donc comparer les majorants atteignables du paragraphe précédent, et non le nominal :

| Encodage | États atteignables | Cellules | Visites / cellule à 300 000 transitions |
|---|---|---|---|
| §6.4 en absolu | ≤ 6 095 | ≤ 24 380 | **~12** |
| §6.4 en égocentrique | ≤ 1 728 | ≤ 5 184 | **~58** |

Un facteur 4,7 en densité d'échantillons. Douze visites par cellule, ce n'est pas zéro, mais c'est une Q-valeur estimée sur douze observations dans un environnement partiellement aléatoire : très bruitée. **L'égocentrique ne rend pas les features de §6.4 possibles, il les rend fiables.**

#### Conséquence obligatoire sur les actions

Si l'état est égocentrique, **les actions doivent l'être aussi**. Sinon l'apprentissage est incohérent.

Contre-exemple : état « pomme devant », action absolue `RIGHT`. Si le serpent va vers la droite, `RIGHT` avance vers la pomme. S'il va vers le haut, `RIGHT` tourne à angle droit. Même état, même action, conséquences opposées. La table apprend du bruit.

L'agent raisonne donc sur **3 actions relatives** : tout droit, tourner à gauche, tourner à droite. Le demi-tour est absent : dès que le serpent mesure 3 cases ou plus, il tue instantanément contre le cou.

Précision vérifiable dans `board.py` : à 2 cases ou moins, le demi-tour n'est **pas** mortel, parce que la queue libère la case au même moment où la tête y arrive. Le serpent ne descend sous 3 cases qu'en mangeant des pommes rouges, donc le cas est rare, et la perte d'un coup légal dans ce cas précis est négligeable face au gain.

#### La conversion vers les actions du sujet

L'environnement attend `UP/DOWN/LEFT/RIGHT`, comme l'impose le sujet. La traduction se fait à la frontière agent/environnement.

**Attention au piège** : le dépôt expose déjà `board.DIRECTIONS = (UP, LEFT, DOWN, RIGHT)`, qui est un ordre **anti-horaire**. Si tu réutilises cette constante en croyant qu'elle tourne dans l'autre sens, gauche et droite seront inversées — et un serpent qui tourne systématiquement du mauvais côté est un bug très pénible à diagnostiquer, parce qu'il apprend quand même, en moins bien.

Avec l'ordre réel du dépôt, `(UP, LEFT, DOWN, RIGHT)` :

```
tout droit  → indice inchangé
gauche      → (indice + 1) % 4
droite      → (indice - 1) % 4
```

Exemples, vérifiables sur la constante :

```
direction courante : UP (indice 0)     direction courante : RIGHT (indice 3)

  tout droit  → UP                       tout droit  → RIGHT
  gauche      → LEFT   (indice 1)        gauche      → UP     (indice 0)
  droite      → RIGHT  (indice 3)        droite      → DOWN   (indice 2)
```

Si tu préfères raisonner dans le sens horaire, définis ton propre tuple `[UP, RIGHT, DOWN, LEFT]` et inverse les deux formules — mais alors n'indexe **jamais** `board.DIRECTIONS` avec.

L'agent produit bien une des 4 actions du sujet. Il raisonne simplement dans son propre repère avant de traduire.

#### D'où vient la direction courante

L'encodage égocentrique a besoin de savoir dans quel sens va le serpent. La réponse est : **l'agent le sait tout seul.** Il vient de choisir son action, donc il sait où il va. Il tient sa propre direction en mémoire, et rien ne circule du plateau vers lui.

```python
class Agent:
    def choose(self, vision):
        etat = encode(vision, self.direction)      # self.direction : mémoire interne
        relative = self.politique(etat)            # tout droit / gauche / droite
        self.direction = tourne(self.direction, relative)
        return self.direction                      # direction absolue, comme l'exige le sujet
```

Trois conséquences, toutes favorables.

**La signature ne change pas.** `choose(vision)` renvoie un tuple de direction absolue, exactement ce que la boucle de jeu attend déjà — vérifié dans les deux boucles, headless et graphique. L'encodage égocentrique ne coûte donc aucune modification de l'interface. (La boucle elle-même devra être réécrite, mais pour une autre raison : le rejeu inverse de §4.7.)

**Le demi-tour devient impossible.** Avec 3 actions relatives, l'agent ne peut pas produire un retournement à 180°, qui est une mort instantanée contre le cou dès 3 cases de longueur. Une cause de mort supprimée par construction plutôt que par apprentissage.

**L'initialisation en début de partie est simple.** Au reset, le serpent reçoit une direction aléatoire. L'environnement la maintient déjà dans `board.direction` ; l'agent la lit une fois au début de l'épisode, puis la met à jour lui-même à chaque action. C'est le cap du serpent, pas un contenu de case.

#### Ce que ça apporte, et ce que ça n'apporte pas

L'égocentrique ne contient **pas plus** d'information que l'absolu. Il contient la même, mieux organisée. Entraînés à l'infini, les deux convergent vers la même politique et le même plafond.

Ce qu'il apporte, c'est la vitesse : à budget d'épisodes réaliste, la différence est nette.

Il apporte aussi un budget. Diviser la table par 4 te laisse la place de multiplier la richesse de l'état par 4 sans payer en convergence. **C'est comme ça qu'il faut le voir : l'égocentrique seul te rend plus rapide, l'égocentrique qui finance un état plus riche te rend plus fort.**

#### Le contre-argument honnête

La symétrie gauche/droite n'est pas parfaite dans ce jeu. Le corps du serpent traîne derrière lui d'une manière qui casse partiellement l'invariance par rotation. Deux situations fusionnées en un seul état peuvent donc mériter des réponses légèrement différentes. C'est une perte d'information, faible mais réelle.

Le gain de densité devrait largement l'emporter. Mais garde les deux encodages derrière un flag et compare les courbes de longueur moyenne : c'est peu de travail et ça remplace une opinion par une mesure.

#### Aller plus loin : la symétrie miroir — OPTIONNEL, pas pour tout de suite

> **Statut : optionnel, noté ici pour mémoire.** On ne le développe pas dans un premier temps. C'est écrit pour qu'on sache que la piste existe et ce qu'elle vaut, si on veut y revenir.

L'encodage égocentrique fusionne les 4 rotations d'une situation. Le miroir va un cran plus loin.

« Pomme à ma droite, mur à ma gauche » et « pomme à ma gauche, mur à ma droite » sont **le même problème vu dans une glace**. La bonne réponse est la même, inversée.

Donc chaque fois qu'on apprend une transition, on apprend aussi son reflet : on échange les features gauche et droite de l'état, et on échange l'action gauche et l'action droite.

```
apprendre(s, a, r, s2, mort)
apprendre(miroir(s), miroir_action(a), r, miroir(s2), mort)
```

Effet : deux fois plus d'expérience par partie, et la table rétrécit encore puisque les états symétriques fusionnent.

Même réserve que pour les rotations, en plus forte : le corps du serpent traîne derrière lui d'une façon qui n'est pas symétrique en miroir, donc on perd un peu d'information. D'où le flag `-mirror on/off` et la comparaison des courbes plutôt qu'un pari.

Priorité basse : à considérer après le rejeu inverse (§4.7), l'initialisation optimiste (§8.4) et le sweep (§8.5).

### 6.7 Pistes d'enrichissement

L'encodage de §6.4 contient déjà la distance au danger et la distance à la pomme. Ce qui reste, par ordre de rapport bénéfice/coût :

**Un palier de distance en plus.** Le curseur de §6.5 : de `{1,2,3+}` à `{1,2,3-4,5+}`. Table × 2,4, et ça suffit souvent.

**« Une verte existe-t-elle plus loin sur ce rayon ? »** C'est le trou connu de §6.4 : si une pomme rouge est devant une verte sur le même rayon, seule la rouge est vue, et l'agent fuit une direction qui contenait une récompense. Un booléen par direction : `24³ = 13 824` états, 41 472 cellules. Jouable, mais pas en premier.

**Longueur de corps visible.** Combien de segments de son propre corps le serpent voit dans chaque direction, plafonné à 2 ou 3. Aide contre l'auto-piégeage, au-delà de ce que donne déjà la distance au premier `S`.

À chaque ajout, refais le calcul de la colonne « visites par cellule » de §6.5 avant de coder. Un état 20 fois plus grand demande à peu près 20 fois plus d'expérience, et ça se voit tout de suite dans le tableau.

### 6.8 La limite structurelle : l'observabilité partielle

Le serpent ne voit que 4 lignes. Il ne voit ni les diagonales, ni la forme globale de son corps.

Conséquence : **deux situations physiquement différentes peuvent produire exactement le même état**. L'une est un piège mortel, l'autre non. L'agent ne peut pas les distinguer, donc il joue la même chose dans les deux, donc il meurt dans l'une des deux.

C'est un **POMDP** (Partially Observable MDP), et ça viole l'hypothèse de Markov sur laquelle repose la garantie de convergence du Q-learning.

Pratiquement : ton serpent plafonnera. Ce n'est pas un défaut de ton code, c'est imposé par la règle de vision du sujet.

**Attention à la formulation, en soutenance.** Dire « aucun algorithme ne franchit ce mur » est faux et un correcteur peut le relever. Le sujet contraint l'**observation** — quatre rayons — pas la **mémoire** de l'agent. Or sur un POMDP, une politique qui garde une trace du passé (historique d'observations, état de croyance, réseau récurrent) domine strictement une politique sans mémoire : c'est un résultat standard.

La phrase juste est donc : **aucune politique sans mémoire ne franchit ce mur.** Le plafond est celui du Q-learning tabulaire sur l'observation courante, ce qui est bien ce que le sujet impose d'implémenter.

Quant au chiffre du plafond, il reste à mesurer sur ce projet — ne cite pas une valeur que tu n'as pas observée.

---

## Partie 7 — Concevoir les récompenses

### 7.1 Ce que tu communiques réellement

Les récompenses ne décrivent pas *comment* réussir. Elles décrivent *ce que* réussir signifie. L'agent trouvera un chemin, et souvent pas celui que tu imaginais.

### 7.2 Un jeu de valeurs fonctionnel

| Événement | Récompense |
|---|---|
| Pomme verte | +20 |
| Pomme rouge | −10 |
| Rien (déplacement simple) | −1 |
| Game over (mur, corps, longueur nulle) | −50 |

**Il n'y a volontairement pas de ligne « troncature ».** C'est le point délicat, et écrire « troncature → 0 » est une erreur qui coûte cher.

Une troncature n'est pas un événement du jeu : c'est une décision de l'environnement d'arrêter de regarder. Le pas qui l'a déclenchée est un **déplacement ordinaire**, et il garde son `−1`.

Si on lui attribue `0`, on lui offre `+1` de plus qu'à n'importe quel autre pas sans pomme. Le coup qui atteint la limite devient donc le meilleur coup disponible, et l'agent apprend à stagner jusqu'à la limite — exactement la pathologie que la troncature devait supprimer, et le symptôme listé en §9.2 sous « il a appris à survivre sans manger ».

La règle, donc : **une troncature ne change que `done`, jamais la récompense.** Côté code, cela veut dire que `step()` ne doit pas remplacer l'événement du pas par un événement « timeout » : la cause de fin se lit ailleurs (`end_cause`), et la récompense continue de se calculer sur l'événement du pas.

### 7.3 Les ratios qui comptent

Ce ne sont pas les valeurs absolues qui importent, mais leurs rapports.

**Mort contre pas.** Si la pénalité par pas est trop lourde face à la mort, l'agent découvre que mourir vite arrête l'hémorragie. Il se suicide au tour 2. C'est la pathologie la plus fréquente et la plus déroutante quand on la voit pour la première fois.

**Pomme verte contre pas.** Si la pomme rapporte trop peu, l'agent préfère survivre en tournant en rond sans jamais manger. La longueur stagne à 3.

**Pomme rouge contre pomme verte.** La rouge doit être clairement négative sans être létale. Si elle est trop punitive, l'agent devient paralysé dès qu'une rouge est visible.

### 7.4 Le reward shaping — OPTIONNEL, et à ne pas tenter en premier

> **Statut : levier optionnel, volontairement reporté.** À ne regarder qu'après le rejeu inverse (§4.7), l'initialisation optimiste (§8.4), l'`α` par visites (§8.1) et le sweep (§8.5). Si la performance suffit sans, on n'y touche pas. Cette section existe pour qu'on ne retombe pas dans les pièges décrits plus bas si on y revient.

**L'intention.** L'agent ne touche `+20` qu'en mangeant. Entre deux pommes il n'encaisse que des `−1`. Il met donc très longtemps à comprendre que se diriger vers une pomme est bon. D'où l'envie de l'aider en route.

#### La version naïve, et pourquoi elle détruit l'agent

« +1 chaque fois que je me rapproche de la pomme ». L'agent trouve ceci en quelques centaines d'épisodes :

```
pas 1 : je me rapproche  → +1
pas 2 : je m'éloigne     →  0     (on n'avait prévu de bonus que pour le rapprochement)
pas 3 : je me rapproche  → +1
pas 4 : je m'éloigne     →  0
```

Aller-retour sur deux cases, indéfiniment, `+1` tous les deux pas, **sans jamais manger**. Il a trouvé un distributeur de points et il ne jouera plus jamais au serpent.

Le bug est précis : on a compté le `+1` et oublié le `−1`.

#### La version correcte : une différence de notes de position

On attache la note **à la position**, pas au mouvement. Chaque situation reçoit une note `Φ`, et le bonus est la différence entre la note d'arrivée et la note de départ — **avec le `γ` devant la note d'arrivée** :

```
bonus = γ · Φ(après) − Φ(avant)
```

**Le `γ` n'est pas décoratif, et l'oublier casse tout.** C'est la forme exacte du théorème de Ng, Harada & Russell (1999) : ce bonus-là ne peut jamais changer la politique optimale. La version sans `γ`, elle, la change dès que `γ < 1` — et §8.2 recommande `γ = 0.95`.

Vérifié sur un MDP jouet à trois états résolu par itération de valeur, avec `Φ(A) = 0`, `Φ(B) = 10` et une sortie rapportant `+1` :

| Shaping | Action optimale en A |
|---|---|
| aucun | sortir (Q = 1,000 contre 0,902) |
| `Φ(après) − Φ(avant)` | **boucler indéfiniment vers B** (Q = 5,128 contre 1,000) |
| `γ·Φ(après) − Φ(avant)` | sortir (Q = 1,000 contre 0,902) — politique préservée |

La version naïve fabrique donc exactement le distributeur qu'on croyait avoir fermé.

Avec la forme correcte et `Φ = −(distance à la pomme verte visible)`, `γ = 0.95` :

| Ce qui se passe | Calcul | Bonus |
|---|---|---|
| Je me rapproche | 0,95×(−4) − (−5) | **+1,2** |
| Je m'éloigne | 0,95×(−5) − (−4) | **−0,75** |

**Pourquoi c'est infarmable.** Sur une trajectoire entière, les bonus se télescopent : leur somme actualisée vaut exactement `γᵗ·Φ(état final) − Φ(état initial)`. Elle ne dépend donc que du départ et de l'arrivée, et le terme `γᵗ` tend vers zéro.

Le total est donc **borné**, quelle que soit la longueur de la boucle. Avec `Φ(départ) = −5`, tourner en rond rapporte `+0,49` sur 2 pas, `+2,01` sur 10 pas, `+4,97` sur 100 pas, et plafonne à `+5` — jamais davantage. Le gain existe donc, mais il est plafonné une fois pour toutes : impossible de le farmer indéfiniment, ce qui est exactement la propriété qu'on cherchait. (Attention à ne pas dire que boucler rapporte *moins* que faire un tour : c'est faux, ça rapporte plus, simplement pas indéfiniment.)

À noter que ce télescopage n'a lieu qu'avec le `γ`. Sans lui, seule la somme **non actualisée** s'annule, et ce n'est pas celle-là que le Q-learning maximise.

#### Le piège mortel : la valeur de « je ne vois aucune pomme »

C'est ici que tout se joue, et le réflexe naturel est faux.

Il faut bien donner une note aux situations où **aucune pomme verte n'est visible sur les 4 rayons**. Le réflexe est de mettre `Φ = 0`. Déroulons :

```
pomme visible à 5 cases     → Φ = -5
plus aucune pomme visible   → Φ =  0

le serpent bouge et perd la pomme de vue :
bonus = 0 − (−5) = +5
```

**+5 pour avoir perdu la pomme de vue.** Et symétriquement `−5` au moment où il en découvre une. Tu viens de construire un agent qui apprend à **fuir les pommes**.

La correction : « je ne vois aucune pomme » n'est pas une situation neutre, c'est la **pire**. Elle doit donc porter la pire note, strictement inférieure à n'importe quelle distance possible :

```
aucune pomme visible                  → Φ = -(size + 1)     soit -11 en 10x10
pomme visible a size-1 cases (le max) → Φ = -(size - 1)     soit  -9 en 10x10
pomme visible a 1 case                → Φ =  -1
```

La sentinelle doit se **calculer depuis la taille du plateau**, pas être écrite en dur. Une constante calibrée sur 10×10 redeviendrait moins mauvaise qu'une pomme lointaine dès que la taille du plateau dépasse 12, et le piège « fuir les pommes » se rouvrirait — ce qui détruirait au passage l'indépendance à la taille revendiquée en §6.4.

Avec `γ = 0.95` et la sentinelle à `−(size + 1) = −11` sur un 10×10 :

| Ce qui se passe | Calcul | Bonus |
|---|---|---|
| Je me rapproche | 0,95×(−4) − (−5) | **+1,20** |
| Je m'éloigne | 0,95×(−5) − (−4) | **−0,75** |
| Je perds la pomme de vue | 0,95×(−11) − (−5) | **−5,45** |
| Je découvre une pomme | 0,95×(−5) − (−11) | **+6,25** |

Les signes sont tous bons. À noter une conséquence de `Φ ≤ 0` et `γ < 1` : rester sur la sentinelle rapporte `0,95×(−11) − (−11) = +0,55` par pas. Ça n'invalide pas le théorème — la politique optimale est préservée — mais ça compense une partie du `−1` par pas, et c'est un effet de plus à surveiller si on active ce shaping.

#### Ce que ce shaping fait vraiment, et pourquoi on le reporte

Le serpent ne voit une pomme verte que si elle partage sa ligne ou sa colonne, soit **18 cases sur 99** (la croix hors tête, cf. §6.2), donc environ **18 %** par pomme. Avec deux pommes vertes, la probabilité qu'aucune ne soit visible vaut `C(81,2)/C(99,2) = 0,67` : **le serpent ne voit aucune pomme verte à peu près deux fois sur trois.**

Donc les deux tiers du temps, `Φ` reste collé à la sentinelle et le bonus ne dit rien d'utile sur la direction à prendre. Ce que ce shaping récompense réellement, ce n'est pas « avancer vers la pomme », c'est **s'aligner** sur une ligne ou une colonne qui en contient une — les gros `−5,45` et `+6,25`. C'est d'ailleurs la bonne compétence pour ce jeu, mais ce n'est plus la mécanique simple qu'on croyait mettre en place.

Conclusion : le rapport bénéfice/risque est mauvais **au départ du projet**. Le rejeu inverse (§4.7) attaque le même problème — l'agent apprend trop lentement — en six lignes et sans toucher aux récompenses. Un shaping mal réglé, lui, produit un agent subtilement faux, c'est-à-dire le pire type de bug à débusquer.

#### Sur le risque de `-42`

Aucun, si `Φ` se calcule uniquement depuis les rayons. Un rayon est une chaîne du type `"00G0W"` ; la distance à la pomme, c'est la position du `G` dedans. C'est littéralement la vision. Ne jamais calculer une distance depuis les coordonnées du plateau.

### 7.5 Terminaison anti-boucle

Ajoute un compteur de pas sans pomme. Au-delà de la limite, l'épisode se termine.

**Valeur retenue pour ce projet : `4 × taille²`**, soit 400 pas sur le 10×10 imposé.

Elle est proportionnelle à l'**aire** et non à la longueur du serpent. C'est contre-intuitif, donc voici la mesure qui tranche — agent aléatoire non suicidaire, 150 parties par configuration, pourcentage de parties finissant sur le garde-fou :

| Règle | 10×10 | 20×20 | 30×30 |
|---|---|---|---|
| `100 × longueur` | 23 % | **75 %** | **97 %** |
| `4 × aire` | 9 % | 11 % | 17 % |

Une limite qui ignore la taille du plateau transforme le comportement normal en troncature dès que le plateau grandit : à 30×30, la quasi-totalité des parties finit sur le chronomètre et non sur le comportement de l'agent. Tes données d'entraînement sont alors noyées.

Et le terme de longueur, lui, ne résiste pas à l'examen : un serpent long a *moins* de cases libres à explorer, donc il n'a pas besoin de plus de pas. Aucune mesure ne l'appuie, l'aire en a une.

Cette valeur doit être la même dans le doc et dans le code — une limite qui diffère entre les deux rend tous tes chiffres incomparables.

Sans ça, un agent bien entraîné qui a appris à survivre peut tourner indéfiniment et bloquer ton entraînement.

Ce n'est **pas** une récompense, c'est une condition de terminaison de l'environnement. Et ce n'est **pas** une mort : elle bootstrappe, et elle laisse au pas sa récompense habituelle. Relire §4.5 et §7.2 avant de l'implémenter, les deux pièges sont là.

---

## Partie 8 — Les hyperparamètres

### 8.1 Alpha, le taux d'apprentissage

Contrôle la fraction de l'erreur qu'on corrige à chaque mise à jour.

| α | Effet |
|---|---|
| 0.01 | Très stable, très lent |
| 0.1 | Bon compromis par défaut |
| 0.3 | Rapide, commence à osciller |
| 1.0 | Écrase l'estimation à chaque fois, ne converge pas en environnement stochastique |

Départ conseillé pour un `α` fixe : **0.1**. Environnement partiellement aléatoire (position des pommes), donc il faut moyenner sur plusieurs visites, donc ne pas monter trop haut.

#### Mieux : décroître α avec le nombre de visites

Le défaut d'un `α` fixe : après mille passages par le même état, l'agent déplace encore son estimation de 10 % à chaque fois. Comme les pommes apparaissent au hasard, la valeur ne se stabilise jamais vraiment, elle tremble.

Le principe : **plus j'ai vu cette situation, moins je bouge.**

```python
n[(s, a)] += 1                       # n valant 1 a la premiere visite
alpha = 1.0 / n[(s, a)] ** 0.7
```

Attention au décalage d'un rang : avec `1/(1 + n)^0.7` après incrémentation, la première visite ne corrigerait que 0,62 de l'erreur, et l'argument « je prends l'observation en entier » tomberait.

| Visite n° | α | Comportement |
|---|---|---|
| 1 | 1.00 | je prends l'observation en entier — bien mieux que d'en jeter 90 % |
| 10 | 0.20 | je corrige encore franchement |
| 100 | 0.04 | j'affine |
| 1000 | 0.008 | je ne bouge presque plus, la valeur est établie |

Résultat : apprend vite sur les situations rares, arrête de trembler sur les situations bien connues. C'est exactement ce qu'il faut dans un environnement qui comporte une part de hasard.

Coût : un second dictionnaire de compteurs, trois lignes. L'exposant `0.7` peut être n'importe quelle valeur entre 0.5 et 1 — c'est une condition théorique de convergence, inutile d'y toucher.

### 8.2 Gamma, l'actualisation

Départ conseillé : **0.95**, soit un horizon d'environ 20 coups.

Si le serpent est trop myope et fonce dans les murs pour attraper une pomme adjacente, monte à 0.97. Si les valeurs divergent et explosent, redescends.

### 8.3 Epsilon, l'exploration

Voir partie 5. `1.0 → 0.01`, décroissance ajustée à ton nombre d'épisodes.

### 8.4 L'initialisation de la table

§3.4 propose d'initialiser les états inconnus à zéro. Une valeur légèrement **positive** vaut mieux :

```python
Q = defaultdict(lambda: [1.0, 1.0, 1.0])     # au lieu de [0.0, 0.0, 0.0]
```

**Pourquoi ça marche.** Un pas normal coûte `−1`. Donc dès qu'une action est réellement essayée, sa valeur descend sous `+1`. Les actions jamais tentées, elles, restent à `+1`, donc au-dessus.

`argmax` préfère alors automatiquement ce qui n'a jamais été essayé. L'agent explore **méthodiquement**, et exactement là où il n'a aucune information — au lieu d'explorer au hasard avec `ε`, ce qui gaspille des coups à re-tester du déjà-connu.

Effet concret : la table se remplit beaucoup plus vite, et tu peux faire décroître `ε` plus rapidement.

À ne pas exagérer : à `+100`, aucune expérience réelle ne redescendrait jamais sous la valeur d'un état inconnu, et l'agent explorerait à vie. `+1` suffit à battre le `−1` du pas.

### 8.5 Le sweep : régler par mesure, pas par intuition

§8.6 dit de ne toucher qu'un paramètre à la fois et de mesurer. C'est juste, mais à la main ça donne : éditer le fichier, lancer, attendre, noter le chiffre, recommencer. Trente fois. Tu en feras cinq.

Un sweep est un script d'une trentaine de lignes qui le fait à ta place :

```python
for alpha in (0.05, 0.1, 0.2):
    for gamma in (0.9, 0.95, 0.99):
        for pomme in (10, 20, 50):
            entraine(5000 épisodes, headless, seed fixe)
            score = evalue(100 parties, epsilon=0)
            print(alpha, gamma, pomme, score)
```

27 configurations. En headless, sans pygame et sans `print` (§11.4), 5 000 épisodes prennent quelques secondes chacun. L'ensemble tourne le temps d'un café.

Tu récupères un tableau trié par longueur moyenne et tu prends la meilleure ligne. Ces chiffres alimentent directement le bonus « résultats et statistiques » du sujet.

Deux règles pour que ça veuille dire quelque chose : **seed fixe** (sinon tu compares du bruit) et **évaluation à `ε = 0`** (§5.4).

### 8.6 Ordre de réglage

Ne touche qu'un paramètre à la fois et mesure. Priorité :

1. **Les récompenses** (impact énorme)
2. **La décroissance d'epsilon** (impact fort)
3. **Gamma** (impact moyen)
4. **Alpha** (impact faible tant qu'il est entre 0.05 et 0.2)

---

## Partie 9 — Diagnostiquer un agent qui n'apprend pas

Le RL échoue silencieusement. Le programme tourne, aucune exception, et l'agent est nul. Voici comment lire les symptômes.

| Symptôme | Cause probable |
|---|---|
| Meurt en 2-3 coups même après 10 000 épisodes | Pénalité par pas trop lourde face à la mort |
| Longueur bloquée à 3, survit longtemps | Récompense de pomme trop faible |
| Progresse puis s'effondre brutalement | α trop grand, ou bootstrap sur état terminal |
| Q-valeurs qui explosent (millions) | γ ≥ 1, ou pas de traitement du terminal |
| Ne progresse plus après 500 épisodes | ε décroît trop vite |
| Bruit permanent, jamais de convergence | ε ne descend pas assez, ou état mal conçu |
| Toutes les Q-valeurs restent à 0 | La mise à jour n'est pas appelée, ou état recalculé après l'action |
| Va systématiquement dans la même direction au début | `argmax` ne départage pas les ex-aequo (§5.2) |
| Apprend à mourir tôt, plafonne alors qu'il survivait bien | La troncature est traitée comme une mort (§4.5) |
| La table se remplit très lentement, peu d'états visités | Initialisation à zéro plutôt qu'optimiste (§8.4) |
| Apprend, mais il faut des dizaines de milliers d'épisodes | Pas de rejeu inverse (§4.7) |

### 9.1 Le bug le plus vicieux

Calculer `s` **après** avoir bougé le serpent au lieu d'avant. Tu apprends alors `Q(s', a)` au lieu de `Q(s, a)`. Le programme tourne, rien ne plante, et l'agent n'apprend rien de cohérent.

Ordre correct, impérativement :

```
vision  = board.vision_chars()          # observer AVANT d'agir
action  = agent.choose(vision)
event   = board.step(action)            # evenement du pas
apres   = board.vision_chars()          # observer APRES
agent.learn(vision, action, recompense(event), apres, board.dead)
```

Deux détails du même ordre, faciles à rater : c'est `board.dead` et non « la partie est finie » qu'on transmet (§4.5), et la récompense se calcule sur l'événement du **pas** et non sur la cause de fin (§7.2).

### 9.2 Instrumente ton entraînement

Enregistre, par tranche de 100 épisodes :

- longueur maximale
- longueur moyenne
- durée moyenne (nombre de pas)
- valeur de ε
- nombre d'états distincts visités

La courbe de longueur moyenne est ton outil de diagnostic principal. Elle doit monter, se stabiliser, et ne pas s'effondrer.

Le nombre d'états visités est aussi révélateur : s'il plafonne à 50 sur les 1 728 états possibles (§6.6), ton agent ne voit qu'une fraction du monde et quelque chose bloque.

Ces courbes servent aussi directement au bonus « résultats et statistiques » du sujet.

#### La répartition des causes de fin

C'est le diagnostic le plus rentable du projet, et il tient en un `Counter` sur l'événement de fin de partie. `SessionStats` l'enregistre et `causes_summary()` l'affiche :

```
causes de fin : collision avec la queue = 167 (84 %), collision avec un mur = 33 (16 %)
```

Il ne dit pas seulement que ça va mal, il dit **quoi corriger** :

| Ce que tu lis | Ce que ça signifie |
|---|---|
| Majorité **mur** | l'encodage du danger ne suffit pas, l'agent ne voit pas venir — vérifier les paliers de distance (§6.5) |
| Majorité **corps** | il s'auto-piège : il lui manque de l'information sur son propre corps (§6.7) |
| Majorité **trop de pas sans pomme** | il a appris à survivre sans manger : la pomme ne rapporte pas assez face au coût du pas (§7.3) |

#### Le maximum n'est pas une mesure

Le sujet demande la longueur maximale, donc il faut l'afficher. Mais pour **régler** quoi que ce soit, c'est la moyenne qui compte : un modèle dont le max est 22 peut être moins bon en moyenne qu'un modèle dont le max est 18. `SessionStats` expose donc `mean_length` et `median_length` à côté du maximum.

#### La barre à battre

`src/baselines.py` fournit un agent qui tire une direction au hasard, lançable avec `-baseline random`. C'est le plancher de performance mesuré :

```
$ .venv/bin/python main.py -visual off -sessions 200 -baseline random -seed 1
200 sessions — longueur : moyenne = 3.04, mediane = 3.0, maximale = 4 | duree : moyenne = 3.3, maximale = 21
causes de fin : collision avec la queue = 167 (84 %), collision avec un mur = 33 (16 %)
```

Le hasard meurt surtout contre son propre cou, parce qu'une direction sur quatre est un demi-tour — ce qui rappelle au passage pourquoi les 3 actions relatives de §6.6 suppriment cette cause de mort par construction.

Un agent qui n'atteint pas nettement plus que 3 de longueur moyenne n'a rien appris, quel que soit son maximum.

---

## Partie 10 — Les variantes de mise à jour

Le sujet écrit, page 10 : *« You can train multiple models using different update approaches for the Q function. »* Ce ne sont donc pas des curiosités théoriques, c'est une piste que le sujet te propose explicitement.

**Ça n'implique pas d'écrire plusieurs agents.** Un agent, une Q-table, un format de fichier. Un flag `-update` et un `if` sur une ligne :

```python
if self.regle == "qlearning":
    cible = r + gamma * max(Q[s2])
else:  # sarsa
    cible = r + gamma * Q[s2][a2]
```

Tu lances l'entraînement deux fois avec un flag différent et tu obtiens deux **fichiers de modèle** — `models/1000sess-qlearning.json` et `models/1000sess-sarsa.json` — pas deux bouts de code. Le sujet demande justement plusieurs modèles.

Coût total : une vingtaine de lignes. Bénéfice : quand le correcteur demande « vous avez essayé autre chose ? », tu réponds avec deux courbes au lieu d'un avis.

### 10.1 SARSA

Même structure, seule la cible change :

```
Q-learning : cible = r + γ · max_a' Q(s', a')
SARSA      : cible = r + γ · Q(s', a')     avec a' l'action réellement choisie ensuite
```

Les deux répondent à la même question — « après mon coup, combien vaut la situation où j'arrive ? » — mais pas de la même façon :

| | Sa réponse |
|---|---|
| Q-learning | « elle vaut ce qu'elle vaudrait si j'y jouais parfaitement » |
| SARSA | « elle vaut ce qu'elle va vraiment me rapporter, vu le coup que je vais réellement jouer ensuite — **coup aléatoire d'exploration compris** » |

**Ce que ça donne à l'écran.** Imagine un couloir le long du mur, et le chemin le plus court vers la pomme passe collé à ce mur.

> **Q-learning** suppose qu'il jouera toujours parfaitement. Longer le mur ne lui coûte donc rien. Il longe le mur.
>
> **SARSA** sait qu'avec une probabilité `ε` il va jouer au hasard. Et collé au mur, un coup au hasard, c'est la mort. Il attribue donc une valeur plus basse aux cases qui touchent le mur : **il garde une marge de sécurité.**

C'est l'exemple classique du « cliff walking » de Sutton & Barto : Q-learning marche au bord de la falaise, SARSA fait le détour prudent.

Les noms savants, en clair :

| | Ce qu'il apprend |
|---|---|
| Q-learning — *off-policy* | la valeur du joueur idéal, alors qu'il joue comme un explorateur imparfait |
| SARSA — *on-policy* | la valeur du joueur qu'il est vraiment, `ε` compris |

**Lequel est meilleur ici ?** On ne le sait pas avant de mesurer. En théorie, quand `ε` tombe à 0.01, les deux convergent vers la même politique. En pratique, pendant l'entraînement, SARSA survit souvent plus longtemps parce qu'il est prudent — et « rester en vie longtemps » est explicitement demandé par le sujet.

Attention à un détail d'implémentation : SARSA a besoin de `a'`, l'action **suivante**. Il faut donc la choisir avant de faire la mise à jour, ce qui décale légèrement la boucle. C'est la seule vraie différence de structure.

### 10.2 Expected SARSA

Cible = espérance sur la politique ε-greedy plutôt que max ou action tirée. Moins de variance que SARSA, souvent légèrement meilleur que les deux.

### 10.3 Double Q-learning

Le `max` du Q-learning surestime systématiquement les valeurs (biais d'optimisme). Double Q-learning maintient deux tables et les fait s'évaluer mutuellement pour corriger ce biais.

### 10.4 Traces d'éligibilité, Q(λ)

Au lieu de propager la récompense d'un seul pas en arrière, on la propage sur toute la trajectoire récente avec un poids décroissant. Accélère nettement la convergence quand les récompenses sont rares. N'augmente pas le plafond de performance.

Le **rejeu inverse de §4.7 en est la version pauvre et suffisante** : même objectif, six lignes, aucun paramètre `λ` à régler. C'est pour ça qu'il est recommandé au cœur du projet et pas ici.

### 10.5 DQN

Remplace la table par un réseau de neurones qui approxime `Q(s, a)`. Indispensable quand l'espace d'états est trop grand pour être énuméré.

Sur ton projet avec ~1 700 états (§6.6) : **inutile et contre-productif**. Une table stocke exactement ce qu'un réseau approxime mal. Le réseau n'a d'intérêt que si tu choisis un encodage d'état très riche.

### 10.6 Dyna-Q — OPTIONNEL

> **Statut : optionnel.** À ne considérer que si le rejeu inverse (§4.7) ne suffit pas, c'est-à-dire si l'entraînement reste trop lent après l'avoir mis en place. Les deux attaquent le même problème ; on commence par le moins cher.

**Ce que fait le Q-learning simple.** L'agent n'apprend que de ce qui vient de se produire. Un pas réel = une mise à jour. 10 000 pas joués = 10 000 leçons. Le nombre de leçons est plafonné par le nombre de pas joués.

**Ce qu'ajoute Dyna-Q.** L'agent tient en plus un **carnet** de ce qu'il a observé : « quand j'étais dans l'état 412 et que j'ai tourné à gauche, j'ai pris −1 et je me suis retrouvé dans l'état 87 ». Après chaque pas réel, il tire dix lignes au hasard dans ce carnet et refait la mise à jour dessus, comme s'il les revivait.

```python
modele[(s, a)] = (r, s2, mort)          # le carnet, rempli en jouant

# après chaque vrai pas :
for _ in range(10):
    s, a = random.choice(list(modele))
    r, s2, mort = modele[(s, a)]
    update(s, a, r, s2, mort)            # exactement la même fonction
```

**Différence avec le plan de base :** aucune, sauf le nombre de mises à jour. Même algorithme, même Q-table, même équation de Bellman, même interface d'agent. Simplement 10 à 50 fois plus de leçons pour le même nombre de parties jouées, donc une table qui converge en beaucoup moins de parties.

**Est-ce autorisé ?** Oui. Le sujet interdit tout modèle autre qu'une Q-table ou un réseau de neurones. Ici le modèle appris **est** une Q-table mise à jour par Bellman ; le carnet n'est que de la mémoire de transitions, pas un modèle appris qui décide.

**Différence avec §4.7, puisque les deux se ressemblent.** Ils visent la même chose — augmenter le nombre de leçons utiles par pas réel — mais pas de la même manière :

| | Rejeu inverse (§4.7) | Dyna-Q (§10.6) |
|---|---|---|
| Ce qu'il rejoue | la partie qui vient de se terminer, dans l'ordre inverse | des transitions anciennes, tirées au hasard |
| Ce qu'il résout surtout | faire remonter la mort le long de la chaîne | densifier l'apprentissage partout |
| Coût | ~6 lignes | ~15 lignes + un dictionnaire qui grossit |
| Statut ici | recommandé, au cœur du projet | optionnel, seulement si besoin |

Ils sont compatibles et leurs effets s'ajoutent. Mais on met le rejeu inverse en place d'abord, on mesure, et on ne sort Dyna-Q que si la mesure le réclame.

---

## Partie 11 — Architecture logicielle

Le sujet impose une structure modulaire. Elle correspond exactement au découpage naturel du RL.

```
┌─────────────────┐
│   ENVIRONMENT   │  plateau, pommes, corps du serpent
│                 │  applique une action, détecte les collisions
└────────┬────────┘  ne connaît ni l'agent ni l'affichage
         │
         ▼
┌─────────────────┐
│   RECOMPENSE    │  evenement du pas → nombre
└────────┬────────┘  (§7.2 : la troncature n'y touche pas)
         │
         ▼
┌─────────────────┐
│      AGENT      │  choose(vision) / learn(s, a, r, s', mort)
│                 │  Q-table, save() / load()
│  ┌───────────┐  │
│  │INTERPRETER│  │  vision + cap → etat encode (§6.4, §6.6)
│  └───────────┘  │
└─────────────────┘

┌─────────────────┐
│     DISPLAY     │  pygame pour le plateau
└─────────────────┘  print pour vision + action

┌─────────────────┐
│      MAIN       │  parsing CLI, boucle d'épisodes
└─────────────────┘
```

### 11.1 Règles de découplage

L'environnement ne doit **jamais** importer l'agent. Et l'agent ne doit **jamais** recevoir le plateau : la seule chose qui franchit la frontière est le **dictionnaire de vision** produit par `board.vision_chars()`, quatre chaînes de symboles, plus le cap courant du serpent.

Ce découplage n'est pas cosmétique : c'est ce qui garantit structurellement que tu ne violes pas la contrainte de vision, et c'est ce que le correcteur vérifiera.

**Où vit l'interpréteur.** Deux découpages sont défendables, et il faut en choisir un et s'y tenir :

- **interpréteur séparé** : un module transforme la vision en état encodé, et l'agent ne voit que l'état. Correspond au schéma du sujet, mais ajoute un objet qui doit connaître le cap du serpent.
- **interpréteur dans l'agent** : l'agent reçoit la vision et l'encode lui-même (`encode(vision, self.direction)`, cf. §6.6). C'est ce que fait le code actuel, dont la boucle appelle `agent.choose(vision)`.

Ce doc retient le **second**, parce qu'il est déjà l'interface du dépôt et qu'il évite de faire circuler le cap dans un troisième objet. Le module d'encodage reste un fichier distinct (`interpreter.py`), simplement appelé par l'agent plutôt que par la boucle.

### 11.2 Pseudocode de la boucle principale

Ce pseudocode suit l'interface réelle du dépôt : `board.step(direction)` rend **l'événement de jeu du pas** (une chaîne : déplacement, pomme, mort), la récompense est calculée à part par une fonction de récompense, et la fin de partie se lit sur `board.alive` / `board.dead` / `board.end_cause`.

```
pas_total = 0                                   # cumule sur TOUS les episodes

pour chaque episode:
    board.reset()
    trajectoire = []

    tant que board.alive:
        vision = board.vision_chars()
        action = agent.choose(vision)           # -> direction absolue (§6.6)

        pas_total += 1                          # compteur global, tous episodes
        agent.epsilon = max(epsilon_min, 1 - pas_total / pas_cible)   # §5.2

        event = board.step(action)              # evenement du PAS, pas la fin
        r = recompense(event)                   # une troncature n'y touche pas

        # `board.dead` et non `not board.alive` : une troncature bootstrappe
        apres = vision si board.dead sinon board.vision_chars()

        si mode_apprentissage:
            trajectoire.ajouter((vision, action, r, apres, board.dead))

        si affichage_actif:
            display.render(board)
            print(vision, action)

    # rejeu inverse : la mort remonte toute la chaîne en une seule partie (§4.7)
    si mode_apprentissage:
        pour (s, a, r, s_prime, mort) dans inverse(trajectoire):
            agent.learn(s, a, r, s_prime, mort)

    stats.enregistrer(board.max_length, board.steps, board.end_cause)
```

Trois pièges sont désamorcés dans ce squelette, et ce sont les trois de la partie 4 :

- c'est `board.dead` — et non « la partie est finie » — qui est transmis à `learn`, sinon une troncature se comporte comme une mort (§4.5) ;
- la récompense se calcule sur `event`, l'événement du **pas**, et non sur la cause de fin, sinon atteindre la limite rapporte une prime (§7.2) ;
- `ε` décroît sur le compteur de **pas cumulés**, mis à jour **dans** la boucle et non en fin d'épisode — un épisode entraîné fait 200 à 300 pas, pendant lesquels `ε` resterait figé (§5.2).

**Ce squelette remplace la boucle actuelle**, qui appelle `learn` en direct à chaque pas. Les deux ne se cumulent pas : §4.7 prévient qu'apprendre deux fois la même transition fausse l'`α` effectif.

### 11.3 Pseudocode de la mise à jour

```
fonction learn(s, a, r, s_prime, mort):
    si mort:
        cible = r                                # pas de futur (§4.4)
    sinon:
        cible = r + gamma * max(Q[s_prime])      # vaut aussi pour une troncature (§4.5)

    n[(s, a)] += 1                               # §8.1, n >= 1
    alpha = 1 / n[(s, a)] ** 0.7

    Q[s][a] = Q[s][a] + alpha * (cible - Q[s][a])
```

Et le choix de l'action, avec le départage des ex-aequo de §5.2. La méthode s'appelle `choose` et reçoit la **vision**, pas l'état déjà encodé : c'est l'interface du dépôt (§11.1), et c'est l'agent qui encode.

```
fonction choose(vision):
    s = encode(vision, self.direction)           # §6.4, §6.6

    si hasard() < epsilon:
        relative = action relative au hasard
    sinon:
        best = max(Q[s])
        candidats = [i pour i, v dans Q[s] si v == best]
        relative = un element au hasard parmi candidats

    self.direction = tourne(self.direction, relative)
    retourner self.direction                     # direction absolue
```

### 11.4 Entraînement headless

L'entraînement doit pouvoir tourner sans pygame et sans `print`. Un `print` par pas sur 50 000 épisodes coûte des heures.

Prévois dès le départ deux flags séparés : affichage graphique, et sortie terminale.

### 11.5 Le format du fichier de modèle

Le sujet exige de pouvoir exporter et réimporter l'état d'apprentissage, et de rendre au minimum trois modèles (1, 10 et 100 sessions). Ce n'est pas la sauvegarde qui pose problème, c'est le **format**.

**Le piège.** Tu améliores ton encodage d'état en semaine 2, puis tu recharges un modèle entraîné avec l'ancien encodage. Les clés de la table ne correspondent plus à rien. **Aucune exception, aucun message.** L'agent se comporte simplement comme s'il n'avait jamais appris, et tu vas chercher le bug ailleurs pendant des heures.

**Le correctif : donner une carte d'identité au fichier.**

```json
{
  "encoder_version": 2,
  "update_rule": "qlearning",
  "hyperparams": {"alpha": "1/n^0.7", "gamma": 0.95, "epsilon_min": 0.01},
  "episodes": 100,
  "qtable": { "...": [1.2, -3.4, 0.5] }
}
```

Au chargement, si `encoder_version` ne correspond pas à celui du code : message clair et refus de charger. Jamais de dégradation silencieuse.

Bénéfice secondaire en soutenance : quand on te demande comment tel modèle a été entraîné, la réponse est écrite dans le fichier.

JSON plutôt que `pickle` : lisible, inspectable, et le sujet donne `.txt` comme exemple, donc rien n'impose un format binaire.

---

## Partie 12 — Plan de travail

### Étape 1 — L'environnement seul
Plateau, pommes, serpent, déplacement, collisions. Teste avec des actions aléatoires. Vérifie que la longueur augmente sur pomme verte, diminue sur rouge, que les collisions sont détectées.

### Étape 2 — L'interpréteur
Extraction de la vision, affichage terminal en croix, encodage de l'état. Vérifie visuellement que la vision affichée correspond au plateau.

### Étape 3 — L'agent avec Q-table
Structure de données, `choose(vision)`, `learn`, sauvegarde/chargement. Teste que Q évolue.

À mettre en place dès cette étape, parce que ce sont des conditions de correction et non des optimisations :
- départage aléatoire des ex-aequo dans `argmax` (§5.2)
- `mort` et `tronque` séparés ; la troncature bootstrappe et ne modifie pas la récompense du pas (§4.5, §7.2)
- format de modèle avec `encoder_version` (§11.5)

### Étape 4 — La boucle et les stats
Entraîne 1 000 épisodes en headless. Trace la courbe de longueur moyenne. **Ne passe pas à la suite tant qu'elle ne monte pas.**

### Étape 5 — Accélération de l'apprentissage
Dans cet ordre, en mesurant après chacun :
1. rejeu inverse de la trajectoire (§4.7) — le plus gros gain
2. initialisation optimiste de la table (§8.4)
3. `α` décroissant par nombre de visites (§8.1)

### Étape 6 — Réglage par sweep
Écris le sweep (§8.5) et laisse-le tourner. Ajuste les récompenses, epsilon et gamma d'après le tableau qu'il produit, pas à l'intuition. Objectif : dépasser 10 de longueur de façon fiable.

### Étape 7 — Affichage et CLI
pygame, step-by-step, vitesse configurable, tous les arguments du sujet.

### Étape 8 — Modèles finaux
Snapshots à 1, 10, 100 épisodes, plus un entraînement long pour le meilleur modèle.

### Étape 9 — Ce qui reste, si le temps le permet
Par ordre d'intérêt, tous optionnels et tous derrière un flag : variantes de mise à jour (§10.1, §10.2, §10.3), symétrie miroir (§6.6), shaping en différence de notes (§7.4), Dyna-Q (§10.6).

---

## Partie 13 — Points de vigilance pour la soutenance

- `flake8` propre sur l'intégralité du dépôt, **`tests/` compris** :
  `.venv/bin/flake8 main.py src/ tests/`
- la suite de tests passe : `.venv/bin/python -m unittest discover -s tests -t .`
  (module `unittest` de la bibliothèque standard, aucune dépendance à installer)
- **tout est commité** : `git status` propre. Le sujet précise que le dépôt sera
  cloné dans un répertoire vide — un fichier non suivi n'existe pas pour le correcteur
- aucun crash, y compris avec des arguments absurdes
- le mode pas-à-pas attend réellement une touche
- la vision terminale correspond au plateau graphique
- `-dontlearn` ne modifie effectivement pas la Q-table (vérifie par comparaison avant/après)
- le modèle 1 session doit être visiblement mauvais, sinon ta démonstration de progression ne tient pas
- savoir expliquer chaque terme de l'équation de mise à jour
- savoir expliquer pourquoi tu as compressé l'état et ce que tu as perdu

---

## Glossaire

**Agent** — L'entité qui décide.
**Bootstrapping** — Mettre à jour une estimation à partir d'une autre estimation.
**Épisode** — Une partie complète jusqu'à un état terminal.
**Exploration / exploitation** — Tester du nouveau contre utiliser ce qu'on sait.
**Greedy** — Qui choisit toujours la valeur maximale.
**MDP** — Markov Decision Process, le cadre formel du RL.
**Model-free** — Qui n'a pas besoin de connaître les règles de transition de l'environnement.
**Off-policy** — Apprend une politique différente de celle qu'il exécute.
**On-policy** — Apprend la politique qu'il exécute.
**Politique (π)** — La stratégie : une fonction état vers action.
**POMDP** — MDP partiellement observable : l'agent ne voit pas tout l'état réel.
**Q-valeur** — Valeur estimée d'un couple (état, action).
**Retour (G)** — Somme actualisée des récompenses futures.
**TD error (δ)** — Écart entre la cible de Bellman et l'estimation actuelle.
**Terminal** — État de fin d'épisode, sans futur.