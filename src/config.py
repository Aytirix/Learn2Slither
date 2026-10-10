"""Configuration d'une session, partagee par le lobby, le jeu et le CLI."""

import math

PILOT_AI = "ia"
PILOT_HUMAN = "joueur"
PILOTS = (PILOT_AI, PILOT_HUMAN)

MIN_SIZE = 5
MAX_SIZE = 50
PAS_TAILLE = 5
TAILLES = tuple(range(MIN_SIZE, MAX_SIZE + 1, PAS_TAILLE))
# Vitesse maximale : autant de pas que la machine en calcule, sans attente
# entre deux pas (voir Game._avancer_au_maximum).
VITESSE_MAX = math.inf
# De 5 en 5 jusqu'a 20, de 10 en 10 jusqu'a 50, puis 75, 100 et MAX.
SPEEDS = (1.0, 5.0, 10.0, 15.0, 20.0, 30.0, 40.0, 50.0, 75.0, 100.0,
          VITESSE_MAX)
VITESSE_FINIE_MAX = SPEEDS[-2]
DEFAULT_SPEED = 5.0

# EVALUATION : longueur a atteindre. Tant qu'aucune partie n'y arrive, on
# en rejoue une autre. 35 = le palier de bonus le plus haut du sujet.
OBJECTIF_DEFAUT = 35
OBJECTIFS = tuple(range(5, 101, 5))


def valeur_voisine(valeurs, actuelle, delta):
    """Valeur suivante (delta > 0) ou precedente (delta < 0) de la liste.

    `actuelle` peut ne pas etre dans la liste (-size 12, -speed 6 en ligne
    de commande) : on passe alors a la premiere valeur au-dessus ou
    au-dessous, sans sauter de cran. 12 -> 15 ou 10, et non 20 ou 5.
    """
    if delta > 0:
        plus_grandes = [v for v in valeurs if v > actuelle]
        return plus_grandes[0] if plus_grandes else valeurs[-1]
    if delta < 0:
        plus_petites = [v for v in valeurs if v < actuelle]
        return plus_petites[-1] if plus_petites else valeurs[0]
    return actuelle


def libelle_vitesse(vitesse):
    """'5 / s', '100 / s' ou 'MAX'."""
    if vitesse == VITESSE_MAX:
        return "MAX"
    return "{:g} / s".format(vitesse)


class GameConfig:
    """Reglages d'une session, venus du lobby ou de la ligne de commande."""

    def __init__(self, pilot=PILOT_AI, model=None, size=10,
                 speed=DEFAULT_SPEED,
                 seed=None, sessions=1, save_path=None, visual=True,
                 learn=True, step_by_step=False, trace=True, baseline=None):
        self.pilot = pilot if pilot in PILOTS else PILOT_AI
        self.model = model
        self.size = max(MIN_SIZE, min(MAX_SIZE, size))
        # Bornee comme la taille : 0 fait diviser par zero dans la boucle
        # graphique, NaN fige le serpent. L'infini est permis : c'est la
        # vitesse MAX, que le jeu traite a part.
        if not isinstance(speed, (int, float)) or math.isnan(speed):
            speed = DEFAULT_SPEED
        if speed != VITESSE_MAX:
            speed = max(SPEEDS[0], min(VITESSE_FINIE_MAX, speed))
        self.speed = speed
        self.seed = seed
        self.sessions = max(1, sessions)
        self.save_path = save_path
        self.visual = visual
        self.learn = learn
        self.step_by_step = step_by_step
        self.trace = trace
        self.baseline = baseline
        self.objectif = OBJECTIF_DEFAUT

    @property
    def ai_driven(self):
        return self.pilot == PILOT_AI

    def toggle_pilot(self, delta=1):
        """Bascule entre pilotage IA et pilotage humain."""
        index = (PILOTS.index(self.pilot) + delta) % len(PILOTS)
        self.pilot = PILOTS[index]

    def change_size(self, delta):
        """Plateau de 5 en 5 : 5, 10, 15... 50."""
        self.size = valeur_voisine(TAILLES, self.size, delta)

    def change_objectif(self, delta):
        """Longueur visee par l'evaluation, de 5 en 5."""
        self.objectif = valeur_voisine(OBJECTIFS, self.objectif, delta)

    def change_speed(self, delta):
        self.speed = valeur_voisine(SPEEDS, self.speed, delta)
