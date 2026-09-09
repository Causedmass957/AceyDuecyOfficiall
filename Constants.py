# --- Logical canvas size ---
# Everything is drawn onto a canvas this size; main.py scales it to the real
# window (windowed or fullscreen).  Layout.py derives all board geometry from it.
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

# --- Colors (RGB) ---
BG_COLOR = (34, 22, 12)       # Dark wood surround
BOARD_FELT = (58, 78, 66)     # Muted green playing field
BOARD_FRAME = (92, 60, 32)    # Wooden frame
BOARD_LIGHT = (222, 184, 135) # Burlywood (light points)
BOARD_DARK = (120, 66, 40)    # Saddle brown (dark points)
BAR_COLOR = (46, 30, 18)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
PANEL_BG = (25, 17, 9)
PANEL_BORDER = (120, 90, 55)

# --- Rendering tweaks ---
TEXT_SIZE = 24

# Player colors
PLAYER_COLORS = {
    1: (231, 76, 60),   # Red
    2: (52, 152, 219),  # Blue
    3: (241, 196, 15),  # Yellow
    4: (46, 204, 113),  # Green
}

# Seating order used to build the turn rotation (counter-clockwise = ascending).
SEATING_ORDER = [1, 2, 3, 4]

# Where each player sits, for prompts / labels.
SEAT_LABELS = {
    1: "top-left",
    2: "bottom-left",
    3: "bottom-right",
    4: "top-right",
}

# ------------------------------------------------------------------
# In-game rules text.  Each entry is (page title, [body lines]).
# ------------------------------------------------------------------
RULES_PAGES = [
    ("Overview", [
        "ACEY DUECY is a 2-to-4 player race game played on a",
        "backgammon board.  Each player owns 15 checkers and one",
        "corner of the board:",
        "",
        "    Player 1 - top-left        Player 4 - top-right",
        "    Player 2 - bottom-left     Player 3 - bottom-right",
        "",
        "Every player follows a private 24-point path that starts at",
        "their own corner, loops the entire board once, and ends in a",
        "6-point Scoring zone next to a neighbour's corner.",
        "Neighbouring players travel in opposite directions.",
        "",
        "Objective: be the first to bear all 15 checkers off the",
        "board.  The other players keep playing to settle 2nd, 3rd",
        "and 4th place.",
    ]),
    ("Starting the game", [
        "1. Choose 2, 3 or 4 players and assign a saved profile to",
        "   each seat.",
        "",
        "2. Initial roll: every player clicks their status panel once",
        "   to roll two dice.  The highest total plays first.  If the",
        "   highest total is tied, everyone rolls again.",
        "",
        "3. Play then passes counter-clockwise around the table,",
        "   which with this seating is player 1, 2, 3, 4 order,",
        "   starting from whoever won the initial roll.",
        "",
        "All 15 of your checkers begin in your Start area, off the",
        "board.  You must bring them onto the board before they can",
        "race.",
    ]),
    ("Rolling and moving", [
        "On your turn press ROLL to throw two dice.",
        "",
        "- A die of value N moves one checker N points forward along",
        "  your path.  The two dice are separate moves.",
        "- You must play a die whenever a legal move for it exists;",
        "  you may only PASS a die that cannot be played.",
        "- Doubles: play the rolled value four times, then roll",
        "  again.  Repeated doubles keep earning another roll.",
        "",
        "Entering from Start: a die of N places a checker on the Nth",
        "point of your path.  While ANY checker is still in your",
        "Start area, the only board checker you may move is one you",
        "entered from Start with the dice you are currently holding.",
        "Checkers placed on earlier rolls stay put until your Start",
        "area is empty.",
    ]),
    ("Acey-Deucey", [
        "Rolling a 1 and a 2 together is an Acey-Deucey:",
        "",
        "1. Play the 1 and the 2 normally.",
        "2. A single bonus die is rolled and played as doubles of",
        "   that number (four moves).",
        "3. You then take one more ordinary roll.",
        "",
        "Any part of the Acey-Deucey you cannot legally play is",
        "forfeited, and if you cannot play the opening 1 and 2 at",
        "all you lose the turn.",
    ]),
    ("Hitting and the Jail", [
        "Landing on a point occupied by exactly one enemy checker",
        "sends that checker to the Jail on the centre bar.",
        "",
        "- You may not land on a point holding two or more enemy",
        "  checkers.",
        "- Any number of your own checkers may share a point.",
        "",
        "While you have a checker in Jail you may do nothing else.",
        "A jailed checker re-enters like a Start checker: a die of N",
        "brings it to the Nth point of your path.  If neither die",
        "can bring it in, the turn is forfeited.",
    ]),
    ("Scoring zone and bearing off", [
        "Your Scoring zone is the final 6 points of your path.",
        "",
        "- Until every one of your checkers is in the Scoring zone,",
        "  a checker that is already there may not move again unless",
        "  it is the one you just moved in with the current dice.",
        "",
        "- Once all 15 checkers are in the Scoring zone you may bear",
        "  off.  Bearing off needs the EXACT number: a checker on",
        "  the Nth point from the edge needs a die of exactly N.  A",
        "  larger die cannot bear a checker off from a lower point.",
        "",
        "First player with all 15 off wins.  Play continues for the",
        "remaining places until every player is finished.",
    ]),
    ("Undo, history and stats", [
        "UNDO takes back your moves one at a time, but only moves",
        "made with the dice you are currently holding.  Once you",
        "roll again or end the turn, previous moves are locked in.",
        "",
        "END TURN appears when you have used every die; it also",
        "confirms the turn so you get a chance to UNDO first.",
        "",
        "HISTORY shows the turn-by-turn log and a live breakdown of",
        "every player's checkers.  Profile stats are written to disk",
        "only when a game finishes.",
        "",
        "Press F11 any time to toggle fullscreen.",
    ]),
]
