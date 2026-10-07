"""Configuration d'une session, partagee par le lobby, le jeu et le CLI."""

import math

PILOT_AI = "ia"
PILOT_HUMAN = "joueur"
PILOTS = (PILOT_AI, PILOT_HUMAN)

MIN_SIZE = 5
MAX_SIZE = 30
SPEEDS = (1.0, 2.0, 4.0, 6.0, 10.0, 15.0, 20.0, 30.0)
DEFAULT_SPEED = 6.0


class GameConfig:
    """Reglages d'une session, venus du lobby ou de la ligne de commande."""

    def __init__(self, pilot=PILOT_AI, model=None, size=10, speed=6.0,
                 seed=None, sessions=1, save_path=None, visual=True,
                 learn=True, step_by_step=False, trace=True, baseline=None):
        self.pilot = pilot if pilot in PILOTS else PILOT_AI
        self.model = model
        self.size = max(MIN_SIZE, min(MAX_SIZE, size))
        # Bornee comme la taille : 0 ou une valeur infinie font diviser par
        # zero dans la boucle graphique, NaN fige le serpent.
        if not isinstance(speed, (int, float)) or not math.isfinite(speed):
            speed = DEFAULT_SPEED
        self.speed = max(SPEEDS[0], min(SPEEDS[-1], speed))
        self.seed = seed
        self.sessions = max(1, sessions)
        self.save_path = save_path
        self.visual = visual
        self.learn = learn
        self.step_by_step = step_by_step
        self.trace = trace
        self.baseline = baseline

    @property
    def ai_driven(self):
        return self.pilot == PILOT_AI

    def toggle_pilot(self, delta=1):
        """Bascule entre pilotage IA et pilotage humain."""
        index = (PILOTS.index(self.pilot) + delta) % len(PILOTS)
        self.pilot = PILOTS[index]

    def change_size(self, delta):
        self.size = max(MIN_SIZE, min(MAX_SIZE, self.size + delta))

    def change_speed(self, delta):
        speeds = list(SPEEDS)
        current = min(speeds, key=lambda s: abs(s - self.speed))
        index = max(0, min(len(speeds) - 1, speeds.index(current) + delta))
        self.speed = speeds[index]
