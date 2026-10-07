"""Ecran ENTRAINEMENT : liste des modeles, details, creation, entrainement.

Quatre vues sur le meme ecran :

    LISTE      les modeles et le detail de celui qui est selectionne
    NOUVEAU    formulaire d'un nouveau modele (nom, hyperparametres)
    CONTINUER  combien de parties ajouter a un modele existant
    EN_COURS   l'entrainement tourne : progression, courbe, ARRETER
"""

import random

import pygame

from .. import config as cfg
from .. import models
from ..agent import agent as ag
from ..agent import modele
from ..training import Entrainement
from . import gfx, theme, widgets
from .model_card import ListeModeles, carte_details, entier

LISTE = "liste"
NOUVEAU = "nouveau"
CONTINUER = "continuer"
EN_COURS = "en_cours"

RETOUR_MENU = "menu"

# Temps de calcul accorde a l'entrainement a chaque image : assez pour
# avancer vite, assez peu pour que la fenetre reste fluide (60 images/s).
BUDGET_S = 0.025

GAMMAS = (0.8, 0.85, 0.9, 0.95, 0.97, 0.99)
EPSILONS_MIN = (0.0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1)
PAS_CIBLES = (1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000)
# Parties a ajouter : 10, 20, 50, 100, 200, 500... jusqu'a un million.
AJOUTS = tuple(base * 10 ** e for e in range(1, 6) for base in (1, 2, 5)) \
    + (1_000_000,)
AJOUT_DEFAUT = 1_000

HINTS_LISTE = (
    "HAUT / BAS  selectionner   ·   ENTREE / C  continuer l'entrainement",
    "N  nouveau modele   ·   ECHAP  menu principal",
)
HINTS_FORMULAIRE = (
    "HAUT / BAS  champ   ·   GAUCHE / DROITE  valeur   ·   ENTREE  lancer",
    "ECHAP  retour a la liste",
)
HINTS_EN_COURS = ("ECHAP  ·  ESPACE  ·  ARRETER : arrete et sauvegarde",)


class Choix:
    """Index dans une liste de valeurs, borne aux extremites."""

    def __init__(self, valeurs, defaut):
        self.valeurs = valeurs
        self.index = valeurs.index(defaut)

    @property
    def valeur(self):
        return self.valeurs[self.index]

    def changer(self, delta):
        self.index = max(0, min(len(self.valeurs) - 1, self.index + delta))


