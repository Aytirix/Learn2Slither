"""Etape 11 : sauvegarder et recharger un modele."""

import json
import os
import random
import tempfile
import unittest
from unittest import mock

from src.agent import interpreter as it
from src.agent import modele
from src.agent.agent import Agent
from src.agent.qtable import QTable

ETAT = (("R", 2), ("G", 2), ("W", 3))


class TestCles(unittest.TestCase):
    def test_etat_vers_texte(self):
        self.assertEqual(modele.etat_vers_texte(ETAT), "R2|G2|W3")

    def test_aller_retour(self):
        self.assertEqual(
            modele.texte_vers_etat(modele.etat_vers_texte(ETAT)), ETAT
        )

    def test_distance_a_deux_chiffres(self):
        etat = (("G", 12), ("W", 3), ("S", 1))
        self.assertEqual(
            modele.texte_vers_etat(modele.etat_vers_texte(etat)), etat
        )


class AvecDossier(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.chemin = os.path.join(self.dossier.name, "m.txt")

    def tearDown(self):
        self.dossier.cleanup()

    def agent_entraine(self):
        agent = Agent(rng=random.Random(0), gamma=0.9, pas_cible=1234,
                      epsilon_min=0.05, qtable=QTable(valeur_initiale=0.5))
        agent.mettre_a_jour(ETAT, it.GAUCHE, 20, None, True)
        agent.mettre_a_jour(ETAT, it.GAUCHE, 20, None, True)
        agent.parties = 42
        agent.pas_total = 600
        return agent


class TestAllerRetour(AvecDossier):
    def test_tout_est_conserve(self):
        avant = self.agent_entraine()
        avant.save(self.chemin)
        apres = modele.charger(self.chemin)
        self.assertEqual(apres.q.table, avant.q.table)
        self.assertEqual(apres.q.visites, avant.q.visites)
        self.assertEqual(apres.parties, 42)
        self.assertEqual(apres.pas_total, 600)
        self.assertEqual(apres.gamma, 0.9)
        self.assertEqual(apres.pas_cible, 1234)
        self.assertEqual(apres.epsilon_min, 0.05)
        self.assertEqual(apres.q.valeur_initiale, 0.5)

    def test_epsilon_reprend_ou_il_en_etait(self):
        """Sinon un modele entraine se remettrait a jouer au hasard."""
        self.agent_entraine().save(self.chemin)
        apres = modele.charger(self.chemin)
        self.assertAlmostEqual(apres.epsilon, 1 - 600 / 1234)

    def test_fichier_json_lisible(self):
        self.agent_entraine().save(self.chemin)
        with open(self.chemin, encoding="utf-8") as fichier:
            donnees = json.load(fichier)
        self.assertEqual(donnees["format"], modele.FORMAT)
        self.assertEqual(donnees["version_encodage"], it.VERSION_ENCODAGE)
        self.assertIn("R2|G2|W3", donnees["qtable"])

    def test_cree_le_dossier(self):
        chemin = os.path.join(self.dossier.name, "a", "b", "m.txt")
        self.agent_entraine().save(chemin)
        self.assertTrue(os.path.isfile(chemin))


class TestEcriture(AvecDossier):
    def test_vers_un_dossier(self):
        with self.assertRaises(modele.ErreurModele):
            self.agent_entraine().save(self.dossier.name)

    def test_parent_qui_est_un_fichier(self):
        with open(self.chemin, "w", encoding="utf-8") as fichier:
            fichier.write("x")
        with self.assertRaises(modele.ErreurModele):
            self.agent_entraine().save(os.path.join(self.chemin, "m.txt"))

    def test_dossier_protege_garde_l_ancien_modele(self):
        """Echec d'ecriture : erreur claire, et l'ancien fichier intact."""
        self.agent_entraine().save(self.chemin)
        with open(self.chemin, "rb") as fichier:
            avant = fichier.read()
        os.chmod(self.dossier.name, 0o500)
        try:
            if os.access(self.dossier.name, os.W_OK):
                self.skipTest("droits ignores (execution en root)")
            with self.assertRaises(modele.ErreurModele):
                Agent(rng=random.Random(1)).save(self.chemin)
        finally:
            os.chmod(self.dossier.name, 0o700)
        with open(self.chemin, "rb") as fichier:
            self.assertEqual(fichier.read(), avant)

    def test_chemin_valide_dans_un_dossier_a_creer(self):
        modele.verifier_chemin_sauvegarde(
            os.path.join(self.dossier.name, "nouveau", "m.txt"))


class TestEcritureSure(AvecDossier):
    """Une sauvegarde ratee ne doit jamais abimer le modele existant."""

    def test_echec_en_cours_d_ecriture_garde_l_ancien_modele(self):
        self.agent_entraine().save(self.chemin)
        with open(self.chemin, "rb") as fichier:
            avant = fichier.read()
        panne = OSError(28, "No space left on device")
        with mock.patch("src.agent.modele.json.dump", side_effect=panne):
            with self.assertRaises(modele.ErreurModele):
                Agent(rng=random.Random(1)).save(self.chemin)
        with open(self.chemin, "rb") as fichier:
            self.assertEqual(fichier.read(), avant)
        self.assertFalse(os.path.exists(self.chemin + ".tmp"))

    def test_fichier_protege_refuse(self):
        self.agent_entraine().save(self.chemin)
        with open(self.chemin, "rb") as fichier:
            avant = fichier.read()
        os.chmod(self.chemin, 0o444)
        try:
            if os.access(self.chemin, os.W_OK):
                self.skipTest("droits ignores (execution en root)")
            with self.assertRaises(modele.ErreurModele):
                modele.verifier_chemin_sauvegarde(self.chemin)
            with self.assertRaises(modele.ErreurModele):
                Agent(rng=random.Random(1)).save(self.chemin)
        finally:
            os.chmod(self.chemin, 0o644)
        with open(self.chemin, "rb") as fichier:
            self.assertEqual(fichier.read(), avant)

    def test_dossier_protege_refuse_des_la_verification(self):
        """Refuse AVANT l'entrainement, pas seulement au moment d'ecrire."""
        os.chmod(self.dossier.name, 0o500)
        try:
            if os.access(self.dossier.name, os.W_OK):
                self.skipTest("droits ignores (execution en root)")
            with self.assertRaises(modele.ErreurModele):
                modele.verifier_chemin_sauvegarde(self.chemin)
        finally:
            os.chmod(self.dossier.name, 0o700)

    def test_parent_fichier_refuse_des_la_verification(self):
        with open(self.chemin, "w", encoding="utf-8") as fichier:
            fichier.write("x")
        with self.assertRaises(modele.ErreurModele) as contexte:
            modele.verifier_chemin_sauvegarde(
                os.path.join(self.chemin, "m.txt"))
        self.assertIn("fichier", str(contexte.exception))

    def test_sans_nom_de_fichier(self):
        with self.assertRaises(modele.ErreurModele):
            modele.verifier_chemin_sauvegarde(
                os.path.join(self.dossier.name, "nouveau") + os.sep)


class TestFichiersRefuses(AvecDossier):
    def ecrire(self, contenu):
        with open(self.chemin, "w", encoding="utf-8") as fichier:
            fichier.write(contenu)

    def modifier(self, cle, valeur):
        self.agent_entraine().save(self.chemin)
        with open(self.chemin, encoding="utf-8") as fichier:
            donnees = json.load(fichier)
        donnees[cle] = valeur
        self.ecrire(json.dumps(donnees))

    def test_fichier_absent(self):
        with self.assertRaises(modele.ErreurModele):
            modele.charger(os.path.join(self.dossier.name, "absent.txt"))

    def test_pas_du_json(self):
        self.ecrire("ceci n'est pas du json")
        with self.assertRaises(modele.ErreurModele):
            modele.charger(self.chemin)

    def test_json_d_autre_chose(self):
        self.ecrire('{"bonjour": 1}')
        with self.assertRaises(modele.ErreurModele):
            modele.charger(self.chemin)

    def test_autre_version_d_encodage(self):
        self.modifier("version_encodage", it.VERSION_ENCODAGE + 1)
        with self.assertRaises(modele.ErreurModele):
            modele.charger(self.chemin)

    def test_cle_de_version_supprimee(self):
        self.agent_entraine().save(self.chemin)
        with open(self.chemin, encoding="utf-8") as fichier:
            donnees = json.load(fichier)
        del donnees["version_encodage"]
        self.ecrire(json.dumps(donnees))
        with self.assertRaises(modele.ErreurModele):
            modele.charger(self.chemin)

    def test_version_booleenne(self):
        """True vaut 1 en Python : il ne doit pas passer pour la version 1."""
        self.modifier("version_encodage", True)
        with self.assertRaises(modele.ErreurModele):
            modele.charger(self.chemin)

    def test_distance_max_flottante(self):
        self.modifier("distance_max", float(it.DISTANCE_MAX))
        with self.assertRaises(modele.ErreurModele):
            modele.charger(self.chemin)

    def test_json_pathologique(self):
        """Entier de 5 000 chiffres, crochets imbriques a l'infini."""
        for contenu in ('{"x": ' + "9" * 5000 + "}", "[" * 100_000):
            with self.subTest(debut=contenu[:8]):
                self.ecrire(contenu)
                with self.assertRaises(modele.ErreurModele):
                    modele.charger(self.chemin)

    def test_version_anterieure_ou_absente(self):
        for version in (it.VERSION_ENCODAGE - 1, None):
            with self.subTest(version=version):
                self.modifier("version_encodage", version)
                with self.assertRaises(modele.ErreurModele):
                    modele.charger(self.chemin)

    def test_autre_distance_max(self):
        self.modifier("distance_max", it.DISTANCE_MAX + 1)
        with self.assertRaises(modele.ErreurModele):
            modele.charger(self.chemin)

    def test_fichier_incomplet(self):
        self.agent_entraine().save(self.chemin)
        with open(self.chemin, encoding="utf-8") as fichier:
            donnees = json.load(fichier)
        del donnees["qtable"]
        self.ecrire(json.dumps(donnees))
        with self.assertRaises(modele.ErreurModele):
            modele.charger(self.chemin)


class TestContenuCorrompu(AvecDossier):
    """Un JSON au bon format mais au contenu faux : refuse au chargement."""

    def corrompre(self, modifier):
        self.agent_entraine().save(self.chemin)
        with open(self.chemin, encoding="utf-8") as fichier:
            donnees = json.load(fichier)
        modifier(donnees)
        with open(self.chemin, "w", encoding="utf-8") as fichier:
            json.dump(donnees, fichier)

    def refuse(self, modifier):
        self.corrompre(modifier)
        with self.assertRaises(modele.ErreurModele):
            modele.charger(self.chemin)

    def ligne(self, donnees):
        return donnees["qtable"]["R2|G2|W3"]

    def test_valeur_texte(self):
        self.refuse(lambda d: self.ligne(d)["valeurs"].__setitem__(0, "abc"))

    def test_valeur_nan(self):
        self.refuse(lambda d: self.ligne(d)["valeurs"].__setitem__(
            0, float("nan")))

    def test_mauvais_nombre_de_valeurs(self):
        self.refuse(lambda d: self.ligne(d).__setitem__("valeurs", [1.0]))

    def test_visite_negative(self):
        self.refuse(lambda d: self.ligne(d)["visites"].__setitem__(0, -1))

    def test_cles_malformees(self):
        for cle in ("X|", "G", "R2|G2", "Z2|G2|W3", "R9|G2|W3"):
            with self.subTest(cle=cle):
                self.refuse(lambda d: d["qtable"].__setitem__(
                    cle, {"valeurs": [1, 1, 1], "visites": [0, 0, 0]}))

    def test_hyperparametres_vides(self):
        self.refuse(lambda d: d.__setitem__("hyperparametres", {}))

    def test_gamma_texte(self):
        self.refuse(lambda d: d["hyperparametres"].__setitem__("gamma", "x"))

    def test_pas_cible_nul(self):
        self.refuse(lambda d: d["hyperparametres"].__setitem__(
            "pas_cible", 0))

    def test_parties_texte(self):
        self.refuse(lambda d: d.__setitem__("parties", "abc"))

    def test_table_liste(self):
        self.refuse(lambda d: d.__setitem__("qtable", []))

    def test_valeur_infinie(self):
        for infini in (float("inf"), float("-inf")):
            with self.subTest(infini=infini):
                self.refuse(lambda d: self.ligne(d)["valeurs"].__setitem__(
                    0, infini))

    def test_valeur_booleenne(self):
        self.refuse(lambda d: self.ligne(d)["valeurs"].__setitem__(0, True))

    def test_valeur_geante(self):
        self.refuse(lambda d: self.ligne(d)["valeurs"].__setitem__(
            0, 10 ** 400))

    def test_mauvais_nombre_de_visites(self):
        self.refuse(lambda d: self.ligne(d).__setitem__("visites", [1, 1]))

    def test_visite_flottante_ou_booleenne(self):
        for visite in (1.5, True):
            with self.subTest(visite=visite):
                self.refuse(lambda d: self.ligne(d)["visites"].__setitem__(
                    0, visite))

    def test_visite_geante(self):
        """Passerait au chargement, puis 1/n**0.7 deborderait en partie."""
        self.refuse(lambda d: self.ligne(d)["visites"].__setitem__(
            0, 10 ** 400))

    def test_gamma_hors_bornes(self):
        for gamma in (5.0, -0.1):
            with self.subTest(gamma=gamma):
                self.refuse(lambda d: d["hyperparametres"].__setitem__(
                    "gamma", gamma))

    def test_epsilon_min_hors_bornes(self):
        for epsilon in (3.0, -0.5):
            with self.subTest(epsilon=epsilon):
                self.refuse(lambda d: d["hyperparametres"].__setitem__(
                    "epsilon_min", epsilon))

    def test_pas_cible_geant(self):
        self.refuse(lambda d: d["hyperparametres"].__setitem__(
            "pas_cible", 10 ** 400))

    def test_compteurs_invalides(self):
        """Avec pas_total = -100 000, epsilon montait a 21."""
        for champ in ("parties", "pas_total"):
            for valeur in (-1, 2.5, True, 10 ** 400):
                with self.subTest(champ=champ, valeur=valeur):
                    self.refuse(lambda d: d.__setitem__(champ, valeur))

    def test_cles_non_canoniques_ou_distance_nulle(self):
        for cle in ("R 2|G2|W3", "R+2|G2|W3", "R02|G2|W3", "W0|G2|W3"):
            with self.subTest(cle=cle):
                self.refuse(lambda d: d["qtable"].__setitem__(
                    cle, {"valeurs": [1, 1, 1], "visites": [0, 0, 0]}))

    def test_ligne_nombre(self):
        self.refuse(lambda d: d["qtable"].__setitem__("R2|G2|W3", 5))


if __name__ == "__main__":
    unittest.main()
