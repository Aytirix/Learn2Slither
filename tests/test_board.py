"""Environnement : vision, collisions, pommes, mort et troncature."""

import unittest

from src.environment import board as bd
from tests.helpers import joue, plateau_nu, pose, tour_du_plateau


class TestConstantes(unittest.TestCase):
    def test_timeout_hors_des_morts(self):
        """Le coeur du changement : une troncature n'est pas une mort."""
        self.assertNotIn(bd.TIMEOUT, bd.DEATH_EVENTS)
        self.assertIn(bd.TIMEOUT, bd.END_CAUSES)

    def test_longueur_nulle_reste_une_mort(self):
        self.assertIn(bd.STARVE, bd.DEATH_EVENTS)

    def test_morts_incluses_dans_les_causes_de_fin(self):
        for cause in bd.DEATH_EVENTS:
            self.assertIn(cause, bd.END_CAUSES)

    def test_libelles_pour_chaque_cause(self):
        """Source unique : une cause sans libelle s'afficherait en brut."""
        self.assertEqual(set(bd.END_CAUSE_LABELS), set(bd.END_CAUSES))


class TestVision(unittest.TestCase):
    """Le canal d'observation : la seule information que le sujet autorise."""

    def plateau(self):
        board = bd.Board(size=5, greens=0, reds=0)
        pose(board, (2, 2), bd.RIGHT)
        board.greens = [(2, 0)]
        board.reds = [(4, 2)]
        return board

    def test_contenu_exact_des_rayons(self):
        vision = self.plateau().vision_chars()
        self.assertEqual(vision[bd.UP], "0GW")
        self.assertEqual(vision[bd.LEFT], "SSW")
        self.assertEqual(vision[bd.DOWN], "00W")
        self.assertEqual(vision[bd.RIGHT], "0RW")

    def test_tout_rayon_finit_par_un_mur(self):
        """§6.4 en depend : le premier symbole non vide existe toujours."""
        for size in (5, 10, 20):
            board = bd.Board(size=size)
            for _ in range(50):
                board.reset()
                for ray in board.vision_chars().values():
                    self.assertTrue(ray.endswith(bd.WALL_CHAR))
                    self.assertEqual(ray.count(bd.WALL_CHAR), 1)

    def test_la_tete_a_son_propre_symbole(self):
        board = self.plateau()
        self.assertEqual(board.cell_char(board.snake[0]), bd.HEAD_CHAR)
        self.assertEqual(board.cell_char(board.snake[1]), bd.BODY_CHAR)
        self.assertEqual(board.cell_char((-1, 0)), bd.WALL_CHAR)

    def test_croix_affichee_en_terminal(self):
        lines = self.plateau().vision_lines()
        self.assertEqual(len(lines), 7)
        self.assertTrue(all(len(line) == 7 for line in lines))
        self.assertEqual(lines[3], "WSSH0RW")
        self.assertEqual("".join(line[3] for line in lines), "WG0H00W")

    def test_un_seul_rayon_commence_par_le_cou(self):
        """La direction initiale est lisible sans ambiguite (§6.6)."""
        board = bd.Board(size=10)
        for _ in range(200):
            board.reset()
            cous = [
                d for d, ray in board.vision_chars().items()
                if ray.startswith(bd.BODY_CHAR)
            ]
            self.assertEqual(len(cous), 1)


class TestDeplacement(unittest.TestCase):
    def test_direction_invalide_refusee(self):
        board = plateau_nu(size=5)
        with self.assertRaises(ValueError):
            board.step((2, 0))
        with self.assertRaises(ValueError):
            board.step(None)

    def test_direction_enregistree(self):
        board = pose(plateau_nu(size=5), (2, 2), bd.RIGHT)
        board.step(bd.DOWN)
        self.assertEqual(board.direction, bd.DOWN)

    def test_compteur_de_pas(self):
        board = plateau_nu(size=10)
        pose(board, (2, 5), bd.RIGHT)
        self.assertEqual(board.steps, 0)
        for attendu in (1, 2, 3):
            board.step(bd.RIGHT)
            self.assertEqual(board.steps, attendu)

    def test_direction_initiale_ne_vise_pas_le_cou(self):
        """Direction inversee au reset = mort immediate sur son corps."""
        board = bd.Board(size=10)
        for _ in range(200):
            board.reset()
            tete = board.snake[0]
            devant = (tete[0] + board.direction[0],
                      tete[1] + board.direction[1])
            self.assertNotIn(devant, board.snake)

    def test_plateau_termine_ne_bouge_plus(self):
        board = pose(plateau_nu(size=5), (0, 2), bd.LEFT)
        self.assertEqual(board.step(bd.LEFT), bd.WALL)
        pas, serpent = board.steps, list(board.snake)
        self.assertEqual(board.step(bd.RIGHT), bd.WALL)
        self.assertEqual(board.steps, pas)
        self.assertEqual(board.snake, serpent)


