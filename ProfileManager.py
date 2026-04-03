import sqlite3
from datetime import datetime


class ProfileManager:
    def __init__(self, db_path="stats.db"):
        self.db_path = db_path
        self._initialize_database()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _initialize_database(self):
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    last_played_at TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_stats (
                    player_id INTEGER PRIMARY KEY,
                    games_played INTEGER NOT NULL DEFAULT 0,
                    wins INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    acey_duecy_rolls INTEGER NOT NULL DEFAULT 0,
                    doubles_rolled INTEGER NOT NULL DEFAULT 0,
                    times_jailed INTEGER NOT NULL DEFAULT 0,
                    times_sent_to_jail INTEGER NOT NULL DEFAULT 0,
                    times_blocked INTEGER NOT NULL DEFAULT 0,
                    pieces_scored INTEGER NOT NULL DEFAULT 0,
                    total_turns INTEGER NOT NULL DEFAULT 0,
                    moves_made INTEGER NOT NULL DEFAULT 0,
                    jail_exits INTEGER NOT NULL DEFAULT 0,
                    captures INTEGER NOT NULL DEFAULT 0,
                    pieces_entered_from_start INTEGER NOT NULL DEFAULT 0,
                    bonus_rolls_earned INTEGER NOT NULL DEFAULT 0,
                    bonus_rolls_forfeited INTEGER NOT NULL DEFAULT 0,
                    longest_block_zone_created INTEGER NOT NULL DEFAULT 0,
                    block_zones_created_7_plus INTEGER NOT NULL DEFAULT 0,
                    block_zones_faced_7_plus INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (player_id) REFERENCES players (id)
                )
            """)

            conn.commit()

    def create_profile(self, name):
        name = name.strip()
        if not name:
            return False

        now = datetime.utcnow().isoformat()

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM players WHERE name = ?", (name,))
            existing = cursor.fetchone()
            if existing:
                return False

            cursor.execute("""
                INSERT INTO players (name, created_at, last_played_at)
                VALUES (?, ?, ?)
            """, (name, now, now))

            player_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO player_stats (player_id)
                VALUES (?)
            """, (player_id,))

            conn.commit()
            return True
    def delete_profile(self, name):
        """
        Deletes a player profile and all associated stats.

        Returns:
            True  -> profile was deleted
            False -> profile not found
        """
        with self._connect() as conn:
            cursor = conn.cursor()

            # Get player ID first
            cursor.execute(
                "SELECT id FROM players WHERE name = ?",
                (name,)
            )

            row = cursor.fetchone()

            if not row:
                return False

            player_id = row[0]

            # Delete stats first because of foreign key relationship
            cursor.execute(
                "DELETE FROM player_stats WHERE player_id = ?",
                (player_id,)
            )

            # Delete player record
            cursor.execute(
                "DELETE FROM players WHERE id = ?",
                (player_id,)
            )

            conn.commit()

            return True

    def profile_exists(self, name):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM players WHERE name = ?", (name,))
            return cursor.fetchone() is not None

    def get_player_id(self, name):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM players WHERE name = ?", (name,))
            row = cursor.fetchone()
            return row[0] if row else None

    def get_profile(self, name):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    p.name,
                    p.created_at,
                    p.last_played_at,
                    s.games_played,
                    s.wins,
                    s.losses,
                    s.second_place,
                    s.third_place,
                    s.acey_duecy_rolls,
                    s.doubles_rolled,
                    s.times_jailed,
                    s.times_sent_to_jail,
                    s.times_blocked,
                    s.times_skunked,
                    s.pieces_scored,
                    s.total_turns,
                    s.moves_made,
                    s.jail_exits,
                    s.captures,
                    s.pieces_entered_from_start,
                    s.bonus_rolls_earned,
                    s.bonus_rolls_forfeited,
                    s.longest_block_zone_created,
                    s.block_zones_created_7_plus,
                    s.block_zones_faced_7_plus
                FROM players p
                JOIN player_stats s ON p.id = s.player_id
                WHERE p.name = ?
            """, (name,))

            row = cursor.fetchone()
            if not row:
                return None

            keys = [
                "name", "created_at", "last_played_at",
                "games_played", "wins", "losses", "second_place", "third_place",
                "acey_duecy_rolls", "doubles_rolled",
                "times_jailed", "times_sent_to_jail", "times_blocked", "times_skunked",
                "pieces_scored", "total_turns", "moves_made",
                "jail_exits", "captures", "pieces_entered_from_start",
                "bonus_rolls_earned", "bonus_rolls_forfeited",
                "longest_block_zone_created",
                "block_zones_created_7_plus",
                "block_zones_faced_7_plus"
            ]

            return dict(zip(keys, row))

    def get_all_profiles(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM players ORDER BY name ASC")
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    def increment_stat(self, name, stat_name, amount=1):
        allowed_stats = {
            "games_played", "wins", "losses", "second_place", "third_place",
            "acey_duecy_rolls", "doubles_rolled",
            "times_jailed", "times_sent_to_jail", "times_blocked", "times_skunked",
            "pieces_scored", "total_turns", "moves_made",
            "jail_exits", "captures", "bonus_rolls_earned", 
            "bonus_rolls_forfeited",
            "longest_block_zone_created",
            "block_zones_created_7_plus",
            "block_zones_faced_7_plus"
        }

        if stat_name not in allowed_stats:
            raise ValueError(f"Unknown stat: {stat_name}")

        player_id = self.get_player_id(name)
        if player_id is None:
            self.create_profile(name)
            player_id = self.get_player_id(name)

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE player_stats
                SET {stat_name} = {stat_name} + ?
                WHERE player_id = ?
            """, (amount, player_id))

            cursor.execute("""
                UPDATE players
                SET last_played_at = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat(), player_id))

            conn.commit()

    def update_max_stat(self, name, stat_name, value):
        allowed_stats = {
            "longest_block_zone_created"
        }

        if stat_name not in allowed_stats:
            raise ValueError(f"Unknown max stat: {stat_name}")

        player_id = self.get_player_id(name)
        if player_id is None:
            self.create_profile(name)
            player_id = self.get_player_id(name)

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(f"""
                SELECT {stat_name}
                FROM player_stats
                WHERE player_id = ?
            """, (player_id,))
            current = cursor.fetchone()[0]

            if value > current:
                cursor.execute(f"""
                    UPDATE player_stats
                    SET {stat_name} = ?
                    WHERE player_id = ?
                """, (value, player_id))

                cursor.execute("""
                    UPDATE players
                    SET last_played_at = ?
                    WHERE id = ?
                """, (datetime.utcnow().isoformat(), player_id))

                conn.commit()

    def record_win(self, name):
        self.increment_stat(name, "games_played", 1)
        self.increment_stat(name, "wins", 1)

    def record_loss(self, name):
        self.increment_stat(name, "games_played", 1)
        self.increment_stat(name, "losses", 1)

    def get_win_rate(self, name):
        profile = self.get_profile(name)
        if not profile:
            return 0.0

        games = profile["games_played"]
        if games == 0:
            return 0.0

        return round((profile["wins"] / games) * 100, 2)