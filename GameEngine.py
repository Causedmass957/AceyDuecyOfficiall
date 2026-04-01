import random

class GameEngine:
    def __init__(self, num_players=4):
        # --- Acey Duecy Attributes ---
        self.is_acey_duecy_pending = False
        self.waiting_for_doubles_roll = False

        # --- Game State ---
        self.num_players = num_players
        self.phase = "INITIAL_ROLL"  # INITIAL_ROLL, PLAYING, GAME_OVER
        self.current_player = None
        self.turn_order = []
        self.winner = None

        # --- Player & Board Data ---
        # Each index (0-23) is a list of player IDs currently on that spot
        self.board = [[] for _ in range(24)]
        self.start_pool = {i: 15 for i in range(1, num_players + 1)}
        self.jail = {i: 0 for i in range(1, num_players + 1)}
        self.finished_pool = {i: 0 for i in range(1, num_players + 1)}

        # --- Dice & Turn Logic ---
        self.player_rolls = {}        # Used during INITIAL_ROLL phase
        self.dice_values = []         # Current raw roll (e.g., [1, 2])
        self.moves_available = []     # Individual move units (e.g., [3, 3, 3, 3])
        
        # Acey-Deucey Logic Flags
        self.is_acey_deucey = False
        self.waiting_for_bonus_roll = False
        self.has_extra_roll = False

        # Selected piece start
        self.selected_index = None # Stores -2 (Start), -1 (Jail), or 0-23
        self.valid_moves_for_selected = []

    # -------------------------------------------------------------------------
    # PHASE 1: INITIAL ROLLS & TURN ORDER
    # -------------------------------------------------------------------------

    def record_initial_roll(self, player_id):
        # If we are in a tie-breaker, only allowed players can roll
        if self.player_rolls.get(player_id) is not None:
            return None
            
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        self.player_rolls[player_id] = d1 + d2
        
        # Check if everyone (or everyone in the tie-breaker) has rolled
        if len(self.player_rolls) == self.num_players:
            self._determine_turn_order()
            
        return d1, d2

    def _determine_turn_order(self):
        """Calculates order or triggers a re-roll if there is a tie for 1st."""
        max_roll = max(self.player_rolls.values())
        
        # Find all players who tied for the highest roll
        winners = [pid for pid, roll in self.player_rolls.items() if roll == max_roll]

        if len(winners) > 1:
            print(f"Tie detected between players {winners}! Re-rolling...")
            # Reset only the players who tied so they can roll again
            # Or reset everyone if you prefer a full clean slate:
            self.player_rolls = {} 
            # We stay in INITIAL_ROLL phase
            return 

        # No tie? Proceed to set the counter-clockwise order
        highest_roller = winners[0]
        players = [1, 2, 3, 4]
        start_idx = players.index(highest_roller)
        
        self.turn_order = []
        for i in range(self.num_players):
            self.turn_order.append(players[(start_idx - i) % self.num_players])
            
        self.current_player = self.turn_order[0]
        self.phase = "PLAYING"

    # -------------------------------------------------------------------------
    # PHASE 2: PLAYING & RULES
    # -------------------------------------------------------------------------

    def roll_dice(self):
        # If we just finished moving 1 and 2, roll for the doubles
        if self.waiting_for_doubles_roll:
            val = random.randint(1, 6)
            self.moves_available = [val, val, val, val]
            self.waiting_for_doubles_roll = False
            self.has_extra_roll = True # They get to roll again after these 4 moves
            print(f"Acey Duecy Doubles Rolled: {val}s!")
            return val, val

        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        
        # Standard Doubles (11, 22, 33, 44, 55, 66)
        if d1 == d2:
            self.moves_available = [d1, d1, d1, d1]
            self.has_extra_roll = True # Standard rule: doubles roll again
            print(f"Standard Doubles: {d1}s")
            
        # Acey Duecy (1 and 2)
        elif (d1 == 1 and d2 == 2) or (d1 == 2 and d2 == 1):
            self.moves_available = [1, 2]
            self.is_acey_duecy_pending = True
            print("ACEY DUECY! Move 1 and 2 to unlock your doubles roll.")
            
        else:
            self.moves_available = [d1, d2]
            self.has_extra_roll = False
            
        return d1, d2

    def get_player_path(self, player_id):
        """
        Translates a player's relative move (0-23) to absolute board index.
        P1: Top-Left -> CW
        P2: Top-Right -> CCW
        P3: Bottom-Left -> CCW (towards finish)
        P4: Bottom-Right -> CW (towards finish)
        """
        if player_id == 1: # Top-Left
            return list(range(24))
        if player_id == 2: # Top-Right
            return list(range(11, -1, -1)) + list(range(23, 11, -1))
        if player_id == 3: # Bottom-Left
            return list(range(23, 11, -1)) + list(range(0, 12))
        if player_id == 4: # Bottom-Right
            return list(range(12, 24)) + list(range(11, -1, -1))
        return []

    def validate_move(self, player_id, start_pos, move_value):
        """
        start_pos options:
        -1: Jail
        -2: Start Area
        0-23: Board index
        """
        # 1. JAIL LOCK: If you have pieces in jail, you MUST move them first
        if self.jail[player_id] > 0 and start_pos != -1:
            return False, "Must move piece out of jail."

        # 2. ENTRY REQUIREMENT: All pieces must be on board to move existing pieces
        if self.start_pool[player_id] > 0 and start_pos >= 0:
            return False, "All pieces must enter the board first."

        # 3. CALCULATE TARGET
        path = self.get_player_path(player_id)
        if start_pos == -1: # From Jail
            target_step = 0
        elif start_pos == -2: # From Start Area
            target_step = move_value - 1
        else: # Normal board move
            current_step = path.index(start_pos)
            target_step = current_step + move_value

        # 4. TARGET CHECK
        if target_step >= 24:
            # Check Exit Rule (Exact roll and all pieces in finish zone)
            return self._can_bear_off(player_id, target_step)

        target_idx = path[target_step]
        occupants = self.board[target_idx]
        
        if len(occupants) >= 2 and occupants[0] != player_id:
            return False, "Blocked by enemy stack."
            
        return True, "Legal Move"

    def _can_bear_off(self, player_id, target_step):
        # Implementation of the 'All pieces in finishing zone' rule
        # and 'Exact roll' (target_step must be exactly 24)
        if target_step != 24:
            return False, "Must have exact roll to bear off."
        # Logic to check if all pieces are in path[18:24] goes here
        return True, "Bearing off"

    def execute_move(self, player_id, start_pos, move_value):
        """Updates the game state. Assumes move was validated."""
        # This will be fleshed out as we build the interactions
        pass

    def next_turn(self):
        # 1. If they just finished moves 1 and 2
        if self.is_acey_duecy_pending and not self.moves_available:
            self.is_acey_duecy_pending = False
            self.waiting_for_doubles_roll = True
            # We stay on the current player and they must click to roll their double
            print("Time to roll your Acey Duecy doubles!")
            return

        # 2. If they have an extra roll (from doubles or finishing an Acey Duecy)
        if self.has_extra_roll and not self.moves_available:
            print(f"Player {self.current_player} rolls again!")
            self.has_extra_roll = False 
            return

        # 3. Otherwise, standard CCW rotation
        current_idx = self.turn_order.index(self.current_player)
        next_idx = (current_idx + 1) % len(self.turn_order)
        self.current_player = self.turn_order[next_idx]
        print(f"Turn passed to Player {self.current_player}")

    def select_piece(self, player_id, index):
        """Checks if the clicked index contains the player's piece."""
        # 1. Handle "Clicking nothing" immediately
        if index is None:
            return False

        # 2. Handle Start Pool (-2)
        if index == -2:
            # Check if current player actually has pieces left to move in
            if self.start_pool[player_id] > 0:
                self.selected_index = -2
                return True
            return False
        
        # 3. Handle Board Triangles (0-23)
        if 0 <= index < 24:
            if player_id in self.board[index]:
                self.selected_index = index
                return True
            
        return False
    
    def attempt_move(self, player_id, start_idx, target_idx):
        """Processes the move if legal and consumes the die value."""
        # 1. Basic validation
        if start_idx is None or target_idx is None:
            return False

        # 2. Get the player's specific path (their 0-23 map)
        path = self.get_player_path(player_id)
        
        # 3. Calculate 'distance' based on the player's unique path
        try:
            if start_idx == -2: # From Start Pool
                # The target_idx must exist in their path
                # move_value is the number of steps into the board (1-indexed)
                move_value = path.index(target_idx) + 1
            else: # From a triangle on the board
                start_step = path.index(start_idx)
                target_step = path.index(target_idx)
                move_value = target_step - start_step
        except ValueError:
            # This happens if the clicked triangle isn't in this player's path
            return False

        # 4. Is this move_value available in the current dice rolls?
        if move_value in self.moves_available:
            # Check for blockades (2+ enemy pieces)
            target_space = self.board[target_idx]
            if len(target_space) >= 2 and target_space[0] != player_id:
                print("Space is blocked!")
                return False

            # 5. Success! Update the data
            if start_idx == -2:
                self.start_pool[player_id] -= 1
            else:
                if player_id in self.board[start_idx]:
                    self.board[start_idx].remove(player_id)

            # Handle Hitting (if exactly 1 enemy piece is there)
            if len(target_space) == 1 and target_space[0] != player_id:
                victim = target_space.pop()
                self.jail[victim] += 1
                print(f"Player {victim} sent to Jail!")
            
            self.board[target_idx].append(player_id)
            
            # 6. Spend the die and return True
            self.moves_available.remove(move_value)
            return True

        return False