class TestMorts(unittest.TestCase):
    def test_les_quatre_murs(self):
        cas = (
            ((0, 2), bd.LEFT),
            ((4, 2), bd.RIGHT),
            ((2, 0), bd.UP),
            ((2, 4), bd.DOWN),
        )
        for tete, direction in cas:
            with self.subTest(direction=direction):
                board = pose(plateau_nu(size=5), tete, direction)
                self.assertEqual(board.step(direction), bd.WALL)
                self.assertTrue(board.dead)
                self.assertFalse(board.truncated)
                self.assertEqual(board.end_cause, bd.WALL)

    def test_corps(self):
        """Demi-tour sur le cou : mort immediate."""
        board = pose(plateau_nu(size=10), (5, 5), bd.RIGHT)
        self.assertEqual(board.step(bd.LEFT), bd.BODY)
        self.assertTrue(board.dead)
        self.assertEqual(board.end_cause, bd.BODY)


class TestPommes(unittest.TestCase):
    def test_verte_allonge_et_reapparait(self):
        board = bd.Board(size=10, greens=1, reds=0)
        pose(board, (5, 5), bd.RIGHT)
        board.greens = [(6, 5)]
        self.assertEqual(board.step(bd.RIGHT), bd.GREEN)
        self.assertEqual(len(board.snake), 4)
        self.assertEqual(board.max_length, 4)
        self.assertEqual(len(board.greens), 1, "une nouvelle verte apparait")
        self.assertNotIn((6, 5), board.greens)

    def test_rouge_raccourcit_de_un(self):
        board = bd.Board(size=10, greens=0, reds=1)
        pose(board, (5, 5), bd.RIGHT)
        board.reds = [(6, 5)]
        self.assertEqual(board.step(bd.RIGHT), bd.RED)
        self.assertEqual(len(board.snake), 2)
        self.assertEqual(len(board.reds), 1)

    def test_rouge_sur_serpent_de_un_tue(self):
        """Le sujet l'impose : longueur tombee a 0 = game over."""
        board = bd.Board(size=10, greens=0, reds=1)
        pose(board, (5, 5), bd.RIGHT, longueur=1)
        board.reds = [(6, 5)]
        self.assertEqual(board.step(bd.RIGHT), bd.STARVE)
        self.assertEqual(board.snake, [])
        self.assertTrue(board.dead)
        self.assertEqual(board.end_cause, bd.STARVE)

    def test_pommes_placees_au_reset(self):
        board = bd.Board(size=10, greens=2, reds=1)
        self.assertEqual(len(board.greens), 2)
        self.assertEqual(len(board.reds), 1)
        occupe = set(board.snake)
        for pomme in board.greens + board.reds:
            self.assertNotIn(pomme, occupe)
            self.assertTrue(board.inside(pomme))


