"""Carte de details d'un modele et liste de modeles, partagees par le choix
du modele et l'ecran d'entrainement."""

import pygame

from ..agent import interpreter as it
from . import gfx, theme, widgets

# Nombre maximal d'etats distincts : par rayon, 4 symboles (W, S, G, R)
# fois DISTANCE_MAX distances, et 3 rayons (devant, gauche, droite).
ETATS_POSSIBLES = (4 * it.DISTANCE_MAX) ** 3
# Modele "plateau" : en plus, 2 valeurs de piege par direction (2 ** 3) et
# 9 positions relatives de la pomme (devant / derriere / au niveau, fois
# gauche / droite / au niveau).
ETATS_POSSIBLES_PLATEAU = ETATS_POSSIBLES * 2 ** 3 * 9

DESCRIPTION = (
    "Q-learning tabulaire : sa croix de vision est resumee en",
    "3 rayons (devant, gauche, droite), puis il choisit tout",
    "droit, gauche ou droite selon les notes de sa table.",
)

DESCRIPTION_PLATEAU = (
    "HORS SUJET : en plus de sa croix, il sait pour chaque coup",
    "si la case mene a un piege (espace trop petit pour lui),",
    "et de quel cote est la pomme verte la plus proche.",
)

LIGNE_H = 52

# Affiche partout ou un modele "plateau" est utilise : il recoit des
# informations hors de la croix, ce que le sujet interdit (-42).
AVERTISSEMENT = "ATTENTION : VOIT TOUT LE PLATEAU (HORS SUJET)"
ETIQUETTE = "VOIT TOUT"


def avertir(screen, fonts, y):
    """Bandeau rouge centre : le modele utilise voit tout le plateau."""
    widgets.texte(screen, fonts["mono"], AVERTISSEMENT,
                  (theme.WIN_W // 2, y), theme.RED_APPLE, centre=True)


def entier(n):
    """3429783 -> '3 429 783'."""
    return "{:,}".format(n).replace(",", " ")


def parties(n):
    """'1 partie', '3 429 783 parties'."""
    return "{} partie{}".format(entier(n), "s" if n > 1 else "")


def lignes_details(infos):
    """(libelle, valeur) affiches pour un modele lisible."""
    return (
        ("VISION", "TOUT LE PLATEAU (hors sujet)" if infos.voit_tout
         else "la croix (conforme au sujet)"),
        ("PARTIES D'ENTRAINEMENT", entier(infos.parties)),
        ("PAS JOUES", entier(infos.pas_total)),
        ("SITUATIONS CONNUES", "{} / {}".format(
            entier(infos.etats),
            entier(ETATS_POSSIBLES_PLATEAU if infos.voit_tout
                   else ETATS_POSSIBLES))),
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
    if infos.voit_tout:
        # Bandeau rouge a droite du nom : impossible de le rater.
        surf = fonts["label"].render(AVERTISSEMENT, True, theme.RED_APPLE)
        screen.blit(surf, (rect.right - 24 - surf.get_width(),
                           rect.y + 34))
    for libelle, valeur in lignes_details(infos):
        couleur = theme.TEXT
        if libelle == "VISION" and infos.voit_tout:
            couleur = theme.RED_APPLE
        widgets.texte(screen, fonts["label"], libelle, (x, y + 3),
                      theme.TEXT_MUTED)
        widgets.texte(screen, fonts["mono"], valeur, (x + 230, y), couleur)
        y += 24
    y += 12
    widgets.texte(screen, fonts["label"], "CE QU'IL FAIT", (x, y),
                  theme.ACCENT)
    for ligne in (DESCRIPTION_PLATEAU if infos.voit_tout else DESCRIPTION):
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
            nom = widgets.texte(screen, self.fonts["mono"], infos.nom,
                                (ligne.x + 16, ligne.centery - 9),
                                theme.TEXT if choisi else theme.TEXT_DIM)
            if infos.voit_tout:
                widgets.texte(screen, self.fonts["label"], ETIQUETTE,
                              (ligne.x + 28 + nom.get_width(),
                               ligne.centery - 7), theme.RED_APPLE)
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
