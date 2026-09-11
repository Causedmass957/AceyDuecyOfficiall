import random


# Per-game counters that are accumulated in memory while a game is played
# and only written to the profile database once the game finishes.  Keeping
# them in memory is what makes UNDO possible without touching the database.
TRACKED_STAT_KEYS = [
    "acey_duecy_rolls",
    "doubles_rolled",
    "times_jailed",
    "times_sent_to_jail",
    "times_blocked",
    "pieces_scored",
    "total_turns",
    "moves_made",
    "jail_exits",
    "captures",
    "pieces_entered_from_start",
    "bonus_rolls_earned",
    "bonus_rolls_forfeited",
    "block_zones_created_7_plus",
    "block_zones_faced_7_plus",
]


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

        # ------------------------------------------------------------
        # Game finish / placement tracking
        #   finished_players -> players who have borne all 15 checkers off
        #   placements       -> finishing order (1st, 2nd, 3rd, 4th)
        # The game keeps running until EVERY player is finished so that
        # 2nd/3rd/4th place are all decided by play.
        # ------------------------------------------------------------
        self.game_over = False
        self.winner_id = None
        self.final_standings = []
        self.required_to_win = 15
        self.finished_players = []
        self.placements = []

        # ------------------------------------------------------------
        # Same-turn movement trackers (unchanged rules)
        # ------------------------------------------------------------
        self.last_entered_index = None
        self.last_scoring_zone_index = None

        # ------------------------------------------------------------
        # Tracking system: per-game stats, turn log and undo buffer
        # ------------------------------------------------------------
        self.game_stats = {}
        self.turn_number = 0
        self.turn_started = False
        self.has_rolled_this_turn = False
        self.current_turn_entry = None       # log entry for the turn in progress
        self.current_turn_moves = []         # move records for UNDO (this roll only)
        self.turn_log = []                   # completed turn entries

    # ================================================================
    # SETUP
    # ================================================================
    def set_player_count(self, count):
        self.num_players = count
        self.start_pool = {i: 15 for i in range(1, count + 1)}
        self.jail = {i: 0 for i in range(1, count + 1)}
        self.finished_pool = {i: 0 for i in range(1, count + 1)}
        self.game_stats = {i: self._blank_stats() for i in range(1, count + 1)}
        self.phase = "INITIAL_ROLL"

    def _blank_stats(self):
        stats = {key: 0 for key in TRACKED_STAT_KEYS}
        stats["_block_zone_max"] = 0
        return stats

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
            # Tie for highest -> everyone rolls again.
            self.player_rolls = {}
            return

        highest_roller = winners[0]

        # Seats are numbered counter-clockwise around the table, so the
        # rotation is simply ascending player number starting at the winner.
        active_players = list(range(1, self.num_players + 1))
        start_idx = active_players.index(highest_roller)

        self.turn_order = [
            active_players[(start_idx + i) % len(active_players)]
            for i in range(len(active_players))
        ]

        self.current_player = self.turn_order[0]
        self.phase = "PLAYING"

    # ================================================================
    # DICE  (rules unchanged)
    # ================================================================
    def roll_dice(self):
        # A fresh roll always closes the UNDO window on the previous dice.
        self.current_turn_moves = []

        # Acey-Deucey bonus single die -> played as doubles of that die.
        if self.waiting_for_doubles_roll:
            val = random.randint(1, 6)
            self.moves_available = [val, val, val, val]
            self.waiting_for_doubles_roll = False
            self.has_extra_roll = True
            self.has_rolled_this_turn = True
            self.selected_index = None
            self.last_entered_index = None
            self.last_scoring_zone_index = None
            self._increment_stat(self.current_player, "bonus_rolls_earned")
            self._log_roll(f"Acey-Deucey bonus {val}-{val}")
            return val, val

        if not self.turn_started:
            self._begin_turn()

        d1, d2 = random.randint(1, 6), random.randint(1, 6)

        if d1 == d2:
            self.moves_available = [d1, d1, d1, d1]
            self.has_extra_roll = True
            self.is_acey_duecy_pending = False
            self._increment_stat(self.current_player, "doubles_rolled")
            self._increment_stat(self.current_player, "bonus_rolls_earned")
            self._log_roll(f"Doubles {d1}-{d2}")
        elif (d1 == 1 and d2 == 2) or (d1 == 2 and d2 == 1):
            self.moves_available = [1, 2]
            self.is_acey_duecy_pending = True
            self.has_extra_roll = False
            self._increment_stat(self.current_player, "acey_duecy_rolls")
            self._log_roll("Acey-Deucey (1-2)")
        else:
            self.moves_available = [d1, d2]
            self.has_extra_roll = False
            self.is_acey_duecy_pending = False
            self._log_roll(f"{d1}-{d2}")

        self.has_rolled_this_turn = True
        self.selected_index = None
        self.last_entered_index = None
        self.last_scoring_zone_index = None
        return d1, d2

    # ================================================================
    # PATHS  (rules unchanged - this is just the seat -> path mapping)
    #
    #   Player 1  top-left      travels clockwise
    #   Player 2  bottom-left   travels counter-clockwise
    #   Player 3  bottom-right  travels clockwise
    #   Player 4  top-right     travels counter-clockwise
    #
    # Board indices: 0 = top-left corner, 11 = top-right corner,
    #                12 = bottom-right corner, 23 = bottom-left corner.
    # ================================================================
    def get_player_path(self, player_id):
        if player_id == 1:
            return list(range(24))
        if player_id == 2:
            return list(range(23, 11, -1)) + list(range(11, -1, -1))
        if player_id == 3:
            return list(range(12, 24)) + list(range(0, 12))
        if player_id == 4:
            return list(range(11, -1, -1)) + list(range(23, 11, -1))
        return []

    # ================================================================
    # MOVE LEGALITY  (rules unchanged)
    # ================================================================
    def is_legal_move(self, player_id, start_pos, move_value):
        # Jail has highest priority
        if self.jail[player_id] > 0 and start_pos != -1:
            return False

        # If pieces are still in start, player may only:
        # - enter from start
        # - continue moving the checker they just entered this roll
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

        # Bearing off requires exact roll and all pieces in scoring zone
        if target_step >= 24:
            if target_step == 24 and self.can_bear_off(player_id):
                # If not all pieces are in scoring zone, do not allow
                # same-turn continuation from scoring zone to bear off
                if start_pos >= 0:
                    scoring_zone = set(path[18:])
                    if start_pos in scoring_zone and not self.all_pieces_in_scoring_zone(player_id):
                        return False
                return True
            return False

        target_idx = path[target_step]

        # Scoring-zone restriction:
        # If not all pieces are in scoring zone yet, a checker already in the
        # scoring zone may only continue moving if it is the same checker that
        # was just moved there this roll.
        if start_pos >= 0:
            scoring_zone = set(path[18:])
            if start_pos in scoring_zone and not self.all_pieces_in_scoring_zone(player_id):
                if start_pos != self.last_scoring_zone_index:
                    return False

        occupants = self.board[target_idx]

        # Cannot land on an opponent point occupied by 2 or more enemy pieces
        if len(occupants) >= 2 and occupants[0] != player_id:
            return False

        return True

    def can_bear_off(self, player_id):
        return self.all_pieces_in_scoring_zone(player_id)

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
        # - can also continue the just-entered checker this roll
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
        # - the checker they just entered this roll
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

    # ================================================================
    # MOVE EXECUTION  (rules unchanged; now records an undo entry)
    # ================================================================
    def attempt_move(self, player_id, start_idx, target_idx):
        path = self.get_player_path(player_id)

        # Guard against a stale board source (e.g. a lingering selection that
        # points at a checker that has already been borne off / moved away).
        if start_idx >= 0 and (start_idx >= 24 or player_id not in self.board[start_idx]):
            return False

        prev_last_entered = self.last_entered_index
        prev_last_scoring = self.last_scoring_zone_index

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

        hit_victim = None

        # Remove from source first
        if start_idx == -2:
            self.start_pool[player_id] -= 1
            self._increment_stat(player_id, "pieces_entered_from_start", 1)
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
            if start_idx == self.last_scoring_zone_index:
                self.last_scoring_zone_index = None
        else:
            target_space = self.board[target_idx]

            # Hit blot -> send victim to jail
            if len(target_space) == 1 and target_space[0] != player_id:
                hit_victim = target_space.pop()
                self.jail[hit_victim] += 1
                self._increment_stat(player_id, "times_sent_to_jail", 1)
                self._increment_stat(player_id, "captures", 1)
                self._increment_stat(hit_victim, "times_jailed", 1)

            self.board[target_idx].append(player_id)

            # Track newly-entered checker or continued movement of it
            if start_idx in (-2, -1) or start_idx == self.last_entered_index:
                self.last_entered_index = target_idx

            # Track same-turn continuation in scoring zone
            scoring_zone = set(path[18:])
            if target_idx in scoring_zone:
                self.last_scoring_zone_index = target_idx
            elif start_idx == self.last_scoring_zone_index:
                self.last_scoring_zone_index = None

        self.moves_available.remove(move_value)
        self._increment_stat(player_id, "moves_made", 1)

        # ------------------------------------------------------------
        # Completing all 15: assign placement and end the turn now,
        # even if dice remain.
        # ------------------------------------------------------------
        finished_now = False
        cleared_moves = []
        if target_idx == 24 and self.finished_pool[player_id] == self.required_to_win:
            finished_now = True
            self.check_game_over(player_id)
            cleared_moves = self.moves_available[:]
            self.moves_available = []
            self.selected_index = None
            self.last_entered_index = None
            self.last_scoring_zone_index = None

        record = {
            "player": player_id,
            "from": start_idx,
            "to": target_idx,
            "die": move_value,
            "hit": hit_victim,
            "prev_last_entered_index": prev_last_entered,
            "prev_last_scoring_zone_index": prev_last_scoring,
            "finished_now": finished_now,
            "cleared_moves": cleared_moves,
        }
        self.current_turn_moves.append(record)
        self._log_move(record)

        if finished_now and self.game_over:
            self._close_turn_entry()

        return True

    # ================================================================
    # UNDO  (only affects moves made with the dice currently in hand)
    # ================================================================
    def can_undo(self):
        return bool(self.current_turn_moves)

    def undo_last_move(self):
        if not self.current_turn_moves:
            return False

        rec = self.current_turn_moves.pop()
        pid = rec["player"]
        src = rec["from"]
        tgt = rec["to"]

        # 1. reverse finish / game-over side effects
        if rec["finished_now"]:
            if pid in self.finished_players:
                self.finished_players.remove(pid)
            if pid in self.placements:
                self.placements.remove(pid)
            if self.winner_id == pid:
                self.winner_id = None
            self.game_over = False
            self.final_standings = []
            self.moves_available.extend(rec["cleared_moves"])

        # 2. reverse destination
        if tgt == 24:
            self.finished_pool[pid] -= 1
            self._increment_stat(pid, "pieces_scored", -1)
        else:
            self.board[tgt].remove(pid)
            if rec["hit"] is not None:
                victim = rec["hit"]
                self.jail[victim] -= 1
                self.board[tgt].append(victim)
                self._increment_stat(pid, "times_sent_to_jail", -1)
                self._increment_stat(pid, "captures", -1)
                self._increment_stat(victim, "times_jailed", -1)

        # 3. reverse source
        if src == -2:
            self.start_pool[pid] += 1
            self._increment_stat(pid, "pieces_entered_from_start", -1)
        elif src == -1:
            self.jail[pid] += 1
            self._increment_stat(pid, "jail_exits", -1)
        else:
            self.board[src].append(pid)

        # 4. hand the die back
        self.moves_available.append(rec["die"])
        self.moves_available.sort()
        self._increment_stat(pid, "moves_made", -1)

        # 5. restore same-turn trackers
        self.last_entered_index = rec["prev_last_entered_index"]
        self.last_scoring_zone_index = rec["prev_last_scoring_zone_index"]

        # 6. tidy the turn log + selection
        if self.current_turn_entry and self.current_turn_entry["moves"]:
            self.current_turn_entry["moves"].pop()
        self.selected_index = None
        return True

    # ================================================================
    # TURN FLOW
    # ================================================================
    def _begin_turn(self):
        self.turn_started = True
        self.turn_number += 1
        self._increment_stat(self.current_player, "total_turns", 1)
        self.current_turn_entry = {
            "turn": self.turn_number,
            "player": self.current_player,
            "name": self.get_player_name(self.current_player),
            "rolls": [],
            "moves": [],
        }

    def awaiting_end_turn(self):
        """True when the player has rolled, has no dice left, and must
        press END TURN to hand play on (giving a window to UNDO)."""
        return (
            self.has_rolled_this_turn
            and not self.moves_available
            and not self.waiting_for_doubles_roll
            and not self.game_over
        )

    def end_turn(self):
        # Closing the turn locks in the current dice -> UNDO window shuts.
        self.current_turn_moves = []

        if self.game_over:
            self._close_turn_entry()
            return

        self._update_block_zone_stats(self.current_player)

        # Bonus-roll transitions keep the SAME player on turn.
        if self.is_acey_duecy_pending and not self.moves_available:
            self.is_acey_duecy_pending = False
            self.waiting_for_doubles_roll = True
            self.has_rolled_this_turn = False
            self._reset_selection_state()
            return

        if self.has_extra_roll and not self.moves_available:
            self.has_extra_roll = False
            self.has_rolled_this_turn = False
            self._reset_selection_state()
            return

        self._advance_to_next_player(forfeited=False)

    def pass_turn(self):
        if self.game_over:
            return False

        # Only allowed when nothing can be played.
        if self.has_legal_moves(self.current_player):
            return False

        self._increment_stat(self.current_player, "times_blocked", 1)

        if self.has_extra_roll or self.is_acey_duecy_pending or self.waiting_for_doubles_roll:
            self._increment_stat(self.current_player, "bonus_rolls_forfeited", 1)

        self.current_turn_moves = []
        self._update_block_zone_stats(self.current_player)
        self.moves_available = []
        self._advance_to_next_player(forfeited=True)
        return True

    def _advance_to_next_player(self, forfeited=False):
        if self.current_turn_entry is not None:
            if forfeited and not self.current_turn_entry["moves"]:
                self.current_turn_entry["moves"].append("no legal move - forfeited")
            self.turn_log.append(self.current_turn_entry)
            self.current_turn_entry = None

        if not self.game_over:
            current_idx = self.turn_order.index(self.current_player)
            for offset in range(1, len(self.turn_order) + 1):
                nxt = self.turn_order[(current_idx + offset) % len(self.turn_order)]
                if nxt not in self.finished_players:
                    self.current_player = nxt
                    break

        self.moves_available = []
        self.has_extra_roll = False
        self.is_acey_duecy_pending = False
        self.waiting_for_doubles_roll = False
        self.has_rolled_this_turn = False
        self.turn_started = False
        self._reset_selection_state()

    def _reset_selection_state(self):
        self.selected_index = None
        self.last_entered_index = None
        self.last_scoring_zone_index = None

    def _close_turn_entry(self):
        if self.current_turn_entry is not None:
            self.turn_log.append(self.current_turn_entry)
            self.current_turn_entry = None

    # Backwards-compatible alias for older callers.
    def next_turn(self, forfeited=False):
        if forfeited:
            self._advance_to_next_player(forfeited=True)
        else:
            self.end_turn()

    # ================================================================
    # SCORING ZONE HELPERS  (rules unchanged)
    # ================================================================
    def all_pieces_in_scoring_zone(self, player_id):
        if self.start_pool[player_id] > 0 or self.jail[player_id] > 0:
            return False

        path = self.get_player_path(player_id)
        scoring_zone = set(path[18:])

        for idx, point in enumerate(self.board):
            if player_id in point and idx not in scoring_zone:
                return False

        return True

    def on_board_count(self, player_id):
        return sum(point.count(player_id) for point in self.board)

    # ================================================================
    # CONTROLLER NAVIGATION HELPERS
    # Give the game pad a concrete list of "things I can pick" and, once
    # a checker is picked, "where it can go" - so the pad cycles through
    # real legal choices instead of a free-floating cursor.
    # ================================================================
    def movable_sources(self, player_id):
        """Ordered list of sources the current player could select this
        roll: -1 = jail, -2 = start pool, 0..23 = a board point that has
        at least one legal move."""
        if self.game_over or self.phase != "PLAYING" or not self.moves_available:
            return []

        if self.jail.get(player_id, 0) > 0:
            return [-1] if self.legal_destinations(player_id, -1) else []

        if self.start_pool.get(player_id, 0) > 0:
            sources = []
            if self.legal_destinations(player_id, -2):
                sources.append(-2)
            li = self.last_entered_index
            if (li is not None and 0 <= li < 24 and player_id in self.board[li]
                    and self.legal_destinations(player_id, li)):
                sources.append(li)
            return sources

        return [idx for idx in range(24)
                if player_id in self.board[idx] and self.legal_destinations(player_id, idx)]

    def legal_destinations(self, player_id, source):
        """Ordered list of target indices reachable from `source` with the
        dice in hand (24 = bear off)."""
        path = self.get_player_path(player_id)
        dests = []

        for mv in sorted(set(self.moves_available)):
            if not self.is_legal_move(player_id, source, mv):
                continue

            if source in (-1, -2):
                step = mv - 1
                target = path[step] if 0 <= step < 24 else None
            else:
                try:
                    step = path.index(source) + mv
                except ValueError:
                    continue
                if step == 24:
                    target = 24
                elif step < 24:
                    target = path[step]
                else:
                    target = None

            if target is not None and target not in dests:
                dests.append(target)

        return sorted(dests)

    # ================================================================
    # PROFILES / NAMES
    # ================================================================
    def set_profile_manager(self, profile_manager):
        self.profile_manager = profile_manager

    def set_player_profiles(self, player_profiles):
        self.player_profiles = player_profiles

    def get_player_name(self, player_id):
        return self.player_profiles.get(player_id, f"Player {player_id}")

    def _get_profile_name(self, player_id):
        return self.player_profiles.get(player_id)

    # ================================================================
    # STAT / LOG PLUMBING  (in-memory until the game finishes)
    # ================================================================
    def _increment_stat(self, player_id, stat_name, amount=1):
        bucket = self.game_stats.get(player_id)
        if bucket is None:
            return
        if stat_name in bucket:
            bucket[stat_name] += amount

    def _log_roll(self, text):
        if self.current_turn_entry is not None:
            self.current_turn_entry["rolls"].append(text)

    def _log_move(self, rec):
        if self.current_turn_entry is None:
            return

        def label(value):
            if value == -2:
                return "start"
            if value == -1:
                return "jail"
            if value == 24:
                return "off"
            return f"pt{value}"

        note = f" (hit P{rec['hit']})" if rec["hit"] is not None else ""
        self.current_turn_entry["moves"].append(
            f"{label(rec['from'])} -> {label(rec['to'])}{note}"
        )

    def _update_block_zone_stats(self, player_id):
        path = self.get_player_path(player_id)

        run = 0
        longest = 0
        for idx in path:
            point = self.board[idx]
            if len(point) >= 2 and point[0] == player_id:
                run += 1
                longest = max(longest, run)
            else:
                run = 0

        bucket = self.game_stats.get(player_id)
        if bucket is None:
            return

        if longest > bucket["_block_zone_max"]:
            bucket["_block_zone_max"] = longest

        if longest >= 7:
            bucket["block_zones_created_7_plus"] += 1
            for opp in range(1, self.num_players + 1):
                if opp != player_id and opp not in self.finished_players:
                    opp_bucket = self.game_stats.get(opp)
                    if opp_bucket is not None:
                        opp_bucket["block_zones_faced_7_plus"] += 1

    # ================================================================
    # GAME OVER / PLACEMENTS
    # ================================================================
    def check_game_over(self, player_id):
        """Called when a player bears a checker off.  If that player has now
        borne all 15 off, record their placement.  The game only ends once
        every player is finished."""
        if self.finished_pool.get(player_id, 0) < self.required_to_win:
            return None

        if player_id not in self.finished_players:
            self.finished_players.append(player_id)
            self.placements.append(player_id)

        place = self.placements.index(player_id) + 1

        if place == 1:
            self.winner_id = player_id

        if len(self.finished_players) >= self.num_players:
            self.final_standings = self.placements[:]
            self.game_over = True

        return place

    def get_standings(self):
        """Best-to-worst player order.  Uses the settled order once the game
        is over, otherwise a provisional order (finishers first, then by
        checkers borne off)."""
        if self.final_standings:
            return self.final_standings[:]

        order = list(self.placements)
        rest = [p for p in range(1, self.num_players + 1) if p not in order]
        rest.sort(key=lambda p: self.finished_pool.get(p, 0), reverse=True)
        return order + rest

    def compile_results(self):
        rows = []
        for rank, pid in enumerate(self.get_standings(), start=1):
            bucket = self.game_stats.get(pid, {})
            rows.append({
                "rank": rank,
                "player": pid,
                "name": self.get_player_name(pid),
                "borne_off": self.finished_pool.get(pid, 0),
                "on_board": self.on_board_count(pid),
                "jailed": self.jail.get(pid, 0),
                "in_start": self.start_pool.get(pid, 0),
                "turns": bucket.get("total_turns", 0),
                "captures": bucket.get("captures", 0),
                "times_jailed": bucket.get("times_jailed", 0),
            })
        return rows

    # Kept for backwards compatibility.
    def get_final_standings(self):
        return self.get_standings()

    # ================================================================
    # SAVE / RESUME
    # A paused game is serialised to plain JSON.  Everything the engine
    # needs to carry on is a list / dict / int / bool / None already;
    # the only wrinkle is that JSON turns int dict-keys into strings, so
    # from_dict() converts the player-id keyed maps back.
    # ================================================================
    SAVE_VERSION = 1

    def to_dict(self):
        return {
            "version": self.SAVE_VERSION,
            "phase": self.phase,
            "num_players": self.num_players,
            "player_profiles": {str(k): v for k, v in self.player_profiles.items()},
            "is_acey_duecy_pending": self.is_acey_duecy_pending,
            "waiting_for_doubles_roll": self.waiting_for_doubles_roll,
            "has_extra_roll": self.has_extra_roll,
            "board": [list(point) for point in self.board],
            "start_pool": self.start_pool,
            "jail": self.jail,
            "finished_pool": self.finished_pool,
            "player_rolls": self.player_rolls,
            "dice_values": list(self.dice_values),
            "moves_available": list(self.moves_available),
            "current_player": self.current_player,
            "turn_order": list(self.turn_order),
            "game_over": self.game_over,
            "winner_id": self.winner_id,
            "final_standings": list(self.final_standings),
            "required_to_win": self.required_to_win,
            "finished_players": list(self.finished_players),
            "placements": list(self.placements),
            "last_entered_index": self.last_entered_index,
            "last_scoring_zone_index": self.last_scoring_zone_index,
            "game_stats": {str(k): dict(v) for k, v in self.game_stats.items()},
            "turn_number": self.turn_number,
            "turn_started": self.turn_started,
            "has_rolled_this_turn": self.has_rolled_this_turn,
            "current_turn_entry": self.current_turn_entry,
            "current_turn_moves": self.current_turn_moves,
            "turn_log": list(self.turn_log),
        }

    @classmethod
    def from_dict(cls, data):
        def int_keys(d):
            return {int(k): v for k, v in (d or {}).items()}

        eng = cls(num_players=data.get("num_players", 4))
        eng.phase = data["phase"]
        eng.num_players = data["num_players"]
        eng.player_profiles = int_keys(data.get("player_profiles"))
        eng.is_acey_duecy_pending = data["is_acey_duecy_pending"]
        eng.waiting_for_doubles_roll = data["waiting_for_doubles_roll"]
        eng.has_extra_roll = data["has_extra_roll"]
        eng.board = [list(point) for point in data["board"]]
        eng.start_pool = int_keys(data["start_pool"])
        eng.jail = int_keys(data["jail"])
        eng.finished_pool = int_keys(data["finished_pool"])
        eng.player_rolls = int_keys(data["player_rolls"])
        eng.dice_values = list(data.get("dice_values", []))
        eng.moves_available = list(data["moves_available"])
        eng.current_player = data["current_player"]
        eng.turn_order = list(data["turn_order"])
        eng.game_over = data["game_over"]
        eng.winner_id = data["winner_id"]
        eng.final_standings = list(data["final_standings"])
        eng.required_to_win = data.get("required_to_win", 15)
        eng.finished_players = list(data["finished_players"])
        eng.placements = list(data["placements"])
        eng.last_entered_index = data["last_entered_index"]
        eng.last_scoring_zone_index = data["last_scoring_zone_index"]
        eng.game_stats = {int(k): dict(v) for k, v in (data.get("game_stats") or {}).items()}
        eng.turn_number = data["turn_number"]
        eng.turn_started = data["turn_started"]
        eng.has_rolled_this_turn = data["has_rolled_this_turn"]
        eng.current_turn_entry = data.get("current_turn_entry")
        eng.current_turn_moves = data.get("current_turn_moves") or []
        eng.turn_log = list(data.get("turn_log", []))
        eng.selected_index = None
        return eng
