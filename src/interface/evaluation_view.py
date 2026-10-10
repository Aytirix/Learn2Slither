"""EVALUATION : parties en boucle avec l'agent fige, puis resultats et rejeu.

    EvaluationGame     la partie affichee ; enchaine les parties et s'arrete
                       a la fin de la premiere qui atteint le seuil
    ResultsScreen      statistiques de toutes les parties et rejeu, coup par
                       coup, de la partie la plus longue (fleches)
"""

import pygame

from ..environment import board as bd
from ..evaluation import Bilan
from . import gfx, theme, widgets
from .board_view import BoardView, cell_center
from .model_card import couper
from .game import Game
from .particles import ParticleSystem

RETOUR_MENU = "menu"

HINTS_RESULTATS = (
    "GAUCHE / DROITE   coup precedent  ·  coup suivant",
    "ORIGINE / FIN     debut de la partie  ·  present",
    "ECHAP  ·  ENTREE  menu principal",
)


class EvaluationGame(Game):
    """Partie d'evaluation : jamais d'apprentissage, parties en boucle."""

    def __init__(self, configuration, agent, seuil=None):
        self.bilan = Bilan() if seuil is None else Bilan(seuil)
        self.termine = False   # une partie a atteint le seuil et est finie
        self.fini = False      # resultats a afficher
        super().__init__(configuration, agent)
        self.bilan.debut_partie(self.board)

    # -- textes du panneau --------------------------------------------
    @property
    def pilot_label(self):
        if len(self.board.snake) >= self.bilan.seuil or self.termine:
            etat = "SEUIL {} ATTEINT".format(self.bilan.seuil)
        else:
            etat = "OBJECTIF {}".format(self.bilan.seuil)
        return "EVALUATION  ·  PARTIE {}  ·  {}".format(
            self.bilan.numero if not self.termine else self.bilan.stats.games,
            etat)

    # Aide clavier du panneau (voir panel_view.hints_for).
    aide_complete = False
    aide_sortie = "arreter et voir les resultats"

    @property
    def fin_hint(self):
        if self.termine:
            return "[ESPACE] voir les resultats"
        if self.step_by_step:
            return self.avec_revoir("[N] partie suivante")
        return "partie suivante..."

    @property
    def pause_fin(self):
        # Partie qui atteint le seuil : on laisse le temps de la voir.
        if self.termine:
            return max(0.3, min(1.2, 30.0 / self.speed))
        # Objectif rate : simple coup d'oeil, l'evaluation en enchaine
        # beaucoup (0.4 s au plus) ; aucune attente a grande vitesse
        # (40 et plus, MAX compris).
        pause = min(0.4, 4.0 / self.speed)
        return 0.0 if pause <= 0.1 else pause

    # -- deroulement --------------------------------------------------
    def _tick(self):
        super()._tick()
        self.bilan.apres_pas(self.board)
        if not self.board.alive:
            self.termine = self.bilan.fin_partie(self.board)
            # Grande vitesse et objectif rate : pas d'ecran de fin du
            # tout, la partie suivante part au meme pas.
            if (not self.termine and not self.step_by_step
                    and self.pause_fin == 0.0):
                self.next_session()

    def next_session(self):
        """Apres l'ecran de fin : partie suivante, ou fin de l'evaluation."""
        if self.termine:
            self.fini = True
            return False
        self.session += 1
        self.restart()
        return True

    def restart(self):
        if self.termine:
            # ESPACE ou R sur la derniere partie : on passe aux resultats.
            self.fini = True
            return
        super().restart()
        # Une partie abandonnee (R) n'est pas comptee : on repart a zero.
        self.bilan.debut_partie(self.board)


class _Rejeu:
    """Ce que BoardView attend d'une partie, pour une photo figee."""

    fin_hint = ""
    show_vision = True
    shake = (0, 0)

    def __init__(self, taille):
        self.board = bd.Board(size=taille)
        self.particles = ParticleSystem()
        self.time_s = 0.0

    def snake_points(self):
        return [cell_center(self.board.size, c) for c in self.board.snake]


