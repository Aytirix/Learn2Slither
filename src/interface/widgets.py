"""Briques communes aux ecrans de menu : fond, titres, boutons, formulaires.

Le lobby, le choix du modele, l'entrainement et l'evaluation partagent le
meme style ; tout ce qui se dessine pareil est ici, une seule fois.
"""

import math

import pygame

from . import gfx, theme

START = "start"
QUIT = "quit"

ROW_H = 64
ROW_GAP = 8
CARD_PAD = 24
ARROW_ZONE = 250
BUTTON_W = 280
BUTTON_H = 58

TOUCHES_VALIDER = (pygame.K_RETURN, pygame.K_KP_ENTER)
TOUCHES_BAS = (pygame.K_DOWN, pygame.K_s)
TOUCHES_HAUT = (pygame.K_UP, pygame.K_z, pygame.K_w)
TOUCHES_DROITE = (pygame.K_RIGHT, pygame.K_d)
TOUCHES_GAUCHE = (pygame.K_LEFT, pygame.K_q, pygame.K_a)


# -- Dessin -------------------------------------------------------------------

class Fond:
    """Etoiles, serpent decoratif ondulant et vignette des ecrans de menu."""

    def __init__(self, starfield):
        self.starfield = starfield
        self.vignette = gfx.make_vignette(theme.WIN_W, theme.WIN_H)
        self.light = pygame.Surface(
            (theme.WIN_W, theme.WIN_H), pygame.SRCALPHA
        )

    def update(self, dt):
        self.starfield.update(dt)

    def render(self, screen, time_s):
        self.light.fill((0, 0, 0, 0))
        screen.fill(theme.BG_DEEP)
        self.starfield.draw(screen, time_s)
        self._vague(time_s)
        screen.blit(self.vignette, (0, 0))
        gfx.additive(screen, gfx.blur(self.light, 10), (0, 0))

    def _vague(self, time_s):
        base_y = theme.WIN_H * 0.80
        span = theme.WIN_W + 240
        points = []
        for i in range(60):
            t = i / 59
            x = -120 + span * t
            y = base_y + math.sin(t * 6.0 - time_s * 1.2) * 46
            points.append((x, y))
        for i in range(len(points) - 1):
            t = i / (len(points) - 1)
            color = gfx.lerp_color(theme.SNAKE_TAIL, theme.SNAKE_HEAD, t)
            pygame.draw.line(
                self.light,
                gfx.scale_color(color, 0.22),
                points[i],
                points[i + 1],
                int(34 * (0.35 + 0.65 * t)),
            )


