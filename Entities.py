class Piece:
    def __init__(self, owner_id, color):
        self.owner_id = owner_id
        self.color = color
        # -2: Start Pool, -1: Jail, 0-23: Board Index, 24: Finished/Off-board
        self.location = -2 
        
        # UI/Animation attributes
        self.current_screen_pos = [0, 0]
        self.is_selected = False

class Player:
    def __init__(self, player_id, color, path):
        self.player_id = player_id
        self.color = color
        self.path = path  # The specific list of 24 board indices (CW or CCW)
        
        # Initialize 15 pieces for this player
        self.pieces = [Piece(player_id, color) for _ in range(15)]
        
        # Tracking for initial high-roll phase
        self.initial_roll_sum = 0
        self.has_rolled_initial = False
        
        # Game State Flags
        self.is_active = False # True only when it is their turn