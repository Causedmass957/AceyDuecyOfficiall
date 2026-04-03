import random
import ProfileManager

class GameEngine:
    def __init__(self, num_players=4):
        self.profile_manager = None
        self.player_profiles = {}
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

        self.game_over = False
        self.winner_id = None
        self.final_standings = []
        self.required_to_win = 15

        # Tracks the most recent checker entered from start or jail this turn.
        # Needed for your rule: if pieces remain in start, the player may only
        # continue moving the piece they just entered.
        self.last_entered_index = None

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
        # Acey-Deucey bonus single die -> becomes doubles of that one die
        if self.waiting_for_doubles_roll:
            val = random.randint(1, 6)
            self.moves_available = [val, val, val, val]
            self.waiting_for_doubles_roll = False
            self.has_extra_roll = True
            self.selected_index = None
            self.last_entered_index = None
            self._increment_stat(self.current_player, "bonus_rolls_earned")
            return val, val

        d1, d2 = random.randint(1, 6), random.randint(1, 6)

        if d1 == d2:
            self.moves_available = [d1, d1, d1, d1]
            self.has_extra_roll = True
            self.is_acey_duecy_pending = False
            self._increment_stat(self.current_player, "doubles_rolled")
            self._increment_stat(self.current_player, "bonus_rolls_earned")
        elif (d1 == 1 and d2 == 2) or (d1 == 2 and d2 == 1):
            self.moves_available = [1, 2]
            self.is_acey_duecy_pending = True
            self.has_extra_roll = False
            self._increment_stat(self.current_player, "acey_duecy_rolls")
        else:
            self.moves_available = [d1, d2]
            self.has_extra_roll = False
            self.is_acey_duecy_pending = False

        self.selected_index = None
        self.last_entered_index = None
        return d1, d2

    def get_player_path(self, player_id):
        full_board = list(range(24))

        if player_id == 1:
            return full_board
        if player_id == 2:
            return list(range(11, -1, -1)) + list(range(23, 11, -1))
        if player_id == 3:
            return list(range(23, 11, -1)) + list(range(11, -1, -1))
        if player_id == 4:
            return list(range(12, 24)) + list(range(0, 12))

        return []

    def is_legal_move(self, player_id, start_pos, move_value):
        # Jail has highest priority
        if self.jail[player_id] > 0 and start_pos != -1:
            return False

        # If pieces are still in start, player may only:
        # - enter from start
        # - continue moving the checker they just entered this turn
        if self.start_pool[player_id] > 0 and start_pos >= 0:
            if start_pos != self.last_entered_index:
                return False

        path = self.get_player_path(player_id)

        # Figure out destination step
        if start_pos == -1:          # leaving jail
            target_step = move_value - 1
        elif start_pos == -2:        # leaving start
            target_step = move_value - 1
        else:
            try:
                current_step = path.index(start_pos)
                target_step = current_step + move_value
            except ValueError:
                return False

        # If this is a checker already in the scoring zone, it cannot move
        # at all until all of the player's pieces are in the scoring zone.
        if start_pos >= 0:
            scoring_zone = set(path[18:])
            if start_pos in scoring_zone and not self.all_pieces_in_scoring_zone(player_id):
                return False

        # Bearing off requires exact roll and all pieces in scoring zone
        if target_step >= 24:
            if target_step == 24 and self.can_bear_off(player_id):
                return True
            return False

        target_idx = path[target_step]
        occupants = self.board[target_idx]

        # Cannot land on an opponent point occupied by 2 or more enemy pieces
        if len(occupants) >= 2 and occupants[0] != player_id:
            return False

        return True

    def can_bear_off(self, player_id): return self.all_pieces_in_scoring_zone(player_id)

    def has_legal_moves(self, player_id):
        if not self.moves_available:
            return False

        # Jail has priority over everything
        if self.jail[player_id] > 0:
            for m in set(self.moves_available):
                if self.is_legal_move(player_id, -1, m):
                    return True
            return False

        # If pieces remain in start:
        # - can always try to enter from start
        # - can also continue the just-entered checker this turn
        if self.start_pool[player_id] > 0:
            for m in set(self.moves_available):
                if self.is_legal_move(player_id, -2, m):
                    return True

            if self.last_entered_index is not None and player_id in self.board[self.last_entered_index]:
                for m in set(self.moves_available):
                    if self.is_legal_move(player_id, self.last_entered_index, m):
                        return True

            return False

        # Normal board movement
        for idx, point in enumerate(self.board):
            if player_id in point:
                for m in set(self.moves_available):
                    if self.is_legal_move(player_id, idx, m):
                        return True

        return False

    def select_piece(self, player_id, index):
        if index is None:
            return False

        # Jail has highest priority
        if self.jail[player_id] > 0:
            if index == -1:
                self.selected_index = -1
                return True
            return False

        # If pieces remain in start, player may select:
        # - the start pool
        # - the checker they just entered this turn
        if self.start_pool[player_id] > 0:
            if index == -2:
                self.selected_index = -2
                return True

            if (
                index == self.last_entered_index
                and 0 <= index < 24
                and player_id in self.board[index]
            ):
                self.selected_index = index
                return True

            return False

        # Normal selection from board
        if 0 <= index < 24 and player_id in self.board[index]:
            self.selected_index = index
            return True

        return False

    def attempt_move(self, player_id, start_idx, target_idx):
        path = self.get_player_path(player_id)

        if target_idx == 24:
            if not self.can_bear_off(player_id):
                return False

            try:
                start_step = path.index(start_idx)
            except ValueError:
                return False

            for m in sorted(self.moves_available):
                if start_step + m == 24:
                    move_value = m
                    break
            else:
                return False

        else:
            try:
                if start_idx == -2 or start_idx == -1:
                    move_value = path.index(target_idx) + 1
                else:
                    move_value = path.index(target_idx) - path.index(start_idx)
            except ValueError:
                return False

        if move_value not in self.moves_available:
            return False

        if not self.is_legal_move(player_id, start_idx, move_value):
            return False

        # Remove from source first
        if start_idx == -2:
            self.start_pool[player_id] -= 1
        elif start_idx == -1:
            self.jail[player_id] -= 1
            self._increment_stat(player_id, "jail_exits", 1)            
        else:
            self.board[start_idx].remove(player_id)

        # Apply destination
        if target_idx == 24:
            self.finished_pool[player_id] += 1
            self._increment_stat(player_id, "pieces_scored", 1)
            if start_idx == self.last_entered_index:
                self.last_entered_index = None
        else:
            target_space = self.board[target_idx]

            # Hit blot -> send victim to jail
            if len(target_space) == 1 and target_space[0] != player_id:
                victim = target_space.pop()
                self.jail[victim] += 1
                self._increment_stat(player_id, "times_sent_to_jail", 1)
                self._increment_stat(victim, "times_jailed", 1)

            self.board[target_idx].append(player_id)

            # Track newly-entered checker or continued movement of it
            if start_idx in (-2, -1) or start_idx == self.last_entered_index:
                self.last_entered_index = target_idx

        self.moves_available.remove(move_value)
        self._increment_stat(player_id, "moves_made", 1)
        if target_idx == 24:
            self.check_game_over()
        return True

    def next_turn(self, forfeited=False):
        if self.game_over:
            return
        # If the player completed the whole roll normally, allow AD bonus or extra roll.
        # If they forfeited because they were stuck, they lose those bonuses.
        if not forfeited:
            if self.is_acey_duecy_pending and not self.moves_available:
                self.is_acey_duecy_pending = False
                self.waiting_for_doubles_roll = True
                self.selected_index = None
                self.last_entered_index = None
                return

            if self.has_extra_roll and not self.moves_available:
                self.has_extra_roll = False
                self.selected_index = None
                self.last_entered_index = None
                return

        current_idx = self.turn_order.index(self.current_player)
        self.current_player = self.turn_order[(current_idx + 1) % len(self.turn_order)]

        self.moves_available = []
        self.has_extra_roll = False
        self.is_acey_duecy_pending = False
        self.waiting_for_doubles_roll = False
        self.selected_index = None
        self.last_entered_index = None

    def pass_turn(self):
        if self.game_over:
            return False
        # Only pass when no legal moves remain.
        if self.has_legal_moves(self.current_player):
            return False
        
        self._increment_stat(self.current_player, "times_blocked", 1)
        self.moves_available = []
        self.next_turn(forfeited=True)
        return True
    
    def all_pieces_in_scoring_zone(self, player_id):
        if self.start_pool[player_id] > 0 or self.jail[player_id] > 0:
            return False

        path = self.get_player_path(player_id)
        scoring_zone = set(path[18:])

        for idx, point in enumerate(self.board):
            if player_id in point and idx not in scoring_zone:
                return False

        return True
    
    def set_profile_manager(self, profile_manager):
        self.profile_manager = profile_manager

    def set_player_profiles(self, player_profiles):
        self.player_profiles = player_profiles

    def get_player_name(self, player_id):
        return self.player_profiles.get(player_id, f"Player {player_id}")

    def _get_profile_name(self, player_id):
        return self.player_profiles.get(player_id)

    def _increment_stat(self, player_id, stat_name, amount=1):
        if self.profile_manager is None:
            return

        profile_name = self._get_profile_name(player_id)
        if not profile_name:
            return

        self.profile_manager.increment_stat(profile_name, stat_name, amount)

    def check_game_over(self):
        for player_id, count in self.finished_pool.items():
            if count >= 15:
                self.game_over = True
                self.winner_id = player_id
                self.final_standings = self.get_final_standings()
                return True
        return False
    
    def get_final_standings(self):
        standings = []

        for player_id in range(1, self.num_players + 1):
            finished = self.finished_pool.get(player_id, 0)
            standings.append((player_id, finished))

        # Higher finished count = better placing
        standings.sort(key=lambda item: item[1], reverse=True)

        return [player_id for player_id, _ in standings]