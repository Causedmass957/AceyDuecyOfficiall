# --- Window Settings ---
import pygame

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

# --- Colors (RGB) ---
BG_COLOR = (40, 26, 13)      # Dark Wood
BOARD_LIGHT = (222, 184, 135) # Burlywood (Light triangles)
BOARD_DARK = (139, 69, 19)    # Saddle Brown (Dark triangles)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)

# --- UI Button Settings ---
ROLL_BUTTON_RECT = pygame.Rect(SCREEN_WIDTH // 2 - 60, SCREEN_HEIGHT // 2 + 75, 120, 50)

# Player Selection UI
SELECTION_BUTTONS = {
    2: pygame.Rect(SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2, 100, 60),
    3: pygame.Rect(SCREEN_WIDTH // 2 - 50,  SCREEN_HEIGHT // 2, 100, 60),
    4: pygame.Rect(SCREEN_WIDTH // 2 + 100, SCREEN_HEIGHT // 2, 100, 60)
}

# --- Rendering Tweaks ---
PIECE_RADIUS = 22
MAX_VISUAL_STACK = 3   # How many pieces to draw before switching to a number
STACK_OFFSET = 20      # Pixels between pieces in a stack
TEXT_SIZE = 24         # Size for the "x5" label

# Player Colors
PLAYER_COLORS = {
    1: (231, 76, 60),   # Red
    2: (52, 152, 219),  # Blue
    3: (241, 196, 15),  # Yellow
    4: (46, 204, 113)   # Green
}

# --- Board Geometry ---
PIPE_WIDTH = 80    # Width of each triangle base
PIPE_HEIGHT = 300  # How far the triangle extends
MIDDLE_BAR = 100    # Space for Jail in the center
MARGIN_X = 60     # Space on the left/right
MARGIN_Y = 50      # Space on top/bottom

HORIZONTAL_OFFSET = -50
BLOCK_WIDTH = PIPE_WIDTH * 6 
TOTAL_BOARD_WIDTH = (BLOCK_WIDTH * 2) + MIDDLE_BAR
BOARD_START_X = (SCREEN_WIDTH - TOTAL_BOARD_WIDTH) // 2 + HORIZONTAL_OFFSET
MIDDLE_BAR_WIDTH = 100 

def generate_board_coords():
    coords = {}
    for i in range(12):
        x = MARGIN_X + (i * PIPE_WIDTH)
        if i >= 6: x += MIDDLE_BAR
        y = MARGIN_Y
        coords[i] = (x, y)
    for i in range(12):
        x = MARGIN_X + ((11 - i) * PIPE_WIDTH)
        if (11 - i) >= 6: x += MIDDLE_BAR
        y = SCREEN_HEIGHT - MARGIN_Y
        coords[12 + i] = (x, y)
    return coords

BOARD_COORDS = generate_board_coords()

START_AREAS = {
    1: (20, 20),
    2: (SCREEN_WIDTH - 80, 20),
    3: (20, SCREEN_HEIGHT - 80),
    4: (SCREEN_WIDTH - 80, SCREEN_HEIGHT - 80)
}
