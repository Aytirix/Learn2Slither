"""Carte de details d'un modele et liste de modeles, partagees par le choix
du modele et l'ecran d'entrainement."""

import pygame

from ..agent import interpreter as it
from . import gfx, theme, widgets

# Nombre maximal d'etats distincts : par rayon, 4 symboles (W, S, G, R)
# fois DISTANCE_MAX distances, et 3 rayons (devant, gauche, droite).
ETATS_POSSIBLES = (4 * it.DISTANCE_MAX) ** 3

DESCRIPTION = (
    "Q-learning tabulaire : sa croix de vision est resumee en",
    "3 rayons (devant, gauche, droite), puis il choisit tout",
    "droit, gauche ou droite selon les notes de sa table.",
)

LIGNE_H = 52


def entier(n):
    """3429783 -> '3 429 783'."""
    return "{:,}".format(n).replace(",", " ")


def parties(n):
    """'1 partie', '3 429 783 parties'."""
    return "{} partie{}".format(entier(n), "s" if n > 1 else "")


def lignes_details(infos):
    """(libelle, valeur) affiches pour un modele lisible."""
    return (
        ("PARTIES D'ENTRAINEMENT", entier(infos.parties)),
        ("PAS JOUES", entier(infos.pas_total)),
        ("SITUATIONS CONNUES", "{} / {}".format(
            entier(infos.etats), entier(ETATS_POSSIBLES))),
        ("EXPLORATION ACTUELLE", "epsilon = {:.3f}".format(infos.epsilon)),
        ("GAMMA (poids du futur)", "{:g}".format(infos.gamma)),
        ("EPSILON MINIMAL", "{:g}".format(infos.epsilon_min)),
        ("PAS CIBLE (fin exploration)", entier(infos.pas_cible)),
        ("VALEUR INITIALE", "{:g}".format(infos.valeur_initiale)),
        ("ALPHA", "1 / n^0.7"),
        ("FICHIER", "{}  ({:.0f} ko)".format(infos.chemin,
                                             infos.octets / 1024)),
    )


def carte_details(screen, fonts, rect, infos):
    """Dessine tout ce que contient le modele `infos` (ou rien si None)."""
    gfx.card(screen, rect, theme.BG_CARD, theme.BORDER, 18)
    x, y = rect.x + 24, rect.y + 20
    if infos is None:
        widgets.texte(screen, fonts["mono"], "Aucun modele selectionne",
                      (x, y), theme.TEXT_MUTED)
        return
    widgets.texte(screen, fonts["title"], infos.nom, (x, y), theme.TEXT)
    y += 50
    if not infos.lisible:
        widgets.texte(screen, fonts["mono"], "Fichier illisible :",
                      (x, y), theme.RED_APPLE)
        for morceau in couper(infos.erreur, 52):
            y += 22
            widgets.texte(screen, fonts["label"], morceau, (x, y),
                          theme.TEXT_DIM)
        return
    for libelle, valeur in lignes_details(infos):
        widgets.texte(screen, fonts["label"], libelle, (x, y + 3),
                      theme.TEXT_MUTED)
        widgets.texte(screen, fonts["mono"], valeur, (x + 230, y),
                      theme.TEXT)
        y += 24
    y += 12
    widgets.texte(screen, fonts["label"], "CE QU'IL FAIT", (x, y),
                  theme.ACCENT)
    for ligne in DESCRIPTION:
        y += 18
        widgets.texte(screen, fonts["label"], ligne, (x, y), theme.TEXT_DIM)


def couper(chaine, largeur):
    mots, lignes, courante = chaine.split(), [], ""
    for mot in mots:
        if courante and len(courante) + 1 + len(mot) > largeur:
            lignes.append(courante)
            courante = mot
        else:
            courante = (courante + " " + mot).strip()
    if courante:
        lignes.append(courante)
    return lignes


class ListeModeles:
    """Liste verticale cliquable et defilante de modeles."""

    def __init__(self, fonts, rect):
        self.fonts = fonts
        self.rect = rect
        self.infos = []
        self.index = 0
        self.decalage = 0
        self.hits = []

    @property
    def visibles(self):
        return max(1, (self.rect.height - 16) // LIGNE_H)

    @property
    def choisi(self):
        if 0 <= self.index < len(self.infos):
            return self.infos[self.index]
        return None

    def remplir(self, infos, chemin=None):
        """Nouvelle liste ; selectionne `chemin` s'il y figure."""
        self.infos = infos
        chemins = [i.chemin for i in infos]
        self.index = chemins.index(chemin) if chemin in chemins else 0
        self._suivre()

    def bouger(self, delta):
        if self.infos:
            self.index = max(0, min(len(self.infos) - 1, self.index + delta))
            self._suivre()

    def defiler(self, delta):
        maximum = max(0, len(self.infos) - self.visibles)
        self.decalage = max(0, min(maximum, self.decalage + delta))

    def _suivre(self):
        """Garde l'element selectionne a l'ecran."""
        if self.index < self.decalage:
            self.decalage = self.index
        elif self.index >= self.decalage + self.visibles:
            self.decalage = self.index - self.visibles + 1

    def clic(self, pos):
        """Selectionne la ligne cliquee ; True si un modele a ete touche."""
        for rect, index in self.hits:
            if rect.collidepoint(pos):
                self.index = index
                return True
        return False

    def render(self, screen):
        self.hits = []
        gfx.card(screen, self.rect, theme.BG_CARD, theme.BORDER, 18)
        if not self.infos:
            widgets.texte(screen, self.fonts["mono"], "Aucun modele",
                          (self.rect.centerx, self.rect.y + 40),
                          theme.TEXT_MUTED, centre=True)
            return
        fin = min(len(self.infos), self.decalage + self.visibles)
        for rang, index in enumerate(range(self.decalage, fin)):
            infos = self.infos[index]
            ligne = pygame.Rect(self.rect.x + 12,
                                self.rect.y + 8 + rang * LIGNE_H,
                                self.rect.width - 24, LIGNE_H - 6)
            choisi = index == self.index
            gfx.card(screen, ligne,
                     theme.BG_DEEP if choisi else theme.BG_CARD,
                     theme.ACCENT if choisi else theme.BORDER, 10,
                     2 if choisi else 1)
            widgets.texte(screen, self.fonts["mono"], infos.nom,
                          (ligne.x + 16, ligne.centery - 9),
                          theme.TEXT if choisi else theme.TEXT_DIM)
            if infos.lisible:
                droite = parties(infos.parties)
                couleur = theme.ACCENT if choisi else theme.TEXT_MUTED
            else:
                droite, couleur = "illisible", theme.RED_APPLE
            surf = self.fonts["label"].render(droite, True, couleur)
            screen.blit(surf, (ligne.right - 16 - surf.get_width(),
                               ligne.centery - surf.get_height() // 2))
            self.hits.append((ligne, index))
        if len(self.infos) > self.visibles:
            widgets.texte(
                screen, self.fonts["label"],
                "{}-{} sur {}  (molette)".format(
                    self.decalage + 1, fin, len(self.infos)),
                (self.rect.centerx, self.rect.bottom - 10),
                theme.TEXT_MUTED, centre=True)
