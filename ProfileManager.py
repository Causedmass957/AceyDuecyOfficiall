import sqlite3
from datetime import datetime


# Every integer column the stats table is expected to have.  Missing columns
# are added automatically on start-up so an older stats.db keeps working.
STAT_COLUMNS = [
    "games_played",
    "wins",
    "losses",
    "times_skunked",
    "second_place",
    "third_place",
    "fourth_place",
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
    "longest_block_zone_created",
    "block_zones_created_7_plus",
    "block_zones_faced_7_plus",
    "biggest_win_margin",
]

# Columns that store a running maximum rather than a running total.
MAX_COLUMNS = {
    "longest_block_zone_created",
    "biggest_win_margin",
}


class ProfileManager:
    def __init__(self, db_path="stats.db"):
        self.db_path = db_path
        self._initialize_database()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    # ================================================================
    # SCHEMA
    # ================================================================
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

            columns_sql = ",\n".join(
                f"{name} INTEGER NOT NULL DEFAULT 0" for name in STAT_COLUMNS
            )
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS player_stats (
                    player_id INTEGER PRIMARY KEY,
                    {columns_sql},
                    FOREIGN KEY (player_id) REFERENCES players (id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS head_to_head (
                    player_id INTEGER NOT NULL,
                    opponent_id INTEGER NOT NULL,
                    wins INTEGER NOT NULL DEFAULT 0,
                    losses INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (player_id, opponent_id)
                )
            """)

            conn.commit()

            self._migrate_stat_columns(cursor)
            conn.commit()

    def _migrate_stat_columns(self, cursor):
        cursor.execute("PRAGMA table_info(player_stats)")
        existing = {row[1] for row in cursor.fetchall()}

        for name in STAT_COLUMNS:
            if name not in existing:
                cursor.execute(
                    f"ALTER TABLE player_stats ADD COLUMN {name} INTEGER NOT NULL DEFAULT 0"
                )

    # ================================================================
    # PROFILE CRUD
    # ================================================================
    def create_profile(self, name):
        name = name.strip()
        if not name:
            return False

        now = datetime.utcnow().isoformat()

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM players WHERE name = ?", (name,))
            if cursor.fetchone():
                return False

            cursor.execute("""
                INSERT INTO players (name, created_at, last_played_at)
                VALUES (?, ?, ?)
            """, (name, now, now))

            player_id = cursor.lastrowid

            cursor.execute("INSERT INTO player_stats (player_id) VALUES (?)", (player_id,))
            conn.commit()
            return True

    def delete_profile(self, name):
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM players WHERE name = ?", (name,))
            row = cursor.fetchone()
            if not row:
                return False

            player_id = row[0]

            cursor.execute("DELETE FROM player_stats WHERE player_id = ?", (player_id,))
            cursor.execute(
                "DELETE FROM head_to_head WHERE player_id = ? OR opponent_id = ?",
                (player_id, player_id),
            )
            cursor.execute("DELETE FROM players WHERE id = ?", (player_id,))
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

    def get_all_profiles(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM players ORDER BY name ASC")
            return [row[0] for row in cursor.fetchall()]

    def get_profile(self, name):
        with self._connect() as conn:
            cursor = conn.cursor()
            stat_cols = ", ".join(f"s.{c}" for c in STAT_COLUMNS)
            cursor.execute(f"""
                SELECT p.name, p.created_at, p.last_played_at, {stat_cols}
                FROM players p
                JOIN player_stats s ON p.id = s.player_id
                WHERE p.name = ?
            """, (name,))

            row = cursor.fetchone()
            if not row:
                return None

            keys = ["name", "created_at", "last_played_at"] + list(STAT_COLUMNS)
            return dict(zip(keys, row))

    # ================================================================
    # STAT WRITES
    # ================================================================
    def _ensure_player(self, name):
        player_id = self.get_player_id(name)
        if player_id is None:
            self.create_profile(name)
            player_id = self.get_player_id(name)
        return player_id

    def increment_stat(self, name, stat_name, amount=1):
        if stat_name not in STAT_COLUMNS or stat_name in MAX_COLUMNS:
            raise ValueError(f"Unknown stat: {stat_name}")

        player_id = self._ensure_player(name)
        if player_id is None:
            return

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE player_stats SET {stat_name} = {stat_name} + ? WHERE player_id = ?",
                (amount, player_id),
            )
            cursor.execute(
                "UPDATE players SET last_played_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), player_id),
            )
            conn.commit()

    def update_max_stat(self, name, stat_name, value):
        if stat_name not in MAX_COLUMNS:
            raise ValueError(f"Unknown max stat: {stat_name}")

        player_id = self._ensure_player(name)
        if player_id is None:
            return

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT {stat_name} FROM player_stats WHERE player_id = ?",
                (player_id,),
            )
            current = cursor.fetchone()[0]

            if value > current:
                cursor.execute(
                    f"UPDATE player_stats SET {stat_name} = ? WHERE player_id = ?",
                    (value, player_id),
                )
                cursor.execute(
                    "UPDATE players SET last_played_at = ? WHERE id = ?",
                    (datetime.utcnow().isoformat(), player_id),
                )
                conn.commit()

    # ================================================================
    # GAME RESULT HELPERS
    # ================================================================
    def record_win(self, name):
        self.increment_stat(name, "games_played", 1)
        self.increment_stat(name, "wins", 1)

    def record_loss(self, name):
        self.increment_stat(name, "games_played", 1)
        self.increment_stat(name, "losses", 1)

    def record_placement(self, name, place):
        column = {2: "second_place", 3: "third_place", 4: "fourth_place"}.get(place)
        if column:
            self.increment_stat(name, column, 1)

    def record_head_to_head(self, winner_name, loser_name):
        winner_id = self._ensure_player(winner_name)
        loser_id = self._ensure_player(loser_name)
        if winner_id is None or loser_id is None or winner_id == loser_id:
            return

        with self._connect() as conn:
            cursor = conn.cursor()
            for a, b, w, l in (
                (winner_id, loser_id, 1, 0),
                (loser_id, winner_id, 0, 1),
            ):
                cursor.execute("""
                    INSERT INTO head_to_head (player_id, opponent_id, wins, losses)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(player_id, opponent_id)
                    DO UPDATE SET wins = wins + ?, losses = losses + ?
                """, (a, b, w, l, w, l))
            conn.commit()

    def get_head_to_head(self, name):
        player_id = self.get_player_id(name)
        if player_id is None:
            return []

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.name, h.wins, h.losses
                FROM head_to_head h
                JOIN players p ON p.id = h.opponent_id
                WHERE h.player_id = ?
                ORDER BY p.name ASC
            """, (player_id,))
            return [
                {"opponent": row[0], "wins": row[1], "losses": row[2]}
                for row in cursor.fetchall()
            ]

    def get_win_rate(self, name):
        profile = self.get_profile(name)
        if not profile:
            return 0.0

        games = profile["games_played"]
        if games == 0:
            return 0.0

        return round((profile["wins"] / games) * 100, 2)