class ResultsScreen:
    """Bilan de l'evaluation, avec rejeu de la partie retenue."""

    def __init__(self, fonts, starfield, bilan, nom_modele, taille):
        self.fonts = fonts
        self.starfield = starfield
        self.vignette = gfx.make_vignette(theme.WIN_W, theme.WIN_H)
        self.board_view = BoardView(fonts)
        self.bilan = bilan
        self.nom_modele = nom_modele
        self.numero, self.photos = bilan.a_rejouer()
        self.rejeu = _Rejeu(taille)
        self.index = max(0, len(self.photos) - 1)   # on part du present
        self._montrer()

    def _montrer(self):
        if self.photos:
            self.photos[self.index].restaurer(self.rejeu.board)

    def aller(self, delta):
        """Recule (delta < 0) ou avance d'autant de coups."""
        if not self.photos:
            return
        self.index = max(0, min(len(self.photos) - 1, self.index + delta))
        self._montrer()

    def handle_event(self, event):
        """Renvoie RETOUR_MENU pour quitter l'ecran, sinon None."""
        if event.type != pygame.KEYDOWN:
            return None
        if event.key in (pygame.K_ESCAPE,) + widgets.TOUCHES_VALIDER:
            return RETOUR_MENU
        if event.key in (pygame.K_LEFT, pygame.K_q, pygame.K_a):
            self.aller(-1)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.aller(1)
        elif event.key in (pygame.K_HOME, pygame.K_PAGEUP):
            self.aller(-len(self.photos))
        elif event.key in (pygame.K_END, pygame.K_PAGEDOWN):
            self.aller(len(self.photos))
        return None

    def update(self, dt):
        self.rejeu.time_s += dt
        self.starfield.update(dt)

    # -- rendu --------------------------------------------------------
    def render(self, screen):
        screen.fill(theme.BG_DEEP)
        self.starfield.draw(screen, self.rejeu.time_s)
        screen.blit(self.vignette, (0, 0))
        if self.photos:
            surf = self.board_view.render(self.rejeu)
            screen.blit(surf, (theme.BOARD_X, theme.BOARD_Y))
        x, y = theme.PANEL_X, theme.BOARD_Y
        widgets.texte(screen, self.fonts["title"], "RESULTATS", (x, y),
                      theme.TEXT)
        widgets.texte(screen, self.fonts["sub"],
                      "EVALUATION  ·  {}  ·  AGENT FIGE".format(
                          self.nom_modele.upper()),
                      (x, y + 38), theme.ACCENT)
        y = self._stats(screen, x, y + 74)
        y = self._rejeu(screen, x, y + 8)
        for ligne in HINTS_RESULTATS:
            widgets.texte(screen, self.fonts["label"], ligne, (x, y),
                          theme.TEXT_MUTED)
            y += 18

    def _stats(self, screen, x, y):
        stats = self.bilan.stats
        if self.bilan.atteint:
            objectif = ("OUI, partie {}".format(stats.games),
                        theme.GREEN_APPLE)
        else:
            objectif = ("NON (arretee)", theme.RED_APPLE)
        duree = stats.total_steps / stats.games if stats.games else 0.0
        lignes = (
            ("PARTIES JOUEES", str(stats.games), theme.TEXT),
            ("LONGUEUR {} ATTEINTE".format(self.bilan.seuil), objectif[0],
             objectif[1]),
            ("LONGUEUR MOYENNE", "{:.2f}".format(stats.mean_length),
             theme.TEXT),
            ("LONGUEUR MEDIANE", "{:g}".format(stats.median_length),
             theme.TEXT),
            ("LONGUEUR MAXIMALE", self._record(), theme.TEXT),
            ("DUREE MOYENNE", "{:.0f} pas".format(duree), theme.TEXT),
        )
        hauteur = 20 + 25 * len(lignes) + 44
        carte = pygame.Rect(x, y, theme.PANEL_W, hauteur)
        gfx.card(screen, carte, theme.BG_CARD, theme.BORDER, 14)
        y += 16
        for libelle, valeur, couleur in lignes:
            widgets.texte(screen, self.fonts["label"], libelle,
                          (x + 16, y + 3), theme.TEXT_MUTED)
            widgets.texte(screen, self.fonts["mono"], valeur, (x + 230, y),
                          couleur)
            y += 25
        causes = stats.causes_summary().replace("causes de fin : ", "")
        for morceau in couper("FINS : " + causes, 50)[:2]:
            widgets.texte(screen, self.fonts["label"], morceau,
                          (x + 16, y + 3), theme.TEXT_DIM)
            y += 18
        return carte.bottom + 12

    def _record(self):
        """Longueur record, avec la graine qui rejoue cette partie."""
        valeur = str(self.bilan.stats.max_length)
        graine = (self.bilan.meilleure[0].graine if self.bilan.meilleure
                  else None)
        if graine is not None:
            valeur += "  (graine {})".format(graine)
        return valeur

    def _rejeu(self, screen, x, y):
        carte = pygame.Rect(x, y, theme.PANEL_W, 150)
        gfx.card(screen, carte, theme.BG_CARD, theme.BORDER, 14)
        titre = "REJEU  ·  PARTIE {}".format(self.numero)
        graine = self.photos[0].graine if self.photos else None
        if graine is not None:
            # -seed <graine> rejoue cette partie a l'identique.
            titre += "  ·  GRAINE {}".format(graine)
        widgets.texte(screen, self.fonts["label"], titre,
                      (x + 16, y + 14), theme.ACCENT)
        if not self.photos:
            widgets.texte(screen, self.fonts["mono"], "aucune partie jouee",
                          (x + 16, y + 44), theme.TEXT_MUTED)
            return carte.bottom + 12
        photo = self.photos[self.index]
        present = self.index == len(self.photos) - 1
        lignes = (
            ("COUP", "{} / {}{}".format(
                self.index, len(self.photos) - 1,
                "  (present)" if present else "")),
            ("LONGUEUR", str(len(photo.snake))),
            ("EVENEMENT", _evenement(photo)),
        )
        yy = y + 44
        for libelle, valeur in lignes:
            widgets.texte(screen, self.fonts["label"], libelle,
                          (x + 16, yy + 3), theme.TEXT_MUTED)
            widgets.texte(screen, self.fonts["mono"], valeur, (x + 140, yy),
                          theme.TEXT)
            yy += 26
        barre = pygame.Rect(x + 16, carte.bottom - 22, theme.PANEL_W - 32, 8)
        gfx.card(screen, barre, theme.BG_DEEP, theme.BORDER, 4)
        if len(self.photos) > 1:
            plein = barre.copy()
            plein.width = int(barre.width * self.index
                              / (len(self.photos) - 1))
            if plein.width > 2:
                gfx.card(screen, plein, theme.ACCENT, theme.ACCENT, 4)
        return carte.bottom + 14


EVENEMENTS = {
    None: "depart",
    bd.MOVE: "deplacement",
    bd.GREEN: "pomme verte (+1)",
    bd.RED: "pomme rouge (-1)",
}


def _evenement(photo):
    if photo.end_cause is not None:
        cause = photo.end_cause
        return "fin : " + bd.END_CAUSE_LABELS.get(cause, cause)
    return EVENEMENTS.get(photo.event, photo.event)
