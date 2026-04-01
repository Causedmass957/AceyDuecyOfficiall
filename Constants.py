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

# --- UI Button Settings ---
ROLL_BUTTON_RECT = pygame.Rect(SCREEN_WIDTH // 2 - 60, SCREEN_HEIGHT // 2 + 75, 120, 50)

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

# Constants.py
# Moved down 100 pixels (from SCREEN_HEIGHT // 2 - 25)
ROLL_BUTTON_RECT = pygame.Rect(SCREEN_WIDTH // 2 - 60, SCREEN_HEIGHT // 2 + 75, 120, 50)

# This is the ONLY offset we use to center everything
# If the board is being cut off on the left, this number needs to be positive
HORIZONTAL_OFFSET = -50

# The width of 6 triangles
BLOCK_WIDTH = PIPE_WIDTH * 6 

# The total width of the entire board assembly
TOTAL_BOARD_WIDTH = (BLOCK_WIDTH * 2) + MIDDLE_BAR

# The "Starting X" that centers everything on your screen
# This ensures equal margins on the left and right
BOARD_START_X = (SCREEN_WIDTH - TOTAL_BOARD_WIDTH) // 2 + HORIZONTAL_OFFSET

# The gap between the left and right sets of triangles
MIDDLE_BAR_WIDTH = 100 

# The total width of the two triangle blocks + the bar
# Assuming 12 triangles total across the top, 6 on each side
BOARD_CONTENT_WIDTH = (PIPE_WIDTH * 12) + MIDDLE_BAR_WIDTH




def generate_board_coords():
    """
    Calculates the base (x, y) for all 24 points.
    0-11: Top row (Left to Right)
    12-23: Bottom row (Right to Left)
    """
    coords = {}
    
    # --- Top Row (Indices 0-11) ---
    for i in range(12):
        x = MARGIN_X + (i * PIPE_WIDTH)
        if i >= 6: x += MIDDLE_BAR # Jump over the Jail center
        y = MARGIN_Y
        coords[i] = (x, y)
        
    # --- Bottom Row (Indices 12-23) ---
    # We go backwards to keep the "horseshoe" flow
    for i in range(12):
        # Index 12 is bottom right, Index 23 is bottom left
        x = MARGIN_X + ((11 - i) * PIPE_WIDTH)
        if (11 - i) >= 6: x += MIDDLE_BAR
        y = SCREEN_HEIGHT - MARGIN_Y
        coords[12 + i] = (x, y)
        
    return coords

BOARD_COORDS = generate_board_coords()

# --- Special Areas ---
JAIL_POS = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
# Start areas for the 4 corners
START_AREAS = {
    1: (20, 20),                  # Top Left
    2: (SCREEN_WIDTH - 80, 20),   # Top Right
    3: (20, SCREEN_HEIGHT - 80),  # Bottom Left
    4: (SCREEN_WIDTH - 80, SCREEN_HEIGHT - 80) # Bottom Right
}