class TrainingScreen:
    """Ecran ENTRAINEMENT complet."""

    def __init__(self, fonts, starfield):
        self.fonts = fonts
        self.fond = widgets.Fond(starfield)
        self.time_s = 0.0
        self.vue = LISTE
        self.message = ""
        self.message_ok = True
        self.liste = ListeModeles(fonts, pygame.Rect(44, 150, 470, 470))
        self.details = pygame.Rect(534, 150, theme.WIN_W - 534 - 44, 400)
        largeur = (self.details.width - 12) // 2
        self.continuer_rect = pygame.Rect(534, 566, largeur, 54)
        self.nouveau_rect = pygame.Rect(534 + largeur + 12, 566, largeur, 54)
        self.arreter_rect = pygame.Rect(theme.WIN_W // 2 - 140, 600, 280, 58)
        self.formulaire = None
        self.entrainement = None
        self.nom = None

    # -- navigation ---------------------------------------------------
    def ouvrir(self, chemin=None):
        """Affiche la liste, relue sur le disque."""
        if chemin is None and self.liste.choisi is not None:
            chemin = self.liste.choisi.chemin
        self.liste.remplir(models.modeles(), chemin)
        self.vue = LISTE

    def _ouvrir_nouveau(self):
        self.message = ""
        self.nom = widgets.Saisie("NOM", indice="ex : mon_modele",
                                  longueur_max=models.NOM_MAX)
        self.gamma = Choix(GAMMAS, ag.GAMMA)
        self.epsilon_min = Choix(EPSILONS_MIN, ag.EPSILON_MIN)
        self.pas_cible = Choix(PAS_CIBLES, ag.PAS_CIBLE)
        self.taille = Choix(tuple(range(cfg.MIN_SIZE, cfg.MAX_SIZE + 1)), 10)
        self.ajout = Choix(AJOUTS, AJOUT_DEFAUT)
        champs = [
            self.nom,
            widgets.Reglage("GAMMA (poids du futur)",
                            lambda: "{:g}".format(self.gamma.valeur),
                            self.gamma.changer),
            widgets.Reglage("EPSILON MINIMAL",
                            lambda: "{:g}".format(self.epsilon_min.valeur),
                            self.epsilon_min.changer),
            widgets.Reglage("PAS CIBLE (fin exploration)",
                            lambda: entier(self.pas_cible.valeur),
                            self.pas_cible.changer),
            self._champ_taille(),
            widgets.Reglage("PARTIES A JOUER",
                            lambda: entier(self.ajout.valeur),
                            self.ajout.changer),
        ]
        self.formulaire = widgets.Formulaire(
            self.fonts, champs, "CREER ET ENTRAINER", y=150,
            hauteur_ligne=52)
        self.vue = NOUVEAU

    def _ouvrir_continuer(self):
        infos = self.liste.choisi
        if infos is None:
            return
        if not infos.lisible:
            self._dire("ce modele est illisible : impossible de le "
                       "continuer", ok=False)
            return
        self.message = ""
        self.taille = Choix(tuple(range(cfg.MIN_SIZE, cfg.MAX_SIZE + 1)), 10)
        self.ajout = Choix(AJOUTS, AJOUT_DEFAUT)
        depart = infos.parties
        champs = [
            # Ligne d'information : actif=False, on ne peut pas la regler.
            widgets.Reglage("DEJA ENTRAINE", lambda: entier(depart),
                            None, actif=lambda: False),
            widgets.Reglage(
                "MONTER JUSQU'A",
                lambda: "{}  (+{})".format(
                    entier(depart + self.ajout.valeur),
                    entier(self.ajout.valeur)),
                self.ajout.changer),
            self._champ_taille(),
        ]
        self.formulaire = widgets.Formulaire(
            self.fonts, champs, "ENTRAINER", y=230)
        self.vue = CONTINUER

    def _champ_taille(self):
        return widgets.Reglage(
            "PLATEAU D'ENTRAINEMENT",
            lambda: "{0} x {0}".format(self.taille.valeur),
            self.taille.changer)

    def _dire(self, message, ok=True):
        self.message = message
        self.message_ok = ok

    # -- lancement ----------------------------------------------------
    def _lancer_nouveau(self):
        nom = self.nom.valeur
        probleme = models.probleme_de_nom(nom)
        if probleme:
            self.formulaire.message = probleme
            return
        agent = ag.Agent(rng=random.Random(), gamma=self.gamma.valeur,
                         epsilon_min=self.epsilon_min.valeur,
                         pas_cible=self.pas_cible.valeur)
        self._lancer(agent, models.chemin_nouveau(nom))

    def _lancer_continuer(self):
        chemin = self.liste.choisi.chemin
        try:
            agent = modele.charger(chemin, rng=random.Random())
        except modele.ErreurModele as erreur:
            self.formulaire.message = str(erreur)
            return
        self._lancer(agent, chemin)

    def _lancer(self, agent, chemin):
        try:
            # Comme -save : on verifie qu'on pourra ecrire AVANT d'entrainer.
            modele.verifier_chemin_sauvegarde(chemin)
        except modele.ErreurModele as erreur:
            self.formulaire.message = str(erreur)
            return
        self.entrainement = Entrainement(
            agent, chemin, agent.parties + self.ajout.valeur,
            taille=self.taille.valeur)
        self.vue = EN_COURS

    def arreter(self):
        """Arrete l'entrainement en cours et sauvegarde (ARRETER, croix de
        la fenetre, Ctrl+C). Sans effet s'il n'y en a pas."""
        run = self.entrainement
        if run is None:
            return
        self.entrainement = None
        if run.terminer():
            self._dire("{} parties jouees, modele sauvegarde dans {}".format(
                entier(run.jouees), run.chemin))
        else:
            self._dire("Erreur : {}".format(run.erreur), ok=False)
        self.ouvrir(run.chemin)

    # -- entrees ------------------------------------------------------
    def handle_event(self, event):
        """Renvoie RETOUR_MENU quand on quitte l'ecran, sinon None."""
        if self.vue == LISTE:
            return self._event_liste(event)
        if self.vue == EN_COURS:
            self._event_en_cours(event)
            return None
        self._event_formulaire(event)
        return None

    def _event_liste(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return RETOUR_MENU
            if event.key in widgets.TOUCHES_VALIDER + (pygame.K_c,):
                self._ouvrir_continuer()
            elif event.key == pygame.K_n:
                self._ouvrir_nouveau()
            elif event.key in widgets.TOUCHES_BAS:
                self.liste.bouger(1)
            elif event.key in widgets.TOUCHES_HAUT:
                self.liste.bouger(-1)
        elif event.type == pygame.MOUSEWHEEL:
            self.liste.defiler(-event.y)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.continuer_rect.collidepoint(event.pos):
                self._ouvrir_continuer()
            elif self.nouveau_rect.collidepoint(event.pos):
                self._ouvrir_nouveau()
            else:
                self.liste.clic(event.pos)
        return None

    def _event_formulaire(self, event):
        action = None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.vue = LISTE
                return
            action = self.formulaire.handle_key(event.key)
        elif event.type == pygame.TEXTINPUT:
            self.formulaire.handle_text(event.text)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = self.formulaire.handle_click(event.pos)
        if action == widgets.START:
            if self.vue == NOUVEAU:
                self._lancer_nouveau()
            else:
                self._lancer_continuer()

    def _event_en_cours(self, event):
        if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE, pygame.K_SPACE):
            self.arreter()
        elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
              and self.arreter_rect.collidepoint(event.pos)):
            self.arreter()

    # -- boucle -------------------------------------------------------
    def update(self, dt):
        self.time_s += dt
        self.fond.update(dt)
        run = self.entrainement
        if run is not None:
            run.avancer(BUDGET_S)
            if run.fini:
                self.arreter()

    def render(self, screen):
        self.fond.render(screen, self.time_s)
        if self.vue == LISTE:
            self._render_liste(screen)
        elif self.vue == EN_COURS:
            self._render_en_cours(screen)
        else:
            self._render_formulaire(screen)

    def _render_liste(self, screen):
        widgets.titre(screen, self.fonts, "ENTRAINEMENT",
                      "CHOISIS UN MODELE OU CREES-EN UN", y=10)
        self.liste.render(screen)
        carte_details(screen, self.fonts, self.details, self.liste.choisi)
        widgets.bouton(screen, self.fonts["mono"], self.continuer_rect,
                       "CONTINUER L'ENTRAINEMENT", focus=True,
                       actif=self.liste.choisi is not None)
        widgets.bouton(screen, self.fonts["mono"], self.nouveau_rect,
                       "NOUVEAU MODELE", focus=True)
        if self.message:
            couleur = theme.GREEN_APPLE if self.message_ok \
                else theme.RED_APPLE
            widgets.texte(screen, self.fonts["mono"], self.message,
                          (theme.WIN_W // 2, 650), couleur, centre=True)
        widgets.aide(screen, self.fonts["label"], HINTS_LISTE, 690)

    def _render_formulaire(self, screen):
        if self.vue == NOUVEAU:
            widgets.titre(screen, self.fonts, "NOUVEAU MODELE",
                          "NOM ET HYPERPARAMETRES DU MODELE", y=10)
        else:
            infos = self.liste.choisi
            widgets.titre(
                screen, self.fonts, "CONTINUER",
                "{}  ·  DEJA {} PARTIES  ·  GAMMA {:g}  ·  PAS CIBLE {}"
                .format(infos.nom.upper(), entier(infos.parties),
                        infos.gamma, entier(infos.pas_cible)), y=60)
        self.formulaire.render(screen, self.time_s)
        widgets.aide(screen, self.fonts["label"], HINTS_FORMULAIRE,
                     self.formulaire.bas + 50)

    def _render_en_cours(self, screen):
        run = self.entrainement
        nom = models.label_for(run.chemin).upper()
        widgets.titre(screen, self.fonts, "ENTRAINEMENT",
                      "{}  ·  PLATEAU {} x {}".format(
                          nom, run.board.size, run.board.size), y=10)
        carte = pygame.Rect(140, 140, theme.WIN_W - 280, 440)
        gfx.card(screen, carte, theme.BG_CARD, theme.BORDER, 18)
        x, y = carte.x + 30, carte.y + 26

        barre = pygame.Rect(x, y, carte.width - 60, 26)
        gfx.card(screen, barre, theme.BG_DEEP, theme.BORDER, 10)
        plein = barre.copy()
        plein.width = max(0, int(barre.width * run.progression))
        if plein.width > 4:
            gfx.card(screen, plein, theme.ACCENT, theme.ACCENT, 10)
        widgets.texte(screen, self.fonts["mono"],
                      "{:.1f} %".format(100 * run.progression),
                      barre.center, theme.TEXT, centre=True)
        y += 50

        vitesse = run.parties_par_seconde
        restant = (run.a_jouer - run.jouees) / vitesse if vitesse else 0
        lignes = (
            ("PARTIES", "{} / {}".format(
                entier(run.depart + run.jouees), entier(run.objectif))),
            ("LONGUEUR MOYENNE (100 dernieres)",
             "{:.2f}".format(run.moyenne_recente)),
            ("RECORD DE CET ENTRAINEMENT", str(run.record)),
            ("EXPLORATION (epsilon)", "{:.3f}".format(run.agent.epsilon)),
            ("VITESSE", "{:.0f} parties / s".format(vitesse)),
            ("TEMPS RESTANT", _duree(restant)),
        )
        for libelle, valeur in lignes:
            widgets.texte(screen, self.fonts["label"], libelle, (x, y + 3),
                          theme.TEXT_MUTED)
            widgets.texte(screen, self.fonts["mono"], valeur, (x + 320, y),
                          theme.TEXT)
            y += 28
        self._courbe(screen, pygame.Rect(x, y + 10, carte.width - 60,
                                         carte.bottom - y - 30), run.courbe)

        widgets.bouton(screen, self.fonts["value"], self.arreter_rect,
                       "ARRETER", time_s=self.time_s)
        widgets.aide(screen, self.fonts["label"], HINTS_EN_COURS, 680)

    def _courbe(self, screen, rect, points):
        """Courbe de la longueur moyenne au fil de l'entrainement."""
        gfx.card(screen, rect, theme.BG_DEEP, theme.BORDER, 10)
        widgets.texte(screen, self.fonts["label"],
                      "LONGUEUR MOYENNE AU FIL DES PARTIES",
                      (rect.x + 12, rect.y + 8), theme.TEXT_MUTED)
        if len(points) < 2:
            return
        haut = max(max(points), 1.0)
        zone = rect.inflate(-24, -40).move(0, 10)
        coords = [
            (zone.x + zone.width * i / (len(points) - 1),
             zone.bottom - zone.height * p / haut)
            for i, p in enumerate(points)
        ]
        pygame.draw.lines(screen, theme.ACCENT, False, coords, 2)
        widgets.texte(screen, self.fonts["label"], "{:.1f}".format(haut),
                      (rect.right - 50, rect.y + 8), theme.TEXT_DIM)


def _duree(secondes):
    secondes = int(secondes)
    if secondes < 60:
        return "{} s".format(secondes)
    if secondes < 3600:
        return "{} min {:02d} s".format(secondes // 60, secondes % 60)
    return "{} h {:02d} min".format(secondes // 3600, secondes % 3600 // 60)