class TestTroncature(unittest.TestCase):
    def test_limite_proportionnelle_a_l_aire(self):
        for size in (5, 10, 20):
            with self.subTest(size=size):
                board = plateau_nu(size=size, idle_factor=4)
                self.assertEqual(board.idle_limit, 4 * size * size)

    def test_limite_independante_de_la_longueur(self):
        board = plateau_nu(size=10, idle_factor=4)
        avant = board.idle_limit
        pose(board, (5, 5), bd.RIGHT, longueur=9)
        self.assertEqual(board.idle_limit, avant)

    def test_facteur_degenere_corrige(self):
        """0 ou negatif tronquerait des le premier pas."""
        for facteur in (0, -5):
            with self.subTest(facteur=facteur):
                board = plateau_nu(size=5, idle_factor=facteur)
                self.assertEqual(board.idle_factor, 1)
                self.assertEqual(board.idle_limit, 25)

    def test_declenche_exactement_a_la_limite(self):
        board = plateau_nu(size=5, idle_factor=1)
        evenements = joue(board, tour_du_plateau(board))
        self.assertEqual(board.idle_limit, 25)
        self.assertEqual(len(evenements), 25)
        self.assertEqual(board.end_cause, bd.TIMEOUT)

    def test_le_pas_qui_tronque_reste_un_deplacement(self):
        """Sinon sa recompense devient une prime pour avoir stagne."""
        board = plateau_nu(size=5, idle_factor=1)
        evenements = joue(board, tour_du_plateau(board))
        self.assertEqual(
            evenements[-1], bd.MOVE,
            "step() ne doit pas remplacer l'evenement du pas par TIMEOUT",
        )
        self.assertEqual(set(evenements), {bd.MOVE})
        self.assertEqual(board.last_event, bd.MOVE)
        self.assertEqual(board.end_cause, bd.TIMEOUT)

    def test_etat_apres_troncature(self):
        board = plateau_nu(size=5, idle_factor=1)
        joue(board, tour_du_plateau(board))
        self.assertFalse(board.alive)
        self.assertTrue(board.truncated)
        self.assertFalse(board.dead, "une troncature n'est pas une mort")

    def test_constante_par_defaut(self):
        """La formule est testee ailleurs ; ici c'est la valeur livree."""
        self.assertEqual(bd.IDLE_FACTOR, 4)
        board = bd.Board(size=10)
        self.assertEqual(board.idle_limit, 4 * 10 * 10)

    def test_pomme_rouge_remet_aussi_le_compteur_a_zero(self):
        """Le rouge est une pomme : il rearme le compteur comme le vert."""
        board = bd.Board(size=10, greens=0, reds=0, idle_factor=4)
        pose(board, (3, 3), bd.RIGHT)
        board.step(bd.RIGHT)
        self.assertEqual(board.idle, 1)
        board.reds = [(5, 3)]
        board.step(bd.RIGHT)
        self.assertEqual(board.last_event, bd.RED)
        self.assertEqual(board.idle, 0)

    def test_pomme_verte_remet_le_compteur_a_zero(self):
        board = bd.Board(size=10, greens=0, reds=0, idle_factor=4)
        pose(board, (3, 3), bd.RIGHT)
        board.step(bd.RIGHT)
        self.assertEqual(board.idle, 1)
        board.greens = [(5, 3)]
        board.step(bd.RIGHT)
        self.assertEqual(board.last_event, bd.GREEN)
        self.assertEqual(board.idle, 0)


class TestConstruction(unittest.TestCase):
    def test_plateau_trop_petit_refuse(self):
        """Sinon _spawn_snake tourne indefiniment : aucune case alignee."""
        for size in (0, 1, 2):
            with self.subTest(size=size):
                with self.assertRaises(ValueError):
                    bd.Board(size=size)

    def test_plateau_minimal_accepte(self):
        board = bd.Board(size=bd.SNAKE_LENGTH, greens=0, reds=0)
        self.assertEqual(len(board.snake), bd.SNAKE_LENGTH)


class TestReset(unittest.TestCase):
    def test_le_serpent_est_reengendre(self):
        """Sinon la session 2 heriterait du serpent de la session 1."""
        board = bd.Board(size=10, greens=0, reds=0)
        board.snake = [(9, 9), (8, 9), (7, 9), (6, 9)]
        board.reset()
        self.assertNotEqual(board.snake, [(9, 9), (8, 9), (7, 9), (6, 9)])
        self.assertEqual(len(board.snake), bd.SNAKE_LENGTH)

    def test_tout_est_remis_a_zero(self):
        board = bd.Board(size=10, greens=1, reds=0, idle_factor=1)
        pose(board, (5, 5), bd.RIGHT)
        board.greens = [(6, 5)]
        board.step(bd.RIGHT)
        self.assertEqual(len(board.snake), 4)
        joue(board, tour_du_plateau(board))
        self.assertTrue(board.truncated)

        board.reset()
        self.assertEqual(len(board.snake), 3, "le serpent est re-engendre")
        self.assertEqual(board.max_length, 3)
        self.assertEqual(board.steps, 0)
        self.assertEqual(board.idle, 0)
        self.assertTrue(board.alive)
        self.assertFalse(board.truncated)
        self.assertIsNone(board.last_event)
        self.assertIsNone(board.end_cause)
        self.assertEqual(len(board.greens), 1)


if __name__ == "__main__":
    unittest.main()
