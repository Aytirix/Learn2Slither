"""Direction artistique : palette, dimensions et polices."""

import pygame

# --- Palette ---------------------------------------------------------
BG_DEEP = (8, 11, 22)
BG_CARD = (14, 19, 36)
GRID = (30, 41, 66)
BORDER = (44, 58, 92)

TEXT = (226, 232, 240)
TEXT_DIM = (120, 137, 168)
TEXT_MUTED = (76, 90, 120)

ACCENT = (34, 211, 238)
SNAKE_HEAD = (125, 240, 255)
SNAKE_TAIL = (67, 56, 202)
SNAKE_EYE = (10, 14, 26)

GREEN_APPLE = (52, 211, 153)
RED_APPLE = (244, 63, 94)

STAR = (170, 195, 235)

# --- Dimensions ------------------------------------------------------
WIN_W = 1180
WIN_H = 760
FPS = 60

BOARD_PX = 620
BOARD_X = 44
BOARD_Y = (WIN_H - BOARD_PX) // 2

PANEL_X = BOARD_X + BOARD_PX + 40
PANEL_W = WIN_W - PANEL_X - 44

MONO_CANDIDATES = (
    "jetbrainsmono,firacode,cascadiacode,hacknerdfont,"
    "dejavusansmono,liberationmono,consolas,couriernew"
)
TITLE_CANDIDATES = (
    "orbitron,exo2,rajdhani,michroma,"
    "jetbrainsmono,dejavusansmono,liberationmono"
)


def load_fonts():
    """Retourne un dict de polices, avec repli sur la police par defaut."""
    mono = pygame.font.match_font(MONO_CANDIDATES)
    title = pygame.font.match_font(TITLE_CANDIDATES)
    return {
        "title": pygame.font.Font(title, 30),
        "sub": pygame.font.Font(mono, 13),
        "label": pygame.font.Font(mono, 12),
        "value": pygame.font.Font(mono, 22),
        "mono": pygame.font.Font(mono, 15),
        "vision": pygame.font.Font(mono, 13),
        "big": pygame.font.Font(title, 40),
        "hero": pygame.font.Font(title, 54),
    }