def texte(screen, font, chaine, pos, couleur, centre=False):
    """Ecrit `chaine` ; `pos` est le coin haut-gauche, ou le centre."""
    surf = font.render(chaine, True, couleur)
    if centre:
        pos = (pos[0] - surf.get_width() // 2,
               pos[1] - surf.get_height() // 2)
    screen.blit(surf, pos)
    return surf


def titre(screen, fonts, grand, sous_titre, y=70):
    """Titre d'ecran et sa ligne d'accroche, centres."""
    texte(screen, fonts["hero"], grand, (theme.WIN_W // 2, y + 30),
          theme.TEXT, centre=True)
    texte(screen, fonts["sub"], sous_titre, (theme.WIN_W // 2, y + 82),
          theme.ACCENT, centre=True)


def bouton(screen, font, rect, libelle, focus=False, time_s=None,
           actif=True):
    """Bouton arrondi ; `time_s` le fait pulser (bouton principal)."""
    if not actif:
        gfx.card(screen, rect, theme.BG_CARD, theme.BORDER, 14)
        texte(screen, font, libelle, rect.center, theme.TEXT_MUTED,
              centre=True)
        return
    pulse = 0.5
    if time_s is not None:
        pulse = 0.65 + 0.35 * math.sin(time_s * 2.6)
    fond = gfx.scale_color(theme.ACCENT, (0.22 + 0.10 * pulse)
                           if focus or time_s is not None else 0.10)
    bord = theme.ACCENT if focus or time_s is not None else theme.BORDER
    gfx.card(screen, rect, fond, bord, 14, 2 if focus else 1)
    texte(screen, font, libelle, rect.center, theme.TEXT, centre=True)


def aide(screen, font, lignes, y):
    """Bloc d'aide clavier centre, une ligne par touche."""
    surfaces = [font.render(h, True, theme.TEXT_MUTED) for h in lignes]
    if not surfaces:
        return y
    x = theme.WIN_W // 2 - max(s.get_width() for s in surfaces) // 2
    for surf in surfaces:
        screen.blit(surf, (x, y))
        y += 20
    return y


# -- Champs de formulaire -----------------------------------------------------

def _toujours():
    return True


class Reglage:
    """Valeur reglee avec < et > (ou les fleches gauche et droite)."""

    def __init__(self, label, lire, changer, actif=_toujours, aide=""):
        self.label = label
        # Explication courte sous le libelle : texte, ou fonction qui la
        # calcule d'apres la valeur courante.
        self.aide = aide
        self.lire = lire
        self.changer = changer
        self.actif = actif


class Pilules:
    """Choix entre quelques options affichees cote a cote."""

    def __init__(self, label, options, lire, choisir, actif=_toujours,
                 aide=""):
        self.label = label
        self.aide = aide
        self.options = options      # [(valeur, libelle), ...]
        self.lire = lire            # -> valeur courante
        self.choisir = choisir      # valeur -> None
        self.actif = actif

    def changer(self, delta):
        valeurs = [v for v, _ in self.options]
        courant = self.lire()
        index = valeurs.index(courant) if courant in valeurs else 0
        self.choisir(valeurs[(index + delta) % len(valeurs)])


class Lien:
    """Valeur qu'on change sur un autre ecran (ex. : choix du modele)."""

    def __init__(self, label, lire, action, actif=_toujours):
        self.label = label
        self.lire = lire
        self.action = action
        self.actif = actif


class Saisie:
    """Texte libre tape au clavier (ex. : nom d'un nouveau modele)."""

    def __init__(self, label, valeur="", longueur_max=32, indice="",
                 aide=""):
        self.label = label
        self.aide = aide
        self.valeur = valeur
        self.longueur_max = longueur_max
        self.indice = indice

    def actif(self):
        return True

    def lire(self):
        return self.valeur

    def ajouter(self, chaine):
        for char in chaine:
            if char.isprintable() and len(self.valeur) < self.longueur_max:
                self.valeur += char

    def effacer(self):
        self.valeur = self.valeur[:-1]


class Formulaire:
    """Carte de champs + bouton principal, au clavier et a la souris.

    Clavier : HAUT/BAS change de champ, GAUCHE/DROITE change la valeur,
    ENTREE valide (ou ouvre l'ecran d'un Lien). Les methodes handle_*
    renvoient START (bouton), l'action d'un Lien, ou None.
    """

    def __init__(self, fonts, champs, libelle_bouton, y, largeur=640,
                 hauteur_ligne=ROW_H):
        self.fonts = fonts
        self.champs = champs
        self.libelle_bouton = libelle_bouton
        self.largeur = largeur
        self.x = (theme.WIN_W - largeur) // 2
        self.y = y
        self.hauteur_ligne = hauteur_ligne
        self.index = 0
        self.message = ""
        self.hits = []
        self.bouton_rect = None
        self.move(0)

    # -- focus --------------------------------------------------------
    def actifs(self):
        return [i for i, c in enumerate(self.champs) if c.actif()]

    @property
    def champ(self):
        return self.champs[self.index]

    def move(self, delta):
        """Deplace le focus sur le champ actif suivant (0 : rester sur le
        champ courant s'il est actif, sinon passer au suivant)."""
        n = len(self.champs)
        pas = -1 if delta < 0 else 1
        i = self.index if delta == 0 else (self.index + pas) % n
        for _ in range(n):
            if self.champs[i].actif():
                self.index = i
                return
            i = (i + pas) % n

    def change(self, delta):
        champ = self.champ
        if isinstance(champ, (Reglage, Pilules)) and champ.actif():
            champ.changer(delta)
            self.move(0)

    # -- entrees ------------------------------------------------------
    def handle_key(self, key):
        saisie = isinstance(self.champ, Saisie)
        if key in TOUCHES_VALIDER or (key == pygame.K_SPACE and not saisie):
            if isinstance(self.champ, Lien):
                return self.champ.action
            return START
        if saisie:
            # Les lettres servent a ecrire : seules les fleches deplacent.
            if key == pygame.K_BACKSPACE:
                self.champ.effacer()
            elif key in (pygame.K_DOWN, pygame.K_TAB):
                self.move(1)
            elif key == pygame.K_UP:
                self.move(-1)
            return None
        if key in TOUCHES_BAS or key == pygame.K_TAB:
            self.move(1)
        elif key in TOUCHES_HAUT:
            self.move(-1)
        elif key in TOUCHES_DROITE:
            if isinstance(self.champ, Lien):
                return self.champ.action
            self.change(1)
        elif key in TOUCHES_GAUCHE:
            self.change(-1)
        return None

    def handle_text(self, chaine):
        if isinstance(self.champ, Saisie):
            self.champ.ajouter(chaine)

    def handle_click(self, pos):
        for rect, action in self.hits:
            if not rect.collidepoint(pos):
                continue
            if action == START:
                return START
            index, quoi = action
            self.index = index
            champ = self.champs[index]
            if isinstance(champ, Lien):
                return champ.action
            if isinstance(champ, Pilules):
                champ.choisir(quoi)
                self.move(0)
            elif isinstance(champ, Reglage):
                self.change(quoi)
            return None
        return None

    # -- rendu --------------------------------------------------------
    @property
    def bas(self):
        """Ordonnee du bas du bouton principal."""
        return self._y_bouton() + BUTTON_H

    def _y_bouton(self):
        pitch = self.hauteur_ligne + ROW_GAP
        hauteur = CARD_PAD * 2 + pitch * len(self.champs) - ROW_GAP
        return self.y + hauteur + 22

    def render(self, screen, time_s):
        self.hits = []
        pitch = self.hauteur_ligne + ROW_GAP
        hauteur = CARD_PAD * 2 + pitch * len(self.champs) - ROW_GAP
        carte = pygame.Rect(self.x, self.y, self.largeur, hauteur)
        gfx.card(screen, carte, theme.BG_CARD, theme.BORDER, 18)
        for i, champ in enumerate(self.champs):
            ligne = pygame.Rect(
                self.x + CARD_PAD,
                self.y + CARD_PAD + i * pitch,
                self.largeur - CARD_PAD * 2,
                self.hauteur_ligne,
            )
            self._ligne(screen, ligne, i, champ, time_s)

        y = self._y_bouton()
        self.bouton_rect = pygame.Rect(
            theme.WIN_W // 2 - BUTTON_W // 2, y, BUTTON_W, BUTTON_H
        )
        bouton(screen, self.fonts["value"], self.bouton_rect,
               self.libelle_bouton, time_s=time_s)
        self.hits.append((self.bouton_rect, START))
        if self.message:
            texte(screen, self.fonts["mono"], self.message,
                  (theme.WIN_W // 2, y + BUTTON_H + 18), theme.RED_APPLE,
                  centre=True)

    def _ligne(self, screen, rect, index, champ, time_s):
        actif = champ.actif()
        focus = actif and index == self.index
        gfx.card(screen, rect, theme.BG_DEEP if focus else theme.BG_CARD,
                 theme.ACCENT if focus else theme.BORDER, 12,
                 2 if focus else 1)
        couleur = theme.TEXT_DIM if actif else theme.TEXT_MUTED
        aide = getattr(champ, "aide", "")
        if callable(aide):
            # Aide calculee d'apres la valeur choisie (ex. : gamma).
            aide = aide()
        if aide:
            # Libelle au-dessus, explication en petit juste en dessous.
            texte(screen, self.fonts["label"], champ.label,
                  (rect.x + 18, rect.centery - 17), couleur)
            texte(screen, self.fonts["label"], aide,
                  (rect.x + 18, rect.centery + 3), theme.TEXT_MUTED)
        else:
            texte(screen, self.fonts["label"], champ.label,
                  (rect.x + 18, rect.centery - 7), couleur)

        if isinstance(champ, Pilules):
            self._pilules(screen, rect, index, champ)
            return
        gauche = rect.right - ARROW_ZONE
        droite = rect.right - 30
        milieu = ((gauche + droite) // 2, rect.centery)
        valeur_couleur = theme.TEXT if actif else theme.TEXT_MUTED
        if isinstance(champ, Saisie):
            self._saisie(screen, rect, champ, focus, time_s)
        elif isinstance(champ, Lien):
            # Cale a droite, juste avant le bouton CHOISIR.
            surf = self.fonts["mono"].render(champ.lire(), True,
                                             valeur_couleur)
            screen.blit(surf, (rect.right - 18 - 118 - 20 - surf.get_width(),
                               rect.centery - surf.get_height() // 2))
            if actif:
                self._choisir(screen, rect, index)
        else:
            texte(screen, self.fonts["mono"], champ.lire(), milieu,
                  valeur_couleur, centre=True)
            if actif:
                self._chevrons(screen, rect, index, gauche, droite)

    def _chevrons(self, screen, rect, index, gauche, droite):
        """Fleches a position fixe, alignees d'une ligne a l'autre."""
        for delta, glyph, x in ((-1, "<", gauche), (1, ">", droite)):
            surf = texte(screen, self.fonts["mono"], glyph,
                         (x, rect.centery), theme.ACCENT, centre=True)
            hit = pygame.Rect(x - surf.get_width() // 2 - 16, rect.y,
                              surf.get_width() + 32, rect.height)
            self.hits.append((hit, (index, delta)))

    def _choisir(self, screen, rect, index):
        pill = pygame.Rect(rect.right - 18 - 118, rect.centery - 19, 118, 38)
        gfx.card(screen, pill, theme.BG_CARD, theme.ACCENT, 10)
        texte(screen, self.fonts["label"], "CHOISIR", pill.center,
              theme.ACCENT, centre=True)
        self.hits.append((rect, (index, None)))

    def _saisie(self, screen, rect, champ, focus, time_s):
        zone = pygame.Rect(rect.right - ARROW_ZONE - 120, rect.y + 10,
                           ARROW_ZONE + 102, rect.height - 20)
        gfx.card(screen, zone, theme.BG_DEEP,
                 theme.ACCENT if focus else theme.BORDER, 8)
        if champ.valeur:
            chaine, couleur = champ.valeur, theme.TEXT
        else:
            chaine, couleur = champ.indice, theme.TEXT_MUTED
        surf = texte(screen, self.fonts["mono"], chaine,
                     (zone.x + 12, zone.centery - 9), couleur)
        if focus and int(time_s * 2) % 2 == 0:
            x = zone.x + 12 + (surf.get_width() if champ.valeur else 0) + 2
            pygame.draw.line(screen, theme.ACCENT, (x, zone.y + 8),
                             (x, zone.bottom - 8), 2)
        self.hits.append((rect, (self.champs.index(champ), None)))

    def _pilules(self, screen, rect, index, champ):
        largeur, hauteur = 118, 38
        n = len(champ.options)
        x = rect.right - 18 - largeur * n - 10 * (n - 1)
        for i, (valeur, libelle) in enumerate(champ.options):
            choisi = champ.lire() == valeur
            pill = pygame.Rect(x + i * (largeur + 10),
                               rect.centery - hauteur // 2, largeur, hauteur)
            gfx.card(screen, pill, theme.ACCENT if choisi else theme.BG_CARD,
                     theme.ACCENT if choisi else theme.BORDER, 10)
            texte(screen, self.fonts["mono"], libelle, pill.center,
                  theme.BG_DEEP if choisi else theme.TEXT_DIM, centre=True)
            self.hits.append((pill, (index, valeur)))
