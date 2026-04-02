import random

class GameEngine:
    def __init__(self, num_players=4):
        self.phase = "PLAYER_SELECTION"
        self.num_players = num_players
        
        self.is_acey_duecy_pending = False
        self.waiting_for_doubles_roll = False
        self.has_extra_roll = False

        self.board = [[] for _ in range(24)]
        self.start_pool = {}
        self.jail = {}
        self.finished_pool = {}

        self.player_rolls = {}
        self.dice_values = []
        self.moves_available = []
        self.current_player = None
        self.turn_order = []
        
        self.selected_index = None

    def set_player_count(self, count):
        self.num_players = count
        self.start_pool = {i: 15 for i in range(1, count + 1)}
        self.jail = {i: 0 for i in range(1, count + 1)}
        self.finished_pool = {i: 0 for i in range(1, count + 1)}
        self.phase = "INITIAL_ROLL"

    def record_initial_roll(self, player_id):
        if self.player_rolls.get(player_id) is not None:
            return None
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        self.player_rolls[player_id] = d1 + d2
        if len(self.player_rolls) == self.num_players:
            self._determine_turn_order()
        return d1, d2

    def _determine_turn_order(self):
        max_roll = max(self.player_rolls.values())
        winners = [pid for pid, roll in self.player_rolls.items() if roll == max_roll]
        if len(winners) > 1:
            self.player_rolls = {}
            return 
        highest_roller = winners[0]
        players_template = [1, 2, 4, 3]
        active_players = [p for p in players_template if p <= self.num_players]
        start_idx = active_players.index(highest_roller)
        self.turn_order = []
        for i in range(len(active_players)):
            self.turn_order.append(active_players[(start_idx - i) % len(active_players)])
        self.current_player = self.turn_order[0]
        self.phase = "PLAYING"

    def roll_dice(self):
        if self.waiting_for_doubles_roll:
            val = random.randint(1, 6)
            self.moves_available = [val, val, val, val]
            self.waiting_for_doubles_roll = False
            self.has_extra_roll = True
            return val, val
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        if d1 == d2:
            self.moves_available = [d1, d1, d1, d1]
            self.has_extra_roll = True
        elif (d1 == 1 and d2 == 2) or (d1 == 2 and d2 == 1):
            self.moves_available = [1, 2]
            self.is_acey_duecy_pending = True
        else:
            self.moves_available = [d1, d2]
            self.has_extra_roll = False
        return d1, d2

    def get_player_path(self, player_id):
        full_board = list(range(24))
        if player_id == 1: return full_board
        if player_id == 2: return list(range(11, -1, -1)) + list(range(23, 11, -1))
        if player_id == 3: return list(range(23, 11, -1)) + list(range(11, -1, -1))
        if player_id == 4: return list(range(12, 24)) + list(range(0, 12))
        return []

    def is_legal_move(self, player_id, start_pos, move_value):
        if self.jail[player_id] > 0 and start_pos != -1: return False
        if self.start_pool[player_id] > 0 and start_pos >= 0: return False
        
        path = self.get_player_path(player_id)
        if start_pos == -1: target_step = move_value - 1
        elif start_pos == -2: target_step = move_value - 1
        else:
            try:
                current_step = path.index(start_pos)
                target_step = current_step + move_value
            except ValueError: return False

        if target_step >= 24:
            if target_step == 24 and self.can_bear_off(player_id): return True
            return False

        target_idx = path[target_step]
        occupants = self.board[target_idx]
        if len(occupants) >= 2 and occupants[0] != player_id: return False
        return True

    def can_bear_off(self, player_id):
        if self.start_pool[player_id] > 0 or self.jail[player_id] > 0: return False
        path = self.get_player_path(player_id)
        scoring_zone = path[18:]
        for idx, point in enumerate(self.board):
            if player_id in point:
                if idx not in scoring_zone: return False
        return True

    def has_legal_moves(self, player_id):
        if not self.moves_available: return False
        if self.jail[player_id] > 0:
            for m in set(self.moves_available):
                if self.is_legal_move(player_id, -1, m): return True
            return False
        if self.start_pool[player_id] > 0:
            for m in set(self.moves_available):
                if self.is_legal_move(player_id, -2, m): return True
            return False
        for idx, point in enumerate(self.board):
            if player_id in point:
                for m in set(self.moves_available):
                    if self.is_legal_move(player_id, idx, m): return True
        return False

    def select_piece(self, player_id, index):
        if index is None: return False
        if self.jail[player_id] > 0:
            if index == -1:
                self.selected_index = -1
                return True
            return False
        if self.start_pool[player_id] > 0:
            if index == -2:
                self.selected_index = -2
                return True
            return False
        if 0 <= index < 24 and player_id in self.board[index]:
            self.selected_index = index
            return True
        return False

    def attempt_move(self, player_id, start_idx, target_idx):
        path = self.get_player_path(player_id)
        if target_idx == 24:
            if not self.can_bear_off(player_id): return False
            for m in sorted(self.moves_available):
                start_step = path.index(start_idx)
                if start_step + m == 24:
                    move_value = m
                    break
            else: return False
        else:
            try:
                if start_idx == -2 or start_idx == -1: move_value = path.index(target_idx) + 1
                else: move_value = path.index(target_idx) - path.index(start_idx)
            except ValueError: return False

        if move_value in self.moves_available and self.is_legal_move(player_id, start_idx, move_value):
            if target_idx == 24:
                self.finished_pool[player_id] += 1
            else:
                target_space = self.board[target_idx]
                if len(target_space) == 1 and target_space[0] != player_id:
                    victim = target_space.pop()
                    self.jail[victim] += 1
                self.board[target_idx].append(player_id)
            
            if start_idx == -2: self.start_pool[player_id] -= 1
            elif start_idx == -1: self.jail[player_id] -= 1
            else: self.board[start_idx].remove(player_id)
            
            self.moves_available.remove(move_value)
            return True
        return False

    def next_turn(self):
        if self.is_acey_duecy_pending and not self.moves_available:
            self.is_acey_duecy_pending = False
            self.waiting_for_doubles_roll = True
            return
        if self.has_extra_roll and not self.moves_available:
            self.has_extra_roll = False
            return
        current_idx = self.turn_order.index(self.current_player)
        self.current_player = self.turn_order[(current_idx + 1) % len(self.turn_order)]
        self.moves_available = []
        self.has_extra_roll = False
        self.is_acey_duecy_pending = False
        self.waiting_for_doubles_roll = False

    def pass_turn(self):
        if self.has_legal_moves(self.current_player):
            return False
        self.moves_available = []
        self.next_turn()
        return True
